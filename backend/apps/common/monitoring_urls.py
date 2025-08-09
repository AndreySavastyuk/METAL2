"""
Monitoring URLs for MetalQMS
Health check and monitoring endpoints
"""

from django.urls import path
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.db import connection
from django.core.cache import cache
from django.utils import timezone
import structlog
import time
import os
import psutil

from .monitoring import MetricsCollector, system_health

logger = structlog.get_logger(__name__)

@never_cache
@require_http_methods(["GET"])
def health_check(request):
    """
    Basic health check endpoint
    Returns 200 if service is healthy
    """
    return JsonResponse({
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'service': 'metalqms-backend',
        'version': getattr(request, 'META', {}).get('HTTP_USER_AGENT', '1.0.0')
    })

@never_cache
@require_http_methods(["GET"])
def health_detailed(request):
    """
    Detailed health check with component status
    """
    start_time = time.time()
    health_status = {
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'service': 'metalqms-backend',
        'checks': {}
    }
    
    overall_healthy = True
    
    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            if result and result[0] == 1:
                health_status['checks']['database'] = {
                    'status': 'healthy',
                    'response_time_ms': None
                }
            else:
                raise Exception("Invalid database response")
    except Exception as e:
        health_status['checks']['database'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        overall_healthy = False
    
    # Redis check
    try:
        cache_start = time.time()
        cache.set('health_check_key', 'test_value', timeout=30)
        cached_value = cache.get('health_check_key')
        cache_time = (time.time() - cache_start) * 1000
        
        if cached_value == 'test_value':
            health_status['checks']['redis'] = {
                'status': 'healthy',
                'response_time_ms': round(cache_time, 2)
            }
        else:
            raise Exception("Cache value mismatch")
    except Exception as e:
        health_status['checks']['redis'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        overall_healthy = False
    
    # Celery check
    try:
        from celery import current_app
        inspect = current_app.control.inspect()
        stats = inspect.stats()
        
        if stats:
            active_workers = len(stats)
            health_status['checks']['celery'] = {
                'status': 'healthy',
                'active_workers': active_workers,
                'workers': list(stats.keys())
            }
        else:
            health_status['checks']['celery'] = {
                'status': 'unhealthy',
                'error': 'No active workers found'
            }
            overall_healthy = False
    except Exception as e:
        health_status['checks']['celery'] = {
            'status': 'degraded',
            'error': str(e)
        }
        # Don't mark as unhealthy for Celery issues in some deployments
    
    # Disk space check
    try:
        disk_usage = psutil.disk_usage('/')
        disk_percent = (disk_usage.used / disk_usage.total) * 100
        
        if disk_percent < 90:
            health_status['checks']['disk_space'] = {
                'status': 'healthy',
                'usage_percent': round(disk_percent, 2),
                'free_gb': round(disk_usage.free / (1024**3), 2)
            }
        elif disk_percent < 95:
            health_status['checks']['disk_space'] = {
                'status': 'warning',
                'usage_percent': round(disk_percent, 2),
                'free_gb': round(disk_usage.free / (1024**3), 2)
            }
        else:
            health_status['checks']['disk_space'] = {
                'status': 'critical',
                'usage_percent': round(disk_percent, 2),
                'free_gb': round(disk_usage.free / (1024**3), 2)
            }
            overall_healthy = False
    except Exception as e:
        health_status['checks']['disk_space'] = {
            'status': 'unknown',
            'error': str(e)
        }
    
    # Memory check
    try:
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        if memory_percent < 80:
            health_status['checks']['memory'] = {
                'status': 'healthy',
                'usage_percent': memory_percent,
                'available_gb': round(memory.available / (1024**3), 2)
            }
        elif memory_percent < 90:
            health_status['checks']['memory'] = {
                'status': 'warning',
                'usage_percent': memory_percent,
                'available_gb': round(memory.available / (1024**3), 2)
            }
        else:
            health_status['checks']['memory'] = {
                'status': 'critical',
                'usage_percent': memory_percent,
                'available_gb': round(memory.available / (1024**3), 2)
            }
            overall_healthy = False
    except Exception as e:
        health_status['checks']['memory'] = {
            'status': 'unknown',
            'error': str(e)
        }
    
    # Overall status
    if not overall_healthy:
        health_status['status'] = 'unhealthy'
    elif any(check.get('status') == 'warning' for check in health_status['checks'].values()):
        health_status['status'] = 'degraded'
    
    # Response time
    health_status['response_time_ms'] = round((time.time() - start_time) * 1000, 2)
    
    # Log health check
    logger.info(
        "health_check_performed",
        status=health_status['status'],
        response_time_ms=health_status['response_time_ms'],
        component="health_check"
    )
    
    # Return appropriate status code
    if health_status['status'] == 'healthy':
        status_code = 200
    elif health_status['status'] == 'degraded':
        status_code = 200  # Still functional
    else:
        status_code = 503  # Service unavailable
    
    return JsonResponse(health_status, status=status_code)

@never_cache
@require_http_methods(["GET"])
def readiness_check(request):
    """
    Readiness check - is the service ready to accept requests?
    """
    try:
        # Check database connectivity
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        # Check critical dependencies
        cache.set('readiness_check', 'ok', timeout=30)
        
        return JsonResponse({
            'status': 'ready',
            'timestamp': timezone.now().isoformat()
        })
    except Exception as e:
        logger.error(
            "readiness_check_failed",
            error=str(e),
            component="health_check"
        )
        return JsonResponse({
            'status': 'not_ready',
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }, status=503)

@never_cache
@require_http_methods(["GET"])
def liveness_check(request):
    """
    Liveness check - is the service alive?
    """
    return JsonResponse({
        'status': 'alive',
        'timestamp': timezone.now().isoformat(),
        'uptime_seconds': time.time() - getattr(liveness_check, '_start_time', time.time())
    })

# Set start time for uptime calculation
liveness_check._start_time = time.time()

@never_cache
@require_http_methods(["GET"])
def metrics_summary(request):
    """
    Summary of key business metrics
    """
    try:
        from apps.warehouse.models import Material, MaterialReceipt
        from apps.quality.models import QCInspection
        from apps.laboratory.models import LabTestRequest
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        # Collect current metrics
        metrics = {
            'timestamp': timezone.now().isoformat(),
            'materials': {
                'total': Material.objects.count(),
                'pending_qc': MaterialReceipt.objects.filter(status='pending_qc').count(),
                'in_qc': QCInspection.objects.filter(status__in=['draft', 'in_progress']).count(),
                'in_lab': LabTestRequest.objects.filter(status__in=['pending', 'assigned', 'in_progress']).count(),
            },
            'users': {
                'total': User.objects.count(),
                'active': User.objects.filter(is_active=True).count(),
            },
            'system': {
                'python_version': f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
                'django_version': None,  # Would need to import django
            }
        }
        
        # Update Prometheus metrics
        MetricsCollector.update_pending_materials()
        MetricsCollector.update_active_users()
        MetricsCollector.update_system_health()
        
        return JsonResponse(metrics)
        
    except Exception as e:
        logger.error(
            "metrics_summary_failed",
            error=str(e),
            component="metrics"
        )
        return JsonResponse({
            'error': 'Failed to collect metrics',
            'timestamp': timezone.now().isoformat()
        }, status=500)

# URL patterns
urlpatterns = [
    path('', health_check, name='health_check'),
    path('detailed/', health_detailed, name='health_detailed'),
    path('ready/', readiness_check, name='readiness_check'),
    path('live/', liveness_check, name='liveness_check'),
    path('metrics-summary/', metrics_summary, name='metrics_summary'),
]