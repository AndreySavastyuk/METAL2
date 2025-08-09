from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.warehouse.models import MaterialReceipt
from apps.common.models import AuditMixin
import re


class QCInspection(AuditMixin):
    """Модель инспекции контроля качества"""
    
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('in_progress', 'В процессе'),
        ('completed', 'Завершено'),
        ('rejected', 'Отклонено'),
    ]

    material_receipt = models.ForeignKey(
        MaterialReceipt,
        on_delete=models.CASCADE,
        related_name='qc_inspections',
        verbose_name='Поступление материала'
    )
    inspector = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='qc_inspections',
        verbose_name='Инспектор'
    )
    inspection_date = models.DateTimeField(
        default=timezone.now,
        verbose_name='Дата инспекции'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name='Статус'
    )
    requires_ppsd = models.BooleanField(
        default=False,
        verbose_name='Требует ППСД'
    )
    requires_ultrasonic = models.BooleanField(
        default=False,
        verbose_name='Требует УЗК'
    )
    comments = models.TextField(
        blank=True,
        verbose_name='Комментарии'
    )
    completion_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата завершения'
    )

    def determine_ppsd_requirement(self):
        """Автоматическое определение необходимости ППСД на основе марки материала"""
        material = self.material_receipt.material
        grade = material.material_grade.upper()
        
        # Список марок, требующих ППСД
        ppsd_grades = [
            '20X13', '12X18H10T', '08X18H10T', '10X17H13M2T',
            '03X17H14M3', '08X17H15M3T', '10X23H18', '20X23H18'
        ]
        
        # Проверяем точное соответствие или частичное вхождение
        for ppsd_grade in ppsd_grades:
            if ppsd_grade in grade:
                return True
        
        # Дополнительная проверка по шаблонам
        stainless_patterns = [
            r'\d+X\d+H\d+',  # Нержавеющие стали типа 12X18H10
            r'.*H\d+.*',      # Содержащие никель
        ]
        
        for pattern in stainless_patterns:
            if re.match(pattern, grade):
                return True
                
        return False

    def determine_ultrasonic_requirement(self):
        """Автоматическое определение необходимости УЗК на основе размера и марки"""
        material = self.material_receipt.material
        size = material.size.lower()
        grade = material.material_grade.upper()
        
        # УЗК требуется для толстых изделий
        thick_patterns = [
            r'⌀\d{3,}',  # Диаметр 100мм и более
            r'лист\s*\d{2,}',  # Лист толщиной 10мм и более
            r'\d{2,}мм',  # Толщина 10мм и более
        ]
        
        for pattern in thick_patterns:
            if re.search(pattern, size):
                return True
        
        # УЗК для ответственных марок
        critical_grades = ['40X', '30ХГСА', '09Г2С']
        if any(cg in grade for cg in critical_grades):
            return True
            
        return False

    def save(self, *args, **kwargs):
        """Переопределение сохранения для автоопределения требований"""
        # Автоматически определяем требования при создании
        if not self.pk:  # Новый объект
            self.requires_ppsd = self.determine_ppsd_requirement()
            self.requires_ultrasonic = self.determine_ultrasonic_requirement()
        
        # Устанавливаем дату завершения при смене статуса
        if self.status == 'completed' and not self.completion_date:
            self.completion_date = timezone.now()
        elif self.status != 'completed':
            self.completion_date = None
            
        super().save(*args, **kwargs)

    def get_completion_percentage(self):
        """Процент завершения инспекции"""
        total_items = self.inspection_results.count()
        if total_items == 0:
            return 0
        
        completed_items = self.inspection_results.exclude(result='').count()
        return round((completed_items / total_items) * 100, 1)

    def get_critical_failures(self):
        """Получить критические несоответствия"""
        return self.inspection_results.filter(
            checklist_item__is_critical=True,
            result='failed'
        )

    def can_complete(self):
        """Проверка возможности завершения инспекции"""
        # Все критические пункты должны быть пройдены
        critical_failures = self.get_critical_failures()
        return critical_failures.count() == 0

    def __str__(self):
        return f"Инспекция {self.material_receipt.material.material_grade} - {self.get_status_display()}"

    class Meta:
        verbose_name = 'Инспекция ОТК'
        verbose_name_plural = 'Инспекции ОТК'
        ordering = ['-inspection_date']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['inspection_date']),
            models.Index(fields=['inspector']),
        ]


class QCChecklist(AuditMixin):
    """Модель чек-листа для контроля качества"""
    
    name = models.CharField(
        max_length=200,
        verbose_name='Название чек-листа'
    )
    material_grade = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Марка материала (фильтр)',
        help_text='Оставьте пустым для универсального чек-листа'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен'
    )
    version = models.CharField(
        max_length=20,
        default='1.0',
        verbose_name='Версия'
    )

    def get_applicable_materials(self):
        """Получить материалы, к которым применим данный чек-лист"""
        from apps.warehouse.models import Material
        
        if not self.material_grade:
            return Material.objects.all()
        
        return Material.objects.filter(
            material_grade__icontains=self.material_grade
        )

    def duplicate_for_new_version(self):
        """Создать копию чек-листа с новой версией"""
        items = list(self.checklist_items.all())
        
        # Увеличиваем версию
        version_parts = self.version.split('.')
        new_version = f"{version_parts[0]}.{int(version_parts[1]) + 1}"
        
        # Создаем новый чек-лист
        new_checklist = QCChecklist.objects.create(
            name=f"{self.name} (v{new_version})",
            material_grade=self.material_grade,
            description=self.description,
            version=new_version,
            created_by=self.created_by,
            updated_by=self.updated_by
        )
        
        # Копируем все пункты
        for item in items:
            QCChecklistItem.objects.create(
                checklist=new_checklist,
                description=item.description,
                order=item.order,
                is_critical=item.is_critical,
                acceptance_criteria=item.acceptance_criteria,
                created_by=item.created_by,
                updated_by=item.updated_by
            )
        
        return new_checklist

    def __str__(self):
        grade_info = f" ({self.material_grade})" if self.material_grade else " (универсальный)"
        return f"{self.name}{grade_info} v{self.version}"

    class Meta:
        verbose_name = 'Чек-лист ОТК'
        verbose_name_plural = 'Чек-листы ОТК'
        ordering = ['material_grade', 'name']
        unique_together = ['name', 'version']


class QCChecklistItem(AuditMixin):
    """Модель пункта чек-листа"""
    
    checklist = models.ForeignKey(
        QCChecklist,
        on_delete=models.CASCADE,
        related_name='checklist_items',
        verbose_name='Чек-лист'
    )
    description = models.TextField(
        verbose_name='Описание пункта'
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name='Порядок'
    )
    is_critical = models.BooleanField(
        default=False,
        verbose_name='Критический пункт',
        help_text='Критические пункты не могут быть отмечены как "Н/П"'
    )
    acceptance_criteria = models.TextField(
        blank=True,
        verbose_name='Критерии приемки',
        help_text='Подробное описание того, что считается приемлемым'
    )

    def __str__(self):
        critical_mark = " [КРИТИЧЕСКИЙ]" if self.is_critical else ""
        return f"{self.order}. {self.description[:50]}...{critical_mark}"

    class Meta:
        verbose_name = 'Пункт чек-листа'
        verbose_name_plural = 'Пункты чек-листа'
        ordering = ['checklist', 'order']
        unique_together = ['checklist', 'order']


class QCInspectionResult(AuditMixin):
    """Модель результата инспекции по пункту чек-листа"""
    
    RESULT_CHOICES = [
        ('passed', 'Пройдено'),
        ('failed', 'Не пройдено'),
        ('na', 'Не применимо'),
    ]

    inspection = models.ForeignKey(
        QCInspection,
        on_delete=models.CASCADE,
        related_name='inspection_results',
        verbose_name='Инспекция'
    )
    checklist_item = models.ForeignKey(
        QCChecklistItem,
        on_delete=models.CASCADE,
        related_name='inspection_results',
        verbose_name='Пункт чек-листа'
    )
    result = models.CharField(
        max_length=10,
        choices=RESULT_CHOICES,
        blank=True,
        verbose_name='Результат'
    )
    notes = models.TextField(
        blank=True,
        verbose_name='Примечания',
        help_text='Дополнительные комментарии по результату проверки'
    )
    measured_value = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Измеренное значение',
        help_text='Фактическое измеренное значение (если применимо)'
    )
    inspector_signature = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Подпись инспектора'
    )

    def clean(self):
        """Валидация модели"""
        super().clean()
        
        # Критические пункты не могут быть отмечены как "Не применимо"
        if (self.checklist_item.is_critical and 
            self.result == 'na'):
            raise ValidationError({
                'result': 'Критические пункты не могут быть отмечены как "Не применимо"'
            })
        
        # Если результат "Не пройдено", примечания обязательны
        if self.result == 'failed' and not self.notes:
            raise ValidationError({
                'notes': 'При отрицательном результате примечания обязательны'
            })

    def save(self, *args, **kwargs):
        """Переопределение сохранения с валидацией"""
        self.clean()
        super().save(*args, **kwargs)
        
        # Обновляем статус инспекции если все критические пункты пройдены
        if self.result == 'passed' and self.checklist_item.is_critical:
            self._check_inspection_completion()

    def _check_inspection_completion(self):
        """Проверка возможности автозавершения инспекции"""
        inspection = self.inspection
        
        # Проверяем все ли критические пункты пройдены
        critical_items = QCChecklistItem.objects.filter(
            checklist__in=inspection.inspection_results.values_list('checklist_item__checklist', flat=True),
            is_critical=True
        )
        
        failed_critical = inspection.inspection_results.filter(
            checklist_item__in=critical_items,
            result='failed'
        ).exists()
        
        if not failed_critical and inspection.status == 'in_progress':
            # Проверяем процент завершения
            if inspection.get_completion_percentage() >= 80:
                inspection.status = 'completed'
                inspection.completion_date = timezone.now()
                inspection.save()

    def get_result_color(self):
        """Получить цвет для отображения результата"""
        colors = {
            'passed': 'green',
            'failed': 'red',
            'na': 'gray',
            '': 'orange'  # Не заполнено
        }
        return colors.get(self.result, 'black')

    def __str__(self):
        result_display = self.get_result_display() if self.result else "Не проверено"
        return f"{self.checklist_item.description[:30]}... - {result_display}"

    class Meta:
        verbose_name = 'Результат инспекции'
        verbose_name_plural = 'Результаты инспекции'
        ordering = ['checklist_item__order']
        unique_together = ['inspection', 'checklist_item']
        indexes = [
            models.Index(fields=['result']),
            models.Index(fields=['checklist_item']),
        ]


class PPSDChecklist(AuditMixin):
    """Чек-лист ППСД (Первый Производственный Образец)"""
    name = models.CharField(max_length=200, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    checklist_items = models.JSONField(default=list, verbose_name='Пункты проверки')
    is_active = models.BooleanField(default=True, verbose_name='Активен')

    class Meta:
        verbose_name = 'Чек-лист ППСД'
        verbose_name_plural = 'Чек-листы ППСД'
        ordering = ['name']

    def __str__(self):
        return self.name


# Сигналы для автоматического создания результатов инспекции
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=QCInspection)
def create_inspection_results(sender, instance, created, **kwargs):
    """Автоматическое создание результатов инспекции на основе применимых чек-листов"""
    if created:
        # Получаем чек-листы, применимые к данному материалу
        material_grade = instance.material_receipt.material.material_grade
        
        # Универсальные чек-листы (без привязки к марке)
        universal_checklists = QCChecklist.objects.filter(
            is_active=True,
            material_grade=''
        )
        
        # Специфические чек-листы для данной марки материала
        specific_checklists = QCChecklist.objects.filter(
            is_active=True,
            material_grade__isnull=False,
            material_grade__icontains=material_grade[:5]  # Частичное совпадение
        )
        
        # Объединяем результаты без union для избежания проблем с ORDER BY
        all_checklist_ids = list(universal_checklists.values_list('id', flat=True)) + \
                           list(specific_checklists.values_list('id', flat=True))
        applicable_checklists = QCChecklist.objects.filter(id__in=all_checklist_ids)
        
        # Создаем результаты для всех пунктов применимых чек-листов
        for checklist in applicable_checklists:
            for item in checklist.checklist_items.all():
                QCInspectionResult.objects.get_or_create(
                    inspection=instance,
                    checklist_item=item,
                    defaults={
                        'created_by': instance.created_by,
                        'updated_by': instance.updated_by
                    }
                ) 