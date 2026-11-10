from django.contrib import admin

from .models import (
    StudentAdmissionApplication,
    EmployeeAdmissionApplication,
)


# =========================================================
# STUDENT ADMISSION APPLICATION
# =========================================================

@admin.register(StudentAdmissionApplication)
class StudentAdmissionApplicationAdmin(admin.ModelAdmin):

    list_display = (
        "application_id",
        "first_name",
        "last_name",
        "applying_class",
        "phone",
        "status",
        "submitted_by",
        "submitted_at",
    )

    list_filter = (
        "status",
        "gender",
        "applying_class",
        "submitted_at",
    )

    search_fields = (
        "application_id",
        "first_name",
        "last_name",
        "phone",
        "email",
        "father_name",
        "mother_name",
        "parent_phone",
    )

    readonly_fields = (
        "application_id",
        "submitted_at",
        "updated_at",
    )

    autocomplete_fields = (
        "submitted_by",
    )

    ordering = (
        "-submitted_at",
    )


# =========================================================
# EMPLOYEE ADMISSION APPLICATION
# =========================================================

@admin.register(EmployeeAdmissionApplication)
class EmployeeAdmissionApplicationAdmin(admin.ModelAdmin):

    list_display = (
        "application_id",
        "first_name",
        "last_name",
        "designation",
        "department",
        "phone",
        "status",
        "submitted_by",
        "submitted_at",
    )

    list_filter = (
        "status",
        "gender",
        "marital_status",
        "department",
        "designation",
        "submitted_at",
    )

    search_fields = (
        "application_id",
        "first_name",
        "last_name",
        "email",
        "phone",
        "designation",
        "department",
        "qualification",
    )

    readonly_fields = (
        "application_id",
        "submitted_at",
        "updated_at",
    )

    autocomplete_fields = (
        "submitted_by",
    )

    ordering = (
        "-submitted_at",
    )