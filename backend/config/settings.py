"""Django settings. Everything that differs between environments comes from environment variables
(see ../.env.example). Defaults are safe for local development with mock integrations."""

import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in env(name, default).split(",") if item.strip()]


def env_number(name: str, default: float) -> float:
    try:
        return float(env(name, str(default)))
    except ValueError as exc:
        raise ImproperlyConfigured(f"{name} must be a number") from exc


DEBUG = env_bool("DJANGO_DEBUG", False)
SECRET_KEY = env("DJANGO_SECRET_KEY") or ("insecure-development-key" if DEBUG else "")
if not SECRET_KEY:
    raise ImproperlyConfigured("Set DJANGO_SECRET_KEY (or DJANGO_DEBUG=1 for local development).")

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,backend")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", "http://localhost:5173,http://localhost:8080")
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = env_bool("DJANGO_SECURE_COOKIES", False)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "drf_spectacular",
    "drf_spectacular_sidecar",
    "accounts",
    "integrations",
    "training",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

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

DATABASES = {
    "default": dj_database_url.config(default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}", conn_max_age=60),
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

LANGUAGE_CODE = "en"
TIME_ZONE = env("TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(env("MEDIA_ROOT", str(BASE_DIR / "media")))
SERVE_MEDIA = env_bool("SERVE_MEDIA", True)
WHITENOISE_USE_FINDERS = WHITENOISE_AUTOREFRESH = DEBUG  # no collectstatic needed in development
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["accounts.permissions.IsStaffMember"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_RATES": {"login": "10/min", "survey": "30/min"},
    "EXCEPTION_HANDLER": "training.api.errors.exception_handler",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Training Management System API",
    "DESCRIPTION": "Cohorts, agendas, weekly surveys, gradebook, Classroom sync and materials. "
    "Authenticate with `Authorization: Token <key>` from POST /api/auth/login/.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SWAGGER_UI_DIST": "SIDECAR",
    "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
    "REDOC_DIST": "SIDECAR",
    "ENUM_NAME_OVERRIDES": {
        "LessonKindEnum": "training.models.Lesson.Kind",
        "AssignmentKindEnum": "training.models.Assignment.Kind",
        "MaterialKindEnum": "training.models.LearningMaterial.Kind",
        "AgendaKindEnum": "training.models.Agenda.Kind",
    },
}

# Email: console output by default; SMTP (e.g. Mailpit in docker-compose) when EMAIL_HOST is set.
EMAIL_HOST = env("EMAIL_HOST")
EMAIL_PORT = int(env_number("EMAIL_PORT", 1025))
EMAIL_HOST_USER = env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", False)
EMAIL_BACKEND = env("EMAIL_BACKEND") or (
    "django.core.mail.backends.smtp.EmailBackend" if EMAIL_HOST else "django.core.mail.backends.console.EmailBackend"
)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "Training Office <training@academy.example>")

# Application settings (read through django.conf.settings.TMS).
TMS = {
    "ORG_NAME": env("ORG_NAME", "Demo Academy"),
    "FRONTEND_URL": env("FRONTEND_URL", "http://localhost:5173").rstrip("/"),
    "PUBLIC_BASE_URL": (env("PUBLIC_BASE_URL") or env("FRONTEND_URL", "http://localhost:5173")).rstrip("/"),
    # Integrations: only the offline mocks are implemented in this demo.
    "GOOGLE_MODE": env("GOOGLE_MODE", "mock"),
    "MOCK_GOOGLE_EMAIL": env("MOCK_GOOGLE_EMAIL", "coordinator@academy.example"),
    "MOCK_TOKEN_DAYS": env_number("MOCK_TOKEN_DAYS", 7),
    "WHATSAPP_MODE": env("WHATSAPP_MODE", "mock"),
    "CLASSROOM_PROVIDER": env("CLASSROOM_PROVIDER", "fake"),
    "CLASSROOM_MIN_COHORT": int(env_number("CLASSROOM_MIN_COHORT", 100)),
    "CLASSROOM_SYNC_MINUTES": env_number("CLASSROOM_SYNC_MINUTES", 15),
    "CLASSROOM_AUTO_IMPORT": env_bool("CLASSROOM_AUTO_IMPORT", False),
    "CLASSROOM_ACTIVE_DAYS": int(env_number("CLASSROOM_ACTIVE_DAYS", 30)),
    "SCHEDULER_TICK_SECONDS": env_number("SCHEDULER_TICK_SECONDS", 60),
    "PDF_FONT_PATH": env("PDF_FONT_PATH"),
    "TOKEN_ENCRYPTION_KEY": env("TOKEN_ENCRYPTION_KEY"),
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")},
}
