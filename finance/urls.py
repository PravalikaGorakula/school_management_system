from django.urls import path
from . import views

app_name = "finance"

urlpatterns = [
    path("", views.fee_management, name="fee_management"),

    path("fees/", views.fee_list, name="fee_list"),
    path("fees/add/", views.fee_create, name="fee_create"),
    path("fees/structures/", views.fee_structure_list, name="fee_structure_list"),
    path("fees/structures/add/", views.fee_structure_create, name="fee_structure_create"),
    path("fees/structures/<int:structure_id>/edit/", views.fee_structure_edit, name="fee_structure_edit"),
    path("fees/structures/<int:structure_id>/publish/", views.fee_structure_publish, name="fee_structure_publish"),

    path("payments/", views.payment_list, name="payment_list"),
    path("payments/add/", views.payment_create, name="payment_create"),
    path("payments/<int:payment_id>/receipt/", views.receipt, name="receipt"),

    path("payroll/", views.salary_list, name="salary_list"),
    path("payroll/add/", views.salary_create, name="salary_create"),
    path("payroll/<int:salary_id>/mark-paid/", views.salary_mark_paid, name="salary_mark_paid"),

    path("expenses/", views.expense_list, name="expense_list"),
    path("expenses/add/", views.expense_create, name="expense_create"),
    path("expenses/<int:expense_id>/review/", views.expense_review, name="expense_review"),

    path("reconciliation/", views.reconciliation, name="reconciliation"),
    path("reconciliation/add/", views.reconciliation_create, name="reconciliation_create"),
    path("reconciliation/<int:entry_id>/match/", views.reconciliation_match, name="reconciliation_match"),

    path("reports/", views.reports, name="reports"),
    path("alerts/", views.alerts, name="alerts"),
    path("audit-logs/", views.audit_logs, name="audit_logs"),
]
