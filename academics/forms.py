from django import forms
from django.contrib.auth.models import User
from .models import (
    ClassSection,
    Subject,
    SubjectEmployeeAssignment,
    TimetableEntry,
    SubjectPeriodRequirement,
)

class ClassSectionForm(forms.ModelForm):

    class_teacher = forms.ModelChoiceField(
        queryset=User.objects.filter(
            is_active=True,
            profile__role="teacher"
        ).order_by(
            "first_name",
            "last_name",
            "username"
        ),
        required=False,
        empty_label="Select Class Teacher",
        widget=forms.Select(
            attrs={
                "class": "form-control"
            }
        )
    )

    class Meta:
        model = ClassSection

        fields = [
            "grade",
            "grade_group",
            "section",
            "academic_year",
            "capacity",
            "class_teacher",
            "status",
        ]

        widgets = {
            "grade": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: Grade 10"
                }
            ),

            "grade_group": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: Secondary"
                }
            ),

            "section": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: A"
                }
            ),

            "academic_year": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: 2026-27"
                }
            ),

            "capacity": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: 40",
                    "min": "1"
                }
            ),

            "status": forms.Select(
                attrs={
                    "class": "form-control"
                }
            ),
        }

    def clean_grade(self):
        grade = self.cleaned_data.get("grade")

        if grade:
            grade = grade.strip()

        return grade

    def clean_section(self):
        section = self.cleaned_data.get("section")

        if section:
            section = section.strip().upper()

        return section

    def clean_academic_year(self):
        academic_year = self.cleaned_data.get("academic_year")

        if academic_year:
            academic_year = academic_year.strip()

        return academic_year

    def clean_capacity(self):
        capacity = self.cleaned_data.get("capacity")

        if capacity is not None and capacity <= 0:
            raise forms.ValidationError(
                "Capacity must be greater than 0."
            )

        return capacity

class SubjectForm(forms.ModelForm):

    class Meta:
        model = Subject

        fields = [
            "subject_name",
            "subject_code",
            "subject_type",
            "department",
            "description",
            "is_active",
        ]

        widgets = {
            "subject_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: Mathematics"
                }
            ),

            "subject_code": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: MAT101"
                }
            ),

            "subject_type": forms.Select(
                attrs={
                    "class": "form-control"
                }
            ),

            "department": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: Science"
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter subject description",
                    "rows": 4
                }
            ),

            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input"
                }
            ),
        }

    def clean_subject_name(self):
        subject_name = self.cleaned_data.get("subject_name")

        if subject_name:
            subject_name = subject_name.strip()

        return subject_name

    def clean_subject_code(self):
        subject_code = self.cleaned_data.get("subject_code")

        if subject_code:
            subject_code = subject_code.strip().upper()

        return subject_code

    def clean_department(self):
        department = self.cleaned_data.get("department")

        if department:
            department = department.strip()

        return department

    def clean_description(self):
        description = self.cleaned_data.get("description")

        if description:
            description = description.strip()

        return description

class SubjectEmployeeAssignmentForm(forms.ModelForm):

    subject = forms.ModelChoiceField(
        queryset=Subject.objects.filter(
            is_active=True
        ).order_by("subject_name"),
        required=True,
        empty_label="Select Subject",
        widget=forms.Select(
            attrs={"class": "form-control"}
        )
    )

    employee = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=True,
        empty_label="Select Employee / Teacher",
        widget=forms.Select(
            attrs={"class": "form-control"}
        )
    )

    class_section = forms.ModelChoiceField(
        queryset=ClassSection.objects.all().order_by(
            "grade",
            "section"
        ),
        required=True,
        empty_label="Select Class & Section",
        widget=forms.Select(
            attrs={"class": "form-control"}
        )
    )

    class Meta:
        model = SubjectEmployeeAssignment

        fields = [
            "subject",
            "employee",
            "class_section",
            "academic_year",
            "is_active",
        ]

        widgets = {
            "academic_year": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: 2026-27",
                }
            ),

            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Get all active teacher accounts
        teachers = User.objects.filter(
            is_active=True,
            profile__role="teacher",
            profile__is_active=True,
        ).select_related(
            "profile"
        ).order_by(
            "first_name",
            "last_name",
            "username",
        )

        # Set employee dropdown queryset
        self.fields["employee"].queryset = teachers

        # Display employee name and username
        self.fields["employee"].label_from_instance = (
            self.employee_label
        )

    @staticmethod
    def employee_label(employee):
        full_name = employee.get_full_name().strip()

        if full_name:
            return f"{full_name} ({employee.username})"

        return employee.username

    def clean_academic_year(self):
        value = self.cleaned_data.get("academic_year")

        if value:
            value = value.strip()

        return value

class TimetableEntryForm(forms.ModelForm):

    class_section = forms.ModelChoiceField(
        queryset=ClassSection.objects.filter(
            status="Active"
        ).order_by(
            "grade",
            "section"
        ),
        required=True,
        empty_label="Select Class & Section",
        widget=forms.Select(
            attrs={
                "class": "form-control"
            }
        )
    )

    subject = forms.ModelChoiceField(
        queryset=Subject.objects.filter(
            is_active=True
        ).order_by(
            "subject_name"
        ),
        required=True,
        empty_label="Select Subject",
        widget=forms.Select(
            attrs={
                "class": "form-control"
            }
        )
    )

    employee = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=True,
        empty_label="Select Teacher",
        widget=forms.Select(
            attrs={
                "class": "form-control"
            }
        )
    )

    day = forms.ChoiceField(
        choices=TimetableEntry.DAY_CHOICES,
        required=True,
        widget=forms.Select(
            attrs={
                "class": "form-control"
            }
        )
    )

    period = forms.ChoiceField(
        choices=[
            (1, "Period 1"),
            (2, "Period 2"),
            (3, "Period 3"),
            (4, "Period 4"),
            (5, "Period 5"),
            (6, "Period 6"),
            (7, "Period 7"),
            (8, "Period 8"),
            (9, "Period 9"),
            (10, "Period 10"),
            (11, "Period 11"),
            (12, "Period 12"),
        ],
        required=True,
        widget=forms.Select(
            attrs={
                "class": "form-control"
            }
        )
    )

    class Meta:
        model = TimetableEntry

        fields = [
            "class_section",
            "subject",
            "employee",
            "day",
            "period",
            "academic_year",
            "room",
        ]

        widgets = {
            "academic_year": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: 2026-27",
                }
            ),

            "room": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: Room 101",
                }
            ),
        }

    def clean_academic_year(self):
        value = self.cleaned_data.get("academic_year")

        if value:
            value = value.strip()

        return value

    def clean(self):

        cleaned_data = super().clean()

        class_section = cleaned_data.get(
            "class_section"
        )

        subject = cleaned_data.get(
            "subject"
        )

        employee = cleaned_data.get(
            "employee"
        )

        day = cleaned_data.get(
            "day"
        )

        period = cleaned_data.get(
            "period"
        )

        academic_year = cleaned_data.get(
            "academic_year"
        )

        if not all([
            class_section,
            subject,
            employee,
            day,
            period,
            academic_year,
        ]):
            return cleaned_data

        period = int(period)

        # -------------------------------------------------
        # 1. CHECK SUBJECT + TEACHER + CLASS ASSIGNMENT
        # -------------------------------------------------

        assignment_exists = (
            SubjectEmployeeAssignment.objects.filter(
                subject=subject,
                employee=employee,
                class_section=class_section,
                academic_year=academic_year,
                is_active=True,
            ).exists()
        )

        if not assignment_exists:

            raise forms.ValidationError(
                "This teacher is not assigned to this subject and class for the selected academic year."
            )

        # -------------------------------------------------
        # 2. CHECK CLASS PERIOD CONFLICT
        # -------------------------------------------------

        class_conflict = (
            TimetableEntry.objects.filter(
                class_section=class_section,
                day=day,
                period=period,
                academic_year=academic_year,
                is_active=True,
            )
        )

        if self.instance.pk:
            class_conflict = class_conflict.exclude(
                pk=self.instance.pk
            )

        if class_conflict.exists():

            raise forms.ValidationError(
                "This class already has a timetable entry for the selected day and period."
            )

        # -------------------------------------------------
        # 3. CHECK TEACHER PERIOD CONFLICT
        # -------------------------------------------------

        teacher_conflict = (
            TimetableEntry.objects.filter(
                employee=employee,
                day=day,
                period=period,
                academic_year=academic_year,
                is_active=True,
            )
        )

        if self.instance.pk:
            teacher_conflict = teacher_conflict.exclude(
                pk=self.instance.pk
            )

        if teacher_conflict.exists():

            raise forms.ValidationError(
                "This teacher is already assigned to another class for the selected day and period."
            )

        return cleaned_data


class SubjectPeriodRequirementForm(forms.ModelForm):

    class_section = forms.ModelChoiceField(
        queryset=ClassSection.objects.filter(
            status="Active"
        ).order_by(
            "grade",
            "section"
        ),
        required=True,
        empty_label="Select Class & Section",
        widget=forms.Select(
            attrs={"class": "form-control"}
        ),
        label="Class & Section",
    )

    subject = forms.ModelChoiceField(
        queryset=Subject.objects.filter(
            is_active=True
        ).order_by("subject_name"),
        required=True,
        empty_label="Select Subject",
        widget=forms.Select(
            attrs={"class": "form-control"}
        ),
        label="Subject",
    )

    periods_per_week = forms.IntegerField(
        min_value=1,
        max_value=30,
        required=True,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": "1",
                "max": "30",
                "placeholder": "Example: 6",
            }
        ),
        label="Periods Per Week",
    )

    academic_year = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Example: 2026-27",
            }
        ),
        label="Academic Year",
    )

    class Meta:
        model = SubjectPeriodRequirement
        fields = [
            "class_section",
            "subject",
            "periods_per_week",
            "academic_year",
        ]

    def clean_academic_year(self):
        academic_year = self.cleaned_data.get("academic_year")

        if academic_year:
            academic_year = academic_year.strip()

        return academic_year

    def clean(self):
        cleaned_data = super().clean()

        class_section = cleaned_data.get("class_section")
        subject = cleaned_data.get("subject")
        academic_year = cleaned_data.get("academic_year")

        if not all([class_section, subject, academic_year]):
            return cleaned_data

        # Academic year must match the selected class.
        if academic_year != class_section.academic_year:
            self.add_error(
                "academic_year",
                "Academic year must match the selected class-section."
            )

        # A teacher must be assigned before configuring
        # the subject's weekly period requirement.
        assignment_exists = SubjectEmployeeAssignment.objects.filter(
            class_section=class_section,
            subject=subject,
            academic_year=academic_year,
            is_active=True,
            employee__is_active=True,
        ).exists()

        if not assignment_exists:
            self.add_error(
                "subject",
                "No active teacher assignment exists for this subject "
                "and class in the selected academic year. "
                "Please assign a teacher first."
            )

        # Prevent duplicate subject requirements.
        duplicate = SubjectPeriodRequirement.objects.filter(
            class_section=class_section,
            subject=subject,
            academic_year=academic_year,
        )

        if self.instance.pk:
            duplicate = duplicate.exclude(pk=self.instance.pk)

        if duplicate.exists():
            self.add_error(
                "subject",
                "A weekly period requirement already exists for this "
                "subject and class in the selected academic year."
            )

        return cleaned_data
