"""
Конфигурация Celery для MetalQMS
"""
import os
from celery import Celery

# Устанавливаем настройки Django для Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('metalqms')

# Используем строку здесь, чтобы celery worker не сериализовал объект конфигурации
# - namespace='CELERY' означает, что все настройки celery должны начинаться с 'CELERY_'
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматически найти задачи во всех зарегистрированных Django приложениях
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    """Отладочная задача для проверки работы Celery"""
    print(f'Request: {self.request!r}')