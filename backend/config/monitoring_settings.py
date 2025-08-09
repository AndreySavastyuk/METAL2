"""
Monitoring Settings for MetalQMS
Prometheus, logging, and observability configuration
"""

import os
from pathlib import Path

# ============================================================================
# Django Prometheus Configuration
# ============================================================================

# Add django-prometheus to installed apps
PROMETHEUS_APPS = [
    'django_prometheus',
]

# Prometheus middleware (should be first and last)
PROMETHEUS_MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    # ... other middleware ...
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

# Additional monitoring middleware
MONITORING_MIDDLEWARE = [
    'apps.common.monitoring_middleware.CorrelationIdMiddleware',
    'apps.common.monitoring_middleware.PrometheusMonitoringMiddleware', 
    'apps.common.monitoring_middleware.BusinessMetricsMiddleware',
    'apps.common.monitoring_middleware.ErrorTrackingMiddleware',
]

# Prometheus metrics configuration
PROMETHEUS_EXPORT_MIGRATIONS = True

# Metrics endpoint configuration
PROMETHEUS_METRICS_EXPORT_PORT = 8001
PROMETHEUS_METRICS_EXPORT_ADDRESS = '0.0.0.0'

# ============================================================================
# Structured Logging Configuration
# ============================================================================

# Base log directory
LOG_DIR = Path(os.getenv('LOG_DIR', 'logs'))
LOG_DIR.mkdir(exist_ok=True)

# Log formatters
LOGGING_FORMATTERS = {
    'json': {
        'format': '%(message)s',
        'class': 'pythonjsonlogger.jsonlogger.JsonFormatter',
    },
    'structured': {
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'datefmt': '%Y-%m-%d %H:%M:%S',
    },
    'colored': {
        '()': 'colorlog.ColoredFormatter',
        'format': '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s%(reset)s',
        'datefmt': '%Y-%m-%d %H:%M:%S',
        'log_colors': {
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        },
    },
}

# Log handlers
LOGGING_HANDLERS = {
    'console': {
        'class': 'logging.StreamHandler',
        'formatter': 'colored' if os.getenv('DEBUG', 'False').lower() == 'true' else 'json',
        'level': 'INFO',
    },
    'file_json': {
        'class': 'logging.handlers.RotatingFileHandler',
        'filename': LOG_DIR / 'app.json.log',
        'formatter': 'json',
        'maxBytes': 50 * 1024 * 1024,  # 50MB
        'backupCount': 10,
        'level': 'INFO',
    },
    'file_structured': {
        'class': 'logging.handlers.RotatingFileHandler',
        'filename': LOG_DIR / 'app.log',
        'formatter': 'structured',
        'maxBytes': 50 * 1024 * 1024,  # 50MB
        'backupCount': 10,
        'level': 'INFO',
    },
    'error_file': {
        'class': 'logging.handlers.RotatingFileHandler',
        'filename': LOG_DIR / 'error.log',
        'formatter': 'json',
        'maxBytes': 50 * 1024 * 1024,  # 50MB
        'backupCount': 10,
        'level': 'ERROR',
    },
    'business_metrics': {
        'class': 'logging.handlers.RotatingFileHandler',
        'filename': LOG_DIR / 'business_metrics.json.log',
        'formatter': 'json',
        'maxBytes': 100 * 1024 * 1024,  # 100MB
        'backupCount': 20,
        'level': 'INFO',
    },
    'audit': {
        'class': 'logging.handlers.RotatingFileHandler',
        'filename': LOG_DIR / 'audit.json.log',
        'formatter': 'json',
        'maxBytes': 100 * 1024 * 1024,  # 100MB
        'backupCount': 30,  # Keep 30 days
        'level': 'INFO',
    },
}

# Logger configuration
LOGGING_LOGGERS = {
    '': {  # Root logger
        'handlers': ['console', 'file_json'],
        'level': 'INFO',
        'propagate': False,
    },
    'django': {
        'handlers': ['console', 'file_structured'],
        'level': 'INFO',
        'propagate': False,
    },
    'django.db.backends': {
        'handlers': ['file_structured'],
        'level': 'WARNING',  # Only log slow queries and errors
        'propagate': False,
    },
    'apps': {
        'handlers': ['console', 'file_json'],
        'level': 'INFO',
        'propagate': False,
    },
    'apps.warehouse': {
        'handlers': ['console', 'file_json', 'business_metrics'],
        'level': 'INFO',
        'propagate': False,
    },
    'apps.quality': {
        'handlers': ['console', 'file_json', 'business_metrics'],
        'level': 'INFO',
        'propagate': False,
    },
    'apps.laboratory': {
        'handlers': ['console', 'file_json', 'business_metrics'],
        'level': 'INFO',
        'propagate': False,
    },
    'apps.workflow': {
        'handlers': ['console', 'file_json', 'business_metrics'],
        'level': 'INFO',
        'propagate': False,
    },
    'apps.certificates': {
        'handlers': ['console', 'file_json'],
        'level': 'INFO',
        'propagate': False,
    },
    'apps.notifications': {
        'handlers': ['console', 'file_json'],
        'level': 'INFO',
        'propagate': False,
    },
    'business_metrics': {
        'handlers': ['business_metrics'],
        'level': 'INFO',
        'propagate': False,
    },
    'audit': {
        'handlers': ['audit'],
        'level': 'INFO',
        'propagate': False,
    },
    'security': {
        'handlers': ['console', 'error_file', 'audit'],
        'level': 'WARNING',
        'propagate': False,
    },
    'celery': {
        'handlers': ['console', 'file_json'],
        'level': 'INFO',
        'propagate': False,
    },
    'celery.task': {
        'handlers': ['file_json', 'business_metrics'],
        'level': 'INFO',
        'propagate': False,
    },
}

# Complete logging configuration
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': LOGGING_FORMATTERS,
    'handlers': LOGGING_HANDLERS,
    'loggers': LOGGING_LOGGERS,
}

# ============================================================================
# Monitoring URLs Configuration
# ============================================================================

MONITORING_URLS = [
    # Prometheus metrics endpoint
    ('metrics/', 'django_prometheus.urls'),
    
    # Health check endpoints
    ('health/', 'apps.common.monitoring_urls'),
]

# ============================================================================
# Performance Monitoring
# ============================================================================

# Database query logging thresholds
DB_QUERY_COUNT_WARNING = 10
DB_QUERY_TIME_WARNING = 0.1  # 100ms

# Request timing thresholds
REQUEST_TIME_WARNING = 5.0  # 5 seconds
REQUEST_TIME_ERROR = 10.0   # 10 seconds

# Memory usage monitoring
MEMORY_WARNING_THRESHOLD = 500 * 1024 * 1024  # 500MB
MEMORY_ERROR_THRESHOLD = 1024 * 1024 * 1024    # 1GB

# ============================================================================
# Metrics Collection Configuration
# ============================================================================

# Business metrics collection intervals
METRICS_COLLECTION_INTERVALS = {
    'active_users': 300,        # 5 minutes
    'pending_materials': 60,    # 1 minute
    'system_health': 30,        # 30 seconds
}

# Metrics retention
METRICS_RETENTION_DAYS = 30

# ============================================================================
# Alert Configuration
# ============================================================================

ALERT_RULES = {
    'high_error_rate': {
        'threshold': 0.05,  # 5% error rate
        'time_window': 300,  # 5 minutes
        'severity': 'warning',
    },
    'high_response_time': {
        'threshold': 2.0,  # 2 seconds
        'time_window': 300,  # 5 minutes
        'severity': 'warning',
    },
    'database_connection_errors': {
        'threshold': 1,  # Any database error
        'time_window': 60,  # 1 minute
        'severity': 'critical',
    },
    'celery_queue_backlog': {
        'threshold': 100,  # 100 pending tasks
        'time_window': 600,  # 10 minutes
        'severity': 'warning',
    },
    'disk_space_low': {
        'threshold': 0.9,  # 90% full
        'time_window': 300,  # 5 minutes
        'severity': 'critical',
    },
    'memory_usage_high': {
        'threshold': 0.8,  # 80% memory usage
        'time_window': 300,  # 5 minutes
        'severity': 'warning',
    },
}

# ============================================================================
# Environment-specific overrides
# ============================================================================

ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

if ENVIRONMENT == 'production':
    # Production-specific logging
    LOGGING_LOGGERS['']['level'] = 'WARNING'
    LOGGING_LOGGERS['django']['level'] = 'WARNING'
    
    # Disable debug logging
    LOGGING_HANDLERS['console']['level'] = 'WARNING'
    
elif ENVIRONMENT == 'development':
    # Development-specific logging
    LOGGING_LOGGERS['']['level'] = 'DEBUG'
    LOGGING_LOGGERS['django.db.backends']['level'] = 'DEBUG'
    
    # Add SQL logging in development
    LOGGING_HANDLERS['sql_debug'] = {
        'class': 'logging.StreamHandler',
        'formatter': 'colored',
        'level': 'DEBUG',
    }
    LOGGING_LOGGERS['django.db.backends']['handlers'].append('sql_debug')

# ============================================================================
# Export configuration
# ============================================================================

def get_monitoring_settings():
    """Get all monitoring-related settings"""
    return {
        'PROMETHEUS_APPS': PROMETHEUS_APPS,
        'PROMETHEUS_MIDDLEWARE': PROMETHEUS_MIDDLEWARE,
        'MONITORING_MIDDLEWARE': MONITORING_MIDDLEWARE,
        'LOGGING': LOGGING_CONFIG,
        'MONITORING_URLS': MONITORING_URLS,
        'ALERT_RULES': ALERT_RULES,
        'METRICS_COLLECTION_INTERVALS': METRICS_COLLECTION_INTERVALS,
    }