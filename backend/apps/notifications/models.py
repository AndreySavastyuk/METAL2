"""
Модели для системы уведомлений
"""
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.utils import timezone
import json


class UserNotificationPreferences(models.Model):
    """Настройки уведомлений пользователя"""
    
    NOTIFICATION_TYPES = [
        ('status_update', 'Изменение статуса материала'),
        ('task_assignment', 'Назначение задачи'),
        ('daily_summary', 'Ежедневная сводка'),
        ('urgent_alert', 'Срочные уведомления'),
        ('sla_warning', 'Предупреждение о нарушении SLA'),
        ('quality_alert', 'Уведомления о качестве'),
        ('workflow_complete', 'Завершение процесса'),
    ]
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='notification_preferences',
        verbose_name='Пользователь'
    )
    
    telegram_chat_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        validators=[RegexValidator(regex=r'^-?\d+$', message='Chat ID должен содержать только цифры')],
        verbose_name='Telegram Chat ID',
        help_text='ID чата в Telegram для отправки уведомлений'
    )
    
    is_telegram_enabled = models.BooleanField(
        default=False,
        verbose_name='Включить Telegram уведомления'
    )
    
    notification_types = models.JSONField(
        default=dict,
        verbose_name='Типы уведомлений',
        help_text='Настройки для каждого типа уведомлений'
    )
    
    quiet_hours_start = models.TimeField(
        null=True,
        blank=True,
        verbose_name='Начало тихих часов',
        help_text='Время начала периода, когда не отправлять уведомления'
    )
    
    quiet_hours_end = models.TimeField(
        null=True,
        blank=True,
        verbose_name='Конец тихих часов',
        help_text='Время окончания периода, когда не отправлять уведомления'
    )
    
    timezone = models.CharField(
        max_length=50,
        default='Europe/Moscow',
        verbose_name='Часовой пояс'
    )
    
    language = models.CharField(
        max_length=10,
        default='ru',
        choices=[('ru', 'Русский'), ('en', 'English')],
        verbose_name='Язык уведомлений'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Настройки уведомлений пользователя'
        verbose_name_plural = 'Настройки уведомлений пользователей'

    def __str__(self):
        return f"Уведомления для {self.user.username}"
    
    def get_notification_preference(self, notification_type: str) -> dict:
        """Получить настройки для конкретного типа уведомления"""
        if not self.notification_types:
            return {'enabled': False, 'urgent_only': False}
        
        return self.notification_types.get(notification_type, {
            'enabled': False,
            'urgent_only': False
        })
    
    def set_notification_preference(self, notification_type: str, enabled: bool = True, urgent_only: bool = False):
        """Установить настройки для конкретного типа уведомления"""
        if not self.notification_types:
            self.notification_types = {}
        
        self.notification_types[notification_type] = {
            'enabled': enabled,
            'urgent_only': urgent_only
        }
        self.save()
    
    def is_in_quiet_hours(self) -> bool:
        """Проверить, находимся ли в тихих часах"""
        if not self.quiet_hours_start or not self.quiet_hours_end:
            return False
        
        now = timezone.now().time()
        
        # Если тихие часы пересекают полночь
        if self.quiet_hours_start > self.quiet_hours_end:
            return now >= self.quiet_hours_start or now <= self.quiet_hours_end
        
        # Обычный случай
        return self.quiet_hours_start <= now <= self.quiet_hours_end
    
    def should_send_notification(self, notification_type: str, is_urgent: bool = False) -> bool:
        """Проверить, нужно ли отправлять уведомление"""
        if not self.is_telegram_enabled or not self.telegram_chat_id:
            return False
        
        # Срочные уведомления отправляются всегда
        if is_urgent:
            return True
        
        # Проверяем тихие часы
        if self.is_in_quiet_hours():
            return False
        
        # Проверяем настройки типа уведомления
        prefs = self.get_notification_preference(notification_type)
        if not prefs.get('enabled', False):
            return False
        
        # Если включен режим "только срочные"
        if prefs.get('urgent_only', False) and not is_urgent:
            return False
        
        return True


class NotificationLog(models.Model):
    """Лог отправленных уведомлений"""
    
    STATUS_CHOICES = [
        ('pending', 'Ожидает отправки'),
        ('sent', 'Отправлено'),
        ('failed', 'Ошибка отправки'),
        ('retry', 'Повторная попытка'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notification_logs',
        verbose_name='Пользователь'
    )
    
    notification_type = models.CharField(
        max_length=50,
        verbose_name='Тип уведомления'
    )
    
    message = models.TextField(
        verbose_name='Сообщение'
    )
    
    telegram_chat_id = models.CharField(
        max_length=50,
        verbose_name='Telegram Chat ID'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Статус'
    )
    
    error_message = models.TextField(
        blank=True,
        verbose_name='Сообщение об ошибке'
    )
    
    retry_count = models.PositiveIntegerField(
        default=0,
        verbose_name='Количество попыток'
    )
    
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Время отправки'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Метаданные для связи с объектами системы
    object_type = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Тип объекта'
    )
    
    object_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='ID объекта'
    )

    class Meta:
        verbose_name = 'Лог уведомления'
        verbose_name_plural = 'Логи уведомлений'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.notification_type} для {self.user.username} - {self.status}"