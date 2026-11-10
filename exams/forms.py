from django import forms

from academics.models import ClassSection, Subject
from .models import Examination, ExamClassSubjectAssignment


# =====================================================
# EXAMINATION FORM
# =====================================================

class ExaminationForm(forms.ModelForm):

    class Meta:
        model = Examination

        # Description, start_time, end_time ikkada levu
        fields = [
            "exam_name",
            "exam_type",
            "academic_year",
            "start_date",
            "end_date",
        ]

        widgets = {
            "exam_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter examination name",
            }),

            "exam_type": forms.Select(attrs={
                "class": "form-control",
            }),

            "academic_year": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Example: 2026-27",
            }),

            "start_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),

            "end_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
        }

    def clean(self):
        cleaned_data = super().clean()

        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if start_date and end_date and end_date < start_date:
            self.add_error(
                "end_date",
                "End date must be on or after the start date."
            )

        return cleaned_data


# =====================================================
# EXAM CLASS / SECTION / SUBJECT ASSIGNMENT FORM
# =====================================================

class ExamAssignmentForm(forms.ModelForm):

    class Meta:
        model = ExamClassSubjectAssignment

        fields = [
            "class_section",
            "subject",
            "exam_date",
            "start_time",
            "end_time",
            "max_marks",
            "passing_marks",
        ]

        widgets = {
            "class_section": forms.Select(attrs={
                "class": "form-control",
            }),

            "subject": forms.Select(attrs={
                "class": "form-control",
            }),
            "exam_date": forms.DateInput(attrs={
            "class": "form-control",
            "type": "date",
            }),

            "start_time": forms.TimeInput(attrs={
                "class": "form-control",
                "type": "time",
            }),

            "end_time": forms.TimeInput(attrs={
                "class": "form-control",
                "type": "time",
            }),

            "max_marks": forms.NumberInput(attrs={
                "class": "form-control",
                "min": "1",
                "step": "1",
            }),

            "passing_marks": forms.NumberInput(attrs={
                "class": "form-control",
                "min": "0",
                "step": "1",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Display all class sections
        self.fields["class_section"].queryset = (
            ClassSection.objects.all().order_by(
            "grade",
            "section",
            )
        )
        self.fields["class_section"].required = False
        self.fields["class_section"].empty_label = "All Classes & Sections"
        # Display all subjects
        self.fields["subject"].queryset = (
            Subject.objects.all().order_by("subject_name")
        )

    def clean(self):
        cleaned_data = super().clean()

        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")
        max_marks = cleaned_data.get("max_marks")
        passing_marks = cleaned_data.get("passing_marks")

        if (
            start_time
            and end_time
            and end_time <= start_time
        ):
            self.add_error(
                "end_time",
                "End time must be later than start time."
            )

        if (
            max_marks is not None
            and passing_marks is not None
            and passing_marks > max_marks
        ):
            self.add_error(
                "passing_marks",
                "Passing marks cannot exceed maximum marks."
            )

        return cleaned_data