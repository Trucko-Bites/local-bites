"""
Session-based login and sign-up for the React app.

The React app and the API share one origin (Vite proxy in dev, Caddy in prod),
so Django's normal session cookie works: no tokens to store in the browser.
The session cookie is HttpOnly, so JavaScript can't read or leak it.

Flow:
  1. GET  /api/auth/csrf/       sets the csrftoken cookie
  2. POST /api/auth/login/      (or /api/auth/register/) with header X-CSRFToken: <cookie value>
  3. Later POSTs send the same header; the session cookie identifies the user
"""

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

User = get_user_model()

DUPLICATE_USERNAME_MESSAGE = "That username is already taken."
DUPLICATE_EMAIL_MESSAGE = "An account with that email already exists."


def describe_user(user):
    """The only user details the frontend needs."""
    return {"username": user.username, "is_staff": user.is_staff}


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(trim_whitespace=False)


class RegisterSerializer(serializers.Serializer):
    """Validates a sign-up form. Every new account is a regular customer (never staff)."""

    # Reuse the User model's own username rules (max length, allowed characters)
    username = serializers.CharField(
        max_length=User._meta.get_field("username").max_length,
        validators=User._meta.get_field("username").validators,
    )
    email = serializers.EmailField()
    # trim_whitespace=False: spaces are allowed in passwords and must not be stripped
    password = serializers.CharField(trim_whitespace=False, write_only=True)
    password_confirmation = serializers.CharField(trim_whitespace=False, write_only=True)

    def validate_username(self, username):
        # Case-insensitive, so "TacoFan" and "tacofan" can't both exist
        if User.objects.filter(username__iexact=username).exists():
            raise serializers.ValidationError(DUPLICATE_USERNAME_MESSAGE)
        return username

    def validate_email(self, email):
        email = User.objects.normalize_email(email)
        # Email must be unique (case-insensitive) so password reset can find one account later
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError(DUPLICATE_EMAIL_MESSAGE)
        return email

    def validate(self, attributes):
        if attributes["password"] != attributes["password_confirmation"]:
            raise serializers.ValidationError({"password_confirmation": "Passwords do not match."})

        # Run settings.AUTH_PASSWORD_VALIDATORS. An unsaved user is passed in so the
        # "too similar to your username/email" check has something to compare against.
        unsaved_user = User(username=attributes["username"], email=attributes["email"])
        try:
            validate_password(attributes["password"], user=unsaved_user)
        except DjangoValidationError as password_errors:
            raise serializers.ValidationError({"password": list(password_errors.messages)})
        return attributes

    def create(self, validated_data):
        # create_user hashes the password; is_staff stays False
        return User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
        )


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfCookieView(APIView):
    """GET /api/auth/csrf/ -- makes sure the browser has a csrftoken cookie."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"detail": "CSRF cookie set."})


# csrf_protect: DRF only checks CSRF for already-logged-in users,
# so the login form itself is protected explicitly.
@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    """POST /api/auth/login/ {"username": "...", "password": "..."}"""

    permission_classes = [AllowAny]

    def post(self, request):
        login_serializer = LoginSerializer(data=request.data)
        login_serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            username=login_serializer.validated_data["username"],
            password=login_serializer.validated_data["password"],
        )
        if user is None:
            # Same message for wrong username or password, so accounts can't be probed
            return Response({"detail": "Invalid username or password."}, status=status.HTTP_400_BAD_REQUEST)
        login(request, user)
        return Response(describe_user(user))


# Same CSRF protection as login: the sign-up form is posted by logged-out users
@method_decorator(csrf_protect, name="dispatch")
class RegisterView(APIView):
    """
    POST /api/auth/register/
    {"username": "...", "email": "...", "password": "...", "password_confirmation": "..."}
    Creates a customer account and logs it in. 201 with {username, is_staff}.
    """

    permission_classes = [AllowAny]
    # Rate limit per client IP; the rate is "register" in settings DEFAULT_THROTTLE_RATES
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"

    def post(self, request):
        register_serializer = RegisterSerializer(data=request.data)
        register_serializer.is_valid(raise_exception=True)
        try:
            # atomic: if the insert fails, the database connection stays usable
            with transaction.atomic():
                new_user = register_serializer.save()
        except IntegrityError:
            # Two sign-ups with the same username at the same instant: the
            # database's unique constraint catches the one the check above missed
            return Response({"username": [DUPLICATE_USERNAME_MESSAGE]}, status=status.HTTP_400_BAD_REQUEST)
        login(request, new_user)
        return Response(describe_user(new_user), status=status.HTTP_201_CREATED)


class LogoutView(APIView):
    """POST /api/auth/logout/"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CurrentUserView(APIView):
    """GET /api/auth/me/ -- 403 when logged out, user details when logged in."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(describe_user(request.user))
