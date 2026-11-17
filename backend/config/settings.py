"""
Django settings for the food truck finder API.

Every environment-specific value comes from environment variables so the
same image runs on a laptop (docker-compose.yml) and on EC2
(docker-compose.prod.yml). See ../.env.example for the full list.
"""

import os
from pathlib import Path

BASE_DIRECTORY = Path(__file__).resolve().parent.parent


def read_boolean_env(variable_name, default_value=False):
    """Turn strings like 'true', '1', 'yes' into a real boolean."""
    raw_value = os.environ.get(variable_name)
    if raw_value is None:
        return default_value
    return raw_value.strip().lower() in ("1", "true", "yes", "on")


def read_list_env(variable_name, default_value=""):
    """Turn a comma-separated env var into a list, skipping blanks."""
    raw_value = os.environ.get(variable_name, default_value)
    return [item.strip() for item in raw_value.split(",") if item.strip()]


# --- Core security settings -------------------------------------------------
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-insecure-key-change-me")
DEBUG = read_boolean_env("DJANGO_DEBUG", default_value=False)
ALLOWED_HOSTS = read_list_env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

# Needed in production so Django accepts POSTs (admin login) coming through
# the HTTPS reverse proxy, e.g. "https://trucks.example.com"
CSRF_TRUSTED_ORIGINS = read_list_env("DJANGO_CSRF_TRUSTED_ORIGINS")

# Caddy terminates HTTPS and forwards plain HTTP; this header tells Django
# the original request was secure.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Only send the login (session) and CSRF cookies over HTTPS. Set true on EC2
# once Caddy has a domain + certificate; leave false for http://localhost.
SESSION_COOKIE_SECURE = read_boolean_env("DJANGO_SECURE_COOKIES", default_value=False)
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE


# --- Applications ------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",          # GeoDjango: PointField, distance lookups
    "rest_framework",
    "rest_framework_gis",          # GeoJSON serializers (must come after rest_framework)
    "trucks",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # serves admin CSS/JS in production
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# --- Database: PostgreSQL + PostGIS -----------------------------------------
# The PostGIS engine is what makes distance queries (dwithin) available.
DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": os.environ.get("POSTGRES_DB", "food_trucks"),
        "USER": os.environ.get("POSTGRES_USER", "food_trucks"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
        "HOST": os.environ.get("POSTGRES_HOST", "db"),   # "db" = compose service name
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# --- Auth / i18n ------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# --- Static files (Django admin only; React is served by Caddy) -------------
STATIC_URL = "/django-static/"
STATIC_ROOT = BASE_DIRECTORY / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}


# --- Logging ----------------------------------------------------------------
# Send errors (including 500 tracebacks) to the console so they appear in
# `docker compose logs backend`. Without this, DEBUG=false hides them.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {
        "handlers": ["console"],
        "level": os.environ.get("DJANGO_LOG_LEVEL", "INFO"),
    },
}


# --- Django REST Framework --------------------------------------------------
REST_FRAMEWORK = {
    # Anyone can read trucks; only logged-in users (truck owners) can change them
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
}
