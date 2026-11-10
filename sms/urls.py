from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),

    path("", include("accounts.urls")),

    path("dashboard/", include("dashboard.urls")),
    path("announcements/", include("announcements.urls")),
    path("documents/", include("documents.urls")),
    path("admissions/", include("admissions.urls")),
    path("academics/",include("academics.urls")),
    path("leaves/",include("leave_management.urls")),
    path("attendance/",include("attendance.urls")),
    path("transport/",include("transport.urls")),
    path("exams/",include("exams.urls")),
    path("notifications/",include("notifications.urls")),
    path(
    "academic-calendar/",
    include("academic_calendar.urls"),),
    path("finance/", include("finance.urls")),
]
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )