import csv
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Sum, Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from accounts.models import SystemActivityLog
from admissions.models import StudentAdmissionApplication, EmployeeAdmissionApplication

from .models import (
    StudentFee, FeePayment, SchoolExpense, StaffSalary, FeeStructure,
    BankStatementEntry,
)
from .forms import (
    StudentFeeForm, FeePaymentForm, SchoolExpenseForm, StaffSalaryForm,
    FeeStructureForm, BankStatementEntryForm,
)


def user_role(user):
    if not user.is_authenticated or not hasattr(user, "profile"):
        return None
    return user.profile.role


def require_finance_role(user):
    if user_role(user) != "accountant":
        raise PermissionDenied("Only the Accountant can access this page.")


def require_expense_reviewer(user):
    if user_role(user) not in ("principal", "vice_principal", "chairman"):
        raise PermissionDenied(
            "Only the Principal, Vice Principal or Chairman can review expenses."
        )


def _context(request, **kwargs):
    profile = getattr(request.user, "profile", None)
    base = {
        "role": getattr(profile, "role", ""),
        "role_display": profile.get_role_display() if profile else "",
    }
    base.update(kwargs)
    return base


def _audit(request, action, description):
    try:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        ip = forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR")
        SystemActivityLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            module="Finance",
            action=action,
            description=description,
            ip_address=ip or None,
        )
    except Exception:
        # Logging must not make a valid finance transaction fail.
        pass


@login_required
def fee_management(request):
    require_finance_role(request.user)
    today = timezone.localdate()
    fees = StudentFee.objects.prefetch_related("payments")
    total_demand = sum((fee.total_amount for fee in fees), Decimal("0.00"))
    total_due = sum((fee.balance for fee in fees), Decimal("0.00"))
    total_paid = FeePayment.objects.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    total_expenses = SchoolExpense.objects.filter(
        approval_status="approved"
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    unpaid_payroll = StaffSalary.objects.filter(status="unpaid").count()
    overdue_count = sum(
        1 for fee in fees
        if fee.due_date and fee.due_date < today and fee.balance > 0
    )
    context = _context(
        request,
        total_demand=total_demand,
        total_paid=total_paid,
        total_due=total_due,
        total_expenses=total_expenses,
        fee_count=StudentFee.objects.count(),
        payment_count=FeePayment.objects.count(),
        unpaid_payroll=unpaid_payroll,
        pending_expenses=SchoolExpense.objects.filter(approval_status="pending").count(),
        overdue_count=overdue_count,
        recent_payments=FeePayment.objects.select_related("fee", "fee__student")[:8],
        recent_expenses=SchoolExpense.objects.all()[:5],
    )
    return render(request, "finance/home.html", context)


@login_required
def fee_structure_list(request):
    require_finance_role(request.user)
    structures = FeeStructure.objects.all().order_by("-created_at")
    status = request.GET.get("status", "").strip()
    academic_year = request.GET.get("academic_year", "").strip()
    if status:
        structures = structures.filter(status=status)
    if academic_year:
        structures = structures.filter(academic_year__icontains=academic_year)
    return render(request, "finance/fee_structure_list.html", _context(
        request,
        structures=structures,
        status=status,
        academic_year=academic_year,
        statuses=FeeStructure.STATUS_CHOICES,
    ))


@login_required
def fee_structure_create(request):
    require_finance_role(request.user)
    if request.method == "POST":
        form = FeeStructureForm(request.POST)
        if form.is_valid():
            structure = form.save(commit=False)
            structure.status = "draft"
            structure.created_by = request.user
            structure.save()
            _audit(request, "create", f"Created fee structure #{structure.pk}: {structure}.")
            messages.success(request, "Fee structure saved as Draft.")
            return redirect("finance:fee_structure_list")
    else:
        form = FeeStructureForm()
    return render(request, "finance/fee_structure_form.html", _context(
        request, form=form, page_title="Add Fee Structure"
    ))


@login_required
def fee_structure_edit(request, structure_id):
    require_finance_role(request.user)
    structure = get_object_or_404(FeeStructure, pk=structure_id)
    if structure.status == "published":
        messages.error(request, "Published fee structures cannot be edited.")
        return redirect("finance:fee_structure_list")
    if request.method == "POST":
        form = FeeStructureForm(request.POST, instance=structure)
        if form.is_valid():
            form.save()
            _audit(request, "update", f"Updated fee structure #{structure.pk}.")
            messages.success(request, "Fee structure updated.")
            return redirect("finance:fee_structure_list")
    else:
        form = FeeStructureForm(instance=structure)
    return render(request, "finance/fee_structure_form.html", _context(
        request, form=form, page_title="Edit Fee Structure"
    ))


@login_required
@require_POST
@transaction.atomic
def fee_structure_publish(request, structure_id):
    require_finance_role(request.user)
    structure = get_object_or_404(
        FeeStructure.objects.select_for_update(), pk=structure_id
    )
    if structure.status == "published":
        messages.info(request, "This fee structure is already published.")
        return redirect("finance:fee_structure_list")
    students = StudentAdmissionApplication.objects.filter(
        applying_class__iexact=structure.target_class.strip(),
        status="account_created",
    )
    if not students.exists():
        messages.error(
            request,
            "No account-created students found for this class. Check class name and admission status."
        )
        return redirect("finance:fee_structure_list")
    created_count = 0
    for student in students:
        _, created = StudentFee.objects.get_or_create(
            student=student,
            fee_structure=structure,
            defaults={
                "academic_year": structure.academic_year,
                "fee_type": structure.fee_type,
                "description": structure.description or structure.installment_name,
                "total_amount": structure.total_amount,
                "due_date": structure.due_date,
                "created_by": request.user,
            },
        )
        created_count += int(created)
    structure.status = "published"
    structure.published_at = timezone.now()
    structure.save(update_fields=["status", "published_at"])
    _audit(request, "approve", f"Published fee structure #{structure.pk}; created {created_count} student demands.")
    messages.success(request, f"Published successfully. {created_count} student fee demand(s) created.")
    return redirect("finance:fee_structure_list")


@login_required
def fee_list(request):
    require_finance_role(request.user)
    fees = StudentFee.objects.select_related("student").prefetch_related("payments")
    query = request.GET.get("q", "").strip()
    if query:
        from django.db.models import Q
        fees = fees.filter(
            Q(student__first_name__icontains=query)
            | Q(student__last_name__icontains=query)
            | Q(student__application_id__icontains=query)
            | Q(academic_year__icontains=query)
        )
    return render(request, "finance/fee_list.html", _context(
        request, fees=fees, query=query
    ))


@login_required
def fee_create(request):
    require_finance_role(request.user)
    if request.method == "POST":
        form = StudentFeeForm(request.POST)
        if form.is_valid():
            fee = form.save(commit=False)
            fee.created_by = request.user
            fee.save()
            _audit(request, "create", f"Created student fee demand #{fee.pk} for {fee.student}.")
            messages.success(request, "Student fee demand created.")
            return redirect("finance:fee_list")
    else:
        form = StudentFeeForm()
    return render(request, "finance/form.html", _context(
        request, form=form, page_title="Create Student Fee Demand",
        cancel_url="finance:fee_list", submit_label="Create Fee Demand"
    ))


@login_required
def payment_list(request):
    require_finance_role(request.user)
    payments = FeePayment.objects.select_related("fee", "fee__student", "collected_by")
    query = request.GET.get("q", "").strip()
    if query:
        from django.db.models import Q
        payments = payments.filter(
            Q(receipt_number__icontains=query)
            | Q(transaction_reference__icontains=query)
            | Q(fee__student__first_name__icontains=query)
            | Q(fee__student__last_name__icontains=query)
            | Q(fee__student__application_id__icontains=query)
        )
    return render(request, "finance/payment_list.html", _context(
        request, payments=payments, query=query
    ))


@login_required
@transaction.atomic
def payment_create(request):
    require_finance_role(request.user)
    if request.method == "POST":
        form = FeePaymentForm(request.POST)
        if form.is_valid():
            selected_fee = form.cleaned_data["fee"]
            fee = StudentFee.objects.select_for_update().get(pk=selected_fee.pk)
            amount = form.cleaned_data["amount"]
            if amount > fee.balance:
                form.add_error("amount", f"Payment exceeds current balance ₹{fee.balance:.2f}.")
            else:
                payment = form.save(commit=False)
                payment.fee = fee
                payment.collected_by = request.user
                payment.save()
                _audit(request, "create", f"Recorded payment {payment.receipt_number} for ₹{payment.amount}.")
                messages.success(request, f"Payment recorded. Receipt: {payment.receipt_number}")
                return redirect("finance:receipt", payment_id=payment.pk)
    else:
        form = FeePaymentForm()
    return render(request, "finance/form.html", _context(
        request, form=form, page_title="Record Fee Payment",
        cancel_url="finance:payment_list", submit_label="Record Payment"
    ))


@login_required
def receipt(request, payment_id):
    require_finance_role(request.user)
    payment = get_object_or_404(
        FeePayment.objects.select_related("fee", "fee__student", "collected_by"),
        pk=payment_id,
    )
    return render(request, "finance/receipt.html", _context(request, payment=payment))


@login_required
def salary_list(request):
    require_finance_role(request.user)
    salaries = StaffSalary.objects.select_related("employee", "recorded_by")
    status = request.GET.get("status", "").strip()
    month = request.GET.get("month", "").strip()
    year = request.GET.get("year", "").strip()
    if status:
        salaries = salaries.filter(status=status)
    if month.isdigit() and 1 <= int(month) <= 12:
        salaries = salaries.filter(month=int(month))
    if year.isdigit():
        salaries = salaries.filter(year=int(year))
    return render(request, "finance/salary_list.html", _context(
        request, salaries=salaries, status=status, month=month, year=year
    ))


@login_required
def salary_create(request):
    require_finance_role(request.user)
    if request.method == "POST":
        form = StaffSalaryForm(request.POST)
        if form.is_valid():
            salary = form.save(commit=False)
            salary.recorded_by = request.user
            salary.save()
            _audit(request, "create", f"Created payroll record #{salary.pk} for {salary.employee} ({salary.month}/{salary.year}).")
            messages.success(request, "Payroll record created.")
            return redirect("finance:salary_list")
    else:
        form = StaffSalaryForm()
    return render(request, "finance/form.html", _context(
        request, form=form, page_title="Create Payroll Record",
        cancel_url="finance:salary_list", submit_label="Save Payroll"
    ))


@login_required
@require_POST
def salary_mark_paid(request, salary_id):
    require_finance_role(request.user)
    salary = get_object_or_404(StaffSalary, pk=salary_id)
    if salary.status != "paid":
        salary.status = "paid"
        salary.paid_on = timezone.localdate()
        salary.save(update_fields=["status", "paid_on"])
        _audit(request, "approve", f"Marked salary #{salary.pk} paid for ₹{salary.net_salary}.")
        messages.success(request, "Salary marked as paid.")
    else:
        messages.info(request, "This salary is already marked as paid.")
    return redirect("finance:salary_list")


@login_required
def expense_list(request):
    if user_role(request.user) not in ("accountant", "principal", "vice_principal", "chairman"):
        raise PermissionDenied("You are not allowed to view finance expenses.")
    expenses = SchoolExpense.objects.select_related("submitted_by", "reviewed_by")
    status = request.GET.get("status", "").strip()
    if status:
        expenses = expenses.filter(approval_status=status)
    return render(request, "finance/expense_list.html", _context(
        request, expenses=expenses, status=status,
        can_review=user_role(request.user) in ("principal", "vice_principal", "chairman")
    ))


@login_required
def expense_create(request):
    require_finance_role(request.user)
    if request.method == "POST":
        form = SchoolExpenseForm(request.POST, request.FILES)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.submitted_by = request.user
            expense.approval_status = "pending"
            expense.save()
            _audit(request, "create", f"Submitted expense #{expense.pk}: {expense.title}, ₹{expense.amount}.")
            messages.success(request, "Expense submitted for management approval.")
            return redirect("finance:expense_list")
    else:
        form = SchoolExpenseForm()
    return render(request, "finance/form.html", _context(
        request, form=form, page_title="Submit School Expense",
        cancel_url="finance:expense_list", submit_label="Submit Expense",
        multipart=True
    ))


@login_required
@require_POST
def expense_review(request, expense_id):
    require_expense_reviewer(request.user)
    expense = get_object_or_404(SchoolExpense, pk=expense_id)
    decision = request.POST.get("decision")
    note = request.POST.get("review_note", "").strip()
    if expense.approval_status != "pending":
        messages.info(request, "This expense has already been reviewed.")
    elif decision not in ("approve", "reject"):
        messages.error(request, "Invalid expense review action.")
    else:
        expense.approval_status = "approved" if decision == "approve" else "rejected"
        expense.reviewed_by = request.user
        expense.reviewed_at = timezone.now()
        expense.review_note = note
        expense.save(update_fields=["approval_status", "reviewed_by", "reviewed_at", "review_note"])
        action = "approve" if decision == "approve" else "reject"
        _audit(request, action, f"{'Approved' if decision == 'approve' else 'Rejected'} expense #{expense.pk}: {expense.title}. Note: {note}")
        messages.success(request, "Expense approved successfully." if decision == "approve" else "Expense rejected successfully.")
    return redirect("finance:expense_list")


@login_required
def reconciliation(request):
    require_finance_role(request.user)
    entries = BankStatementEntry.objects.select_related("matched_payment", "created_by")
    status = request.GET.get("status", "").strip()
    query = request.GET.get("q", "").strip()
    if status:
        entries = entries.filter(status=status)
    if query:
        from django.db.models import Q
        entries = entries.filter(
            Q(bank_reference__icontains=query)
            | Q(description__icontains=query)
            | Q(matched_payment__receipt_number__icontains=query)
        )
    return render(request, "finance/reconciliation.html", _context(
        request, entries=entries, status=status, query=query,
        unmatched_count=BankStatementEntry.objects.filter(status="unmatched").count(),
        matched_count=BankStatementEntry.objects.filter(status="matched").count()
    ))


@login_required
def reconciliation_create(request):
    require_finance_role(request.user)
    if request.method == "POST":
        form = BankStatementEntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.created_by = request.user
            entry.status = "unmatched"
            entry.save()
            _audit(request, "create", f"Added bank statement entry #{entry.pk}, reference {entry.bank_reference}, amount ₹{entry.amount}.")
            messages.success(request, "Bank statement entry added. You can now match it.")
            return redirect("finance:reconciliation")
    else:
        form = BankStatementEntryForm()
    return render(request, "finance/form.html", _context(
        request, form=form, page_title="Add Bank Statement Entry",
        cancel_url="finance:reconciliation", submit_label="Add Statement Entry"
    ))


@login_required
@require_POST
@transaction.atomic
def reconciliation_match(request, entry_id):
    require_finance_role(request.user)
    entry = get_object_or_404(BankStatementEntry.objects.select_for_update(), pk=entry_id)
    if entry.status == "matched":
        messages.info(request, "This statement entry is already matched.")
        return redirect("finance:reconciliation")
    candidates = FeePayment.objects.filter(
        amount=entry.amount
    ).filter(
        transaction_reference__iexact=entry.bank_reference
    )
    if not candidates.exists():
        candidates = FeePayment.objects.filter(
            amount=entry.amount, receipt_number__iexact=entry.bank_reference
        )
    if candidates.count() != 1:
        messages.error(
            request,
            "Automatic match requires exactly one payment with the same amount and bank reference. Check the reference or reconcile manually."
        )
        return redirect("finance:reconciliation")
    payment = candidates.first()
    entry.matched_payment = payment
    entry.status = "matched"
    entry.save(update_fields=["matched_payment", "status"])
    _audit(request, "verify", f"Reconciled bank entry #{entry.pk} with receipt {payment.receipt_number}.")
    messages.success(request, f"Matched with receipt {payment.receipt_number}.")
    return redirect("finance:reconciliation")


@login_required
def reports(request):
    require_finance_role(request.user)
    today = timezone.localdate()
    start = request.GET.get("start", "").strip()
    end = request.GET.get("end", "").strip()
    start_date = parse_date(start) if start else None
    end_date = parse_date(end) if end else None
    if start and not start_date:
        messages.error(request, "Start date is invalid.")
        start = ""
    if end and not end_date:
        messages.error(request, "End date is invalid.")
        end = ""
    if start_date and end_date and start_date > end_date:
        messages.error(request, "Start date cannot be after end date.")
        start = end = ""
        start_date = end_date = None
    payments = FeePayment.objects.select_related("fee", "fee__student")
    expenses = SchoolExpense.objects.filter(approval_status="approved")
    salaries = StaffSalary.objects.all()
    if start_date:
        payments = payments.filter(paid_at__date__gte=start_date)
        expenses = expenses.filter(expense_date__gte=start_date)
        salaries = salaries.filter(paid_on__gte=start_date)
    if end_date:
        payments = payments.filter(paid_at__date__lte=end_date)
        expenses = expenses.filter(expense_date__lte=end_date)
        salaries = salaries.filter(paid_on__lte=end_date)
    collected = payments.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    expense_total = expenses.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    payroll_total = sum((s.net_salary for s in salaries if s.status == "paid"), Decimal("0.00"))
    fees = StudentFee.objects.prefetch_related("payments")
    dues = sum((f.balance for f in fees), Decimal("0.00"))
    export_type = request.GET.get("export", "")
    if export_type:
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="finance_{export_type}_{today.isoformat()}.csv"'
        response.write("\ufeff")
        writer = csv.writer(response)
        if export_type == "collections":
            writer.writerow(["Receipt", "Date", "Student ID", "Student", "Amount", "Method", "Reference"])
            for p in payments:
                writer.writerow([p.receipt_number, p.paid_at.isoformat(), p.fee.student.application_id, f"{p.fee.student.first_name} {p.fee.student.last_name}", p.amount, p.get_payment_method_display(), p.transaction_reference])
        elif export_type == "expenses":
            writer.writerow(["Date", "Title", "Category", "Vendor", "Bill Number", "Amount", "Status"])
            for e in expenses:
                writer.writerow([e.expense_date, e.title, e.get_category_display(), e.vendor, e.bill_number, e.amount, e.approval_status])
        elif export_type == "dues":
            writer.writerow(["Student ID", "Student", "Academic Year", "Fee Type", "Demand", "Paid", "Balance", "Due Date"])
            for f in fees:
                if f.balance > 0:
                    writer.writerow([f.student.application_id, f"{f.student.first_name} {f.student.last_name}", f.academic_year, f.get_fee_type_display(), f.total_amount, f.paid_amount, f.balance, f.due_date or ""])
        elif export_type == "payroll":
            writer.writerow(["Employee", "Month", "Year", "Basic", "Allowances", "Deductions", "Net Salary", "Status", "Paid On"])
            for s in salaries:
                writer.writerow([f"{s.employee.first_name} {s.employee.last_name}", s.month, s.year, s.basic_salary, s.allowances, s.deductions, s.net_salary, s.status, s.paid_on or ""])
        else:
            return HttpResponse("Unknown report type.", status=400)
        _audit(request, "download", f"Exported finance report: {export_type}.")
        return response
    return render(request, "finance/reports.html", _context(
        request, start=start, end=end, collected=collected,
        expense_total=expense_total, payroll_total=payroll_total, dues=dues,
        payment_count=payments.count(), expense_count=expenses.count(),
        salary_count=salaries.count()
    ))


@login_required
def alerts(request):
    require_finance_role(request.user)
    today = timezone.localdate()
    overdue_fees = []
    for fee in StudentFee.objects.select_related("student").prefetch_related("payments"):
        if fee.due_date and fee.due_date < today and fee.balance > 0:
            overdue_fees.append(fee)
    pending_expenses = SchoolExpense.objects.filter(approval_status="pending")
    unpaid_salaries = StaffSalary.objects.filter(status="unpaid").select_related("employee")
    return render(request, "finance/alerts.html", _context(
        request, today=today, overdue_fees=overdue_fees,
        pending_expenses=pending_expenses, unpaid_salaries=unpaid_salaries,
        overdue_count=len(overdue_fees), pending_expense_count=pending_expenses.count(),
        unpaid_salary_count=unpaid_salaries.count()
    ))


@login_required
def audit_logs(request):
    if user_role(request.user) not in ("accountant", "principal", "vice_principal", "chairman"):
        raise PermissionDenied("You are not allowed to view finance audit logs.")
    logs = SystemActivityLog.objects.filter(module__iexact="Finance").select_related("user")
    action = request.GET.get("action", "").strip()
    if action:
        logs = logs.filter(action=action)
    return render(request, "finance/audit_logs.html", _context(
        request, logs=logs[:300], action=action,
        action_choices=SystemActivityLog.ACTION_CHOICES
    ))
