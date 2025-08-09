"""
Общие модели и миксины для всех приложений
"""

from django.db import models
from django.contrib.auth.models import User


class AuditMixin(models.Model):
    """Миксин для отслеживания аудита изменений"""
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='%(class)s_created',
        verbose_name='Создано пользователем'
    )
    created_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name='Дата создания'
    )
    updated_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='%(class)s_updated',
        verbose_name='Обновлено пользователем'
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        verbose_name='Дата обновления'
    )

    class Meta:
        abstract = True