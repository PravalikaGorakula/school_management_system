from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.urls import reverse


class AcademicCalendarEvent(models.Model):

    EVENT_TYPES = [
        ("holiday", "Holiday"),
        ("examination", "Examination"),
        ("school_event", "School Event"),
        ("sports", "Sports"),
        ("cultural", "Cultural Event"),
        ("parent_meeting", "Parent Meeting"),
        ("academic_activity", "Academic Activity"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("published", "Published"),
        ("cancelled", "Cancelled"),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    event_type = models.CharField(
        max_length=30,
        choices=EVENT_TYPES,
        default="school_event",
    )

    start_date = models.DateField()
    end_date = models.DateField()

    academic_year = models.CharField(max_length=20)

    class_section = models.ForeignKey(
        "academics.ClassSection",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="calendar_events",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="published",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_calendar_events",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_date", "title"]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__gte=F("start_date")),
                name="calendar_end_date_after_start",
            ),
        ]

    def clean(self):
        if (
            self.start_date
            and self.end_date
            and self.end_date < self.start_date
        ):
            raise ValidationError({
                "end_date": "End date cannot be before start date."
            })

        if self.class_section_id and self.academic_year:
            if self.class_section.academic_year != self.academic_year:
                raise ValidationError({
                    "class_section": (
                        "Selected class section belongs to another academic year."
                    )
                })

    def get_absolute_url(self):
        return reverse(
            "academic_calendar:event_detail",
            kwargs={"pk": self.pk},
        )

    def __str__(self):
        return f"{self.title} - {self.start_date}"