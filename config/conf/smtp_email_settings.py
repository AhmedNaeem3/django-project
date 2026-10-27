import os


def get_smtp_email_settings():
    """
    Get SMTP email settings from environment variables.
    Returns a dictionary with the email backend and options.
    """

    MAILERS = {
        "default": {
            "BACKEND": "django.core.mail.backends.smtp.EmailBackend",
            "OPTIONS": {
                "host": os.environ["EMAIL_HOST"],
                "port": int(os.environ.get("EMAIL_PORT", "587")),
                "use_tls": os.environ.get("EMAIL_USE_TLS", "True") == "True",
                "username": os.environ.get("EMAIL_HOST_USER", ""),
                "password": os.environ.get("EMAIL_HOST_PASSWORD", ""),
                "timeout": 10,
            },
        },
    }

    return MAILERS
