from datetime import date

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import (
    Bus,
    BusTrip,
    StudentBusAssignment,
    BusLocation,
    BusExpense,
    BusIssue,
    SafetyAlert,
    BusRoute,
    BusStop,
)
from .forms import BusForm
from admissions.models import StudentAdmissionApplication


# =========================================================
# ROLE HELPERS
# =========================================================

def get_user_role(user):

    if not user.is_authenticated:
        return None

    try:
        return str(user.profile.role).lower()
    except Exception:
        return None


def is_vice_principal(user):
    return get_user_role(user) == "vice_principal"


def is_bus_driver(user):
    return get_user_role(user) == "bus_driver"


def is_accountant(user):
    return get_user_role(user) == "accountant"


# =========================================================
# AUTHORIZATION HELPERS
# =========================================================

def vice_principal_required(request):

    if not is_vice_principal(request.user):
        return HttpResponseForbidden(
            "You are not authorized to access this page."
        )

    return None


def accountant_required(request):

    if not is_accountant(request.user):
        return HttpResponseForbidden(
            "You are not authorized to access bus expenses."
        )

    return None


# =========================================================
# DRIVER DECORATOR
# =========================================================

def driver_required(view_func):

    def wrapper(request, *args, **kwargs):

        if not is_bus_driver(request.user):
            return HttpResponseForbidden(
                "You are not authorized to access the bus driver portal."
            )

        return view_func(request, *args, **kwargs)

    wrapper.__name__ = view_func.__name__
    wrapper.__doc__ = view_func.__doc__

    return wrapper


# =========================================================
# GET BUS ASSIGNED TO DRIVER
# =========================================================

def get_driver_bus(user):

    buses = (
        Bus.objects
        .select_related(
            "route",
            "driver",
        )
        .filter(
            is_active=True,
        )
    )

    for bus in buses:

        driver = bus.driver

        if not driver:
            continue

        # -------------------------------------------------
        # Direct user relation
        # -------------------------------------------------

        for field_name in [
            "user",
            "created_by",
            "account",
        ]:

            if hasattr(driver, field_name):

                related_user = getattr(
                    driver,
                    field_name,
                    None,
                )

                if related_user == user:
                    return bus

        # -------------------------------------------------
        # Employee credentials
        # -------------------------------------------------

        try:

            credentials = driver.employee_credentials.all()

            for credential in credentials:

                if getattr(
                    credential,
                    "user",
                    None
                ) == user:

                    return bus

        except Exception:
            pass

        # -------------------------------------------------
        # Single employee credential
        # -------------------------------------------------

        try:

            credential = driver.employeecredential

            if getattr(
                credential,
                "user",
                None
            ) == user:

                return bus

        except Exception:
            pass

    return None


# =========================================================
# DRIVER - MY BUS
# =========================================================

@login_required
@driver_required
def driver_my_bus(request):

    bus = get_driver_bus(request.user)

    if not bus:

        return render(
            request,
            "transport/driver/my_bus.html",
            {
                "bus": None,
                "route": None,
                "stops": [],
            },
        )

    stops = (
        bus.route.stops
        .filter(
            is_active=True,
        )
        if bus.route
        else []
    )

    return render(
        request,
        "transport/driver/my_bus.html",
        {
            "bus": bus,
            "route": bus.route,
            "stops": stops,
        },
    )


# =========================================================
# DRIVER - MY STUDENTS
# =========================================================

@login_required
@driver_required
def driver_students(request):

    bus = get_driver_bus(request.user)

    assignments = (
        StudentBusAssignment.objects
        .select_related(
            "student",
            "bus",
            "route",
            "pickup_stop",
            "drop_stop",
        )
        .filter(
            bus=bus,
            is_active=True,
        )
        if bus
        else StudentBusAssignment.objects.none()
    )

    return render(
        request,
        "transport/driver/students.html",
        {
            "bus": bus,
            "assignments": assignments,
        },
    )


# =========================================================
# DRIVER - MY BUS LOCATION
# =========================================================

@login_required
@driver_required
def driver_bus_location(request):

    bus = get_driver_bus(request.user)

    locations = (
        bus.location_history
        .all()[:50]
        if bus
        else []
    )

    return render(
        request,
        "transport/driver/bus_location.html",
        {
            "bus": bus,
            "locations": locations,
        },
    )


# =========================================================
# DRIVER - MY TRIP HISTORY
# =========================================================

@login_required
@driver_required
def driver_trip_history(request):

    bus = get_driver_bus(request.user)

    trips = (
        BusTrip.objects
        .select_related(
            "bus",
            "route",
            "driver",
            "current_stop",
        )
        .filter(
            bus=bus,
        )
        .order_by(
            "-trip_date",
            "-scheduled_start_time",
        )
        if bus
        else []
    )

    return render(
        request,
        "transport/driver/trip_history.html",
        {
            "bus": bus,
            "trips": trips,
        },
    )


# =========================================================
# DRIVER - MY SAFETY & ALERTS
# =========================================================

@login_required
@driver_required
def driver_safety_alerts(request):

    bus = get_driver_bus(request.user)

    alerts = (
        SafetyAlert.objects
        .filter(
            bus=bus,
        )
        .select_related(
            "trip",
            "acknowledged_by",
        )
        .order_by(
            "-created_at",
        )
        if bus
        else []
    )

    return render(
        request,
        "transport/driver/safety_alerts.html",
        {
            "bus": bus,
            "alerts": alerts,
        },
    )


# =========================================================
# DRIVER - REPORT BUS ISSUE
# =========================================================

@login_required
@driver_required
def driver_report_issue(request):

    bus = get_driver_bus(request.user)

    if not bus:

        return render(
            request,
            "transport/driver/report_issue.html",
            {
                "bus": None,
                "issues": [],
            },
        )

    if request.method == "POST":

        BusIssue.objects.create(
            bus=bus,
            reported_by=request.user,
            issue_type=request.POST.get(
                "issue_type"
            ),
            priority=request.POST.get(
                "priority"
            ),
            title=request.POST.get(
                "title"
            ),
            description=request.POST.get(
                "description"
            ),
            photo=request.FILES.get(
                "photo"
            ),
        )

        messages.success(
            request,
            "Bus issue reported successfully."
        )

        return redirect(
            "transport:driver_report_issue"
        )

    issues = (
        BusIssue.objects
        .filter(
            bus=bus,
            reported_by=request.user,
        )
        .order_by(
            "-created_at"
        )
    )

    return render(
        request,
        "transport/driver/report_issue.html",
        {
            "bus": bus,
            "issues": issues,
        },
    )


# =========================================================
# DRIVER - EMERGENCY
# =========================================================

@login_required
@driver_required
def driver_emergency(request):

    bus = get_driver_bus(request.user)

    if not bus:

        return render(
            request,
            "transport/driver/emergency.html",
            {
                "bus": None,
            },
        )

    if request.method == "POST":

        emergency_message = (
            request.POST.get(
                "message",
                "Emergency reported by bus driver.",
            )
            .strip()
        )

        SafetyAlert.objects.create(
            bus=bus,
            alert_type="emergency",
            severity="critical",
            title="Driver Emergency Alert",
            message=(
                emergency_message
                or "Emergency reported by bus driver."
            ),
            latitude=bus.current_latitude,
            longitude=bus.current_longitude,
            status="new",
        )

        messages.success(
            request,
            "Emergency alert has been sent successfully."
        )

        return redirect(
            "transport:driver_emergency"
        )

    return render(
        request,
        "transport/driver/emergency.html",
        {
            "bus": bus,
        },
    )

# =========================================================
# STUDENT AND PARENT HELPERS
# =========================================================

def is_student_or_parent(user):
    return (
        user.is_authenticated
        and get_user_role(user) in ["student", "parent"]
    )


def get_logged_in_student(user):
    """
    Return the student admission record linked to a student login.
    """
    if get_user_role(user) != "student":
        return None

    return (
        StudentAdmissionApplication.objects
        .filter(
            credential__user=user,
            credential__is_active=True,
            status="account_created",
        )
        .select_related("class_section")
        .first()
    )


def get_parent_linked_students(user):
    """
    Return students linked to this parent.

    IMPORTANT:
    Ee function ParentStudent model relation details telisina
    tarvata implement cheyyali. ParentStudent fields guess
    cheyakunda empty queryset return chestunnam.
    """
    if get_user_role(user) != "parent":
        return StudentAdmissionApplication.objects.none()

    return StudentAdmissionApplication.objects.none()


def get_live_bus_student(user, student_id=None):
    """
    Student login: own bus assignment.
    Parent login: only a linked child's bus assignment.
    """

    role = get_user_role(user)

    if role == "student":
        student = get_logged_in_student(user)

        if student_id and (
            not student or str(student.pk) != str(student_id)
        ):
            return None

        return student

    if role == "parent":
        if not student_id:
            return None

        return get_parent_linked_students(user).filter(
            pk=student_id
        ).first()

    return None


def get_student_bus_assignment_for_user(user, student_id=None):
    student = get_live_bus_student(
        user,
        student_id=student_id,
    )

    if not student:
        return None

    return (
        StudentBusAssignment.objects
        .filter(
            student=student,
            is_active=True,
            bus__is_active=True,
        )
        .select_related(
            "student",
            "bus",
            "route",
            "pickup_stop",
            "drop_stop",
        )
        .first()
    )

# =========================================================
# STUDENT / PARENT - LIVE BUS
# =========================================================

@login_required
def student_live_bus(request):

    role = get_user_role(request.user)

    if role not in ["student", "parent"]:
        return HttpResponseForbidden(
            "Only students and parents can access Live Bus."
        )

    student_id = request.GET.get("student_id")

    assignment = get_student_bus_assignment_for_user(
        request.user,
        student_id=student_id,
    )

    if not assignment:
        return render(
            request,
            "transport/student/live_bus.html",
            {
                "assignment": None,
                "student": get_logged_in_student(request.user),
                "bus": None,
                "route": None,
                "stops": [],
                "alerts": [],
                "trip": None,
                "locations": [],
                "error_message": (
                    "No bus assignment was found, or you do not "
                    "have permission to view this student's bus."
                ),
            },
        )

    student = assignment.student
    bus = assignment.bus
    route = assignment.route

    stops = BusStop.objects.filter(
        route=route,
        is_active=True,
    ).order_by("stop_order")

    today = timezone.localdate()

    trip = (
        BusTrip.objects
        .filter(
            bus=bus,
            trip_date=today,
            status__in=["scheduled", "started"],
        )
        .select_related(
            "route",
            "current_stop",
            "driver",
        )
        .order_by("scheduled_start_time")
        .first()
    )

    locations = (
        BusLocation.objects
        .filter(bus=bus)
        .order_by("-gps_timestamp", "-received_at")[:20]
    )

    alerts = (
        SafetyAlert.objects
        .filter(bus=bus)
        .select_related("trip", "acknowledged_by")
        .order_by("-created_at")[:10]
    )

    current_stop = trip.current_stop if trip else None
    next_stop = None

    if current_stop:
        next_stop = stops.filter(
            stop_order__gt=current_stop.stop_order
        ).first()

    student_stop = (
        assignment.pickup_stop
        if assignment.pickup_required
        else assignment.drop_stop
    )

    return render(
        request,
        "transport/student/live_bus.html",
        {
            "assignment": assignment,
            "student": student,
            "bus": bus,
            "route": route,
            "stops": stops,
            "alerts": alerts,
            "trip": trip,
            "locations": locations,
            "current_stop": current_stop,
            "next_stop": next_stop,
            "student_stop": student_stop,
            "error_message": None,
            "is_parent_view": role == "parent",
        },
    )

# =========================================================
# STUDENT / PARENT - LIVE BUS DATA API
# =========================================================

@login_required
def student_live_bus_data(request):

    role = get_user_role(request.user)

    # Only student and parent can access
    if role not in ["student", "parent"]:
        return JsonResponse(
            {
                "success": False,
                "message": "Unauthorized access.",
            },
            status=403,
        )

    student_id = request.GET.get("student_id")

    # Get authorized student's bus assignment
    assignment = get_student_bus_assignment_for_user(
        request.user,
        student_id=student_id,
    )

    if not assignment:
        return JsonResponse(
            {
                "success": False,
                "message": (
                    "No bus assignment found, or you are not "
                    "authorized to view this student's bus."
                ),
            },
            status=404,
        )

    bus = assignment.bus

    # Latest GPS location
    latest_location = (
        BusLocation.objects
        .filter(bus=bus)
        .order_by("-gps_timestamp", "-received_at")
        .first()
    )

    today = timezone.localdate()

    # Today's active trip
    trip = (
        BusTrip.objects
        .filter(
            bus=bus,
            trip_date=today,
            status__in=["scheduled", "started"],
        )
        .select_related("current_stop")
        .order_by("scheduled_start_time")
        .first()
    )

    current_stop = trip.current_stop if trip else None
    next_stop = None

    if current_stop and assignment.route:
        next_stop = (
            BusStop.objects
            .filter(
                route=assignment.route,
                is_active=True,
                stop_order__gt=current_stop.stop_order,
            )
            .order_by("stop_order")
            .first()
        )

    # Location values
    latitude = None
    longitude = None
    speed = None
    ignition = None
    gps_timestamp = None

    if latest_location:

        if latest_location.latitude is not None:
            latitude = float(latest_location.latitude)

        if latest_location.longitude is not None:
            longitude = float(latest_location.longitude)

        if latest_location.speed is not None:
            speed = float(latest_location.speed)

        ignition = latest_location.ignition

        if latest_location.gps_timestamp:
            gps_timestamp = latest_location.gps_timestamp.isoformat()

    # Fallback to Bus model's current location
    if latitude is None and bus.current_latitude is not None:
        latitude = float(bus.current_latitude)

    if longitude is None and bus.current_longitude is not None:
        longitude = float(bus.current_longitude)

    if speed is None and bus.current_speed is not None:
        speed = float(bus.current_speed)

    if ignition is None:
        ignition = bus.current_ignition

    # Tracker online status
    tracker_online = False

    if bus.last_location_update:
        seconds_since_update = (
            timezone.now() - bus.last_location_update
        ).total_seconds()

        tracker_online = seconds_since_update <= 120

    # Active safety alerts
    alerts = (
        SafetyAlert.objects
        .filter(
            bus=bus,
            status__in=["new", "acknowledged"],
        )
        .order_by("-created_at")[:10]
    )

    alert_data = []

    for alert in alerts:
        alert_data.append({
            "type": alert.get_alert_type_display(),
            "severity": alert.get_severity_display(),
            "title": alert.title,
            "message": alert.message,
            "created_at": alert.created_at.strftime(
                "%d %b %Y, %I:%M %p"
            ),
        })

    # Student pickup/drop stop
    student_stop = None

    if assignment.pickup_required and assignment.pickup_stop:
        student_stop = assignment.pickup_stop.stop_name

    elif assignment.drop_stop:
        student_stop = assignment.drop_stop.stop_name

    # Return live bus data
    return JsonResponse({
        "success": True,

        "student": {
            "id": assignment.student_id,
            "name": str(assignment.student),
        },

        "bus": {
            "number": bus.bus_number,
            "registration": bus.registration_number,
            "name": bus.bus_name,
            "tracker_provider": bus.tracker_provider,
        },

        "location": {
            "latitude": latitude,
            "longitude": longitude,
            "speed": speed,
            "ignition": ignition,
            "gps_timestamp": gps_timestamp,
            "tracker_online": tracker_online,
            "last_update": (
                bus.last_location_update.isoformat()
                if bus.last_location_update
                else None
            ),
        },

        "trip": {
            "status": (
                trip.get_status_display()
                if trip
                else "No active trip"
            ),
            "current_stop": (
                current_stop.stop_name
                if current_stop
                else None
            ),
            "next_stop": (
                next_stop.stop_name
                if next_stop
                else None
            ),
        },

        "student_stop": student_stop,
        "alerts": alert_data,
        "server_time": timezone.now().isoformat(),
    })

@login_required
def vp_buses_dashboard(request):

    forbidden = vice_principal_required(request)

    if forbidden:
        return forbidden

    return render(
        request,
        "transport/vp/buses_dashboard.html",
    )

@login_required
def vp_all_buses(request):

    forbidden = vice_principal_required(request)

    if forbidden:
        return forbidden

    buses = (
        Bus.objects
        .select_related(
            "driver",
            "route",
        )
        .order_by(
            "bus_number"
        )
    )

    return render(
        request,
        "transport/vp/all_buses.html",
        {
            "buses": buses,
        },
    )

@login_required
def vp_bus_assignment(request):

    forbidden = vice_principal_required(request)

    if forbidden:
        return forbidden

    bus_id = request.POST.get("bus_id") or request.GET.get("bus_id")

    if request.GET.get("mode") == "edit" and not bus_id:
        messages.error(request, "Select a bus to edit.")
        return redirect("transport:vp_all_buses")

    if bus_id and not str(bus_id).isdigit():
        return HttpResponseForbidden("Invalid bus selection.")

    bus = get_object_or_404(Bus, pk=bus_id) if bus_id else None

    if request.method == "POST":

        form = BusForm(request.POST, instance=bus)

        if form.is_valid():

            bus = form.save()

            messages.success(
                request,
                (
                    f"Bus {bus.bus_number} updated successfully."
                    if bus_id
                    else f"Bus {bus.bus_number} assigned successfully."
                ),
            )

            return redirect(
                "transport:vp_all_buses"
            )

    else:

        form = BusForm(instance=bus)

    return render(
        request,
        "transport/vp/bus_assignment.html",
        {
            "form": form,
            "bus": bus,
            "is_editing": bus is not None,
        },
    )


@login_required
def vp_student_assignment(request):
    forbidden = vice_principal_required(request)
    if forbidden:
        return forbidden

    if request.method == "POST":
        student_id = request.POST.get("student", "").strip()
        grade = request.POST.get("grade", "").strip()
        bus_id = request.POST.get("bus", "").strip()
        route_id = request.POST.get("route", "").strip()
        pickup_stop_id = request.POST.get("pickup_stop", "").strip()
        drop_stop_id = request.POST.get("drop_stop", "").strip()

        pickup_required = request.POST.get("pickup_required") == "on"
        drop_required = request.POST.get("drop_required") == "on"
        is_active = request.POST.get("is_active") == "on"

        # Validate the selected student and grade.
        student = get_object_or_404(
            StudentAdmissionApplication,
            pk=student_id,
            status="account_created",
        )

        if student.applying_class != grade:
            messages.error(
                request,
                "Selected student does not belong to this grade.",
            )
            return redirect("transport:vp_student_assignment")

        # Prevent duplicate active assignments.
        if is_active and StudentBusAssignment.objects.filter(
            student=student,
            is_active=True,
        ).exists():
            messages.error(
                request,
                "This student already has an active bus assignment. Use Edit.",
            )
            return redirect("transport:vp_student_assignment")

        # Validate bus and route.
        bus = get_object_or_404(
            Bus,
            pk=bus_id,
            is_active=True,
        )

        route = get_object_or_404(
            BusRoute,
            pk=route_id,
            is_active=True,
        )

        if bus.route_id != route.pk:
            messages.error(
                request,
                "Selected bus is not assigned to this route.",
            )
            return redirect("transport:vp_student_assignment")

        pickup_stop = None
        drop_stop = None

        # Validate pickup stop without raising a Stop-related 404.
        if pickup_required:
            if not pickup_stop_id:
                messages.error(request, "Please select a pickup stop.")
                return redirect("transport:vp_student_assignment")

            pickup_stop = BusStop.objects.filter(
                pk=pickup_stop_id,
                route=route,
                is_active=True,
            ).first()

            if pickup_stop is None:
                messages.error(
                    request,
                    "Selected pickup stop is not active or does not belong to this route. Please select it again.",
                )
                return redirect("transport:vp_student_assignment")

        # Validate drop stop without raising a Stop-related 404.
        if drop_required:
            if not drop_stop_id:
                messages.error(request, "Please select a drop stop.")
                return redirect("transport:vp_student_assignment")

            drop_stop = BusStop.objects.filter(
                pk=drop_stop_id,
                route=route,
                is_active=True,
            ).first()

            if drop_stop is None:
                messages.error(
                    request,
                    "Selected drop stop is not active or does not belong to this route. Please select it again.",
                )
                return redirect("transport:vp_student_assignment")

        # Save the assignment.
        StudentBusAssignment.objects.create(
            student=student,
            bus=bus,
            route=route,
            pickup_stop=pickup_stop,
            drop_stop=drop_stop,
            pickup_required=pickup_required,
            drop_required=drop_required,
            is_active=is_active,
        )

        messages.success(
            request,
            f"Bus assignment saved for {student.first_name} {student.last_name}.",
        )
        return redirect("transport:vp_student_assignment")

    # Display existing assignments.
    assignments = (
        StudentBusAssignment.objects
        .select_related(
            "student",
            "bus",
            "bus__driver",
            "route",
            "pickup_stop",
            "drop_stop",
        )
        .order_by(
            "-is_active",
            "bus__bus_number",
            "student__first_name",
        )
    )

    # Only grades with account-created students.
    grades = (
        StudentAdmissionApplication.objects
        .filter(status="account_created")
        .exclude(applying_class__isnull=True)
        .exclude(applying_class="")
        .values_list("applying_class", flat=True)
        .distinct()
        .order_by("applying_class")
    )

    return render(
        request,
        "transport/vp/student_assignment.html",
        {
            "assignments": assignments,
            "grades": grades,
            "buses": Bus.objects.filter(
                is_active=True
            ).select_related("route"),
            "routes": BusRoute.objects.filter(
                is_active=True
            ).order_by("route_name"),
            "stops": BusStop.objects.select_related(
                "route"
            ).order_by(
                "route_id",
                "stop_order",
            ),
            "editing": False,
            "assignment": None,
        },
    )

@login_required
def students_by_grade(request):
    forbidden = vice_principal_required(request)
    if forbidden:
        return forbidden

    grade = request.GET.get("grade", "").strip()
    assignment_id = request.GET.get("assignment_id", "").strip()

    if not grade:
        return JsonResponse({"students": []})

    students = StudentAdmissionApplication.objects.filter(
        status="account_created",
        applying_class=grade,
    ).order_by("first_name", "last_name")

    # Exclude students who already have an active assignment.
    already_assigned = StudentBusAssignment.objects.filter(
        is_active=True
    ).values_list("student_id", flat=True)

    students = list(students.exclude(pk__in=already_assigned))

    # While editing, keep the student already assigned to this record.
    if assignment_id.isdigit():
        current = (
            StudentBusAssignment.objects
            .filter(pk=int(assignment_id))
            .select_related("student")
            .first()
        )

        if (
            current
            and current.student.status == "account_created"
            and current.student.applying_class == grade
            and all(s.pk != current.student_id for s in students)
        ):
            students.insert(0, current.student)

    return JsonResponse({
        "students": [
            {
                "id": s.pk,
                "name": f"{s.first_name or ''} {s.last_name or ''}".strip(),
                "application_id": s.application_id or "",
            }
            for s in students
        ]
    })

@login_required
def vp_student_assignment_edit(request, assignment_id):
    forbidden = vice_principal_required(request)
    if forbidden:
        return forbidden

    assignment = get_object_or_404(
        StudentBusAssignment.objects.select_related(
            "student", "bus", "route", "pickup_stop", "drop_stop"
        ),
        pk=assignment_id,
    )

    if request.method == "POST":
        student_id = request.POST.get("student", "").strip()
        grade = request.POST.get("grade", "").strip()
        bus_id = request.POST.get("bus", "").strip()
        route_id = request.POST.get("route", "").strip()
        pickup_stop_id = request.POST.get("pickup_stop", "").strip()
        drop_stop_id = request.POST.get("drop_stop", "").strip()

        pickup_required = request.POST.get("pickup_required") == "on"
        drop_required = request.POST.get("drop_required") == "on"
        is_active = request.POST.get("is_active") == "on"

        student = get_object_or_404(
            StudentAdmissionApplication,
            pk=student_id,
            status="account_created",
        )

        if student.applying_class != grade:
            messages.error(request, "Selected student does not belong to this grade.")
            return redirect(
                "transport:vp_student_assignment_edit",
                assignment_id=assignment.pk,
            )

        duplicate = StudentBusAssignment.objects.filter(
            student=student,
            is_active=True,
        ).exclude(pk=assignment.pk).exists()

        if duplicate and is_active:
            messages.error(
                request,
                "This student already has another active bus assignment.",
            )
            return redirect(
                "transport:vp_student_assignment_edit",
                assignment_id=assignment.pk,
            )

        bus = get_object_or_404(Bus, pk=bus_id, is_active=True)
        route = get_object_or_404(BusRoute, pk=route_id, is_active=True)

        if bus.route_id != route.id:
            messages.error(request, "Selected bus is not assigned to this route.")
            return redirect(
                "transport:vp_student_assignment_edit",
                assignment_id=assignment.pk,
            )

        pickup_stop = None
        drop_stop = None

        if pickup_required:
            if not pickup_stop_id:
                messages.error(request, "Select a pickup stop.")
                return redirect(
                    "transport:vp_student_assignment_edit",
                    assignment_id=assignment.pk,
                )

            pickup_stop = get_object_or_404(
                BusStop,
                pk=pickup_stop_id,
                route=route,
                is_active=True,
            )

        if drop_required:
            if not drop_stop_id:
                messages.error(request, "Select a drop stop.")
                return redirect(
                    "transport:vp_student_assignment_edit",
                    assignment_id=assignment.pk,
                )

            drop_stop = get_object_or_404(
                BusStop,
                pk=drop_stop_id,
                route=route,
                is_active=True,
            )

        assignment.student = student
        assignment.bus = bus
        assignment.route = route
        assignment.pickup_stop = pickup_stop
        assignment.drop_stop = drop_stop
        assignment.pickup_required = pickup_required
        assignment.drop_required = drop_required
        assignment.is_active = is_active
        assignment.save()

        messages.success(request, "Student bus assignment updated successfully.")
        return redirect("transport:vp_student_assignment")

    assignments = (
        StudentBusAssignment.objects
        .select_related(
            "student", "bus", "bus__driver", "route", "pickup_stop", "drop_stop"
        )
        .order_by("-is_active", "bus__bus_number", "student__first_name")
    )

    grades = (
        StudentAdmissionApplication.objects
        .filter(status="account_created")
        .exclude(applying_class__isnull=True)
        .exclude(applying_class="")
        .values_list("applying_class", flat=True)
        .distinct()
        .order_by("applying_class")
    )

    return render(
        request,
        "transport/vp/student_assignment.html",
        {
            "assignments": assignments,
            "grades": grades,
            "buses": Bus.objects.filter(is_active=True).select_related("route"),
            "routes": BusRoute.objects.filter(is_active=True).order_by("route_name"),
            "stops": BusStop.objects.select_related("route").order_by(
                "route_id", "stop_order"
            ),
            "editing": True,
            "assignment": assignment,
        },
    )

@login_required
def vp_trip_history(request):

    forbidden = vice_principal_required(request)

    if forbidden:
        return forbidden

    trips = (
        BusTrip.objects
        .select_related(
            "bus",
            "route",
            "driver",
            "current_stop",
        )
        .order_by(
            "-trip_date",
            "-scheduled_start_time",
        )
    )

    return render(
        request,
        "transport/vp/trip_history.html",
        {
            "trips": trips,
        },
    )


# =========================================================
# VP - ALL BUS LOCATIONS
# =========================================================

@login_required
def vp_bus_location(request):

    forbidden = vice_principal_required(request)

    if forbidden:
        return forbidden

    buses = (
        Bus.objects
        .select_related(
            "route",
            "driver",
        )
        .filter(
            is_active=True,
        )
        .order_by(
            "bus_number"
        )
    )

    locations = (
        BusLocation.objects
        .select_related(
            "bus",
        )
        .order_by(
            "-gps_timestamp",
            "-received_at",
        )[:200]
    )

    return render(
        request,
        "transport/vp/bus_location.html",
        {
            "buses": buses,
            "locations": locations,
        },
    )


# =========================================================
# VP - ALL SAFETY ALERTS
# =========================================================

@login_required
def vp_safety_alerts(request):

    forbidden = vice_principal_required(request)

    if forbidden:
        return forbidden

    alerts = (
        SafetyAlert.objects
        .select_related(
            "bus",
            "trip",
            "acknowledged_by",
        )
        .order_by(
            "-created_at"
        )
    )

    return render(
        request,
        "transport/vp/safety_alerts.html",
        {
            "alerts": alerts,
        },
    )


# =========================================================
# VP - ALL BUS ISSUES
# =========================================================

@login_required
def vp_bus_issues(request):

    forbidden = vice_principal_required(request)

    if forbidden:
        return forbidden

    issues = (
        BusIssue.objects
        .select_related(
            "bus",
            "reported_by",
        )
        .order_by(
            "-created_at"
        )
    )

    return render(
        request,
        "transport/vp/bus_issues.html",
        {
            "issues": issues,
        },
    )


# =========================================================
# ACCOUNTANT - BUS EXPENSES ONLY
# =========================================================

@login_required
def accountant_expenses(request):

    forbidden = accountant_required(request)

    if forbidden:
        return forbidden

    expenses = (
        BusExpense.objects
        .select_related(
            "bus",
            "reported_by",
            "reviewed_by",
        )
        .order_by(
            "-expense_date",
            "-created_at",
        )
    )

    return render(
        request,
        "transport/accountant/expenses.html",
        {
            "expenses": expenses,
        },
    )


# =========================================================
# VP - BUS ROUTE FORM
# =========================================================

class BusRouteForm(forms.ModelForm):

    class Meta:

        model = BusRoute

        fields = [
            "route_name",
            "route_code",
            "start_location",
            "end_location",
            "total_distance_km",
            "estimated_duration_minutes",
            "is_active",
        ]

        widgets = {

            "route_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder":
                        "Example: Madanapalle - School Route",
                }
            ),

            "route_code": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder":
                        "Example: MRT-001",
                }
            ),

            "start_location": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder":
                        "Example: Madanapalle",
                }
            ),

            "end_location": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder":
                        "Example: School Campus",
                }
            ),

            "total_distance_km": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                }
            ),

            "estimated_duration_minutes":
                forms.NumberInput(
                    attrs={
                        "class": "form-control",
                        "min": "0",
                    }
                ),

            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }


# =========================================================
# VP - BUS STOP FORM
# =========================================================

class BusStopForm(forms.ModelForm):

    class Meta:

        model = BusStop

        fields = [
            "stop_name",
            "stop_order",
            "address",
            "pickup_time",
            "drop_time",
            "is_active",
        ]

        widgets = {

            "stop_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder":
                        "Example: Angallu",
                }
            ),

            "stop_order": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1",
                    "placeholder":
                        "1",
                }
            ),

            "address": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder":
                        "Example: Angallu Main Road",
                }
            ),

            "pickup_time": forms.TimeInput(
                attrs={
                    "class": "form-control",
                    "type": "time",
                }
            ),

            "drop_time": forms.TimeInput(
                attrs={
                    "class": "form-control",
                    "type": "time",
                }
            ),

            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }


# =========================================================
# VP - ALL BUS ROUTES
# =========================================================

@login_required
def vp_bus_routes(request):

    forbidden = vice_principal_required(request)

    if forbidden:
        return forbidden

    routes = (
        BusRoute.objects
        .prefetch_related(
            "stops",
            "buses",
        )
        .order_by(
            "route_name"
        )
    )

    route_form = BusRouteForm()

    if request.method == "POST":

        action = request.POST.get(
            "action"
        )

        # -------------------------------------------------
        # CREATE ROUTE
        # -------------------------------------------------

        if action == "create_route":

            route_form = BusRouteForm(
                request.POST
            )

            if route_form.is_valid():

                route = route_form.save()

                messages.success(
                    request,
                    f"Route '{route.route_name}' created successfully."
                )

                return redirect(
                    "transport:vp_bus_routes"
                )

            messages.error(
                request,
                "Please correct the route details."
            )

    return render(
        request,
        "transport/vp/bus_routes.html",
        {
            "routes": routes,
            "route_form": route_form,
        },
    )


# =========================================================
# VP - ROUTE DETAIL
# =========================================================

@login_required
def vp_route_detail(request, route_id):

    forbidden = vice_principal_required(request)

    if forbidden:
        return forbidden

    route = get_object_or_404(
        BusRoute.objects.prefetch_related(
            "stops",
            "buses",
        ),
        pk=route_id,
    )

    stops = (
        route.stops
        .all()
        .order_by(
            "stop_order"
        )
    )

    assigned_bus = (
        route.buses
        .filter(
            is_active=True,
        )
        .first()
    )

    buses = (
        Bus.objects
        .filter(
            is_active=True,
        )
        .order_by(
            "bus_number"
        )
    )

    stop_form = BusStopForm()

    if request.method == "POST":

        action = request.POST.get(
            "action"
        )

        # -------------------------------------------------
        # ADD STOP
        # -------------------------------------------------

        if action == "add_stop":

            stop_form = BusStopForm(
                request.POST
            )

            if stop_form.is_valid():

                stop = stop_form.save(
                    commit=False
                )

                stop.route = route

                try:

                    stop.save()

                    messages.success(
                        request,
                        f"Stop '{stop.stop_name}' added successfully."
                    )

                    return redirect(
                        "transport:vp_route_detail",
                        route_id=route.id,
                    )

                except Exception:

                    messages.error(
                        request,
                        "This stop order already exists for this route."
                    )

        # -------------------------------------------------
        # ASSIGN / CHANGE BUS
        # -------------------------------------------------

        elif action == "assign_bus":

            bus_id = request.POST.get(
                "assigned_bus"
            )

            # -------------------------------------------------
            # REMOVE BUS
            # -------------------------------------------------

            if not bus_id:

                Bus.objects.filter(
                    route=route
                ).update(
                    route=None
                )

                messages.success(
                    request,
                    "Bus assignment removed."
                )

            # -------------------------------------------------
            # ASSIGN BUS
            # -------------------------------------------------

            else:

                bus = get_object_or_404(
                    Bus,
                    pk=bus_id,
                    is_active=True,
                )

                # Remove old bus from this route
                Bus.objects.filter(
                    route=route
                ).update(
                    route=None
                )

                # Remove selected bus from another route
                Bus.objects.filter(
                    pk=bus.pk
                ).update(
                    route=None
                )

                bus.route = route

                bus.save(
                    update_fields=[
                        "route"
                    ]
                )

                messages.success(
                    request,
                    f"Bus {bus.bus_number} assigned successfully."
                )

            return redirect(
                "transport:vp_route_detail",
                route_id=route.id,
            )

    return render(
        request,
        "transport/vp/route_detail.html",
        {
            "route": route,
            "stops": stops,
            "assigned_bus": assigned_bus,
            "buses": buses,
            "stop_form": stop_form,
        },
    )


# =========================================================
# VP - DELETE ROUTE
# =========================================================

@login_required
@require_POST
def vp_delete_route(request, route_id):

    forbidden = vice_principal_required(request)

    if forbidden:
        return forbidden

    route = get_object_or_404(
        BusRoute,
        pk=route_id,
    )

    route_name = route.route_name

    # Unassign buses first
    Bus.objects.filter(
        route=route
    ).update(
        route=None
    )

    route.delete()

    messages.success(
        request,
        f"Route '{route_name}' deleted successfully."
    )

    return redirect(
        "transport:vp_bus_routes"
    )


# =========================================================
# VP - DELETE STOP
# =========================================================

@login_required
@require_POST
def vp_delete_stop(request, stop_id):

    forbidden = vice_principal_required(request)

    if forbidden:
        return forbidden

    stop = get_object_or_404(
        BusStop,
        pk=stop_id,
    )

    route_id = stop.route_id
    stop_name = stop.stop_name

    stop.delete()

    messages.success(
        request,
        f"Stop '{stop_name}' deleted successfully."
    )

    return redirect(
        "transport:vp_route_detail",
        route_id=route_id,
    )

@login_required
def route_options(request):

    location = request.GET.get("location", "").strip()
    routes = (
        BusRoute.objects
        .filter(is_active=True)
        .order_by("route_name")
    )

    if location:
        routes = routes.filter(start_location__iexact=location)

    selected_route_id = request.GET.get("selected_route_id", "").strip()
    if selected_route_id.isdigit():
        selected_route = BusRoute.objects.filter(pk=selected_route_id).first()
        if selected_route and (
            not location
            or selected_route.start_location.casefold() == location.casefold()
        ):
            routes = routes | BusRoute.objects.filter(pk=selected_route.pk)
            routes = routes.order_by("route_name")

    data = []

    for route in routes:
        data.append({
            "id": route.id,
            "name": route.route_name,
            "code": route.route_code,
        })

    return JsonResponse({
        "routes": data
    })


@login_required
def stop_options(request):

    route_id = request.GET.get("route_id", "").strip()

    if not route_id.isdigit():
        return JsonResponse({
            "stops": []
        })

    stops = BusStop.objects.filter(
        route_id=route_id,
    )
    selected_stop_id = request.GET.get("selected_stop_id", "").strip()
    if selected_stop_id.isdigit():
        stops = stops | BusStop.objects.filter(
            route_id=route_id,
            pk=selected_stop_id,
        )
    stops = stops.distinct().order_by("stop_order")

    data = []

    for stop in stops:
        data.append({
            "id": stop.id,
            "name": stop.stop_name,
            "order": stop.stop_order,
        })

    return JsonResponse({
        "stops": data
    })