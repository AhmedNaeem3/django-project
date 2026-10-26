from celery import shared_task
from django.core.mail import send_mail


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
