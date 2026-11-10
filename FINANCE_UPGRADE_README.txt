FINANCE MANAGEMENT UPGRADE - INSTALLATION NOTES
================================================

This upgrade reuses the existing Django dashboard/base.html, sidebar, finance models,
forms, and SystemActivityLog. It does not create a separate dashboard.

Implemented finance areas:
1. Fee management and fee structures
2. Fee payments and printable receipt (Print / Save PDF)
3. Payroll list, salary entry, net salary calculation, and mark-paid action
4. Expense entry with bill upload and Principal / Vice Principal / Chairman approval
5. Bank reconciliation using a manually entered statement line; auto-match requires
   one exact payment amount + transaction reference (or receipt number)
6. Financial reports and CSV exports (collections, dues, expenses, payroll)
7. Alerts for overdue fee balances, pending expenses, and unpaid payroll
8. Finance audit trail using the existing accounts.SystemActivityLog

IMPORTANT:
- Back up your project folder and database before replacing files.
- Reconciliation in this version is manual statement-line entry. It does not connect
  to a bank API or import a bank-specific CSV format.
- Fee payments are manually recorded. A live online payment gateway is not included.
- Expenses are included in financial reports only after approval.
- Audit logs record actions from these finance views; this is not a statutory ledger.

After copying/extracting this project:
1. Open VS Code terminal in the folder containing manage.py.
2. Activate your existing virtual environment.
3. Run:
       python manage.py check
       python manage.py migrate
       python manage.py runserver
4. Log in with the Accountant account and open Finance Management from the existing sidebar.
5. Principal / Vice Principal / Chairman can open /finance/expenses/ to review submitted expenses.
6. For receipt printing, open a payment receipt and select Print / Save PDF.

The migration 0003_bankstatemententry.py creates the bank statement reconciliation table.
