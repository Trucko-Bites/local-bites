"""
Session-based login for the React app.

The React app and the API share one origin (Vite proxy in dev, Caddy in prod),
so Django's normal session cookie works: no tokens to store in the browser.
The session cookie is HttpOnly, so JavaScript can't read or leak it.

Flow:
  1. GET  /api/auth/csrf/    sets the csrftoken cookie
  2. POST /api/auth/login/   with header X-CSRFToken: <cookie value>
  3. Later POSTs send the same header; the session cookie identifies the user
"""

from django.contrib.auth import authenticate, login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


def describe_user(user):
    """The only user details the frontend needs."""
    return {"username": user.username, "is_staff": user.is_staff}


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(trim_whitespace=False)


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
