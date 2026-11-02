from celery import shared_task
from django.core.mail import send_mail
from django.core.management import call_command


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
