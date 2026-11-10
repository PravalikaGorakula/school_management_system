from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):

    ROLE_CHOICES = (
        ("admission_staff", "Admission Staff"),
        ("system_administrator", "System Administrator"),
        ("vice_principal", "Vice Principal"),
        ("teacher", "Teacher"),
        ("student", "Student"),
        ("principal", "Principal"),
        ("chairman", "Chairman"),
        ("accountant", "Accountant"),
        ("parent", "Parent"),
        ("bus_driver", "Bus Driver"),
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile"
    )

    role = models.CharField(
        max_length=30,
        choices=ROLE_CHOICES
    )

    phone = models.CharField(
        max_length=15,
        blank=True,
        null=True
    )

    profile_image = models.ImageField(
        upload_to="profile_images/",
        blank=True,
        null=True
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"


class SystemActivityLog(models.Model):

    ACTION_CHOICES = (
        ("login", "Login"),
        ("logout", "Logout"),
        ("create", "Create"),
        ("update", "Update"),
        ("delete", "Delete"),
        ("approve", "Approve"),
        ("reject", "Reject"),
        ("verify", "Verify"),
        ("upload", "Upload"),
        ("download", "Download"),
        ("other", "Other"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="system_activity_logs"
    )

    module = models.CharField(
        max_length=100
    )

    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        default="other"
    )

    description = models.TextField()

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True
    )

    timestamp = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "System Activity Log"
        verbose_name_plural = "System Activity Logs"

    def __str__(self):
        username = self.user.username if self.user else "System"
        return f"{username} - {self.module} - {self.action}"
