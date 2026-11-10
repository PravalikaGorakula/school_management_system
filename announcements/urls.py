from django.urls import path

from . import views


app_name = "announcements"


urlpatterns = [

    # -----------------------------------------------------
    # Received Announcements
    # -----------------------------------------------------

    path(
        "",
        views.announcement_list,
        name="list",
    ),

    # -----------------------------------------------------
    # Create Announcement
    # -----------------------------------------------------

    path(
        "create/",
        views.announcement_create,
        name="create",
    ),

    # -----------------------------------------------------
    # Announcement History
    # -----------------------------------------------------

    path(
        "history/",
        views.announcement_history,
        name="history",
    ),

    # -----------------------------------------------------
    # Announcement Detail
    # -----------------------------------------------------

    path(
        "<int:announcement_id>/",
        views.announcement_detail,
        name="detail",
    ),
]