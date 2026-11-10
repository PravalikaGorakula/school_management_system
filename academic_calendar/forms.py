from django import forms
from academics.models import ClassSection
from .models import AcademicCalendarEvent


class AcademicCalendarEventForm(forms.ModelForm):

    class Meta:
        model = AcademicCalendarEvent

        fields = [
            "title",
            "description",
            "event_type",
            "start_date",
            "end_date",
            "academic_year",
            "class_section",
            "status",
        ]

        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter event title",
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Enter event description",
            }),
            "event_type": forms.Select(attrs={
                "class": "form-control",
            }),
            "start_date": forms.DateInput(attrs={
                "type": "date",
                "class": "form-control",
            }),
            "end_date": forms.DateInput(attrs={
                "type": "date",
                "class": "form-control",
            }),
            "academic_year": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "2026-27",
            }),
            "class_section": forms.Select(attrs={
                "class": "form-control",
            }),
            "status": forms.Select(attrs={
                "class": "form-control",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["class_section"].queryset = (
            ClassSection.objects.all().order_by(
                "grade",
                "section",
            )
        )

        self.fields["class_section"].required = False

    def clean(self):
        cleaned_data = super().clean()

        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        academic_year = cleaned_data.get("academic_year")
        class_section = cleaned_data.get("class_section")

        if start_date and end_date and end_date < start_date:
            self.add_error(
                "end_date",
                "End date must be on or after start date.",
            )

        if (
            class_section
            and academic_year
            and class_section.academic_year != academic_year
        ):
            self.add_error(
                "class_section",
                "Select a class section from the chosen academic year.",
            )

        return cleaned_data