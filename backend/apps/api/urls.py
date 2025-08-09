"""
URLs для API тестирования
"""
from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    path('health/', views.health_check, name='health'),
    path('system/', views.system_info, name='system'),
    path('test/', views.test_endpoint, name='test'),
    
    # CORS preflight
    path('health/', views.options_handler, name='health_options'),
    path('system/', views.options_handler, name='system_options'),
    path('test/', views.options_handler, name='test_options'),
]