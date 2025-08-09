"""
Celery задачи для обработки PDF сертификатов
"""
import logging
import time
from typing import Optional, Dict, Any
from celery import shared_task
from celery.exceptions import Retry
from django.conf import settings
from django.utils import timezone
from django.core.files.storage import default_storage
from django.db import transaction
from apps.warehouse.models import Certificate
from .models import CertificateSearchIndex, CertificatePreview, ProcessingLog
from .services import certificate_processor

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_uploaded_certificate(self, certificate_id: int):
    """
    Полная обработка загруженного сертификата:
    1. Извлечение текста
    2. Парсинг данных
    3. Создание поискового индекса
    4. Генерация превью
    """
    start_time = time.time()
    
    try:
        # Получаем сертификат
        certificate = Certificate.objects.get(id=certificate_id)
        
        logger.info(f"Начинаем обработку сертификата {certificate_id}")
        
        # Проверяем существование файла
        if not certificate.pdf_file or not default_storage.exists(certificate.pdf_file.name):
            raise ValueError(f"PDF файл для сертификата {certificate_id} не найден")
        
        # Создаем или обновляем поисковый индекс
        search_index, created = CertificateSearchIndex.objects.get_or_create(
            certificate=certificate,
            defaults={'processing_status': 'processing'}
        )
        
        if not created:
            search_index.processing_status = 'processing'
            search_index.save()
        
        # 1. Извлечение текста
        logger.info(f"Извлекаем текст из сертификата {certificate_id}")
        file_path = certificate.pdf_file.path
        extracted_text = certificate_processor.extract_text_from_pdf(file_path)
        
        if not extracted_text:
            search_index.processing_status = 'failed'
            search_index.error_message = 'Не удалось извлечь текст из PDF'
            search_index.save()
            raise ValueError("Не удалось извлечь текст из PDF")
        
        # 2. Парсинг данных
        logger.info(f"Парсим данные сертификата {certificate_id}")
        parsed_data = certificate_processor.parse_certificate_data(extracted_text)
        
        # 3. Обновляем поисковый индекс
        search_index.extracted_text = extracted_text
        search_index.grade = parsed_data.get('grade', '')
        search_index.heat_number = parsed_data.get('heat_number', '')
        search_index.certificate_number = parsed_data.get('certificate_number', '')
        search_index.supplier = parsed_data.get('supplier', '')
        search_index.chemical_composition = parsed_data.get('chemical_composition', {})
        search_index.mechanical_properties = parsed_data.get('mechanical_properties', {})
        search_index.test_results = parsed_data.get('test_results', {})
        
        # Создаем полнотекстовый поиск (если поддерживается)
        try:
            from django.contrib.postgres.search import SearchVector
            search_text = f"{extracted_text} {search_index.grade} {search_index.heat_number} {search_index.certificate_number} {search_index.supplier}"
            search_index.search_vector = SearchVector('extracted_text', weight='A') + \
                                       SearchVector('grade', weight='B') + \
                                       SearchVector('heat_number', weight='B') + \
                                       SearchVector('certificate_number', weight='B') + \
                                       SearchVector('supplier', weight='C')
        except ImportError:
            # Fallback для SQLite - просто сохраняем текст для простого поиска
            pass
        
        search_index.processing_status = 'completed'
        search_index.error_message = ''
        search_index.save()
        
        # 4. Обновляем parsed_data в основной модели
        with transaction.atomic():
            certificate.parsed_data.update({
                'processed_at': timezone.now().isoformat(),
                'processing_version': '1.0',
                **parsed_data
            })
            certificate.save(update_fields=['parsed_data'])
        
        # 5. Генерация превью (запускаем отдельной задачей для параллельности)
        generate_certificate_preview.delay(certificate_id)
        
        # 6. Отправляем уведомление об обработке (если настроено)
        notify_certificate_processed.delay(certificate_id, success=True)
        
        processing_time = time.time() - start_time
        logger.info(f"Сертификат {certificate_id} успешно обработан за {processing_time:.2f} сек")
        
        return {
            'certificate_id': certificate_id,
            'success': True,
            'processing_time': processing_time,
            'extracted_data': {
                'text_length': len(extracted_text),
                'grade': parsed_data.get('grade'),
                'heat_number': parsed_data.get('heat_number'),
                'chemical_elements': len(parsed_data.get('chemical_composition', {}))
            }
        }
        
    except Certificate.DoesNotExist:
        error_msg = f"Сертификат с ID {certificate_id} не найден"
        logger.error(error_msg)
        return {'certificate_id': certificate_id, 'success': False, 'error': error_msg}
        
    except Exception as e:
        error_msg = f"Ошибка обработки сертификата {certificate_id}: {e}"
        logger.error(error_msg)
        
        # Обновляем статус в индексе
        try:
            search_index = CertificateSearchIndex.objects.get(certificate_id=certificate_id)
            search_index.processing_status = 'failed'
            search_index.error_message = str(e)
            search_index.save()
        except CertificateSearchIndex.DoesNotExist:
            pass
        
        # Уведомление об ошибке
        notify_certificate_processed.delay(certificate_id, success=False, error=str(e))
        
        # Повторная попытка если возможно
        if self.request.retries < self.max_retries:
            countdown = 60 * (2 ** self.request.retries)  # Exponential backoff
            logger.info(f"Повторная попытка обработки сертификата {certificate_id} через {countdown} сек")
            raise self.retry(countdown=countdown, exc=e)
        
        return {'certificate_id': certificate_id, 'success': False, 'error': str(e)}


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def generate_certificate_preview(self, certificate_id: int):
    """
    Генерация превью сертификата
    """
    try:
        certificate = Certificate.objects.get(id=certificate_id)
        
        logger.info(f"Генерируем превью для сертификата {certificate_id}")
        
        # Проверяем существование файла
        if not certificate.pdf_file or not default_storage.exists(certificate.pdf_file.name):
            raise ValueError(f"PDF файл для сертификата {certificate_id} не найден")
        
        # Создаем или обновляем превью
        preview_obj, created = CertificatePreview.objects.get_or_create(
            certificate=certificate,
            defaults={'generation_status': 'generating'}
        )
        
        if not created:
            preview_obj.generation_status = 'generating'
            preview_obj.save()
        
        # Генерируем превью
        preview_url = certificate_processor.generate_certificate_preview(certificate.pdf_file)
        
        if preview_url:
            preview_obj.generation_status = 'completed'
            preview_obj.error_message = ''
            preview_obj.save()
            
            logger.info(f"Превью для сертификата {certificate_id} успешно сгенерировано")
            return {'certificate_id': certificate_id, 'success': True, 'preview_url': preview_url}
        else:
            preview_obj.generation_status = 'failed'
            preview_obj.error_message = 'Не удалось сгенерировать превью'
            preview_obj.save()
            raise ValueError("Не удалось сгенерировать превью")
        
    except Certificate.DoesNotExist:
        error_msg = f"Сертификат с ID {certificate_id} не найден"
        logger.error(error_msg)
        return {'certificate_id': certificate_id, 'success': False, 'error': error_msg}
        
    except Exception as e:
        error_msg = f"Ошибка генерации превью для сертификата {certificate_id}: {e}"
        logger.error(error_msg)
        
        # Обновляем статус превью
        try:
            preview_obj = CertificatePreview.objects.get(certificate_id=certificate_id)
            preview_obj.generation_status = 'failed'
            preview_obj.error_message = str(e)
            preview_obj.save()
        except CertificatePreview.DoesNotExist:
            pass
        
        # Повторная попытка если возможно
        if self.request.retries < self.max_retries:
            countdown = 30 * (2 ** self.request.retries)
            logger.info(f"Повторная попытка генерации превью для сертификата {certificate_id} через {countdown} сек")
            raise self.retry(countdown=countdown, exc=e)
        
        return {'certificate_id': certificate_id, 'success': False, 'error': str(e)}


@shared_task
def reprocess_certificates_batch(certificate_ids: list, force_reprocess: bool = False):
    """
    Пакетная обработка сертификатов
    """
    if not certificate_ids:
        return {'processed': 0, 'errors': 0}
    
    logger.info(f"Запуск пакетной обработки {len(certificate_ids)} сертификатов")
    
    processed = 0
    errors = 0
    
    for cert_id in certificate_ids:
        try:
            # Проверяем, нужна ли обработка
            if not force_reprocess:
                try:
                    search_index = CertificateSearchIndex.objects.get(certificate_id=cert_id)
                    if search_index.processing_status == 'completed':
                        logger.info(f"Сертификат {cert_id} уже обработан, пропускаем")
                        continue
                except CertificateSearchIndex.DoesNotExist:
                    pass
            
            # Запускаем обработку
            process_uploaded_certificate.delay(cert_id)
            processed += 1
            
            # Небольшая пауза между запусками для контроля нагрузки
            time.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Ошибка запуска обработки сертификата {cert_id}: {e}")
            errors += 1
    
    result = {'processed': processed, 'errors': errors, 'total': len(certificate_ids)}
    logger.info(f"Пакетная обработка завершена: {result}")
    
    return result


@shared_task
def cleanup_failed_processing():
    """
    Очистка неудачных обработок и повторная попытка
    """
    # Находим обработки, которые зависли в статусе 'processing'
    stuck_indexes = CertificateSearchIndex.objects.filter(
        processing_status='processing',
        indexed_at__lt=timezone.now() - timezone.timedelta(hours=1)
    )
    
    cleaned = 0
    for index in stuck_indexes:
        logger.warning(f"Обнаружен зависший индекс для сертификата {index.certificate_id}")
        index.processing_status = 'failed'
        index.error_message = 'Обработка превысила таймаут'
        index.save()
        
        # Перезапускаем обработку
        process_uploaded_certificate.delay(index.certificate_id)
        cleaned += 1
    
    # То же для превью
    stuck_previews = CertificatePreview.objects.filter(
        generation_status='generating',
        generated_at__lt=timezone.now() - timezone.timedelta(hours=1)
    )
    
    for preview in stuck_previews:
        logger.warning(f"Обнаружено зависшее превью для сертификата {preview.certificate_id}")
        preview.generation_status = 'failed'
        preview.error_message = 'Генерация превысила таймаут'
        preview.save()
        
        # Перезапускаем генерацию
        generate_certificate_preview.delay(preview.certificate_id)
        cleaned += 1
    
    logger.info(f"Очищено {cleaned} зависших обработок")
    return {'cleaned': cleaned}


@shared_task
def notify_certificate_processed(certificate_id: int, success: bool = True, error: str = None):
    """
    Уведомление об обработке сертификата
    """
    try:
        certificate = Certificate.objects.get(id=certificate_id)
        
        # Отправляем уведомление через Telegram (если настроено)
        try:
            from apps.notifications.services import telegram_service
            
            # Находим пользователей для уведомления
            recipients = []
            
            # Уведомляем создателя сертификата
            if certificate.created_by:
                recipients.append(certificate.created_by.id)
            
            # Уведомляем администраторов при ошибках
            if not success:
                from django.contrib.auth.models import User
                admin_users = User.objects.filter(
                    groups__name='Administrators'
                ).values_list('id', flat=True)
                recipients.extend(admin_users)
            
            if recipients:
                if success:
                    message = f"Сертификат успешно обработан\n\nМатериал: {certificate.material}"
                    alert_type = "Обработка сертификата"
                else:
                    message = f"Ошибка обработки сертификата\n\nМатериал: {certificate.material}\nОшибка: {error}"
                    alert_type = "Ошибка обработки"
                
                telegram_service.send_urgent_alert(
                    user_ids=list(set(recipients)),
                    alert_type=alert_type,
                    message=message,
                    material=certificate.material
                )
                
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления о сертификате {certificate_id}: {e}")
        
        return {'notified': True, 'certificate_id': certificate_id}
        
    except Certificate.DoesNotExist:
        logger.error(f"Сертификат {certificate_id} не найден для уведомления")
        return {'notified': False, 'error': 'Certificate not found'}
    
    except Exception as e:
        logger.error(f"Ошибка уведомления о сертификате {certificate_id}: {e}")
        return {'notified': False, 'error': str(e)}


@shared_task
def update_search_statistics():
    """
    Обновление статистики поиска и индексации
    """
    from django.db.models import Count, Q
    
    # Собираем статистику
    stats = {
        'total_certificates': Certificate.objects.count(),
        'processed_certificates': CertificateSearchIndex.objects.filter(
            processing_status='completed'
        ).count(),
        'failed_processing': CertificateSearchIndex.objects.filter(
            processing_status='failed'
        ).count(),
        'pending_processing': CertificateSearchIndex.objects.filter(
            processing_status='pending'
        ).count(),
        'with_previews': CertificatePreview.objects.filter(
            generation_status='completed'
        ).count(),
        'failed_previews': CertificatePreview.objects.filter(
            generation_status='failed'
        ).count(),
    }
    
    # Находим сертификаты без индексации
    unprocessed = Certificate.objects.exclude(
        search_index__processing_status='completed'
    ).count()
    
    stats['unprocessed_certificates'] = unprocessed
    
    # Логируем статистику
    logger.info(f"Статистика обработки сертификатов: {stats}")
    
    # Если есть необработанные сертификаты, можем запустить их обработку
    if unprocessed > 0:
        unprocessed_ids = Certificate.objects.exclude(
            search_index__processing_status='completed'
        ).values_list('id', flat=True)[:10]  # Обрабатываем по 10 за раз
        
        if unprocessed_ids:
            reprocess_certificates_batch.delay(list(unprocessed_ids))
            logger.info(f"Запущена обработка {len(unprocessed_ids)} необработанных сертификатов")
    
    return stats


@shared_task
def optimize_search_index():
    """
    Оптимизация поискового индекса
    """
    try:
        # Удаляем дублирующиеся записи
        duplicates = CertificateSearchIndex.objects.values('certificate_id').annotate(
            count=Count('id')
        ).filter(count__gt=1)
        
        removed = 0
        for dup in duplicates:
            # Оставляем только последнюю запись
            indexes = CertificateSearchIndex.objects.filter(
                certificate_id=dup['certificate_id']
            ).order_by('-indexed_at')
            
            for index in indexes[1:]:  # Удаляем все кроме первой (последней)
                index.delete()
                removed += 1
        
        # Очищаем записи для несуществующих сертификатов
        orphaned = CertificateSearchIndex.objects.filter(
            certificate__isnull=True
        )
        orphaned_count = orphaned.count()
        orphaned.delete()
        
        logger.info(f"Оптимизация индекса: удалено {removed} дубликатов, {orphaned_count} осиротевших записей")
        
        return {
            'duplicates_removed': removed,
            'orphaned_removed': orphaned_count
        }
        
    except Exception as e:
        logger.error(f"Ошибка оптимизации поискового индекса: {e}")
        return {'error': str(e)}