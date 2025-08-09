"""
Celery задачи для отправки уведомлений
"""
import logging
from typing import List, Optional
from datetime import datetime, timedelta
from celery import shared_task
from celery.exceptions import Retry
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from telegram import Bot
from telegram.error import TelegramError, Forbidden, BadRequest, TimedOut, NetworkError
from .models import NotificationLog, UserNotificationPreferences

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=5, default_retry_delay=60)
def send_telegram_message(self, notification_log_id: int):
    """
    Отправить сообщение в Telegram с retry логикой и exponential backoff
    """
    try:
        log = NotificationLog.objects.get(id=notification_log_id)
        
        if not settings.TELEGRAM_BOT_TOKEN:
            log.status = 'failed'
            log.error_message = 'TELEGRAM_BOT_TOKEN не настроен'
            log.save()
            logger.error(f"TELEGRAM_BOT_TOKEN не настроен для уведомления {notification_log_id}")
            return False
        
        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        
        try:
            # Отправляем сообщение
            message = bot.send_message(
                chat_id=log.telegram_chat_id,
                text=log.message,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            
            # Успешная отправка
            log.status = 'sent'
            log.sent_at = timezone.now()
            log.error_message = ''
            log.save()
            
            logger.info(f"Уведомление {notification_log_id} успешно отправлено в чат {log.telegram_chat_id}")
            return True
            
        except Forbidden as e:
            # Пользователь заблокировал бота или чат ID неверный
            log.status = 'failed'
            log.error_message = f'Unauthorized: {str(e)}'
            log.save()
            
            # Отключаем уведомления для этого пользователя
            try:
                preferences = log.user.notification_preferences
                preferences.is_telegram_enabled = False
                preferences.save()
                logger.warning(f"Отключены Telegram уведомления для пользователя {log.user.username}: {e}")
            except UserNotificationPreferences.DoesNotExist:
                pass
            
            return False
            
        except BadRequest as e:
            # Неверный формат сообщения или chat_id
            log.status = 'failed'
            log.error_message = f'Bad Request: {str(e)}'
            log.save()
            logger.error(f"Ошибка формата сообщения {notification_log_id}: {e}")
            return False
            
        except (TimedOut, NetworkError) as e:
            # Временные проблемы с сетью - можно повторить
            log.retry_count += 1
            log.status = 'retry'
            log.error_message = f'Network error (retry {log.retry_count}): {str(e)}'
            log.save()
            
            # Exponential backoff: 1min, 2min, 4min, 8min, 16min
            countdown = 60 * (2 ** self.request.retries)
            
            logger.warning(f"Сетевая ошибка для уведомления {notification_log_id}, повтор через {countdown}с: {e}")
            raise self.retry(countdown=countdown, exc=e)
            
        except TelegramError as e:
            # Другие ошибки Telegram API
            log.retry_count += 1
            log.status = 'retry'
            log.error_message = f'Telegram error (retry {log.retry_count}): {str(e)}'
            log.save()
            
            if self.request.retries < self.max_retries:
                countdown = 60 * (2 ** self.request.retries)
                logger.warning(f"Ошибка Telegram API для уведомления {notification_log_id}, повтор через {countdown}с: {e}")
                raise self.retry(countdown=countdown, exc=e)
            else:
                log.status = 'failed'
                log.save()
                logger.error(f"Исчерпаны попытки отправки уведомления {notification_log_id}: {e}")
                return False
        
    except NotificationLog.DoesNotExist:
        logger.error(f"NotificationLog с ID {notification_log_id} не найден")
        return False
    
    except Exception as e:
        logger.error(f"Неожиданная ошибка при отправке уведомления {notification_log_id}: {e}")
        
        try:
            log = NotificationLog.objects.get(id=notification_log_id)
            log.status = 'failed'
            log.error_message = f'Unexpected error: {str(e)}'
            log.save()
        except NotificationLog.DoesNotExist:
            pass
        
        return False


@shared_task
def send_daily_summaries():
    """
    Отправить ежедневные сводки всем пользователям с включенными уведомлениями
    """
    logger.info("Начинаем отправку ежедневных сводок")
    
    # Получаем всех пользователей с включенными ежедневными сводками
    preferences = UserNotificationPreferences.objects.filter(
        is_telegram_enabled=True,
        telegram_chat_id__isnull=False,
        notification_types__daily_summary__enabled=True
    )
    
    success_count = 0
    total_count = preferences.count()
    
    from .services import telegram_service
    
    for pref in preferences:
        try:
            if telegram_service.send_daily_summary(pref.user.id):
                success_count += 1
        except Exception as e:
            logger.error(f"Ошибка отправки ежедневной сводки пользователю {pref.user.username}: {e}")
    
    logger.info(f"Ежедневные сводки отправлены {success_count} из {total_count} пользователей")
    return {"success": success_count, "total": total_count}


@shared_task
def cleanup_old_notification_logs(days_to_keep: int = 30):
    """
    Очистка старых логов уведомлений
    """
    cutoff_date = timezone.now() - timedelta(days=days_to_keep)
    
    deleted_count = NotificationLog.objects.filter(
        created_at__lt=cutoff_date
    ).delete()[0]
    
    logger.info(f"Удалено {deleted_count} старых записей логов уведомлений")
    return deleted_count


@shared_task
def retry_failed_notifications():
    """
    Повторная попытка отправки неудачных уведомлений
    """
    # Находим уведомления, которые не удалось отправить в последние 24 часа
    cutoff_time = timezone.now() - timedelta(hours=24)
    
    failed_logs = NotificationLog.objects.filter(
        status='failed',
        retry_count__lt=3,  # Максимум 3 дополнительные попытки
        created_at__gte=cutoff_time
    )
    
    retry_count = 0
    
    for log in failed_logs:
        # Пропускаем если ошибка была связана с авторизацией
        if 'Forbidden' in log.error_message or 'Bad Request' in log.error_message:
            continue
        
        log.status = 'retry'
        log.retry_count += 1
        log.save()
        
        # Отправляем с задержкой
        send_telegram_message.apply_async(
            args=[log.id],
            countdown=60 * log.retry_count  # 1min, 2min, 3min задержка
        )
        
        retry_count += 1
    
    logger.info(f"Запущены повторные попытки для {retry_count} неудачных уведомлений")
    return retry_count


@shared_task(bind=True, max_retries=3, default_retry_delay=300)  # 5 минут между попытками
def send_bulk_notifications(self, user_ids: List[int], notification_type: str, 
                           message_template: str, context: dict = None, 
                           is_urgent: bool = False):
    """
    Массовая отправка уведомлений с rate limiting
    """
    import time
    from .services import telegram_service
    
    if context is None:
        context = {}
    
    try:
        success_count = 0
        failed_count = 0
        
        for i, user_id in enumerate(user_ids):
            try:
                user = User.objects.get(id=user_id)
                preferences = telegram_service._get_user_preferences(user)
                
                if not preferences.should_send_notification(notification_type, is_urgent):
                    continue
                
                # Форматируем сообщение
                message = message_template.format(**context)
                
                # Создаем лог
                log = telegram_service._create_notification_log(
                    user=user,
                    notification_type=notification_type,
                    message=message,
                    chat_id=preferences.telegram_chat_id
                )
                
                # Отправляем
                send_telegram_message.delay(log.id)
                success_count += 1
                
                # Rate limiting: не более 30 сообщений в секунду (требование Telegram)
                if (i + 1) % 30 == 0:
                    time.sleep(1)
                
            except User.DoesNotExist:
                logger.warning(f"Пользователь с ID {user_id} не найден")
                failed_count += 1
                continue
            except Exception as e:
                logger.error(f"Ошибка отправки массового уведомления пользователю {user_id}: {e}")
                failed_count += 1
                continue
        
        logger.info(f"Массовая рассылка завершена: {success_count} успешно, {failed_count} неудачно")
        return {"success": success_count, "failed": failed_count}
        
    except Exception as e:
        logger.error(f"Ошибка массовой рассылки: {e}")
        
        if self.request.retries < self.max_retries:
            logger.info(f"Повторная попытка массовой рассылки через 5 минут")
            raise self.retry(countdown=300, exc=e)
        
        return {"success": 0, "failed": len(user_ids)}


# Временно отключено до интеграции с workflow
# @shared_task
# def send_sla_violation_alerts():
#     """
#     Отправка уведомлений о нарушениях SLA
#     """
#     from apps.workflow.models import SLAViolation
#     from .services import telegram_service
#     
#     # Получаем активные нарушения SLA, по которым еще не отправлялись уведомления
#     violations = SLAViolation.objects.filter(
#         status='ACTIVE',
#         notification_sent=False
#     ).select_related('process')
#     
#     alert_count = 0
#     
#     for violation in violations:
#         try:
#             # Определяем получателей уведомления
#             process = violation.process
#             responsible_users = []
#             
#             # Добавляем ответственного за текущую задачу
#             if hasattr(process, 'current_task_assigned_to'):
#                 responsible_users.append(process.current_task_assigned_to.id)
#             
#             # Добавляем руководителей
#             supervisors = User.objects.filter(
#                 groups__name__in=['Руководители', 'Администраторы']
#             ).values_list('id', flat=True)
#             responsible_users.extend(supervisors)
#             
#             if responsible_users:
#                 alert_message = (
#                     f"Нарушение SLA!\n\n"
#                     f"Процесс: {process.flow_class.__name__}\n"
#                     f"Тип нарушения: {violation.violation_type}\n"
#                     f"Время нарушения: {violation.violation_time.strftime('%d.%m.%Y %H:%M')}\n"
#                     f"Превышение: {violation.get_violation_duration()}"
#                 )
#                 
#                 # Получаем материал из процесса
#                 material = getattr(process, 'material', None)
#                 
#                 telegram_service.send_urgent_alert(
#                     user_ids=list(set(responsible_users)),
#                     alert_type="Нарушение SLA",
#                     message=alert_message,
#                     material=material
#                 )
#                 
#                 # Отмечаем, что уведомление отправлено
#                 violation.notification_sent = True
#                 violation.save()
#                 
#                 alert_count += 1
#                 
#         except Exception as e:
#             logger.error(f"Ошибка отправки уведомления о нарушении SLA {violation.id}: {e}")
#     
#     logger.info(f"Отправлено {alert_count} уведомлений о нарушениях SLA")
#     return alert_count


@shared_task
def test_telegram_connection():
    """
    Тестирование подключения к Telegram Bot API
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не настроен")
        return {"status": "error", "message": "TELEGRAM_BOT_TOKEN не настроен"}
    
    try:
        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        me = bot.get_me()
        
        logger.info(f"Telegram бот подключен успешно: @{me.username}")
        return {
            "status": "success", 
            "bot_info": {
                "username": me.username,
                "first_name": me.first_name,
                "id": me.id
            }
        }
        
    except Exception as e:
        logger.error(f"Ошибка подключения к Telegram Bot API: {e}")
        return {"status": "error", "message": str(e)}