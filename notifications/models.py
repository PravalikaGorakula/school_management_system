from django.db import models
from django.contrib.auth.models import User


class Notification(models.Model):

    NOTIFICATION_TYPES = [
        ("announcement", "Announcement"),
        ("assignment", "Assignment"),
        ("event", "Upcoming Event"),
        ("approval", "Approval"),
        ("marks", "Marks Update"),
        ("exam", "Exam"),
        ("attendance", "Attendance"),
        ("transport", "Transport"),
        ("system", "System"),
        ("general", "General"),
    ]

    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("normal", "Normal"),
        ("high", "High"),
        ("urgent", "Urgent"),
    ]

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications"
    )

    title = models.CharField(
        max_length=200
    )

    message = models.TextField()

    notification_type = models.CharField(
        max_length=30,
        choices=NOTIFICATION_TYPES,
        default="general"
    )

    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default="normal"
    )

    is_read = models.BooleanField(
        default=False
    )

    related_url = models.CharField(
        max_length=500,
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    expires_at = models.DateTimeField(
        blank=True,
        null=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.recipient.username} - {self.title}"