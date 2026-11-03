from datetime import UTC

from django.conf import settings
from django.utils import timezone
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build


class GoogleDriveClient:
    AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
    TOKEN_URI = "https://oauth2.googleapis.com/token"

    def __init__(self, connection):
        self.connection = connection

    @classmethod
    def build_flow(cls, **kwargs):
        return Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "auth_uri": cls.AUTH_URI,
                    "token_uri": cls.TOKEN_URI,
                    "redirect_uris": [settings.GOOGLE_DRIVE_REDIRECT_URI],
                }
            },
            scopes=settings.GOOGLE_DRIVE_SCOPES,
            redirect_uri=settings.GOOGLE_DRIVE_REDIRECT_URI,
            **kwargs,
        )

    def save_credentials(self, credentials):
        self.connection.access_token = credentials.token

        if credentials.refresh_token:
            self.connection.refresh_token = credentials.refresh_token

        self.connection.token_expiry = timezone.make_aware(credentials.expiry, UTC)
        self.connection.save()

    def build_service(self):
        credentials = Credentials(
            token=self.connection.access_token,
            refresh_token=self.connection.refresh_token,
            token_uri=self.TOKEN_URI,
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            scopes=settings.GOOGLE_DRIVE_SCOPES,
            expiry=timezone.make_naive(self.connection.token_expiry, UTC),
        )

        if not credentials.valid:
            credentials.refresh(Request())
            self.save_credentials(credentials)

        return build("drive", "v3", credentials=credentials, cache_discovery=False)
