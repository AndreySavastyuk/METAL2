"""
Сервисы для отправки уведомлений
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, date
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Count, Q
from telegram import Bot
from telegram.error import TelegramError, Forbidden, BadRequest
import asyncio
from .models import UserNotificationPreferences, NotificationLog

logger = logging.getLogger(__name__)


class TelegramNotificationService:
    """Сервис для отправки уведомлений в Telegram"""
    
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.bot = None
        if self.bot_token:
            self.bot = Bot(token=self.bot_token)
    
    def _check_bot_available(self) -> bool:
        """Проверить доступность бота"""
        if not self.bot_token:
            logger.warning("TELEGRAM_BOT_TOKEN не настроен")
            return False
        
        if not self.bot:
            logger.error("Telegram Bot не инициализирован")
            return False
        
        return True
    
    def _get_user_preferences(self, user: User) -> Optional[UserNotificationPreferences]:
        """Получить настройки уведомлений пользователя"""
        try:
            return user.notification_preferences
        except UserNotificationPreferences.DoesNotExist:
            # Создаем настройки по умолчанию
            return UserNotificationPreferences.objects.create(
                user=user,
                notification_types={
                    'status_update': {'enabled': True, 'urgent_only': False},
                    'task_assignment': {'enabled': True, 'urgent_only': False},
                    'urgent_alert': {'enabled': True, 'urgent_only': False},
                }
            )
    
    def _create_notification_log(self, user: User, notification_type: str, 
                               message: str, chat_id: str, 
                               object_type: str = None, object_id: int = None) -> NotificationLog:
        """Создать запись в логе уведомлений"""
        return NotificationLog.objects.create(
            user=user,
            notification_type=notification_type,
            message=message,
            telegram_chat_id=chat_id,
            object_type=object_type,
            object_id=object_id
        )
    
    def _format_material_info(self, material) -> str:
        """Форматировать информацию о материале"""
        return (
            f"📦 *Материал:* {material.material_grade}\n"
            f"🏭 *Поставщик:* {material.supplier}\n"
            f"📄 *Сертификат:* {material.certificate_number}\n"
            f"🔥 *Плавка:* {material.heat_number}\n"
            f"📏 *Размер:* {material.size}\n"
            f"⚖️ *Количество:* {material.quantity} {material.get_unit_display()}"
        )
    
    def send_status_update(self, user_id: int, material, old_status: str, 
                          new_status: str, is_urgent: bool = False) -> bool:
        """Отправить уведомление об изменении статуса материала"""
        if not self._check_bot_available():
            return False
        
        try:
            user = User.objects.get(id=user_id)
            preferences = self._get_user_preferences(user)
            
            if not preferences.should_send_notification('status_update', is_urgent):
                logger.info(f"Уведомление о статусе отключено для пользователя {user.username}")
                return False
            
            # Формируем сообщение
            status_emoji = {
                'pending_qc': '⏳',
                'in_qc': '🔍',
                'approved': '✅',
                'rejected': '❌',
                'in_lab': '🧪',
                'lab_complete': '✅',
                'in_production': '⚙️',
                'completed': '🎉'
            }
            
            old_emoji = status_emoji.get(old_status, '📋')
            new_emoji = status_emoji.get(new_status, '📋')
            
            # Переводим статусы на русский
            status_translations = {
                'pending_qc': 'Ожидает ОТК',
                'in_qc': 'В ОТК',
                'approved': 'Одобрено',
                'rejected': 'Отклонено',
                'in_lab': 'В лаборатории',
                'lab_complete': 'Лаборатория завершена',
                'in_production': 'В производстве',
                'completed': 'Завершено'
            }
            
            old_status_ru = status_translations.get(old_status, old_status)
            new_status_ru = status_translations.get(new_status, new_status)
            
            message = (
                f"🔄 *Изменение статуса материала*\n\n"
                f"{self._format_material_info(material)}\n\n"
                f"📊 *Статус изменен:*\n"
                f"{old_emoji} {old_status_ru} → {new_emoji} {new_status_ru}\n\n"
                f"🕐 *Время:* {timezone.now().strftime('%d.%m.%Y %H:%M')}"
            )
            
            if is_urgent:
                message = f"🚨 *СРОЧНО!* 🚨\n\n{message}"
            
            # Создаем лог
            log = self._create_notification_log(
                user=user,
                notification_type='status_update',
                message=message,
                chat_id=preferences.telegram_chat_id,
                object_type='material',
                object_id=material.id
            )
            
            from .tasks import send_telegram_message
            send_telegram_message.delay(log.id)
            
            return True
            
        except User.DoesNotExist:
            logger.error(f"Пользователь с ID {user_id} не найден")
            return False
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления о статусе: {e}")
            return False
    
    def send_task_assignment(self, user_id: int, task_type: str, 
                           material, additional_info: str = "", 
                           is_urgent: bool = False) -> bool:
        """Отправить уведомление о назначении задачи"""
        if not self._check_bot_available():
            return False
        
        try:
            user = User.objects.get(id=user_id)
            preferences = self._get_user_preferences(user)
            
            if not preferences.should_send_notification('task_assignment', is_urgent):
                logger.info(f"Уведомления о задачах отключены для пользователя {user.username}")
                return False
            
            # Переводим типы задач
            task_translations = {
                'qc_inspection': 'Проверка ОТК',
                'lab_testing': 'Лабораторные испытания',
                'production_prep': 'Подготовка к производству',
                'final_inspection': 'Финальная проверка',
                'warehouse_receipt': 'Приемка на склад'
            }
            
            task_emojis = {
                'qc_inspection': '🔍',
                'lab_testing': '🧪',
                'production_prep': '⚙️',
                'final_inspection': '📋',
                'warehouse_receipt': '📦'
            }
            
            task_ru = task_translations.get(task_type, task_type)
            task_emoji = task_emojis.get(task_type, '📋')
            
            message = (
                f"{task_emoji} *Новая задача назначена*\n\n"
                f"👤 *Исполнитель:* {user.get_full_name() or user.username}\n"
                f"📋 *Тип задачи:* {task_ru}\n\n"
                f"{self._format_material_info(material)}\n\n"
                f"🕐 *Время назначения:* {timezone.now().strftime('%d.%m.%Y %H:%M')}"
            )
            
            if additional_info:
                message += f"\n\n📝 *Дополнительная информация:*\n{additional_info}"
            
            if is_urgent:
                message = f"🚨 *СРОЧНАЯ ЗАДАЧА!* 🚨\n\n{message}"
            
            # Создаем лог
            log = self._create_notification_log(
                user=user,
                notification_type='task_assignment',
                message=message,
                chat_id=preferences.telegram_chat_id,
                object_type='material',
                object_id=material.id
            )
            
            from .tasks import send_telegram_message
            send_telegram_message.delay(log.id)
            
            return True
            
        except User.DoesNotExist:
            logger.error(f"Пользователь с ID {user_id} не найден")
            return False
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления о задаче: {e}")
            return False
    
    def send_daily_summary(self, user_id: int, summary_date: date = None) -> bool:
        """Отправить ежедневную сводку"""
        if not self._check_bot_available():
            return False
        
        try:
            user = User.objects.get(id=user_id)
            preferences = self._get_user_preferences(user)
            
            if not preferences.should_send_notification('daily_summary'):
                logger.info(f"Ежедневная сводка отключена для пользователя {user.username}")
                return False
            
            if summary_date is None:
                summary_date = timezone.now().date()
            
            # Получаем статистику за день
            from apps.warehouse.models import MaterialReceipt
            from apps.quality.models import QCInspection
            from apps.laboratory.models import TestRequest
            
            start_date = timezone.make_aware(datetime.combine(summary_date, datetime.min.time()))
            end_date = timezone.make_aware(datetime.combine(summary_date, datetime.max.time()))
            
            # Статистика по поступлениям
            receipts_count = MaterialReceipt.objects.filter(
                created_at__range=[start_date, end_date]
            ).count()
            
            # Статистика по проверкам ОТК
            qc_inspections = QCInspection.objects.filter(
                created_at__range=[start_date, end_date]
            ).aggregate(
                total=Count('id'),
                approved=Count('id', filter=Q(status='approved')),
                rejected=Count('id', filter=Q(status='rejected'))
            )
            
            # Статистика по лабораторным испытаниям
            lab_tests = TestRequest.objects.filter(
                created_at__range=[start_date, end_date]
            ).aggregate(
                total=Count('id'),
                completed=Count('id', filter=Q(status='completed'))
            )
            
            message = (
                f"📊 *Ежедневная сводка за {summary_date.strftime('%d.%m.%Y')}*\n\n"
                f"📦 *Поступления материалов:* {receipts_count}\n\n"
                f"🔍 *Проверки ОТК:*\n"
                f"  • Всего: {qc_inspections['total']}\n"
                f"  • Одобрено: {qc_inspections['approved']} ✅\n"
                f"  • Отклонено: {qc_inspections['rejected']} ❌\n\n"
                f"🧪 *Лабораторные испытания:*\n"
                f"  • Всего: {lab_tests['total']}\n"
                f"  • Завершено: {lab_tests['completed']} ✅\n\n"
                f"🕐 *Время формирования:* {timezone.now().strftime('%d.%m.%Y %H:%M')}"
            )
            
            # Создаем лог
            log = self._create_notification_log(
                user=user,
                notification_type='daily_summary',
                message=message,
                chat_id=preferences.telegram_chat_id
            )
            
            from .tasks import send_telegram_message
            send_telegram_message.delay(log.id)
            
            return True
            
        except User.DoesNotExist:
            logger.error(f"Пользователь с ID {user_id} не найден")
            return False
        except Exception as e:
            logger.error(f"Ошибка отправки ежедневной сводки: {e}")
            return False
    
    def send_urgent_alert(self, user_ids: List[int], alert_type: str, 
                         message: str, material=None) -> bool:
        """Отправить срочное уведомление группе пользователей"""
        if not self._check_bot_available():
            return False
        
        success_count = 0
        
        for user_id in user_ids:
            try:
                user = User.objects.get(id=user_id)
                preferences = self._get_user_preferences(user)
                
                if not preferences.should_send_notification('urgent_alert', is_urgent=True):
                    continue
                
                alert_message = f"🚨 *СРОЧНОЕ УВЕДОМЛЕНИЕ* 🚨\n\n"
                alert_message += f"⚠️ *Тип:* {alert_type}\n\n"
                alert_message += f"📝 *Сообщение:*\n{message}\n\n"
                
                if material:
                    alert_message += f"{self._format_material_info(material)}\n\n"
                
                alert_message += f"🕐 *Время:* {timezone.now().strftime('%d.%m.%Y %H:%M')}"
                
                # Создаем лог
                log = self._create_notification_log(
                    user=user,
                    notification_type='urgent_alert',
                    message=alert_message,
                    chat_id=preferences.telegram_chat_id,
                    object_type='material' if material else None,
                    object_id=material.id if material else None
                )
                
                from .tasks import send_telegram_message
                send_telegram_message.delay(log.id)
                success_count += 1
                
            except User.DoesNotExist:
                logger.error(f"Пользователь с ID {user_id} не найден")
                continue
            except Exception as e:
                logger.error(f"Ошибка отправки срочного уведомления пользователю {user_id}: {e}")
                continue
        
        logger.info(f"Срочное уведомление отправлено {success_count} из {len(user_ids)} пользователей")
        return success_count > 0


# Singleton instance
telegram_service = TelegramNotificationService()