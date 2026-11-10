from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import (
    FeeStructure,
    BankStatementEntry,
    StudentFee,
    FeePayment,
    SchoolExpense,
    StaffSalary,
)

class FeeStructureForm(forms.ModelForm):

    class Meta:
        model = FeeStructure

        fields = [
            "academic_year",
            "target_class",
            "installment_name",
            "fee_type",
            "description",
            "total_amount",
            "due_date",
        ]

        widgets = {
            "academic_year": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Example: 2026-27",
            }),

            "target_class": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Example: Grade 5",
            }),

            "installment_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Example: Term 1 / Full Year",
            }),

            "fee_type": forms.Select(attrs={
                "class": "form-control",
            }),

            "description": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter fee details",
            }),

            "total_amount": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "Enter amount",
                "min": "0.01",
                "step": "0.01",
            }),

            "due_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
        }

    def clean_academic_year(self):
        academic_year = self.cleaned_data["academic_year"].strip()

        if not academic_year:
            raise ValidationError("Academic year is required.")

        return academic_year

    def clean_target_class(self):
        target_class = self.cleaned_data["target_class"].strip()

        if not target_class:
            raise ValidationError("Class is required.")

        return target_class

    def clean_installment_name(self):
        installment_name = (
            self.cleaned_data["installment_name"].strip()
        )

        if not installment_name:
            raise ValidationError("Installment name is required.")

        return installment_name

    def clean_total_amount(self):
        amount = self.cleaned_data["total_amount"]

        if amount <= 0:
            raise ValidationError(
                "Fee amount must be greater than zero."
            )

        return amount

    def clean(self):
        cleaned_data = super().clean()

        academic_year = cleaned_data.get("academic_year")
        target_class = cleaned_data.get("target_class")
        installment_name = cleaned_data.get("installment_name")
        fee_type = cleaned_data.get("fee_type")

        if all([
            academic_year,
            target_class,
            installment_name,
            fee_type,
        ]):
            duplicate = FeeStructure.objects.filter(
                academic_year__iexact=academic_year,
                target_class__iexact=target_class,
                installment_name__iexact=installment_name,
                fee_type=fee_type,
            )

            if self.instance.pk:
                duplicate = duplicate.exclude(
                    pk=self.instance.pk
                )

            if duplicate.exists():
                raise ValidationError(
                    "This fee structure already exists for "
                    "the selected academic year, class, "
                    "installment and fee type."
                )

        return cleaned_data

class StudentFeeForm(forms.ModelForm):
    class Meta:
        model = StudentFee
        fields = [
            "student",
            "academic_year",
            "fee_type",
            "description",
            "total_amount",
            "due_date",
        ]
        widgets = {
            "due_date": forms.DateInput(
                attrs={"type": "date"}
            ),
            "description": forms.TextInput(
                attrs={"placeholder": "Fee details"}
            ),
        }

    def clean_total_amount(self):
        amount = self.cleaned_data["total_amount"]
        if amount <= 0:
            raise ValidationError("Fee amount must be greater than zero.")
        return amount

class FeePaymentForm(forms.ModelForm):
    class Meta:
        model = FeePayment
        fields = [
            "fee",
            "amount",
            "payment_method",
            "transaction_reference",
            "remarks",
        ]
        widgets = {
            "remarks": forms.TextInput(
                attrs={"placeholder": "Optional remarks"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fee"].queryset = StudentFee.objects.select_related(
            "student"
        ).order_by("-created_at")

    def clean(self):
        cleaned_data = super().clean()
        fee = cleaned_data.get("fee")
        amount = cleaned_data.get("amount")

        if fee and amount:
            if amount <= 0:
                self.add_error("amount", "Enter an amount greater than zero.")
            elif amount > fee.balance:
                self.add_error(
                    "amount",
                    f"Payment cannot exceed the pending balance "
                    f"of ₹{fee.balance}.",
                )

        return cleaned_data

class SchoolExpenseForm(forms.ModelForm):
    class Meta:
        model = SchoolExpense
        fields = [
            "title",
            "category",
            "amount",
            "expense_date",
            "vendor",
            "bill_number",
            "bill_file",
            "notes",
        ]
        widgets = {
            "expense_date": forms.DateInput(
                attrs={"type": "date"}
            ),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise ValidationError("Expense amount must be greater than zero.")
        return amount

    def clean_bill_file(self):
        uploaded_file = self.cleaned_data.get("bill_file")

        if uploaded_file:
            allowed_extensions = (".pdf", ".jpg", ".jpeg", ".png")
            if not uploaded_file.name.lower().endswith(allowed_extensions):
                raise ValidationError(
                    "Upload only PDF, JPG, JPEG or PNG bills."
                )

            if uploaded_file.size > 5 * 1024 * 1024:
                raise ValidationError(
                    "Bill file size must be 5 MB or less."
                )

        return uploaded_file

class StaffSalaryForm(forms.ModelForm):
    class Meta:
        model = StaffSalary
        fields = [
            "employee",
            "month",
            "year",
            "basic_salary",
            "allowances",
            "deductions",
            "notes",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_month(self):
        month = self.cleaned_data["month"]
        if not 1 <= month <= 12:
            raise ValidationError("Month must be between 1 and 12.")
        return month

    def clean_year(self):
        year = self.cleaned_data["year"]
        if not 2000 <= year <= timezone.localdate().year + 1:
            raise ValidationError("Enter a valid salary year.")
        return year

    def clean(self):
        cleaned_data = super().clean()
        basic = cleaned_data.get("basic_salary")
        allowances = cleaned_data.get("allowances")
        deductions = cleaned_data.get("deductions")

        if basic is not None and basic < 0:
            self.add_error("basic_salary", "Salary cannot be negative.")

        if allowances is not None and allowances < 0:
            self.add_error("allowances", "Allowances cannot be negative.")

        if deductions is not None and deductions < 0:
            self.add_error("deductions", "Deductions cannot be negative.")

        if (
            basic is not None
            and allowances is not None
            and deductions is not None
            and basic + allowances - deductions < 0
        ):
            self.add_error(
                "deductions",
                "Deductions cannot exceed basic salary plus allowances.",
            )

        return cleaned_data

class BankStatementEntryForm(forms.ModelForm):
    class Meta:
        model = BankStatementEntry
        fields = ["statement_date", "bank_reference", "description", "amount"]
        widgets = {
            "statement_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.TextInput(attrs={
                "placeholder": "Optional bank narration"
            }),
            "bank_reference": forms.TextInput(attrs={
                "placeholder": "Exact UPI / bank transaction reference"
            }),
            "amount": forms.NumberInput(attrs={
                "min": "0.01", "step": "0.01"
            }),
        }

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise ValidationError("Statement amount must be greater than zero.")
        return amount

    def clean_bank_reference(self):
        value = self.cleaned_data["bank_reference"].strip()
        if not value:
            raise ValidationError("Bank reference is required for reconciliation.")
        return value
