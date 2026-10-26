from django.contrib.auth import authenticate
from django.core.cache import cache
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.generics import CreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Profile
from .serializers import (
    LoginSerializer,
    ProfileSerializer,
    UserRegistrationSerializer,
    UserSerializer,
)


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


class ProfileAPIView(CreateAPIView, RetrieveUpdateDestroyAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        try:
            return self.request.user.profile
        except Profile.DoesNotExist:
            raise NotFound({"error": "Profile not found."})

    def get_cache_key(self):
        return f"profile:{self.request.user.pk}"

    def retrieve(self, request, *args, **kwargs):
        cache_key = self.get_cache_key()
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(cached_data)

        response = super().retrieve(request, *args, **kwargs)
        cache.set(cache_key, response.data, timeout=60)
        return response

    def perform_create(self, serializer):
        if Profile.objects.filter(user=self.request.user).exists():
            raise ValidationError({"error": "You already have a profile."})

        serializer.save(user=self.request.user)
        cache.delete(self.get_cache_key())

    def perform_update(self, serializer):
        serializer.save()
        cache.delete(self.get_cache_key())

    def perform_destroy(self, instance):
        instance.delete()
        cache.delete(self.get_cache_key())
