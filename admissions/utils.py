from datetime import datetime
import secrets
import string

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import transaction

from accounts.models import UserProfile

from .models import (
    StudentAdmissionApplication,
    EmployeeAdmissionApplication,
    StudentCredential,
    EmployeeCredential,
)


# =========================================================
# APPLICATION ID GENERATION
# =========================================================

def generate_student_application_id():
    year = datetime.now().year
    prefix = f"STU-APP-{year}-"

    last_application = (
        StudentAdmissionApplication.objects
        .filter(application_id__startswith=prefix)
        .order_by("-application_id")
        .first()
    )

    if last_application and last_application.application_id:
        try:
            last_number = int(
                last_application.application_id.split("-")[-1]
            )
            next_number = last_number + 1
        except (ValueError, IndexError):
            next_number = 1
    else:
        next_number = 1

    application_id = f"{prefix}{next_number:04d}"

    while StudentAdmissionApplication.objects.filter(
        application_id=application_id
    ).exists():
        next_number += 1
        application_id = f"{prefix}{next_number:04d}"

    return application_id


def generate_employee_application_id():
    year = datetime.now().year
    prefix = f"EMP-APP-{year}-"

    last_application = (
        EmployeeAdmissionApplication.objects
        .filter(application_id__startswith=prefix)
        .order_by("-application_id")
        .first()
    )

    if last_application and last_application.application_id:
        try:
            last_number = int(
                last_application.application_id.split("-")[-1]
            )
            next_number = last_number + 1
        except (ValueError, IndexError):
            next_number = 1
    else:
        next_number = 1

    application_id = f"{prefix}{next_number:04d}"

    while EmployeeAdmissionApplication.objects.filter(
        application_id=application_id
    ).exists():
        next_number += 1
        application_id = f"{prefix}{next_number:04d}"

    return application_id


# =========================================================
# TEMPORARY PASSWORD
# =========================================================

def generate_temporary_password():
    characters = (
        string.ascii_letters
        + string.digits
        + "@#$%&*"
    )

    password = (
        secrets.choice(string.ascii_uppercase)
        + secrets.choice(string.ascii_lowercase)
        + secrets.choice(string.digits)
        + secrets.choice("@#$%&*")
        + "".join(
            secrets.choice(characters)
            for _ in range(8)
        )
    )

    return password


# =========================================================
# SCHOOL ACCOUNT EMAIL
# =========================================================

def generate_account_email(application_id):
    """
    Student:
        STU-APP-2026-0011
        ->
        app-stu-2026-0011@smscollege.edu

    Employee:
        EMP-APP-2026-0001
        ->
        app-emp-2026-0001@smscollege.edu
    """

    application_id = str(
        application_id
    ).strip().upper()

    if application_id.startswith("STU-APP-"):
        application_id = application_id.replace(
            "STU-APP-",
            "APP-STU-",
            1,
        )

    elif application_id.startswith("EMP-APP-"):
        application_id = application_id.replace(
            "EMP-APP-",
            "APP-EMP-",
            1,
        )

    domain = getattr(
        settings,
        "ACCOUNT_EMAIL_DOMAIN",
        "smscollege.edu",
    ).strip().lower()

    return f"{application_id.lower()}@{domain}"


# =========================================================
# UNIQUE USERNAME GENERATION
# =========================================================

def generate_username(application_id, prefix=None):
    """
    Examples:
        STU-APP-2026-0003 -> stu2026003
        EMP-APP-2026-0003 -> emp2026003

    Checks:
        1. Django User table
        2. StudentCredential table
        3. EmployeeCredential table

    Existing usernames are never reused.
    """

    application_id = str(application_id).strip().upper()
    parts = application_id.split("-")

    if len(parts) >= 4 and parts[-2].isdigit() and parts[-1].isdigit():
        year = parts[-2]
        number = int(parts[-1])
    else:
        raise ValueError(
            f"Invalid application ID format: {application_id}"
        )

    if prefix:
        prefix = prefix.strip().lower()
    elif application_id.startswith("STU-APP-"):
        prefix = "stu"
    elif application_id.startswith("EMP-APP-"):
        prefix = "emp"
    else:
        prefix = "user"

    # Example: emp + 2026 + 003 = emp2026003
    base_username = f"{prefix}{year}{number:03d}"

    username = base_username
    counter = 1

    while True:
        user_exists = User.objects.filter(
            username=username
        ).exists()

        student_credential_exists = (
            StudentCredential.objects.filter(
                username=username
            ).exists()
        )

        employee_credential_exists = (
            EmployeeCredential.objects.filter(
                username=username
            ).exists()
        )

        if not (
            user_exists
            or student_credential_exists
            or employee_credential_exists
        ):
            return username

        # If username already exists, try another unique username.
        username = f"{base_username}{counter}"
        counter += 1


# =========================================================
# CREATE / GET ACCOUNT BY APPLICATION
# =========================================================

@transaction.atomic
def create_user_account(
    application,
    role,
    username_prefix,
    default_password=None,
):
    """
    Each application gets its own account.

    - Email can be duplicated.
    - Phone number can be duplicated.
    - Existing accounts are NOT found by email or phone.
    - The same application does not create a second account
      when its credential record already exists.
    - Usernames are generated uniquely.
    """

    personal_email = (
        getattr(application, "email", "") or ""
    ).strip().lower()

    # -----------------------------------------------------
    # 1. CHECK WHETHER THIS APPLICATION ALREADY HAS AN ACCOUNT
    # -----------------------------------------------------

    existing_credential = None

    if isinstance(application, StudentAdmissionApplication):
        existing_credential = (
            StudentCredential.objects
            .select_related("user")
            .filter(student_application=application)
            .first()
        )

    elif isinstance(application, EmployeeAdmissionApplication):
        existing_credential = (
            EmployeeCredential.objects
            .select_related("user")
            .filter(employee_application=application)
            .first()
        )

    # Same application: retain its already assigned username.
    if existing_credential and existing_credential.user_id:
        user = existing_credential.user

        profile, _ = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                "role": role,
                "phone": getattr(application, "phone", ""),
                "is_active": True,
            },
        )

        # Do not change an existing username.
        # Do not reset the password on repeated approval.
        return user, profile, False

    # -----------------------------------------------------
    # 2. GENERATE A NEW USERNAME
    # -----------------------------------------------------

    username = generate_username(
        application.application_id,
        prefix=username_prefix,
    )

    # -----------------------------------------------------
    # 3. GENERATE / SELECT INITIAL PASSWORD
    # -----------------------------------------------------

    temporary_password = (
        default_password
        if default_password
        else generate_temporary_password()
    )

    # -----------------------------------------------------
    # 4. CREATE A NEW USER
    # -----------------------------------------------------

    user = User.objects.create_user(
        username=username,
        email=personal_email,
        password=temporary_password,
        first_name=getattr(application, "first_name", "") or "",
        last_name=getattr(application, "last_name", "") or "",
    )

    user.is_active = True
    user.save(update_fields=["is_active"])

    # -----------------------------------------------------
    # 5. CREATE PROFILE
    # -----------------------------------------------------

    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={
            "role": role,
            "phone": getattr(application, "phone", ""),
            "is_active": True,
        },
    )

    profile.role = role
    profile.phone = getattr(application, "phone", "")
    profile.is_active = True
    profile.save(
        update_fields=[
            "role",
            "phone",
            "is_active",
            "updated_at",
        ]
    )

    return user, profile, True

# =========================================================
# SEND ACCOUNT CREATED EMAIL
# =========================================================

def send_account_created_email(
    user,
    temporary_password,
    role_name,
    account_email=None,
):
    """
    Send account credentials to personal email.

    Personal Gmail:
        Used for notifications/password reset.

    School email:
        Generated/stored school account email.
    """

    if not user.email:
        return False

    login_url = (
        f"{settings.SITE_URL}/login/"
    )

    school_email = (
        account_email
        if account_email
        else "Not generated"
    )

    subject = (
        "SMS Account Created - Login Credentials"
    )

    message = f"""
Dear {user.first_name},

Your School Management System account has been
created successfully.

ACCOUNT DETAILS
--------------------------------

Username:
{user.username}

School Email:
{school_email}

Personal Email:
{user.email}

Initial Password:
{temporary_password}

Role:
{role_name}

Login URL:
{login_url}


PASSWORD INFORMATION
--------------------------------

Your initial password can be used to login.

Changing the password is OPTIONAL.

You can continue using the initial password,
or change it later from your Profile.


IMPORTANT
--------------------------------

Please keep your login credentials secure.

This is an automated email from the
School Management System.

Regards,
School Management System
"""

    try:

        result = send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[
                user.email
            ],
            fail_silently=False,
        )

        return result > 0

    except Exception as e:

        print(
            "ACCOUNT EMAIL ERROR:",
            e,
        )

        return False