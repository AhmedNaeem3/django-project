from datetime import timezone as dt_timezone

from django.conf import settings
from django.utils import timezone
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"


def build_drive_flow(**kwargs):
    return Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": GOOGLE_TOKEN_URI,
                "redirect_uris": [settings.GOOGLE_DRIVE_REDIRECT_URI],
            }
        },
        scopes=settings.GOOGLE_DRIVE_SCOPES,
        redirect_uri=settings.GOOGLE_DRIVE_REDIRECT_URI,
        **kwargs,
    )


def save_credentials(connection, credentials):
    connection.access_token = credentials.token

    if credentials.refresh_token:
        connection.refresh_token = credentials.refresh_token

    connection.token_expiry = timezone.make_aware(credentials.expiry, dt_timezone.utc)
    connection.save()


def build_drive_service(connection):
    credentials = Credentials(
        token=connection.access_token,
        refresh_token=connection.refresh_token,
        token_uri=GOOGLE_TOKEN_URI,
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=settings.GOOGLE_DRIVE_SCOPES,
        expiry=timezone.make_naive(connection.token_expiry, dt_timezone.utc),
    )

    if not credentials.valid:
        credentials.refresh(Request())
        save_credentials(connection, credentials)

    return build("drive", "v3", credentials=credentials, cache_discovery=False)
