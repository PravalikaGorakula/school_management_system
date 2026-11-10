from django.urls import path

from . import views


app_name = "exams"


urlpatterns = [

    # =====================================================
    # EXAMINATIONS
    # =====================================================

    path(
        "",
        views.examination_list,
        name="exam_list",
    ),

    path(
        "create/",
        views.examination_create,
        name="exam_create",
    ),

    path(
        "<int:exam_id>/",
        views.examination_detail,
        name="examination_detail",
    ),

    path(
    "<int:exam_id>/edit/",
    views.examination_edit,
    name="exam_edit",
    ),

    # =====================================================
    # EXAM CLASS + SUBJECT
    # =====================================================

    path(
        "<int:exam_id>/assign/",
        views.assign_exam_subject,
        name="exam_assignment",
    ),

    path(
        "assignment/<int:assignment_id>/remove/",
        views.remove_exam_assignment,
        name="exam_assignment_remove",
    ),

    # =====================================================
    # TEACHER MARKS
    # =====================================================

    path(
        "teacher/marks/",
        views.teacher_marks,
        name="teacher_marks",
    ),

    path(
        "teacher/marks/<int:assignment_id>/save/",
        views.save_teacher_marks,
        name="save_teacher_marks",
    ),

    path(
        "teacher/marks/<int:assignment_id>/submit/",
        views.submit_teacher_marks,
        name="submit_teacher_marks",
    ),

    # =====================================================
    # PUBLISH
    # =====================================================

    path(
        "<int:exam_id>/publish/",
        views.publish_examination,
        name="exam_publish",
    ),

    # =====================================================
    # MANAGEMENT RESULTS
    # =====================================================

    path(
        "results/",
        views.result_list,
        name="result_list",
    ),

    # =====================================================
    # STUDENT
    # =====================================================

    path(
        "student/marks/",
        views.student_marks,
        name="student_marks",
    ),

    path(
        "student/results/",
        views.student_results,
        name="student_results",
    ),

    path(
        "report-card/<int:exam_id>/",
        views.report_card,
        name="report_card",
    ),
    path(
    "parent/results/",
    views.parent_results,
    name="parent_results",
),
]