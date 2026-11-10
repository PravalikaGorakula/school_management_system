from django.contrib import admin

from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "owner",
        "category",
        "document_type",
        "uploaded_by",
        "is_verified",
        "uploaded_at",
    )

    list_filter = (
        "category",
        "document_type",
        "is_verified",
        "uploaded_at",
    )

    search_fields = (
        "name",
        "owner__username",
        "owner__first_name",
        "owner__last_name",
        "owner__email",
        "uploaded_by__username",
    )

    readonly_fields = (
        "uploaded_at",
        "updated_at",
    )

    autocomplete_fields = (
        "owner",
        "uploaded_by",
    )

    ordering = (
        "-uploaded_at",
    )