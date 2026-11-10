from django.contrib import admin

from .models import (
    Examination,
    ExamClassSubjectAssignment,
    ExamMark,
)


@admin.register(Examination)
class ExaminationAdmin(admin.ModelAdmin):

    list_display = (
        "exam_name",
        "exam_type",
        "academic_year",
        "start_date",
        "end_date",
        "status",
        "created_by",
    )

    list_filter = (
        "exam_type",
        "academic_year",
        "status",
    )

    search_fields = (
        "exam_name",
        "academic_year",
    )


@admin.register(ExamClassSubjectAssignment)
class ExamClassSubjectAssignmentAdmin(admin.ModelAdmin):

    list_display = (
        "examination",
        "class_section",
        "subject",
        "max_marks",
        "passing_marks",
    )

    list_filter = (
        "examination",
        "class_section",
        "subject",
    )

    search_fields = (
        "examination__exam_name",
        "subject__subject_name",
        "subject__subject_code",
    )


@admin.register(ExamMark)
class ExamMarkAdmin(admin.ModelAdmin):

    list_display = (
        "examination",
        "student",
        "class_section",
        "subject",
        "obtained_marks",
        "max_marks",
        "percentage",
        "grade",
        "status",
        "entered_by",
    )

    list_filter = (
        "examination",
        "class_section",
        "subject",
        "grade",
        "status",
    )

    search_fields = (
        "student__application_id",
        "student__first_name",
        "student__last_name",
    )