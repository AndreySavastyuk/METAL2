"""
API views для тестирования интеграции frontend-backend
"""
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.conf import settings
import json

logger = logging.getLogger('apps.api')


@csrf_exempt
@require_http_methods(["GET"])
def health_check(request):
    """
    Проверка здоровья API
    """
    logger.info("Health check requested")
    
    response_data = {
        'status': 'ok',
        'timestamp': timezone.now().isoformat(),
        'message': 'MetalQMS Backend API is running',
        'version': '1.0.0',
        'environment': 'development' if settings.DEBUG else 'production',
        'services': {
            'database': 'connected',
            'redis': 'connected',  # TODO: реальная проверка
            'celery': 'running',   # TODO: реальная проверка
        }
    }
    
    return JsonResponse(response_data)


@csrf_exempt
@require_http_methods(["GET"])
def system_info(request):
    """
    Информация о системе
    """
    logger.info("System info requested")
    
    response_data = {
        'app_name': 'MetalQMS',
        'description': 'Система управления качеством металлургического производства',
        'version': '1.0.0',
        'api_version': 'v1',
        'debug_mode': settings.DEBUG,
        'timezone': str(settings.TIME_ZONE),
        'allowed_hosts': settings.ALLOWED_HOSTS,
        'cors_enabled': True,
        'features': [
            'Warehouse Management',
            'Quality Control',
            'Laboratory Testing',
            'Certificate Processing',
            'Telegram Notifications',
            'Workflow Management',
            'PDF Processing',
            'QR Code Generation'
        ],
        'endpoints': {
            'health': '/api/health/',
            'system': '/api/system/',
            'warehouse': '/api/warehouse/',
            'qc': '/api/qc/',
            'laboratory': '/api/laboratory/',
            'notifications': '/api/notifications/',
            'certificates': '/api/certificates/',
        }
    }
    
    return JsonResponse(response_data)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def test_endpoint(request):
    """
    Тестовый endpoint для проверки интеграции
    """
    logger.info(f"Test endpoint accessed: {request.method}")
    
    if request.method == 'GET':
        response_data = {
            'method': 'GET',
            'message': 'Test endpoint is working',
            'timestamp': timezone.now().isoformat(),
            'query_params': dict(request.GET),
            'headers': {
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'content_type': request.content_type,
                'origin': request.META.get('HTTP_ORIGIN', ''),
                'referer': request.META.get('HTTP_REFERER', ''),
            }
        }
    
    elif request.method == 'POST':
        try:
            if request.content_type == 'application/json':
                body_data = json.loads(request.body.decode('utf-8'))
            else:
                body_data = dict(request.POST)
        except (json.JSONDecodeError, UnicodeDecodeError):
            body_data = None
        
        response_data = {
            'method': 'POST',
            'message': 'POST request received successfully',
            'timestamp': timezone.now().isoformat(),
            'received_data': body_data,
            'content_type': request.content_type,
            'content_length': len(request.body) if request.body else 0,
        }
    
    return JsonResponse(response_data)


@csrf_exempt
@require_http_methods(["OPTIONS"])
def options_handler(request):
    """
    Обработка CORS preflight запросов
    """
    logger.debug("CORS preflight request")
    
    response = JsonResponse({'message': 'CORS preflight'})
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
    response['Access-Control-Max-Age'] = '86400'
    
    return response