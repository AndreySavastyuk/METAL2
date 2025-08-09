"""
MetalQMS Monitoring Configuration
Prometheus metrics and custom monitoring utilities
"""
import time
import uuid
from datetime import datetime
from typing import Dict, Any

import structlog
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.utils import timezone
from prometheus_client import Counter, Histogram, Gauge, Info
from prometheus_client.core import CollectorRegistry

User = get_user_model()

# Custom registry for metrics
registry = CollectorRegistry()

# ============================================================================
# Django Application Metrics
# ============================================================================

# Request metrics
http_requests_total = Counter(
    'django_http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status_code'],
    registry=registry
)

http_request_duration_seconds = Histogram(
    'django_http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, float('inf')],
    registry=registry
)

# User metrics
active_users_total = Gauge(
    'django_active_users_total',
    'Number of active users',
    registry=registry
)

authenticated_users_total = Gauge(
    'django_authenticated_users_total',
    'Number of authenticated users in current session',
    registry=registry
)

# Database metrics
database_queries_total = Counter(
    'django_database_queries_total',
    'Total number of database queries',
    ['db_alias', 'query_type'],
    registry=registry
)

database_query_duration_seconds = Histogram(
    'django_database_query_duration_seconds',
    'Database query duration in seconds',
    ['db_alias'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, float('inf')],
    registry=registry
)

# ============================================================================
# Business Metrics (MetalQMS specific)
# ============================================================================

# Material processing metrics
materials_processed_total = Counter(
    'metalqms_materials_processed_total',
    'Total number of materials processed',
    ['material_grade', 'supplier', 'status'],
    registry=registry
)

materials_pending_total = Gauge(
    'metalqms_materials_pending_total',
    'Number of materials currently pending processing',
    ['stage'],  # warehouse, qc, laboratory, production
    registry=registry
)

# Inspection metrics
inspections_total = Counter(
    'metalqms_inspections_total',
    'Total number of inspections performed',
    ['inspection_type', 'result', 'inspector'],
    registry=registry
)

inspection_duration_seconds = Histogram(
    'metalqms_inspection_duration_seconds',
    'Time taken to complete inspections',
    ['inspection_type'],
    buckets=[300, 600, 1800, 3600, 7200, 14400, 28800, float('inf')],  # 5min to 8h
    registry=registry
)

# Laboratory metrics
lab_tests_total = Counter(
    'metalqms_lab_tests_total',
    'Total number of laboratory tests',
    ['test_type', 'result'],
    registry=registry
)

lab_test_duration_seconds = Histogram(
    'metalqms_lab_test_duration_seconds',
    'Laboratory test processing time',
    ['test_type'],
    buckets=[3600, 7200, 14400, 28800, 86400, 172800, float('inf')],  # 1h to 2 days
    registry=registry
)

# Certificate processing metrics
certificates_processed_total = Counter(
    'metalqms_certificates_processed_total',
    'Total number of certificates processed',
    ['processing_status', 'file_type'],
    registry=registry
)

certificate_processing_duration_seconds = Histogram(
    'metalqms_certificate_processing_duration_seconds',
    'Certificate processing time',
    buckets=[1, 5, 10, 30, 60, 300, float('inf')],
    registry=registry
)

# Workflow metrics
workflow_transitions_total = Counter(
    'metalqms_workflow_transitions_total',
    'Total workflow state transitions',
    ['from_state', 'to_state', 'workflow_type'],
    registry=registry
)

workflow_completion_time_seconds = Histogram(
    'metalqms_workflow_completion_time_seconds',
    'Time to complete full workflow',
    ['workflow_type'],
    buckets=[3600, 7200, 14400, 28800, 86400, 172800, 604800, float('inf')],  # 1h to 1 week
    registry=registry
)

# System health metrics
system_health = Gauge(
    'metalqms_system_health',
    'System health status (1=healthy, 0=unhealthy)',
    ['component'],
    registry=registry
)

# Application info
app_info = Info(
    'metalqms_app_info',
    'Application information',
    registry=registry
)

# ============================================================================
# Monitoring Utilities
# ============================================================================

class MetricsCollector:
    """Utility class for collecting and updating metrics"""
    
    @staticmethod
    def update_active_users():
        """Update active users metrics"""
        try:
            # Count users with recent activity (last 30 minutes)
            thirty_minutes_ago = timezone.now() - timezone.timedelta(minutes=30)
            active_count = User.objects.filter(last_login__gte=thirty_minutes_ago).count()
            active_users_total.set(active_count)
        except Exception as e:
            structlog.get_logger().error("Failed to update active users metric", error=str(e))
    
    @staticmethod
    def update_pending_materials():
        """Update pending materials metrics by stage"""
        try:
            from apps.warehouse.models import Material, MaterialReceipt
            from apps.quality.models import QCInspection
            from apps.laboratory.models import LabTestRequest
            
            # Materials in warehouse (pending QC)
            warehouse_pending = MaterialReceipt.objects.filter(status='pending_qc').count()
            materials_pending_total.labels(stage='warehouse').set(warehouse_pending)
            
            # Materials in QC
            qc_pending = QCInspection.objects.filter(status__in=['draft', 'in_progress']).count()
            materials_pending_total.labels(stage='qc').set(qc_pending)
            
            # Materials in laboratory
            lab_pending = LabTestRequest.objects.filter(status__in=['pending', 'assigned', 'in_progress']).count()
            materials_pending_total.labels(stage='laboratory').set(lab_pending)
            
        except Exception as e:
            structlog.get_logger().error("Failed to update pending materials metrics", error=str(e))
    
    @staticmethod
    def update_system_health():
        """Update system health metrics"""
        try:
            # Check database connectivity
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                system_health.labels(component='database').set(1)
            except Exception:
                system_health.labels(component='database').set(0)
            
            # Check Redis connectivity
            try:
                from django.core.cache import cache
                cache.set('health_check', 'ok', timeout=30)
                if cache.get('health_check') == 'ok':
                    system_health.labels(component='redis').set(1)
                else:
                    system_health.labels(component='redis').set(0)
            except Exception:
                system_health.labels(component='redis').set(0)
            
            # Check Celery workers
            try:
                from celery import current_app
                inspect = current_app.control.inspect()
                stats = inspect.stats()
                if stats:
                    system_health.labels(component='celery').set(1)
                else:
                    system_health.labels(component='celery').set(0)
            except Exception:
                system_health.labels(component='celery').set(0)
                
        except Exception as e:
            structlog.get_logger().error("Failed to update system health metrics", error=str(e))

# ============================================================================
# Monitoring Middleware and Decorators
# ============================================================================

def track_material_processing(material_grade: str, supplier: str, status: str):
    """Track material processing event"""
    materials_processed_total.labels(
        material_grade=material_grade,
        supplier=supplier,
        status=status
    ).inc()

def track_inspection(inspection_type: str, result: str, inspector: str, duration: float = None):
    """Track inspection event"""
    inspections_total.labels(
        inspection_type=inspection_type,
        result=result,
        inspector=inspector
    ).inc()
    
    if duration is not None:
        inspection_duration_seconds.labels(inspection_type=inspection_type).observe(duration)

def track_lab_test(test_type: str, result: str, duration: float = None):
    """Track laboratory test event"""
    lab_tests_total.labels(test_type=test_type, result=result).inc()
    
    if duration is not None:
        lab_test_duration_seconds.labels(test_type=test_type).observe(duration)

def track_certificate_processing(processing_status: str, file_type: str, duration: float = None):
    """Track certificate processing event"""
    certificates_processed_total.labels(
        processing_status=processing_status,
        file_type=file_type
    ).inc()
    
    if duration is not None:
        certificate_processing_duration_seconds.observe(duration)

def track_workflow_transition(from_state: str, to_state: str, workflow_type: str):
    """Track workflow state transition"""
    workflow_transitions_total.labels(
        from_state=from_state,
        to_state=to_state,
        workflow_type=workflow_type
    ).inc()

# Initialize application info
app_info.info({
    'version': getattr(settings, 'VERSION', '1.0.0'),
    'environment': getattr(settings, 'ENVIRONMENT', 'development'),
    'debug': str(settings.DEBUG)
})

# ============================================================================
# Structured Logging Setup
# ============================================================================

def add_correlation_id(logger, method_name, event_dict):
    """Add correlation ID to all log events"""
    if 'correlation_id' not in event_dict:
        event_dict['correlation_id'] = str(uuid.uuid4())
    return event_dict

def add_timestamp(logger, method_name, event_dict):
    """Add timestamp to all log events"""
    event_dict['timestamp'] = datetime.utcnow().isoformat()
    return event_dict

def add_service_info(logger, method_name, event_dict):
    """Add service information to all log events"""
    event_dict['service'] = 'metalqms'
    event_dict['component'] = event_dict.get('component', 'backend')
    return event_dict

# Configure structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        add_correlation_id,
        add_timestamp,
        add_service_info,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# Get structured logger
logger = structlog.get_logger(__name__)