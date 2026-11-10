from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.utils import timezone
from decimal import Decimal

from django.db.models import (
    Sum,
    Q,
    F,
    Avg,
    Value,
    DecimalField,
    ExpressionWrapper,
)
from django.db.models.functions import Coalesce
from academics.models import ClassSection, Subject
from attendance.models import StudentAttendance, EmployeeAttendance
from exams.models import Examination, ExamMark
from finance.models import StudentFee, FeePayment, SchoolExpense, StaffSalary
from transport.models import Bus, BusRoute, BusExpense, BusIssue, SafetyAlert
from leave_management.models import LeaveRequest
from announcements.models import Announcement
from notifications.models import Notification
from admissions.models import StudentAdmissionApplication, EmployeeAdmissionApplication, ApplicationApproval
def get_today_attendance():
    """
    Calculate today's combined student + employee attendance.
    """

    today = timezone.localdate()

    student_records = StudentAttendance.objects.filter(
        date=today
    )

    employee_records = EmployeeAttendance.objects.filter(
        date=today
    )

    student_total = student_records.count()
    employee_total = employee_records.count()

    student_present = student_records.filter(
        status__in=["Present", "Late"]
    ).count()

    employee_present = employee_records.filter(
        status__in=["Present", "Late"]
    ).count()

    total = student_total + employee_total
    present = student_present + employee_present
    absent = total - present

    if total > 0:
        percentage = round(
            (present / total) * 100,
            1
        )
    else:
        percentage = 0

    return {
        "percentage": percentage,
        "total": total,
        "present": present,
        "absent": absent,
        "student_total": student_total,
        "employee_total": employee_total,
    }


# ============================================================
# NOTIFICATION HELPERS
# ============================================================

def get_notification_counts(user):
    """
    Common notification counts.
    """

    notifications = Notification.objects.filter(
        recipient=user
    )

    # --------------------------------------------------------
    # APPROVALS
    # --------------------------------------------------------

    approval_notifications = notifications.filter(
        notification_type__icontains="approval"
    )

    approval_count = approval_notifications.count()

    unread_approval_count = approval_notifications.filter(
        is_read=False
    ).count()

    # --------------------------------------------------------
    # LEAVES
    # --------------------------------------------------------

    leave_notifications = notifications.filter(
        notification_type__icontains="leave"
    )

    leave_count = leave_notifications.count()

    unread_leave_count = leave_notifications.filter(
        is_read=False
    ).count()

    # --------------------------------------------------------
    # EVENTS
    # --------------------------------------------------------

    event_notifications = notifications.filter(
        notification_type__icontains="event"
    )

    event_count = event_notifications.count()

    unread_event_count = event_notifications.filter(
        is_read=False
    ).count()

    # --------------------------------------------------------
    # SAFETY ALERTS
    # --------------------------------------------------------

    safety_notifications = notifications.filter(
        Q(notification_type__icontains="safety")
        |
        Q(notification_type__icontains="emergency")
        |
        Q(notification_type__icontains="alert")
    )

    safety_count = safety_notifications.count()

    unread_safety_count = safety_notifications.filter(
        is_read=False
    ).count()

    # --------------------------------------------------------
    # ANNOUNCEMENTS
    # --------------------------------------------------------

    announcement_notifications = notifications.filter(
        notification_type__icontains="announcement"
    )

    announcement_count = announcement_notifications.count()

    unread_announcement_count = announcement_notifications.filter(
        is_read=False
    ).count()

    return {
        "approval_count": approval_count,
        "unread_approval_count": unread_approval_count,

        "leave_count": leave_count,
        "unread_leave_count": unread_leave_count,

        "event_count": event_count,
        "unread_event_count": unread_event_count,

        "safety_count": safety_count,
        "unread_safety_count": unread_safety_count,

        "announcement_count": announcement_count,
        "unread_announcement_count": unread_announcement_count,
    }


# ============================================================
# DASHBOARD HOME
# ============================================================

@login_required
def dashboard_home(request):

    # ========================================================
    # PROFILE CHECK
    # ========================================================

    if not hasattr(request.user, "profile"):
        return HttpResponseForbidden(
            "User profile not found."
        )

    profile = request.user.profile

    role = profile.role

    today = timezone.localdate()

    # ========================================================
    # COMMON ATTENDANCE
    # Chairman excluded
    # ========================================================

    attendance = get_today_attendance()

    # ========================================================
    # COMMON NOTIFICATIONS
    # ========================================================

    notification_counts = get_notification_counts(
        request.user
    )

    # ========================================================
    # ANNOUNCEMENTS
    # ========================================================

    now = timezone.now()

    active_announcements = Announcement.objects.filter(
        is_active=True
    ).filter(
        Q(expiry_date__isnull=True)
        |
        Q(expiry_date__gte=now)
    ).count()

    # ========================================================
    # BASE CONTEXT
    # ========================================================

    context = {

        "role": role,

        "role_name": role.replace(
            "_",
            " "
        ).title(),

        "today": today,

        "attendance": attendance,

        "active_announcements":
            active_announcements,

        "approval_count":
            notification_counts[
                "approval_count"
            ],

        "unread_approval_count":
            notification_counts[
                "unread_approval_count"
            ],

        "leave_count":
            notification_counts[
                "leave_count"
            ],

        "unread_leave_count":
            notification_counts[
                "unread_leave_count"
            ],

        "event_count":
            notification_counts[
                "event_count"
            ],

        "unread_event_count":
            notification_counts[
                "unread_event_count"
            ],

        "safety_count":
            notification_counts[
                "safety_count"
            ],

        "unread_safety_count":
            notification_counts[
                "unread_safety_count"
            ],

        "announcement_count":
            notification_counts[
                "announcement_count"
            ],

        "unread_announcement_count":
            notification_counts[
                "unread_announcement_count"
            ],

        "actions": [],
    }

    # ========================================================
    # ADMISSION STAFF
    # ========================================================

    if role == "admission_staff":

        student_pending = (
            StudentAdmissionApplication.objects
            .filter(
                status__in=[
                    "submitted",
                    "system_admin_pending",
                ]
            )
            .count()
        )

        employee_pending = (
            EmployeeAdmissionApplication.objects
            .filter(
                status__in=[
                    "submitted",
                    "system_admin_pending",
                ]
            )
            .count()
        )

        total_pending = (
            student_pending
            +
            employee_pending
        )

        context.update({

            "student_pending":
                student_pending,

            "employee_pending":
                employee_pending,

            "admission_pending":
                total_pending,

        })

    # ========================================================
    # SYSTEM ADMINISTRATOR
    # ========================================================

    elif role == "system_administrator":

        active_accounts = User.objects.filter(
            is_active=True
        ).count()

        new_accounts_today = User.objects.filter(
            date_joined__date=today
        ).count()

        system_admin_pending = (
            ApplicationApproval.objects
            .filter(
                application_type__in=[
                    "Student",
                    "Employee",
                ],
                stage="system_admin",
                status="pending",
            )
            .count()
        )

        student_approvals = (
            ApplicationApproval.objects
            .filter(
                application_type="Student",
                stage="system_admin",
                status="pending",
            )
            .count()
        )

        employee_approvals = (
            ApplicationApproval.objects
            .filter(
                application_type="Employee",
                stage="system_admin",
                status="pending",
            )
            .count()
        )

        context.update({

            "active_accounts":
                active_accounts,

            "new_accounts_today":
                new_accounts_today,

            "system_admin_pending":
                system_admin_pending,

            "student_approvals":
                student_approvals,

            "employee_approvals":
                employee_approvals,

        })

    # ========================================================
    # VICE PRINCIPAL
    # ========================================================

    elif role == "vice_principal":

        # ----------------------------------------------------
        # VP APPROVALS
        # ----------------------------------------------------

        vp_pending = (
            ApplicationApproval.objects
            .filter(
                status="pending",
                stage="vice_principal",
            )
            .count()
        )

        vp_student_pending = (
            ApplicationApproval.objects
            .filter(
                application_type="Student",
                status="pending",
                stage="vice_principal",
            )
            .count()
        )

        vp_employee_pending = (
            ApplicationApproval.objects
            .filter(
                application_type="Employee",
                status="pending",
                stage="vice_principal",
            )
            .count()
        )

        # ----------------------------------------------------
        # CLASS SECTIONS
        # ----------------------------------------------------

        class_count = ClassSection.objects.count()

        context.update({

            "vp_pending":
                vp_pending,

            "vp_student_pending":
                vp_student_pending,

            "vp_employee_pending":
                vp_employee_pending,

            "class_count":
                class_count,

        })

    # ========================================================
    # TEACHER
    # ========================================================

    elif role == "teacher":

        # ----------------------------------------------------
        # MY CLASSES
        # ----------------------------------------------------

        try:

            my_classes = ClassSection.objects.filter(
                class_teacher=request.user
            ).count()

        except Exception:

            my_classes = 0

        # ----------------------------------------------------
        # ASSIGNMENTS
        # ----------------------------------------------------
        # Assignment model may differ in project.
        # Notification count is used safely for now.

        assignment_count = Notification.objects.filter(
            recipient=request.user,
            notification_type__icontains="assignment"
        ).count()

        unread_assignment_count = Notification.objects.filter(
            recipient=request.user,
            notification_type__icontains="assignment",
            is_read=False
        ).count()

        context.update({

            "my_classes":
                my_classes,

            "assignment_count":
                assignment_count,

            "unread_assignment_count":
                unread_assignment_count,

        })

    # ========================================================
    # STUDENT
    # ========================================================

    elif role == "student":

        # Student-specific dynamic values
        context.update({

            "student_event_count":
                notification_counts[
                    "event_count"
                ],

        })

    # ========================================================
    # PARENT
    # ========================================================

    elif role == "parent":

        # Parent uses child-related dashboard
        context.update({

            "parent_event_count":
                notification_counts[
                    "event_count"
                ],

        })
        # ========================================================
    # ACCOUNTANT
    # ========================================================

    elif role == "accountant":

        # ----------------------------------------------------
        # TOTAL FEES COLLECTED
        # ----------------------------------------------------

        total_fees_collected = (
            FeePayment.objects.aggregate(
                total=Sum("amount")
            )["total"]
            or Decimal("0.00")
        )

        # ----------------------------------------------------
        # TODAY'S COLLECTION
        # ----------------------------------------------------

        today_collection = (
            FeePayment.objects.filter(
                paid_at__date=today
            ).aggregate(
                total=Sum("amount")
            )["total"]
            or Decimal("0.00")
        )

        # ----------------------------------------------------
        # TOTAL TRANSACTIONS
        # ----------------------------------------------------

        total_transactions = FeePayment.objects.count()

        # ----------------------------------------------------
        # PENDING FEES
        # Total fee amount minus payments made for each fee
        # ----------------------------------------------------

        fee_balances = (
            StudentFee.objects
            .annotate(
                paid_total=Coalesce(
                    Sum("payments__amount"),
                    Value(Decimal("0.00")),
                    output_field=DecimalField(
                        max_digits=12,
                        decimal_places=2,
                    ),
                )
            )
            .annotate(
                balance=ExpressionWrapper(
                    F("total_amount") - F("paid_total"),
                    output_field=DecimalField(
                        max_digits=12,
                        decimal_places=2,
                    ),
                )
            )
            .filter(balance__gt=Decimal("0.00"))
        )

        pending_fees = (
            fee_balances.aggregate(
                total=Sum("balance")
            )["total"]
            or Decimal("0.00")
        )

        # ----------------------------------------------------
        # SEND DATA TO ACCOUNTANT DASHBOARD
        # ----------------------------------------------------

        context.update({

            "total_fees_collected":
                total_fees_collected,

            "pending_fees":
                pending_fees,

            "today_collection":
                today_collection,

            "total_transactions":
                total_transactions,

        })

    # ========================================================
    # RENDER
    # ========================================================

    return render(
        request,
        "dashboard/dashboard.html",
        context
    )


from django.contrib.auth.decorators import login_required
from django.shortcuts import render


# ============================================================
# CHAIRMAN / PRINCIPAL ACCESS HELPERS
# ============================================================

def chairman_only(request):
    return (
        hasattr(request.user, "profile")
        and request.user.profile.role == "chairman"
    )


def management_user(request):
    return (
        hasattr(request.user, "profile")
        and request.user.profile.role in {
            "chairman",
            "principal",
        }
    )


# ============================================================
# DATABASE TOTAL HELPERS
# ============================================================

def _money_total(queryset, field_name="amount"):
    total = queryset.aggregate(
        total=Sum(field_name)
    )["total"]

    return total or Decimal("0.00")


def _paid_salary_total(queryset=None):
    if queryset is None:
        queryset = StaffSalary.objects.filter(status="paid")

    total = queryset.aggregate(
        total=Sum(
            ExpressionWrapper(
                F("basic_salary")
                + F("allowances")
                - F("deductions"),
                output_field=DecimalField(
                    max_digits=14,
                    decimal_places=2,
                ),
            )
        )
    )["total"]

    return total or Decimal("0.00")


def _approved_expense_total():
    school_expenses = _money_total(
        SchoolExpense.objects.filter(
            approval_status="approved"
        )
    )

    transport_expenses = _money_total(
        BusExpense.objects.filter(
            status="approved"
        )
    )

    return school_expenses + transport_expenses


# ============================================================
# CHAIRMAN / PRINCIPAL DASHBOARD
# ============================================================

@login_required
def chairman_dashboard(request):

    if not management_user(request):
        return render(
            request,
            "dashboard/403.html",
            status=403,
        )

    role = request.user.profile.role
    today = timezone.localdate()

    student_count = StudentAdmissionApplication.objects.filter(
        status="account_created"
    ).count()

    employee_count = EmployeeAdmissionApplication.objects.filter(
        status="account_created"
    ).count()

    subject_count = Subject.objects.filter(
        is_active=True
    ).count()

    bus_count = Bus.objects.count()

    approval_count = (
        ApplicationApproval.objects.filter(
            status="pending"
        ).count()
        + SchoolExpense.objects.filter(
            approval_status="pending"
        ).count()
        + BusExpense.objects.filter(
            status="submitted"
        ).count()
        + LeaveRequest.objects.filter(
            status="pending"
        ).count()
    )

    context = {
        "role": role,
        "today": today,
        "student_count": student_count,
        "new_admission_count":
            StudentAdmissionApplication.objects.filter(
                submitted_at__date=today
            ).count(),
        "employee_count": employee_count,
        "subject_count": subject_count,
        "expense_total": _approved_expense_total(),
        "bus_count": bus_count,
        "approval_count": approval_count,
    }

    return render(
        request,
        "dashboard/chairman_dashboard.html",
        context,
    )


# ============================================================
# STUDENTS
# ============================================================

@login_required
def chairman_students(request):

    if not management_user(request):
        return render(
            request,
            "dashboard/403.html",
            status=403,
        )

    today = timezone.localdate()

    students = StudentAdmissionApplication.objects.filter(
        status="account_created"
    )

    today_attendance = StudentAttendance.objects.filter(
        date=today
    )

    attendance_total = today_attendance.count()

    attendance_present = today_attendance.filter(
        status__in=["Present", "Late"]
    ).count()

    attendance_percentage = (
        round(
            attendance_present * 100 / attendance_total,
            1,
        )
        if attendance_total
        else 0
    )

    student_fee_total = _money_total(
        FeePayment.objects.filter(
            fee__student__status="account_created"
        )
    )

    context = {
        "student_count": students.count(),
        "new_admission_count":
            StudentAdmissionApplication.objects.filter(
                submitted_at__date=today
            ).count(),
        "attendance_percentage": attendance_percentage,
        "student_fee_total": student_fee_total,
        "student_attendance_total": attendance_total,
        "student_attendance_present": attendance_present,
        "students": students.order_by(
            "first_name",
            "last_name",
        ),
    }

    return render(
        request,
        "dashboard/chairman/students.html",
        context,
    )


# ============================================================
# EMPLOYEES
# ============================================================

@login_required
def chairman_employees(request):

    if not management_user(request):
        return render(
            request,
            "dashboard/403.html",
            status=403,
        )

    employees = EmployeeAdmissionApplication.objects.filter(
        status="account_created"
    )

    teaching_staff = employees.filter(
        Q(designation__icontains="teacher")
        | Q(department__icontains="teaching")
    )

    salary_total = _paid_salary_total(
        StaffSalary.objects.filter(
            status="paid",
            employee__status="account_created",
        )
    )

    context = {
        "employee_count": employees.count(),
        "teaching_staff_count": teaching_staff.count(),
        "non_teaching_staff_count": max(
            employees.count() - teaching_staff.count(),
            0,
        ),
        "salary_total": salary_total,
        "employees": employees.order_by(
            "first_name",
            "last_name",
        ),
    }

    return render(
        request,
        "dashboard/chairman/employees.html",
        context,
    )


# ============================================================
# ACADEMICS
# ============================================================

@login_required
def chairman_academics(request):

    if not management_user(request):
        return render(
            request,
            "dashboard/403.html",
            status=403,
        )

    classes = ClassSection.objects.all()
    subjects = Subject.objects.filter(is_active=True)
    examinations = Examination.objects.all()

    published_marks = ExamMark.objects.filter(
        status="published"
    )

    average = published_marks.aggregate(
        average=Avg("percentage")
    )["average"]

    context = {
        "class_section_count":
            classes.filter(status="Active").count(),
        "subject_count": subjects.count(),
        "exam_count": examinations.count(),
        "academic_percentage":
            round(float(average), 1)
            if average is not None
            else 0,
        "classes": classes,
        "subjects": subjects,
        "examinations": examinations,
    }

    return render(
        request,
        "dashboard/chairman/academics.html",
        context,
    )


# ============================================================
# FINANCE - CHAIRMAN ONLY
# ============================================================

@login_required
def chairman_finance(request):

    if not chairman_only(request):
        return render(
            request,
            "dashboard/403.html",
            status=403,
        )

    fee_total = _money_total(
        FeePayment.objects.all()
    )

    salary_total = _paid_salary_total()
    expense_total = _approved_expense_total()

    context = {
        "fee_total": fee_total,
        "salary_total": salary_total,
        "expense_total": expense_total,
        "income_total": fee_total,
        "pending_school_expense_count":
            SchoolExpense.objects.filter(
                approval_status="pending"
            ).count(),
        "pending_transport_expense_count":
            BusExpense.objects.filter(
                status="submitted"
            ).count(),
    }

    return render(
        request,
        "dashboard/chairman/finance.html",
        context,
    )


# ============================================================
# TRANSPORT
# ============================================================

@login_required
def chairman_transport(request):

    if not management_user(request):
        return render(
            request,
            "dashboard/403.html",
            status=403,
        )

    buses = Bus.objects.all()

    context = {
        "bus_count": buses.count(),
        "active_bus_count": buses.filter(
            is_active=True,
            status="active",
        ).count(),
        "driver_count":
            buses.exclude(
                driver__isnull=True
            ).values(
                "driver_id"
            ).distinct().count(),
        "route_count": BusRoute.objects.filter(
            is_active=True
        ).count(),
        "open_issue_count":
            BusIssue.objects.exclude(
                status__in=["resolved", "closed"]
            ).count(),
        "new_safety_alert_count":
            SafetyAlert.objects.filter(
                status="new"
            ).count(),
        "buses": buses.select_related(
            "driver",
            "route",
        ),
    }

    return render(
        request,
        "dashboard/chairman/transport.html",
        context,
    )


# ============================================================
# APPROVALS
# ============================================================

@login_required
def chairman_approvals(request):

    if not management_user(request):
        return render(
            request,
            "dashboard/403.html",
            status=403,
        )

    admission_approvals = ApplicationApproval.objects.filter(
        status="pending"
    ).order_by("-created_at")

    school_expenses = SchoolExpense.objects.filter(
        approval_status="pending"
    ).order_by("-created_at")

    transport_expenses = BusExpense.objects.filter(
        status="submitted"
    ).order_by("-created_at")

    pending_leaves = LeaveRequest.objects.filter(
        status="pending"
    ).select_related(
        "user"
    ).order_by("-applied_at")

    bus_issues = BusIssue.objects.exclude(
        status__in=["resolved", "closed"]
    ).select_related(
        "bus"
    ).order_by("-created_at")

    context = {
        "pending_admission_approvals": admission_approvals,
        "admission_approval_count": admission_approvals.count(),
        "pending_school_expenses": school_expenses,
        "school_expense_pending_count": school_expenses.count(),
        "pending_transport_expenses": transport_expenses,
        "transport_expense_pending_count": transport_expenses.count(),
        "pending_leaves": pending_leaves,
        "leave_pending_count": pending_leaves.count(),
        "open_bus_issues": bus_issues,
        "open_bus_issue_count": bus_issues.count(),
        "approval_count": (
            admission_approvals.count()
            + school_expenses.count()
            + transport_expenses.count()
            + pending_leaves.count()
        ),
    }

    return render(
        request,
        "dashboard/chairman/approvals.html",
        context,
    )


# ============================================================
# REPORTS
# ============================================================

@login_required
def chairman_reports(request):

    if not management_user(request):
        return render(
            request,
            "dashboard/403.html",
            status=403,
        )

    today = timezone.localdate()

    students = StudentAdmissionApplication.objects.filter(
        status="account_created"
    )

    employees = EmployeeAdmissionApplication.objects.filter(
        status="account_created"
    )

    attendance = StudentAttendance.objects.filter(
        date=today
    )

    attendance_total = attendance.count()

    attendance_present = attendance.filter(
        status__in=["Present", "Late"]
    ).count()

    attendance_percentage = (
        round(
            attendance_present * 100 / attendance_total,
            1,
        )
        if attendance_total
        else 0
    )

    average = ExamMark.objects.filter(
        status="published"
    ).aggregate(
        average=Avg("percentage")
    )["average"]

    fee_total = _money_total(
        FeePayment.objects.all()
    )

    salary_total = _paid_salary_total()
    expense_total = _approved_expense_total()

    context = {
        "student_count": students.count(),
        "new_admission_count":
            StudentAdmissionApplication.objects.filter(
                submitted_at__date=today
            ).count(),
        "attendance_percentage": attendance_percentage,
        "employee_count": employees.count(),
        "teaching_staff_count":
            employees.filter(
                Q(designation__icontains="teacher")
                | Q(department__icontains="teaching")
            ).count(),
        "class_section_count":
            ClassSection.objects.filter(
                status="Active"
            ).count(),
        "subject_count":
            Subject.objects.filter(
                is_active=True
            ).count(),
        "exam_count": Examination.objects.count(),
        "academic_percentage":
            round(float(average), 1)
            if average is not None
            else 0,
        "fee_total": fee_total,
        "salary_total": salary_total,
        "expense_total": expense_total,
        "income_total": fee_total,
        "bus_count": Bus.objects.count(),
        "active_bus_count":
            Bus.objects.filter(
                is_active=True,
                status="active",
            ).count(),
        "route_count":
            BusRoute.objects.filter(
                is_active=True
            ).count(),
        "approval_count": (
            ApplicationApproval.objects.filter(
                status="pending"
            ).count()
            + SchoolExpense.objects.filter(
                approval_status="pending"
            ).count()
            + BusExpense.objects.filter(
                status="submitted"
            ).count()
            + LeaveRequest.objects.filter(
                status="pending"
            ).count()
        ),
    }

    return render(
        request,
        "dashboard/chairman/reports.html",
        context,
    )
