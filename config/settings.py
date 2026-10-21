"""Django settings for AllergenTrace.

All environment-specific values come from environment variables, so the same
code runs locally (docker compose), in CI and in the cloud (Render + Neon).
See `.env.example` for the list of variables.
"""

import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.environ.get("DJANGO_DEBUG", "False") == "True"

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if not DEBUG:
        raise RuntimeError("DJANGO_SECRET_KEY must be set when DEBUG is off.")
    SECRET_KEY = "insecure-local-development-key"

ALLOWED_HOSTS = [h for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h]
# Render sets this variable automatically for the public hostname of the service.
if render_host := os.environ.get("RENDER_EXTERNAL_HOSTNAME"):
    ALLOWED_HOSTS.append(render_host)
CSRF_TRUSTED_ORIGINS = [f"https://{h}" for h in ALLOWED_HOSTS if h not in ("localhost", "127.0.0.1")]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "catalog",
    "recipes",
    "publication",
    "simple_history",
]

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "home"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
    "publication.middleware.PublicationSyncMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "publication.context_processors.impact",
                "publication.context_processors.pending_approvals",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Local default matches docker-compose.yml; in the cloud DATABASE_URL points to Neon.
DATABASES = {
    "default": dj_database_url.config(
        default="postgres://allergentrace:allergentrace@localhost:5432/allergentrace",
    )
}
# Login rate limits and lockouts are kept in a cache table in the same database, so all
# workers share them and they survive restarts (see accounts/security.py).
CACHES = {"default": {"BACKEND": "django.core.cache.backends.db.DatabaseCache", "LOCATION": "django_cache"}}
# Fail with a clear error instead of hanging when the database cannot be reached.
DATABASES["default"].setdefault("OPTIONS", {})["connect_timeout"] = 10

# Passwords are stored with bcrypt (cost 12) over SHA-256. Older PBKDF2 hashes still verify and
# Django re-hashes them with bcrypt at the user's next successful login.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en"
# The back office is English. Only the guest menu is bilingual (US-14): its URL carries the
# language, so there is no LocaleMiddleware and Django's own German strings never mix in.
LANGUAGES = [("de", "Deutsch"), ("en", "English")]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "Europe/Berlin"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
# Bootstrap is served from our own server instead of a CDN, so guests' IP addresses
# are not sent to third parties (NFR-11).
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# US-20: approval notices. In the cloud they go through the Brevo API (see config/mail.py);
# locally they are printed to the console.
BREVO_API_KEY = os.environ.get("BREVO_API_KEY", "")
EMAIL_BACKEND = (
    "config.mail.BrevoEmailBackend" if BREVO_API_KEY else "django.core.mail.backends.console.EmailBackend"
)
# Contact address shown in the privacy policy and the terms of use.
CONTACT_EMAIL = os.environ.get("DJANGO_CONTACT_EMAIL", "")

PASSWORD_RESET_TIMEOUT = 3 * 24 * 3600  # also the validity of registration links

# Security events (rejected logins, rate limits, lockouts) go to the console, i.e. the Render log.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {
        "accounts.security": {"handlers": ["console"], "level": "INFO"},
        "config.mail": {"handlers": ["console"], "level": "INFO"},
    },
}

DEFAULT_FROM_EMAIL = os.environ.get("DJANGO_DEFAULT_FROM_EMAIL", "AllergenTrace <noreply@localhost>")

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = os.environ.get("DJANGO_SECURE_SSL_REDIRECT", "True") == "True"
    SESSION_COOKIE_SECURE = SECURE_SSL_REDIRECT
    CSRF_COOKIE_SECURE = SECURE_SSL_REDIRECT
    SECURE_HSTS_SECONDS = 3600 if SECURE_SSL_REDIRECT else 0

# HSTS subdomains and preload only make sense for a domain we own; the app runs on a
# subdomain of the hosting provider (see docs/technical-debt.md).
SILENCED_SYSTEM_CHECKS = ["security.W005", "security.W021"]
