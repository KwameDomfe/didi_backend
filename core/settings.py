"""
Django settings for core project.

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.2/ref/settings/

"""
import sys, os
from pathlib import Path
from urllib.parse import urlparse

# ── Environment selection ──────────────────────────────────────────────────────
# Switch environments by setting DJANGO_ENV in your shell or CI/CD:
#   DJANGO_ENV=development  → loads .env.development  (default)
#   DJANGO_ENV=production   → loads .env.production
#   DJANGO_ENV=staging      → loads .env.staging
# OS / platform environment variables always take precedence over the file.
from decouple import Csv, UndefinedValueError, Config, RepositoryEnv, RepositoryEmpty

_env_name = os.environ.get('DJANGO_ENV', 'development')
_env_file = Path(__file__).resolve().parent.parent / f".env.{_env_name}"

if _env_file.exists():
    config = Config(RepositoryEnv(str(_env_file)))
else:
    # Fall back to os-only (useful on platforms that inject env vars directly)
    config = Config(RepositoryEmpty())


# import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


def _config_first(*names: str, default=None, cast=str):
    for name in names:
        try:
            return config(name, cast=cast)
        except UndefinedValueError:
            continue
    return default


def _config_csv(name: str, default: str | None = None) -> list[str]:
    raw_default = '' if default is None else default
    return config(name, default=raw_default, cast=Csv())


def _normalize_csv_items(values: list[str]) -> list[str]:
    cleaned = []
    for value in values:
        item = value.strip().strip('[]').strip().strip('"\'')
        if item:
            cleaned.append(item)
    return cleaned

### Custom User Model
AUTH_USER_MODEL = 'accounts.CustomUser'

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# Accept either DJANGO_DEBUG or DEBUG (from .env). Default to False for production safety.
DEBUG = _config_first('DJANGO_DEBUG', 'DEBUG', default=False, cast=bool)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = (
    _config_first('DJANGO_SECRET_KEY', 'SECRET_KEY', default='')
    or ('dev-insecure-secret-key-change-me' if DEBUG else '')
)

# Fail loudly if SECRET_KEY is not set in production
if not SECRET_KEY:
    raise ValueError("DJANGO_SECRET_KEY environment variable must be set in production")

# Always allow localhost for local development
ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'didi-app-feixt.ondigitalocean.app']

# Accept either DJANGO_ALLOWED_HOSTS or ALLOWED_HOSTS (comma-separated)
allowed_hosts_env = _config_csv(
    'DJANGO_ALLOWED_HOSTS',
    default=_config_first('ALLOWED_HOSTS', default=''),
)
allowed_hosts_env = _normalize_csv_items(allowed_hosts_env)
if allowed_hosts_env:
    ALLOWED_HOSTS += allowed_hosts_env

# De-duplicate while preserving order
ALLOWED_HOSTS = list(dict.fromkeys(ALLOWED_HOSTS))

### Security Settings for Production
# `runserver` only speaks HTTP, so skip HTTPS enforcement there even if DEBUG=False.
IS_RUNSERVER = 'runserver' in sys.argv
if not DEBUG and not IS_RUNSERVER:
    # Force HTTPS
    SECURE_SSL_REDIRECT = True
    
    # HSTS Settings (HTTP Strict Transport Security)
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    
    # Cookie Security
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    
    # Additional Security Headers
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'
    
    # Proxy settings for platforms like Digital Ocean App Platform
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

### Application definition

DEFAULT_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.sites',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework.authtoken',
    'django_filters',
    'corsheaders',
    'djoser',
    'channels',
    'drf_spectacular',
    'drf_spectacular_sidecar',
    'django_json_widget',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.facebook',
    'allauth.socialaccount.providers.linkedin_oauth2',
    'allauth.socialaccount.providers.twitter',
    'dj_rest_auth',
    'dj_rest_auth.registration',
]
# django-allauth and social login settings
SITE_ID = 1

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
)

# Optionally, configure allauth/dj-rest-auth settings here
# ACCOUNT_EMAIL_VERIFICATION = 'optional'
# ACCOUNT_AUTHENTICATION_METHOD = 'username_email'
# ACCOUNT_EMAIL_REQUIRED = True

THIRD_PARTY_API_SERVICES = [
    
]

LOCAL_APPS = [
    'apps.accounts',
    'apps.restaurants',
    'apps.orders',
    'apps.social',
    'apps.posts',
]

INSTALLED_APPS = (
    DEFAULT_APPS + 
    THIRD_PARTY_APPS + 
    THIRD_PARTY_API_SERVICES + 
    LOCAL_APPS
)

### Middleware configuration

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


ROOT_URLCONF = 'core.urls'

### Templates configuration with context processors for auth and messages
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'


### Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

# Use PostgreSQL in production (DATABASE_URL env var), SQLite locally
DATABASE_URL = os.environ.get('DATABASE_URL')
db_info = urlparse(DATABASE_URL) if DATABASE_URL else None

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2' if db_info else 'django.db.backends.sqlite3',
        'NAME': db_info.path[1:] if db_info else BASE_DIR / 'db.sqlite3',
        'USER': db_info.username if db_info else '',
        'PASSWORD': db_info.password if db_info else '',
        'HOST': db_info.hostname if db_info else '',
        'PORT': db_info.port if db_info else '',
        'OPTIONS': {'sslmode': 'require'} if db_info else {},
        'CONN_MAX_AGE': 60 if db_info else 0,  # Reuse DB connections for 60s in production
    }
}


### Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


### Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


### Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

### Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

### REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'The Restaurant Backend API',
    'DESCRIPTION': 'API for The Restaurant backend services',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    # Available themes:
    # - 'drf-spectacular-sidecar'
    # - 'cerulean'
    # - 'cosmo'
    # - 'darkly'
    # - 'flatly'
    # - 'journal'
    # - 'litera'
    # - 'lumen'
    # - 'lux'
    # - 'materia'
    # - 'minty'
    # - 'pulse'
    # - 'sandstone'
    # - 'simplex'
    # - 'sketchy'
    # - 'slate'
    # - 'solar'
    # - 'spacelab'
    # - 'superhero'
    # - 'united'
    # - 'yeti'
    'SWAGGER_UI_DIST': 'drf-spectacular-sidecar',  # Use sidecar package
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': True,
    },
}

### CORS Configuration
if DEBUG:
    # Development: Allow all origins for easier testing
    CORS_ALLOW_ALL_ORIGINS = True
else:
    # Production: Only allow specific origins
    CORS_ALLOW_ALL_ORIGINS = False
    
    # Get allowed origins from environment variable
    cors_origins_env = _config_csv('CORS_ALLOWED_ORIGINS')
    cors_origins_env = _normalize_csv_items(cors_origins_env)
    if cors_origins_env:
        CORS_ALLOWED_ORIGINS = cors_origins_env
    else:
        # Default production origins
        CORS_ALLOWED_ORIGINS = [
            'https://127.0.0.1:8000',
            'https://didi-app-feixt.ondigitalocean.app',
            'https://www.bedidi-app-scq7q.ondigitalocean.app',
        ]

CSRF_TRUSTED_ORIGINS = _config_csv(
    'CSRF_TRUSTED_ORIGINS',
    ','.join(CORS_ALLOWED_ORIGINS) if not DEBUG else None,
)
CSRF_TRUSTED_ORIGINS = _normalize_csv_items(CSRF_TRUSTED_ORIGINS)

CORS_ALLOW_CREDENTIALS = True

# Additional CORS settings for mobile compatibility
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

### JWT Configuration
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
}

### Media files Configuration
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

### Email Configuration
if DEBUG:
    # Development: Print emails to console
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    # Production: Use SMTP
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
    try:
        EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
    except ValueError:
        EMAIL_PORT = 587
    EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
    EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
    EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')

DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='The Restaurant <noreply@core.com>')
FRONTEND_URL = config('FRONTEND_URL', default='http://localhost:5173')

### Channels Configuration
ASGI_APPLICATION = 'core.asgi.application'

### Redis Configuration for Channels
# If REDIS_URL is not set, fall back to InMemoryChannelLayer to avoid
# connection hangs on platforms without a Redis service.
REDIS_URL = os.environ.get('REDIS_URL') or config('REDIS_URL', default='')

if REDIS_URL:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                'hosts': [REDIS_URL],
            },
        },
    }
else:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }

### Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': config('DJANGO_LOG_LEVEL', default='INFO' if not DEBUG else 'DEBUG'),
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': config('DJANGO_LOG_LEVEL', default='INFO'),
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.utils.autoreload': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}
