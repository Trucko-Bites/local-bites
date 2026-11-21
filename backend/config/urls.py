from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path

from trucks.auth_views import CsrfCookieView, CurrentUserView, LoginView, LogoutView, RegisterView


def health_check(request):
    """Used by Docker healthchecks and for a quick 'is the API up?' test."""
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health_check),
    # Login and sign-up (session cookie, same origin as the React app)
    path("api/auth/csrf/", CsrfCookieView.as_view()),
    path("api/auth/login/", LoginView.as_view()),
    path("api/auth/register/", RegisterView.as_view()),
    path("api/auth/logout/", LogoutView.as_view()),
    path("api/auth/me/", CurrentUserView.as_view()),
    # Everything else the React app calls lives under /api/
    path("api/", include("trucks.urls")),
]
