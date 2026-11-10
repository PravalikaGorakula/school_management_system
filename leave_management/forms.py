from django import forms
from django.contrib.auth.models import User

from .models import LeaveRequest


class LeaveRequestForm(forms.ModelForm):

    class Meta:
        model = LeaveRequest

        fields = [
            "leave_type",
            "from_date",
            "to_date",
            "reason",
        ]

        widgets = {
            "leave_type": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "from_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),

            "to_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),

            "reason": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": "Enter reason for leave",
                }
            ),
        }

    def clean(self):

        cleaned_data = super().clean()

        from_date = cleaned_data.get("from_date")
        to_date = cleaned_data.get("to_date")

        if from_date and to_date:

            if to_date < from_date:

                raise forms.ValidationError(
                    "To date cannot be earlier than from date."
                )

        return cleaned_data