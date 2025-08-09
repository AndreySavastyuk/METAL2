"""
Модели для BPMN workflow процессов
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
from viewflow.workflow.models import Process, Task
from decimal import Decimal
from datetime import timedelta

from apps.warehouse.models import MaterialReceipt
from apps.common.models import AuditMixin
from apps.quality.models import QCInspection
from apps.laboratory.models import LabTestRequest


class MaterialInspectionProcess(AuditMixin, Process):
    """
    Модель процесса инспекции материала с BPMN workflow
    """
    
    class STATUS_CHOICES(models.TextChoices):
        DRAFT = 'draft', 'Черновик'
        ACTIVE = 'active', 'Активен'
        COMPLETED = 'completed', 'Завершен'
        CANCELLED = 'cancelled', 'Отменен'
        ERROR = 'error', 'Ошибка'
        
    class PRIORITY_CHOICES(models.TextChoices):
        LOW = 'low', 'Низкий'
        NORMAL = 'normal', 'Обычный'
        HIGH = 'high', 'Высокий'
        URGENT = 'urgent', 'Срочный'
        
    # Связь с бизнес-объектами
    material_receipt = models.OneToOneField(
        MaterialReceipt, 
        on_delete=models.CASCADE,
        related_name='inspection_process',
        verbose_name='Приемка материала'
    )
    
    # Метаданные процесса
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES.choices,
        default=PRIORITY_CHOICES.NORMAL,
        verbose_name='Приоритет'
    )
    
    # Участники процесса
    initiator = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='initiated_processes',
        verbose_name='Инициатор процесса'
    )
    
    current_assignee = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='current_processes',
        verbose_name='Текущий исполнитель'
    )
    
    # Временные метки и SLA
    started_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name='Время начала'
    )
    
    completed_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name='Время завершения'
    )
    
    due_date = models.DateTimeField(
        null=True, blank=True,
        verbose_name='Срок выполнения'
    )
    
    sla_deadline = models.DateTimeField(
        null=True, blank=True,
        verbose_name='SLA крайний срок'
    )
    
    # Статус выполнения
    progress_percentage = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=Decimal('0.00'),
        verbose_name='Процент выполнения'
    )
    
    # Бизнес-логика процесса
    requires_ppsd = models.BooleanField(
        default=False,
        verbose_name='Требует ППСД'
    )
    
    requires_ultrasonic = models.BooleanField(
        default=False,
        verbose_name='Требует УЗК'
    )
    
    requires_production_prep = models.BooleanField(
        default=True,
        verbose_name='Требует подготовку к производству'
    )
    
    # Комментарии и заметки
    comments = models.TextField(
        blank=True,
        verbose_name='Комментарии к процессу'
    )
    
    escalation_notes = models.TextField(
        blank=True,
        verbose_name='Заметки об эскалации'
    )
    
    class Meta:
        verbose_name = 'Процесс инспекции материала'
        verbose_name_plural = 'Процессы инспекции материалов'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['priority', '-created_at']),
            models.Index(fields=['current_assignee']),
            models.Index(fields=['sla_deadline']),
        ]
    
    def __str__(self):
        material = self.material_receipt.material
        return f"Процесс #{self.pk}: {material.material_grade} - {material.supplier}"
    
    def save(self, *args, **kwargs):
        """Автоматическое вычисление метрик процесса"""
        
        # Устанавливаем время начала при первом сохранении
        if not self.pk and not self.started_at:
            self.started_at = timezone.now()
        
        # Вычисляем SLA deadline
        if self.started_at and not self.sla_deadline:
            self.sla_deadline = self.calculate_sla_deadline()
        
        # Обновляем процент выполнения
        if self.pk:
            self.progress_percentage = self.calculate_progress()
        
        super().save(*args, **kwargs)
    
    def calculate_sla_deadline(self) -> timezone.datetime:
        """Вычисляет SLA deadline на основе приоритета и типа материала"""
        
        # Базовые SLA в часах
        base_sla_hours = {
            self.PRIORITY_CHOICES.URGENT: 12,   # 12 часов
            self.PRIORITY_CHOICES.HIGH: 24,     # 1 день  
            self.PRIORITY_CHOICES.NORMAL: 72,   # 3 дня
            self.PRIORITY_CHOICES.LOW: 120,     # 5 дней
        }
        
        hours = base_sla_hours.get(self.priority, 72)
        
        # Корректировка на сложность
        if self.requires_ppsd and self.requires_ultrasonic:
            hours += 24  # Дополнительный день для сложных испытаний
        elif self.requires_ppsd or self.requires_ultrasonic:
            hours += 12  # Полдня для одного типа испытаний
        
        return self.started_at + timedelta(hours=hours)
    
    def calculate_progress(self) -> Decimal:
        """Вычисляет процент выполнения на основе завершенных задач"""
        
        if not self.pk:
            return Decimal('0.00')
        
        total_tasks = self.task_set.count()
        if total_tasks == 0:
            return Decimal('0.00')
        
        completed_tasks = self.task_set.filter(status=Task.STATUS.DONE).count()
        
        progress = (completed_tasks / total_tasks) * 100
        return Decimal(str(round(progress, 2)))
    
    def is_overdue(self) -> bool:
        """Проверяет, просрочен ли процесс"""
        if not self.sla_deadline:
            return False
        return timezone.now() > self.sla_deadline
    
    def get_sla_status(self) -> str:
        """Возвращает статус SLA: 'ok', 'warning', 'critical', 'overdue'"""
        
        if not self.sla_deadline:
            return 'ok'
        
        now = timezone.now()
        
        if now > self.sla_deadline:
            return 'overdue'
        
        time_remaining = self.sla_deadline - now
        total_time = self.sla_deadline - self.started_at
        
        if time_remaining / total_time <= 0.2:  # 20% времени осталось
            return 'critical'
        elif time_remaining / total_time <= 0.5:  # 50% времени осталось
            return 'warning'
        
        return 'ok'
    
    def get_time_remaining(self) -> timedelta:
        """Возвращает оставшееся время до SLA deadline"""
        if not self.sla_deadline:
            return timedelta(0)
        
        remaining = self.sla_deadline - timezone.now()
        return remaining if remaining.total_seconds() > 0 else timedelta(0)
    
    def escalate(self, reason: str, escalated_by: User):
        """Эскалация процесса"""
        
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        escalation_note = f"[{timestamp}] Эскалация от {escalated_by.username}: {reason}"
        
        current_notes = self.escalation_notes or ""
        self.escalation_notes = f"{current_notes}\n{escalation_note}" if current_notes else escalation_note
        
        # Повышаем приоритет
        priority_upgrade = {
            self.PRIORITY_CHOICES.LOW: self.PRIORITY_CHOICES.NORMAL,
            self.PRIORITY_CHOICES.NORMAL: self.PRIORITY_CHOICES.HIGH,
            self.PRIORITY_CHOICES.HIGH: self.PRIORITY_CHOICES.URGENT,
        }
        
        if self.priority in priority_upgrade:
            self.priority = priority_upgrade[self.priority]
        
        self.save()
    
    def complete(self, completed_by: User):
        """Завершение процесса"""
        
        if self.status != self.STATUS.COMPLETED:
            self.status = self.STATUS.COMPLETED
            self.completed_at = timezone.now()
            self.current_assignee = None
            self.progress_percentage = Decimal('100.00')
            
            # Добавляем комментарий о завершении
            timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            completion_note = f"[{timestamp}] Процесс завершен пользователем {completed_by.username}"
            
            current_comments = self.comments or ""
            self.comments = f"{current_comments}\n{completion_note}" if current_comments else completion_note
            
            self.save()


class WorkflowTaskLog(AuditMixin):
    """
    Журнал выполнения задач workflow для аудита
    """
    
    class ACTION_CHOICES(models.TextChoices):
        CREATED = 'created', 'Создана'
        ASSIGNED = 'assigned', 'Назначена'
        STARTED = 'started', 'Начата'
        COMPLETED = 'completed', 'Завершена'
        CANCELLED = 'cancelled', 'Отменена'
        ESCALATED = 'escalated', 'Эскалирована'
        REASSIGNED = 'reassigned', 'Переназначена'
        
    process = models.ForeignKey(
        MaterialInspectionProcess,
        on_delete=models.CASCADE,
        related_name='task_logs',
        verbose_name='Процесс'
    )
    
    task_name = models.CharField(
        max_length=100,
        verbose_name='Название задачи'
    )
    
    task_id = models.CharField(
        max_length=50,
        verbose_name='ID задачи'
    )
    
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES.choices,
        verbose_name='Действие'
    )
    
    performer = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        verbose_name='Исполнитель'
    )
    
    assignee = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='assigned_task_logs',
        verbose_name='Назначена на'
    )
    
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Время действия'
    )
    
    duration_seconds = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name='Длительность (сек)'
    )
    
    comment = models.TextField(
        blank=True,
        verbose_name='Комментарий'
    )
    
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Дополнительные данные'
    )
    
    class Meta:
        verbose_name = 'Лог задачи workflow'
        verbose_name_plural = 'Логи задач workflow'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['process', '-timestamp']),
            models.Index(fields=['task_name', '-timestamp']),
            models.Index(fields=['performer', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.task_name}: {self.get_action_display()} - {self.performer.username}"
    
    @classmethod
    def log_task_action(cls, process, task_name, task_id, action, performer, 
                       assignee=None, comment="", metadata=None, duration=None):
        """Удобный метод для создания лога"""
        
        return cls.objects.create(
            process=process,
            task_name=task_name,
            task_id=task_id,
            action=action,
            performer=performer,
            assignee=assignee,
            comment=comment,
            metadata=metadata or {},
            duration_seconds=duration,
            created_by=performer,
            updated_by=performer
        )


class WorkflowSLAViolation(AuditMixin):
    """
    Нарушения SLA в workflow процессах
    """
    
    class VIOLATION_TYPE_CHOICES(models.TextChoices):
        WARNING = 'warning', 'Предупреждение'
        CRITICAL = 'critical', 'Критическое'
        OVERDUE = 'overdue', 'Просрочено'
        
    class STATUS_CHOICES(models.TextChoices):
        ACTIVE = 'active', 'Активное'
        ACKNOWLEDGED = 'acknowledged', 'Принято к сведению'
        RESOLVED = 'resolved', 'Разрешено'
        
    process = models.ForeignKey(
        MaterialInspectionProcess,
        on_delete=models.CASCADE,
        related_name='sla_violations',
        verbose_name='Процесс'
    )
    
    violation_type = models.CharField(
        max_length=20,
        choices=VIOLATION_TYPE_CHOICES.choices,
        verbose_name='Тип нарушения'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES.choices,
        default=STATUS_CHOICES.ACTIVE,
        verbose_name='Статус нарушения'
    )
    
    detected_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Время обнаружения'
    )
    
    acknowledged_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='acknowledged_violations',
        verbose_name='Принято к сведению'
    )
    
    acknowledged_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name='Время принятия'
    )
    
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='resolved_violations',
        verbose_name='Разрешено пользователем'
    )
    
    resolved_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name='Время разрешения'
    )
    
    message = models.TextField(
        verbose_name='Сообщение о нарушении'
    )
    
    resolution_comment = models.TextField(
        blank=True,
        verbose_name='Комментарий к разрешению'
    )
    
    class Meta:
        verbose_name = 'Нарушение SLA'
        verbose_name_plural = 'Нарушения SLA'
        ordering = ['-detected_at']
        indexes = [
            models.Index(fields=['status', '-detected_at']),
            models.Index(fields=['violation_type', '-detected_at']),
        ]
    
    def __str__(self):
        return f"SLA {self.get_violation_type_display()}: Процесс #{self.process.pk}"
    
    def acknowledge(self, user: User, comment: str = ""):
        """Принятие нарушения к сведению"""
        
        self.status = self.STATUS_CHOICES.ACKNOWLEDGED
        self.acknowledged_by = user
        self.acknowledged_at = timezone.now()
        
        if comment:
            self.resolution_comment = comment
        
        self.save()
    
    def resolve(self, user: User, comment: str = ""):
        """Разрешение нарушения"""
        
        self.status = self.STATUS_CHOICES.RESOLVED
        self.resolved_by = user
        self.resolved_at = timezone.now()
        
        if comment:
            existing_comment = self.resolution_comment or ""
            separator = "\n---\n" if existing_comment else ""
            self.resolution_comment = f"{existing_comment}{separator}Разрешено: {comment}"
        
        self.save()