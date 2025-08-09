from pathlib import Path
import environ
import os

env = environ.Env()
environ.Env.read_env()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = env('SECRET_KEY', default='your-secret-key-for-development-only-change-in-production')
DEBUG = env.bool('DEBUG', True)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1', 'testserver'])

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party
    'rest_framework',
    'corsheaders',
    'django_filters',
    'drf_spectacular',
    
    # Workflow engine
    'viewflow',
    'viewflow.workflow',
    
    # Local apps
    'apps.common',
    'apps.api',
    'apps.warehouse',
    'apps.quality',
    'apps.laboratory',
    'apps.production',
    'apps.certificates',
    'apps.workflow',
    'apps.notifications',
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

# CORS
CORS_ALLOW_ALL_ORIGINS = env.bool('CORS_ALLOW_ALL_ORIGINS', default=False)
CORS_ALLOWED_ORIGINS = env.list(
    'CORS_ALLOWED_ORIGINS',
    default=[
        'http://localhost:3000',
        'http://127.0.0.1:3000',
    ],
)
CORS_ALLOW_CREDENTIALS = False

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

# Database: prefer DATABASE_URL (PostgreSQL), fallback to SQLite for local dev
DATABASES = {
    'default': env.db(
        'DATABASE_URL',
        default=f"sqlite:///{(BASE_DIR / 'metalqms.db').as_posix()}",
    )
}

# Celery Configuration (опционально для локального тестирования)
CELERY_BROKER_URL = env('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('REDIS_URL', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Europe/Moscow'

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# Telegram
TELEGRAM_BOT_TOKEN = env('TELEGRAM_BOT_TOKEN', default='')
TELEGRAM_WEBHOOK_URL = env('TELEGRAM_WEBHOOK_URL', default='')
TELEGRAM_RATE_LIMIT = 30  # сообщений в секунду (ограничение Telegram API)

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
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
}

# DRF Spectacular (API docs)
SPECTACULAR_SETTINGS = {
    'TITLE': 'MetalQMS API',
    'DESCRIPTION': 'Quality Management System for Metal Production',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
    },
}

# Celery Configuration
CELERY_BROKER_URL = env('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = env('REDIS_URL', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Europe/Moscow'
TIME_ZONE = 'Europe/Moscow'

# Workflow Configuration
VIEWFLOW_SITE_NAME = "MetalQMS Workflow"
VIEWFLOW_LOCK_DEFAULT_TIMEOUT = 60 * 60  # 1 hour
VIEWFLOW_DEFAULT_APP_LABEL = 'workflow'

# SLA Monitoring
SLA_WARNING_THRESHOLD = 0.8  # 80% of SLA time
SLA_CRITICAL_THRESHOLD = 1.0  # 100% of SLA time

# Celery Beat Schedule
CELERY_BEAT_SCHEDULE = {
    # Временно отключены workflow задачи
    # 'monitor-sla-violations': {
    #     'task': 'apps.workflow.tasks.monitor_sla_violations',
    #     'schedule': 900.0,  # Каждые 15 минут
    # },
    # 'cleanup-old-sla-violations': {
    #     'task': 'apps.workflow.tasks.cleanup_old_sla_violations',
    #     'schedule': 86400.0,  # Раз в день
    # },
    # 'generate-sla-report': {
    #     'task': 'apps.workflow.tasks.generate_sla_report',
    #     'schedule': 86400.0,  # Раз в день в 01:00
    # },
    
    # Telegram уведомления
    'send-daily-summaries': {
        'task': 'apps.notifications.tasks.send_daily_summaries',
        'schedule': 28800.0,  # Каждые 8 часов (09:00, 17:00, 01:00)
    },
    'cleanup-old-notification-logs': {
        'task': 'apps.notifications.tasks.cleanup_old_notification_logs',
        'schedule': 86400.0,  # Раз в день
        'kwargs': {'days_to_keep': 30}
    },
    'retry-failed-notifications': {
        'task': 'apps.notifications.tasks.retry_failed_notifications',
        'schedule': 3600.0,  # Каждый час
    },
    # 'send-sla-violation-alerts': {
    #     'task': 'apps.notifications.tasks.send_sla_violation_alerts',
    #     'schedule': 600.0,  # Каждые 10 минут
    # },
    
    # Обработка сертификатов
    'cleanup-failed-certificate-processing': {
        'task': 'apps.certificates.tasks.cleanup_failed_processing',
        'schedule': 1800.0,  # Каждые 30 минут
    },
    'update-certificate-search-statistics': {
        'task': 'apps.certificates.tasks.update_search_statistics',
        'schedule': 3600.0,  # Каждый час
    },
    'optimize-certificate-search-index': {
        'task': 'apps.certificates.tasks.optimize_search_index',
        'schedule': 86400.0,  # Раз в день
    },
}

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} [{name}] {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '[{levelname}] {asctime} {message}',
            'style': '{',
        },
        'structured': {
            'format': '{levelname} | {asctime} | {name} | {process} | {thread} | {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'filters': ['require_debug_true'],
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'metalqms.log'),
            'maxBytes': 1024*1024*10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'metalqms_errors.log'),
            'maxBytes': 1024*1024*10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'api_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'api.log'),
            'maxBytes': 1024*1024*5,  # 5 MB
            'backupCount': 3,
            'formatter': 'structured',
        },
        'celery_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'celery.log'),
            'maxBytes': 1024*1024*5,  # 5 MB
            'backupCount': 3,
            'formatter': 'verbose',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'filters': ['require_debug_false'],
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['error_file', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['error_file', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console', 'file', 'api_file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'apps.api': {
            'handlers': ['api_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps.warehouse': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'apps.certificates': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'apps.notifications': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'celery': {
            'handlers': ['celery_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'celery.task': {
            'handlers': ['celery_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
}

# Создаем папку для логов если её нет
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

# =============================================================================
# CUSTOM MIDDLEWARE FOR REQUEST LOGGING
# =============================================================================

MIDDLEWARE.append('apps.common.middleware.RequestLoggingMiddleware')

# Добавляем middleware для логирования DB запросов только в DEBUG режиме
if DEBUG:
    MIDDLEWARE.append('apps.common.middleware.DatabaseQueryLoggingMiddleware')