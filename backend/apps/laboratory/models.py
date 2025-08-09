from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime, timedelta
from apps.warehouse.models import MaterialReceipt
from apps.common.models import AuditMixin
import json


class TestEquipment(AuditMixin):
    """Модель испытательного оборудования"""
    
    EQUIPMENT_TYPE_CHOICES = [
        ('spectrometer', 'Спектрометр'),
        ('tensile_machine', 'Разрывная машина'),
        ('hardness_tester', 'Твердомер'),
        ('ultrasonic_detector', 'УЗ дефектоскоп'),
        ('microscope', 'Микроскоп'),
        ('furnace', 'Печь'),
        ('scales', 'Весы'),
        ('other', 'Прочее'),
    ]

    name = models.CharField(
        max_length=200,
        verbose_name='Название оборудования'
    )
    equipment_type = models.CharField(
        max_length=50,
        choices=EQUIPMENT_TYPE_CHOICES,
        default='other',
        verbose_name='Тип оборудования'
    )
    model = models.CharField(
        max_length=100,
        verbose_name='Модель'
    )
    serial_number = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Серийный номер'
    )
    manufacturer = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Производитель'
    )
    calibration_date = models.DateField(
        verbose_name='Дата калибровки'
    )
    next_calibration_date = models.DateField(
        verbose_name='Дата следующей калибровки'
    )
    calibration_interval_months = models.PositiveIntegerField(
        default=12,
        verbose_name='Интервал калибровки (месяцев)'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активно'
    )
    location = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Расположение'
    )
    responsible_person = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='responsible_equipment',
        verbose_name='Ответственное лицо'
    )
    accuracy_class = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Класс точности'
    )
    measurement_range = models.TextField(
        blank=True,
        verbose_name='Диапазон измерений'
    )
    notes = models.TextField(
        blank=True,
        verbose_name='Примечания'
    )

    def clean(self):
        """Валидация модели"""
        super().clean()
        
        # Проверка дат калибровки
        if self.calibration_date and self.next_calibration_date:
            if self.next_calibration_date <= self.calibration_date:
                raise ValidationError({
                    'next_calibration_date': 'Дата следующей калибровки должна быть позже текущей'
                })

    def save(self, *args, **kwargs):
        """Переопределение сохранения для автоматического расчета даты калибровки"""
        # Автоматически рассчитываем следующую дату калибровки если не указана
        if self.calibration_date and not self.next_calibration_date:
            self.next_calibration_date = self.calibration_date + timedelta(
                days=self.calibration_interval_months * 30
            )
        
        self.clean()
        super().save(*args, **kwargs)

    def needs_calibration(self, warning_days=30):
        """Проверка необходимости калибровки"""
        if not self.next_calibration_date:
            return True
            
        today = timezone.now().date()
        warning_date = self.next_calibration_date - timedelta(days=warning_days)
        
        return today >= warning_date

    def is_overdue(self):
        """Проверка просрочки калибровки"""
        if not self.next_calibration_date:
            return True
            
        return timezone.now().date() > self.next_calibration_date

    def days_until_calibration(self):
        """Количество дней до калибровки"""
        if not self.next_calibration_date:
            return 0
            
        delta = self.next_calibration_date - timezone.now().date()
        return delta.days

    def get_calibration_status(self):
        """Получить статус калибровки"""
        if self.is_overdue():
            return 'overdue'
        elif self.needs_calibration():
            return 'warning'
        else:
            return 'valid'

    def get_calibration_status_display(self):
        """Человекочитаемый статус калибровки"""
        status = self.get_calibration_status()
        statuses = {
            'overdue': 'Просрочена',
            'warning': 'Требует внимания',
            'valid': 'Действительна'
        }
        return statuses.get(status, 'Неизвестно')

    def __str__(self):
        return f"{self.name} ({self.model}) - {self.serial_number}"

    class Meta:
        verbose_name = 'Испытательное оборудование'
        verbose_name_plural = 'Испытательное оборудование'
        ordering = ['name', 'model']
        indexes = [
            models.Index(fields=['equipment_type']),
            models.Index(fields=['is_active']),
            models.Index(fields=['next_calibration_date']),
            models.Index(fields=['calibration_date']),
        ]


class LabTestRequest(AuditMixin):
    """Модель запроса на лабораторные испытания"""
    
    TEST_TYPE_CHOICES = [
        ('chemical_analysis', 'Химический анализ'),
        ('mechanical_properties', 'Механические свойства'),
        ('ultrasonic', 'Ультразвуковой контроль'),
        ('hardness', 'Измерение твердости'),
        ('metallographic', 'Металлографический анализ'),
        ('corrosion_resistance', 'Коррозионная стойкость'),
        ('fatigue_test', 'Испытание на усталость'),
        ('impact_test', 'Испытание на ударную вязкость'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Низкий'),
        ('normal', 'Обычный'),
        ('high', 'Высокий'),
        ('urgent', 'Срочный'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Ожидает'),
        ('assigned', 'Назначено'),
        ('in_progress', 'Выполняется'),
        ('completed', 'Завершено'),
        ('cancelled', 'Отменено'),
        ('on_hold', 'Приостановлено'),
    ]

    material_receipt = models.ForeignKey(
        MaterialReceipt,
        on_delete=models.CASCADE,
        related_name='lab_test_requests',
        verbose_name='Поступление материала'
    )
    requested_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='lab_requests',
        verbose_name='Заказчик'
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_lab_tests',
        verbose_name='Исполнитель'
    )
    test_type = models.CharField(
        max_length=50,
        choices=TEST_TYPE_CHOICES,
        verbose_name='Тип испытания'
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='normal',
        verbose_name='Приоритет'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Статус'
    )
    internal_testing = models.BooleanField(
        default=True,
        verbose_name='Внутреннее испытание',
        help_text='Выполняется в собственной лаборатории'
    )
    external_lab = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Внешняя лаборатория',
        help_text='Указать если internal_testing = False'
    )
    request_date = models.DateTimeField(
        default=timezone.now,
        verbose_name='Дата запроса'
    )
    required_completion_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Требуемая дата завершения'
    )
    actual_start_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Фактическая дата начала'
    )
    actual_completion_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Фактическая дата завершения'
    )
    test_requirements = models.TextField(
        verbose_name='Требования к испытанию',
        help_text='Подробное описание того, что нужно проверить'
    )
    sample_preparation_notes = models.TextField(
        blank=True,
        verbose_name='Примечания по подготовке образцов'
    )
    estimated_duration_hours = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Оценочная продолжительность (часы)'
    )

    def clean(self):
        """Валидация модели"""
        super().clean()
        
        # Если не внутреннее испытание, должна быть указана внешняя лаборатория
        if not self.internal_testing and not self.external_lab:
            raise ValidationError({
                'external_lab': 'Для внешних испытаний необходимо указать лабораторию'
            })
        
        # Проверка дат
        if (self.actual_start_date and self.actual_completion_date and 
            self.actual_completion_date < self.actual_start_date):
            raise ValidationError({
                'actual_completion_date': 'Дата завершения не может быть раньше даты начала'
            })

    def save(self, *args, **kwargs):
        """Переопределение сохранения для автоматической установки дат"""
        # Автоматически устанавливаем дату начала при переводе в статус "выполняется"
        if self.status == 'in_progress' and not self.actual_start_date:
            self.actual_start_date = timezone.now()
        
        # Автоматически устанавливаем дату завершения при завершении
        if self.status == 'completed' and not self.actual_completion_date:
            self.actual_completion_date = timezone.now()
        
        self.clean()
        super().save(*args, **kwargs)

    def get_duration(self):
        """Получить фактическую продолжительность испытания"""
        if self.actual_start_date and self.actual_completion_date:
            delta = self.actual_completion_date - self.actual_start_date
            return delta.total_seconds() / 3600  # в часах
        return None

    def is_overdue(self):
        """Проверка просрочки испытания"""
        if not self.required_completion_date:
            return False
        
        if self.status in ['completed', 'cancelled']:
            return False
            
        return timezone.now().date() > self.required_completion_date

    def get_priority_weight(self):
        """Получить числовой вес приоритета для сортировки"""
        weights = {
            'low': 1,
            'normal': 2,
            'high': 3,
            'urgent': 4
        }
        return weights.get(self.priority, 2)

    def __str__(self):
        material = self.material_receipt.material
        return f"{self.get_test_type_display()} - {material.material_grade} ({self.get_status_display()})"

    class Meta:
        verbose_name = 'Запрос на испытание'
        verbose_name_plural = 'Запросы на испытания'
        ordering = ['-request_date']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['test_type']),
            models.Index(fields=['priority']),
            models.Index(fields=['request_date']),
            models.Index(fields=['required_completion_date']),
        ]


class LabTestResult(AuditMixin):
    """Модель результата лабораторного испытания"""
    
    CONCLUSION_CHOICES = [
        ('passed', 'Соответствует'),
        ('failed', 'Не соответствует'),
        ('conditional', 'Условно соответствует'),
        ('retest_required', 'Требуется переиспытание'),
    ]

    test_request = models.OneToOneField(
        LabTestRequest,
        on_delete=models.CASCADE,
        related_name='test_result',
        verbose_name='Запрос на испытание'
    )
    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='performed_tests',
        verbose_name='Исполнитель'
    )
    test_date = models.DateTimeField(
        default=timezone.now,
        verbose_name='Дата испытания'
    )
    equipment_used = models.ManyToManyField(
        TestEquipment,
        related_name='test_results',
        verbose_name='Использованное оборудование'
    )
    results = models.JSONField(
        default=dict,
        verbose_name='Результаты испытания',
        help_text='Данные испытания в формате JSON'
    )
    conclusion = models.CharField(
        max_length=20,
        choices=CONCLUSION_CHOICES,
        verbose_name='Заключение'
    )
    certificate_number = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Номер протокола/сертификата'
    )
    test_conditions = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Условия испытания',
        help_text='Температура, влажность и другие параметры'
    )
    sample_description = models.TextField(
        verbose_name='Описание образца'
    )
    test_method = models.CharField(
        max_length=200,
        verbose_name='Метод испытания',
        help_text='ГОСТ, ТУ или другой стандарт'
    )
    comments = models.TextField(
        blank=True,
        verbose_name='Комментарии'
    )
    file_attachments = models.TextField(
        blank=True,
        verbose_name='Приложенные файлы',
        help_text='Пути к файлам с графиками, фотографиями и т.д.'
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_tests',
        verbose_name='Утвердил'
    )
    approval_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата утверждения'
    )

    def clean(self):
        """Валидация модели"""
        super().clean()
        
        # Проверка оборудования возможна только после сохранения объекта
        # (из-за ограничений ManyToMany)
        if self.pk:
            for equipment in self.equipment_used.all():
                if equipment.is_overdue():
                    raise ValidationError({
                        'equipment_used': f'Оборудование {equipment.name} имеет просроченную калибровку'
                    })

    def save(self, *args, **kwargs):
        """Переопределение сохранения"""
        # Автоматически обновляем статус запроса
        if self.test_request.status != 'completed':
            self.test_request.status = 'completed'
            self.test_request.actual_completion_date = self.test_date
            self.test_request.save()
        
        self.clean()
        super().save(*args, **kwargs)

    def get_chemical_composition(self):
        """Извлечь химический состав из результатов"""
        if self.test_request.test_type == 'chemical_analysis':
            return self.results.get('chemical_composition', {})
        return None

    def get_mechanical_properties(self):
        """Извлечь механические свойства из результатов"""
        if self.test_request.test_type == 'mechanical_properties':
            return self.results.get('mechanical_properties', {})
        return None

    def get_defects_found(self):
        """Извлечь найденные дефекты (для УЗК)"""
        if self.test_request.test_type == 'ultrasonic':
            return self.results.get('defects', [])
        return []

    def is_approved(self):
        """Проверка утверждения результата"""
        return self.approved_by is not None and self.approval_date is not None

    def format_results_for_certificate(self):
        """Форматирование результатов для протокола"""
        formatted = {}
        
        if self.test_request.test_type == 'chemical_analysis':
            composition = self.get_chemical_composition()
            if composition:
                formatted['Химический состав'] = composition
                
        elif self.test_request.test_type == 'mechanical_properties':
            properties = self.get_mechanical_properties()
            if properties:
                formatted['Механические свойства'] = properties
                
        elif self.test_request.test_type == 'ultrasonic':
            defects = self.get_defects_found()
            formatted['Обнаруженные дефекты'] = defects if defects else 'Не обнаружены'
            
        return formatted

    def __str__(self):
        return f"Протокол {self.certificate_number} - {self.test_request}"

    class Meta:
        verbose_name = 'Результат испытания'
        verbose_name_plural = 'Результаты испытаний'
        ordering = ['-test_date']
        indexes = [
            models.Index(fields=['conclusion']),
            models.Index(fields=['test_date']),
            models.Index(fields=['certificate_number']),
        ]


# Модель для стандартных требований к испытаниям
class TestStandard(AuditMixin):
    """Модель стандартов испытаний"""
    
    name = models.CharField(
        max_length=100,
        verbose_name='Название стандарта'
    )
    standard_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Номер стандарта'
    )
    test_type = models.CharField(
        max_length=50,
        choices=LabTestRequest.TEST_TYPE_CHOICES,
        verbose_name='Тип испытания'
    )
    material_grades = models.TextField(
        blank=True,
        verbose_name='Применимые марки материалов',
        help_text='Перечислить через запятую'
    )
    requirements = models.JSONField(
        default=dict,
        verbose_name='Требования стандарта',
        help_text='Минимальные и максимальные значения'
    )
    test_method = models.TextField(
        verbose_name='Методика испытания'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен'
    )

    def get_applicable_grades(self):
        """Получить список применимых марок"""
        if self.material_grades:
            return [grade.strip() for grade in self.material_grades.split(',')]
        return []

    def is_applicable_for_material(self, material_grade):
        """Проверить применимость стандарта к марке материала"""
        applicable_grades = self.get_applicable_grades()
        if not applicable_grades:
            return True  # Универсальный стандарт
        
        return any(grade in material_grade for grade in applicable_grades)

    def check_compliance(self, test_results):
        """Проверить соответствие результатов стандарту"""
        compliance = {}
        requirements = self.requirements
        
        for parameter, limits in requirements.items():
            if parameter in test_results:
                value = test_results[parameter]
                min_val = limits.get('min')
                max_val = limits.get('max')
                
                is_compliant = True
                if min_val is not None and value < min_val:
                    is_compliant = False
                if max_val is not None and value > max_val:
                    is_compliant = False
                    
                compliance[parameter] = {
                    'value': value,
                    'required': limits,
                    'compliant': is_compliant
                }
        
        return compliance

    def __str__(self):
        return f"{self.standard_number} - {self.name}"

    class Meta:
        verbose_name = 'Стандарт испытания'
        verbose_name_plural = 'Стандарты испытаний'
        ordering = ['standard_number'] 