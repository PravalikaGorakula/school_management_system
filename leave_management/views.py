from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.http import HttpResponseForbidden
from django.utils import timezone

from .forms import LeaveRequestForm
from .models import LeaveRequest
from attendance.services import flag_approved_leave_attendance_conflicts


# =========================================================
# ROLE HELPER
# =========================================================

def get_user_role(user):

    if not hasattr(user, "profile"):
        return None

    return user.profile.role


# =========================================================
# LEAVE APPLY PERMISSION
# Chairman cannot apply
# =========================================================

def can_apply_leave(user):

    role = get_user_role(user)

    return role in [
        "admission_staff",
        "system_administrator",
        "vice_principal",
        "teacher",
        "student",
        "principal",
        "accountant",
        "parent",
        "bus_driver",
    ]


# =========================================================
# LEAVE APPROVAL PERMISSION
#
# These roles can see Leave Approvals
# =========================================================

def can_view_leave_approvals(user):

    role = get_user_role(user)

    return role in [
        "principal",
        "vice_principal",
        "teacher",
    ]


# =========================================================
# WHO CAN APPROVE WHICH ROLE
# =========================================================

def get_approval_roles(user):

    role = get_user_role(user)

    # -----------------------------------------------------
    # Teacher can approve Student leaves
    # -----------------------------------------------------

    if role == "teacher":

        return [
            "student",
        ]

    # -----------------------------------------------------
    # Vice Principal can approve:
    #
    # Teacher
    # Admission Staff
    # System Administrator
    # Accountant
    # Bus Driver
    # -----------------------------------------------------

    if role == "vice_principal":

        return [
            "teacher",
            "admission_staff",
            "system_administrator",
            "accountant",
            "bus_driver",
        ]

    # -----------------------------------------------------
    # Principal can approve Vice Principal leaves
    # -----------------------------------------------------

    if role == "principal":

        return [
            "vice_principal",
        ]

    return []


# =========================================================
# LEAVE HOME
# =========================================================

@login_required
def leave_home(request):

    role = get_user_role(request.user)

    context = {
        "role": role,

        "can_apply": can_apply_leave(
            request.user
        ),

        "can_approve": can_view_leave_approvals(
            request.user
        ),

        "role_display": request.user.profile.get_role_display(),
    }

    return render(
        request,
        "leave_management/leave_home.html",
        context
    )


# =========================================================
# APPLY LEAVE
#
# This page contains:
#
# 1. Apply Leave
# 2. Leave History
# 3. Leave Approvals card
#
# Leave Approvals card is shown only to:
#
# Principal
# Vice Principal
# Teacher
# =========================================================

@login_required
def apply_leave(request):

    # -----------------------------------------------------
    # BACKEND PERMISSION CHECK
    # -----------------------------------------------------

    if not can_apply_leave(request.user):

        return HttpResponseForbidden(
            "You do not have permission to apply for leave."
        )

    role = get_user_role(request.user)

    # -----------------------------------------------------
    # CHECK APPROVAL PERMISSION
    # Used by apply_leave.html
    #
    # {% if can_approve_leave %}
    # -----------------------------------------------------

    can_approve_leave = can_view_leave_approvals(
        request.user
    )

    # -----------------------------------------------------
    # GET CURRENT USER LEAVE HISTORY
    # -----------------------------------------------------

    leaves = (
        LeaveRequest.objects
        .filter(
            user=request.user
        )
        .select_related(
            "user",
            "reviewed_by",
        )
        .order_by(
            "-applied_at"
        )
    )

    # -----------------------------------------------------
    # POST - APPLY LEAVE
    # -----------------------------------------------------

    if request.method == "POST":

        form = LeaveRequestForm(
            request.POST
        )

        if form.is_valid():

            leave = form.save(
                commit=False
            )

            # Current logged-in user
            # becomes the applicant
            leave.user = request.user

            # New leave always starts as pending
            leave.status = "pending"

            leave.save()

            messages.success(
                request,
                "Leave application submitted successfully."
            )

            # Redirect back to same page
            # so the new leave appears in history
            return redirect(
                "leave_management:apply_leave"
            )

    else:

        form = LeaveRequestForm()

    # -----------------------------------------------------
    # CONTEXT
    # -----------------------------------------------------

    context = {

        "form": form,

        "leaves": leaves,

        "role": role,

        "role_display": (
            request.user.profile.get_role_display()
        ),

        "can_apply": can_apply_leave(
            request.user
        ),

        "can_approve_leave": can_approve_leave,

        "breadcrumb": "Leaves / Apply Leave",
    }

    return render(
        request,
        "leave_management/apply_leave.html",
        context
    )


# =========================================================
# LEAVE HISTORY
#
# Shows only current logged-in user's leaves
# =========================================================

@login_required
def leave_history(request):

    leaves = (
        LeaveRequest.objects
        .filter(
            user=request.user
        )
        .select_related(
            "user",
            "reviewed_by",
        )
        .order_by(
            "-applied_at"
        )
    )

    context = {

        "leaves": leaves,

        "role": get_user_role(
            request.user
        ),

        "role_display": (
            request.user.profile.get_role_display()
        ),

        "breadcrumb": "Leaves / Leave History",
    }

    return render(
        request,
        "leave_management/leave_history.html",
        context
    )


# =========================================================
# LEAVE APPROVAL LIST
#
# Only:
# Principal
# Vice Principal
# Teacher
# =========================================================

@login_required
def leave_approvals(request):

    # -----------------------------------------------------
    # BACKEND PERMISSION CHECK
    # -----------------------------------------------------

    if not can_view_leave_approvals(
        request.user
    ):

        return HttpResponseForbidden(
            "You do not have permission to access leave approvals."
        )

    # -----------------------------------------------------
    # GET APPLICANT ROLES
    # CURRENT REVIEWER CAN APPROVE
    # -----------------------------------------------------

    approval_roles = get_approval_roles(
        request.user
    )

    # -----------------------------------------------------
    # GET ONLY PENDING LEAVES
    # FOR THE ALLOWED APPLICANT ROLES
    # -----------------------------------------------------

    leaves = (
        LeaveRequest.objects
        .filter(
            status="pending",
            user__profile__role__in=approval_roles,
        )
        .select_related(
            "user",
            "user__profile",
        )
        .order_by(
            "-applied_at"
        )
    )

    # -----------------------------------------------------
    # CONTEXT
    # -----------------------------------------------------

    context = {

        "leaves": leaves,

        "approval_roles": approval_roles,

        "role": get_user_role(
            request.user
        ),

        "role_display": (
            request.user.profile.get_role_display()
        ),

        "breadcrumb": "Leaves / Approvals",
    }

    return render(
        request,
        "leave_management/leave_approvals.html",
        context
    )


# =========================================================
# APPROVE LEAVE
# =========================================================

@login_required
def approve_leave(request, leave_id):

    # -----------------------------------------------------
    # ONLY PRINCIPAL / VP / TEACHER
    # -----------------------------------------------------

    if not can_view_leave_approvals(
        request.user
    ):

        return HttpResponseForbidden(
            "You do not have permission to approve leave."
        )

    # -----------------------------------------------------
    # APPROVE ONLY PENDING LEAVE
    # -----------------------------------------------------

    leave = get_object_or_404(
        LeaveRequest,
        id=leave_id,
        status="pending",
    )

    # -----------------------------------------------------
    # GET ROLES THIS REVIEWER CAN APPROVE
    # -----------------------------------------------------

    approval_roles = get_approval_roles(
        request.user
    )

    # -----------------------------------------------------
    # GET APPLICANT ROLE
    # -----------------------------------------------------

    applicant_role = get_user_role(
        leave.user
    )

    # -----------------------------------------------------
    # CHECK WHETHER REVIEWER CAN APPROVE
    # THIS PARTICULAR APPLICANT
    # -----------------------------------------------------

    if applicant_role not in approval_roles:

        return HttpResponseForbidden(
            "You are not authorized to approve this leave."
        )

    # -----------------------------------------------------
    # APPROVE ONLY THROUGH POST
    # -----------------------------------------------------

    if request.method != "POST":

        return HttpResponseForbidden(
            "Invalid request."
        )

    # -----------------------------------------------------
    # UPDATE LEAVE
    # -----------------------------------------------------

    leave.status = "approved"

    leave.reviewed_by = request.user

    leave.reviewed_at = timezone.now()

    leave.reviewer_remarks = request.POST.get(
        "reviewer_remarks",
        ""
    ).strip()

    with transaction.atomic():
        leave.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
                "reviewer_remarks",
                "updated_at",
            ]
        )
        flag_approved_leave_attendance_conflicts(
            leave.user,
            leave.from_date,
            leave.to_date,
        )

    # -----------------------------------------------------
    # SUCCESS MESSAGE
    # -----------------------------------------------------

    messages.success(
        request,
        "Leave approved successfully."
    )

    # -----------------------------------------------------
    # BACK TO APPROVALS
    # -----------------------------------------------------

    return redirect(
        "leave_management:leave_approvals"
    )


# =========================================================
# REJECT LEAVE
# =========================================================

@login_required
def reject_leave(request, leave_id):

    # -----------------------------------------------------
    # ONLY PRINCIPAL / VP / TEACHER
    # -----------------------------------------------------

    if not can_view_leave_approvals(
        request.user
    ):

        return HttpResponseForbidden(
            "You do not have permission to reject leave."
        )

    # -----------------------------------------------------
    # REJECT ONLY PENDING LEAVE
    # -----------------------------------------------------

    leave = get_object_or_404(
        LeaveRequest,
        id=leave_id,
        status="pending",
    )

    # -----------------------------------------------------
    # GET ROLES THIS REVIEWER CAN REJECT
    # -----------------------------------------------------

    approval_roles = get_approval_roles(
        request.user
    )

    # -----------------------------------------------------
    # GET APPLICANT ROLE
    # -----------------------------------------------------

    applicant_role = get_user_role(
        leave.user
    )

    # -----------------------------------------------------
    # CHECK WHETHER REVIEWER CAN REJECT
    # THIS PARTICULAR APPLICANT
    # -----------------------------------------------------

    if applicant_role not in approval_roles:

        return HttpResponseForbidden(
            "You are not authorized to reject this leave."
        )

    # -----------------------------------------------------
    # REJECT ONLY THROUGH POST
    # -----------------------------------------------------

    if request.method != "POST":

        return HttpResponseForbidden(
            "Invalid request."
        )

    # -----------------------------------------------------
    # UPDATE LEAVE
    # -----------------------------------------------------

    leave.status = "rejected"

    leave.reviewed_by = request.user

    leave.reviewed_at = timezone.now()

    leave.reviewer_remarks = request.POST.get(
        "reviewer_remarks",
        ""
    ).strip()

    leave.save(
        update_fields=[
            "status",
            "reviewed_by",
            "reviewed_at",
            "reviewer_remarks",
            "updated_at",
        ]
    )

    # -----------------------------------------------------
    # SUCCESS MESSAGE
    # -----------------------------------------------------

    messages.success(
        request,
        "Leave rejected successfully."
    )

    # -----------------------------------------------------
    # BACK TO APPROVALS
    # -----------------------------------------------------

    return redirect(
        "leave_management:leave_approvals"
    )