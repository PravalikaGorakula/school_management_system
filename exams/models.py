from django.db import models
from django.contrib.auth.models import User

from academics.models import ClassSection, Subject
from admissions.models import StudentAdmissionApplication


# =========================================================
# EXAMINATION
# =========================================================

class Examination(models.Model):

    EXAM_TYPE_CHOICES = [
        ("Unit Test", "Unit Test"),
        ("Mid Term", "Mid Term"),
        ("Quarterly", "Quarterly"),
        ("Half Yearly", "Half Yearly"),
        ("Annual", "Annual"),
        ("Final", "Final"),
        ("Other", "Other"),
    ]

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("published", "Published"),
        ("cancelled", "Cancelled"),
    ]

    exam_name = models.CharField(
        max_length=200
    )

    exam_type = models.CharField(
        max_length=50,
        choices=EXAM_TYPE_CHOICES
    )

    academic_year = models.CharField(
        max_length=20
    )

    start_date = models.DateField(
        verbose_name="Exam Start Date"
    )

    end_date = models.DateField(
        verbose_name="Exam End Date"
    )

    description = models.TextField(
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft"
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_examinations"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-start_date", "-created_at"]

    def __str__(self):
        return (
            f"{self.exam_name} - "
            f"{self.academic_year}"
        )


# =========================================================
# EXAM CLASS SUBJECT ASSIGNMENT
# =========================================================

class ExamClassSubjectAssignment(models.Model):

    examination = models.ForeignKey(
        Examination,
        on_delete=models.CASCADE,
        related_name="assignments"
    )

    class_section = models.ForeignKey(
        ClassSection,
        on_delete=models.CASCADE,
        related_name="exam_assignments"
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="exam_assignments"
    )
    exam_date = models.DateField(
    verbose_name="Exam Date",
    null=True,
    blank=True
    )

    # Subject examination start time
    start_time = models.TimeField(
        verbose_name="Start Time",
        null=True,
        blank=True
    )

    # Subject examination end time
    end_time = models.TimeField(
        verbose_name="End Time",
        null=True,
        blank=True
    )

    max_marks = models.PositiveIntegerField(
        default=100
    )

    passing_marks = models.PositiveIntegerField(
        default=35
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
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
                    "examination",
                    "class_section",
                    "subject",
                ],
                name="unique_exam_class_subject"
            )
        ]

    def __str__(self):
        return (
            f"{self.examination.exam_name} - "
            f"{self.class_section} - "
            f"{self.subject.subject_name}"
        )


# =========================================================
# EXAM MARK
# =========================================================

class ExamMark(models.Model):

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("published", "Published"),
    ]

    examination = models.ForeignKey(
        Examination,
        on_delete=models.CASCADE,
        related_name="marks"
    )

    assignment = models.ForeignKey(
        ExamClassSubjectAssignment,
        on_delete=models.CASCADE,
        related_name="marks"
    )

    student = models.ForeignKey(
        StudentAdmissionApplication,
        on_delete=models.CASCADE,
        related_name="exam_marks"
    )

    class_section = models.ForeignKey(
        ClassSection,
        on_delete=models.CASCADE,
        related_name="exam_marks"
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="exam_marks"
    )

    max_marks = models.PositiveIntegerField(
        default=100
    )

    obtained_marks = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0
    )

    percentage = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0
    )

    grade = models.CharField(
        max_length=5,
        blank=True
    )

    remarks = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft"
    )

    entered_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="entered_exam_marks"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = [
            "student__first_name",
            "student__last_name",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "assignment",
                    "student",
                ],
                name="unique_exam_assignment_student"
            )
        ]

    def calculate_percentage(self):

        if self.max_marks:
            return round(
                (
                    float(self.obtained_marks)
                    / float(self.max_marks)
                ) * 100,
                2
            )

        return 0

    def calculate_grade(self):

        percentage = self.calculate_percentage()

        if percentage >= 90:
            return "A+"

        if percentage >= 80:
            return "A"

        if percentage >= 70:
            return "B+"

        if percentage >= 60:
            return "B"

        if percentage >= 50:
            return "C"

        if percentage >= 40:
            return "D"

        return "F"

    def save(self, *args, **kwargs):

        self.examination = self.assignment.examination
        self.class_section = self.assignment.class_section
        self.subject = self.assignment.subject
        self.max_marks = self.assignment.max_marks

        self.percentage = self.calculate_percentage()
        self.grade = self.calculate_grade()

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.student.application_id} - "
            f"{self.subject.subject_name} - "
            f"{self.obtained_marks}"
        )