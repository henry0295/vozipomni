import os
from pathlib import Path
from decouple import config

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='vozipomni-insecure-secret-key-change-me')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

# Application definition
INSTALLED_APPS = [
    # Local apps (debe ir primero para modelo de usuario personalizado)
    'apps.users',
    
    # Django apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_simplejwt',
    'corsheaders',
    'channels',
    'django_filters',
    'drf_spectacular',
    'django_celery_beat',
    'django_celery_results',
    
    # Local apps (resto de apps)
    'apps.campaigns',
    'apps.agents',
    'apps.contacts',
    'apps.telephony',
    'apps.reports',
    'apps.queues',
    'apps.recordings',
    'apps.api',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# Database
# Use DATABASE_URL if provided (from docker-compose env), otherwise individual vars
_db_url = os.environ.get('DATABASE_URL', '')
if _db_url:
    import re as _re
    _m = _re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):([^/]+)/(.+)', _db_url)
    if _m:
        _DB_USER, _DB_PASS, _DB_HOST, _DB_PORT, _DB_NAME = _m.groups()
    else:
        _DB_NAME = config('DB_NAME', default='vozipomni')
        _DB_USER = config('DB_USER', default='vozipomni_user')
        _DB_PASS = config('DB_PASSWORD', default='vozipomni_db_2026')
        _DB_HOST = config('DB_HOST', default='postgres')
        _DB_PORT = config('DB_PORT', default='5432')
else:
    _DB_NAME = config('DB_NAME', default='vozipomni')
    _DB_USER = config('DB_USER', default='vozipomni_user')
    _DB_PASS = config('DB_PASSWORD', default='vozipomni_db_2026')
    _DB_HOST = config('DB_HOST', default='postgres')
    _DB_PORT = config('DB_PORT', default='5432')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': _DB_NAME,
        'USER': _DB_USER,
        'PASSWORD': _DB_PASS,
        'HOST': _DB_HOST,
        'PORT': _DB_PORT,
        'CONN_MAX_AGE': 600,
        'OPTIONS': {
            'connect_timeout': 10,
        }
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'es-co'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'static'
STATICFILES_DIRS = []

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Recordings
RECORDINGS_ROOT = BASE_DIR / 'recordings'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'users.User'

# Redis Configuration
REDIS_URL = config('REDIS_URL', default='redis://localhost:6379/0')

# Asterisk Configuration
ASTERISK_HOST = config('ASTERISK_HOST', default='asterisk')
ASTERISK_AMI_PORT = config('ASTERISK_AMI_PORT', default=5038, cast=int)
ASTERISK_AMI_USER = config('ASTERISK_AMI_USER', default='admin')
ASTERISK_AMI_PASSWORD = config('ASTERISK_AMI_PASSWORD', default='')
ASTERISK_CONFIG_DIR = config('ASTERISK_CONFIG_DIR', default='/var/lib/asterisk/dynamic')

# Celery Configuration
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = 'django-db'
CELERY_CACHE_BACKEND = 'django-cache'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutos

# Channels (WebSocket)
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [REDIS_URL],
            'capacity': 1500,
            'expiry': 10,
        },
    },
}

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DATETIME_FORMAT': '%Y-%m-%d %H:%M:%S',
    'DATE_FORMAT': '%Y-%m-%d',
}

# JWT Configuration
from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
}

# CORS Configuration
# Limpiar espacios en blanco de cada origen
CORS_ALLOWED_ORIGINS = [
    origin.strip() 
    for origin in config('CORS_ORIGINS', default='http://localhost:3000,http://localhost,http://127.0.0.1').split(',')
]

# Configuración de CORS para producción
CORS_ORIGIN_ALLOW_ALL = config('CORS_ALLOW_ALL', default=False, cast=bool)

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]
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

# Configuración adicional para depuración
CORS_PREFLIGHT_MAX_AGE = 86400  # 24 horas

# Asterisk Configuration
ASTERISK_CONFIG = {
    'HOST': config('ASTERISK_HOST', default='localhost'),
    'AMI_PORT': config('ASTERISK_AMI_PORT', default=5038, cast=int),
    'AMI_USERNAME': config('ASTERISK_AMI_USER', default='admin'),
    'AMI_PASSWORD': config('ASTERISK_AMI_PASSWORD', default='vozipomni_ami_2026'),
    'SIP_PORT': 5060,
    'WEBRTC_PORT': 8088,
    'RTP_START': 10000,
    'RTP_END': 10100,
}

# PJSIP Configuration Path
# Ruta donde se generará automáticamente el archivo pjsip_wizard.conf
# con las configuraciones de troncales creadas desde la interfaz web
PJSIP_CONFIG_PATH = config('PJSIP_CONFIG_PATH', default=f'{ASTERISK_CONFIG_DIR}/pjsip_wizard.conf')

# API Documentation
SPECTACULAR_SETTINGS = {
    'TITLE': 'VoziPOmni Contact Center API',
    'DESCRIPTION': 'API REST para el sistema de Contact Center VoziPOmni',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
}

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'celery': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Security Settings for Production
if not DEBUG:
    # Solo activar SSL redirect si hay HTTPS configurado
    SECURE_SSL_REDIRECT = False  # Desactivado para entorno sin HTTPS
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 0
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False

# Forzar CORS permisivo en producción si no hay HTTPS
CORS_ORIGIN_ALLOW_ALL = True
