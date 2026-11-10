from django.urls import path
from django.contrib.auth import views as auth_views

from . import views


app_name = "accounts"


urlpatterns = [

    # =========================================================
    # LOGIN
    # =========================================================

    path(
        "login/",
        views.login_view,
        name="login",
    ),

    # =========================================================
    # LOGOUT
    # =========================================================

    path(
        "logout/",
        views.logout_view,
        name="logout",
    ),

    # =========================================================
    # PROFILE
    # =========================================================

    path(
        "profile/",
        views.profile_view,
        name="profile",
    ),
    path(
    "change-password/",
    views.change_password_view,
    name="change_password",
    ),
    path(
    "forgot-password/",
    auth_views.PasswordResetView.as_view(
        template_name="accounts/forgot_password.html",
        email_template_name="accounts/password_reset_email.txt",
        html_email_template_name="accounts/password_reset_email.html",
        subject_template_name="accounts/password_reset_subject.txt",
        success_url="/forgot-password/done/",
    ),
    name="password_reset",
    ),
    path(
        "forgot-password/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="accounts/password_reset_done.html"
        ),
        name="password_reset_done",
    ),

    # =========================================================
    # RESET PASSWORD
    # =========================================================

    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html",
            success_url="/reset-password-complete/",
        ),
        name="password_reset_confirm",
    ),

    path(
        "reset-password-complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
    path(
        "system-logs/",
        views.system_logs_view,
        name="system_logs",
    ),
]