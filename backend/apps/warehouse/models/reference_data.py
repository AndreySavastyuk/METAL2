"""
Справочные модели для warehouse приложения
"""

from django.db import models
from apps.common.models import AuditMixin


class Supplier(AuditMixin):
    """Поставщик"""
    name = models.CharField(
        max_length=200,
        unique=True,
        verbose_name='Название'
    )
    legal_name = models.CharField(
        max_length=300,
        verbose_name='Юридическое название'
    )
    inn = models.CharField(
        max_length=12,
        unique=True,
        verbose_name='ИНН'
    )
    kpp = models.CharField(
        max_length=9,
        blank=True,
        verbose_name='КПП'
    )
    address = models.TextField(
        verbose_name='Адрес'
    )
    contact_person = models.CharField(
        max_length=200,
        verbose_name='Контактное лицо'
    )
    phone = models.CharField(
        max_length=20,
        verbose_name='Телефон'
    )
    email = models.EmailField(
        verbose_name='Email'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен'
    )

    class Meta:
        verbose_name = 'Поставщик'
        verbose_name_plural = 'Поставщики'
        ordering = ['name']

    def __str__(self):
        return self.name


class MaterialGrade(AuditMixin):
    """Марка материала"""
    name = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Название марки'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание'
    )
    density = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name='Плотность (г/см³)'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активна'
    )

    class Meta:
        verbose_name = 'Марка материала'
        verbose_name_plural = 'Марки материалов'
        ordering = ['name']

    def __str__(self):
        return self.name


class ProductType(AuditMixin):
    """Тип проката"""
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Название'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен'
    )

    class Meta:
        verbose_name = 'Тип проката'
        verbose_name_plural = 'Типы проката'
        ordering = ['name']

    def __str__(self):
        return self.name