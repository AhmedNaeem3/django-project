from datetime import date

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .models import GoogleDriveOAuthState, PasswordlessLoginToken, Profile, User
from .tasks import send_welcome_email


class UserRegistrationSerializer(serializers.ModelSerializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "password", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate(self, attrs):
        user = User(
            email=attrs["email"],
            first_name=attrs["first_name"],
            last_name=attrs["last_name"],
        )

        try:
            validate_password(attrs["password"], user)
        except DjangoValidationError as error:
            raise serializers.ValidationError({"password": list(error.messages)})

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        Profile.objects.create(
            user=user,
        )
        transaction.on_commit(
            lambda: send_welcome_email.delay(user.email, user.first_name), robust=True
        )
        return user


class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "created_at"]


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True,
        required=False,
        style={"input_type": "password"},
    )


class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Profile
        fields = [
            "id",
            "user",
            "phone_number",
            "bio",
            "date_of_birth",
            "city",
            "passwordless_login_enabled",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate_date_of_birth(self, value):
        if value and value > date.today():
            raise serializers.ValidationError("Date of birth cannot be in the future.")
        return value


class GoogleDriveCallbackSerializer(serializers.Serializer):
    state = serializers.CharField(max_length=255)
    code = serializers.CharField(max_length=512, required=False)
    error = serializers.CharField(max_length=100, required=False)

    def validate_state(self, value):
        oauth_state = GoogleDriveOAuthState.objects.filter(
            state=value,
            created_at__gte=timezone.now() - settings.GOOGLE_DRIVE_OAUTH_STATE_LIFETIME,
        ).first()

        if oauth_state is None:
            raise serializers.ValidationError(
                "Invalid or expired OAuth state. Start again."
            )

        return oauth_state

    def validate(self, attrs):
        if "error" in attrs:
            raise serializers.ValidationError("Google Drive authorization was denied.")

        if "code" not in attrs:
            raise serializers.ValidationError("Missing Google authorization code.")

        return attrs


class PasswordlessLoginVerifySerializer(serializers.Serializer):
    token = serializers.CharField(max_length=64)

    def validate_token(self, value):
        login_token = PasswordlessLoginToken.objects.filter(
            token=value,
            created_at__gte=timezone.now() - settings.PASSWORDLESS_LOGIN_TOKEN_LIFETIME,
            user__is_active=True,
            user__profile__passwordless_login_enabled=True,
        ).first()

        if login_token is None:
            raise serializers.ValidationError(
                "This login link is invalid or has expired."
            )

        return login_token
