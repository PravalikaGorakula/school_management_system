
from django.urls import path
from . import views

app_name = "academic_calendar"

urlpatterns = [
    path("", views.calendar_view, name="calendar"),
    path("add/", views.event_add, name="event_add"),
    path("event/<int:pk>/", views.event_detail, name="event_detail"),
    path("event/<int:pk>/edit/", views.event_edit, name="event_edit"),
    path("event/<int:pk>/delete/", views.event_delete, name="event_delete"),
]