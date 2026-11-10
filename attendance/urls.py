from django.urls import path

from . import views


app_name = "attendance"


urlpatterns = [

    # Main Attendance Dashboard
    path(
        "",
        views.attendance_dashboard,
        name="attendance_dashboard",
    ),

    # My Attendance
    path(
        "my/",
        views.my_attendance,
        name="my_attendance",
    ),

    # Teacher - Student Attendance
    path(
        "teacher/",
        views.teacher_attendance,
        name="teacher_attendance",
    ),
    path(
    "sessions/<int:session_id>/finalize/",
    views.finalize_student_attendance,
    name="finalize_student_attendance",
    ),
    path(
        "review/",
        views.attendance_review,
        name="attendance_review",
    ),
    path(
        "records/<int:attendance_id>/correction/",
        views.request_attendance_correction,
        name="request_attendance_correction",
    ),
    path(
        "corrections/<int:correction_id>/review/",
        views.review_attendance_correction,
        name="review_attendance_correction",
    ),

    # Student - My Attendance
    path(
        "student/",
        views.student_attendance,
        name="student_attendance",
    ),

    # Management - Student Attendance
    path(
        "students/",
        views.student_attendance_management,
        name="student_attendance_management",
    ),

    # Management - Employee Attendance
    path(
        "employees/",
        views.employee_attendance,
        name="employee_attendance",
    ),

    # Parent - Child Attendance
    path(
        "child/",
        views.child_attendance,
        name="child_attendance",
    ),
    path(
    "employee/my/",
    views.employee_my_attendance,
    name="employee_my_attendance",
),

path(
    "employee/check-in/",
    views.employee_check_in,
    name="employee_check_in",
),

path(
    "employee/check-out/",
    views.employee_check_out,
    name="employee_check_out",
), 
]