def get_console_email_settings():
    """
    Get console email settings.
    Returns a dictionary with the email backend and options.
    """

    MAILERS = {
        "default": {
            "BACKEND": "django.core.mail.backends.console.EmailBackend",
        },
    }

    return MAILERS
