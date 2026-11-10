from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.utils import timezone
from django.conf import settings
from django.contrib import messages
from accounts.models import UserProfile
from transport.models import (
    Bus,
    StudentBusAssignment,
    BusRoute,
    BusStop
)
from .models import (
    StudentAdmissionApplication,
    EmployeeAdmissionApplication,
    ApplicationApproval,
    ParentStudent,
    StudentCredential,
    EmployeeCredential,
)

from .forms import (
    StudentAdmissionApplicationForm,
    EmployeeAdmissionApplicationForm,
)

from .utils import (
    generate_student_application_id,
    generate_employee_application_id,
    create_user_account,
)
from .notifications import (
    send_credentials_email,
    send_credentials_sms,
)

from accounts.models import UserProfile

def is_admission_staff(user):

    if not user.is_authenticated:
        return False

    try:
        return user.profile.role == "admission_staff"
    except AttributeError:
        return False

EMPLOYEE_STAFF_ROLE_GROUPS = (
    ("Teaching Staff", ("teacher",)),
    ("Admission Staff", ("admission_staff",)),
    (
        "Management Staff",
        (
            "principal",
            "vice_principal",
            "chairman",
            "accountant",
            "system_administrator",
        ),
    ),
    ("Bus Drivers", ("bus_driver",)),
)

def get_employee_staff_role_groups():
    role_labels = dict(UserProfile.ROLE_CHOICES)
    return [
        {
            "label": category,
            "roles": [
                (role, role_labels[role])
                for role in role_values
                if role in role_labels
            ],
        }
        for category, role_values in EMPLOYEE_STAFF_ROLE_GROUPS
    ]

def get_employee_staff_role_values():
    return {
        role
        for category, role_values in EMPLOYEE_STAFF_ROLE_GROUPS
        for role in role_values
        if role in dict(UserProfile.ROLE_CHOICES)
    }

def generate_account_email(application_id):
    """
    Generate institutional email automatically.

    Example:
    APP-STU-2026-0011@smscollege.edu
    APP-EMP-2026-0005@smscollege.edu
    """

    application_number = (
        str(application_id)
        .strip()
        .lower()
    )

    domain = getattr(
        settings,
        "ACCOUNT_EMAIL_DOMAIN",
        "smscollege.edu",
    )

    domain = domain.strip().lower()

    return f"{application_number}@{domain}"

def generate_unique_student_username():

    year = timezone.now().year

    prefix = f"stu{year}"

    existing_users = set(
        User.objects
        .filter(
            username__startswith=prefix
        )
        .values_list(
            "username",
            flat=True
        )
    )

    existing_credentials = set(
        StudentCredential.objects
        .filter(
            username__startswith=prefix
        )
        .values_list(
            "username",
            flat=True
        )
    )

    existing_usernames = (
        existing_users |
        existing_credentials
    )

    number = 1

    while True:

        username = f"{prefix}{number:04d}"

        if username not in existing_usernames:
            return username

        number += 1

@login_required
def admissions_home(request):

    if not is_admission_staff(request.user):

        return HttpResponseForbidden(
            "You do not have permission to access Admissions."
        )

    student_count = (
        StudentAdmissionApplication.objects.count()
    )

    employee_count = (
        EmployeeAdmissionApplication.objects.count()
    )

    pending_students = (
        StudentAdmissionApplication.objects
        .filter(
            status__in=[
                "submitted",
                "system_admin_pending",
                "vp_pending",
            ]
        )
        .count()
    )

    pending_employees = (
        EmployeeAdmissionApplication.objects
        .filter(
            status__in=[
                "submitted",
                "system_admin_pending",
                "vp_pending",
            ]
        )
        .count()
    )

    context = {
        "student_count": student_count,
        "employee_count": employee_count,
        "pending_students": pending_students,
        "pending_employees": pending_employees,
    }

    return render(
        request,
        "admissions/admissions_home.html",
        context,
    )

@login_required
def student_applications(request):

    if not is_admission_staff(request.user):

        return HttpResponseForbidden(
            "You do not have permission to access student applications."
        )

    applications = (
        StudentAdmissionApplication.objects
        .all()
        .order_by("-submitted_at")
    )

    context = {
        "applications": applications,
    }

    return render(
        request,
        "admissions/student_applications.html",
        context,
    )

@login_required
def create_student_application(request):

    if not is_admission_staff(request.user):

        return HttpResponseForbidden(
            "You do not have permission to create student applications."
        )

    if request.method == "POST":

        form = StudentAdmissionApplicationForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():

            with transaction.atomic():

                application = form.save(
                    commit=False
                )

                application.application_id = (
                    generate_student_application_id()
                )

                application.submitted_by = (
                    request.user
                )

                application.status = (
                    "system_admin_pending"
                )

                application.save()

                ApplicationApproval.objects.create(
                    application_type="Student",
                    application_id=(
                        application.application_id
                    ),
                    stage="system_admin",
                    status="pending",
                )

            messages.success(
                request,
                "Student application submitted successfully."
            )

            return redirect(
                "admissions:student_applications"
            )

    else:

        form = StudentAdmissionApplicationForm()

    return render(
        request,
        "admissions/student_application_form.html",
        {
            "form": form,
        },
    )


@login_required
def student_application_detail(request, application_id):

    if not is_admission_staff(request.user):
        return HttpResponseForbidden(
            "You do not have permission to view student applications."
        )

    application = get_object_or_404(
        StudentAdmissionApplication,
        id=application_id,
    )

    account_created = (
        application.status == "account_created"
    )

    return render(
        request,
        "admissions/student_application_detail.html",
        {
            "application": application,
            "account_created": account_created,
        },
    )


@login_required
@transaction.atomic
def student_application_edit(request, application_id):

    # 1. Only Admission Staff can edit
    if not is_admission_staff(request.user):
        return HttpResponseForbidden(
            "You do not have permission to edit student applications."
        )

    # 2. Get existing application
    application = get_object_or_404(
        StudentAdmissionApplication,
        id=application_id,
    )

    # 3. Do not allow editing after account creation
    if application.status == "account_created":
        messages.error(
            request,
            "This application cannot be edited because "
            "the student account has already been created.",
        )
        return redirect(
            "admissions:student_application_detail",
            application_id=application.id,
        )

    # 4. Handle resubmission
    if request.method == "POST":
        form = StudentAdmissionApplicationForm(
            request.POST,
            request.FILES,
            instance=application,
        )

        if form.is_valid():
            updated_application = form.save(commit=False)

            # Always send the edited application to System Admin
            updated_application.status = "system_admin_pending"
            updated_application.save()
            form.save_m2m()

            # 5. Find the latest System Admin approval
            approval = (
                ApplicationApproval.objects
                .filter(
                    application_type="Student",
                    application_id=updated_application.application_id,
                    stage="system_admin",
                )
                .order_by("-created_at")
                .first()
            )

            if approval:
                # Reopen the existing approval
                approval.status = "pending"
                approval.review_comment = ""

                # Clear review details only when these fields
                # allow NULL in your model
                approval.reviewed_by = None
                approval.reviewed_at = None

                approval.save(
                    update_fields=[
                        "status",
                        "review_comment",
                        "reviewed_by",
                        "reviewed_at",
                    ]
                )

            else:
                # Create a new System Admin approval
                ApplicationApproval.objects.create(
                    application_type="Student",
                    application_id=updated_application.application_id,
                    stage="system_admin",
                    status="pending",
                )

            messages.success(
                request,
                "Application resubmitted successfully. "
                "It is now pending System Admin approval.",
            )

            return redirect(
                "admissions:student_application_detail",
                application_id=updated_application.id,
            )

    else:
        form = StudentAdmissionApplicationForm(
            instance=application,
        )

    return render(
        request,
        "admissions/student_application_form.html",
        {
            "application": application,
            "form": form,
            "is_edit": True,
        },
    )

@login_required
def employee_applications(request):

    if not is_admission_staff(request.user):

        return HttpResponseForbidden(
            "You do not have permission to access employee applications."
        )

    applications = (
        EmployeeAdmissionApplication.objects
        .all()
        .order_by("-submitted_at")
    )

    return render(
        request,
        "admissions/employee_applications.html",
        {
            "applications": applications,
        },
    )

@login_required
def create_employee_application(request):

    if not is_admission_staff(request.user):

        return HttpResponseForbidden(
            "You do not have permission to create employee applications."
        )

    if request.method == "POST":

        form = EmployeeAdmissionApplicationForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():

            with transaction.atomic():

                application = form.save(
                    commit=False
                )

                application.application_id = (
                    generate_employee_application_id()
                )

                application.submitted_by = (
                    request.user
                )

                application.status = (
                    "system_admin_pending"
                )

                application.save()

                ApplicationApproval.objects.create(
                    application_type="Employee",
                    application_id=(
                        application.application_id
                    ),
                    stage="system_admin",
                    status="pending",
                )

            messages.success(
                request,
                "Employee application submitted successfully."
            )

            return redirect(
                "admissions:employee_applications"
            )

    else:

        form = EmployeeAdmissionApplicationForm()

    return render(
        request,
        "admissions/employee_application_form.html",
        {
            "form": form,
        },
    )

@login_required
def employee_application_detail(
    request,
    application_id,
):

    if not is_admission_staff(request.user):

        return HttpResponseForbidden(
            "You do not have permission to view employee applications."
        )

    application = get_object_or_404(
        EmployeeAdmissionApplication,
        id=application_id,
    )

    return render(
        request,
        "admissions/employee_application_detail.html",
        {
            "application": application,
        },
    )

@login_required
@transaction.atomic
def employee_application_edit(request, application_id):

    # 1. Only Admission Staff can edit
    if not is_admission_staff(request.user):
        return HttpResponseForbidden(
            "You do not have permission to edit employee applications."
        )

    # 2. Get existing employee application
    application = get_object_or_404(
        EmployeeAdmissionApplication,
        id=application_id,
    )

    # 3. Do not allow editing after account creation
    if application.status == "account_created":
        messages.error(
            request,
            "This application cannot be edited because "
            "the employee account has already been created.",
        )
        return redirect(
            "admissions:employee_application_detail",
            application_id=application.id,
        )

    # 4. Edit and resubmit
    if request.method == "POST":
        form = EmployeeAdmissionApplicationForm(
            request.POST,
            request.FILES,
            instance=application,
        )

        if form.is_valid():
            updated_application = form.save(commit=False)

            # Restart the approval process from System Admin
            updated_application.status = "system_admin_pending"
            updated_application.save()
            form.save_m2m()

            # Find existing System Admin approval
            approval = (
                ApplicationApproval.objects
                .filter(
                    application_type="Employee",
                    application_id=updated_application.application_id,
                    stage="system_admin",
                )
                .order_by("-created_at")
                .first()
            )

            if approval:
                # Reopen System Admin approval
                approval.status = "pending"
                approval.review_comment = ""

                # These assignments require nullable model fields
                approval.reviewed_by = None
                approval.reviewed_at = None

                approval.save(
                    update_fields=[
                        "status",
                        "review_comment",
                        "reviewed_by",
                        "reviewed_at",
                    ]
                )
            else:
                # Create approval if one does not exist
                ApplicationApproval.objects.create(
                    application_type="Employee",
                    application_id=updated_application.application_id,
                    stage="system_admin",
                    status="pending",
                )

            messages.success(
                request,
                "Employee application updated successfully. "
                "It is now pending System Admin approval.",
            )

            return redirect(
                "admissions:employee_application_detail",
                application_id=updated_application.id,
            )

    else:
        form = EmployeeAdmissionApplicationForm(
            instance=application,
        )

    return render(
        request,
        "admissions/employee_application_form.html",
        {
            "application": application,
            "form": form,
            "is_edit": True,
        },
    )


@login_required
def system_admin_approvals(request):

    if request.user.profile.role != "system_administrator":

        return HttpResponseForbidden(
            "You do not have permission to access approvals."
        )

    # -----------------------------------------------------
    # STUDENT
    # -----------------------------------------------------

    student_approvals = (
        ApplicationApproval.objects
        .filter(
            application_type="Student",
            stage="system_admin",
            status="pending",
        )
        .order_by("-created_at")
    )

    for approval in student_approvals:

        approval.application = (
            StudentAdmissionApplication.objects
            .filter(
                application_id=approval.application_id
            )
            .first()
        )

    # -----------------------------------------------------
    # EMPLOYEE
    # -----------------------------------------------------

    employee_approvals = (
        ApplicationApproval.objects
        .filter(
            application_type="Employee",
            stage="system_admin",
            status="pending",
        )
        .order_by("-created_at")
    )

    for approval in employee_approvals:

        approval.application = (
            EmployeeAdmissionApplication.objects
            .filter(
                application_id=approval.application_id
            )
            .first()
        )

    student_count = student_approvals.count()

    employee_count = employee_approvals.count()

    total_count = (
        student_count +
        employee_count
    )

    context = {
        "student_approvals": student_approvals,
        "employee_approvals": employee_approvals,
        "student_count": student_count,
        "employee_count": employee_count,
        "total_count": total_count,
    }

    return render(
        request,
        "admissions/system_admin/approvals.html",
        context,
    )


# =========================================================
# SYSTEM ADMIN STUDENT APPROVAL DETAIL
# =========================================================

@login_required
def system_admin_student_approval_detail(
    request,
    approval_id,
):

    if request.user.profile.role != "system_administrator":

        return HttpResponseForbidden(
            "You do not have permission to view this application."
        )

    approval = get_object_or_404(
        ApplicationApproval,
        id=approval_id,
        application_type="Student",
        stage="system_admin",
        status="pending",
    )

    application = get_object_or_404(
        StudentAdmissionApplication,
        application_id=approval.application_id,
    )

    return render(
        request,
        "admissions/system_admin/student_approval_detail.html",
        {
            "approval": approval,
            "application": application,
        },
    )


# =========================================================
# SYSTEM ADMIN EMPLOYEE APPROVAL DETAIL
# =========================================================

@login_required
def system_admin_employee_approval_detail(
    request,
    approval_id,
):

    if request.user.profile.role != "system_administrator":

        return HttpResponseForbidden(
            "You do not have permission to view this application."
        )

    approval = get_object_or_404(
        ApplicationApproval,
        id=approval_id,
        application_type="Employee",
        stage="system_admin",
        status="pending",
    )

    application = get_object_or_404(
        EmployeeAdmissionApplication,
        application_id=approval.application_id,
    )

    return render(
        request,
        "admissions/system_admin/employee_approval_detail.html",
        {
            "approval": approval,
            "application": application,
        },
    )


# =========================================================
# SYSTEM ADMIN ACCEPT STUDENT
# =========================================================

@login_required
@transaction.atomic
def system_admin_accept_student(
    request,
    approval_id,
):

    if request.user.profile.role != "system_administrator":

        return HttpResponseForbidden(
            "You do not have permission to accept student applications."
        )

    approval = get_object_or_404(
        ApplicationApproval,
        id=approval_id,
        application_type="Student",
        stage="system_admin",
        status="pending",
    )

    application = get_object_or_404(
        StudentAdmissionApplication,
        application_id=approval.application_id,
    )

    if request.method != "POST":

        return redirect(
            "admissions:system_admin_student_approval_detail",
            approval_id=approval.id,
        )

    approval.status = "accepted"

    approval.reviewed_by = request.user

    approval.reviewed_at = timezone.now()

    approval.review_comment = (
        request.POST.get(
            "review_comment",
            ""
        ).strip()
        or "Application accepted by System Administrator."
    )

    approval.save()

    application.status = "vp_pending"

    application.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    ApplicationApproval.objects.create(
        application_type="Student",
        application_id=application.application_id,
        stage="vice_principal",
        status="pending",
    )

    messages.success(
        request,
        "Student application moved to Vice Principal approval."
    )

    return redirect(
        "admissions:system_admin_approvals"
    )


# =========================================================
# SYSTEM ADMIN REJECT STUDENT
# =========================================================

@login_required
@transaction.atomic
def system_admin_reject_student(
    request,
    approval_id,
):

    if request.user.profile.role != "system_administrator":

        return HttpResponseForbidden(
            "You do not have permission to reject student applications."
        )

    if request.method != "POST":

        return redirect(
            "admissions:system_admin_approvals"
        )

    approval = get_object_or_404(
        ApplicationApproval,
        id=approval_id,
        application_type="Student",
        stage="system_admin",
        status="pending",
    )

    application = get_object_or_404(
        StudentAdmissionApplication,
        application_id=approval.application_id,
    )

    review_comment = request.POST.get(
        "review_comment",
        ""
    ).strip()

    if not review_comment:

        review_comment = (
            "Application rejected by System Administrator."
        )

    approval.status = "rejected"

    approval.reviewed_by = request.user

    approval.reviewed_at = timezone.now()

    approval.review_comment = review_comment

    approval.save()

    application.status = "system_admin_rejected"

    application.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    messages.success(
        request,
        "Student application rejected successfully."
    )

    return redirect(
        "admissions:system_admin_approvals"
    )


# =========================================================
# SYSTEM ADMIN ACCEPT EMPLOYEE
# =========================================================

@login_required
@transaction.atomic
def system_admin_accept_employee(
    request,
    approval_id,
):

    if request.user.profile.role != "system_administrator":

        return HttpResponseForbidden(
            "You do not have permission to accept employee applications."
        )

    approval = get_object_or_404(
        ApplicationApproval,
        id=approval_id,
        application_type="Employee",
        stage="system_admin",
        status="pending",
    )

    application = get_object_or_404(
        EmployeeAdmissionApplication,
        application_id=approval.application_id,
    )

    if request.method != "POST":

        return redirect(
            "admissions:system_admin_employee_approval_detail",
            approval_id=approval.id,
        )

    approval.status = "accepted"

    approval.reviewed_by = request.user

    approval.reviewed_at = timezone.now()

    approval.review_comment = (
        request.POST.get(
            "review_comment",
            ""
        ).strip()
        or "Application accepted by System Administrator."
    )

    approval.save()

    application.status = "vp_pending"

    application.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    ApplicationApproval.objects.create(
        application_type="Employee",
        application_id=application.application_id,
        stage="vice_principal",
        status="pending",
    )

    messages.success(
        request,
        "Employee application moved to Vice Principal approval."
    )

    return redirect(
        "admissions:system_admin_approvals"
    )


# =========================================================
# SYSTEM ADMIN REJECT EMPLOYEE
# =========================================================

@login_required
@transaction.atomic
def system_admin_reject_employee(
    request,
    approval_id,
):

    if request.user.profile.role != "system_administrator":

        return HttpResponseForbidden(
            "You do not have permission to reject employee applications."
        )

    if request.method != "POST":

        return redirect(
            "admissions:system_admin_approvals"
        )

    approval = get_object_or_404(
        ApplicationApproval,
        id=approval_id,
        application_type="Employee",
        stage="system_admin",
        status="pending",
    )

    application = get_object_or_404(
        EmployeeAdmissionApplication,
        application_id=approval.application_id,
    )

    review_comment = request.POST.get(
        "review_comment",
        ""
    ).strip()

    if not review_comment:

        review_comment = (
            "Application rejected by System Administrator."
        )

    approval.status = "rejected"

    approval.reviewed_by = request.user

    approval.reviewed_at = timezone.now()

    approval.review_comment = review_comment

    approval.save()

    application.status = "system_admin_rejected"

    application.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    messages.success(
        request,
        "Employee application rejected successfully."
    )

    return redirect(
        "admissions:system_admin_approvals"
    )


# =========================================================
# VP STUDENT APPROVALS
# =========================================================

@login_required
def vp_student_approvals(request):

    if request.user.profile.role != "vice_principal":

        return HttpResponseForbidden(
            "You do not have permission to access student approvals."
        )

    approvals = (
        ApplicationApproval.objects
        .filter(
            application_type="Student",
            stage="vice_principal",
            status="pending",
        )
        .order_by("-created_at")
    )

    for approval in approvals:

        approval.application = (
            StudentAdmissionApplication.objects
            .filter(
                application_id=approval.application_id
            )
            .first()
        )

    return render(
        request,
        "admissions/vp/student_approvals.html",
        {
            "approvals": approvals,
            "approval_type": "Student",
            "total_count": approvals.count(),
        },
    )


# =========================================================
# VP EMPLOYEE APPROVALS
# =========================================================

@login_required
def vp_employee_approvals(request):

    if request.user.profile.role != "vice_principal":

        return HttpResponseForbidden(
            "You do not have permission to access employee approvals."
        )

    approvals = (
        ApplicationApproval.objects
        .filter(
            application_type="Employee",
            stage="vice_principal",
            status="pending",
        )
        .order_by("-created_at")
    )

    for approval in approvals:

        approval.application = (
            EmployeeAdmissionApplication.objects
            .filter(
                application_id=approval.application_id
            )
            .first()
        )

    return render(
        request,
        "admissions/vp/employee_approvals.html",
        {
            "approvals": approvals,
            "approval_type": "Employee",
            "total_count": approvals.count(),
        },
    )


# =========================================================
# VP STUDENT APPROVAL DETAIL
# =========================================================

@login_required
def vp_student_approval_detail(
    request,
    approval_id,
):

    if request.user.profile.role != "vice_principal":

        return HttpResponseForbidden(
            "You do not have permission to view this application."
        )

    approval = get_object_or_404(
        ApplicationApproval,
        id=approval_id,
        application_type="Student",
        stage="vice_principal",
        status="pending",
    )

    application = get_object_or_404(
        StudentAdmissionApplication,
        application_id=approval.application_id,
    )

    return render(
        request,
        "admissions/vp/student_approval_detail.html",
        {
            "approval": approval,
            "application": application,
        },
    )

@login_required
def vp_employee_approval_detail(
    request,
    approval_id,
):

    if request.user.profile.role != "vice_principal":

        return HttpResponseForbidden(
            "You do not have permission to view this application."
        )

    approval = get_object_or_404(
        ApplicationApproval,
        id=approval_id,
        application_type="Employee",
        stage="vice_principal",
        status="pending",
    )

    application = get_object_or_404(
        EmployeeAdmissionApplication,
        application_id=approval.application_id,
    )

    return render(
        request,
        "admissions/vp/employee_approval_detail.html",
        {
            "approval": approval,
            "application": application,
            "employee_staff_role_groups": get_employee_staff_role_groups(),
        },
    )

@login_required
@transaction.atomic
def vp_approve_student(request, approval_id):

    print("\n" + "=" * 70)
    print("VP APPROVAL STARTED")
    print("APPROVAL ID:", approval_id)
    print("=" * 70)

    # =====================================================
    # 1. REQUEST METHOD
    # =====================================================

    if request.method != "POST":
        return redirect(
            "admissions:vp_student_approvals"
        )

    # =====================================================
    # 2. VP ROLE CHECK
    # =====================================================

    if not hasattr(request.user, "profile"):
        return HttpResponseForbidden(
            "User profile not found."
        )

    if request.user.profile.role != "vice_principal":
        return HttpResponseForbidden(
            "Only Vice Principal can approve students."
        )

    # =====================================================
    # 3. GET VP APPROVAL
    # =====================================================

    approval = get_object_or_404(
        ApplicationApproval,
        id=approval_id,
        application_type="Student",
        stage="vice_principal",
        status="pending",
    )

    print(
        "Approval found:",
        approval.id
    )

    print(
        "Application ID:",
        approval.application_id
    )

    print(
        "Approval status:",
        approval.status
    )

    # =====================================================
    # 4. GET STUDENT APPLICATION
    # =====================================================

    application = get_object_or_404(
        StudentAdmissionApplication,
        application_id=approval.application_id,
    )

    print(
        "Student application found:",
        application.application_id
    )

    # =====================================================
    # 5. PREVENT DUPLICATE APPROVAL
    # =====================================================

    if application.status == "account_created":

        messages.info(
            request,
            "Student account has already been created."
        )

        return redirect(
            "admissions:vp_student_approvals"
        )

    # =====================================================
    # 6. BUS VALIDATION
    # =====================================================

    assigned_bus = None

    if application.bus_required:

        print(
            "Bus required: YES"
        )

        # -------------------------------------------------
        # CHECK ROUTE
        # -------------------------------------------------

        if not application.bus_route:

            messages.error(
                request,
                (
                    "Bus is required but no bus route "
                    "is selected."
                )
            )

            return redirect(
                "admissions:vp_student_approvals"
            )

        print(
            "Selected route:",
            application.bus_route.route_name
        )

        # -------------------------------------------------
        # FIND ACTIVE BUS
        # -------------------------------------------------

        assigned_bus = (
            Bus.objects
            .filter(
                route=application.bus_route,
                is_active=True,
                status="active",
            )
            .first()
        )

        if not assigned_bus:

            messages.error(
                request,
                (
                    "No active bus is assigned to the "
                    "selected route. Please assign a bus "
                    "to this route first."
                )
            )

            return redirect(
                "admissions:vp_student_approvals"
            )

        print(
            "Bus found:",
            assigned_bus.bus_number
        )

        # -------------------------------------------------
        # CHECK PICKUP STOP
        # -------------------------------------------------

        if application.pickup_stop:

            if (
                application.pickup_stop.route_id
                != application.bus_route.id
            ):

                messages.error(
                    request,
                    (
                        "Selected pickup stop does not "
                        "belong to the selected route."
                    )
                )

                return redirect(
                    "admissions:vp_student_approvals"
                )

    else:

        print(
            "Bus required: NO"
        )

    # =====================================================
    # 7. GENERATE STUDENT SCHOOL EMAIL
    # =====================================================

    account_email = generate_account_email(
        application.application_id
    )

    print(
        "Student school email:",
        account_email
    )

    # =====================================================
    # 8. STUDENT INITIAL PASSWORD
    # =====================================================

    initial_password = getattr(
        settings,
        "STUDENT_INITIAL_PASSWORD",
        "Student@2026",
    )

    print(
        "Student initial password configured."
    )

    # =====================================================
    # 9. CREATE / GET STUDENT USER
    # =====================================================

    print(
        "Creating/finding student user..."
    )

    user, profile, user_created = (
        create_user_account(
            application=application,
            role="student",
            username_prefix="stu",
            default_password=initial_password,
        )
    )

    print(
        "Student username:",
        user.username
    )

    print(
        "Student user created:",
        user_created
    )

    # =====================================================
    # 10. UPDATE STUDENT USER
    # =====================================================

    user.first_name = (
        application.first_name or ""
    )

    user.last_name = (
        application.last_name or ""
    )

    # IMPORTANT:
    # User email is student's personal/application email.
    # School email is stored separately in StudentCredential.

    user.email = (
        application.email or ""
    ).strip().lower()

    user.is_active = True

    user.save()

    print(
        "Student User ready."
    )

    # =====================================================
    # 11. UPDATE STUDENT PROFILE
    # =====================================================

    profile.role = "student"
    profile.is_active = True
    profile.phone = application.phone

    profile.save()

    print(
        "Student Profile ready."
    )

    # =====================================================
    # 12. STUDENT CREDENTIAL
    # =====================================================

    print(
        "Creating/finding student credential..."
    )

    # -----------------------------------------------------
    # FIND BY APPLICATION
    # -----------------------------------------------------

    credential = (
        StudentCredential.objects
        .filter(
            student_application=application
        )
        .first()
    )

    # -----------------------------------------------------
    # IF NOT FOUND, FIND BY USERNAME
    # -----------------------------------------------------

    if credential is None:

        credential = (
            StudentCredential.objects
            .filter(
                username=user.username
            )
            .first()
        )

    # -----------------------------------------------------
    # UPDATE EXISTING CREDENTIAL
    # -----------------------------------------------------

    if credential:

        print(
            "Existing StudentCredential found:",
            credential.id
        )

        credential.student_application = application
        credential.user = user
        credential.username = user.username
        credential.account_email = account_email
        credential.temporary_password = initial_password
        credential.is_active = True

        credential.save()

    # -----------------------------------------------------
    # CREATE NEW CREDENTIAL
    # -----------------------------------------------------

    else:

        credential = (
            StudentCredential.objects.create(
                student_application=application,
                user=user,
                username=user.username,
                account_email=account_email,
                temporary_password=initial_password,
                is_active=True,
            )
        )

        print(
            "New StudentCredential created:",
            credential.id
        )

    print(
        "Student credential ready:",
        credential.id
    )

    # =====================================================
    # 13. CREATE / GET SEPARATE PARENT ACCOUNT
    # =====================================================

    parent_user = None
    parent_username = None
    parent_password = None

    if application.parent_email:

        parent_email = (
            application.parent_email
            .strip()
            .lower()
        )

        print(
            "Parent email:",
            parent_email
        )

        # -------------------------------------------------
        # PARENT PASSWORD
        # -------------------------------------------------

        parent_password = getattr(
            settings,
            "PARENT_INITIAL_PASSWORD",
            "Parent@2026",
        )

        # -------------------------------------------------
        # IMPORTANT
        # NEVER USE STUDENT USER AS PARENT
        # -------------------------------------------------

        parent_user = (
            User.objects
            .filter(
                email__iexact=parent_email
            )
            .exclude(
                id=user.id
            )
            .first()
        )

        # -------------------------------------------------
        # CREATE NEW PARENT
        # -------------------------------------------------

        if parent_user is None:

            parent_username = (
                f"parent_{user.username}"
            )

            counter = 1

            while User.objects.filter(
                username=parent_username
            ).exists():

                parent_username = (
                    f"parent_{user.username}_{counter}"
                )

                counter += 1

            parent_user = User.objects.create_user(
                username=parent_username,
                email=parent_email,
                password=parent_password,
                first_name=(
                    application.father_name
                    or application.mother_name
                    or "Parent"
                ),
            )

            parent_user.is_active = True

            parent_user.save()

            print(
                "New parent account created:",
                parent_username
            )

        # -------------------------------------------------
        # EXISTING PARENT
        # -------------------------------------------------

        else:

            parent_username = (
                parent_user.username
            )

            # Reset password so we know the
            # password that will be emailed.

            parent_user.set_password(
                parent_password
            )

            parent_user.is_active = True

            parent_user.save()

            print(
                "Existing parent account found:",
                parent_username
            )

            print(
                "Parent password reset."
            )

        # =================================================
        # 14. PARENT PROFILE
        # =================================================

        parent_profile, _ = (
            UserProfile.objects.get_or_create(
                user=parent_user,
                defaults={
                    "role": "parent",
                    "phone": application.parent_phone,
                    "is_active": True,
                },
            )
        )

        parent_profile.role = "parent"

        parent_profile.phone = (
            application.parent_phone
        )

        parent_profile.is_active = True

        parent_profile.save()

        print(
            "Parent profile ready."
        )

    else:

        print(
            "No parent email provided."
        )

    # =====================================================
    # 15. LINK PARENT WITH STUDENT
    # =====================================================

    if parent_user:

        ParentStudent.objects.update_or_create(
            parent=parent_user,
            student=application,
            defaults={
                "relationship": "Parent",
                "is_active": True,
            },
        )

        print(
            "Parent linked with student."
        )

    # =====================================================
    # 16. AUTOMATIC BUS ASSIGNMENT
    # =====================================================

    if (
        application.bus_required
        and assigned_bus
    ):

        bus_assignment, created = (
            StudentBusAssignment.objects
            .update_or_create(
                student=application,
                defaults={
                    "bus": assigned_bus,
                    "route": application.bus_route,
                    "pickup_stop": application.pickup_stop,
                    "pickup_required": True,
                    "drop_required": False,
                    "is_active": True,
                    "assigned_date": timezone.localdate(),
                },
            )
        )

        print(
            "Bus assignment ready:",
            bus_assignment.id
        )

        print(
            "Bus:",
            assigned_bus.bus_number
        )

    # =====================================================
    # 17. UPDATE APPLICATION STATUS
    # =====================================================

    application.status = "account_created"

    application.save()

    print(
        "Application status:",
        application.status
    )

    # =====================================================
    # 18. ACCEPT VP APPROVAL
    # =====================================================

    approval.status = "accepted"

    approval.reviewed_by = request.user

    approval.reviewed_at = timezone.now()

    approval.review_comment = (
        request.POST.get(
            "review_comment",
            ""
        ).strip()
        or
        "Student application approved by Vice Principal."
    )

    approval.save()

    print(
        "VP approval saved."
    )

    # =====================================================
    # 19. VERIFY APPROVAL
    # =====================================================

    approval.refresh_from_db()

    print(
        "FINAL VP APPROVAL STATUS:",
        approval.status
    )

    if approval.status != "accepted":

        raise Exception(
            "VP approval was not saved correctly."
        )

    # =====================================================
    # 20. SEND STUDENT CREDENTIAL EMAIL
    # =====================================================

    if application.email:

        try:

            print("\n" + "=" * 70)
            print("SENDING STUDENT CREDENTIAL EMAIL")
            print("=" * 70)

            print(
                "Student email:",
                application.email
            )

            print(
                "Student username:",
                user.username
            )

            print(
                "Student school email:",
                account_email
            )

            print(
                "Student password:",
                initial_password
            )

            send_credentials_email(
                email=application.email,
                first_name=(
                    application.first_name
                    or "Student"
                ),
                username=user.username,
                password=initial_password,
                role="Student",
                account_email=account_email,
            )

            print(
                "Student credential email sent."
            )

        except Exception as e:

            print(
                "Student email error:",
                repr(e)
            )

    else:

        print(
            "Student email not available."
        )

    # =====================================================
    # 21. SEND STUDENT SMS
    # =====================================================

    if application.phone:

        try:

            print("\n" + "=" * 70)
            print("SENDING STUDENT CREDENTIAL SMS")
            print("=" * 70)

            send_credentials_sms(
                phone=application.phone,
                username=user.username,
                email=account_email,
                password=initial_password,
            )

            print(
                "Student SMS sent."
            )

        except Exception as e:

            print(
                "Student SMS error:",
                repr(e)
            )

    # =====================================================
    # 22. SEND PARENT CREDENTIAL EMAIL
    # =====================================================

    if (
        parent_user
        and parent_username
        and parent_password
        and application.parent_email
    ):

        try:

            print("\n" + "=" * 70)
            print("SENDING PARENT CREDENTIAL EMAIL")
            print("=" * 70)

            print(
                "Parent email:",
                application.parent_email
            )

            print(
                "Parent username:",
                parent_username
            )

            print(
                "Parent password:",
                parent_password
            )

            send_credentials_email(
                email=application.parent_email,
                first_name=(
                    application.father_name
                    or application.mother_name
                    or "Parent"
                ),
                username=parent_username,
                password=parent_password,
                role="Parent",
                account_email=parent_user.email,
            )

            print(
                "Parent credential email sent."
            )

        except Exception as e:

            print(
                "Parent email error:",
                repr(e)
            )

    else:

        print(
            "Parent credential email skipped."
        )

    # =====================================================
    # 23. SEND PARENT SMS
    # =====================================================

    if (
        parent_user
        and parent_username
        and parent_password
        and application.parent_phone
    ):

        try:

            print("\n" + "=" * 70)
            print("SENDING PARENT CREDENTIAL SMS")
            print("=" * 70)

            send_credentials_sms(
                phone=application.parent_phone,
                username=parent_username,
                email=parent_user.email,
                password=parent_password,
            )

            print(
                "Parent SMS sent."
            )

        except Exception as e:

            print(
                "Parent SMS error:",
                repr(e)
            )

    # =====================================================
    # 24. SUCCESS MESSAGE
    # =====================================================

    messages.success(
        request,
        (
            "Student approved successfully. "
            "Separate student and parent accounts "
            "have been created."
        )
    )

    # =====================================================
    # 25. FINAL LOG
    # =====================================================

    print("\n" + "=" * 70)

    print(
        "VP APPROVAL COMPLETED SUCCESSFULLY"
    )

    print(
        "APPLICATION:",
        application.application_id
    )

    print(
        "APPROVAL:",
        approval.id
    )

    print(
        "STUDENT USERNAME:",
        user.username
    )

    print(
        "STUDENT SCHOOL EMAIL:",
        account_email
    )

    if parent_user:

        print(
            "PARENT USERNAME:",
            parent_username
        )

        print(
            "PARENT EMAIL:",
            parent_user.email
        )

    print(
        "APPROVAL STATUS:",
        approval.status
    )

    print(
        "=" * 70 + "\n"
    )

    # =====================================================
    # 26. REDIRECT
    # =====================================================

    return redirect(
        "admissions:vp_student_approvals"
    )

@login_required
@transaction.atomic
def vp_reject_student(
    request,
    approval_id,
):

    if not hasattr(request.user, "profile"):

        return HttpResponseForbidden(
            "User profile not found."
        )

    if request.user.profile.role != "vice_principal":

        return HttpResponseForbidden(
            "You do not have permission to reject student applications."
        )

    if request.method != "POST":

        return redirect(
            "admissions:vp_student_approvals"
        )

    approval = get_object_or_404(
        ApplicationApproval,
        id=approval_id,
        application_type="Student",
        stage="vice_principal",
        status="pending",
    )

    application = get_object_or_404(
        StudentAdmissionApplication,
        application_id=approval.application_id,
    )

    review_comment = request.POST.get(
        "review_comment",
        ""
    ).strip()

    if not review_comment:

        review_comment = (
            "Application rejected by Vice Principal."
        )

    approval.status = "rejected"

    approval.reviewed_by = request.user

    approval.reviewed_at = timezone.now()

    approval.review_comment = review_comment

    approval.save()

    application.status = "vp_rejected"

    application.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    messages.success(
        request,
        "Student application rejected successfully."
    )

    return redirect(
        "admissions:vp_student_approvals"
    )

@login_required
@transaction.atomic
def vp_approve_employee(
    request,
    approval_id,
):

    # -----------------------------------------------------
    # ROLE CHECK
    # -----------------------------------------------------

    if not hasattr(request.user, "profile"):

        return HttpResponseForbidden(
            "User profile not found."
        )

    if request.user.profile.role != "vice_principal":

        return HttpResponseForbidden(
            "Only Vice Principal can approve employees."
        )

    # -----------------------------------------------------
    # POST ONLY
    # -----------------------------------------------------

    if request.method != "POST":

        return redirect(
            "admissions:vp_employee_approvals"
        )

    # -----------------------------------------------------
    # APPROVAL
    # -----------------------------------------------------

    approval = get_object_or_404(
        ApplicationApproval,
        id=approval_id,
        application_type="Employee",
        stage="vice_principal",
        status="pending",
    )

    # -----------------------------------------------------
    # APPLICATION
    # -----------------------------------------------------

    application = get_object_or_404(
        EmployeeAdmissionApplication,
        application_id=approval.application_id,
    )

    staff_role = (
        request.POST.get("staff_role", "").strip()
        or application.staff_role
        or ""
    )
    if staff_role not in get_employee_staff_role_values():
        return HttpResponseBadRequest(
            "Select a valid employee staff role before approval."
        )

    # -----------------------------------------------------
    # SCHOOL EMAIL
    # -----------------------------------------------------

    account_email = generate_account_email(
        application.application_id
    )

    # -----------------------------------------------------
    # PASSWORD
    # -----------------------------------------------------

    initial_password = getattr(
        settings,
        "EMPLOYEE_INITIAL_PASSWORD",
        "Employee@123",
    )

    # -----------------------------------------------------
    # CREATE USER
    # -----------------------------------------------------

    user, profile, created = create_user_account(
        application=application,
        role=staff_role,
        username_prefix="emp",
        default_password=initial_password,
    )

    # -----------------------------------------------------
    # UPDATE USER
    # -----------------------------------------------------

    user.first_name = (
        application.first_name or ""
    )

    user.last_name = (
        application.last_name or ""
    )

    user.email = (
        application.email or ""
    ).strip().lower()

    user.is_active = True

    user.save(
        update_fields=[
            "first_name",
            "last_name",
            "email",
            "is_active",
        ]
    )

    # -----------------------------------------------------
    # UPDATE PROFILE
    # -----------------------------------------------------

    profile.role = staff_role

    profile.is_active = True

    if hasattr(profile, "phone"):

        profile.phone = application.phone

    profile.save()

    # -----------------------------------------------------
    # EMPLOYEE CREDENTIAL
    #
    # IMPORTANT:
    # employee_application is the model field.
    # -----------------------------------------------------

    credential, credential_created = (
        EmployeeCredential.objects
        .update_or_create(
            employee_application=application,
            defaults={
                "user": user,
                "username": user.username,
                "account_email": account_email,
                "temporary_password": initial_password,
                "is_active": True,
            },
        )
    )

    # -----------------------------------------------------
    # EMAIL
    # -----------------------------------------------------

    email_sent = False

    if application.email:

        email_sent = send_credentials_email(
            email=application.email,
            first_name=application.first_name,
            username=user.username,
            password=initial_password,
            role=dict(UserProfile.ROLE_CHOICES)[staff_role],
            account_email=account_email,
        )

    # -----------------------------------------------------
    # SMS
    # -----------------------------------------------------

    sms_sent = False

    if application.phone:

        sms_sent = send_credentials_sms(
            phone=application.phone,
            username=user.username,
            email=account_email,
            password=initial_password,
        )

    # -----------------------------------------------------
    # APPROVAL UPDATE
    # -----------------------------------------------------

    approval.status = "accepted"

    approval.reviewed_by = request.user

    approval.reviewed_at = timezone.now()

    approval.review_comment = (
        request.POST.get(
            "review_comment",
            ""
        ).strip()
        or (
            "Employee application approved by Vice Principal as "
            f"{dict(UserProfile.ROLE_CHOICES)[staff_role]}."
        )
    )

    approval.save()

    # -----------------------------------------------------
    # APPLICATION STATUS
    # -----------------------------------------------------

    application.status = "account_created"
    application.staff_role = staff_role

    application.save(
        update_fields=[
            "status",
            "staff_role",
            "updated_at",
        ]
    )

    # -----------------------------------------------------
    # SUCCESS
    # -----------------------------------------------------

    messages.success(
        request,
        (
            "Employee account created successfully. "
            f"Username: {user.username} | "
            f"School Email: {account_email}"
        ),
    )

    return redirect(
        "admissions:vp_employee_approvals"
    )

@login_required
@transaction.atomic
def vp_reject_employee(
    request,
    approval_id,
):

    if not hasattr(request.user, "profile"):

        return HttpResponseForbidden(
            "User profile not found."
        )

    if request.user.profile.role != "vice_principal":

        return HttpResponseForbidden(
            "You do not have permission to reject employee applications."
        )

    if request.method != "POST":

        return redirect(
            "admissions:vp_employee_approvals"
        )

    approval = get_object_or_404(
        ApplicationApproval,
        id=approval_id,
        application_type="Employee",
        stage="vice_principal",
        status="pending",
    )

    application = get_object_or_404(
        EmployeeAdmissionApplication,
        application_id=approval.application_id,
    )

    review_comment = request.POST.get(
        "review_comment",
        ""
    ).strip()

    if not review_comment:

        review_comment = (
            "Application rejected by Vice Principal."
        )

    approval.status = "rejected"

    approval.reviewed_by = request.user

    approval.reviewed_at = timezone.now()

    approval.review_comment = review_comment

    approval.save()

    application.status = "vp_rejected"

    application.save(
        update_fields=[
            "status",
            "updated_at",
        ]
    )

    messages.success(
        request,
        "Employee application rejected successfully."
    )

    return redirect(
        "admissions:vp_employee_approvals"
    )


@login_required
def system_admin_user_credentials(request):

    # =========================================================
    # 1. SYSTEM ADMIN PERMISSION
    # =========================================================

    if not hasattr(request.user, "profile"):
        return HttpResponseForbidden("User profile not found.")

    if request.user.profile.role != "system_administrator":
        return HttpResponseForbidden(
            "You do not have permission to view user credentials."
        )

    # =========================================================
    # 2. FETCH CREDENTIALS
    # =========================================================

    employee_credentials = (
        EmployeeCredential.objects
        .select_related("employee_application", "user")
        .order_by("-created_at")
    )

    student_credentials = (
        StudentCredential.objects
        .select_related("student_application", "user")
        .order_by("-created_at")
    )

    employee_count = employee_credentials.count()
    student_count = student_credentials.count()

    # =========================================================
    # 3. HELPER: READ BUS DETAILS
    # =========================================================

    def get_bus_details(assignment):
        bus_number = "—"
        route_name = "—"
        pickup_stop = "—"

        if not assignment:
            return bus_number, route_name, pickup_stop

        bus = getattr(assignment, "bus", None)
        route = getattr(assignment, "route", None)
        stop = getattr(assignment, "pickup_stop", None)

        if bus:
            bus_number = (
                getattr(bus, "bus_number", None)
                or getattr(bus, "registration_number", None)
                or "—"
            )

        if route:
            route_name = (
                getattr(route, "route_name", None)
                or getattr(route, "name", None)
                or "—"
            )

        if stop:
            pickup_stop = (
                getattr(stop, "stop_name", None)
                or getattr(stop, "name", None)
                or "—"
            )

        return bus_number, route_name, pickup_stop

    # =========================================================
    # 4. EMPLOYEE ACCOUNT DETAILS
    # =========================================================

    employee_accounts = []

    for credential in employee_credentials:

        application = credential.employee_application
        employee_user = credential.user

        employee_name = (
            f"{getattr(application, 'first_name', '') or ''} "
            f"{getattr(application, 'last_name', '') or ''}"
        ).strip()

        if not employee_name:
            employee_name = (
                f"{getattr(employee_user, 'first_name', '') or ''} "
                f"{getattr(employee_user, 'last_name', '') or ''}"
            ).strip()

        if not employee_name:
            employee_name = (
                getattr(employee_user, "username", None) or "—"
            )

        application_id = (
            getattr(application, "application_id", None) or "—"
        )

        designation = (
            getattr(application, "designation", None)
            or getattr(application, "employee_type", None)
            or getattr(application, "position", None)
            or getattr(application, "job_role", None)
            or getattr(application, "role", None)
            or "—"
        )

        username = (
            getattr(credential, "username", None)
            or getattr(employee_user, "username", None)
            or "—"
        )

        school_email = (
            getattr(credential, "account_email", None)
            or "—"
        )

        created_at = getattr(credential, "created_at", None)

        account_status = "Active"

        if not getattr(employee_user, "is_active", True):
            account_status = "Inactive"
        elif not getattr(credential, "is_active", True):
            account_status = "Inactive"

        # -----------------------------------------------------
        # EMPLOYEE BUS DETAILS
        # -----------------------------------------------------
        # IMPORTANT:
        # Employee bus assignment model/relationship was not
        # included in the supplied code. Do not query a guessed
        # model here. These values remain blank until the actual
        # employee assignment model is connected.

        bus_number = "—"
        route_name = "—"
        pickup_stop = "—"

        employee_accounts.append({
            "application_id": application_id,
            "employee_name": employee_name,
            "designation": designation,
            "username": username,
            "school_email": school_email,
            "bus_number": bus_number,
            "route_name": route_name,
            "pickup_stop": pickup_stop,
            "created_at": created_at,
            "status": account_status,
        })

    # =========================================================
    # 5. STUDENT ACCOUNT DETAILS
    # =========================================================

    student_accounts = []

    for credential in student_credentials:

        application = credential.student_application
        student_user = credential.user

        student_name = (
            f"{getattr(application, 'first_name', '') or ''} "
            f"{getattr(application, 'last_name', '') or ''}"
        ).strip()

        if not student_name:
            student_name = (
                f"{getattr(student_user, 'first_name', '') or ''} "
                f"{getattr(student_user, 'last_name', '') or ''}"
            ).strip()

        if not student_name:
            student_name = "—"

        admission_id = (
            getattr(application, "admission_id", None)
            or getattr(application, "admission_number", None)
            or "—"
        )

        application_id = (
            getattr(application, "application_id", None) or "—"
        )

        student_username = (
            getattr(credential, "username", None)
            or getattr(student_user, "username", None)
            or "—"
        )

        school_email = (
            getattr(credential, "account_email", None)
            or "—"
        )

        # Student account creation date
        created_at = getattr(credential, "created_at", None)

        # -----------------------------------------------------
        # PARENT DETAILS
        # -----------------------------------------------------

        parent_username = "—"
        parent_email = "—"

        try:
            parent_link = (
                ParentStudent.objects
                .select_related("parent")
                .filter(
                    student=application,
                    is_active=True,
                )
                .first()
            )

            if parent_link and parent_link.parent:
                parent_user = parent_link.parent

                parent_username = (
                    getattr(parent_user, "username", None) or "—"
                )

                parent_email = (
                    getattr(parent_user, "email", None) or "—"
                )

        except Exception as exc:
            print("Parent lookup error:", repr(exc))

        # -----------------------------------------------------
        # STUDENT BUS DETAILS
        # -----------------------------------------------------

        bus_number = "—"
        route_name = "—"
        pickup_stop = "—"

        try:
            bus_assignment = (
                StudentBusAssignment.objects
                .select_related("bus", "route", "pickup_stop")
                .filter(
                    student=application,
                    is_active=True,
                )
                .first()
            )

            bus_number, route_name, pickup_stop = get_bus_details(
                bus_assignment
            )

        except Exception as exc:
            print("Student bus assignment lookup error:", repr(exc))

        # -----------------------------------------------------
        # ACCOUNT STATUS
        # -----------------------------------------------------

        account_status = "Active"

        if not getattr(student_user, "is_active", True):
            account_status = "Inactive"
        elif not getattr(credential, "is_active", True):
            account_status = "Inactive"

        student_accounts.append({
            "admission_id": admission_id,
            "application_id": application_id,
            "student_name": student_name,
            "student_username": student_username,
            "school_email": school_email,
            "created_at": created_at,
            "parent_username": parent_username,
            "parent_email": parent_email,
            "bus_number": bus_number,
            "route_name": route_name,
            "pickup_stop": pickup_stop,
            "status": account_status,
        })

    # =========================================================
    # 6. CONTEXT
    # =========================================================

    context = {
        "employee_credentials": employee_credentials,
        "student_credentials": student_credentials,
        "employee_accounts": employee_accounts,
        "student_accounts": student_accounts,
        "employee_count": employee_count,
        "student_count": student_count,
        "total_count": employee_count + student_count,
    }

    # =========================================================
    # 7. RENDER
    # =========================================================

    return render(
        request,
        "admissions/system_admin/user_credentials.html",
        context,
    )
