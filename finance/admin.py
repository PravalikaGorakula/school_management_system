from django.contrib import admin
from .models import (
    FeeStructure,
    StudentFee,
    FeePayment,
    SchoolExpense,
    StaffSalary,
    BankStatementEntry,
)


@admin.register(StudentFee)
class StudentFeeAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "academic_year",
        "fee_type",
        "total_amount",
        "due_date",
        "created_at",
    )

    list_filter = (
        "academic_year",
        "fee_type",
    )

    search_fields = (
        "student__application_id",
        "student__first_name",
        "student__last_name",
    )


@admin.register(FeePayment)
class FeePaymentAdmin(admin.ModelAdmin):
    list_display = (
        "receipt_number",
        "fee",
        "amount",
        "payment_method",
        "collected_by",
        "paid_at",
    )

    list_filter = (
        "payment_method",
        "paid_at",
    )

    search_fields = (
        "receipt_number",
        "transaction_reference",
    )


@admin.register(SchoolExpense)
class SchoolExpenseAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "amount",
        "expense_date",
        "approval_status",
        "submitted_by",
    )

    list_filter = (
        "category",
        "approval_status",
        "expense_date",
    )

    search_fields = (
        "title",
        "vendor",
        "bill_number",
    )


@admin.register(StaffSalary)
class StaffSalaryAdmin(admin.ModelAdmin):
    list_display = (
        "employee",
        "month",
        "year",
        "basic_salary",
        "net_salary",
        "status",
    )

    list_filter = (
        "month",
        "year",
        "status",
    )

    search_fields = (
        "employee__first_name",
        "employee__last_name",
        "employee__application_id",
    )

@admin.register(BankStatementEntry)
class BankStatementEntryAdmin(admin.ModelAdmin):
    list_display = (
        "statement_date",
        "bank_reference",
        "amount",
        "status",
        "matched_payment",
        "created_by",
    )
    list_filter = ("status", "statement_date")
    search_fields = ("bank_reference", "description", "matched_payment__receipt_number")
