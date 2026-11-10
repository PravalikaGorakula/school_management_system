from django.urls import path

from . import views


app_name = "leave_management"


urlpatterns = [

    path(
        "",
        views.leave_home,
        name="home",
    ),

    path(
        "apply/",
        views.apply_leave,
        name="apply_leave",
    ),

    path(
        "history/",
        views.leave_history,
        name="leave_history",
    ),

    path(
        "approvals/",
        views.leave_approvals,
        name="leave_approvals",
    ),

    path(
        "approvals/<int:leave_id>/approve/",
        views.approve_leave,
        name="approve_leave",
    ),

    path(
        "approvals/<int:leave_id>/reject/",
        views.reject_leave,
        name="reject_leave",
    ),

]