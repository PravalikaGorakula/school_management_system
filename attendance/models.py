from django.contrib.auth.models import User
from django.db import models

from admissions.models import StudentAdmissionApplication
from academics.models import ClassSection, Subject

class StudentAttendance(models.Model):

    STATUS_CHOICES = [
        ("Present", "Present"),
        ("Absent", "Absent"),
        ("Late", "Late"),
    ]

    student = models.ForeignKey(
        StudentAdmissionApplication,
        on_delete=models.CASCADE,
        related_name="student_attendance_records",
    )

    class_section = models.ForeignKey(
        ClassSection,
        on_delete=models.CASCADE,
        related_name="student_attendance_records",
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="student_attendance_records",
    )

    date = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Present",
    )

    remarks = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    marked_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_attendance_marked",
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = [
            "-date",
            "student__first_name",
            "student__last_name",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "student",
                    "class_section",
                    "subject",
                    "date",
                ],
                name="unique_student_subject_date_attendance",
            )
        ]

    def __str__(self):
        return (
            f"{self.student.application_id} - "
            f"{self.subject.subject_name} - "
            f"{self.date} - "
            f"{self.status}"
        )

class AttendanceParentNotification(models.Model):

    parent = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="attendance_parent_notifications",
    )

    student = models.ForeignKey(
        StudentAdmissionApplication,
        on_delete=models.CASCADE,
        related_name="attendance_parent_notifications",
    )

    attendance = models.ForeignKey(
        StudentAttendance,
        on_delete=models.CASCADE,
        related_name="parent_notifications",
    )

    title = models.CharField(
        max_length=255,
        default="Attendance Alert",
    )

    message = models.TextField()

    is_read = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    read_at = models.DateTimeField(
        blank=True,
        null=True,
    )

    class Meta:
        ordering = [
            "-created_at",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "parent",
                    "attendance",
                ],
                name="unique_parent_attendance_notification",
            )
        ]

    def __str__(self):
        return (
            f"{self.student.application_id} - "
            f"{self.parent.username} - "
            f"{self.title}"
        )


class EmployeeAttendance(models.Model):

    STATUS_CHOICES = [
        ("Present", "Present"),
        ("Absent", "Absent"),
        ("Late", "Late"),
        ("Half Day", "Half Day"),
        ("Leave", "Leave"),
    ]

    employee = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="employee_attendance_records",
    )

    date = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Present",
    )

    # LOGIN / LOGOUT TIME
    check_in = models.TimeField(blank=True, null=True)
    check_out = models.TimeField(blank=True, null=True)

    # LOGIN GPS
    login_latitude = models.DecimalField(
        max_digits=10, decimal_places=7, blank=True, null=True
    )
    login_longitude = models.DecimalField(
        max_digits=10, decimal_places=7, blank=True, null=True
    )
    login_accuracy = models.FloatField(blank=True, null=True)

    # LOGIN LOCATION NAME
    login_location_name = models.CharField(
        max_length=255, blank=True, null=True
    )

    # LOGOUT GPS
    logout_latitude = models.DecimalField(
        max_digits=10, decimal_places=7, blank=True, null=True
    )
    logout_longitude = models.DecimalField(
        max_digits=10, decimal_places=7, blank=True, null=True
    )
    logout_accuracy = models.FloatField(blank=True, null=True)

    # LOGOUT LOCATION NAME
    logout_location_name = models.CharField(
        max_length=255, blank=True, null=True
    )

    # CALCULATION
    working_minutes = models.PositiveIntegerField(default=0)
    late_minutes = models.PositiveIntegerField(default=0)

    # REMARKS
    remarks = models.TextField(blank=True, null=True)

    # MARKED BY
    marked_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="employee_attendance_marked",
    )

    # TIMESTAMPS
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "employee__first_name", "employee__last_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "date"],
                name="unique_employee_date_attendance",
            )
        ]

    def __str__(self):
        return (
            f"{self.employee.get_full_name() or self.employee.username} - "
            f"{self.date} - {self.status}"
        )


class AttendanceSession(models.Model):
    """
    One attendance session for a class, subject and date.
    """

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("finalized", "Finalized"),
    ]

    class_section = models.ForeignKey(
        "academics.ClassSection",
        on_delete=models.PROTECT,
        related_name="attendance_sessions",
    )

    subject = models.ForeignKey(
        "academics.Subject",
        on_delete=models.PROTECT,
        related_name="attendance_sessions",
    )

    date = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft",
    )

    created_by = models.ForeignKey(
        "auth.User",
        on_delete=models.PROTECT,
        related_name="created_attendance_sessions",
    )

    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    finalized_by = models.ForeignKey(
        "auth.User",
        on_delete=models.PROTECT,
        related_name="finalized_attendance_sessions",
        null=True,
        blank=True,
    )

    finalized_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-date", "class_section", "subject"]
        constraints = [
            models.UniqueConstraint(
                fields=["class_section", "subject", "date"],
                name="unique_class_subject_attendance_session",
            )
        ]

    def __str__(self):
        return (
            f"{self.class_section} - "
            f"{self.subject} - {self.date} - {self.status}"
        )


class AttendanceCorrection(models.Model):
    """
    Stores attendance correction requests and their approval history.
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    attendance = models.ForeignKey(
        "attendance.StudentAttendance",
        on_delete=models.PROTECT,
        related_name="correction_requests",
    )

    old_status = models.CharField(
        max_length=20,
        choices=StudentAttendance.STATUS_CHOICES,
    )

    new_status = models.CharField(
        max_length=20,
        choices=StudentAttendance.STATUS_CHOICES,
    )

    reason = models.TextField()

    requested_by = models.ForeignKey(
        "auth.User",
        on_delete=models.PROTECT,
        related_name="attendance_correction_requests",
    )

    reviewed_by = models.ForeignKey(
        "auth.User",
        on_delete=models.PROTECT,
        related_name="reviewed_attendance_corrections",
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )

    reviewer_remarks = models.TextField(
        blank=True,
    )

    requested_at = models.DateTimeField(
        auto_now_add=True,
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-requested_at"]

    def __str__(self):
        return (
            f"Correction #{self.pk} - "
            f"{self.attendance_id} - {self.status}"
        )
