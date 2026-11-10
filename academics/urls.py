
from django.urls import path
from . import views

app_name = "academics"

urlpatterns = [

    # =========================================================
    # CLASS & SECTIONS
    # =========================================================
    path(
        "class-sections/",
        views.class_sections,
        name="class_sections",
    ),
    path(
        "class-sections/add/",
        views.add_class_section,
        name="add_class_section",
    ),
    path(
        "class-sections/<int:class_section_id>/edit/",
        views.edit_class_section,
        name="edit_class_section",
    ),
    path(
        "class-sections/<int:class_section_id>/delete/",
        views.delete_class_section,
        name="delete_class_section",
    ),

    # =========================================================
    # SUBJECTS
    # =========================================================
    path(
        "subjects/",
        views.subjects,
        name="subjects",
    ),
    path(
        "subjects/add/",
        views.add_subject,
        name="add_subject",
    ),
    path(
        "subjects/assign-employee/",
        views.assign_subject_employee,
        name="assign_subject_employee",
    ),
    path(
        "subject-assignments/<int:assignment_id>/edit/",
        views.edit_subject_assignment,
        name="edit_subject_assignment",
    ),
    path(
        "subject-assignments/<int:assignment_id>/delete/",
        views.delete_subject_assignment,
        name="delete_subject_assignment",
    ),
    path(
        "subjects/<int:subject_id>/edit/",
        views.edit_subject,
        name="edit_subject",
    ),
    path(
        "subjects/<int:subject_id>/toggle/",
        views.toggle_subject,
        name="toggle_subject",
    ),
    path(
        "subjects/<int:subject_id>/delete/",
        views.delete_subject,
        name="delete_subject",
    ),

    # =========================================================
    # TIMETABLE WORKFLOW
    # =========================================================

    # Timetable dashboard
    path(
        "timetable/",
        views.timetable,
        name="timetable",
    ),

    # Step 1: Configure school timings and periods
    path(
        "timetable/configure/",
        views.timetable_config,
        name="timetable_config",
    ),

    # Step 2: Subject period requirements
    path(
        "subject-period-requirements/",
        views.subject_period_requirements,
        name="subject_period_requirements",
    ),

    # Step 3: Generate and edit timetable
    path(
        "timetable/generate/",
        views.timetable_generate,
        name="timetable_generate",
    ),

    # Step 4: Validate and approval
    path(
        "timetable/validate/",
        views.timetable_validate,
        name="timetable_validate",
    ),

    # Teacher options for timetable
    path(
        "timetable/employee-options/",
        views.timetable_employee_options,
        name="timetable_employee_options",
    ),

    # =========================================================
    # TEACHER
    # =========================================================
    path(
        "teacher/timetable/",
        views.teacher_timetable,
        name="teacher_timetable",
    ),
    path(
        "teacher/students/",
        views.teacher_students,
        name="teacher_students",
    ),
    path(
        "teacher/students/<int:student_id>/message-parent/",
        views.message_parent,
        name="message_parent",
    ),

    # =========================================================
    # STUDENT
    # =========================================================
    path(
        "student/subjects/",
        views.student_subjects_home,
        name="student_subjects_home",
    ),
    path(
        "student/subjects/list/",
        views.student_subject_list,
        name="student_subject_list",
    ),
    path(
        "student/subjects/<int:assignment_id>/message/",
        views.student_message_teacher,
        name="student_message_teacher",
    ),
    path(
        "student/assignments/",
        views.student_assignments,
        name="student_assignments",
    ),
    path(
        "student/assignments/<int:assignment_id>/submit/",
        views.student_submit_assignment,
        name="student_submit_assignment",
    ),
    path(
        "student/assignments/<int:assignment_id>/download/",
        views.student_download_assignment,
        name="student_download_assignment",
    ),
    path(
        "student/submissions/<int:submission_id>/download/",
        views.student_download_submission,
        name="student_download_submission",
    ),
    path(
        "student/timetable/",
        views.student_timetable,
        name="student_timetable",
    ),
    path(
        "student/all-results/",
        views.student_all_results,
        name="student_all_results",
    ),
]
