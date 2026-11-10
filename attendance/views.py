from math import radians, sin, cos, sqrt, atan2
import json
from datetime import datetime, time, timedelta
from django.conf import settings
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect, render
from accounts.models import UserProfile
from notifications.models import Notification
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from django.db import transaction
from academics.models import (
    ClassSection,
    Subject,
    SubjectEmployeeAssignment,
    TimetableEntry,
)

from admissions.models import (
    StudentAdmissionApplication,
    ParentStudent,
)

from .models import (
    StudentAttendance,
    EmployeeAttendance,
    AttendanceParentNotification,
    AttendanceSession,
    AttendanceCorrection,
)
from .services import (
    SYSTEM_ABSENCE_PREFIX,
    employee_attendance_summary,
    employee_start_date,
    holiday_details,
    holiday_report_entries,
    is_holiday,
    student_account_start_date,
    student_is_on_approved_leave,
    student_attendance_summary,
    user_is_on_approved_leave,
)
MANAGEMENT_ROLES = {
    "chairman",
    "principal",
    "vice_principal",
    "accountant",
}

EMPLOYEE_ATTENDANCE_VIEW_ROLES = {
    "chairman",
    "principal",
    "vice_principal",
    "accountant",
}

MY_ATTENDANCE_ROLES = {
    "principal",
    "vice_principal",
    "teacher",
    "bus_driver",
    "admission_staff",
    "system_administrator",
    "accountant",
}

EMPLOYEE_ROLES = {
    "chairman",
    "principal",
    "vice_principal",
    "teacher",
    "bus_driver",
    "system_administrator",
    "admission_staff",
    "accountant",
}
def get_role(user):

    profile = getattr(
        user,
        "profile",
        None,
    )

    if not profile:
        return None

    return profile.role


def sync_parent_attendance_notifications(record):
    if record.status != "Absent":
        AttendanceParentNotification.objects.filter(
            attendance=record
        ).delete()
        return

    parent_links = ParentStudent.objects.filter(
        student=record.student,
        is_active=True,
    ).select_related("parent")
    student_name = (
        f"{record.student.first_name} {record.student.last_name or ''}"
    ).strip()
    message_text = (
        f"Your child {student_name} was marked Absent for "
        f"{record.subject.subject_name} on {record.date:%d %b %Y}."
    )

    for parent_link in parent_links:
        AttendanceParentNotification.objects.get_or_create(
            parent=parent_link.parent,
            attendance=record,
            defaults={
                "student": record.student,
                "title": "Attendance Alert",
                "message": message_text,
            },
        )


def create_attendance_notifications(recipients, title, message, related_url):
    for recipient in recipients:
        Notification.objects.create(
            recipient=recipient,
            title=title,
            message=message,
            notification_type="attendance",
            related_url=related_url,
        )

# =========================================================
# GPS DISTANCE CALCULATION
# =========================================================

def calculate_distance_meters(
    latitude1,
    longitude1,
    latitude2,
    longitude2,
):
    """
    Calculate distance between two GPS coordinates
    using the Haversine formula.
    """

    earth_radius = 6371000  # meters

    lat1 = radians(float(latitude1))
    lon1 = radians(float(longitude1))

    lat2 = radians(float(latitude2))
    lon2 = radians(float(longitude2))

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        sin(dlat / 2) ** 2
        + cos(lat1)
        * cos(lat2)
        * sin(dlon / 2) ** 2
    )

    c = 2 * atan2(
        sqrt(a),
        sqrt(1 - a),
    )

    return earth_radius * c


# =========================================================
# GET EMPLOYEE ATTENDANCE RECORD
# =========================================================

def get_today_employee_attendance(user):

    today = timezone.localdate()

    attendance = EmployeeAttendance.objects.filter(
        employee=user,
        date=today,
    ).first()

    if attendance is None:
        attendance = EmployeeAttendance(
            employee=user,
            date=today,
            status="Present",
        )

    return attendance

def finalize_employee_attendance(employees, attendance_date):
    """
    After school closing:
    1. No check-in -> Absent
    2. Check-in but no check-out -> Absent
    3. Approved Leave -> Preserve Leave
    4. Completed attendance -> Preserve existing status
    """

    closing_time = time(17, 0)  # School closing: 5:00 PM

    now = timezone.localtime()
    today = timezone.localdate()

    # Never finalize a future date.
    if attendance_date > today:
        return

    # Wait until school closing time for today's attendance.
    if attendance_date == today and now.time() < closing_time:
        return

    for employee in employees:
        attendance, created = EmployeeAttendance.objects.get_or_create(
            employee=employee,
            date=attendance_date,
            defaults={"status": "Absent"},
        )

        # Preserve approved leave.
        if attendance.status == "Leave":
            continue

        # No check-in: absent.
        if not attendance.check_in:
            if attendance.status != "Absent":
                attendance.status = "Absent"
                attendance.save(update_fields=["status"])
            continue

        # Check-in exists but checkout is missing: absent.
        if not attendance.check_out:
            if attendance.status != "Absent":
                attendance.status = "Absent"
                attendance.save(update_fields=["status"])

def get_location_name(latitude, longitude):
    if latitude is None or longitude is None:
        return None

    try:
        params = urlencode({
            "lat": str(latitude),
            "lon": str(longitude),
            "format": "jsonv2",
            "zoom": 14,
            "addressdetails": 1,
        })

        url = (
            "https://nominatim.openstreetmap.org/reverse?"
            f"{params}"
        )

        request = Request(
            url,
            headers={
                "User-Agent": "SchoolManagementSystem/1.0"
            },
        )

        with urlopen(request, timeout=10) as response:
            data = json.loads(
                response.read().decode("utf-8")
            )

        address = data.get("address", {})

        area = (
            address.get("suburb")
            or address.get("neighbourhood")
            or address.get("residential")
            or address.get("village")
            or address.get("town")
            or address.get("city")
            or address.get("municipality")
        )

        district = address.get("state_district")
        state = address.get("state")

        parts = []

        for value in (area, district, state):
            if value and value not in parts:
                parts.append(value)

        if parts:
            return ", ".join(parts)

        return data.get("display_name")

    except (
        HTTPError,
        URLError,
        TimeoutError,
        ValueError,
        OSError,
    ):
        return None

def check_school_location(latitude, longitude):

    geofence_enabled = getattr(
        settings,
        "ATTENDANCE_GEOFENCE_ENABLED",
        False,
    )

    if not geofence_enabled:
        return True, 0

    school_latitude = getattr(
        settings,
        "ATTENDANCE_SCHOOL_LATITUDE",
        None,
    )

    school_longitude = getattr(
        settings,
        "ATTENDANCE_SCHOOL_LONGITUDE",
        None,
    )

    radius = getattr(
        settings,
        "ATTENDANCE_GEOFENCE_RADIUS_METERS",
        200,
    )

    if (
        school_latitude is None
        or school_longitude is None
    ):
        return False, None

    distance = calculate_distance_meters(
        latitude,
        longitude,
        school_latitude,
        school_longitude,
    )

    return distance <= radius, distance

def calculate_late_minutes(check_in_time):

    start_time_string = getattr(
        settings,
        "ATTENDANCE_START_TIME",
        "08:30",
    )

    grace_minutes = getattr(
        settings,
        "ATTENDANCE_GRACE_MINUTES",
        10,
    )

    start_time = datetime.strptime(
        start_time_string,
        "%H:%M",
    ).time()

    start_datetime = datetime.combine(
        timezone.localdate(),
        start_time,
    )

    check_in_datetime = datetime.combine(
        timezone.localdate(),
        check_in_time,
    )

    difference = (
        check_in_datetime - start_datetime
    ).total_seconds() / 60

    if difference <= grace_minutes:
        return 0

    return int(difference)

@login_required
def employee_my_attendance(request):
    if get_role(request.user) not in (
        EMPLOYEE_ATTENDANCE_VIEW_ROLES | MY_ATTENDANCE_ROLES
    ):
        return HttpResponseForbidden(
            "You are not allowed to view employee attendance."
        )

    today = timezone.localdate()

    # Create today's record if it does not exist.
    attendance = get_today_employee_attendance(request.user)

    records = EmployeeAttendance.objects.filter(
        employee=request.user
    ).order_by("-date")[:30]
    attendance_summary = employee_attendance_summary(
        request.user,
        employee_start_date(request.user),
        today,
    )

    return render(
        request,
        "attendance/employee_my_attendance.html",
        {
            "attendance": attendance,
            "records": records,
            "attendance_summary": attendance_summary,
            "selected_holiday": holiday_details(today),
        },
    )

@login_required
def employee_check_in(request):
    if get_role(request.user) not in EMPLOYEE_ROLES:
        return JsonResponse({
            "success": False,
            "message": "You are not authorized to check in as an employee.",
        }, status=403)
    if request.method != "POST":
        return JsonResponse({
            "success": False,
            "message": "Invalid request method.",
        }, status=405)

    try:
        if user_is_on_approved_leave(request.user, timezone.localdate()):
            return JsonResponse({
                "success": False,
                "message": "Approved leave is recorded for today; check-in is unavailable.",
            }, status=400)
        if is_holiday(timezone.localdate()):
            holiday = holiday_details(timezone.localdate())
            return JsonResponse({
                "success": False,
                "message": f"{holiday['name']} is a holiday. Check-in is unavailable.",
            }, status=400)

        latitude = request.POST.get("latitude")
        longitude = request.POST.get("longitude")
        accuracy = request.POST.get("accuracy")

        if not latitude or not longitude:
            return JsonResponse({
                "success": False,
                "message": "GPS location is required.",
            }, status=400)

        try:
            latitude = float(latitude)
            longitude = float(longitude)
            accuracy = float(accuracy) if accuracy else None
        except (TypeError, ValueError):
            return JsonResponse({
                "success": False,
                "message": "Invalid GPS coordinates.",
            }, status=400)

        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            return JsonResponse({
                "success": False,
                "message": "GPS coordinates are out of range.",
            }, status=400)

        attendance = get_today_employee_attendance(request.user)

        if attendance.check_in:
            return JsonResponse({
                "success": False,
                "message": "You have already checked in today.",
            }, status=400)

        inside_school, distance = check_school_location(
            latitude,
            longitude,
        )

        if not inside_school:
            if distance is None:
                return JsonResponse({
                    "success": False,
                    "message": "School GPS location is not configured.",
                }, status=400)

            return JsonResponse({
                "success": False,
                "message": (
                    f"You are approximately {round(distance)} meters "
                    "away from school. Please check in from the school."
                ),
                "distance": round(distance),
            }, status=400)

        current_time = timezone.localtime().time()
        late_minutes = calculate_late_minutes(current_time)
        status = "Late" if late_minutes > 0 else "Present"

        attendance.check_in = current_time
        attendance.login_latitude = latitude
        attendance.login_longitude = longitude
        attendance.login_accuracy = accuracy

        # Convert GPS coordinates into a readable place name.
        attendance.login_location_name = get_location_name(
            latitude,
            longitude,
        )

        attendance.status = status
        attendance.late_minutes = late_minutes
        attendance.marked_by = request.user
        attendance.save()

        return JsonResponse({
            "success": True,
            "message": "Attendance checked in successfully.",
            "check_in": current_time.strftime("%I:%M %p"),
            "status": status,
            "late_minutes": late_minutes,
            "location_name": attendance.login_location_name,
        })

    except Exception:
        return JsonResponse({
            "success": False,
            "message": "Unable to check in. Please try again.",
        }, status=500)


@login_required
def employee_check_out(request):
    if get_role(request.user) not in EMPLOYEE_ROLES:
        return JsonResponse({
            "success": False,
            "message": "You are not authorized to check out as an employee.",
        }, status=403)
    if request.method != "POST":
        return JsonResponse({
            "success": False,
            "message": "Invalid request method.",
        }, status=405)

    try:
        if user_is_on_approved_leave(request.user, timezone.localdate()):
            return JsonResponse({
                "success": False,
                "message": "Approved leave is recorded for today; check-out is unavailable.",
            }, status=400)
        if is_holiday(timezone.localdate()):
            holiday = holiday_details(timezone.localdate())
            return JsonResponse({
                "success": False,
                "message": f"{holiday['name']} is a holiday. Check-out is unavailable.",
            }, status=400)

        latitude = request.POST.get("latitude")
        longitude = request.POST.get("longitude")
        accuracy = request.POST.get("accuracy")

        if not latitude or not longitude:
            return JsonResponse({
                "success": False,
                "message": "GPS location is required.",
            }, status=400)

        try:
            latitude = float(latitude)
            longitude = float(longitude)
            accuracy = float(accuracy) if accuracy else None
        except (TypeError, ValueError):
            return JsonResponse({
                "success": False,
                "message": "Invalid GPS coordinates.",
            }, status=400)

        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            return JsonResponse({
                "success": False,
                "message": "GPS coordinates are out of range.",
            }, status=400)

        attendance = get_today_employee_attendance(request.user)

        if not attendance.check_in:
            return JsonResponse({
                "success": False,
                "message": "Please check in before checking out.",
            }, status=400)

        if attendance.check_out:
            return JsonResponse({
                "success": False,
                "message": "You have already checked out today.",
            }, status=400)

        inside_school, distance = check_school_location(
            latitude,
            longitude,
        )

        if not inside_school:
            if distance is None:
                return JsonResponse({
                    "success": False,
                    "message": "School GPS location is not configured.",
                }, status=400)

            return JsonResponse({
                "success": False,
                "message": (
                    f"You are approximately {round(distance)} meters "
                    "away from school. Please check out from the school."
                ),
                "distance": round(distance),
            }, status=400)

        current_time = timezone.localtime().time()

        login_datetime = datetime.combine(
            timezone.localdate(),
            attendance.check_in,
        )
        logout_datetime = datetime.combine(
            timezone.localdate(),
            current_time,
        )

        working_minutes = max(
            0,
            int((logout_datetime - login_datetime).total_seconds() / 60),
        )

        full_day_minutes = getattr(
            settings,
            "ATTENDANCE_FULL_DAY_MINUTES",
            420,
        )
        half_day_minutes = getattr(
            settings,
            "ATTENDANCE_HALF_DAY_MINUTES",
            240,
        )

        if working_minutes >= full_day_minutes:
            attendance.status = (
                "Late" if attendance.late_minutes > 0 else "Present"
            )
        elif working_minutes >= half_day_minutes:
            attendance.status = "Half Day"
        else:
            attendance.status = "Absent"

        attendance.check_out = current_time
        attendance.logout_latitude = latitude
        attendance.logout_longitude = longitude
        attendance.logout_accuracy = accuracy

        # Convert GPS coordinates into a readable place name.
        attendance.logout_location_name = get_location_name(
            latitude,
            longitude,
        )

        attendance.working_minutes = working_minutes
        attendance.marked_by = request.user
        attendance.save()

        hours = working_minutes // 60
        minutes = working_minutes % 60

        return JsonResponse({
            "success": True,
            "message": "Attendance checked out successfully.",
            "check_out": current_time.strftime("%I:%M %p"),
            "working_minutes": working_minutes,
            "working_hours": f"{hours}h {minutes}m",
            "status": attendance.status,
            "location_name": attendance.logout_location_name,
        })

    except Exception:
        return JsonResponse({
            "success": False,
            "message": "Unable to check out. Please try again.",
        }, status=500)

@login_required
def attendance_dashboard(request):

    role = get_role(request.user)

    cards = []

    # -----------------------------------------------------
    # CHAIRMAN
    # -----------------------------------------------------

    if role == "chairman":

        cards = [
            {
                "title": "Student Attendance",
                "description": "View student attendance.",
                "url": "attendance:student_attendance_management",
                "icon": "fa-solid fa-users",
            },
            {
                "title": "Employee Attendance",
                "description": "View employee attendance.",
                "url": "attendance:employee_my_attendance",
                "icon": "fa-solid fa-user-tie",
            },
        ]

    # -----------------------------------------------------
    # PRINCIPAL
    # -----------------------------------------------------

    elif role == "principal":

        cards = [
            {
                "title": "My Attendance",
                "description": "View your attendance.",
                "url": "attendance:employee_my_attendance",
                "icon": "fa-solid fa-user-check",
            },
            {
                "title": "Student Attendance",
                "description": "View student attendance.",
                "url": "attendance:student_attendance_management",
                "icon": "fa-solid fa-users",
            },
            {
                "title": "Attendance Review",
                "description": "Review submitted attendance and correction requests.",
                "url": "attendance:attendance_review",
                "icon": "fa-solid fa-clipboard-check",
            },
            {
                "title": "Employee Attendance",
                "description": "View employee attendance.",
                "url": "attendance:employee_attendance",
                "icon": "fa-solid fa-user-tie",
            },
        ]

    # -----------------------------------------------------
    # VICE PRINCIPAL
    # -----------------------------------------------------

    elif role == "vice_principal":

        cards = [
            {
                "title": "My Attendance",
                "description": "View your attendance.",
                "url": "attendance:employee_my_attendance",
                "icon": "fa-solid fa-user-check",
            },
            {
                "title": "Student Attendance",
                "description": "View student attendance.",
                "url": "attendance:student_attendance_management",
                "icon": "fa-solid fa-users",
            },
            {
                "title": "Attendance Review",
                "description": "Review submitted attendance and correction requests.",
                "url": "attendance:attendance_review",
                "icon": "fa-solid fa-clipboard-check",
            },
            {
                "title": "Employee Attendance",
                "description": "View employee attendance.",
                "url": "attendance:employee_attendance",
                "icon": "fa-solid fa-user-tie",
            },
        ]

    # -----------------------------------------------------
    # TEACHER
    # -----------------------------------------------------

    elif role == "teacher":

        cards = [
            {
                "title": "My Attendance",
                "description": "View your attendance.",
                "url": "attendance:employee_my_attendance",
                "icon": "fa-solid fa-user-check",
            },
            {
                "title": "Student Attendance",
                "description": "View and mark student attendance.",
                "url": "attendance:teacher_attendance",
                "icon": "fa-solid fa-users",
            },
        ]

    # -----------------------------------------------------
    # ADMISSION STAFF
    # -----------------------------------------------------

    elif role == "admission_staff":

        cards = [
            {
                "title": "My Attendance",
                "description": "View your personal attendance.",
                "url": "attendance:employee_my_attendance",
                "icon": "fa-solid fa-user-check",
            },
        ]

    # -----------------------------------------------------
    # SYSTEM ADMINISTRATOR
    # -----------------------------------------------------

    elif role == "system_administrator":

        cards = [
            {
                "title": "My Attendance",
                "description": "View your personal attendance.",
                "url": "attendance:employee_my_attendance",
                "icon": "fa-solid fa-user-check",
            },
            
        ]

    # -----------------------------------------------------
    # ACCOUNTANT
    # -----------------------------------------------------

    elif role == "accountant":

        cards = [
            {
                "title": "My Attendance",
                "description": "View your personal attendance.",
                "url": "attendance:employee_my_attendance",
                "icon": "fa-solid fa-user-check",
            },
        ]

    # -----------------------------------------------------
    # STUDENT
    # -----------------------------------------------------

    elif role == "student":

        cards = [
            {
                "title": "My Attendance",
                "description": "View your attendance.",
                "url": "attendance:student_attendance",
                "icon": "fa-solid fa-calendar-check",
            },
        ]

    # -----------------------------------------------------
    # PARENT
    # -----------------------------------------------------

    elif role == "parent":

        cards = [
            {
                "title": "Child Attendance",
                "description": "View your child's attendance.",
                "url": "attendance:child_attendance",
                "icon": "fa-solid fa-child",
            },
        ]

    # -----------------------------------------------------
    # BUS DRIVER
    # -----------------------------------------------------

    elif role == "bus_driver":

        cards = [
            {
                "title": "My Attendance",
                "description": "View your attendance.",
                "url": "attendance:employee_my_attendance",
                "icon": "fa-solid fa-user-check",
            },
        ]

    return render(
        request,
        "attendance/attendance_dashboard.html",
        {
            "role": role,
            "cards": cards,
        },
    )

@login_required
def my_attendance(request):

    role = get_role(request.user)

    if role not in MY_ATTENDANCE_ROLES:

        return HttpResponseForbidden(
            "You are not allowed to access this page."
        )

    records = (
        EmployeeAttendance.objects
        .filter(
            employee=request.user
        )
        .order_by("-date")
    )

    summary = employee_attendance_summary(
        request.user,
        employee_start_date(request.user),
        timezone.localdate(),
    )

    return render(
        request,
        "attendance/my_attendance.html",
        {
            "records": records,
            "total": summary["eligible_working_days"],
            "present": summary["present_days"],
            "absent": summary["absent_days"],
            "late": summary["late_days"],
            "leave": summary["leave_days"],
            "half_days": summary["half_days"],
            "unsubmitted_days": summary["unsubmitted_days"],
            "percentage": summary["percentage"],
        },
    )


@login_required
def teacher_attendance(request):
    """
    Teacher attendance workflow:
    Draft -> Submitted -> Finalized.

    Parent notifications are created only after finalization.
    """

    if get_role(request.user) != "teacher":
        return HttpResponseForbidden(
            "Only teachers can mark student attendance."
        )

    # ---------------------------------------------------------
    # 1. Get classes from the teacher's active subject assignments
    # ---------------------------------------------------------
    assigned_subjects = (
        SubjectEmployeeAssignment.objects
        .filter(
            employee=request.user,
            is_active=True,
        )
        .select_related("subject", "class_section")
    )

    assigned_classes = (
        ClassSection.objects
        .filter(
            id__in=assigned_subjects.values_list(
                "class_section_id",
                flat=True,
            )
        )
        .distinct()
        .order_by("grade", "section")
    )

    # ---------------------------------------------------------
    # 2. Resolve selected class
    # ---------------------------------------------------------
    selected_class_id = request.GET.get("class_section")
    selected_class = None

    if selected_class_id:
        selected_class = assigned_classes.filter(
            pk=selected_class_id
        ).first()

    if selected_class is None:
        selected_class = assigned_classes.first()

    # ---------------------------------------------------------
    # 3. Get subjects assigned to this teacher for this class
    # ---------------------------------------------------------
    class_subjects = SubjectEmployeeAssignment.objects.none()

    if selected_class:
        class_subjects = (
            assigned_subjects
            .filter(class_section=selected_class)
            .select_related("subject", "class_section")
            .order_by("subject__subject_name")
        )

    selected_subject_id = request.GET.get("subject")
    selected_subject = None

    if selected_subject_id:
        selected_subject = class_subjects.filter(
            subject_id=selected_subject_id
        ).first()

    if selected_subject is None:
        selected_subject = class_subjects.first()

    # ---------------------------------------------------------
    # 4. Resolve date
    # ---------------------------------------------------------
    selected_date = timezone.localdate()
    date_string = request.GET.get("date")

    if date_string:
        try:
            selected_date = datetime.strptime(
                date_string,
                "%Y-%m-%d",
            ).date()
        except (ValueError, TypeError):
            messages.error(request, "Please select a valid date.")

    selected_holiday = holiday_details(selected_date, selected_class)

    # ---------------------------------------------------------
    # 5. Load active students and existing attendance
    # ---------------------------------------------------------
    students = StudentAdmissionApplication.objects.none()
    attendance_session = None
    attendance_records = {}

    if selected_class and selected_subject:
        students = (
            StudentAdmissionApplication.objects
            .filter(
                class_section=selected_class,
                status="account_created",
            )
            .order_by("first_name", "last_name")
        )

        attendance_session = AttendanceSession.objects.filter(
            class_section=selected_class,
            subject=selected_subject.subject,
            date=selected_date,
        ).first()

        records = StudentAttendance.objects.filter(
            class_section=selected_class,
            subject=selected_subject.subject,
            date=selected_date,
            student__in=students,
        ).select_related("student")

        attendance_records = {
            record.student_id: record
            for record in records
        }

        for student in students:
            student.approved_leave_today = student_is_on_approved_leave(
                student,
                selected_date,
            )
            student.attendance_record = attendance_records.get(
                student.id
            )

    # ---------------------------------------------------------
    # 6. Save Draft or Submit Attendance
    # ---------------------------------------------------------
    if request.method == "POST":
        post_class_id = request.POST.get("class_section")
        post_subject_id = request.POST.get("subject")
        post_date_string = request.POST.get("date")
        action = request.POST.get("action", "save_draft")

        if action not in {"save_draft", "submit"}:
            messages.error(request, "Invalid attendance action.")
            return redirect("attendance:teacher_attendance")

        # Validate date
        try:
            post_date = datetime.strptime(
                post_date_string,
                "%Y-%m-%d",
            ).date()
        except (ValueError, TypeError):
            messages.error(request, "Invalid attendance date.")
            return redirect("attendance:teacher_attendance")

        if post_date > timezone.localdate():
            messages.error(request, "Attendance cannot be marked for a future date.")
            return redirect("attendance:teacher_attendance")

        # Verify class is assigned to this teacher
        post_class = assigned_classes.filter(
            pk=post_class_id
        ).first()

        if not post_class:
            return HttpResponseForbidden(
                "You are not assigned to this class."
            )

        # Verify subject is assigned to this teacher for this class
        post_assignment = SubjectEmployeeAssignment.objects.filter(
            employee=request.user,
            class_section=post_class,
            subject_id=post_subject_id,
            is_active=True,
        ).select_related("subject").first()

        if not post_assignment:
            return HttpResponseForbidden(
                "You are not assigned to this subject."
            )

        holiday = holiday_details(post_date, post_class)
        if holiday:
            messages.error(
                request,
                f"{holiday['name']} is a holiday. Attendance cannot be marked.",
            )
            return redirect(
                f"/attendance/teacher/?class_section={post_class.pk}"
                f"&subject={post_assignment.subject_id}"
                f"&date={post_date:%Y-%m-%d}"
            )

        assigned_students = list(
            StudentAdmissionApplication.objects.filter(
                class_section=post_class,
                status="account_created",
            ).order_by("first_name", "last_name")
        )
        post_students = [
            student
            for student in assigned_students
            if not student_is_on_approved_leave(student, post_date)
        ]

        if not post_students:
            messages.error(
                request,
                "There are no eligible students for attendance on this date.",
            )
            return redirect("attendance:teacher_attendance")

        # Validate all students BEFORE saving when submitting.
        valid_statuses = {
            value for value, label in StudentAttendance.STATUS_CHOICES
        }
        invalid_statuses = []
        missing_students = []

        for student in post_students:
            status = request.POST.get(f"status_{student.id}")

            if status and status not in valid_statuses:
                invalid_statuses.append(student)
            elif status not in valid_statuses:
                missing_students.append(student)

        if invalid_statuses:
            messages.error(
                request,
                "One or more students have an invalid attendance status.",
            )
            return redirect(
                f"/attendance/teacher/?class_section={post_class.pk}"
                f"&subject={post_assignment.subject_id}"
                f"&date={post_date:%Y-%m-%d}"
            )

        if action == "submit" and missing_students:
            messages.error(
                request,
                (
                    f"Attendance is incomplete. Mark all "
                    f"{len(post_students)} students before submitting."
                ),
            )
            return redirect(
                f"/attendance/teacher/?class_section={post_class.pk}"
                f"&subject={post_assignment.subject_id}"
                f"&date={post_date:%Y-%m-%d}"
            )

        # A teacher may edit only a draft session.
        with transaction.atomic():
            attendance_session, created = (
                AttendanceSession.objects.get_or_create(
                    class_section=post_class,
                    subject=post_assignment.subject,
                    date=post_date,
                    defaults={
                        "status": "draft",
                        "created_by": request.user,
                    },
                )
            )

            # Lock the session row while processing the request.
            attendance_session = (
                AttendanceSession.objects
                .select_for_update()
                .get(pk=attendance_session.pk)
            )

            if attendance_session.status != "draft":
                messages.error(
                    request,
                    (
                        "This attendance session has already been "
                        "submitted. Use the correction process if changes "
                        "are required."
                    ),
                )
                return redirect(
                    f"/attendance/teacher/?class_section={post_class.pk}"
                    f"&subject={post_assignment.subject_id}"
                    f"&date={post_date:%Y-%m-%d}"
                )

            saved_count = 0

            for student in post_students:
                status = request.POST.get(f"status_{student.id}")

                existing_record = StudentAttendance.objects.filter(
                    student=student,
                    class_section=post_class,
                    subject=post_assignment.subject,
                    date=post_date,
                )

                if status in valid_statuses:
                    existing_record.update_or_create(
                        defaults={
                            "status": status,
                            "marked_by": request.user,
                            "remarks": "",
                        },
                        student=student,
                        class_section=post_class,
                        subject=post_assignment.subject,
                        date=post_date,
                    )
                    saved_count += 1

            if action == "submit":
                attendance_session.status = "submitted"
                attendance_session.submitted_at = timezone.now()
                attendance_session.save(
                    update_fields=["status", "submitted_at"]
                )

        if action == "save_draft":
            messages.success(
                request,
                (
                    f"Draft saved. {saved_count} student attendance "
                    "record(s) saved. You can continue later."
                ),
            )
        else:
            messages.success(
                request,
                (
                    "Attendance submitted successfully. "
                    "An authorized reviewer must finalize it."
                ),
            )

        return redirect(
            f"/attendance/teacher/?class_section={post_class.pk}"
            f"&subject={post_assignment.subject_id}"
            f"&date={post_date:%Y-%m-%d}"
        )

    # ---------------------------------------------------------
    # 7. Render teacher attendance page
    # ---------------------------------------------------------
    context = {
        "assigned_classes": assigned_classes,
        "assigned_subjects": class_subjects,
        "selected_class": selected_class,
        "selected_subject": selected_subject,
        "selected_date": selected_date,
        "selected_holiday": selected_holiday,
        "students": students,
        "eligible_student_count": sum(
            not getattr(student, "approved_leave_today", False)
            for student in students
        ),
        "approved_leave_count": sum(
            getattr(student, "approved_leave_today", False)
            for student in students
        ),
        "attendance_records": attendance_records,
        "attendance_session": attendance_session,
    }

    return render(
        request,
        "attendance/teacher_attendance.html",
        context,
    )


@login_required
def finalize_student_attendance(request, session_id):
    if request.method != "POST":
        return HttpResponseForbidden(
            "Attendance finalization requires a POST request."
        )

    role = get_role(request.user)

    if role not in {"principal", "vice_principal"}:
        return HttpResponseForbidden(
            "You are not authorized to finalize attendance."
        )

    with transaction.atomic():
        session = (
            AttendanceSession.objects
            .select_for_update()
            .select_related("class_section", "subject")
            .filter(pk=session_id)
            .first()
        )

        if not session:
            messages.error(request, "Attendance session not found.")
            return redirect("attendance:attendance_dashboard")

        if session.status != "submitted":
            messages.error(
                request,
                "Only submitted attendance can be finalized.",
            )
            return redirect("attendance:attendance_dashboard")

        students = StudentAdmissionApplication.objects.filter(
            class_section=session.class_section,
            status="account_created",
        )

        students = [
            student
            for student in students
            if not student_is_on_approved_leave(student, session.date)
        ]

        if not students:
            messages.error(
                request,
                "No active students were found for this class.",
            )
            return redirect("attendance:attendance_dashboard")

        records = list(
            StudentAttendance.objects.filter(
                class_section=session.class_section,
                subject=session.subject,
                date=session.date,
                student__in=students,
            ).select_related("student")
        )

        records_by_student = {
            record.student_id: record for record in records
        }

        # Every active student must have an attendance record.
        if any(student.pk not in records_by_student for student in students):
            messages.error(
                request,
                "Attendance is incomplete. It cannot be finalized.",
            )
            return redirect("attendance:attendance_dashboard")

        # Finalize first, within the same database transaction.
        session.status = "finalized"
        session.finalized_by = request.user
        session.finalized_at = timezone.now()
        session.save(
            update_fields=["status", "finalized_by", "finalized_at"]
        )

        # Notify parents only after finalization.
        for record in records:
            sync_parent_attendance_notifications(record)

    messages.success(
        request,
        "Attendance finalized successfully. Parent alerts were processed.",
    )
    return redirect("attendance:attendance_dashboard")


@login_required
def attendance_review(request):
    if get_role(request.user) not in {"principal", "vice_principal"}:
        return HttpResponseForbidden(
            "You are not authorized to review attendance."
        )

    sessions = AttendanceSession.objects.select_related(
        "class_section",
        "subject",
        "created_by",
        "finalized_by",
    ).order_by("-date", "class_section__grade", "subject__subject_name")

    selected_status = request.GET.get("status", "submitted")
    valid_session_statuses = {
        value for value, label in AttendanceSession.STATUS_CHOICES
    }
    if selected_status not in valid_session_statuses:
        selected_status = "submitted"
    sessions = sessions.filter(status=selected_status)

    class_id = request.GET.get("class_section", "")
    subject_id = request.GET.get("subject", "")
    date_string = request.GET.get("date", "")

    if class_id.isdigit():
        sessions = sessions.filter(class_section_id=int(class_id))
    if subject_id.isdigit():
        sessions = sessions.filter(subject_id=int(subject_id))
    if date_string:
        try:
            selected_date = datetime.strptime(date_string, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            messages.error(request, "Please select a valid attendance date.")
        else:
            sessions = sessions.filter(date=selected_date)

    session_rows = []
    for session in sessions[:100]:
        students = StudentAdmissionApplication.objects.filter(
            class_section=session.class_section,
            status="account_created",
        ).order_by("first_name", "last_name")
        records = StudentAttendance.objects.filter(
            class_section=session.class_section,
            subject=session.subject,
            date=session.date,
            student__in=students,
        ).select_related("student")
        session_rows.append({"session": session, "records": records})

    correction_requests = AttendanceCorrection.objects.filter(
        status="pending"
    ).select_related(
        "attendance__student",
        "attendance__class_section",
        "attendance__subject",
        "requested_by",
    ).order_by("requested_at")
    system_records = list(StudentAttendance.objects.filter(
        remarks__startswith=SYSTEM_ABSENCE_PREFIX,
    ).select_related(
        "student",
        "class_section",
        "subject",
    ).order_by("-date")[:100])
    session_states = {
        (session.class_section_id, session.subject_id, session.date): session.status
        for session in AttendanceSession.objects.filter(
            date__in={record.date for record in system_records},
            class_section_id__in={record.class_section_id for record in system_records},
            subject_id__in={record.subject_id for record in system_records},
        ).only("class_section_id", "subject_id", "date", "status")
    }
    system_unsubmitted_records = [
        record
        for record in system_records
        if session_states.get(
            (record.class_section_id, record.subject_id, record.date)
        ) not in {"submitted", "finalized"}
    ]

    return render(
        request,
        "attendance/attendance_review.html",
        {
            "session_rows": session_rows,
            "correction_requests": correction_requests,
            "system_unsubmitted_records": system_unsubmitted_records,
            "classes": ClassSection.objects.order_by("grade", "section"),
            "subjects": SubjectEmployeeAssignment.objects.select_related(
                "subject"
            ).values_list("subject_id", "subject__subject_name").distinct(),
            "selected_status": selected_status,
            "class_id": class_id,
            "subject_id": subject_id,
            "date_string": date_string,
            "statuses": AttendanceSession.STATUS_CHOICES,
        },
    )


@login_required
def request_attendance_correction(request, attendance_id):
    if request.method not in {"GET", "POST"}:
        return HttpResponseForbidden("Correction requests require GET or POST.")
    if get_role(request.user) != "teacher":
        return HttpResponseForbidden(
            "Only teachers can request attendance corrections."
        )

    record = StudentAttendance.objects.filter(pk=attendance_id).select_related(
        "class_section", "subject", "student"
    ).first()
    if not record:
        messages.error(request, "Attendance record not found.")
        return redirect("attendance:teacher_attendance")

    assigned = SubjectEmployeeAssignment.objects.filter(
        employee=request.user,
        class_section=record.class_section,
        subject=record.subject,
        is_active=True,
    ).exists()
    finalized = AttendanceSession.objects.filter(
        class_section=record.class_section,
        subject=record.subject,
        date=record.date,
        status="finalized",
    ).exists()
    if not assigned or not finalized:
        return HttpResponseForbidden(
            "You can request changes only for finalized attendance you are assigned to."
        )

    if request.method == "GET":
        return render(
            request,
            "attendance/attendance_correction_request.html",
            {
                "record": record,
                "status_choices": StudentAttendance.STATUS_CHOICES,
            },
        )

    new_status = request.POST.get("new_status")
    reason = request.POST.get("reason", "").strip()
    valid_statuses = {
        value for value, label in StudentAttendance.STATUS_CHOICES
    }
    if new_status not in valid_statuses or not reason:
        messages.error(
            request,
            "Choose a valid status and provide a correction reason.",
        )
        return redirect("attendance:request_attendance_correction", attendance_id=record.pk)
    if new_status == record.status:
        messages.error(request, "The proposed status must differ from the current status.")
        return redirect("attendance:request_attendance_correction", attendance_id=record.pk)
    if AttendanceCorrection.objects.filter(
        attendance=record,
        requested_by=request.user,
        status="pending",
    ).exists():
        messages.error(request, "A correction request is already pending for this record.")
        return redirect("attendance:request_attendance_correction", attendance_id=record.pk)

    AttendanceCorrection.objects.create(
        attendance=record,
        old_status=record.status,
        new_status=new_status,
        reason=reason,
        requested_by=request.user,
    )
    management_users = User.objects.filter(
        profile__role__in={"principal", "vice_principal"}
    )
    create_attendance_notifications(
        management_users,
        "Attendance correction requested",
        (
            f"{request.user.get_full_name() or request.user.username} requested "
            f"a correction for {record.student.first_name} "
            f"{record.student.last_name} on {record.date:%d %b %Y}."
        ),
        "/attendance/review/",
    )
    messages.success(request, "Correction request sent for management review.")
    return redirect("attendance:request_attendance_correction", attendance_id=record.pk)


@login_required
def review_attendance_correction(request, correction_id):
    if request.method != "POST":
        return HttpResponseForbidden("Correction review requires a POST request.")
    if get_role(request.user) not in {"principal", "vice_principal"}:
        return HttpResponseForbidden(
            "You are not authorized to review correction requests."
        )

    decision = request.POST.get("decision")
    if decision not in {"approved", "rejected"}:
        messages.error(request, "Invalid correction decision.")
        return redirect("attendance:attendance_review")

    with transaction.atomic():
        correction = (
            AttendanceCorrection.objects.select_for_update()
            .select_related("attendance", "requested_by")
            .filter(pk=correction_id)
            .first()
        )
        if correction is None or correction.status != "pending":
            messages.error(request, "This correction is no longer pending.")
            return redirect("attendance:attendance_review")
        if correction.requested_by_id == request.user.pk:
            return HttpResponseForbidden(
                "You cannot review your own correction request."
            )

        attendance = StudentAttendance.objects.select_for_update().get(
            pk=correction.attendance_id
        )
        session = AttendanceSession.objects.select_for_update().filter(
            class_section=attendance.class_section,
            subject=attendance.subject,
            date=attendance.date,
            status="finalized",
        ).first()
        if session is None:
            messages.error(
                request,
                "The finalized attendance session could not be found.",
            )
            return redirect("attendance:attendance_review")

        if decision == "approved":
            if attendance.status != correction.old_status:
                messages.error(
                    request,
                    "The attendance record changed after this request was made.",
                )
                return redirect("attendance:attendance_review")
            attendance.status = correction.new_status
            attendance.save(update_fields=["status", "updated_at"])
            sync_parent_attendance_notifications(attendance)

        correction.status = decision
        correction.reviewed_by = request.user
        correction.reviewed_at = timezone.now()
        correction.reviewer_remarks = request.POST.get(
            "reviewer_remarks", ""
        ).strip()
        correction.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
                "reviewer_remarks",
            ]
        )
        create_attendance_notifications(
            [correction.requested_by],
            f"Attendance correction {decision}",
            (
                f"Your correction request for "
                f"{attendance.student.first_name} "
                f"{attendance.student.last_name} on "
                f"{attendance.date:%d %b %Y} was {decision}."
            ),
            "/attendance/teacher/",
        )

    messages.success(request, f"Correction request {decision}.")
    return redirect("attendance:attendance_review")

@login_required
def student_attendance(request):

    # =========================================================
    # CHECK ROLE
    # =========================================================

    if get_role(request.user) != "student":

        return HttpResponseForbidden(
            "Only students can access this page."
        )

    # =========================================================
    # GET STUDENT
    # =========================================================

    student = (
        StudentAdmissionApplication.objects
        .filter(
            credential__user=request.user,
            credential__is_active=True,
            status="account_created",
        )
        .select_related(
            "class_section"
        )
        .first()
    )

    # =========================================================
    # STUDENT NOT FOUND
    # =========================================================

    if not student:

        return render(
            request,
            "attendance/student_attendance.html",
            {
                "student": None,
                "records": [],
                "subject_attendance": [],
                "total": 0,
                "present": 0,
                "absent": 0,
                "late": 0,
                "percentage": 0,
                "warning": False,
                "error": "Student record not found.",
            },
        )

    # =========================================================
    # ALL ATTENDANCE RECORDS
    # =========================================================

    records = (
        StudentAttendance.objects
        .filter(
            student=student
        )
        .select_related(
            "subject",
            "class_section",
        )
        .order_by(
            "-date",
            "subject__subject_name",
        )
    )

    # =========================================================
    # OVERALL ATTENDANCE
    # =========================================================

    overall_summary = student_attendance_summary(
        student,
        student_account_start_date(student),
        timezone.localdate(),
    )
    total = overall_summary["eligible_working_days"]
    present = overall_summary["present_days"]
    absent = overall_summary["absent_days"]
    late = overall_summary["late_days"]
    percentage = overall_summary["percentage"]

    # =========================================================
    # ATTENDANCE WARNING
    # =========================================================

    warning = (
        percentage is not None
        and percentage < 75
    )

    # =========================================================
    # SUBJECT-WISE ATTENDANCE
    # =========================================================

    subject_data = {}

    for record in records:

        subject_id = record.subject_id

        if subject_id not in subject_data:

            subject_data[subject_id] = {

                "subject": record.subject,

                "total": 0,

                "present": 0,

                "absent": 0,

                "late": 0,

                "percentage": 0,

            }

        # -----------------------------------------------------
        # TOTAL CLASSES
        # -----------------------------------------------------

        subject_data[subject_id]["total"] += 1

        # -----------------------------------------------------
        # STATUS
        # -----------------------------------------------------

        if record.status == "Present":

            subject_data[subject_id]["present"] += 1

        elif record.status == "Absent":

            subject_data[subject_id]["absent"] += 1

        elif record.status == "Late":

            subject_data[subject_id]["late"] += 1

    # =========================================================
    # CALCULATE SUBJECT PERCENTAGE
    # =========================================================

    subject_attendance = []

    for data in subject_data.values():
        subject_summary = student_attendance_summary(
            student,
            student_account_start_date(student),
            timezone.localdate(),
            subject_id=data["subject"].pk,
        )
        data["total"] = subject_summary["eligible_working_days"]
        data["present"] = subject_summary["present_days"]
        data["absent"] = subject_summary["absent_days"]
        data["late"] = subject_summary["late_days"]
        data["percentage"] = subject_summary["percentage"]

        # -----------------------------------------------------
        # LOW ATTENDANCE FLAG
        # -----------------------------------------------------

        data["warning"] = (
            data["percentage"] is not None
            and data["percentage"] < 75
        )

        subject_attendance.append(
            data
        )

    # =========================================================
    # SORT SUBJECTS
    # =========================================================

    subject_attendance.sort(
        key=lambda item:
            item["subject"].subject_name.lower()
    )

    # =========================================================
    # HISTORY FILTER
    # =========================================================

    selected_subject_id = request.GET.get(
        "subject"
    )

    selected_month = request.GET.get(
        "month"
    )

    start_string = request.GET.get("start_date", "").strip()
    end_string = request.GET.get("end_date", "").strip()
    report_start = student_account_start_date(student)
    report_end = timezone.localdate()

    if selected_month:
        try:
            month_start = datetime.strptime(
                f"{selected_month}-01",
                "%Y-%m-%d",
            ).date()
            month_end = (month_start.replace(day=28) + timedelta(days=4))
            report_start = month_start
            report_end = month_end.replace(day=1) - timedelta(days=1)
        except (ValueError, TypeError):
            selected_month = ""

    if start_string or end_string:
        try:
            report_start = datetime.strptime(start_string, "%Y-%m-%d").date()
            report_end = datetime.strptime(end_string, "%Y-%m-%d").date()
            selected_month = ""
        except (ValueError, TypeError):
            messages.error(request, "Enter both report dates in YYYY-MM-DD format.")
            report_start = student_account_start_date(student)
            report_end = timezone.localdate()

    history_records = records

    # ---------------------------------------------------------
    # SUBJECT FILTER
    # ---------------------------------------------------------

    if selected_subject_id:

        try:

            history_records = history_records.filter(
                subject_id=int(
                    selected_subject_id
                )
            )

        except (
            ValueError,
            TypeError,
        ):

            pass

    # ---------------------------------------------------------
    # MONTH FILTER
    #
    # Expected format:
    # 2026-10
    # ---------------------------------------------------------

    if selected_month:

        try:

            year, month = (
                selected_month.split("-")
            )

            history_records = history_records.filter(
                date__year=int(year),
                date__month=int(month),
            )

        except (
            ValueError,
            TypeError,
        ):

            pass

    if start_string and end_string and not selected_month:
        history_records = history_records.filter(
            date__range=(report_start, report_end)
        )

    # =========================================================
    # HISTORY COUNTS
    # =========================================================

    history_total = history_records.count()

    history_present = (
        history_records
        .filter(status="Present")
        .count()
    )

    history_absent = (
        history_records
        .filter(status="Absent")
        .count()
    )

    history_late = (
        history_records
        .filter(status="Late")
        .count()
    )
    history_summary = student_attendance_summary(
        student,
        report_start,
        report_end,
        subject_id=(
            int(selected_subject_id)
            if selected_subject_id and selected_subject_id.isdigit()
            else None
        ),
    )

    # =========================================================
    # SUBJECT LIST FOR FILTER
    # =========================================================

    student_subjects = (
        StudentAttendance.objects
        .filter(
            student=student
        )
        .values(
            "subject_id",
            "subject__subject_name",
        )
        .distinct()
        .order_by(
            "subject__subject_name"
        )
    )

    # =========================================================
    # CONTEXT
    # =========================================================

    context = {

        # Student
        "student":
            student,

        # Overall
        "records":
            records,

        "total":
            total,

        "present":
            present,

        "absent":
            absent,

        "late":
            late,

        "percentage":
            percentage,

        "warning":
            warning,

        "eligible_working_days":
            overall_summary["eligible_working_days"],

        "approved_leave_days":
            overall_summary["leave_days"],

        "unsubmitted_days":
            overall_summary["unsubmitted_days"],

        # Subject-wise
        "subject_attendance":
            subject_attendance,

        # Filtered history
        "history_records":
            history_records,

        "history_total":
            history_total,

        "history_present":
            history_present,

        "history_absent":
            history_absent,

        "history_late":
            history_late,

        # Filters
        "student_subjects":
            student_subjects,

        "selected_subject_id":
            selected_subject_id,

        "selected_month":
            selected_month,

        "report_start_date":
            start_string,

        "report_end_date":
            end_string,

        "history_summary":
            history_summary,

        "holiday_entries":
            holiday_report_entries(report_start, report_end, student.class_section),

        "current_holiday":
            holiday_details(timezone.localdate(), student.class_section),

    }

    # =========================================================
    # RENDER
    # =========================================================

    return render(
        request,
        "attendance/student_attendance.html",
        context,
    )

@login_required
def student_attendance_management(request):
    if get_role(request.user) not in MANAGEMENT_ROLES:
        return HttpResponseForbidden(
            "You are not allowed to access student attendance."
        )

    # Active class sections
    classes = (
        ClassSection.objects
        .filter(status__in=["Active", "Full"])
        .order_by("grade", "section")
    )

    # Selected date
    date_string = request.GET.get("date", "").strip()

    try:
        selected_date = datetime.strptime(
            date_string, "%Y-%m-%d"
        ).date()
    except (ValueError, TypeError):
        selected_date = timezone.localdate()

    range_start_string = request.GET.get("start_date", "").strip()
    range_end_string = request.GET.get("end_date", "").strip()
    selected_month = request.GET.get("month", "").strip()
    report_start = None
    report_end = selected_date
    if range_start_string and range_end_string:
        try:
            report_start = datetime.strptime(
                range_start_string, "%Y-%m-%d"
            ).date()
            report_end = datetime.strptime(
                range_end_string, "%Y-%m-%d"
            ).date()
        except (ValueError, TypeError):
            messages.error(request, "Enter a valid report date range.")
            range_start_string = ""
            range_end_string = ""
    elif selected_month:
        try:
            report_start = datetime.strptime(
                f"{selected_month}-01", "%Y-%m-%d"
            ).date()
            month_after = report_start.replace(day=28) + timedelta(days=4)
            report_end = month_after.replace(day=1) - timedelta(days=1)
        except (ValueError, TypeError):
            selected_month = ""

    # Selected class
    class_id = request.GET.get("class_id", "").strip()
    subject_id = request.GET.get("subject_id", "").strip()
    subjects = Subject.objects.order_by("subject_name")
    selected_class = None

    if class_id.isdigit():
        selected_class = classes.filter(
            id=int(class_id)
        ).first()

    # Selected student
    student_id = request.GET.get("student_id", "").strip()
    selected_student = None

    # Registered student accounts
    all_students = (
        StudentAdmissionApplication.objects
        .filter(status="account_created")
        .select_related("class_section")
        .order_by("first_name", "last_name")
    )

    if student_id.isdigit():
        selected_student = all_students.filter(
            id=int(student_id)
        ).first()

    # If a student is selected, use their class
    if selected_student:
        selected_class = selected_student.class_section
        class_id = str(selected_class.id) if selected_class else ""

    # Students in selected class
    if selected_class:
        students = all_students.filter(
            class_section=selected_class
        )
    else:
        students = all_students

    # Student dropdown options
    student_options = students

    # Attendance records for the selected date
    daily_records = (
        StudentAttendance.objects
        .filter(date=selected_date)
        .select_related(
            "student",
            "class_section",
            "subject",
            "marked_by",
        )
        .order_by("student__first_name", "student__last_name")
    )

    if selected_class:
        daily_records = daily_records.filter(
            class_section=selected_class
        )
    if subject_id.isdigit():
        daily_records = daily_records.filter(subject_id=int(subject_id))

    report_records = StudentAttendance.objects.all().select_related(
        "student", "class_section", "subject", "marked_by"
    )
    if report_start:
        report_records = report_records.filter(
            date__range=(report_start, report_end)
        )
    else:
        report_records = report_records.filter(date=selected_date)
    if selected_class:
        report_records = report_records.filter(class_section=selected_class)
    if subject_id.isdigit():
        report_records = report_records.filter(subject_id=int(subject_id))
    if selected_student:
        report_records = report_records.filter(student=selected_student)

    # Class-wise daily attendance summary
    class_summary = {
        "total_students": students.count() if selected_class else 0,
        "present": 0,
        "absent": 0,
        "leave": 0,
        "unsubmitted": 0,
        "marked_students": 0,
        "eligible_students": 0,
        "percentage": None,
    }

    if selected_class:
        selected_holiday = holiday_details(selected_date, selected_class)
        on_leave_student_ids = {
            student.pk
            for student in students
            if student_is_on_approved_leave(student, selected_date)
        }
        eligible_student_ids = {
            student.pk for student in students
        } - on_leave_student_ids
        scheduled_entries = TimetableEntry.objects.filter(
            class_section=selected_class,
            day=selected_date.strftime("%A"),
            is_active=True,
        )
        if subject_id.isdigit():
            scheduled_entries = scheduled_entries.filter(
                subject_id=int(subject_id)
            )
        if selected_holiday or not scheduled_entries.exists():
            eligible_student_ids.clear()
        class_summary["eligible_students"] = len(eligible_student_ids)
        class_summary["total_students"] = len(eligible_student_ids)
        class_summary["leave"] = len(on_leave_student_ids)
        # Aggregate subject-wise records into one status per student/day.
        student_day_statuses = {}
        session_statuses = {
            (session.subject_id): session.status
            for session in AttendanceSession.objects.filter(
                class_section=selected_class,
                date=selected_date,
            )
        }

        for record in daily_records:
            student_key = record.student_id
            statuses = student_day_statuses.setdefault(student_key, set())
            if (
                record.remarks
                and record.remarks.startswith(SYSTEM_ABSENCE_PREFIX)
                and session_statuses.get(record.subject_id)
                not in {"submitted", "finalized"}
            ):
                statuses.add("unsubmitted")
            else:
                statuses.add((record.status or "").strip().lower())

        daily_student_status = {}

        for student_key, statuses in student_day_statuses.items():
            if "leave" in statuses:
                final_status = "Leave"
            elif "present" in statuses or "late" in statuses:
                final_status = "Present"
            elif "absent" in statuses:
                final_status = "Absent"
            elif "half day" in statuses:
                final_status = "Half Day"
            elif "unsubmitted" in statuses:
                final_status = "Unsubmitted"
            else:
                continue

            if student_key in eligible_student_ids:
                daily_student_status[student_key] = final_status

        class_summary["marked_students"] = len(
            daily_student_status
        )

        class_summary["present"] = sum(
            status == "Present"
            for status in daily_student_status.values()
        )

        class_summary["absent"] = sum(
            status == "Absent"
            for status in daily_student_status.values()
        )

        class_summary["unsubmitted"] = sum(
            status == "Unsubmitted"
            for status in daily_student_status.values()
        )

        confirmed = class_summary["present"] + class_summary["absent"]

        if class_summary["eligible_students"]:
            class_summary["percentage"] = round(
                class_summary["present"] / class_summary["eligible_students"] * 100,
                2,
            )
        class_summary["unsubmitted"] += len(
            eligible_student_ids - set(daily_student_status)
        )

    # Individual student's complete attendance history
    records = StudentAttendance.objects.none()

    student_summary = {
        "present_days": 0,
        "absent_days": 0,
        "leave_days": 0,
        "working_days": 0,
        "percentage": None,
        "eligible_working_days": 0,
        "unsubmitted_days": 0,
    }

    if selected_student:
        individual_records = (
            StudentAttendance.objects
            .filter(student=selected_student)
            .select_related(
                "student",
                "class_section",
                "subject",
                "marked_by",
            )
            .order_by("-date", "subject__subject_name")
        )

        summary_start = report_start or student_account_start_date(selected_student)
        student_summary = student_attendance_summary(
            selected_student,
            summary_start,
            report_end if report_start else selected_date,
            subject_id=int(subject_id) if subject_id.isdigit() else None,
        )
        if subject_id.isdigit():
            individual_records = individual_records.filter(
                subject_id=int(subject_id)
            )
        records = (
            individual_records.filter(date__range=(report_start, report_end))
            if report_start
            else individual_records
        )

    else:
        records = report_records

    records = list(records)
    statuses_by_session = {
        (session.class_section_id, session.subject_id, session.date): session.status
        for session in AttendanceSession.objects.filter(
            date__in={record.date for record in records}
        ).only("class_section_id", "subject_id", "date", "status")
    }
    for record in records:
        record.system_generated = bool(
            record.remarks
            and record.remarks.startswith(SYSTEM_ABSENCE_PREFIX)
        )
        session_status = statuses_by_session.get(
            (record.class_section_id, record.subject_id, record.date)
        )
        record.system_generated_label = (
            "System-generated · Awaiting teacher submission"
            if record.system_generated
            and session_status not in {"submitted", "finalized"}
            else "System-generated"
            if record.system_generated
            else ""
        )

    return render(
        request,
        "attendance/student_attendance_management.html",
        {
            "classes": classes,
            "subjects": subjects,
            "students": students,
            "student_options": student_options,
            "selected_class": selected_class,
            "selected_class_id": class_id,
            "selected_student": selected_student,
            "selected_student_id": student_id,
            "selected_subject_id": subject_id,
            "selected_date": selected_date.isoformat(),
            "records": records,
            "class_summary": class_summary,
            "student_summary": student_summary,
            "selected_holiday": holiday_details(selected_date, selected_class),
            "report_start_date": range_start_string,
            "report_end_date": range_end_string,
            "selected_month": selected_month,
            "report_start": report_start,
            "report_end": report_end,
            "holiday_entries": holiday_report_entries(
                report_start or selected_date,
                report_end,
                selected_class,
            ),
        },
    )

@login_required
def employee_attendance(request):
    if get_role(request.user) not in EMPLOYEE_ATTENDANCE_VIEW_ROLES:
        return HttpResponseForbidden(
            "You are not allowed to view employee attendance."
        )

    # Validate selected date
    date_string = request.GET.get("date", "").strip()

    try:
        selected_date = datetime.strptime(
            date_string,
            "%Y-%m-%d",
        ).date()
    except (ValueError, TypeError):
        selected_date = timezone.localdate()

    range_start_string = request.GET.get("start_date", "").strip()
    range_end_string = request.GET.get("end_date", "").strip()
    selected_month = request.GET.get("month", "").strip()
    report_start = None
    report_end = selected_date
    if range_start_string and range_end_string:
        try:
            report_start = datetime.strptime(
                range_start_string, "%Y-%m-%d"
            ).date()
            report_end = datetime.strptime(
                range_end_string, "%Y-%m-%d"
            ).date()
        except (ValueError, TypeError):
            messages.error(request, "Enter a valid report date range.")
            range_start_string = ""
            range_end_string = ""
    elif selected_month:
        try:
            report_start = datetime.strptime(
                f"{selected_month}-01", "%Y-%m-%d"
            ).date()
            month_after = report_start.replace(day=28) + timedelta(days=4)
            report_end = month_after.replace(day=1) - timedelta(days=1)
        except (ValueError, TypeError):
            selected_month = ""

    # Get all employee accounts
    employees = (
        User.objects
        .filter(
            profile__role__in=EMPLOYEE_ROLES,
            profile__is_active=True,
            is_active=True,
        )
        .select_related("profile")
        .order_by("first_name", "last_name", "username")
    )

    # Get selected employee
    selected_employee_id = request.GET.get("employee", "").strip()
    selected_employee = None

    if selected_employee_id.isdigit():
        selected_employee = employees.filter(
            id=int(selected_employee_id)
        ).first()

    if selected_employee is None:
        selected_employee_id = ""

    # Attendance records for selected date
    records_query = EmployeeAttendance.objects.all()
    if report_start:
        records_query = records_query.filter(
            date__range=(report_start, report_end)
        )
    else:
        records_query = records_query.filter(date=selected_date)

    records = (
        records_query
        .select_related(
            "employee",
            "employee__profile",
            "marked_by",
        )
        .order_by(
            "employee__first_name",
            "employee__last_name",
        )
    )

    if selected_employee:
        records = records.filter(
            employee=selected_employee
        )
    system_generated_record_ids = set(
        records.filter(
            remarks__startswith=SYSTEM_ABSENCE_PREFIX
        ).values_list("pk", flat=True)
    )

    # Individual employee attendance summary cards
    attendance_summary = None

    if selected_employee:
        effective_start = (
            report_start
            if report_start
            else employee_start_date(selected_employee)
        )
        attendance_summary = employee_attendance_summary(
            selected_employee,
            effective_start,
            report_end,
        )

    # Render page
    return render(
        request,
        "attendance/employee_attendance.html",
        {
            "employees": employees,
            "records": records,
            "selected_date": selected_date.isoformat(),
            "selected_employee_id": selected_employee_id,
            "selected_employee": selected_employee,
            "attendance_summary": attendance_summary,
            "selected_holiday": holiday_details(selected_date),
            "report_start_date": range_start_string,
            "report_end_date": range_end_string,
            "selected_month": selected_month,
            "system_generated_record_ids": system_generated_record_ids,
            "holiday_entries": holiday_report_entries(
                report_start or selected_date,
                report_end,
            ),
            "view_only": True,
        },
    )

@login_required
def child_attendance(request):

    if get_role(request.user) != "parent":

        return HttpResponseForbidden(
            "Only parents can access child attendance."
        )

    links = (
        ParentStudent.objects
        .filter(
            parent=request.user,
            is_active=True,
        )
        .select_related(
            "student",
            "student__class_section",
        )
    )

    student_id = request.GET.get("student_id", "").strip()
    selected_link = None
    if student_id.isdigit():
        selected_link = links.filter(student_id=int(student_id)).first()
    if selected_link is None:
        selected_link = links.first()
    selected_student = selected_link.student if selected_link else None

    today = timezone.localdate()
    report_start = student_account_start_date(selected_student) if selected_student else today
    report_end = today
    range_start = request.GET.get("start_date", "").strip()
    range_end = request.GET.get("end_date", "").strip()
    selected_month = request.GET.get("month", "").strip()
    if range_start and range_end:
        try:
            report_start = datetime.strptime(range_start, "%Y-%m-%d").date()
            report_end = datetime.strptime(range_end, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            messages.error(request, "Enter a valid attendance date range.")
            range_start = ""
            range_end = ""
    elif selected_month:
        try:
            report_start = datetime.strptime(
                f"{selected_month}-01", "%Y-%m-%d"
            ).date()
            month_after = report_start.replace(day=28) + timedelta(days=4)
            report_end = month_after.replace(day=1) - timedelta(days=1)
        except (ValueError, TypeError):
            selected_month = ""

    records = []
    summary = None
    if selected_student:
        records_query = StudentAttendance.objects.filter(
            student=selected_student
        ).select_related("subject", "class_section")
        if range_start and range_end or selected_month:
            records_query = records_query.filter(
                date__range=(report_start, report_end)
            )
        candidate_records = list(records_query.order_by("-date"))
        session_states = {
            (session.class_section_id, session.subject_id, session.date): session.status
            for session in AttendanceSession.objects.filter(
                date__in={record.date for record in candidate_records},
                class_section_id__in={record.class_section_id for record in candidate_records},
                subject_id__in={record.subject_id for record in candidate_records},
            ).only("class_section_id", "subject_id", "date", "status")
        }
        records = [
            record
            for record in candidate_records
            if not (
                record.remarks
                and record.remarks.startswith(SYSTEM_ABSENCE_PREFIX)
                and session_states.get(
                    (record.class_section_id, record.subject_id, record.date)
                ) not in {"submitted", "finalized"}
            )
        ]
        summary = student_attendance_summary(
            selected_student,
            report_start,
            report_end,
        )

    return render(
        request,
        "attendance/child_attendance.html",
        {
            "links": links,
            "selected_student": selected_student,
            "records": records,
            "summary": summary,
            "total": summary["eligible_working_days"] if summary else 0,
            "present": summary["present_days"] if summary else 0,
            "absent": summary["absent_days"] if summary else 0,
            "late": summary["late_days"] if summary else 0,
            "percentage": summary["percentage"] if summary else None,
            "selected_student_id": str(selected_student.pk) if selected_student else "",
            "selected_holiday": holiday_details(today, selected_student.class_section if selected_student else None),
            "holiday_entries": holiday_report_entries(
                report_start,
                report_end,
                selected_student.class_section if selected_student else None,
            ),
            "report_start_date": range_start,
            "report_end_date": range_end,
            "selected_month": selected_month,
        },
    )