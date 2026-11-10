from functools import wraps

from django.http import HttpResponseForbidden
from django.shortcuts import redirect


# =========================================================
# ROLE CONSTANTS
# =========================================================

ADMISSION_STAFF = "admission_staff"
SYSTEM_ADMINISTRATOR = "system_administrator"
VICE_PRINCIPAL = "vice_principal"
TEACHER = "teacher"
STUDENT = "student"
PRINCIPAL = "principal"
CHAIRMAN = "chairman"
ACCOUNTANT = "accountant"
PARENT = "parent"
BUS_DRIVER = "bus_driver"


# =========================================================
# DOCUMENT PERMISSIONS
# =========================================================

DOCUMENT_PERMISSIONS = {

    ADMISSION_STAFF: {
        "student": True,
        "employee": True,
        "user": False,
        "fee": False,
        "report": False,
        "transport": False,
        "personal": False,
        "upload": True,
        "view": True,
        "download": True,
        "manage": False,
    },

    SYSTEM_ADMINISTRATOR: {
        "student": True,
        "employee": True,
        "user": True,
        "fee": False,
        "report": False,
        "transport": False,
        "personal": False,
        "upload": True,
        "view": True,
        "download": True,
        "manage": True,
    },

    VICE_PRINCIPAL: {
        "student": True,
        "employee": True,
        "user": False,
        "fee": False,
        "report": False,
        "transport": False,
        "personal": False,
        "upload": True,
        "view": True,
        "download": True,
        "manage": False,
    },

    TEACHER: {
        "student": True,
        "employee": False,
        "user": False,
        "fee": False,
        "report": False,
        "transport": False,
        "personal": True,
        "upload": False,
        "view": True,
        "download": True,
        "manage": False,
    },

    STUDENT: {
        "student": False,
        "employee": False,
        "user": False,
        "fee": False,
        "report": False,
        "transport": False,
        "personal": True,
        "upload": True,
        "view": True,
        "download": True,
        "manage": False,
    },

    PRINCIPAL: {
        "student": True,
        "employee": True,
        "user": False,
        "fee": False,
        "report": True,
        "transport": False,
        "personal": False,
        "upload": True,
        "view": True,
        "download": True,
        "manage": False,
    },

    CHAIRMAN: {
        "student": True,
        "employee": True,
        "user": False,
        "fee": False,
        "report": True,
        "transport": False,
        "personal": False,
        "upload": False,
        "view": True,
        "download": True,
        "manage": False,
    },

    ACCOUNTANT: {
        "student": True,
        "employee": True,
        "user": False,
        "fee": True,
        "report": False,
        "transport": False,
        "personal": False,
        "upload": True,
        "view": True,
        "download": True,
        "manage": False,
    },

    PARENT: {
        "student": True,
        "employee": False,
        "user": False,
        "fee": False,
        "report": False,
        "transport": False,
        "personal": False,
        "upload": False,
        "view": True,
        "download": True,
        "manage": False,
    },

    BUS_DRIVER: {
        "student": False,
        "employee": False,
        "user": False,
        "fee": False,
        "report": False,
        "transport": True,
        "personal": True,
        "upload": True,
        "view": True,
        "download": True,
        "manage": False,
    },
}


# =========================================================
# GET USER ROLE
# =========================================================

def get_user_role(user):

    if not user.is_authenticated:
        return None

    try:
        return user.profile.role

    except AttributeError:
        return None


# =========================================================
# GET ROLE PERMISSIONS
# =========================================================

def get_role_permissions(user):

    role = get_user_role(user)

    if not role:
        return {}

    return DOCUMENT_PERMISSIONS.get(
        role,
        {}
    )


# =========================================================
# CHECK PERMISSION
# =========================================================

def has_document_permission(
    user,
    permission
):

    permissions = get_role_permissions(
        user
    )

    return permissions.get(
        permission,
        False
    )


# =========================================================
# CHECK CATEGORY PERMISSION
# =========================================================

def can_access_category(
    user,
    category
):

    permissions = get_role_permissions(
        user
    )

    return permissions.get(
        category,
        False
    )


# =========================================================
# DECORATOR
# =========================================================

def document_permission_required(
    permission
):

    def decorator(view_func):

        @wraps(view_func)
        def wrapper(
            request,
            *args,
            **kwargs
        ):

            if not request.user.is_authenticated:
                return redirect(
                    "accounts:login"
                )

            if not has_document_permission(
                request.user,
                permission
            ):
                return HttpResponseForbidden(
                    "You do not have permission to access this document feature."
                )

            return view_func(
                request,
                *args,
                **kwargs
            )

        return wrapper

    return decorator


# =========================================================
# CATEGORY DECORATOR
# =========================================================

def document_category_required(
    category
):

    def decorator(view_func):

        @wraps(view_func)
        def wrapper(
            request,
            *args,
            **kwargs
        ):

            if not request.user.is_authenticated:
                return redirect(
                    "accounts:login"
                )

            if not can_access_category(
                request.user,
                category
            ):
                return HttpResponseForbidden(
                    "You do not have permission to access this document category."
                )

            return view_func(
                request,
                *args,
                **kwargs
            )

        return wrapper

    return decorator