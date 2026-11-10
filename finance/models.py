from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum
from django.utils import timezone

from admissions.models import (
    StudentAdmissionApplication,
    EmployeeAdmissionApplication,
)

class FeeStructure(models.Model):

    FEE_TYPES = [
        ("tuition", "Tuition Fee"),
        ("admission", "Admission Fee"),
        ("transport", "Transport Fee"),
        ("exam", "Examination Fee"),
        ("other", "Other Fee"),
    ]

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("published", "Published"),
    ]

    academic_year = models.CharField(
        max_length=20,
        default="2026-27",
    )

    target_class = models.CharField(
        max_length=60,
    )

    installment_name = models.CharField(
        max_length=80,
        default="Full Year",
    )

    fee_type = models.CharField(
        max_length=20,
        choices=FEE_TYPES,
        default="tuition",
    )

    description = models.CharField(
        max_length=200,
        blank=True,
    )

    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.01"))
        ],
    )

    due_date = models.DateField(
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_fee_structures",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    published_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "academic_year",
                    "target_class",
                    "installment_name",
                    "fee_type",
                ],
                name="unique_fee_structure_class_year_installment_type",
            )
        ]

    def __str__(self):
        return (
            f"{self.academic_year} - "
            f"{self.target_class} - "
            f"{self.installment_name} - "
            f"{self.get_fee_type_display()}"
        )

class StudentFee(models.Model):

    FEE_TYPES = [
        ("tuition", "Tuition Fee"),
        ("admission", "Admission Fee"),
        ("transport", "Transport Fee"),
        ("exam", "Examination Fee"),
        ("other", "Other Fee"),
    ]

    student = models.ForeignKey(
        StudentAdmissionApplication,
        on_delete=models.PROTECT,
        related_name="finance_fee_records",
    )
    fee_structure = models.ForeignKey(
    "FeeStructure",
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="student_demands",
    )

    academic_year = models.CharField(
        max_length=20,
        default="2026-27",
    )

    fee_type = models.CharField(
        max_length=20,
        choices=FEE_TYPES,
        default="tuition",
    )

    description = models.CharField(
        max_length=200,
        blank=True,
    )

    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    due_date = models.DateField(
        null=True,
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_student_fees",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-created_at"]

    @property
    def paid_amount(self):
        total = self.payments.aggregate(
            total=Sum("amount")
        )["total"]

        return total or Decimal("0.00")

    @property
    def balance(self):
        return max(
            Decimal("0.00"),
            self.total_amount - self.paid_amount,
        )

    @property
    def payment_status(self):
        if self.paid_amount <= 0:
            return "Pending"

        if self.paid_amount >= self.total_amount:
            return "Paid"

        return "Partially Paid"

    def __str__(self):
        return (
            f"{self.student.application_id} - "
            f"{self.get_fee_type_display()}"
        )

class FeePayment(models.Model):

    PAYMENT_METHODS = [
        ("cash", "Cash"),
        ("upi", "UPI"),
        ("bank_transfer", "Bank Transfer"),
        ("card", "Card"),
        ("cheque", "Cheque"),
    ]

    fee = models.ForeignKey(
        StudentFee,
        on_delete=models.PROTECT,
        related_name="payments",
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS,
        default="cash",
    )

    transaction_reference = models.CharField(
        max_length=100,
        blank=True,
    )

    receipt_number = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
    )

    remarks = models.CharField(
        max_length=250,
        blank=True,
    )

    collected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="collected_fee_payments",
    )

    paid_at = models.DateTimeField(
        default=timezone.now,
    )

    class Meta:
        ordering = ["-paid_at"]

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            prefix = timezone.localdate().strftime(
                "RCPT%Y%m%d"
            )

            last_number = (
                FeePayment.objects.filter(
                    receipt_number__startswith=prefix
                ).count() + 1
            )

            self.receipt_number = (
                f"{prefix}-{last_number:04d}"
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return self.receipt_number or f"Payment {self.pk}"

class SchoolExpense(models.Model):

    CATEGORIES = [
        ("utilities", "Electricity / Water / Internet"),
        ("stationery", "Stationery"),
        ("maintenance", "Maintenance"),
        ("transport", "Transport"),
        ("salary", "Salary Related"),
        ("supplies", "School Supplies"),
        ("other", "Other"),
    ]

    APPROVAL_STATUS = [
        ("pending", "Pending Approval"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    title = models.CharField(
        max_length=150,
    )

    category = models.CharField(
        max_length=20,
        choices=CATEGORIES,
        default="other",
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    expense_date = models.DateField(
        default=timezone.localdate,
    )

    vendor = models.CharField(
        max_length=150,
        blank=True,
    )

    bill_number = models.CharField(
        max_length=100,
        blank=True,
    )

    bill_file = models.FileField(
        upload_to="finance/expense_bills/",
        blank=True,
        null=True,
    )

    notes = models.TextField(
        blank=True,
    )

    approval_status = models.CharField(
        max_length=20,
        choices=APPROVAL_STATUS,
        default="pending",
    )

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="submitted_school_expenses",
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_school_expenses",
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    review_note = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-expense_date", "-created_at"]

    def __str__(self):
        return f"{self.title} - Rs. {self.amount}"

class StaffSalary(models.Model):

    PAYMENT_STATUS = [
        ("unpaid", "Unpaid"),
        ("paid", "Paid"),
    ]

    employee = models.ForeignKey(
        EmployeeAdmissionApplication,
        on_delete=models.PROTECT,
        related_name="finance_salary_records",
    )

    month = models.PositiveSmallIntegerField()

    year = models.PositiveSmallIntegerField()

    basic_salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    allowances = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    deductions = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    status = models.CharField(
        max_length=10,
        choices=PAYMENT_STATUS,
        default="unpaid",
    )

    paid_on = models.DateField(
        null=True,
        blank=True,
    )

    notes = models.TextField(
        blank=True,
    )

    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="recorded_staff_salaries",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = [
            "-year",
            "-month",
            "employee__first_name",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["employee", "month", "year"],
                name="unique_staff_salary_month_year",
            )
        ]

    @property
    def net_salary(self):
        return (
            self.basic_salary
            + self.allowances
            - self.deductions
        )

    def __str__(self):
        return (
            f"{self.employee.first_name} "
            f"{self.employee.last_name} - "
            f"{self.month}/{self.year}"
        )

class BankStatementEntry(models.Model):
    STATUS_CHOICES = [
        ("unmatched", "Unmatched"),
        ("matched", "Matched"),
    ]

    statement_date = models.DateField()
    bank_reference = models.CharField(max_length=100, db_index=True)
    description = models.CharField(max_length=250, blank=True)
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    matched_payment = models.ForeignKey(
        FeePayment,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="bank_statement_matches",
    )
    status = models.CharField(
        max_length=12,
        choices=STATUS_CHOICES,
        default="unmatched",
        db_index=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_bank_statement_entries",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-statement_date", "-created_at"]

    def __str__(self):
        return f"{self.statement_date} - {self.bank_reference} - {self.amount}"
