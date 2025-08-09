"""
Monitoring Middleware для MetalQMS
Prometheus metrics collection and structured logging
"""

import time
import uuid
from django.utils.deprecation import MiddlewareMixin
from django.urls import resolve, Resolver404
from django.contrib.auth import get_user_model
from django.db import connection
import structlog

from .monitoring import (
    http_requests_total,
    http_request_duration_seconds,
    authenticated_users_total,
    database_queries_total,
    database_query_duration_seconds
)

logger = structlog.get_logger(__name__)
User = get_user_model()


class PrometheusMonitoringMiddleware(MiddlewareMixin):
    """
    Middleware для сбора метрик Prometheus
    """
    
    def process_request(self, request):
        # Add correlation ID to request
        if not hasattr(request, 'correlation_id'):
            request.correlation_id = str(uuid.uuid4())
        
        # Track request start time
        request._prometheus_start_time = time.time()
        
        # Track database queries count before request
        request._db_queries_before = len(connection.queries)
        
        # Log incoming request
        logger.info(
            "incoming_request",
            method=request.method,
            path=request.path,
            remote_addr=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            correlation_id=request.correlation_id,
            component="middleware"
        )
        
        return None
    
    def process_response(self, request, response):
        # Skip monitoring for static files and monitoring endpoints
        if (request.path.startswith('/static/') or 
            request.path.startswith('/media/') or
            request.path.startswith('/metrics') or
            request.path.startswith('/health')):
            return response
        
        # Get endpoint name
        try:
            resolved = resolve(request.path)
            endpoint = f"{resolved.namespace}:{resolved.url_name}" if resolved.namespace else resolved.url_name
            if not endpoint:
                endpoint = resolved.view_name or "unknown"
        except Resolver404:
            endpoint = "unknown"
        
        # Calculate request duration
        duration = 0
        if hasattr(request, '_prometheus_start_time'):
            duration = time.time() - request._prometheus_start_time
            http_request_duration_seconds.labels(
                method=request.method,
                endpoint=endpoint
            ).observe(duration)
        
        # Track request count
        http_requests_total.labels(
            method=request.method,
            endpoint=endpoint,
            status_code=response.status_code
        ).inc()
        
        # Track database queries
        if hasattr(request, '_db_queries_before'):
            queries_count = len(connection.queries) - request._db_queries_before
            
            if queries_count > 0:
                # Track recent queries
                recent_queries = connection.queries[-queries_count:]
                for query in recent_queries:
                    query_type = query['sql'].split()[0].upper() if query['sql'] else 'UNKNOWN'
                    db_alias = 'default'
                    
                    database_queries_total.labels(
                        db_alias=db_alias,
                        query_type=query_type
                    ).inc()
                    
                    # Track query duration if available
                    if 'time' in query and query['time']:
                        try:
                            query_duration = float(query['time'])
                            database_query_duration_seconds.labels(db_alias=db_alias).observe(query_duration)
                        except (ValueError, TypeError):
                            pass
        
        # Log response
        logger.info(
            "outgoing_response",
            method=request.method,
            path=request.path,
            status_code=response.status_code,
            duration=duration,
            db_queries=len(connection.queries) - getattr(request, '_db_queries_before', 0),
            correlation_id=getattr(request, 'correlation_id', 'unknown'),
            component="middleware"
        )
        
        # Update authenticated users count (sample every 10th request to reduce DB load)
        if hash(request.path) % 10 == 0:
            try:
                from django.utils import timezone
                from datetime import timedelta
                
                # Count users active in last 30 minutes
                thirty_minutes_ago = timezone.now() - timedelta(minutes=30)
                auth_count = User.objects.filter(
                    is_active=True, 
                    last_login__gte=thirty_minutes_ago
                ).count()
                authenticated_users_total.set(auth_count)
            except Exception as e:
                logger.error("Failed to update authenticated users metric", error=str(e))
        
        return response


class CorrelationIdMiddleware(MiddlewareMixin):
    """
    Middleware для добавления correlation ID к каждому запросу
    """
    
    def process_request(self, request):
        # Get correlation ID from header or generate new one
        correlation_id = (
            request.META.get('HTTP_X_CORRELATION_ID') or 
            request.META.get('HTTP_X_REQUEST_ID') or 
            str(uuid.uuid4())
        )
        request.correlation_id = correlation_id
        
        # Add to structlog context
        try:
            structlog.contextvars.clear_contextvars()
            structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
        except AttributeError:
            # Fallback for older versions of structlog
            pass
        
        return None
    
    def process_response(self, request, response):
        # Add correlation ID to response headers
        if hasattr(request, 'correlation_id'):
            response['X-Correlation-ID'] = request.correlation_id
            response['X-Request-ID'] = request.correlation_id
        
        return response


class BusinessMetricsMiddleware(MiddlewareMixin):
    """
    Middleware для сбора бизнес-метрик MetalQMS
    """
    
    def process_response(self, request, response):
        # Track API usage by endpoint
        if request.path.startswith('/api/'):
            try:
                resolved = resolve(request.path)
                
                # Track material-related operations
                if 'material' in resolved.url_name:
                    logger.info(
                        "material_api_usage",
                        endpoint=resolved.url_name,
                        method=request.method,
                        status_code=response.status_code,
                        correlation_id=getattr(request, 'correlation_id', 'unknown'),
                        component="business_metrics"
                    )
                
                # Track QC operations
                elif 'qc' in resolved.url_name or 'inspection' in resolved.url_name:
                    logger.info(
                        "qc_api_usage",
                        endpoint=resolved.url_name,
                        method=request.method,
                        status_code=response.status_code,
                        correlation_id=getattr(request, 'correlation_id', 'unknown'),
                        component="business_metrics"
                    )
                
                # Track laboratory operations
                elif 'lab' in resolved.url_name or 'test' in resolved.url_name:
                    logger.info(
                        "laboratory_api_usage",
                        endpoint=resolved.url_name,
                        method=request.method,
                        status_code=response.status_code,
                        correlation_id=getattr(request, 'correlation_id', 'unknown'),
                        component="business_metrics"
                    )
                    
            except Resolver404:
                pass
        
        return response


class ErrorTrackingMiddleware(MiddlewareMixin):
    """
    Middleware для отслеживания ошибок
    """
    
    def process_exception(self, request, exception):
        logger.error(
            "request_exception",
            method=request.method,
            path=request.path,
            exception_type=type(exception).__name__,
            exception_message=str(exception),
            correlation_id=getattr(request, 'correlation_id', 'unknown'),
            component="error_tracking",
            exc_info=True
        )
        
        return None
    
    def process_response(self, request, response):
        # Log 4xx and 5xx responses
        if response.status_code >= 400:
            logger.warning(
                "error_response",
                method=request.method,
                path=request.path,
                status_code=response.status_code,
                correlation_id=getattr(request, 'correlation_id', 'unknown'),
                component="error_tracking"
            )
        
        return response