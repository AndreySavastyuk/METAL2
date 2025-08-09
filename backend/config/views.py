"""
Базовые view функции для проекта
"""

from django.http import JsonResponse
from django.shortcuts import render


def home_view(request):
    """Домашняя страница"""
    return JsonResponse({
        'message': '🏭 MetalQMS - Система управления качеством металлообработки',
        'status': 'running',
        'version': '1.0.0',
        'services': {
            'admin': '/admin/',
            'api_docs': '/api/docs/',
            'health': '/health/'
        }
    })


def health_check(request):
    """Проверка здоровья системы"""
    return JsonResponse({
        'status': 'healthy',
        'timestamp': '2025-08-03T02:26:54Z',
        'database': 'connected',
        'django': 'running'
    })