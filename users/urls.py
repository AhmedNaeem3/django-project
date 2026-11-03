from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    LoginAPIView,
    LogoutAPIView,
    PasswordlessLoginVerifyAPIView,
    ProfileAPIView,
    UserRegistrationView,
    GoogleDriveCallbackAPIView,
    GoogleDriveConnectAPIView,
    GoogleDriveFileDetailAPIView,
    GoogleDriveFilesAPIView,
)

urlpatterns = [
    path("register/", UserRegistrationView.as_view(), name="register"),
    path("login/", LoginAPIView.as_view(), name="login"),
    path(
        "login/passwordless/verify/",
        PasswordlessLoginVerifyAPIView.as_view(),
        name="passwordless_login_verify",
    ),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("logout/", LogoutAPIView.as_view(), name="logout"),
    path("profile/", ProfileAPIView.as_view(), name="profile"),
    path(
        "google-drive/callback/",
        GoogleDriveCallbackAPIView.as_view(),
        name="google_drive_callback",
    ),
    path(
        "google-drive/connect/",
        GoogleDriveConnectAPIView.as_view(),
        name="google_drive_connect",
    ),
    path(
        "google-drive/files/",
        GoogleDriveFilesAPIView.as_view(),
        name="google_drive_files",
    ),
    path(
        "google-drive/files/<str:file_id>/",
        GoogleDriveFileDetailAPIView.as_view(),
        name="google_drive_file_detail",
    ),
]
