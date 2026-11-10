from django.urls import path
from . import views

app_name = "admissions"

urlpatterns = [

    # =========================================================
    # ADMISSIONS
    # =========================================================

    path(
        "",
        views.admissions_home,
        name="home",
    ),

    # =========================================================
    # STUDENT APPLICATIONS
    # =========================================================

    path(
        "students/",
        views.student_applications,
        name="student_applications",
    ),

    path(
        "students/add/",
        views.create_student_application,
        name="create_student_application",
    ),

    path(
        "students/<int:application_id>/",
        views.student_application_detail,
        name="student_application_detail",
    ),
    path(
    "students/<int:application_id>/edit/",
    views.student_application_edit,
    name="student_application_edit",
    ),
    path(
        "employees/",
        views.employee_applications,
        name="employee_applications",
    ),

    path(
        "employees/add/",
        views.create_employee_application,
        name="create_employee_application",
    ),

    path(
        "employees/<int:application_id>/",
        views.employee_application_detail,
        name="employee_application_detail",
    ),
    path(
    "employees/<int:application_id>/edit/",
    views.employee_application_edit,
    name="employee_application_edit",
    ),

    # =========================================================
    # SYSTEM ADMINISTRATOR APPROVALS
    # =========================================================

    path(
        "system-admin/approvals/",
        views.system_admin_approvals,
        name="system_admin_approvals",
    ),

    path(
        "system-admin/approvals/student/<int:approval_id>/",
        views.system_admin_student_approval_detail,
        name="system_admin_student_approval_detail",
    ),

    path(
        "system-admin/approvals/employee/<int:approval_id>/",
        views.system_admin_employee_approval_detail,
        name="system_admin_employee_approval_detail",
    ),

    path(
        "system-admin/approvals/student/<int:approval_id>/accept/",
        views.system_admin_accept_student,
        name="system_admin_accept_student",
    ),

    path(
        "system-admin/approvals/student/<int:approval_id>/reject/",
        views.system_admin_reject_student,
        name="system_admin_reject_student",
    ),

    path(
        "system-admin/approvals/employee/<int:approval_id>/accept/",
        views.system_admin_accept_employee,
        name="system_admin_accept_employee",
    ),

    path(
        "system-admin/approvals/employee/<int:approval_id>/reject/",
        views.system_admin_reject_employee,
        name="system_admin_reject_employee",
    ),
    path(
        "vp/student-approvals/",
        views.vp_student_approvals,
        name="vp_student_approvals",
    ),

    path(
        "vp/employee-approvals/",
        views.vp_employee_approvals,
        name="vp_employee_approvals",
    ),
    path(
    "vp/employee-approvals/<int:approval_id>/",
    views.vp_employee_approval_detail,
    name="vp_employee_approval_detail",
    ),
    path(
    "vp/employee-approvals/<int:approval_id>/approve/",
    views.vp_approve_employee,
    name="vp_approve_employee",
    ),
    path(
    "vp/employee-approvals/<int:approval_id>/reject/",
    views.vp_reject_employee,
    name="vp_reject_employee",
    ),
    
    path(
    "vp/student-approvals/<int:approval_id>/",
    views.vp_student_approval_detail,
    name="vp_student_approval_detail",
    ),
    path(
    "vp/student-approvals/<int:approval_id>/approve/",
    views.vp_approve_student,
    name="vp_approve_student",
    ),
    path(
    "vp/student-approvals/<int:approval_id>/reject/",
    views.vp_reject_student,
    name="vp_reject_student",
    ),
    
    path(
    "system-admin/user-credentials/",
    views.system_admin_user_credentials,
    name="system_admin_user_credentials",
),


]