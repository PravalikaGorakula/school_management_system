from django.urls import path

from . import views


app_name = "dashboard"


urlpatterns = [
    path(
        "",
        views.dashboard_home,
        name="home",
    ),
    
    path(
        "chairman/",
        views.chairman_dashboard,
        name="chairman_dashboard"
    ),
    path(
        "chairman/students/",
        views.chairman_students,
        name="chairman_students"
    ),

    path(
        "chairman/employees/",
        views.chairman_employees,
        name="chairman_employees"
    ),

    path(
        "chairman/academics/",
        views.chairman_academics,
        name="chairman_academics"
    ),

    path(
        "chairman/finance/",
        views.chairman_finance,
        name="chairman_finance"
    ),

    path(
        "chairman/transport/",
        views.chairman_transport,
        name="chairman_transport"
    ),

    path(
        "chairman/approvals/",
        views.chairman_approvals,
        name="chairman_approvals"
    ),

    path(
        "chairman/reports/",
        views.chairman_reports,
        name="chairman_reports"
    ),
]