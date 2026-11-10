from django.db import models
from django.contrib.auth.models import User


class LeaveRequest(models.Model):

    LEAVE_TYPE_CHOICES = (
        ("Casual Leave", "Casual Leave"),
        ("Sick Leave", "Sick Leave"),
        ("Earned Leave", "Earned Leave"),
        ("Emergency Leave", "Emergency Leave"),
        ("Permission", "Permission"),
        ("Other", "Other"),
    )

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("cancelled", "Cancelled"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="leave_requests"
    )

    leave_type = models.CharField(
        max_length=30,
        choices=LEAVE_TYPE_CHOICES
    )

    from_date = models.DateField()

    to_date = models.DateField()

    reason = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    applied_at = models.DateTimeField(
        auto_now_add=True
    )

    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_leave_requests"
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    reviewer_remarks = models.TextField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = [
            "-applied_at"
        ]

    def __str__(self):
        return (
            f"{self.user.username} - "
            f"{self.leave_type} - "
            f"{self.from_date} to {self.to_date}"
        )

    @property
    def total_days(self):
        return (
            self.to_date - self.from_date
        ).days + 1