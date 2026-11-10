from django.contrib import admin
from .models import AcademicCalendarEvent


@admin.register(AcademicCalendarEvent)
class AcademicCalendarEventAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "event_type",
        "start_date",
        "end_date",
        "academic_year",
        "class_section",
        "status",
    )

    list_filter = (
        "event_type",
        "status",
        "academic_year",
    )

    search_fields = (
        "title",
        "description",
    )

    date_hierarchy = "start_date"