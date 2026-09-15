"""
Django settings for tryPDF!.

Every deployment knob is an environment variable. A local .env file (if present)
is loaded first, so `python manage.py runserver` behaves like production.
"""
import os
import sys
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.utils.csp import CSP

BASE_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# .env loading
# ---------------------------------------------------------------------------
# ponytail: 8 lines of stdlib instead of the python-dotenv dependency. Handles
# KEY=value, comments and blank lines. Add python-dotenv if you ever need
# multiline values, export prefixes or variable interpolation.
def _load_dotenv(path):
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        # Real environment variables always win over the file.
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


_load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in ("true", "1", "yes", "on")


def env_list(name, default=""):
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
DEBUG = env_bool("DEBUG", False)

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if not DEBUG:
        # Refuse to boot rather than silently signing sessions with a public key.
        raise ImproperlyConfigured(
            "DJANGO_SECRET_KEY is not set. Generate one with: "
            "python -c 'import secrets; print(secrets.token_urlsafe(64))'"
        )
    SECRET_KEY = "django-insecure-local-development-only-key"

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

# Railway / Render inject the public hostname; fold it into both lists.
for _var, _is_url in (("RAILWAY_PUBLIC_DOMAIN", False), ("RENDER_EXTERNAL_URL", True)):
    _value = os.environ.get(_var, "").strip().rstrip("/")
    if not _value:
        continue
    _host = _value.split("://", 1)[-1] if _is_url else _value
    _origin = _value if _is_url else f"https://{_value}"
    if _host and _host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_host)
    if _origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(_origin)

# Reverse-proxy HTTPS support (Railway, Render and similar).
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True


# ---------------------------------------------------------------------------
# Security (the HTTPS-only settings would break plain-HTTP local dev)
# ---------------------------------------------------------------------------
TESTING = "test" in sys.argv
RUNSERVER = "runserver" in sys.argv

# The settings below assume the site is actually reachable over HTTPS. The dev
# server and the test client only speak plain HTTP, so enabling them there
# redirects you to a URL that cannot answer and stops the CSRF cookie being sent
# at all. DEBUG alone is not the right switch: a .env with DEBUG=false is
# correct for production and still perfectly normal for a local runserver.
HTTPS_ENABLED = not DEBUG and not TESTING and not RUNSERVER

if HTTPS_ENABLED:
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # Start HSTS at one day; raise to 31536000 once HTTPS is permanent.
    SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", 86400))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", False)
    SECURE_HSTS_PRELOAD = False
    # The container health check talks plain HTTP to 127.0.0.1; a 301 would
    # make it fail and the platform would restart a perfectly healthy container.
    SECURE_REDIRECT_EXEMPT = [r"^healthz$"]

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# ALLOWED_HOSTS = * turns off host validation, and every canonical URL, og:url
# and sitemap entry is built from request.get_host() - so a poisoned Host header
# would rewrite all of them. Refuse to start rather than serve that.
if "*" in ALLOWED_HOSTS and not DEBUG:
    raise ImproperlyConfigured(
        "ALLOWED_HOSTS must not be '*' in production - list your real hostnames."
    )

# Content Security Policy. Django 6 ships this middleware, so no django-csp.
#
# No 'unsafe-inline' for scripts: every inline <script> carries {{ csp_nonce }}.
# The client-side navigation in base.html injects scripts carrying a nonce from
# the page it fetched, which will not match this document's - that is fine,
# because scripts created by script (rather than by the parser) are not subject
# to the inline check at all.
#
# 'self' rather than 'strict-dynamic': the PDF tools reach their library with a
# dynamic import() of /static/vendor/pdf.min.mjs, and strict-dynamic makes the
# browser ignore host sources for exactly that kind of request.
SECURE_CSP = {
    "default-src": [CSP.SELF],
    # wasm-unsafe-eval, not unsafe-eval: pdf.js compiles a WebAssembly image
    # decoder. It does not permit eval().
    "script-src": [CSP.SELF, CSP.NONCE, CSP.WASM_UNSAFE_EVAL,
                   "https://www.googletagmanager.com"],
    # Inline style="" attributes are used throughout the templates; a nonce
    # cannot cover those, only <style> blocks.
    "style-src": [CSP.SELF, CSP.UNSAFE_INLINE],
    # blob: is the uploader's image thumbnails (URL.createObjectURL).
    "img-src": [CSP.SELF, "data:", "blob:", "https://www.googletagmanager.com"],
    # The exfiltration barrier: even an injected script cannot POST a user's
    # file anywhere but back to us.
    "connect-src": [CSP.SELF, "https://www.google-analytics.com",
                    "https://*.google-analytics.com",
                    "https://*.analytics.google.com"],
    "worker-src": [CSP.SELF, "blob:"],          # the pdf.js worker
    "font-src": [CSP.SELF],
    "object-src": [CSP.NONE],
    "base-uri": [CSP.SELF],
    "form-action": [CSP.SELF],
    "frame-ancestors": [CSP.NONE],
}


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'tools',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.csp.ContentSecurityPolicyMiddleware',
    'tools.throttle.AdminLoginThrottleMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.template.context_processors.csp',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# ---------------------------------------------------------------------------
# Database - DATABASE_URL in production, SQLite locally.
# ---------------------------------------------------------------------------
_database_url = os.environ.get("DATABASE_URL", "")
if _database_url:
    import urllib.parse as _up

    _u = _up.urlparse(_database_url)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': _up.unquote(_u.path.lstrip('/')),
            'USER': _up.unquote(_u.username or ''),
            'PASSWORD': _up.unquote(_u.password or ''),
            'HOST': _u.hostname,
            'PORT': _u.port or 5432,
            'CONN_MAX_AGE': 60,
            'CONN_HEALTH_CHECKS': True,
        }
    }
else:
    # SQLITE_PATH exists because the container runs as a non-root user against a
    # root-owned /app, so the database cannot live next to the code.
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.environ.get("SQLITE_PATH") or BASE_DIR / 'db.sqlite3',
        }
    }
    if not DEBUG and not TESTING:
        # Loud, because this is silent data loss: hosts like Render have an
        # ephemeral filesystem, so every deploy would discard all feedback.
        print(
            "WARNING: DATABASE_URL is not set, falling back to SQLite. On a "
            "platform with an ephemeral filesystem this database is wiped on "
            "every deploy. Provision Postgres and set DATABASE_URL.",
            file=sys.stderr,
        )

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------------------
# Static and media files
# ---------------------------------------------------------------------------
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Hashed, compressed filenames in production; plain files in development, where
# collectstatic has usually not been run.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "config.storage.ForgivingManifestStaticFilesStorage"
        )
    },
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


# ---------------------------------------------------------------------------
# Upload limits
# ---------------------------------------------------------------------------
# MAX_UPLOAD_BYTES is the real cap, enforced per file in tools/uploads.py.
# Django's *_MAX_MEMORY_SIZE settings only decide when a body spills to disk.
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", 50))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
MAX_UPLOAD_TOTAL_MB = int(os.environ.get("MAX_UPLOAD_TOTAL_MB", 100))
MAX_UPLOAD_TOTAL_BYTES = MAX_UPLOAD_TOTAL_MB * 1024 * 1024
MAX_UPLOAD_FILES = int(os.environ.get("MAX_UPLOAD_FILES", 25))

# How long generated files stay on disk. On POSIX the download is unlinked as
# soon as it is streamed, so this only cleans up after crashes.
MEDIA_RETENTION_SECONDS = int(os.environ.get("MEDIA_RETENTION_SECONDS", 1800))

DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024      # non-file POST data
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024      # spill to disk past this
DATA_UPLOAD_MAX_NUMBER_FILES = MAX_UPLOAD_FILES + 5
DATA_UPLOAD_MAX_NUMBER_FIELDS = 200

# External converters must finish well inside the gunicorn worker timeout,
# otherwise the worker is killed and the user sees a 502 instead of an error.
CONVERT_TIMEOUT_SECONDS = int(os.environ.get("CONVERT_TIMEOUT_SECONDS", 90))


# ---------------------------------------------------------------------------
# Email - Gmail, over the API where possible.
# ---------------------------------------------------------------------------
# Two transports, both talking only to Google:
#
#   1. Gmail API (preferred). Plain HTTPS to gmail.googleapis.com, so it works
#      on hosts that block outbound SMTP - Render's free/starter tiers do.
#      Set GMAIL_CLIENT_ID / SECRET / REFRESH_TOKEN; get them with:
#          python manage.py gmail_auth
#   2. Gmail SMTP (fallback). Needs an App Password, and an unblocked port 587.
#
# Whichever is configured, the report is written to the database before mail is
# attempted, so a failed notification never loses a submission.
GMAIL_CLIENT_ID = os.environ.get("GMAIL_CLIENT_ID", "")
GMAIL_CLIENT_SECRET = os.environ.get("GMAIL_CLIENT_SECRET", "")
GMAIL_REFRESH_TOKEN = os.environ.get("GMAIL_REFRESH_TOKEN", "")

# Gmail needs an *App Password*, not your account password: Google Account ->
# Security -> 2-Step Verification (must be on) -> App passwords. The 16-character
# value it gives you goes in EMAIL_HOST_PASSWORD; spaces in it are ignored.
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", 587))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "").replace(" ", "")
EMAIL_TIMEOUT = int(os.environ.get("EMAIL_TIMEOUT", 15))

# TLS and SSL are mutually exclusive in Django; picking the wrong one for the
# port is the classic Gmail misconfiguration, so derive it from the port.
if EMAIL_PORT == 465:
    EMAIL_USE_SSL = True
    EMAIL_USE_TLS = False
else:
    EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
    EMAIL_USE_SSL = False

if GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET and GMAIL_REFRESH_TOKEN:
    EMAIL_BACKEND = "config.email_backend.GmailAPIBackend"
elif EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
else:
    # Nothing configured: print the message to the console instead of failing.
    # Reports still reach the database and the admin site.
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Gmail rejects or rewrites a From address that is not the authenticated
# account, so default to it rather than a made-up noreply@ address.
DEFAULT_FROM_EMAIL = (
    os.environ.get("DEFAULT_FROM_EMAIL") or EMAIL_HOST_USER or "noreply@trypdf.in"
)

FEEDBACK_EMAIL = os.environ.get("FEEDBACK_EMAIL", "kamalswarnkar0111@gmail.com")

# ---------------------------------------------------------------------------
# Per-IP throttles (tools/throttle.py)
# ---------------------------------------------------------------------------
# The feedback forms send email, so the limit protects the Gmail quota.
FEEDBACK_RATE_LIMIT = int(os.environ.get("FEEDBACK_RATE_LIMIT", 5))
FEEDBACK_RATE_WINDOW_SECONDS = int(os.environ.get("FEEDBACK_RATE_WINDOW_SECONDS", 3600))

# Each tool POST can hold a worker for the whole CONVERT_TIMEOUT_SECONDS, and
# there are only WEB_CONCURRENCY x threads of them. Without a cap, a handful of
# requests from one address takes the site down for everyone else.
TOOL_RATE_LIMIT = int(os.environ.get("TOOL_RATE_LIMIT", 20))
TOOL_RATE_WINDOW_SECONDS = int(os.environ.get("TOOL_RATE_WINDOW_SECONDS", 300))

# Django has no brute-force protection on the admin login.
ADMIN_LOGIN_RATE_LIMIT = int(os.environ.get("ADMIN_LOGIN_RATE_LIMIT", 10))
ADMIN_LOGIN_RATE_WINDOW_SECONDS = int(os.environ.get("ADMIN_LOGIN_RATE_WINDOW_SECONDS", 900))

# The admin lives at a guessable URL by default, which is what makes it worth
# brute-forcing in the first place. Set ADMIN_URL to something unguessable in
# production; it is defence in depth on top of the throttle above, not instead
# of a strong superuser password.
ADMIN_URL = os.environ.get("ADMIN_URL", "admin").strip("/") + "/"


# ---------------------------------------------------------------------------
# Logging - without this, logger.exception() never reaches the platform logs.
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "standard"},
    },
    "root": {"handlers": ["console"], "level": os.environ.get("LOG_LEVEL", "INFO")},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False},
        # Logs "C++ to Python logger bridge initialized" on every worker boot.
        "pikepdf": {"level": "WARNING"},
    },
}
