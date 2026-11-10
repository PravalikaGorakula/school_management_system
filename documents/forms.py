from django import forms

from .models import Document


class DocumentForm(forms.ModelForm):

    class Meta:
        model = Document

        fields = [
            "category",
            "document_type",
            "name",
            "file",
            "description",
        ]

        widgets = {

            "category": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "document_type": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter document name",
                }
            ),

            "file": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Enter document description",
                }
            ),
        }

    def clean_name(self):

        name = self.cleaned_data.get("name")

        if name:
            name = name.strip()

        if not name:
            raise forms.ValidationError(
                "Document name is required."
            )

        return name

    def clean_file(self):

        uploaded_file = self.cleaned_data.get("file")

        if not uploaded_file:
            raise forms.ValidationError(
                "Please select a document file."
            )

        # Maximum file size: 10 MB
        max_size = 10 * 1024 * 1024

        if uploaded_file.size > max_size:
            raise forms.ValidationError(
                "File size must not exceed 10 MB."
            )

        allowed_extensions = [
            ".pdf",
            ".jpg",
            ".jpeg",
            ".png",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
        ]

        file_name = uploaded_file.name.lower()

        if not any(
            file_name.endswith(extension)
            for extension in allowed_extensions
        ):
            raise forms.ValidationError(
                "Only PDF, JPG, JPEG, PNG, DOC, DOCX, XLS and XLSX files are allowed."
            )

        return uploaded_file