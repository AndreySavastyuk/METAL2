"""
Скрипт для тестирования системы обработки PDF сертификатов
"""
import os
import sys
import django
from django.conf import settings

# Настройка Django
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from apps.warehouse.models import Material, Certificate
from apps.certificates.models import CertificateSearchIndex, CertificatePreview
from apps.certificates.services import certificate_processor
from apps.certificates.tasks import process_uploaded_certificate


def create_test_data():
    """Создание тестовых данных"""
    print("📦 Создание тестовых данных...")
    
    # Создаем пользователя
    user, created = User.objects.get_or_create(
        username='test_pdf_user',
        defaults={
            'first_name': 'PDF',
            'last_name': 'Тестер',
            'email': 'pdf@test.com'
        }
    )
    
    if created:
        print(f"✅ Создан пользователь: {user.username}")
    
    # Создаем материал
    material, created = Material.objects.get_or_create(
        material_grade='40X',
        supplier='Тестовый поставщик PDF',
        certificate_number='PDF-CERT-001',
        heat_number='PDF-HEAT-001',
        defaults={
            'size': '⌀50',
            'quantity': 500,
            'unit': 'kg',
            'order_number': 'PDF-ORDER-001',
            'created_by': user,
            'updated_by': user
        }
    )
    
    if created:
        print(f"✅ Создан материал: {material}")
    
    return user, material


def test_text_extraction():
    """Тестирование извлечения текста из PDF"""
    print("\n📝 ТЕСТИРОВАНИЕ ИЗВЛЕЧЕНИЯ ТЕКСТА")
    print("=" * 50)
    
    # Находим сертификаты с PDF файлами
    certificates_with_files = Certificate.objects.filter(
        pdf_file__isnull=False
    ).exclude(pdf_file='')[:3]
    
    if not certificates_with_files:
        print("⚠️ Нет сертификатов с PDF файлами для тестирования")
        print("💡 Загрузите PDF сертификаты через админку Django")
        return
    
    for certificate in certificates_with_files:
        print(f"\n📄 Тестируем сертификат: {certificate}")
        print(f"   Файл: {certificate.pdf_file.name}")
        
        try:
            # Извлекаем текст
            text = certificate_processor.extract_text_from_pdf(certificate.pdf_file.path)
            
            if text:
                print(f"✅ Текст извлечен: {len(text)} символов")
                
                # Показываем первые 200 символов
                preview = text[:200] + "..." if len(text) > 200 else text
                print(f"📖 Превью текста:")
                print(f"   {preview}")
                
                # Парсим данные
                parsed_data = certificate_processor.parse_certificate_data(text)
                print(f"🔍 Извлеченные данные:")
                
                if parsed_data.get('grade'):
                    print(f"   • Марка: {parsed_data['grade']}")
                if parsed_data.get('heat_number'):
                    print(f"   • Плавка: {parsed_data['heat_number']}")
                if parsed_data.get('supplier'):
                    print(f"   • Поставщик: {parsed_data['supplier']}")
                if parsed_data.get('chemical_composition'):
                    elements = len(parsed_data['chemical_composition'])
                    print(f"   • Химический состав: {elements} элементов")
                
            else:
                print("❌ Не удалось извлечь текст")
                
        except Exception as e:
            print(f"❌ Ошибка: {e}")


def test_preview_generation():
    """Тестирование генерации превью"""
    print("\n🖼️ ТЕСТИРОВАНИЕ ГЕНЕРАЦИИ ПРЕВЬЮ")
    print("=" * 50)
    
    certificates_with_files = Certificate.objects.filter(
        pdf_file__isnull=False
    ).exclude(pdf_file='')[:2]
    
    if not certificates_with_files:
        print("⚠️ Нет сертификатов с PDF файлами для тестирования")
        return
    
    for certificate in certificates_with_files:
        print(f"\n📄 Генерируем превью для: {certificate}")
        
        try:
            preview_url = certificate_processor.generate_certificate_preview(certificate.pdf_file)
            
            if preview_url:
                print(f"✅ Превью сгенерировано: {preview_url}")
            else:
                print("❌ Не удалось сгенерировать превью")
                
        except Exception as e:
            print(f"❌ Ошибка генерации превью: {e}")


def test_search_functionality():
    """Тестирование поиска в сертификатах"""
    print("\n🔍 ТЕСТИРОВАНИЕ ПОИСКА В СЕРТИФИКАТАХ")
    print("=" * 50)
    
    # Проверяем наличие обработанных сертификатов
    processed_count = CertificateSearchIndex.objects.filter(
        processing_status='completed'
    ).count()
    
    print(f"📊 Обработанных сертификатов: {processed_count}")
    
    if processed_count == 0:
        print("⚠️ Нет обработанных сертификатов для поиска")
        print("💡 Запустите обработку командой: python manage.py reprocess_all_certificates")
        return
    
    # Тестовые запросы
    test_queries = [
        '40X',
        'сталь',
        'плавка',
        'сертификат',
        'поставщик'
    ]
    
    for query in test_queries:
        print(f"\n🔎 Поиск по запросу: '{query}'")
        
        try:
            results = certificate_processor.search_in_certificates(query, limit=5)
            
            if results:
                print(f"✅ Найдено результатов: {len(results)}")
                
                for i, result in enumerate(results[:3], 1):
                    print(f"   {i}. Материал: {result.get('grade', 'N/A')}")
                    print(f"      Плавка: {result.get('heat_number', 'N/A')}")
                    print(f"      Релевантность: {result.get('match_score', 0):.1f}")
                    print(f"      Поля: {', '.join(result.get('matched_fields', []))}")
            else:
                print("❌ Результатов не найдено")
                
        except Exception as e:
            print(f"❌ Ошибка поиска: {e}")


def test_async_processing():
    """Тестирование асинхронной обработки"""
    print("\n⚡ ТЕСТИРОВАНИЕ АСИНХРОННОЙ ОБРАБОТКИ")
    print("=" * 50)
    
    # Находим сертификат для обработки
    certificates = Certificate.objects.filter(
        pdf_file__isnull=False
    ).exclude(pdf_file='')[:1]
    
    if not certificates:
        print("⚠️ Нет сертификатов для тестирования асинхронной обработки")
        return
    
    certificate = certificates[0]
    print(f"📄 Тестируем асинхронную обработку сертификата: {certificate}")
    
    try:
        # Запускаем асинхронную обработку
        task = process_uploaded_certificate.delay(certificate.id)
        print(f"✅ Задача запущена с ID: {task.id}")
        print("⏳ Дождитесь выполнения задачи в Celery worker")
        print("📊 Проверьте результат через админку или API")
        
    except Exception as e:
        print(f"❌ Ошибка запуска асинхронной обработки: {e}")


def show_statistics():
    """Показать статистику обработки"""
    print("\n📊 СТАТИСТИКА ОБРАБОТКИ СЕРТИФИКАТОВ")
    print("=" * 50)
    
    # Общая статистика
    total_certs = Certificate.objects.count()
    
    # Статистика по обработке текста
    text_stats = CertificateSearchIndex.objects.values('processing_status').annotate(
        count=Count('id')
    )
    
    # Статистика по превью
    preview_stats = CertificatePreview.objects.values('generation_status').annotate(
        count=Count('id')
    )
    
    print(f"📄 Всего сертификатов: {total_certs}")
    
    print(f"\n📝 Обработка текста:")
    for stat in text_stats:
        status_name = {
            'completed': 'Завершено',
            'failed': 'Ошибки',
            'pending': 'В ожидании',
            'processing': 'Обрабатывается'
        }.get(stat['processing_status'], stat['processing_status'])
        print(f"   • {status_name}: {stat['count']}")
    
    print(f"\n🖼️ Генерация превью:")
    for stat in preview_stats:
        status_name = {
            'completed': 'Завершено',
            'failed': 'Ошибки',
            'pending': 'В ожидании',
            'generating': 'Генерируется'
        }.get(stat['generation_status'], stat['generation_status'])
        print(f"   • {status_name}: {stat['count']}")
    
    # Статистика извлеченных данных
    if CertificateSearchIndex.objects.filter(processing_status='completed').exists():
        print(f"\n🔍 Извлеченные данные:")
        
        with_grade = CertificateSearchIndex.objects.filter(
            processing_status='completed',
            grade__isnull=False
        ).exclude(grade='').count()
        
        with_heat = CertificateSearchIndex.objects.filter(
            processing_status='completed',
            heat_number__isnull=False
        ).exclude(heat_number='').count()
        
        with_supplier = CertificateSearchIndex.objects.filter(
            processing_status='completed',
            supplier__isnull=False
        ).exclude(supplier='').count()
        
        print(f"   • С маркой материала: {with_grade}")
        print(f"   • С номером плавки: {with_heat}")
        print(f"   • С поставщиком: {with_supplier}")


def print_available_commands():
    """Показать доступные команды"""
    print("\n🛠️ ДОСТУПНЫЕ КОМАНДЫ ДЛЯ УПРАВЛЕНИЯ ОБРАБОТКОЙ")
    print("=" * 60)
    
    commands = [
        ("python manage.py reprocess_all_certificates", "Обработать все сертификаты"),
        ("python manage.py reprocess_all_certificates --force", "Переобработать все сертификаты"),
        ("python manage.py reprocess_all_certificates --ids 1,2,3", "Обработать конкретные сертификаты"),
        ("python manage.py reprocess_all_certificates --text-only", "Только извлечение текста"),
        ("python manage.py reprocess_all_certificates --preview-only", "Только генерация превью"),
        ("python manage.py reprocess_all_certificates --async", "Асинхронная обработка"),
        ("python manage.py reprocess_all_certificates --stats", "Показать статистику"),
        ("python manage.py reprocess_all_certificates --dry-run", "Показать что будет обработано"),
    ]
    
    for command, description in commands:
        print(f"• {command}")
        print(f"  {description}\n")


def main():
    """Основная функция тестирования"""
    print("🔬 ТЕСТИРОВАНИЕ СИСТЕМЫ ОБРАБОТКИ PDF СЕРТИФИКАТОВ")
    print("=" * 60)
    
    # Создаем тестовые данные
    user, material = create_test_data()
    
    # Показываем статистику
    show_statistics()
    
    # Тестируем извлечение текста
    test_text_extraction()
    
    # Тестируем генерацию превью
    test_preview_generation()
    
    # Тестируем поиск
    test_search_functionality()
    
    # Тестируем асинхронную обработку
    test_async_processing()
    
    # Показываем доступные команды
    print_available_commands()
    
    print("\n✨ Тестирование завершено!")
    print("📊 Для полного тестирования:")
    print("1. Загрузите PDF сертификаты через админку Django")
    print("2. Запустите: python manage.py reprocess_all_certificates")
    print("3. Проверьте API endpoints:")
    print("   GET /api/certificates/processing/search/?q=40X")
    print("   GET /api/certificates/processing/statistics/")


if __name__ == '__main__':
    from django.db.models import Count
    main()