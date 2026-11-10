from django.db import models
from django.contrib.auth.models import User


class Announcement(models.Model):

    PRIORITY_CHOICES = (
        ("normal", "Normal"),
        ("important", "Important"),
        ("urgent", "Urgent"),
    )

    AUDIENCE_CHOICES = (
        ("all", "Everyone"),
        ("staff", "Staff"),
        ("students", "Students"),
        ("parents", "Parents"),
        ("teachers", "Teachers"),
        ("management", "Management"),
    )

    title = models.CharField(
        max_length=200
    )

    message = models.TextField()

    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default="normal"
    )

    audience = models.CharField(
        max_length=20,
        choices=AUDIENCE_CHOICES,
        default="all"
    )

    publish_date = models.DateTimeField(
        auto_now_add=True
    )

    expiry_date = models.DateTimeField(
        blank=True,
        null=True
    )

    is_active = models.BooleanField(
        default=True
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_announcements"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-publish_date"]

    def __str__(self):
        return self.title