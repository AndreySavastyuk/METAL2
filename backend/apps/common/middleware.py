"""
Middleware для логирования запросов в MetalQMS
"""
import time
import json
import logging
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpRequest, HttpResponse
from django.utils import timezone
from typing import Optional, Dict, Any

logger = logging.getLogger('apps.api')


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware для логирования всех HTTP запросов
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """
        Обработка входящего запроса
        """
        request._start_time = time.time()
        request._request_id = self._generate_request_id()
        
        # Логируем входящий запрос
        self._log_request(request)
        
        return None
    
    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """
        Обработка исходящего ответа
        """
        if hasattr(request, '_start_time'):
            duration = time.time() - request._start_time
            self._log_response(request, response, duration)
        
        return response
    
    def process_exception(self, request: HttpRequest, exception: Exception) -> Optional[HttpResponse]:
        """
        Обработка исключений
        """
        if hasattr(request, '_start_time'):
            duration = time.time() - request._start_time
            self._log_exception(request, exception, duration)
        
        return None
    
    def _generate_request_id(self) -> str:
        """
        Генерация уникального ID для запроса
        """
        import uuid
        return str(uuid.uuid4())[:8]
    
    def _get_client_ip(self, request: HttpRequest) -> str:
        """
        Получение IP адреса клиента
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip or 'unknown'
    
    def _get_user_info(self, request: HttpRequest) -> Dict[str, Any]:
        """
        Получение информации о пользователе
        """
        if hasattr(request, 'user') and request.user.is_authenticated:
            return {
                'user_id': request.user.id,
                'username': request.user.username,
                'is_staff': request.user.is_staff,
                'is_superuser': request.user.is_superuser
            }
        return {'user_id': None, 'username': 'anonymous'}
    
    def _should_log_request(self, request: HttpRequest) -> bool:
        """
        Определяет, нужно ли логировать запрос
        """
        # Не логируем запросы к статическим файлам и админке Django
        skip_paths = [
            '/static/',
            '/media/',
            '/favicon.ico',
            '/admin/jsi18n/',
            '/__debug__/',
        ]
        
        path = request.path_info
        return not any(path.startswith(skip_path) for skip_path in skip_paths)
    
    def _get_request_body(self, request: HttpRequest) -> Optional[str]:
        """
        Получение тела запроса (с ограничениями)
        """
        try:
            content_type = request.content_type
            
            # Логируем только JSON и form data
            if content_type in ['application/json', 'application/x-www-form-urlencoded']:
                body = request.body.decode('utf-8')
                
                # Ограничиваем размер логируемого тела
                if len(body) > 1000:
                    return body[:1000] + '... (truncated)'
                
                # Скрываем чувствительные данные
                if content_type == 'application/json':
                    try:
                        data = json.loads(body)
                        self._mask_sensitive_data(data)
                        return json.dumps(data)
                    except (json.JSONDecodeError, TypeError):
                        pass
                
                return body
            
            elif 'multipart/form-data' in content_type:
                return f'<multipart data, size: {len(request.body)} bytes>'
            
        except Exception as e:
            logger.warning(f"Failed to get request body: {e}")
            
        return None
    
    def _mask_sensitive_data(self, data: Dict[str, Any]) -> None:
        """
        Маскирование чувствительных данных
        """
        sensitive_fields = [
            'password', 'token', 'secret', 'key', 'authorization',
            'csrf_token', 'csrfmiddlewaretoken'
        ]
        
        if isinstance(data, dict):
            for key, value in data.items():
                if any(field in key.lower() for field in sensitive_fields):
                    data[key] = '***MASKED***'
                elif isinstance(value, dict):
                    self._mask_sensitive_data(value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            self._mask_sensitive_data(item)
    
    def _log_request(self, request: HttpRequest) -> None:
        """
        Логирование входящего запроса
        """
        if not self._should_log_request(request):
            return
        
        request_data = {
            'request_id': getattr(request, '_request_id', 'unknown'),
            'timestamp': timezone.now().isoformat(),
            'method': request.method,
            'path': request.path_info,
            'query_params': dict(request.GET),
            'client_ip': self._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'referer': request.META.get('HTTP_REFERER', ''),
            'content_type': request.content_type,
            'content_length': request.META.get('CONTENT_LENGTH', 0),
            'user': self._get_user_info(request),
        }
        
        # Добавляем тело запроса для POST/PUT/PATCH
        if request.method in ['POST', 'PUT', 'PATCH']:
            request_data['body'] = self._get_request_body(request)
        
        logger.info(
            f"Request {request.method} {request.path_info}",
            extra={'request_data': request_data}
        )
    
    def _log_response(self, request: HttpRequest, response: HttpResponse, duration: float) -> None:
        """
        Логирование ответа
        """
        if not self._should_log_request(request):
            return
        
        response_data = {
            'request_id': getattr(request, '_request_id', 'unknown'),
            'timestamp': timezone.now().isoformat(),
            'status_code': response.status_code,
            'content_type': response.get('Content-Type', ''),
            'content_length': len(response.content) if hasattr(response, 'content') else 0,
            'duration_ms': round(duration * 1000, 2),
        }
        
        # Определяем уровень логирования по статус коду
        if response.status_code >= 500:
            log_level = 'error'
        elif response.status_code >= 400:
            log_level = 'warning'
        elif duration > 5.0:  # Медленные запросы
            log_level = 'warning'
        else:
            log_level = 'info'
        
        message = f"Response {response.status_code} for {request.method} {request.path_info} in {duration:.2f}s"
        
        getattr(logger, log_level)(
            message,
            extra={'response_data': response_data}
        )
    
    def _log_exception(self, request: HttpRequest, exception: Exception, duration: float) -> None:
        """
        Логирование исключений
        """
        exception_data = {
            'request_id': getattr(request, '_request_id', 'unknown'),
            'timestamp': timezone.now().isoformat(),
            'exception_type': type(exception).__name__,
            'exception_message': str(exception),
            'duration_ms': round(duration * 1000, 2),
            'method': request.method,
            'path': request.path_info,
            'user': self._get_user_info(request),
        }
        
        logger.error(
            f"Exception in {request.method} {request.path_info}: {exception}",
            extra={'exception_data': exception_data},
            exc_info=True
        )


class DatabaseQueryLoggingMiddleware(MiddlewareMixin):
    """
    Middleware для логирования SQL запросов (только в DEBUG режиме)
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)
    
    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """
        Сброс счетчика запросов
        """
        from django.db import reset_queries
        reset_queries()
        return None
    
    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """
        Логирование количества SQL запросов
        """
        from django.conf import settings
        from django.db import connection
        
        if settings.DEBUG and self._should_log_queries(request):
            queries_count = len(connection.queries)
            
            if queries_count > 0:
                total_time = sum(float(query['time']) for query in connection.queries)
                
                # Предупреждение при большом количестве запросов
                if queries_count > 10:
                    logger.warning(
                        f"High number of DB queries: {queries_count} queries in {total_time:.2f}s for {request.method} {request.path_info}",
                        extra={
                            'db_queries': {
                                'count': queries_count,
                                'total_time': total_time,
                                'queries': [
                                    {
                                        'sql': query['sql'][:200] + '...' if len(query['sql']) > 200 else query['sql'],
                                        'time': query['time']
                                    }
                                    for query in connection.queries
                                ]
                            }
                        }
                    )
                else:
                    logger.debug(
                        f"DB queries: {queries_count} queries in {total_time:.2f}s for {request.method} {request.path_info}",
                        extra={
                            'db_queries': {
                                'count': queries_count,
                                'total_time': total_time
                            }
                        }
                    )
        
        return response
    
    def _should_log_queries(self, request: HttpRequest) -> bool:
        """
        Определяет, нужно ли логировать SQL запросы
        """
        # Не логируем запросы к статическим файлам
        skip_paths = ['/static/', '/media/', '/favicon.ico']
        path = request.path_info
        return not any(path.startswith(skip_path) for skip_path in skip_paths)