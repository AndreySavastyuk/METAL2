from django.apps import AppConfig


class WorkflowConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.workflow'
    verbose_name = 'Рабочие процессы'
    
    def ready(self):
        """Инициализация приложения workflow"""
        
        # Импортируем сигналы
        try:
            from . import signals
            signals.setup_workflow_signals()
        except ImportError:
            pass
        
        # Импортируем задачи Celery
        try:
            from . import tasks
        except ImportError:
            pass 