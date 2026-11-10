from django.conf import settings
from django.core.mail import send_mail


def send_credentials_email(
    email,
    first_name,
    username,
    password,
    role,
    account_email=None,
):
    """
    Send newly created account credentials
    to the personal email entered during admission.
    """

    if not email:
        print("EMAIL ERROR: No recipient email provided.")
        return False

    try:
        school_email = account_email or "Not generated"

        subject = "SMS College - Account Credentials"

        message = f"""
Dear {first_name or role},

Your SMS College account has been created successfully.

Account Details
------------------------------
Role           : {role}
Username       : {username}
School Email   : {school_email}
Initial Password: {password}
------------------------------

Login URL:
{settings.SITE_URL}/accounts/login/

Important:
Password change is optional.
You can continue using the initial password or change it later
from your Profile.

Please keep your login credentials safe.

Regards,
SMS College
"""

        print("=" * 70)
        print("SENDING CREDENTIAL EMAIL")
        print("=" * 70)
        print("To       :", email)
        print("Username :", username)
        print("School   :", school_email)
        print("=" * 70)

        result = send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )

        print("EMAIL SEND RESULT:", result)

        return result > 0

    except Exception as e:

        print("=" * 70)
        print("EMAIL SENDING FAILED")
        print("=" * 70)
        print("Error:", str(e))
        print("=" * 70)

        return False


def send_credentials_sms(
    phone,
    username,
    email,
    password,
):
    """
    SMS sending placeholder.

    Real SMS provider is not connected yet.
    """

    if not phone:
        print("SMS ERROR: No phone number provided.")
        return False

    message = (
        f"SMS College Account Created. "
        f"Username: {username} | "
        f"School Email: {email} | "
        f"Password: {password}"
    )

    print("=" * 70)
    print("SMS CREDENTIAL MESSAGE")
    print("=" * 70)
    print("Phone   :", phone)
    print("Message :", message)
    print("=" * 70)

    # Real SMS provider is required here.
    # For now this only prints the message in terminal.

    return False