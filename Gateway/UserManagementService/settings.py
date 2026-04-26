# BASE_DIR = /mnt/newhome/nimamze/Documents/Code/Project/Enma/Gateway
from pathlib import Path
from dotenv import load_dotenv
import os
from datetime import timedelta
from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("SECRET_KEY")
DEBUG = os.getenv("DEBUG_MODE", "True") == "True"
SAVE_FILES_LOCALLY = os.getenv("SAVE_FILES_LOCALLY", "True") == "True"

ALLOWED_HOSTS = []

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "drf_yasg",
    "rest_framework",
    "rest_framework.authtoken",
    "django_celery_results",
    "core.apps.CoreConfig",
    "accounts.apps.AccountsConfig",
    "addresses.apps.AddressesConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "UserManagementService.urls"

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


WSGI_APPLICATION = "UserManagementService.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": "5432",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Asia/Tehran"

USE_I18N = True

USE_TZ = True

STATIC_URL = "/static/"

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

os.makedirs(MEDIA_ROOT, exist_ok=True)
if not SAVE_FILES_LOCALLY:
    INSTALLED_APPS += ["storages"]
    AWS_USERS_ACCESS_KEY_ID = os.getenv("S3_USERS_ACCESS_KEY")
    AWS_USERS_SECRET_ACCESS_KEY = os.getenv("S3_USERS_SECRET_KEY")
    AWS_USERS_STORAGE_BUCKET_NAME = os.getenv("S3_USERS_BUCKET_NAME")
    AWS_USERS_S3_ENDPOINT_URL = os.getenv("S3_USERS_ENDPOINT")


AUTH_USER_MODEL = "accounts.CustomUser"

AUTHENTICATION_BACKENDS = [
    "accounts.backend.CustomAuthentication",
    "django.contrib.auth.backends.ModelBackend",
]

SWAGGER_SETTINGS = {
    "SECURITY_DEFINITIONS": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "JWT Authorization header using the Bearer scheme. Example: 'Bearer <token>'",
        },
    }
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "accounts.authentication.RedisBlacklistJWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": False,
}

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 100,
                "retry_on_timeout": True,
            },
        },
    }
}

CELERY_ACCEPT_CONTENT = ["application/json"]
CELERY_RESULT_SERIALIZER = "json"
CELERY_TASK_SERIALIZER = "json"
CELERY_TIMEZONE = "Asia/Tehran"
CELERY_BROKER_URL = f"{REDIS_URL}/0"
CELERY_RESULT_BACKEND = f"{REDIS_URL}/1"

EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")

CELERY_BEAT_SCHEDULE = {
    "cleanup-expired-jwt-tokens-every-night": {
        "task": "core.tasks.cleanup_expired_jwt_tokens",
        "schedule": crontab(hour=2, minute=0),
    },
    "send-daily-email": {
        "task": "core.tasks.send_email_for_not_login_users",
        "schedule": crontab(hour=3, minute=0),
    },
}

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

KAVENEGAR_API_KEY = os.getenv("KAVENEGAR_API_KEY")
KAVENEGAR_SENDER = os.getenv("KAVENEGAR_SENDER")


REST_FRAMEWORK = {
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {"anon": "50/day", "user": "500/day"},
}

RATE_LIMIT_PASSWORD_CHANGE = int(os.getenv("PASSWORD_CHANGE_RATE_LIMIT", 86400))
RATE_LIMIT_PHONE_CHANGE = int(os.getenv("PHONE_CHANGE_RATE_LIMIT", 86400))
RATE_LIMIT_PASSWORD_RESET = int(os.getenv("PASSWORD_FORGOT_RATE_LIMIT", 86400))
RATE_LIMIT_OTP_DAILY = int(os.getenv("OTP_DAILY_RATE_LIMIT", 5))
OTP_TTL = int(os.getenv("OTP_TIME_VALIDATION", 300))
OTP_AUTHORIZATION_TTL = int(os.getenv("SIGN_UP_OTP_TIME_VALIDATION", 300))
OTP_SIGNUP_TTL = int(os.getenv("SIGN_UP_OTP_TIME_VALIDATION", 86400))
OTP_RATE_LIMIT_TTL = int(os.getenv("SIGN_UP_OTP_TIME_VALIDATION", 86400))

MAPIR_API_KEY = os.getenv("MAPIR_API_KEY")
