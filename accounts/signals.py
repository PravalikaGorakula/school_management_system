from django.db.models.signals import (
    post_save,
    post_delete,
)
from django.dispatch import receiver
from django.contrib.auth.models import User

from .models import (
    UserProfile,
    SystemActivityLog,
)


# =========================================================
# USER PROFILE CREATION
# =========================================================

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):

    if created:

        UserProfile.objects.get_or_create(
            user=instance
        )


# =========================================================
# USER PROFILE SAVE
# =========================================================

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):

    if hasattr(instance, "profile"):

        instance.profile.save()


# =========================================================
# SYSTEM ACTIVITY LOGGER
# =========================================================

def create_system_log(
    user=None,
    module="System",
    action="other",
    description="",
    ip_address=None,
):

    return SystemActivityLog.objects.create(

        user=user,

        module=module,

        action=action,

        description=description,

        ip_address=ip_address,
    )


# =========================================================
# AUTOMATIC MODEL CREATE / UPDATE LOGGING
# =========================================================

@receiver(post_save)
def log_model_save(
    sender,
    instance,
    created,
    **kwargs
):

    # -----------------------------------------------------
    # Ignore log model itself
    # -----------------------------------------------------

    if sender == SystemActivityLog:
        return

    # -----------------------------------------------------
    # Ignore Django internal models
    # -----------------------------------------------------

    if sender._meta.app_label in [
        "contenttypes",
        "sessions",
        "admin",
    ]:
        return

    # -----------------------------------------------------
    # Only project applications
    # -----------------------------------------------------

    allowed_apps = [
        "accounts",
        "admissions",
        "academics",
        "announcements",
        "attendance",
        "documents",
        "leave_management",
        "transport",
    ]

    if sender._meta.app_label not in allowed_apps:
        return

    # -----------------------------------------------------
    # Do not create duplicate log for UserProfile
    # -----------------------------------------------------

    if sender == UserProfile:
        return

    action = "create" if created else "update"

    module_name = sender._meta.verbose_name.title()

    description = (
        f"{module_name} "
        f"{'created' if created else 'updated'} "
        f"successfully."
    )

    SystemActivityLog.objects.create(

        user=None,

        module=module_name,

        action=action,

        description=description,

    )


# =========================================================
# AUTOMATIC MODEL DELETE LOGGING
# =========================================================

@receiver(post_delete)
def log_model_delete(
    sender,
    instance,
    **kwargs
):

    if sender == SystemActivityLog:
        return

    if sender._meta.app_label in [
        "contenttypes",
        "sessions",
        "admin",
    ]:
        return

    allowed_apps = [
        "accounts",
        "admissions",
        "academics",
        "announcements",
        "attendance",
        "documents",
        "leave_management",
        "transport",
    ]

    if sender._meta.app_label not in allowed_apps:
        return

    if sender == UserProfile:
        return

    module_name = sender._meta.verbose_name.title()

    description = (
        f"{module_name} deleted."
    )

    SystemActivityLog.objects.create(

        user=None,

        module=module_name,

        action="delete",

        description=description,

    )