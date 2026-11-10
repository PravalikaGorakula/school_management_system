from django.contrib import admin

from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "role",
        "phone",
        "is_active",
        "created_at",
        "updated_at",
    )

    list_filter = (
        "role",
        "is_active",
    )

    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__email",
        "phone",
    )

    ordering = (
        "-created_at",
    )