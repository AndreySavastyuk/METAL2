"""
Celery задачи для мониторинга SLA и автоматических эскалаций
"""
from celery import shared_task
from django.utils import timezone
from django.contrib.auth.models import User
from django.conf import settings
from datetime import timedelta
import logging

from .models import MaterialInspectionProcess, WorkflowSLAViolation, WorkflowTaskLog
from apps.warehouse.services import NotificationService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def monitor_sla_violations(self):
    """
    Мониторинг нарушений SLA для всех активных процессов
    Запускается каждые 15 минут
    """
    try:
        logger.info("Начало мониторинга SLA нарушений")
        
        # Получаем все активные процессы
        active_processes = MaterialInspectionProcess.objects.filter(
            status=MaterialInspectionProcess.STATUS.ACTIVE,
            sla_deadline__isnull=False
        )
        
        violations_created = 0
        warnings_sent = 0
        
        for process in active_processes:
            violation_created, warning_sent = check_process_sla(process)
            
            if violation_created:
                violations_created += 1
            if warning_sent:
                warnings_sent += 1
        
        logger.info(
            f"Мониторинг SLA завершен. "
            f"Создано нарушений: {violations_created}, "
            f"Отправлено предупреждений: {warnings_sent}"
        )
        
        return {
            'success': True,
            'violations_created': violations_created,
            'warnings_sent': warnings_sent,
            'processes_checked': active_processes.count()
        }
        
    except Exception as exc:
        logger.error(f"Ошибка мониторинга SLA: {exc}")
        self.retry(countdown=60, exc=exc)


def check_process_sla(process):
    """
    Проверка SLA для конкретного процесса
    
    Returns:
        tuple: (violation_created, warning_sent)
    """
    violation_created = False
    warning_sent = False
    
    sla_status = process.get_sla_status()
    now = timezone.now()
    
    # Проверяем, есть ли уже активные нарушения
    existing_violation = process.sla_violations.filter(status='active').first()
    
    if sla_status == 'overdue':
        # Процесс просрочен
        if not existing_violation or existing_violation.violation_type != 'overdue':
            # Создаем или обновляем нарушение
            if existing_violation:
                existing_violation.violation_type = 'overdue'
                existing_violation.message = f"Процесс просрочен на {process.get_time_remaining()}"
                existing_violation.save()
            else:
                WorkflowSLAViolation.objects.create(
                    process=process,
                    violation_type='overdue',
                    message=f"Процесс просрочен. Deadline: {process.sla_deadline}",
                    created_by=process.current_assignee or process.initiator,
                    updated_by=process.current_assignee or process.initiator
                )
                violation_created = True
            
            # Автоматическая эскалация при просрочке
            escalate_overdue_process.delay(process.id)
            warning_sent = True
    
    elif sla_status == 'critical':
        # Критическое состояние (остается мало времени)
        if not existing_violation or existing_violation.violation_type == 'warning':
            # Обновляем или создаем критическое нарушение
            if existing_violation:
                existing_violation.violation_type = 'critical'
                existing_violation.message = f"Критическое состояние SLA. Остается: {process.get_time_remaining()}"
                existing_violation.save()
            else:
                WorkflowSLAViolation.objects.create(
                    process=process,
                    violation_type='critical',
                    message=f"Критическое состояние SLA. Deadline: {process.sla_deadline}",
                    created_by=process.current_assignee or process.initiator,
                    updated_by=process.current_assignee or process.initiator
                )
                violation_created = True
            
            # Отправляем критическое уведомление
            send_sla_warning.delay(process.id, 'critical')
            warning_sent = True
    
    elif sla_status == 'warning':
        # Предупреждение (остается 50% времени)
        if not existing_violation:
            # Создаем предупреждение
            WorkflowSLAViolation.objects.create(
                process=process,
                violation_type='warning',
                message=f"Предупреждение SLA. Остается: {process.get_time_remaining()}",
                created_by=process.current_assignee or process.initiator,
                updated_by=process.current_assignee or process.initiator
            )
            violation_created = True
            
            # Отправляем предупреждение
            send_sla_warning.delay(process.id, 'warning')
            warning_sent = True
    
    return violation_created, warning_sent


@shared_task(bind=True, max_retries=3)
def escalate_overdue_process(self, process_id):
    """
    Автоматическая эскалация просроченного процесса
    """
    try:
        process = MaterialInspectionProcess.objects.get(id=process_id)
        
        # Повышаем приоритет процесса
        old_priority = process.priority
        process.escalate(
            reason="Автоматическая эскалация из-за просрочки SLA",
            escalated_by=process.current_assignee or process.initiator
        )
        
        # Логируем эскалацию
        WorkflowTaskLog.log_task_action(
            process=process,
            task_name="Automatic Escalation",
            task_id="auto_escalation",
            action="escalated",
            performer=process.current_assignee or process.initiator,
            comment=f"Автоматическая эскалация: {old_priority} → {process.priority}",
            metadata={
                'escalation_reason': 'SLA overdue',
                'old_priority': old_priority,
                'new_priority': process.priority,
                'overdue_time': str(timezone.now() - process.sla_deadline)
            }
        )
        
        # Уведомляем менеджеров об эскалации
        notify_managers_about_escalation.delay(process_id)
        
        logger.info(f"Процесс {process_id} автоматически эскалирован")
        
        return {'success': True, 'process_id': process_id}
        
    except MaterialInspectionProcess.DoesNotExist:
        logger.error(f"Процесс {process_id} не найден для эскалации")
        return {'success': False, 'error': 'Process not found'}
    except Exception as exc:
        logger.error(f"Ошибка эскалации процесса {process_id}: {exc}")
        self.retry(countdown=60, exc=exc)


@shared_task(bind=True, max_retries=3)
def send_sla_warning(self, process_id, warning_type):
    """
    Отправка предупреждения о нарушении SLA
    """
    try:
        process = MaterialInspectionProcess.objects.get(id=process_id)
        material = process.material_receipt.material
        
        # Формируем сообщение в зависимости от типа предупреждения
        if warning_type == 'critical':
            emoji = "🚨"
            title = "КРИТИЧЕСКОЕ предупреждение SLA"
            urgency = "КРИТИЧЕСКОЕ"
        else:
            emoji = "⚠️"
            title = "Предупреждение SLA"
            urgency = "ПРЕДУПРЕЖДЕНИЕ"
        
        message = (
            f"{emoji} {title}\n"
            f"📋 Процесс: #{process.id}\n"
            f"📦 Материал: {material.material_grade}\n"
            f"🏭 Поставщик: {material.supplier}\n"
            f"⏰ Deadline: {process.sla_deadline.strftime('%d.%m.%Y %H:%M')}\n"
            f"⏱️ Осталось: {process.get_time_remaining()}\n"
            f"👤 Исполнитель: {process.current_assignee.username if process.current_assignee else 'Не назначен'}\n"
            f"📊 Прогресс: {process.progress_percentage}%\n"
            f"🚨 Статус: {urgency}"
        )
        
        # Определяем получателей
        recipients = []
        
        # Текущий исполнитель
        if process.current_assignee:
            recipients.append(process.current_assignee)
        
        # Инициатор процесса
        if process.initiator and process.initiator != process.current_assignee:
            recipients.append(process.initiator)
        
        # Для критических предупреждений добавляем менеджеров
        if warning_type == 'critical':
            from django.contrib.auth.models import Group
            manager_group = Group.objects.filter(name__in=['manager', 'менеджер', 'supervisor']).first()
            if manager_group:
                recipients.extend(manager_group.user_set.filter(is_active=True))
        
        # Убираем дубликаты
        recipients = list(set(recipients))
        
        # Отправляем уведомления (через NotificationService)
        notification_response = NotificationService.send_status_change_notification(
            inspection_id=None,  # SLA уведомление
            old_status='active',
            new_status=f'sla_{warning_type}',
            user=process.current_assignee or process.initiator
        )
        
        # Логируем отправку предупреждения
        WorkflowTaskLog.log_task_action(
            process=process,
            task_name="SLA Warning",
            task_id="sla_warning",
            action="created",
            performer=process.current_assignee or process.initiator,
            comment=f"Отправлено {urgency} предупреждение SLA",
            metadata={
                'warning_type': warning_type,
                'recipients_count': len(recipients),
                'sla_status': process.get_sla_status(),
                'time_remaining': str(process.get_time_remaining())
            }
        )
        
        logger.info(f"Отправлено SLA предупреждение для процесса {process_id}")
        
        return {
            'success': True,
            'process_id': process_id,
            'warning_type': warning_type,
            'recipients_count': len(recipients)
        }
        
    except MaterialInspectionProcess.DoesNotExist:
        logger.error(f"Процесс {process_id} не найден для отправки предупреждения")
        return {'success': False, 'error': 'Process not found'}
    except Exception as exc:
        logger.error(f"Ошибка отправки SLA предупреждения для процесса {process_id}: {exc}")
        self.retry(countdown=60, exc=exc)


@shared_task(bind=True, max_retries=3)
def notify_managers_about_escalation(self, process_id):
    """
    Уведомление менеджеров об эскалации процесса
    """
    try:
        process = MaterialInspectionProcess.objects.get(id=process_id)
        material = process.material_receipt.material
        
        message = (
            f"🚨 ЭСКАЛАЦИЯ ПРОЦЕССА\n"
            f"📋 Процесс: #{process.id}\n"
            f"📦 Материал: {material.material_grade}\n"
            f"🏭 Поставщик: {material.supplier}\n"
            f"⚡ Приоритет: {process.get_priority_display()}\n"
            f"👤 Исполнитель: {process.current_assignee.username if process.current_assignee else 'Не назначен'}\n"
            f"⏰ Просрочка: {timezone.now() - process.sla_deadline if process.sla_deadline else 'N/A'}\n"
            f"📊 Прогресс: {process.progress_percentage}%\n"
            f"🔴 Требуется немедленное внимание!"
        )
        
        # Получаем менеджеров и администраторов
        from django.contrib.auth.models import Group
        
        managers = User.objects.filter(
            is_active=True,
            groups__name__in=['manager', 'менеджер', 'supervisor', 'admin']
        ).distinct()
        
        # Добавляем всех администраторов
        admins = User.objects.filter(is_active=True, is_staff=True)
        
        recipients = list(set(list(managers) + list(admins)))
        
        # Логируем уведомление менеджеров
        WorkflowTaskLog.log_task_action(
            process=process,
            task_name="Manager Escalation Notification",
            task_id="manager_notification",
            action="created",
            performer=process.current_assignee or process.initiator,
            comment=f"Уведомление менеджеров об эскалации отправлено {len(recipients)} получателям",
            metadata={
                'escalation_reason': 'SLA overdue',
                'recipients_count': len(recipients),
                'manager_usernames': [u.username for u in recipients]
            }
        )
        
        logger.info(f"Менеджеры уведомлены об эскалации процесса {process_id}")
        
        return {
            'success': True,
            'process_id': process_id,
            'recipients_count': len(recipients)
        }
        
    except MaterialInspectionProcess.DoesNotExist:
        logger.error(f"Процесс {process_id} не найден для уведомления менеджеров")
        return {'success': False, 'error': 'Process not found'}
    except Exception as exc:
        logger.error(f"Ошибка уведомления менеджеров для процесса {process_id}: {exc}")
        self.retry(countdown=60, exc=exc)


@shared_task(bind=True)
def cleanup_old_sla_violations(self):
    """
    Очистка старых разрешенных нарушений SLA (старше 30 дней)
    Запускается раз в день
    """
    try:
        cutoff_date = timezone.now() - timedelta(days=30)
        
        old_violations = WorkflowSLAViolation.objects.filter(
            status='resolved',
            resolved_at__lt=cutoff_date
        )
        
        count = old_violations.count()
        old_violations.delete()
        
        logger.info(f"Удалено {count} старых нарушений SLA")
        
        return {'success': True, 'deleted_count': count}
        
    except Exception as exc:
        logger.error(f"Ошибка очистки старых нарушений SLA: {exc}")
        return {'success': False, 'error': str(exc)}


@shared_task(bind=True)
def generate_sla_report(self):
    """
    Генерация ежедневного отчета по SLA
    """
    try:
        now = timezone.now()
        yesterday = now - timedelta(days=1)
        
        # Статистика за вчера
        processes_completed = MaterialInspectionProcess.objects.filter(
            completed_at__date=yesterday.date(),
            status=MaterialInspectionProcess.STATUS.COMPLETED
        )
        
        processes_overdue = MaterialInspectionProcess.objects.filter(
            sla_deadline__lt=now,
            status=MaterialInspectionProcess.STATUS.ACTIVE
        )
        
        violations_created = WorkflowSLAViolation.objects.filter(
            detected_at__date=yesterday.date()
        )
        
        # Статистика по приоритетам
        priority_stats = {}
        for priority, _ in MaterialInspectionProcess.PRIORITY_CHOICES.choices:
            priority_stats[priority] = {
                'completed': processes_completed.filter(priority=priority).count(),
                'overdue': processes_overdue.filter(priority=priority).count(),
            }
        
        report_data = {
            'date': yesterday.date().isoformat(),
            'completed_processes': processes_completed.count(),
            'overdue_processes': processes_overdue.count(),
            'violations_created': violations_created.count(),
            'priority_breakdown': priority_stats,
            'average_completion_time': None,  # TODO: вычислить среднее время
        }
        
        # Вычисляем среднее время завершения
        completed_durations = []
        for process in processes_completed:
            if process.started_at and process.completed_at:
                duration = process.completed_at - process.started_at
                completed_durations.append(duration.total_seconds())
        
        if completed_durations:
            avg_seconds = sum(completed_durations) / len(completed_durations)
            report_data['average_completion_time'] = str(timedelta(seconds=avg_seconds))
        
        logger.info(f"Сгенерирован SLA отчет за {yesterday.date()}")
        
        return {
            'success': True,
            'report_date': yesterday.date().isoformat(),
            'report_data': report_data
        }
        
    except Exception as exc:
        logger.error(f"Ошибка генерации SLA отчета: {exc}")
        return {'success': False, 'error': str(exc)}


# Периодические задачи для Celery Beat
# Добавить в настройки:
CELERY_BEAT_SCHEDULE = {
    'monitor-sla-violations': {
        'task': 'apps.workflow.tasks.monitor_sla_violations',
        'schedule': 900.0,  # Каждые 15 минут
    },
    'cleanup-old-sla-violations': {
        'task': 'apps.workflow.tasks.cleanup_old_sla_violations',
        'schedule': 86400.0,  # Раз в день
    },
    'generate-sla-report': {
        'task': 'apps.workflow.tasks.generate_sla_report',
        'schedule': 86400.0,  # Раз в день в 01:00
        'options': {'eta': timezone.now().replace(hour=1, minute=0, second=0, microsecond=0)}
    },
}