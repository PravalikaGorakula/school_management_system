from django.contrib import admin

from .models import (
    StudentAttendance,
    EmployeeAttendance,
    AttendanceParentNotification,
    AttendanceSession,
    AttendanceCorrection,
)


@admin.register(StudentAttendance)
class StudentAttendanceAdmin(admin.ModelAdmin):

    list_display = (
        "student",
        "class_section",
        "subject",
        "date",
        "status",
        "marked_by",
    )

    list_filter = (
        "status",
        "date",
        "class_section",
        "subject",
    )

    search_fields = (
        "student__application_id",
        "student__first_name",
        "student__last_name",
        "subject__subject_name",
    )

    ordering = (
        "-date",
    )


@admin.register(EmployeeAttendance)
class EmployeeAttendanceAdmin(admin.ModelAdmin):

    list_display = (
        "employee",
        "date",
        "status",
        "check_in",
        "check_out",
        "marked_by",
    )

    list_filter = (
        "status",
        "date",
    )

    search_fields = (
        "employee__username",
        "employee__first_name",
        "employee__last_name",
    )

    ordering = (
        "-date",
    )


@admin.register(AttendanceParentNotification)
class AttendanceParentNotificationAdmin(admin.ModelAdmin):
    list_display = ("parent", "student", "attendance", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = (
        "parent__username",
        "student__application_id",
        "student__first_name",
        "student__last_name",
    )


@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    list_display = (
        "class_section",
        "subject",
        "date",
        "status",
        "created_by",
        "finalized_by",
    )
    list_filter = ("status", "date", "class_section", "subject")
    search_fields = ("class_section__grade", "class_section__section", "subject__subject_name")


@admin.register(AttendanceCorrection)
class AttendanceCorrectionAdmin(admin.ModelAdmin):
    list_display = (
        "attendance",
        "old_status",
        "new_status",
        "status",
        "requested_by",
        "reviewed_by",
        "requested_at",
    )
    list_filter = ("status", "requested_at", "reviewed_at")
    search_fields = (
        "attendance__student__application_id",
        "attendance__student__first_name",
        "attendance__student__last_name",
        "requested_by__username",
    )