"""
Django management команда для массовой обработки PDF сертификатов
"""
import time
from typing import List, Dict, Any
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q, Count
from django.utils import timezone
from apps.warehouse.models import Certificate
from apps.certificates.models import CertificateSearchIndex, CertificatePreview
from apps.certificates.tasks import (
    process_uploaded_certificate, 
    reprocess_certificates_batch,
    cleanup_failed_processing
)


class Command(BaseCommand):
    """
    Команда для массовой обработки сертификатов
    
    Примеры использования:
    
    # Обработать все необработанные сертификаты
    python manage.py reprocess_all_certificates
    
    # Обработать все сертификаты заново
    python manage.py reprocess_all_certificates --force
    
    # Обработать конкретные сертификаты
    python manage.py reprocess_all_certificates --ids 1,2,3
    
    # Обработать только извлечение текста
    python manage.py reprocess_all_certificates --text-only
    
    # Обработать только превью
    python manage.py reprocess_all_certificates --preview-only
    
    # Асинхронная обработка через Celery
    python manage.py reprocess_all_certificates --async
    
    # Пакетная обработка
    python manage.py reprocess_all_certificates --batch-size 50
    """
    
    help = 'Массовая обработка PDF сертификатов - извлечение текста, парсинг данных, создание превью'
    
    def add_arguments(self, parser):
        """Добавление аргументов командной строки"""
        
        # Основные опции
        parser.add_argument(
            '--force',
            action='store_true',
            help='Переобработать все сертификаты, включая уже обработанные'
        )
        
        parser.add_argument(
            '--ids',
            type=str,
            help='Обработать только указанные ID сертификатов (через запятую)'
        )
        
        parser.add_argument(
            '--batch-size',
            type=int,
            default=10,
            help='Размер пакета для обработки (по умолчанию: 10)'
        )
        
        # Режимы обработки
        parser.add_argument(
            '--text-only',
            action='store_true',
            help='Обработать только извлечение текста и парсинг данных'
        )
        
        parser.add_argument(
            '--preview-only',
            action='store_true',
            help='Обработать только генерацию превью'
        )
        
        # Способ выполнения
        parser.add_argument(
            '--async',
            action='store_true',
            help='Асинхронная обработка через Celery (по умолчанию: синхронная)'
        )
        
        parser.add_argument(
            '--workers',
            type=int,
            default=1,
            help='Количество воркеров для параллельной обработки (только для синхронного режима)'
        )
        
        # Фильтры
        parser.add_argument(
            '--failed-only',
            action='store_true',
            help='Обработать только сертификаты с ошибками'
        )
        
        parser.add_argument(
            '--missing-preview',
            action='store_true',
            help='Обработать только сертификаты без превью'
        )
        
        parser.add_argument(
            '--missing-text',
            action='store_true',
            help='Обработать только сертификаты без извлеченного текста'
        )
        
        # Дополнительные опции
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать какие сертификаты будут обработаны, но не запускать обработку'
        )
        
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Очистить зависшие обработки перед началом'
        )
        
        parser.add_argument(
            '--stats',
            action='store_true',
            help='Показать только статистику без обработки'
        )
    
    def handle(self, *args, **options):
        """Основная логика команды"""
        
        self.options = options
        self.start_time = time.time()
        
        # Показываем статистику
        if options['stats']:
            self.show_statistics()
            return
        
        # Очистка зависших обработок
        if options['cleanup']:
            self.stdout.write("🧹 Очищаем зависшие обработки...")
            cleanup_failed_processing.delay()
            time.sleep(2)  # Даем время на выполнение
        
        # Получаем список сертификатов для обработки
        certificates = self.get_certificates_to_process()
        
        if not certificates:
            self.stdout.write(
                self.style.WARNING("✅ Нет сертификатов для обработки")
            )
            return
        
        self.stdout.write(
            f"📋 Найдено {len(certificates)} сертификатов для обработки"
        )
        
        # Dry run - показываем что будет обработано
        if options['dry_run']:
            self.show_dry_run(certificates)
            return
        
        # Запускаем обработку
        if options['async']:
            self.process_async(certificates)
        else:
            self.process_sync(certificates)
        
        # Показываем итоговую статистику
        self.show_final_stats()
    
    def get_certificates_to_process(self) -> List[Certificate]:
        """Получение списка сертификатов для обработки"""
        
        queryset = Certificate.objects.all()
        
        # Фильтр по конкретным ID
        if self.options['ids']:
            try:
                ids = [int(id.strip()) for id in self.options['ids'].split(',')]
                queryset = queryset.filter(id__in=ids)
                self.stdout.write(f"🎯 Фильтр по ID: {ids}")
            except ValueError:
                raise CommandError("Неверный формат ID. Используйте: --ids 1,2,3")
        
        # Фильтры по статусу обработки
        if not self.options['force']:
            if self.options['failed_only']:
                queryset = queryset.filter(
                    Q(search_index__processing_status='failed') |
                    Q(preview__generation_status='failed')
                )
                self.stdout.write("🔴 Фильтр: только неудачно обработанные")
            
            elif self.options['missing_preview']:
                queryset = queryset.filter(
                    Q(preview__isnull=True) |
                    Q(preview__generation_status__in=['failed', 'pending'])
                )
                self.stdout.write("🖼️ Фильтр: отсутствует превью")
            
            elif self.options['missing_text']:
                queryset = queryset.filter(
                    Q(search_index__isnull=True) |
                    Q(search_index__processing_status__in=['failed', 'pending']) |
                    Q(search_index__extracted_text='')
                )
                self.stdout.write("📝 Фильтр: отсутствует текст")
            
            else:
                # По умолчанию обрабатываем только необработанные
                queryset = queryset.exclude(
                    search_index__processing_status='completed'
                )
                self.stdout.write("⏳ Фильтр: только необработанные")
        
        # Сортировка и ограничение
        queryset = queryset.select_related('material').order_by('-uploaded_at')
        
        return list(queryset)
    
    def show_dry_run(self, certificates: List[Certificate]):
        """Показ что будет обработано в dry-run режиме"""
        
        self.stdout.write(
            self.style.WARNING("🔍 DRY RUN - Сертификаты для обработки:")
        )
        
        for i, cert in enumerate(certificates[:20], 1):  # Показываем первые 20
            material = cert.material
            status_info = self.get_certificate_status(cert)
            
            self.stdout.write(
                f"  {i}. ID: {cert.id} | "
                f"Материал: {material.material_grade} | "
                f"Файл: {cert.pdf_file.name if cert.pdf_file else 'НЕТ'} | "
                f"Статус: {status_info}"
            )
        
        if len(certificates) > 20:
            self.stdout.write(f"  ... и еще {len(certificates) - 20} сертификатов")
        
        # Показываем что будет сделано
        operations = []
        if not self.options['preview_only']:
            operations.append("извлечение текста и парсинг")
        if not self.options['text_only']:
            operations.append("генерация превью")
        
        self.stdout.write(f"\n🔧 Будет выполнено: {', '.join(operations)}")
        
        if self.options['async']:
            self.stdout.write("⚡ Режим: асинхронная обработка через Celery")
        else:
            self.stdout.write(f"🔄 Режим: синхронная обработка ({self.options['workers']} воркеров)")
    
    def get_certificate_status(self, certificate: Certificate) -> str:
        """Получение статуса обработки сертификата"""
        status_parts = []
        
        # Статус текста
        try:
            search_index = certificate.search_index
            if search_index.processing_status == 'completed':
                status_parts.append("Текст: ✅")
            elif search_index.processing_status == 'failed':
                status_parts.append("Текст: ❌")
            else:
                status_parts.append(f"Текст: ⏳{search_index.processing_status}")
        except:
            status_parts.append("Текст: ⭕")
        
        # Статус превью
        try:
            preview = certificate.preview
            if preview.generation_status == 'completed':
                status_parts.append("Превью: ✅")
            elif preview.generation_status == 'failed':
                status_parts.append("Превью: ❌")
            else:
                status_parts.append(f"Превью: ⏳{preview.generation_status}")
        except:
            status_parts.append("Превью: ⭕")
        
        return " | ".join(status_parts)
    
    def process_async(self, certificates: List[Certificate]):
        """Асинхронная обработка через Celery"""
        
        self.stdout.write(
            self.style.SUCCESS("⚡ Запуск асинхронной обработки через Celery...")
        )
        
        # Разбиваем на пакеты
        batch_size = self.options['batch_size']
        certificate_ids = [cert.id for cert in certificates]
        
        batches = [
            certificate_ids[i:i + batch_size] 
            for i in range(0, len(certificate_ids), batch_size)
        ]
        
        self.stdout.write(f"📦 Создано {len(batches)} пакетов по {batch_size} сертификатов")
        
        # Запускаем пакеты с интервалом
        for i, batch in enumerate(batches, 1):
            self.stdout.write(f"🚀 Запуск пакета {i}/{len(batches)}: {len(batch)} сертификатов")
            
            if self.options['text_only']:
                # Запускаем только обработку текста
                for cert_id in batch:
                    process_uploaded_certificate.delay(cert_id)
            elif self.options['preview_only']:
                # Запускаем только генерацию превью
                from apps.certificates.tasks import generate_certificate_preview
                for cert_id in batch:
                    generate_certificate_preview.delay(cert_id)
            else:
                # Полная обработка пакетом
                reprocess_certificates_batch.delay(batch, force_reprocess=self.options['force'])
            
            # Пауза между пакетами для контроля нагрузки
            if i < len(batches):
                time.sleep(1)
        
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Запущена асинхронная обработка {len(certificates)} сертификатов\n"
                f"📊 Отслеживайте прогресс в логах Celery или Django админке"
            )
        )
    
    def process_sync(self, certificates: List[Certificate]):
        """Синхронная обработка"""
        
        self.stdout.write(
            self.style.SUCCESS("🔄 Запуск синхронной обработки...")
        )
        
        processed = 0
        errors = 0
        skipped = 0
        
        from apps.certificates.services import certificate_processor
        
        for i, certificate in enumerate(certificates, 1):
            try:
                self.stdout.write(
                    f"📄 [{i}/{len(certificates)}] Обрабатываем сертификат {certificate.id} "
                    f"({certificate.material.material_grade})..."
                )
                
                # Проверяем существование файла
                if not certificate.pdf_file:
                    self.stdout.write(
                        self.style.WARNING(f"  ⚠️ Пропускаем: отсутствует PDF файл")
                    )
                    skipped += 1
                    continue
                
                # Обработка текста
                if not self.options['preview_only']:
                    success = self.process_certificate_text(certificate)
                    if not success:
                        errors += 1
                        continue
                
                # Генерация превью
                if not self.options['text_only']:
                    success = self.process_certificate_preview(certificate)
                    if not success:
                        errors += 1
                        continue
                
                processed += 1
                self.stdout.write(
                    self.style.SUCCESS(f"  ✅ Успешно обработан")
                )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"  ❌ Ошибка: {e}")
                )
                errors += 1
        
        # Итоговая статистика
        self.stdout.write(
            self.style.SUCCESS(
                f"\n📊 Обработка завершена:\n"
                f"  ✅ Успешно обработано: {processed}\n"
                f"  ❌ Ошибок: {errors}\n"
                f"  ⚠️ Пропущено: {skipped}\n"
                f"  📈 Общий процент успеха: {processed / len(certificates) * 100:.1f}%"
            )
        )
    
    def process_certificate_text(self, certificate: Certificate) -> bool:
        """Обработка текста одного сертификата"""
        try:
            from apps.certificates.services import certificate_processor
            
            # Извлекаем текст
            text = certificate_processor.extract_text_from_pdf(certificate.pdf_file.path)
            if not text:
                self.stdout.write("    ❌ Не удалось извлечь текст")
                return False
            
            # Парсим данные
            parsed_data = certificate_processor.parse_certificate_data(text)
            
            # Обновляем или создаем индекс
            search_index, created = CertificateSearchIndex.objects.get_or_create(
                certificate=certificate,
                defaults={'processing_status': 'completed'}
            )
            
            search_index.extracted_text = text
            search_index.grade = parsed_data.get('grade', '')
            search_index.heat_number = parsed_data.get('heat_number', '')
            search_index.certificate_number = parsed_data.get('certificate_number', '')
            search_index.supplier = parsed_data.get('supplier', '')
            search_index.chemical_composition = parsed_data.get('chemical_composition', {})
            search_index.mechanical_properties = parsed_data.get('mechanical_properties', {})
            search_index.test_results = parsed_data.get('test_results', {})
            search_index.processing_status = 'completed'
            search_index.error_message = ''
            search_index.save()
            
            # Обновляем основную модель
            certificate.parsed_data.update({
                'processed_at': timezone.now().isoformat(),
                'processing_version': '1.0',
                **parsed_data
            })
            certificate.save(update_fields=['parsed_data'])
            
            self.stdout.write(f"    📝 Текст: {len(text)} символов")
            if parsed_data.get('grade'):
                self.stdout.write(f"    🔍 Найдена марка: {parsed_data['grade']}")
            
            return True
            
        except Exception as e:
            self.stdout.write(f"    ❌ Ошибка обработки текста: {e}")
            return False
    
    def process_certificate_preview(self, certificate: Certificate) -> bool:
        """Генерация превью одного сертификата"""
        try:
            from apps.certificates.services import certificate_processor
            
            preview_url = certificate_processor.generate_certificate_preview(certificate.pdf_file)
            
            if preview_url:
                self.stdout.write(f"    🖼️ Превью сгенерировано")
                return True
            else:
                self.stdout.write("    ❌ Не удалось сгенерировать превью")
                return False
                
        except Exception as e:
            self.stdout.write(f"    ❌ Ошибка генерации превью: {e}")
            return False
    
    def show_statistics(self):
        """Показ текущей статистики"""
        
        self.stdout.write(
            self.style.SUCCESS("📊 СТАТИСТИКА ОБРАБОТКИ СЕРТИФИКАТОВ")
        )
        self.stdout.write("=" * 50)
        
        # Общая статистика
        total_certs = Certificate.objects.count()
        
        # Статистика по тексту
        with_text = CertificateSearchIndex.objects.filter(
            processing_status='completed'
        ).count()
        failed_text = CertificateSearchIndex.objects.filter(
            processing_status='failed'
        ).count()
        pending_text = CertificateSearchIndex.objects.filter(
            processing_status='pending'
        ).count()
        
        # Статистика по превью
        with_preview = CertificatePreview.objects.filter(
            generation_status='completed'
        ).count()
        failed_preview = CertificatePreview.objects.filter(
            generation_status='failed'
        ).count()
        
        # Выводим статистику
        self.stdout.write(f"📄 Всего сертификатов: {total_certs}")
        self.stdout.write(f"")
        self.stdout.write(f"📝 Обработка текста:")
        self.stdout.write(f"  ✅ Успешно: {with_text} ({with_text/total_certs*100:.1f}%)")
        self.stdout.write(f"  ❌ Ошибки: {failed_text}")
        self.stdout.write(f"  ⏳ В ожидании: {pending_text}")
        self.stdout.write(f"  ⭕ Не обработано: {total_certs - with_text - failed_text - pending_text}")
        self.stdout.write(f"")
        self.stdout.write(f"🖼️ Генерация превью:")
        self.stdout.write(f"  ✅ Успешно: {with_preview} ({with_preview/total_certs*100:.1f}%)")
        self.stdout.write(f"  ❌ Ошибки: {failed_preview}")
        self.stdout.write(f"  ⭕ Не сгенерировано: {total_certs - with_preview - failed_preview}")
        
        # Топ-проблемы
        self.stdout.write(f"")
        self.stdout.write("🔍 Частые ошибки:")
        
        error_stats = CertificateSearchIndex.objects.filter(
            processing_status='failed'
        ).values('error_message').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        for error in error_stats:
            self.stdout.write(f"  • {error['error_message'][:50]}... ({error['count']} раз)")
    
    def show_final_stats(self):
        """Показ финальной статистики после обработки"""
        
        elapsed = time.time() - self.start_time
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\n🎉 Команда выполнена за {elapsed:.1f} секунд"
            )
        )
        
        # Показываем обновленную статистику
        if not self.options['dry_run']:
            self.stdout.write("\n📈 Обновленная статистика:")
            self.show_statistics()