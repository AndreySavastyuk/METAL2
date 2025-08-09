"""
Test settings for MetalQMS Django backend
"""
from config.settings import *
import tempfile
import os

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Disable migrations for faster tests
class DisableMigrations:
    def __contains__(self, item):
        return True
        
    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Media files - use temporary directory
MEDIA_ROOT = tempfile.mkdtemp()

# Static files - use temporary directory
STATIC_ROOT = tempfile.mkdtemp()

# Disable logging during tests
LOGGING_CONFIG = None
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'CRITICAL',
    },
}

# Test-specific settings
DEBUG = False
TEMPLATE_DEBUG = False

# Password hashers - use fast hasher for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Cache - use dummy cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

# Email - use console backend for tests
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Celery - run tasks synchronously in tests
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_BROKER_URL = 'memory://'
CELERY_RESULT_BACKEND = 'cache+memory://'

# Telegram - test token
TELEGRAM_BOT_TOKEN = 'test_token_123456789'

# File upload settings for tests
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# Disable CSRF for API tests
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

# Test-specific apps
INSTALLED_APPS += [
    'tests',
]

# DRF test settings
REST_FRAMEWORK.update({
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
})

# Disable file system watchers
USE_I18N = False
USE_L10N = False

# Test runner
TEST_RUNNER = 'django.test.runner.DiscoverRunner'

# Factory Boy settings
FACTORY_FOR_DJANGO_MODELS = True

# Pytest settings
PYTEST_TIMEOUT = 300  # 5 minutes timeout for tests

# Coverage settings
COVERAGE_MODULE_EXCLUDES = [
    'tests.*',
    'config.*',
    'migrations.*',
    'venv.*',
    '.*__pycache__.*',
    'manage.py',
    'setup.py',
]

# Mock external services
MOCK_EXTERNAL_SERVICES = True

# QR Code settings for tests
QR_CODE_CACHE_TIMEOUT = 0  # Disable caching in tests

# Workflow settings for tests
WORKFLOW_AUTO_START = False  # Disable auto workflow start in tests

# Notification settings for tests
NOTIFICATION_RETRY_DELAY = 0  # No delay in tests
NOTIFICATION_MAX_RETRIES = 1  # Minimal retries in tests