from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.core.management import call_command
from django.utils import timezone
from django.utils.html import format_html

from .models import GoogleDriveOAuthState


@shared_task
def send_welcome_email(user_email, first_name):
    subject = "Welcome to Our Platform!"

    message = (
        f"Hello {first_name},\n\n"
        "Welcome to our platform! "
        "We're happy to have you with us."
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=None,
        recipient_list=[user_email],
        fail_silently=False,
    )

    return f"Welcome email sent to {user_email}"


@shared_task
def send_drive_file_email(user_email, first_name, action, file_name):
    subject = f"Google Drive file {action}"

    message = (
        f"Hello {first_name},\n\n"
        f'The file "{file_name}" was {action} in your Google Drive.'
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=None,
        recipient_list=[user_email],
        fail_silently=False,
    )

    return f"Drive {action} email sent to {user_email}"


@shared_task
def send_passwordless_login_email(user_email, first_name, login_url):
    subject = "Your login link"
    minutes = int(settings.PASSWORDLESS_LOGIN_TOKEN_LIFETIME.total_seconds() // 60)

    message = (
        f"Hello {first_name},\n\n"
        f"Open this link to log in: {login_url}\n\n"
        f"The link works once and expires in {minutes} minutes. "
        "If you did not ask for it, you can ignore this email."
    )

    html_message = format_html(
        "<p>Hello {},</p>"
        "<p>Click the button below to log in.</p>"
        '<p><a href="{}" style="display:inline-block;padding:12px 24px;'
        "background-color:#2563eb;color:#ffffff;text-decoration:none;"
        'border-radius:6px;font-weight:bold;">Log in</a></p>'
        "<p>The link works once and expires in {} minutes. "
        "If you did not ask for it, you can ignore this email.</p>",
        first_name,
        login_url,
        minutes,
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=None,
        recipient_list=[user_email],
        html_message=html_message,
        fail_silently=False,
    )

    return f"Passwordless login email sent to {user_email}"


@shared_task
def cleanup_expired_jwt_tokens():
    call_command("flushexpiredtokens")


@shared_task
def cleanup_expired_google_drive_oauth_states():
    cutoff = timezone.now() - settings.GOOGLE_DRIVE_OAUTH_STATE_LIFETIME
    GoogleDriveOAuthState.objects.filter(created_at__lt=cutoff).delete()

