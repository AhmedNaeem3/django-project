from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.core.management import call_command
from django.utils import timezone

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
def cleanup_expired_jwt_tokens():
    call_command("flushexpiredtokens")


@shared_task
def cleanup_expired_google_drive_oauth_states():
    cutoff = timezone.now() - settings.GOOGLE_DRIVE_OAUTH_STATE_LIFETIME
    deleted, _ = GoogleDriveOAuthState.objects.filter(created_at__lt=cutoff).delete()
    return f"Deleted {deleted} expired Google Drive OAuth states"
