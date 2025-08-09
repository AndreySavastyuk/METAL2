"""
Service layer для модуля склада
Содержит бизнес-логику и интеграции между модулями
"""
import logging
from decimal import Decimal
from django.db import transaction
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from typing import Dict, Any, Optional, List

from .models import Material, MaterialReceipt, Certificate
from apps.quality.models import QCInspection, QCChecklist
from apps.laboratory.models import LabTestRequest

logger = logging.getLogger(__name__)


class ServiceResponse:
    """Стандартизированный формат ответа сервисов"""
    
    def __init__(self, success: bool = True, data: Any = None, 
                 error: str = None, warnings: List[str] = None):
        self.success = success
        self.data = data or {}
        self.error = error
        self.warnings = warnings or []
        self.timestamp = timezone.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Конверсия в словарь для JSON ответов"""
        return {
            'success': self.success,
            'data': self.data,
            'error': self.error,
            'warnings': self.warnings,
            'timestamp': self.timestamp.isoformat()
        }
    
    @classmethod
    def success_response(cls, data: Any = None, warnings: List[str] = None):
        """Создание успешного ответа"""
        return cls(success=True, data=data, warnings=warnings)
    
    @classmethod 
    def error_response(cls, error: str, data: Any = None):
        """Создание ответа с ошибкой"""
        return cls(success=False, error=error, data=data)


class MaterialInspectionService:
    """
    Сервис для управления workflow инспекции материалов.
    Координирует взаимодействие между складом, ОТК и лабораторией.
    """
    
    # Матрица требований ультразвукового контроля
    ULTRASONIC_REQUIREMENTS = {
        # Для круглого проката
        'круглый': {
            'диаметр_мм': {
                (50, 100): ['40X', '20X13', '12X18H10T'],
                (100, 200): ['40X', '20X13', '12X18H10T', '09Г2С'],
                (200, 500): 'all'  # Все марки
            }
        },
        # Для листового проката
        'лист': {
            'толщина_мм': {
                (10, 20): ['40X', '20X13'],
                (20, 50): ['40X', '20X13', '12X18H10T'],
                (50, 100): 'all'
            }
        }
    }
    
    # Материалы требующие ППСД
    PPSD_REQUIRED_GRADES = [
        '12X18H10T', '08X18H10T', '10X17H13M2T', 
        '03X17H14M3', '20X13', '40X13'
    ]
    
    @staticmethod
    def _parse_size(size: str) -> Dict[str, Any]:
        """Парсинг размера материала"""
        size = size.lower().strip()
        
        # Круглый прокат: ⌀50, d50, диаметр 50
        if '⌀' in size or size.startswith('d') or 'диаметр' in size:
            import re
            match = re.search(r'(\d+)', size)
            if match:
                diameter = int(match.group(1))
                return {'type': 'круглый', 'diameter': diameter}
        
        # Листовой прокат: лист 10мм, 10x1000x2000
        elif 'лист' in size or 'x' in size:
            import re
            match = re.search(r'(\d+)', size)
            if match:
                thickness = int(match.group(1))
                return {'type': 'лист', 'thickness': thickness}
        
        return {'type': 'unknown', 'raw': size}
    
    @classmethod
    def check_ppsd_requirement(cls, material_grade: str, size: str = None) -> ServiceResponse:
        """
        Проверка требования ППСД для материала
        
        Args:
            material_grade: Марка материала
            size: Размер материала (опционально)
            
        Returns:
            ServiceResponse с результатом проверки
        """
        try:
            logger.info(f"Проверка ППСД для материала {material_grade}, размер: {size}")
            
            # Базовая проверка по марке
            requires_ppsd = material_grade.upper() in [grade.upper() for grade in cls.PPSD_REQUIRED_GRADES]
            
            reasons = []
            if requires_ppsd:
                reasons.append(f"Марка {material_grade} входит в список материалов, требующих ППСД")
            
            # Дополнительные проверки по размеру (если указан)
            if size:
                size_info = cls._parse_size(size)
                
                # Для больших размеров может потребоваться ППСД
                if size_info['type'] == 'круглый' and size_info.get('diameter', 0) > 200:
                    requires_ppsd = True
                    reasons.append(f"Большой диаметр ({size_info['diameter']}мм) требует ППСД")
                elif size_info['type'] == 'лист' and size_info.get('thickness', 0) > 50:
                    requires_ppsd = True
                    reasons.append(f"Большая толщина листа ({size_info['thickness']}мм) требует ППСД")
            
            return ServiceResponse.success_response({
                'requires_ppsd': requires_ppsd,
                'material_grade': material_grade,
                'size': size,
                'reasons': reasons
            })
            
        except Exception as e:
            logger.error(f"Ошибка при проверке ППСД: {e}")
            return ServiceResponse.error_response(f"Ошибка проверки ППСД: {str(e)}")
    
    @classmethod
    def check_ultrasonic_requirement(cls, material_grade: str, size: str) -> ServiceResponse:
        """
        Проверка требования ультразвукового контроля
        
        Args:
            material_grade: Марка материала
            size: Размер материала
            
        Returns:
            ServiceResponse с результатом проверки
        """
        try:
            logger.info(f"Проверка УЗК для материала {material_grade}, размер: {size}")
            
            size_info = cls._parse_size(size)
            requires_ultrasonic = False
            reasons = []
            
            if size_info['type'] == 'круглый':
                diameter = size_info.get('diameter', 0)
                
                for (min_d, max_d), grades in cls.ULTRASONIC_REQUIREMENTS['круглый']['диаметр_мм'].items():
                    if min_d <= diameter < max_d:
                        if grades == 'all' or material_grade.upper() in [g.upper() for g in grades]:
                            requires_ultrasonic = True
                            reasons.append(f"Диаметр {diameter}мм и марка {material_grade} требуют УЗК")
                        break
                        
            elif size_info['type'] == 'лист':
                thickness = size_info.get('thickness', 0)
                
                for (min_t, max_t), grades in cls.ULTRASONIC_REQUIREMENTS['лист']['толщина_мм'].items():
                    if min_t <= thickness < max_t:
                        if grades == 'all' or material_grade.upper() in [g.upper() for g in grades]:
                            requires_ultrasonic = True
                            reasons.append(f"Толщина {thickness}мм и марка {material_grade} требуют УЗК")
                        break
            
            return ServiceResponse.success_response({
                'requires_ultrasonic': requires_ultrasonic,
                'material_grade': material_grade,
                'size': size,
                'size_info': size_info,
                'reasons': reasons
            })
            
        except Exception as e:
            logger.error(f"Ошибка при проверке УЗК: {e}")
            return ServiceResponse.error_response(f"Ошибка проверки УЗК: {str(e)}")
    
    @classmethod
    @transaction.atomic
    def create_inspection(cls, material_receipt_id: int, inspector_id: int, 
                         auto_assign: bool = True) -> ServiceResponse:
        """
        Создание инспекции ОТК для приемки материала
        
        Args:
            material_receipt_id: ID приемки материала
            inspector_id: ID инспектора
            auto_assign: Автоматическое назначение на основе бизнес-правил
            
        Returns:
            ServiceResponse с созданной инспекцией
        """
        try:
            logger.info(f"Создание инспекции для приемки {material_receipt_id}, инспектор {inspector_id}")
            
            # Получаем приемку и материал
            try:
                receipt = MaterialReceipt.objects.select_related('material').get(id=material_receipt_id)
                inspector = User.objects.get(id=inspector_id)
            except MaterialReceipt.DoesNotExist:
                return ServiceResponse.error_response(f"Приемка с ID {material_receipt_id} не найдена")
            except User.DoesNotExist:
                return ServiceResponse.error_response(f"Инспектор с ID {inspector_id} не найден")
            
            # Проверяем, что инспекция еще не создана
            existing_inspection = QCInspection.objects.filter(material_receipt=receipt).first()
            if existing_inspection:
                return ServiceResponse.error_response(
                    f"Инспекция уже существует (ID: {existing_inspection.id})",
                    data={'existing_inspection_id': existing_inspection.id}
                )
            
            material = receipt.material
            warnings = []
            
            # Автоматическая проверка требований
            requires_ppsd = False
            requires_ultrasonic = False
            
            if auto_assign:
                # Проверка ППСД
                ppsd_check = cls.check_ppsd_requirement(material.material_grade, material.size)
                if ppsd_check.success:
                    requires_ppsd = ppsd_check.data.get('requires_ppsd', False)
                    if ppsd_check.data.get('reasons'):
                        warnings.extend(ppsd_check.data['reasons'])
                
                # Проверка УЗК
                ultrasonic_check = cls.check_ultrasonic_requirement(material.material_grade, material.size)
                if ultrasonic_check.success:
                    requires_ultrasonic = ultrasonic_check.data.get('requires_ultrasonic', False)
                    if ultrasonic_check.data.get('reasons'):
                        warnings.extend(ultrasonic_check.data['reasons'])
            
            # Создаем инспекцию
            inspection = QCInspection.objects.create(
                material_receipt=receipt,
                inspector=inspector,
                status='draft',
                requires_ppsd=requires_ppsd,
                requires_ultrasonic=requires_ultrasonic,
                comments=f"Инспекция создана автоматически. {'; '.join(warnings) if warnings else ''}",
                created_by=inspector,
                updated_by=inspector
            )
            
            # Обновляем статус приемки
            receipt.status = 'in_qc'
            receipt.updated_by = inspector
            receipt.save()
            
            logger.info(f"Инспекция {inspection.id} создана успешно")
            
            return ServiceResponse.success_response({
                'inspection_id': inspection.id,
                'material_receipt_id': receipt.id,
                'material_grade': material.material_grade,
                'requires_ppsd': requires_ppsd,
                'requires_ultrasonic': requires_ultrasonic,
                'status': inspection.status,
                'created_at': inspection.created_at,
                'inspector': {
                    'id': inspector.id,
                    'username': inspector.username,
                    'full_name': inspector.get_full_name()
                }
            }, warnings=warnings)
            
        except Exception as e:
            logger.error(f"Ошибка при создании инспекции: {e}")
            return ServiceResponse.error_response(f"Ошибка создания инспекции: {str(e)}")
    
    @classmethod
    @transaction.atomic
    def transition_status(cls, inspection_id: int, new_status: str, 
                         user: User, comment: str = "") -> ServiceResponse:
        """
        Переход статуса инспекции с валидацией бизнес-правил
        
        Args:
            inspection_id: ID инспекции
            new_status: Новый статус
            user: Пользователь, выполняющий переход
            comment: Комментарий к переходу
            
        Returns:
            ServiceResponse с результатом перехода
        """
        try:
            logger.info(f"Переход статуса инспекции {inspection_id} в {new_status}, пользователь {user.username}")
            
            # Получаем инспекцию
            try:
                inspection = QCInspection.objects.select_related(
                    'material_receipt__material', 'inspector'
                ).get(id=inspection_id)
            except QCInspection.DoesNotExist:
                return ServiceResponse.error_response(f"Инспекция с ID {inspection_id} не найдена")
            
            # Валидные переходы статусов
            valid_transitions = {
                'draft': ['in_progress', 'cancelled'],
                'in_progress': ['completed', 'rejected', 'draft'],
                'completed': ['rejected'],  # Можно только отклонить
                'rejected': ['draft'],      # Можно вернуть в черновик
                'cancelled': ['draft']      # Можно возобновить
            }
            
            current_status = inspection.status
            allowed_statuses = valid_transitions.get(current_status, [])
            
            if new_status not in allowed_statuses:
                return ServiceResponse.error_response(
                    f"Недопустимый переход из статуса '{current_status}' в '{new_status}'",
                    data={
                        'current_status': current_status,
                        'allowed_transitions': allowed_statuses
                    }
                )
            
            # Дополнительные проверки для завершения
            warnings = []
            if new_status == 'completed':
                # Проверяем критические пункты чек-листа
                critical_failures = inspection.get_critical_failures()
                if critical_failures:
                    return ServiceResponse.error_response(
                        "Нельзя завершить инспекцию с невыполненными критическими пунктами",
                        data={'critical_failures': [str(item) for item in critical_failures]}
                    )
                
                # Проверяем процент выполнения
                completion_percentage = inspection.get_completion_percentage()
                if completion_percentage < 100:
                    warnings.append(f"Инспекция завершена с {completion_percentage}% выполнения")
                
                # Автоматическое назначение в лабораторию если нужно
                if inspection.requires_ppsd or inspection.requires_ultrasonic:
                    lab_response = cls.assign_to_laboratory(inspection_id)
                    if lab_response.success:
                        warnings.append("Автоматически назначены лабораторные испытания")
                    else:
                        warnings.append(f"Не удалось назначить лабораторные испытания: {lab_response.error}")
            
            # Выполняем переход
            old_status = inspection.status
            inspection.status = new_status
            inspection.updated_by = user
            
            if new_status == 'completed':
                inspection.completion_date = timezone.now()
            
            # Добавляем комментарий
            timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            transition_comment = f"[{timestamp}] {user.username}: {old_status} → {new_status}"
            if comment:
                transition_comment += f" ({comment})"
            
            current_comments = inspection.comments or ""
            inspection.comments = f"{current_comments}\n{transition_comment}" if current_comments else transition_comment
            
            inspection.save()
            
            # Обновляем статус приемки
            receipt_status_map = {
                'completed': 'approved',
                'rejected': 'rejected',
                'in_progress': 'in_qc'
            }
            
            if new_status in receipt_status_map:
                inspection.material_receipt.status = receipt_status_map[new_status]
                inspection.material_receipt.updated_by = user
                inspection.material_receipt.save()
            
            logger.info(f"Статус инспекции {inspection_id} изменен: {old_status} → {new_status}")
            
            return ServiceResponse.success_response({
                'inspection_id': inspection.id,
                'transition': {
                    'from': old_status,
                    'to': new_status,
                    'performed_by': user.username,
                    'performed_at': timezone.now(),
                    'comment': comment
                },
                'material_receipt_status': inspection.material_receipt.status,
                'completion_percentage': inspection.get_completion_percentage(),
                'next_possible_transitions': valid_transitions.get(new_status, [])
            }, warnings=warnings)
            
        except Exception as e:
            logger.error(f"Ошибка при переходе статуса инспекции: {e}")
            return ServiceResponse.error_response(f"Ошибка перехода статуса: {str(e)}")
    
    @classmethod
    @transaction.atomic
    def assign_to_laboratory(cls, inspection_id: int) -> ServiceResponse:
        """
        Назначение материала в лабораторию для дополнительных испытаний
        
        Args:
            inspection_id: ID инспекции ОТК
            
        Returns:
            ServiceResponse с созданными заявками в лабораторию
        """
        try:
            logger.info(f"Назначение в лабораторию для инспекции {inspection_id}")
            
            # Получаем инспекцию
            try:
                inspection = QCInspection.objects.select_related(
                    'material_receipt__material', 'inspector'
                ).get(id=inspection_id)
            except QCInspection.DoesNotExist:
                return ServiceResponse.error_response(f"Инспекция с ID {inspection_id} не найдена")
            
            material_receipt = inspection.material_receipt
            created_requests = []
            
            # Создаем заявки на испытания
            if inspection.requires_ppsd:
                # Химический анализ для ППСД
                chem_request = LabTestRequest.objects.create(
                    material_receipt=material_receipt,
                    requested_by=inspection.inspector,
                    test_type='chemical_analysis',
                    priority='normal',
                    status='pending',
                    internal_testing=True,
                    test_requirements='ППСД - полный химический анализ согласно ГОСТ',
                    comments=f'Заявка создана автоматически для инспекции {inspection_id}',
                    created_by=inspection.inspector,
                    updated_by=inspection.inspector
                )
                created_requests.append({
                    'id': chem_request.id,
                    'type': 'chemical_analysis',
                    'reason': 'ППСД требование'
                })
                
                # Механические испытания для ППСД
                mech_request = LabTestRequest.objects.create(
                    material_receipt=material_receipt,
                    requested_by=inspection.inspector,
                    test_type='mechanical_properties',
                    priority='normal',
                    status='pending',
                    internal_testing=True,
                    test_requirements='ППСД - механические свойства согласно ГОСТ',
                    comments=f'Заявка создана автоматически для инспекции {inspection_id}',
                    created_by=inspection.inspector,
                    updated_by=inspection.inspector
                )
                created_requests.append({
                    'id': mech_request.id,
                    'type': 'mechanical_properties',
                    'reason': 'ППСД требование'
                })
            
            if inspection.requires_ultrasonic:
                # Ультразвуковой контроль
                ut_request = LabTestRequest.objects.create(
                    material_receipt=material_receipt,
                    requested_by=inspection.inspector,
                    test_type='ultrasonic',
                    priority='normal',
                    status='pending',
                    internal_testing=True,
                    test_requirements='УЗК согласно ГОСТ 14782',
                    comments=f'Заявка создана автоматически для инспекции {inspection_id}',
                    created_by=inspection.inspector,
                    updated_by=inspection.inspector
                )
                created_requests.append({
                    'id': ut_request.id,
                    'type': 'ultrasonic',
                    'reason': 'Требование УЗК по размеру/марке'
                })
            
            if not created_requests:
                return ServiceResponse.success_response({
                    'inspection_id': inspection_id,
                    'message': 'Дополнительные лабораторные испытания не требуются',
                    'requires_ppsd': inspection.requires_ppsd,
                    'requires_ultrasonic': inspection.requires_ultrasonic
                })
            
            logger.info(f"Создано {len(created_requests)} заявок в лабораторию для инспекции {inspection_id}")
            
            return ServiceResponse.success_response({
                'inspection_id': inspection_id,
                'material_receipt_id': material_receipt.id,
                'created_requests': created_requests,
                'total_requests': len(created_requests),
                'message': f'Созданы заявки на {len(created_requests)} типов испытаний'
            })
            
        except Exception as e:
            logger.error(f"Ошибка при назначении в лабораторию: {e}")
            return ServiceResponse.error_response(f"Ошибка назначения в лабораторию: {str(e)}")


class MaterialService:
    """Дополнительные сервисы для работы с материалами"""
    
    @classmethod
    @transaction.atomic
    def process_material_receipt(cls, material_id: int, received_by: User, 
                               document_number: str, auto_create_qc: bool = True) -> ServiceResponse:
        """
        Обработка поступления материала с автоматическим созданием инспекции ОТК
        
        Args:
            material_id: ID материала
            received_by: Пользователь, принявший материал
            document_number: Номер документа поступления
            auto_create_qc: Автоматически создать инспекцию ОТК
            
        Returns:
            ServiceResponse с созданной приемкой и инспекцией
        """
        try:
            logger.info(f"Обработка поступления материала {material_id}")
            
            # Получаем материал
            try:
                material = Material.objects.get(id=material_id, is_deleted=False)
            except Material.DoesNotExist:
                return ServiceResponse.error_response(f"Материал с ID {material_id} не найден")
            
            # Создаем приемку
            receipt = MaterialReceipt.objects.create(
                material=material,
                received_by=received_by,
                document_number=document_number,
                status='pending_qc',
                notes=f'Приемка создана автоматически пользователем {received_by.username}',
                created_by=received_by,
                updated_by=received_by
            )
            
            result_data = {
                'receipt_id': receipt.id,
                'material_id': material.id,
                'material_grade': material.material_grade,
                'status': receipt.status,
                'document_number': document_number
            }
            
            # Автоматическое создание инспекции ОТК
            if auto_create_qc:
                # Ищем доступного инспектора ОТК
                from django.contrib.auth.models import Group
                qc_group = Group.objects.filter(name__in=['qc', 'quality_control']).first()
                
                if qc_group:
                    qc_inspector = qc_group.user_set.filter(is_active=True).first()
                    
                    if qc_inspector:
                        inspection_response = MaterialInspectionService.create_inspection(
                            receipt.id, qc_inspector.id, auto_assign=True
                        )
                        
                        if inspection_response.success:
                            result_data['qc_inspection'] = inspection_response.data
                            result_data['auto_assigned_inspector'] = qc_inspector.username
                        else:
                            logger.warning(f"Не удалось создать инспекцию: {inspection_response.error}")
                            result_data['qc_warning'] = inspection_response.error
                    else:
                        result_data['qc_warning'] = "Нет доступных инспекторов ОТК"
                else:
                    result_data['qc_warning'] = "Группа ОТК не найдена"
            
            logger.info(f"Приемка {receipt.id} создана успешно")
            
            return ServiceResponse.success_response(result_data)
            
        except Exception as e:
            logger.error(f"Ошибка при обработке поступления материала: {e}")
            return ServiceResponse.error_response(f"Ошибка обработки поступления: {str(e)}")


class NotificationService:
    """Сервис для отправки уведомлений"""
    
    @classmethod
    def send_status_change_notification(cls, inspection_id: int, old_status: str, 
                                      new_status: str, user: User) -> ServiceResponse:
        """
        Отправка уведомления об изменении статуса инспекции
        
        Args:
            inspection_id: ID инспекции
            old_status: Старый статус
            new_status: Новый статус
            user: Пользователь, изменивший статус
            
        Returns:
            ServiceResponse с результатом отправки
        """
        try:
            logger.info(f"Отправка уведомления об изменении статуса инспекции {inspection_id}")
            
            # Получаем инспекцию
            try:
                inspection = QCInspection.objects.select_related(
                    'material_receipt__material', 'inspector'
                ).get(id=inspection_id)
            except QCInspection.DoesNotExist:
                return ServiceResponse.error_response(f"Инспекция с ID {inspection_id} не найдена")
            
            material = inspection.material_receipt.material
            
            # Формируем сообщение
            status_names = {
                'draft': 'Черновик',
                'in_progress': 'В процессе',
                'completed': 'Завершено',
                'rejected': 'Отклонено',
                'cancelled': 'Отменено'
            }
            
            message = (
                f"🔔 Изменение статуса инспекции\n"
                f"📋 Инспекция: #{inspection_id}\n"
                f"📦 Материал: {material.material_grade}\n"
                f"🏭 Поставщик: {material.supplier}\n"
                f"📄 Сертификат: {material.certificate_number}\n"
                f"🔄 Статус: {status_names.get(old_status, old_status)} → {status_names.get(new_status, new_status)}\n"
                f"👤 Изменил: {user.get_full_name() or user.username}\n"
                f"⏰ Время: {timezone.now().strftime('%d.%m.%Y %H:%M')}"
            )
            
            # Определяем получателей
            recipients = []
            
            # Инспектор всегда получает уведомления
            if inspection.inspector:
                recipients.append(inspection.inspector)
            
            # При завершении уведомляем склад
            if new_status == 'completed':
                from django.contrib.auth.models import Group
                warehouse_group = Group.objects.filter(name__in=['warehouse', 'warehouse_staff']).first()
                if warehouse_group:
                    recipients.extend(warehouse_group.user_set.filter(is_active=True))
            
            # При назначении лабораторных испытаний уведомляем лабораторию
            if new_status == 'completed' and (inspection.requires_ppsd or inspection.requires_ultrasonic):
                from django.contrib.auth.models import Group
                lab_group = Group.objects.filter(name__in=['lab', 'laboratory']).first()
                if lab_group:
                    recipients.extend(lab_group.user_set.filter(is_active=True))
            
            # Убираем дубликаты
            recipients = list(set(recipients))
            
            # TODO: Интеграция с Telegram Bot
            # В реальной системе здесь будет отправка через Telegram Bot API
            notifications_sent = []
            for recipient in recipients:
                # Заглушка для Telegram уведомления
                notifications_sent.append({
                    'recipient': recipient.username,
                    'method': 'telegram',
                    'status': 'pending'  # В реальности будет actual status
                })
            
            logger.info(f"Подготовлено {len(notifications_sent)} уведомлений")
            
            return ServiceResponse.success_response({
                'inspection_id': inspection_id,
                'message': message,
                'recipients_count': len(recipients),
                'notifications': notifications_sent
            })
            
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления: {e}")
            return ServiceResponse.error_response(f"Ошибка отправки уведомления: {str(e)}")