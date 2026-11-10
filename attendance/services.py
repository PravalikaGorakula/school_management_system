import logging
from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from academic_calendar.models import AcademicCalendarEvent
from admissions.models import (
    EmployeeCredential,
    StudentAdmissionApplication,
    StudentCredential,
)
from academics.models import SubjectEmployeeAssignment, TimetableEntry
from leave_management.models import LeaveRequest
from notifications.models import Notification

from .models import AttendanceSession, EmployeeAttendance, StudentAttendance


logger = logging.getLogger(__name__)
SYSTEM_ABSENCE_PREFIX = "System-generated absent:"
EMPLOYEE_ROLE_NAMES = {
    "chairman",
    "principal",
    "vice_principal",
    "teacher",
    "bus_driver",
    "system_administrator",
    "admission_staff",
    "accountant",
}
MANAGEMENT_ROLE_NAMES = {"principal", "vice_principal"}


def weekly_holiday_weekdays():
    configured = getattr(settings, "ATTENDANCE_WEEKLY_HOLIDAYS", (6,))
    return {
        weekday
        for weekday in configured
        if isinstance(weekday, int) and 0 <= weekday <= 6
    }


def declared_holidays_for_date(attendance_date, class_section=None):
    events = AcademicCalendarEvent.objects.filter(
        event_type="holiday",
        status="published",
        start_date__lte=attendance_date,
        end_date__gte=attendance_date,
    )
    if class_section is None:
        events = events.filter(class_section__isnull=True)
    else:
        events = events.filter(
            Q(class_section__isnull=True)
            | Q(class_section=class_section)
        )
    return events.order_by("title", "pk")


def holiday_details(attendance_date, class_section=None):
    event = declared_holidays_for_date(
        attendance_date,
        class_section=class_section,
    ).first()
    if event:
        return {
            "name": event.title,
            "status": "Holiday",
            "event": event,
            "kind": "academic_calendar",
        }

    if attendance_date.weekday() in weekly_holiday_weekdays():
        return {
            "name": attendance_date.strftime("%A"),
            "status": "Holiday",
            "event": None,
            "kind": "weekly",
        }
    return None


def is_holiday(attendance_date, class_section=None):
    return holiday_details(attendance_date, class_section) is not None


def approved_leave_requests(user, start_date, end_date):
    if user is None:
        return LeaveRequest.objects.none()
    return LeaveRequest.objects.filter(
        user=user,
        status="approved",
        from_date__lte=end_date,
        to_date__gte=start_date,
    )


def user_is_on_approved_leave(user, attendance_date):
    return approved_leave_requests(
        user,
        attendance_date,
        attendance_date,
    ).exists()


def approved_leave_dates(user, start_date, end_date):
    dates = set()
    for leave in approved_leave_requests(user, start_date, end_date):
        current = max(start_date, leave.from_date)
        final = min(end_date, leave.to_date)
        while current <= final:
            dates.add(current)
            current += timedelta(days=1)
    return dates


def student_is_on_approved_leave(student, attendance_date):
    credential = StudentCredential.objects.filter(
        student_application=student,
        is_active=True,
    ).select_related("user").first()
    return bool(
        credential
        and approved_leave_requests(
            credential.user,
            attendance_date,
            attendance_date,
        ).exists()
    )


def eligible_working_dates(start_date, end_date, class_section=None, leave_user=None):
    if end_date < start_date:
        return []

    leave_dates = approved_leave_dates(leave_user, start_date, end_date)
    dates = []
    current = start_date
    while current <= end_date:
        if (
            not is_holiday(current, class_section=class_section)
            and current not in leave_dates
        ):
            dates.append(current)
        current += timedelta(days=1)
    return dates


def holiday_report_entries(start_date, end_date, class_section=None):
    if end_date < start_date:
        return []
    entries = []
    final_date = min(end_date, timezone.localdate())
    for current in _date_range(start_date, final_date):
        details = holiday_details(current, class_section)
        if details:
            entries.append({"date": current, **details})
    return entries


def student_account_start_date(student):
    credential = StudentCredential.objects.filter(
        student_application=student,
        is_active=True,
    ).first()
    if credential:
        return timezone.localtime(credential.created_at).date()
    if student.submitted_at:
        return timezone.localtime(student.submitted_at).date()
    return date.min


def employee_start_date(user):
    joining_date = EmployeeCredential.objects.filter(
        user=user,
        is_active=True,
    ).values_list(
        "employee_application__joining_date",
        flat=True,
    ).first()
    if joining_date:
        return joining_date
    return timezone.localtime(user.date_joined).date()


def _clamped_range(start_date, end_date, first_eligible_date):
    today = timezone.localdate()
    start_date = max(start_date, first_eligible_date)
    end_date = min(end_date, today)
    return start_date, end_date


def _percent(credited_days, eligible_days):
    if not eligible_days:
        return None
    return round(credited_days / eligible_days * 100, 2)


def student_attendance_summary(student, start_date, end_date, subject_id=None):
    start_date, end_date = _clamped_range(
        start_date,
        end_date,
        student_account_start_date(student),
    )
    if end_date < start_date:
        return {
            "eligible_working_days": 0,
            "working_days": 0,
            "present_days": 0,
            "absent_days": 0,
            "late_days": 0,
            "leave_days": 0,
            "unsubmitted_days": 0,
            "pending_leave_requests": 0,
            "percentage": None,
        }

    credential = StudentCredential.objects.filter(
        student_application=student,
        is_active=True,
    ).select_related("user").first()
    leave_dates = approved_leave_dates(
        credential.user if credential else None,
        start_date,
        end_date,
    )
    pending_leave_requests = (
        LeaveRequest.objects.filter(
            user=credential.user,
            status="pending",
            from_date__lte=end_date,
            to_date__gte=start_date,
        ).count()
        if credential
        else 0
    )
    scheduled_weekdays = None
    if subject_id:
        scheduled_weekdays = set(
            TimetableEntry.objects.filter(
                class_section=student.class_section,
                subject_id=subject_id,
                is_active=True,
            ).values_list("day", flat=True)
        )
    all_working_dates = [
        current
        for current in _date_range(start_date, end_date)
        if (
            not is_holiday(current, student.class_section)
            and (
                scheduled_weekdays is None
                or current.strftime("%A") in scheduled_weekdays
            )
        )
    ]
    eligible_dates = [
        current for current in all_working_dates if current not in leave_dates
    ]

    records_query = StudentAttendance.objects.filter(
        student=student,
        date__range=(start_date, end_date),
    )
    if subject_id:
        records_query = records_query.filter(subject_id=subject_id)
    records = list(records_query.select_related("subject"))

    session_statuses = {
        (session.class_section_id, session.subject_id, session.date): session.status
        for session in AttendanceSession.objects.filter(
            date__range=(start_date, end_date),
        ).only("class_section_id", "subject_id", "date", "status")
    }
    records_by_date = {}
    unsubmitted_dates = set()
    for record in records:
        session_status = session_statuses.get(
            (record.class_section_id, record.subject_id, record.date)
        )
        if (
            record.remarks
            and record.remarks.startswith(SYSTEM_ABSENCE_PREFIX)
            and session_status not in {"submitted", "finalized"}
        ):
            unsubmitted_dates.add(record.date)
            continue
        records_by_date.setdefault(record.date, []).append(record.status)

    counts = {"present": 0, "absent": 0, "late": 0}
    for current in eligible_dates:
        statuses = records_by_date.get(current, [])
        if "Present" in statuses:
            counts["present"] += 1
        elif "Late" in statuses:
            counts["late"] += 1
        elif statuses and all(status == "Absent" for status in statuses):
            counts["absent"] += 1

    credited = counts["present"] + counts["late"]
    leave_workdays = len(set(all_working_dates) & leave_dates)
    unsubmitted = len(
        (unsubmitted_dates | (set(eligible_dates) - set(records_by_date)))
        & set(eligible_dates)
    )
    return {
        "eligible_working_days": len(eligible_dates),
        "working_days": len(eligible_dates),
        "present_days": counts["present"],
        "absent_days": counts["absent"],
        "late_days": counts["late"],
        "leave_days": leave_workdays,
        "unsubmitted_days": unsubmitted,
        "pending_leave_requests": pending_leave_requests,
        "percentage": _percent(credited, len(eligible_dates)),
    }


def employee_attendance_summary(user, start_date, end_date):
    start_date, end_date = _clamped_range(
        start_date,
        end_date,
        employee_start_date(user),
    )
    if end_date < start_date:
        return {
            "eligible_working_days": 0,
            "working_days": 0,
            "present_days": 0,
            "absent_days": 0,
            "late_days": 0,
            "half_days": 0,
            "leave_days": 0,
            "unsubmitted_days": 0,
            "pending_leave_requests": 0,
            "percentage": None,
        }

    leave_dates = approved_leave_dates(user, start_date, end_date)
    pending_leave_requests = LeaveRequest.objects.filter(
        user=user,
        status="pending",
        from_date__lte=end_date,
        to_date__gte=start_date,
    ).count()
    all_working_dates = [
        current
        for current in _date_range(start_date, end_date)
        if not is_holiday(current)
    ]
    records = {
        record.date: record
        for record in EmployeeAttendance.objects.filter(
            employee=user,
            date__range=(start_date, end_date),
        )
    }
    counts = {
        "present": 0,
        "absent": 0,
        "late": 0,
        "half": 0,
        "leave": 0,
        "unsubmitted": 0,
    }
    eligible_dates = []
    for current in all_working_dates:
        record = records.get(current)
        if current in leave_dates or (record and record.status == "Leave"):
            counts["leave"] += 1
            continue
        eligible_dates.append(current)
        if record is None:
            counts["unsubmitted"] += 1
        elif record.status == "Present":
            counts["present"] += 1
        elif record.status == "Late":
            counts["late"] += 1
        elif record.status == "Half Day":
            counts["half"] += 1
        elif record.status == "Absent":
            counts["absent"] += 1

    credited = counts["present"] + counts["late"] + counts["half"] * 0.5
    eligible_count = len(eligible_dates)
    return {
        "eligible_working_days": eligible_count,
        "working_days": eligible_count,
        "present_days": counts["present"],
        "absent_days": counts["absent"],
        "late_days": counts["late"],
        "half_days": counts["half"],
        "leave_days": counts["leave"],
        "unsubmitted_days": counts["unsubmitted"],
        "pending_leave_requests": pending_leave_requests,
        "percentage": _percent(credited, eligible_count),
    }


def _date_range(start_date, end_date):
    current = start_date
    while current <= end_date:
        yield current
        current += timedelta(days=1)


def _create_conflict_notification(title, message):
    recipients = User.objects.filter(
        profile__role__in=MANAGEMENT_ROLE_NAMES,
        profile__is_active=True,
    )
    for recipient in recipients:
        Notification.objects.get_or_create(
            recipient=recipient,
            title=title,
            message=message,
            notification_type="attendance",
            related_url="/attendance/review/",
        )


def _flag_finalized_holiday_conflicts(
    attendance_date,
    holiday_name,
    class_section=None,
    event_marker="",
):
    sessions = AttendanceSession.objects.filter(
        date=attendance_date,
        status="finalized",
    ).select_related("class_section", "subject")
    if class_section is not None:
        sessions = sessions.filter(class_section=class_section)

    flagged = 0
    for session in sessions:
        _create_conflict_notification(
            "Published holiday conflicts with finalized attendance",
            (
                f"{event_marker} {holiday_name} is declared as a holiday on {attendance_date}. "
                f"Finalized attendance exists for {session.class_section}, "
                f"{session.subject}. Review session #{session.pk}."
            ),
        )
        flagged += 1
    return flagged


def flag_holiday_conflicts(event):
    event_marker = f"Academic calendar event #{event.pk}"
    Notification.objects.filter(
        title="Published holiday conflicts with finalized attendance",
        message__contains=event_marker,
    ).delete()
    if event.event_type != "holiday" or event.status != "published":
        return 0
    total = 0
    for attendance_date in _date_range(event.start_date, event.end_date):
        total += _flag_finalized_holiday_conflicts(
            attendance_date,
            event.title,
            class_section=event.class_section,
            event_marker=event_marker,
        )
    return total


def _student_joined_on(student):
    return student_account_start_date(student)


def flag_approved_leave_attendance_conflicts(user, start_date, end_date):
    flagged = 0
    student_credential = StudentCredential.objects.filter(
        user=user,
        is_active=True,
    ).select_related("student_application").first()
    if student_credential:
        records = StudentAttendance.objects.filter(
            student=student_credential.student_application,
            date__range=(start_date, end_date),
        ).select_related("class_section", "subject", "student")
        for record in records:
            if AttendanceSession.objects.filter(
                class_section=record.class_section,
                subject=record.subject,
                date=record.date,
                status="finalized",
            ).exists():
                _create_conflict_notification(
                    "Approved leave conflicts with finalized attendance",
                    (
                        f"Approved leave for {record.student.application_id} "
                        f"overlaps finalized attendance on {record.date}. "
                        f"Review {record.class_section}, {record.subject}."
                    ),
                )
                flagged += 1

    if EmployeeCredential.objects.filter(user=user, is_active=True).exists():
        records = EmployeeAttendance.objects.filter(
            employee=user,
            date__range=(start_date, end_date),
        ).exclude(status="Leave")
        for record in records:
            _create_conflict_notification(
                "Approved leave conflicts with recorded employee attendance",
                (
                    f"Approved leave for {user.get_full_name() or user.username} "
                    f"overlaps recorded attendance on {record.date}."
                ),
            )
            flagged += 1
    return flagged


def _employee_on_leave(user, attendance_date):
    return approved_leave_requests(user, attendance_date, attendance_date).exists()


def process_daily_attendance(attendance_date):
    if attendance_date > timezone.localdate():
        raise ValueError("Attendance cannot be processed for a future date.")

    result = {
        "attendance_date": attendance_date,
        "employees_processed": 0,
        "employees_on_leave": 0,
        "students_processed": 0,
        "students_on_leave": 0,
        "skipped_holidays": 0,
        "skipped_unscheduled_assignments": 0,
        "unsubmitted_class_sessions": 0,
        "conflicts": 0,
        "errors": 0,
    }

    global_holiday = holiday_details(attendance_date)
    if global_holiday:
        result["skipped_holidays"] += 1
        result["conflicts"] += _flag_finalized_holiday_conflicts(
            attendance_date,
            global_holiday["name"],
            event_marker=(
                f"Academic calendar event #{global_holiday['event'].pk}"
                if global_holiday["event"]
                else ""
            ),
        )
        logger.info(
            "Skipping attendance for %s (%s).",
            attendance_date,
            global_holiday["name"],
        )
        return result

    employee_users = User.objects.filter(
        profile__role__in=EMPLOYEE_ROLE_NAMES,
        profile__is_active=True,
        is_active=True,
    ).select_related("profile")

    for employee in employee_users:
        if attendance_date < employee_start_date(employee):
            continue
        try:
            with transaction.atomic():
                record = EmployeeAttendance.objects.select_for_update().filter(
                    employee=employee,
                    date=attendance_date,
                ).first()
                on_leave = _employee_on_leave(employee, attendance_date)
                if on_leave:
                    result["employees_on_leave"] += 1
                    if record is None:
                        EmployeeAttendance.objects.create(
                            employee=employee,
                            date=attendance_date,
                            status="Leave",
                            remarks="Approved leave.",
                        )
                    elif (
                        record.status == "Absent"
                        and record.remarks
                        and record.remarks.startswith(SYSTEM_ABSENCE_PREFIX)
                    ):
                        record.status = "Leave"
                        record.remarks = "Approved leave."
                        record.save(update_fields=["status", "remarks", "updated_at"])
                    continue
                if record is None:
                    EmployeeAttendance.objects.create(
                        employee=employee,
                        date=attendance_date,
                        status="Absent",
                        remarks=(
                            f"{SYSTEM_ABSENCE_PREFIX} unmarked at daily processing."
                        ),
                    )
                    result["employees_processed"] += 1
        except IntegrityError:
            logger.info(
                "Employee attendance already exists for user=%s date=%s.",
                employee.pk,
                attendance_date,
            )
        except Exception:
            result["errors"] += 1
            logger.exception(
                "Failed employee attendance processing user=%s date=%s.",
                employee.pk,
                attendance_date,
            )

    scheduled_assignments = set(
        TimetableEntry.objects.filter(
            day=attendance_date.strftime("%A"),
            is_active=True,
        ).values_list(
            "class_section_id",
            "subject_id",
            "employee_id",
            "academic_year",
        )
    )
    assignments = SubjectEmployeeAssignment.objects.filter(
        is_active=True,
        employee__is_active=True,
        class_section__status__in=["Active", "Full"],
    ).select_related("class_section", "subject")
    for assignment in assignments:
        if (
            assignment.class_section_id,
            assignment.subject_id,
            assignment.employee_id,
            assignment.academic_year,
        ) not in scheduled_assignments:
            result["skipped_unscheduled_assignments"] += 1
            continue
        assignment_holiday = holiday_details(
            attendance_date,
            assignment.class_section,
        )
        if assignment_holiday:
            result["skipped_holidays"] += 1
            result["conflicts"] += _flag_finalized_holiday_conflicts(
                attendance_date,
                assignment_holiday["name"],
                class_section=assignment.class_section,
                event_marker=(
                    f"Academic calendar event #{assignment_holiday['event'].pk}"
                    if assignment_holiday["event"]
                    else ""
                ),
            )
            continue

        session = AttendanceSession.objects.filter(
            class_section=assignment.class_section,
            subject=assignment.subject,
            date=attendance_date,
        ).first()
        students = StudentAdmissionApplication.objects.filter(
            class_section=assignment.class_section,
            status="account_created",
        )
        missing_from_teacher = False
        for student in students:
            if attendance_date < _student_joined_on(student):
                continue
            credential = StudentCredential.objects.filter(
                student_application=student,
                is_active=True,
            ).select_related("user").first()
            leave_user = credential.user if credential else None
            on_leave = _employee_on_leave(leave_user, attendance_date)
            try:
                with transaction.atomic():
                    record = StudentAttendance.objects.select_for_update().filter(
                        student=student,
                        class_section=assignment.class_section,
                        subject=assignment.subject,
                        date=attendance_date,
                    ).first()
                    if on_leave:
                        result["students_on_leave"] += 1
                        if (
                            session
                            and session.status == "finalized"
                            and record
                        ):
                            _create_conflict_notification(
                                "Approved leave conflicts with finalized attendance",
                                (
                                    f"Approved leave for {student.application_id} "
                                    f"overlaps finalized attendance on {attendance_date}."
                                ),
                            )
                            result["conflicts"] += 1
                        continue
                    if record is not None:
                        continue
                    if session and session.status in {"submitted", "finalized"}:
                        missing_from_teacher = True
                        continue
                    StudentAttendance.objects.create(
                        student=student,
                        class_section=assignment.class_section,
                        subject=assignment.subject,
                        date=attendance_date,
                        status="Absent",
                        remarks=(
                            f"{SYSTEM_ABSENCE_PREFIX} teacher session not submitted."
                        ),
                    )
                    result["students_processed"] += 1
                    missing_from_teacher = True
            except IntegrityError:
                logger.info(
                    "Student attendance already exists student=%s subject=%s date=%s.",
                    student.pk,
                    assignment.subject_id,
                    attendance_date,
                )
            except Exception:
                result["errors"] += 1
                logger.exception(
                    "Failed student attendance processing student=%s date=%s.",
                    student.pk,
                    attendance_date,
                )

        if missing_from_teacher:
            result["unsubmitted_class_sessions"] += 1
            _create_conflict_notification(
                "Teacher attendance not submitted",
                (
                    f"Teacher attendance was not submitted for "
                    f"{assignment.class_section}, {assignment.subject} "
                    f"on {attendance_date}. System-generated absences are "
                    "unconfirmed and require review."
                ),
            )
            logger.warning(
                "Teacher attendance not submitted: class=%s subject=%s date=%s.",
                assignment.class_section_id,
                assignment.subject_id,
                attendance_date,
            )

    logger.info("Daily attendance processing result: %s", result)
    return result