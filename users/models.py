from sqlite3.dbapi2 import Timestamp
from django.conf import settings
from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
)
from django.core.validators import RegexValidator
from users.utils.user_manager import UserManager
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    def __str__(self):
        return self.email


class Profile(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    phone_number = models.CharField(
        max_length=16,
        blank=True,
        validators=[
            RegexValidator(
                regex=r"^\+?\d{7,15}$",
                message="Enter a valid phone number with 7 to 15 digits.",
            )
        ],
    )
    bio = models.TextField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    city = models.CharField(max_length=100, blank=True)
    passwordless_login_enabled = models.BooleanField(default=False)

    def __str__(self):
        return f"Profile of {self.user.email}"


class GoogleDriveConnection(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="google_drive_connection",
    )
    access_token = models.TextField()
    refresh_token = models.TextField(blank=True, default="")
    token_expiry = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Google Drive connection for {self.user.email}"


class GoogleDriveOAuthState(TimeStampedModel):
    state = models.CharField(max_length=255, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="google_drive_oauth_states",
    )
    code_verifier = models.CharField(max_length=128)

    def __str__(self):
        return f"Google Drive OAuth state for {self.user.email}"


class PasswordlessLoginToken(TimeStampedModel):
    token = models.CharField(max_length=64, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="passwordless_login_tokens",
    )

    def __str__(self):
        return f"Passwordless login token for {self.user.email}"
