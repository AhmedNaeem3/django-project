import io
from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from .models import Profile
from .serializers import (
    LoginSerializer,
    ProfileSerializer,
    UserRegistrationSerializer,
    UserSerializer,
)
from google.auth.exceptions import GoogleAuthError, RefreshError
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload
from oauthlib.oauth2.rfc6749.errors import OAuth2Error
from users.models import GoogleDriveConnection
from django.core.cache import cache
from django.http import FileResponse, HttpResponse
from .google_drive import build_drive_flow, build_drive_service, save_credentials
from .tasks import send_drive_file_email


class UserRegistrationView(CreateAPIView):
    serializer_class = UserRegistrationSerializer
    authentication_classes = []
    permission_classes = [AllowAny]


class LoginAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request,
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )

        if user is None:
            return Response(
                {"error": "Invalid email or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")

        if not refresh_token:
            return Response(
                {"error": "Refresh token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = RefreshToken(refresh_token)
        except TokenError as error:
            return Response(
                {"error": str(error)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if str(token["user_id"]) != str(request.user.id):
            return Response(
                {"error": "This refresh token does not belong to you."},
                status=status.HTTP_403_FORBIDDEN,
            )

        token.blacklist()

        return Response(
            {"message": "Successfully logged out."},
            status=status.HTTP_205_RESET_CONTENT,
        )


class ProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request):
        try:
            return request.user.profile
        except Profile.DoesNotExist:
            raise NotFound({"error": "Profile not found."})

    def get(self, request):
        profile = self.get_object(request)
        serializer = ProfileSerializer(profile)
        return Response(serializer.data)

    def put(self, request):
        profile = self.get_object(request)
        serializer = ProfileSerializer(profile, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

    def patch(self, request):
        profile = self.get_object(request)
        serializer = ProfileSerializer(
            profile,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

    def delete(self, request):
        profile = self.get_object(request)
        user = profile.user

        outstanding_tokens = OutstandingToken.objects.filter(user=user)

        for outstanding_token in outstanding_tokens:
            try:
                RefreshToken(outstanding_token.token).blacklist()
            except TokenError:
                pass

        user.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


def google_drive_callback(request):
    state = request.GET.get("state")
    cache_key = f"google_drive_oauth:{state}"
    oauth_data = cache.get(cache_key)

    if oauth_data is None:
        return HttpResponse(
            "Invalid or expired OAuth state. Start again.",
            status=400,
        )

    cache.delete(cache_key)

    flow = build_drive_flow(
        state=state,
        code_verifier=oauth_data["code_verifier"],
    )

    try:
        flow.fetch_token(authorization_response=request.build_absolute_uri())
    except (GoogleAuthError, OAuth2Error, ValueError):
        return HttpResponse(
            "Google Drive connection failed.",
            status=400,
        )

    connection, _ = GoogleDriveConnection.objects.get_or_create(
        user_id=oauth_data["user_id"],
    )
    save_credentials(connection, flow.credentials)

    return HttpResponse("Google Drive connected successfully.")


class GoogleDriveConnectAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        flow = build_drive_flow()

        authorization_url, state = flow.authorization_url(
            access_type="offline",
            prompt="consent",
        )

        cache.set(
            f"google_drive_oauth:{state}",
            {
                "user_id": request.user.pk,
                "code_verifier": flow.code_verifier,
            },
            timeout=600,
        )

        return Response(
            {"authorization_url": authorization_url},
            status=status.HTTP_200_OK,
        )


class GoogleDriveAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_drive_service(self, request):
        try:
            connection = request.user.google_drive_connection
        except GoogleDriveConnection.DoesNotExist:
            raise NotFound({"error": "Google Drive is not connected."})

        return build_drive_service(connection)

    def get_upload_media(self, request):
        uploaded_file = request.FILES.get("file")

        if uploaded_file is None:
            raise ValidationError({"error": "File is required."})

        return MediaIoBaseUpload(
            uploaded_file,
            mimetype=uploaded_file.content_type or "application/octet-stream",
            resumable=True,
        )

    def send_file_email(self, request, action, file_name):
        send_drive_file_email.delay(
            request.user.email,
            request.user.first_name,
            action,
            file_name,
        )

    def handle_exception(self, exc):
        if isinstance(exc, RefreshError):
            exc = PermissionDenied(
                {"error": "Google Drive access expired. Please connect again."}
            )

        if isinstance(exc, HttpError):
            return Response({"error": exc.reason}, status=exc.status_code)

        return super().handle_exception(exc)


class GoogleDriveFilesAPIView(GoogleDriveAPIView):
    def get(self, request):
        service = self.get_drive_service(request)

        result = service.files().list(
            q="trashed = false",
            fields="files(id, name, mimeType, size, modifiedTime)",
            pageSize=100,
        ).execute()

        return Response(result.get("files", []))

    def post(self, request):
        media = self.get_upload_media(request)
        service = self.get_drive_service(request)

        drive_file = service.files().create(
            body={"name": request.FILES["file"].name},
            media_body=media,
            fields="id, name, mimeType, size, modifiedTime",
        ).execute()

        self.send_file_email(request, "uploaded", drive_file["name"])

        return Response(drive_file, status=status.HTTP_201_CREATED)


class GoogleDriveFileDetailAPIView(GoogleDriveAPIView):
    def get(self, request, file_id):
        service = self.get_drive_service(request)

        drive_file = service.files().get(
            fileId=file_id,
            fields="name, mimeType",
        ).execute()
        content = service.files().get_media(fileId=file_id).execute()

        return FileResponse(
            io.BytesIO(content),
            as_attachment=True,
            filename=drive_file["name"],
            content_type=drive_file["mimeType"],
        )

    def patch(self, request, file_id):
        service = self.get_drive_service(request)
        content = request.data.get("content")
        append = request.data.get("append")

        if append is not None:
            old_content = service.files().get_media(fileId=file_id).execute()

            try:
                old_text = old_content.decode()
            except UnicodeDecodeError:
                raise ValidationError({"error": "Append only works on text files."})

            content = f"{old_text.rstrip()}\n{append}" if old_text.strip() else append

        if content is None:
            media = self.get_upload_media(request)
        else:
            media = MediaIoBaseUpload(
                io.BytesIO(content.encode()),
                mimetype="text/plain",
                resumable=True,
            )

        drive_file = service.files().update(
            fileId=file_id,
            media_body=media,
            fields="id, name, mimeType, size, modifiedTime",
        ).execute()

        self.send_file_email(request, "updated", drive_file["name"])

        return Response(drive_file)

    def delete(self, request, file_id):
        service = self.get_drive_service(request)

        drive_file = service.files().get(fileId=file_id, fields="name").execute()
        service.files().delete(fileId=file_id).execute()

        self.send_file_email(request, "deleted", drive_file["name"])

        return Response(status=status.HTTP_204_NO_CONTENT)
