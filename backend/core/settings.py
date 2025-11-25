from pathlib import Path
from datetime import timedelta
import os
from dotenv import load_dotenv

# -----------------------------------------------------------------------------
# Paths & .env
# -----------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")  # read backend/.env


def env_bool(key: str, default: bool = False) -> bool:
    return os.getenv(key, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_list(key: str, default: str = "") -> list[str]:
    raw = os.getenv(key, default)
    if not raw:
        return []
    return [x.strip() for x in raw.split(",") if x.strip()]


# -----------------------------------------------------------------------------
# Security / debug
# -----------------------------------------------------------------------------
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-key-change-me")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost")

# Frontend origin(s) for CORS/CSRF (Vite on 5174/5173 by default)
FRONTEND_ORIGINS = env_list(
    "FRONTEND_ORIGINS",
    "http://127.0.0.1:5174,http://localhost:5174,"
    "http://127.0.0.1:5173,http://localhost:5173",
)

# -----------------------------------------------------------------------------
# Installed apps
# -----------------------------------------------------------------------------
INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # 3rd-party
    "rest_framework",
    "drf_spectacular",
    "corsheaders",
    "django_filters",
    "storages",  # harmless if S3 not configured

    # Local apps
    "users",
    "catalog",
    "cart",
    "orders",
    "payments",
    "promotions",
    "shipping",
    "wishlist",
    "searchapp",
    "reports",
    "cms",
    "backoffice",
]

# -----------------------------------------------------------------------------
# Middleware
# -----------------------------------------------------------------------------
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",   # keep CORS first
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

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

WSGI_APPLICATION = "core.wsgi.application"
ASGI_APPLICATION = "core.asgi.application"

# -----------------------------------------------------------------------------
# Database
# -----------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if DATABASE_URL:
    try:
        import dj_database_url  # type: ignore
        DATABASES["default"] = dj_database_url.parse(
            DATABASE_URL, conn_max_age=600, ssl_require=not DEBUG
        )
    except Exception:
        pass  # fall back to sqlite

# -----------------------------------------------------------------------------
# Auth / i18n
# -----------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# -----------------------------------------------------------------------------
# Static / media
# -----------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# NOTE: images on the Orders page depend on MEDIA_* working.
# core/urls.py already serves MEDIA in DEBUG. Keep DEBUG=True in dev.

# -----------------------------------------------------------------------------
# DRF / JWT / Filters / Pagination
# -----------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": int(os.getenv("PAGE_SIZE", 12)),

    # --- NEW: scoped throttling (env-overridable) ---
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "apply-coupon": os.getenv("THROTTLE_APPLY_COUPON", "10/min"),
        "cart-items": os.getenv("THROTTLE_CART_ITEMS", "30/min"),
        "orders-public": os.getenv("THROTTLE_ORDERS_PUBLIC", "60/hour"),  # <-- added
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.getenv("JWT_ACCESS_MINUTES", 60))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.getenv("JWT_REFRESH_DAYS", 7))),
    "ROTATE_REFRESH_TOKENS": env_bool("JWT_ROTATE_REFRESH", False),
    "BLACKLIST_AFTER_ROTATION": env_bool("JWT_BLACKLIST_AFTER_ROTATION", False),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# Swagger / OpenAPI
SPECTACULAR_SETTINGS = {
    "TITLE": "E-Commerce API",
    "DESCRIPTION": "Catalog, Cart, Checkout, Payments",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SECURITY": [{"jwtAuth": []}],
    "COMPONENT_SPLIT_REQUEST": True,
    "SERVERS": [{"url": os.getenv("OPENAPI_SERVER_URL", "http://127.0.0.1:8000")}],
    "COMPONENTS": {
        "securitySchemes": {
            "jwtAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
        }
    },
}

# -----------------------------------------------------------------------------
# CORS / CSRF
# -----------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = FRONTEND_ORIGINS
CORS_ALLOW_CREDENTIALS = True
# Make sure Authorization header is allowed in dev tools & proxies:
CORS_ALLOW_HEADERS = list(os.getenv("CORS_ALLOW_HEADERS", "").split(",")) if os.getenv("CORS_ALLOW_HEADERS") else [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

# CSRF is relevant for admin or any future form views; keep trusted origins.
# Must include scheme (which FRONTEND_ORIGINS already does).
CSRF_TRUSTED_ORIGINS = FRONTEND_ORIGINS

# -----------------------------------------------------------------------------
# Cookies (site-wide so /api/* gets the cart session)
# For cross-port localhost dev (5173 ↔ 8000), we need SameSite=None.
# -----------------------------------------------------------------------------
SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "sessionid")
SESSION_COOKIE_PATH = os.getenv("SESSION_COOKIE_PATH", "/")
CSRF_COOKIE_NAME    = os.getenv("CSRF_COOKIE_NAME", "csrftoken")
CSRF_COOKIE_PATH    = os.getenv("CSRF_COOKIE_PATH", "/")

if DEBUG:
    # Cross-site (different ports) XHR needs SameSite=None
    SESSION_COOKIE_SAMESITE = "None"
    CSRF_COOKIE_SAMESITE    = "None"
    # Chrome usually expects Secure with None, but relax on localhost:
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE    = False
else:
    # In production, keep your existing policy (override via env if needed)
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    CSRF_COOKIE_SAMESITE    = os.getenv("CSRF_COOKIE_SAMESITE", "Lax")

# -----------------------------------------------------------------------------
# Email (dev)
# -----------------------------------------------------------------------------
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "no-reply@ecommerce.local")

# -----------------------------------------------------------------------------
# App specific
# -----------------------------------------------------------------------------
CART_SESSION_ID = os.getenv("CART_SESSION_ID", "cart")

# --- NEW: Cart behavior toggles ---
CART_MERGE_STRATEGY = os.getenv("CART_MERGE_STRATEGY", "sum").lower()  # "sum" or "max"
CART_MAX_QTY = int(os.getenv("CART_MAX_QTY", 99))

# Orders / Pricing
# Read by orders.pricing.GST_RATE (Decimal percent, e.g. 18)
GST_RATE_PERCENT = os.getenv("GST_RATE_PERCENT", "0")

# Payments (Razorpay placeholders; mocked in dev)
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
PAYMENT_CURRENCY = os.getenv("PAYMENT_CURRENCY", "INR")
PAYMENTS_MOCK = env_bool("PAYMENTS_MOCK", True)  # used by payments/views

# Optional S3 config. If bucket is set, switch default storage to S3 automatically.
AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME", "")
AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME", "")
AWS_S3_CUSTOM_DOMAIN = os.getenv("AWS_S3_CUSTOM_DOMAIN", "").strip()

if AWS_STORAGE_BUCKET_NAME:
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
    if AWS_S3_CUSTOM_DOMAIN:
        MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/"

# -----------------------------------------------------------------------------
# Production security toggles (off in DEBUG)
# -----------------------------------------------------------------------------
if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
    SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", True)
    CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", True)
    SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", 3600))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", True)
    SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", True)
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    X_FRAME_OPTIONS = os.getenv("X_FRAME_OPTIONS", "DENY")
    SECURE_REFERRER_POLICY = os.getenv("SECURE_REFERRER_POLICY", "same-origin")

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "%(levelname)s %(name)s: %(message)s"},
        "verbose": {
            "format": "%(asctime)s %(levelname)s [%(name)s] %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "verbose"}},
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "django.db.backends": {"handlers": ["console"], "level": os.getenv("DB_LOG_LEVEL", "WARNING"), "propagate": False},
    },
}
