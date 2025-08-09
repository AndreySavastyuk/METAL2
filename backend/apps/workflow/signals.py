"""
Django сигналы для автоматической активации workflow
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.utils import timezone
import logging

from apps.warehouse.models import MaterialReceipt
from .models import MaterialInspectionProcess, WorkflowTaskLog
from .flows import MaterialInspectionFlow
from apps.warehouse.services import MaterialInspectionService

logger = logging.getLogger(__name__)


@receiver(post_save, sender=MaterialReceipt)
def auto_start_workflow_on_material_receipt(sender, instance, created, **kwargs):
    """
    Автоматическое создание и запуск workflow при создании приемки материала
    """
    
    # Запускаем workflow только для новых приемок
    if not created:
        return
    
    # Проверяем, что приемка не имеет связанного процесса
    if hasattr(instance, 'inspection_process'):
        logger.warning(f"Приемка {instance.id} уже имеет связанный процесс workflow")
        return
    
    try:
        logger.info(f"Создание workflow процесса для приемки {instance.id}")
        
        # Определяем приоритет на основе материала
        priority = determine_process_priority(instance)
        
        # Определяем требования ППСД/УЗК
        requires_ppsd, requires_ultrasonic = determine_testing_requirements(instance)
        
        # Создаем процесс workflow
        process = MaterialInspectionProcess.objects.create(
            material_receipt=instance,
            initiator=instance.received_by,
            current_assignee=instance.received_by,
            priority=priority,
            requires_ppsd=requires_ppsd,
            requires_ultrasonic=requires_ultrasonic,
            comments=f"Процесс создан автоматически при поступлении материала {instance.material.material_grade}",
            created_by=instance.received_by,
            updated_by=instance.received_by
        )
        
        # Запускаем workflow процесс
        flow = MaterialInspectionFlow()
        
        # Создаем процесс в viewflow
        activation = flow.start.activate()
        activation.prepare(process)
        activation.execute()
        
        # Логируем создание процесса
        WorkflowTaskLog.log_task_action(
            process=process,
            task_name="Process Creation",
            task_id="process_creation",
            action="created",
            performer=instance.received_by,
            comment=f"Workflow процесс создан автоматически для материала {instance.material.material_grade}",
            metadata={
                'material_id': instance.material.id,
                'material_grade': instance.material.material_grade,
                'supplier': instance.material.supplier,
                'priority': priority,
                'requires_ppsd': requires_ppsd,
                'requires_ultrasonic': requires_ultrasonic,
                'auto_created': True
            }
        )
        
        logger.info(f"Workflow процесс {process.id} успешно создан для приемки {instance.id}")
        
    except Exception as e:
        logger.error(f"Ошибка создания workflow процесса для приемки {instance.id}: {e}")
        import traceback
        traceback.print_exc()


def determine_process_priority(material_receipt):
    """
    Определение приоритета процесса на основе материала и других факторов
    """
    material = material_receipt.material
    
    # Критические материалы (нержавеющие стали)
    critical_grades = ['12X18H10T', '08X18H10T', '10X17H13M2T', '03X17H14M3']
    if material.material_grade in critical_grades:
        return MaterialInspectionProcess.PRIORITY_CHOICES.HIGH
    
    # Срочные поставки (по размеру заказа)
    if material.quantity >= 1000:  # Большие партии
        return MaterialInspectionProcess.PRIORITY_CHOICES.HIGH
    
    # Специальные поставщики
    priority_suppliers = ['СпецСталь', 'ПремиумМетал']
    if material.supplier in priority_suppliers:
        return MaterialInspectionProcess.PRIORITY_CHOICES.HIGH
    
    # Обычный приоритет по умолчанию
    return MaterialInspectionProcess.PRIORITY_CHOICES.NORMAL


def determine_testing_requirements(material_receipt):
    """
    Определение требований к испытаниям (ППСД/УЗК)
    """
    material = material_receipt.material
    
    # Проверяем ППСД
    ppsd_response = MaterialInspectionService.check_ppsd_requirement(
        material.material_grade, material.size
    )
    requires_ppsd = ppsd_response.success and ppsd_response.data.get('requires_ppsd', False)
    
    # Проверяем УЗК
    ultrasonic_response = MaterialInspectionService.check_ultrasonic_requirement(
        material.material_grade, material.size
    )
    requires_ultrasonic = (
        ultrasonic_response.success and 
        ultrasonic_response.data.get('requires_ultrasonic', False)
    )
    
    return requires_ppsd, requires_ultrasonic


@receiver(pre_save, sender=MaterialReceipt)
def check_status_transition_for_workflow(sender, instance, **kwargs):
    """
    Проверка изменения статуса приемки для синхронизации с workflow
    """
    
    if not instance.pk:
        return  # Новый объект, ничего не делаем
    
    try:
        # Получаем старое состояние
        old_instance = MaterialReceipt.objects.get(pk=instance.pk)
        
        # Проверяем изменение статуса
        if old_instance.status != instance.status:
            logger.info(f"Изменение статуса приемки {instance.id}: {old_instance.status} → {instance.status}")
            
            # Если есть связанный процесс workflow
            if hasattr(instance, 'inspection_process'):
                process = instance.inspection_process
                
                # Логируем изменение статуса
                WorkflowTaskLog.log_task_action(
                    process=process,
                    task_name="Receipt Status Change",
                    task_id="receipt_status_change",
                    action="completed",
                    performer=instance.updated_by or instance.received_by,
                    comment=f"Статус приемки изменен: {old_instance.status} → {instance.status}",
                    metadata={
                        'old_status': old_instance.status,
                        'new_status': instance.status,
                        'material_grade': instance.material.material_grade
                    }
                )
                
                # Обновляем процесс при завершении приемки
                if instance.status == 'approved' and process.status == MaterialInspectionProcess.STATUS.ACTIVE:
                    # Проверяем готовность к завершению процесса
                    check_process_completion.delay(process.id)
    
    except MaterialReceipt.DoesNotExist:
        logger.warning(f"Не удалось найти старое состояние приемки {instance.id}")
    except Exception as e:
        logger.error(f"Ошибка при проверке изменения статуса приемки {instance.id}: {e}")


# Celery задача для проверки готовности завершения процесса
from celery import shared_task

@shared_task(bind=True)
def check_process_completion(self, process_id):
    """
    Проверка готовности процесса к завершению
    """
    try:
        process = MaterialInspectionProcess.objects.get(id=process_id)
        
        # Проверяем все условия для завершения
        material_receipt = process.material_receipt
        
        # Условия завершения:
        # 1. Приемка одобрена
        # 2. Все необходимые испытания завершены
        # 3. Нет активных критических задач
        
        can_complete = True
        completion_blockers = []
        
        # Проверка 1: Статус приемки
        if material_receipt.status != 'approved':
            can_complete = False
            completion_blockers.append(f"Приемка не одобрена (статус: {material_receipt.status})")
        
        # Проверка 2: ППСД испытания (если требуются)
        if process.requires_ppsd:
            from apps.laboratory.models import LabTestRequest
            
            ppsd_tests = LabTestRequest.objects.filter(
                material_receipt=material_receipt,
                test_type__in=['chemical_analysis', 'mechanical_properties']
            )
            
            incomplete_ppsd = ppsd_tests.exclude(status='completed')
            if incomplete_ppsd.exists():
                can_complete = False
                completion_blockers.append(f"Незавершенные ППСД испытания: {incomplete_ppsd.count()}")
        
        # Проверка 3: УЗК испытания (если требуются)
        if process.requires_ultrasonic:
            from apps.laboratory.models import LabTestRequest
            
            ultrasonic_tests = LabTestRequest.objects.filter(
                material_receipt=material_receipt,
                test_type='ultrasonic'
            )
            
            incomplete_ultrasonic = ultrasonic_tests.exclude(status='completed')
            if incomplete_ultrasonic.exists():
                can_complete = False
                completion_blockers.append(f"Незавершенные УЗК испытания: {incomplete_ultrasonic.count()}")
        
        # Логируем проверку
        WorkflowTaskLog.log_task_action(
            process=process,
            task_name="Completion Check",
            task_id="completion_check",
            action="completed",
            performer=process.current_assignee or process.initiator,
            comment=f"Проверка готовности к завершению: {'готов' if can_complete else 'не готов'}",
            metadata={
                'can_complete': can_complete,
                'completion_blockers': completion_blockers,
                'progress_percentage': str(process.progress_percentage)
            }
        )
        
        # Если готов к завершению - завершаем процесс
        if can_complete:
            process.complete(process.current_assignee or process.initiator)
            logger.info(f"Процесс {process_id} автоматически завершен")
        else:
            logger.info(f"Процесс {process_id} не готов к завершению: {', '.join(completion_blockers)}")
        
        return {
            'success': True,
            'process_id': process_id,
            'can_complete': can_complete,
            'completion_blockers': completion_blockers
        }
        
    except MaterialInspectionProcess.DoesNotExist:
        logger.error(f"Процесс {process_id} не найден")
        return {'success': False, 'error': 'Process not found'}
    except Exception as exc:
        logger.error(f"Ошибка проверки завершения процесса {process_id}: {exc}")
        return {'success': False, 'error': str(exc)}


# Сигнал для создания Celery app при импорте
def setup_workflow_signals():
    """
    Настройка сигналов workflow
    Вызывается при инициализации приложения
    """
    logger.info("Workflow сигналы настроены")


# Дополнительные сигналы для интеграции с другими модулями

@receiver(post_save, sender='quality.QCInspection')
def sync_qc_inspection_with_workflow(sender, instance, created, **kwargs):
    """
    Синхронизация инспекции ОТК с workflow процессом
    """
    try:
        # Находим связанный процесс workflow
        material_receipt = instance.material_receipt
        
        if hasattr(material_receipt, 'inspection_process'):
            process = material_receipt.inspection_process
            
            # Обновляем требования в процессе
            if process.requires_ppsd != instance.requires_ppsd or \
               process.requires_ultrasonic != instance.requires_ultrasonic:
                
                process.requires_ppsd = instance.requires_ppsd
                process.requires_ultrasonic = instance.requires_ultrasonic
                process.save()
                
                # Логируем синхронизацию
                WorkflowTaskLog.log_task_action(
                    process=process,
                    task_name="QC Sync",
                    task_id="qc_sync",
                    action="completed",
                    performer=instance.updated_by or instance.inspector,
                    comment=f"Синхронизация с ОТК: ППСД={instance.requires_ppsd}, УЗК={instance.requires_ultrasonic}",
                    metadata={
                        'qc_inspection_id': instance.id,
                        'requires_ppsd': instance.requires_ppsd,
                        'requires_ultrasonic': instance.requires_ultrasonic
                    }
                )
                
                logger.info(f"Процесс {process.id} синхронизирован с инспекцией ОТК {instance.id}")
    
    except Exception as e:
        logger.error(f"Ошибка синхронизации инспекции ОТК {instance.id} с workflow: {e}")


@receiver(post_save, sender='laboratory.LabTestRequest')
def sync_lab_request_with_workflow(sender, instance, created, **kwargs):
    """
    Синхронизация лабораторных заявок с workflow процессом
    """
    try:
        # Находим связанный процесс workflow
        material_receipt = instance.material_receipt
        
        if hasattr(material_receipt, 'inspection_process'):
            process = material_receipt.inspection_process
            
            # Проверяем изменение статуса лабораторной заявки
            if not created and instance.status == 'completed':
                # Проверяем готовность к завершению процесса
                check_process_completion.delay(process.id)
                
                # Логируем завершение лабораторного испытания
                WorkflowTaskLog.log_task_action(
                    process=process,
                    task_name="Lab Test Completed",
                    task_id="lab_test_completed",
                    action="completed",
                    performer=instance.updated_by,
                    comment=f"Завершено лабораторное испытание: {instance.get_test_type_display()}",
                    metadata={
                        'lab_request_id': instance.id,
                        'test_type': instance.test_type,
                        'internal_testing': instance.internal_testing
                    }
                )
                
                logger.info(f"Лабораторное испытание {instance.id} завершено для процесса {process.id}")
    
    except Exception as e:
        logger.error(f"Ошибка синхронизации лабораторной заявки {instance.id} с workflow: {e}")