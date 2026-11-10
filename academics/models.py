from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

class ClassSection(models.Model):

    STATUS_CHOICES = (
        ("Active", "Active"),
        ("Inactive", "Inactive"),
        ("Full", "Full"),
    )

    grade = models.CharField(
        max_length=50
    )

    section = models.CharField(
        max_length=10
    )

    grade_group = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    class_teacher = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="class_sections"
    )

    academic_year = models.CharField(
        max_length=20
    )

    capacity = models.PositiveIntegerField(
        default=40
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Active"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"{self.grade} - {self.section} ({self.academic_year})"

class Subject(models.Model):

    SUBJECT_TYPE_CHOICES = (
        ("Core", "Core"),
        ("Elective", "Elective"),
    )

    subject_name = models.CharField(
        max_length=100
    )

    subject_code = models.CharField(
        max_length=30,
        unique=True
    )

    subject_type = models.CharField(
        max_length=20,
        choices=SUBJECT_TYPE_CHOICES,
        default="Core"
    )

    department = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    description = models.TextField(
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
        return f"{self.subject_name} ({self.subject_code})"

class SubjectEmployeeAssignment(models.Model):

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="employee_assignments"
    )

    employee = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="subject_assignments"
    )

    class_section = models.ForeignKey(
        ClassSection,
        on_delete=models.CASCADE,
        related_name="subject_assignments"
    )

    academic_year = models.CharField(
        max_length=20
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

    class Meta:
        unique_together = (
            "subject",
            "employee",
            "class_section",
            "academic_year",
        )
        ordering = [
            "subject__subject_name",
            "class_section__grade",
            "class_section__section",
        ]

    def __str__(self):
        return (
            f"{self.subject.subject_name} - "
            f"{self.employee.get_full_name() or self.employee.username} - "
            f"{self.class_section}"
        )

class TimetableEntry(models.Model):

    DAY_CHOICES = (
        ("Monday", "Monday"),
        ("Tuesday", "Tuesday"),
        ("Wednesday", "Wednesday"),
        ("Thursday", "Thursday"),
        ("Friday", "Friday"),
        ("Saturday", "Saturday"),
    )

    class_section = models.ForeignKey(
        ClassSection,
        on_delete=models.CASCADE,
        related_name="timetable_entries"
    )
    timetable_plan = models.ForeignKey(
    "TimetablePlan",
    on_delete=models.CASCADE,
    null=True,
    blank=True,
    related_name="entries",
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="timetable_entries"
    )

    employee = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="timetable_entries"
    )

    academic_year = models.CharField(
        max_length=20
    )

    day = models.CharField(
        max_length=20,
        choices=DAY_CHOICES
    )

    period = models.PositiveIntegerField()

    room = models.CharField(
        max_length=100,
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

    class Meta:
        ordering = [
            "academic_year",
            "class_section__grade",
            "class_section__section",
            "day",
            "period",
        ]

    def __str__(self):
        return (
            f"{self.class_section} - "
            f"{self.subject.subject_name} - "
            f"{self.day} P{self.period}"
        )


class SchoolTimetableConfig(models.Model):
    """School timetable settings for an academic year."""

    academic_year = models.CharField(
        max_length=20,
        unique=True,
    )

    working_days = models.JSONField(
        default=list,
    )

    school_start_time = models.TimeField()
    school_end_time = models.TimeField()

    periods_per_day = models.PositiveIntegerField(
        default=8,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return f"Timetable Configuration - {self.academic_year}"


class PeriodDefinition(models.Model):
    """Defines the time and type of each daily timetable slot."""

    PERIOD_TYPE_CHOICES = (
        ("Teaching", "Teaching Period"),
        ("Break", "Short Break"),
        ("Lunch", "Lunch Break"),
        ("Assembly", "Assembly"),
        ("Activity", "Activity"),
    )

    academic_year = models.CharField(
        max_length=20,
    )

    period_number = models.PositiveIntegerField()

    period_name = models.CharField(
        max_length=50,
        blank=True,
    )

    start_time = models.TimeField()
    end_time = models.TimeField()

    period_type = models.CharField(
        max_length=20,
        choices=PERIOD_TYPE_CHOICES,
        default="Teaching",
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ["academic_year", "period_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["academic_year", "period_number"],
                name="unique_period_number_per_year",
            ),
        ]

    def __str__(self):
        return (
            f"{self.academic_year} - "
            f"Period {self.period_number} "
            f"({self.start_time} - {self.end_time})"
        )


class SubjectPeriodRequirement(models.Model):
    """Weekly subject-period requirements for each class section."""

    class_section = models.ForeignKey(
        ClassSection,
        on_delete=models.CASCADE,
        related_name="period_requirements",
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="period_requirements",
    )

    academic_year = models.CharField(
        max_length=20,
    )

    periods_per_week = models.PositiveIntegerField(
        default=1,
    )

    class Meta:
        ordering = [
            "class_section__grade",
            "class_section__section",
            "subject__subject_name",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "class_section",
                    "subject",
                    "academic_year",
                ],
                name="unique_subject_requirement_per_class_year",
            ),
        ]

    def __str__(self):
        return (
            f"{self.class_section} - "
            f"{self.subject.subject_name}: "
            f"{self.periods_per_week} periods/week"
        )


class TimetablePlan(models.Model):
    """A draft or published timetable version for one class section."""

    STATUS_CHOICES = (
        ("Draft", "Draft"),
        ("Published", "Published"),
        ("Archived", "Archived"),
    )

    class_section = models.ForeignKey(
        ClassSection,
        on_delete=models.CASCADE,
        related_name="timetable_plans",
    )

    academic_year = models.CharField(
        max_length=20,
    )

    version = models.PositiveIntegerField(
        default=1,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Draft",
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="created_timetable_plans",
    )

    published_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="published_timetable_plans",
    )

    generated_at = models.DateTimeField(
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
        ordering = [
            "academic_year",
            "class_section__grade",
            "class_section__section",
            "-version",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "class_section",
                    "academic_year",
                    "version",
                ],
                name="unique_timetable_version_per_class_year",
            ),
        ]

    def __str__(self):
        return (
            f"{self.class_section} - "
            f"{self.academic_year} - "
            f"Version {self.version} ({self.status})"
        )

class StudentTeacherMessage(models.Model):

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="student_teacher_messages",
    )

    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="teacher_student_messages",
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="student_teacher_messages",
    )

    message_subject = models.CharField(
        max_length=200,
        default="Message from Student",
    )

    message = models.TextField()

    is_read = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return (
            f"{self.student.username} → "
            f"{self.teacher.username} → "
            f"{self.subject.subject_name}"
        )


class Assignment(models.Model):

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="assignments",
    )

    class_section = models.ForeignKey(
        ClassSection,
        on_delete=models.CASCADE,
        related_name="assignments",
    )

    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="created_assignments",
    )

    title = models.CharField(
        max_length=200
    )

    description = models.TextField(
        blank=True,
        null=True
    )

    assignment_file = models.FileField(
        upload_to="assignments/"
    )

    due_date = models.DateField(
        null=True,
        blank=True
    )

    academic_year = models.CharField(
        max_length=20
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.subject.subject_name} - "
            f"{self.title}"
        )


class AssignmentSubmission(models.Model):

    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name="submissions",
    )

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="assignment_submissions",
    )

    submission_file = models.FileField(
        upload_to="assignment_submissions/"
    )

    comment = models.TextField(
        blank=True,
        null=True
    )

    submitted_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        unique_together = (
            "assignment",
            "student",
        )
        ordering = ["-submitted_at"]

    def __str__(self):
        return (
            f"{self.student.username} - "
            f"{self.assignment.title}"
        )