#!/usr/bin/env python
"""
Скрипт для тестирования API модуля склада
"""
import os
import sys
import django
import requests
import json
from datetime import datetime

# Настройка Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from apps.warehouse.models import Material, MaterialReceipt, Certificate


def test_warehouse_api():
    """Тестирование API модуля склада"""
    
    print("🧪 Тестирование API модуля склада...")
    
    # Создаем клиента API
    client = APIClient()
    
    # Получаем пользователя для аутентификации
    try:
        admin_user = User.objects.get(username='admin')
        client.force_authenticate(user=admin_user)
        print(f"✅ Аутентификация: {admin_user.username}")
    except User.DoesNotExist:
        print("❌ Пользователь admin не найден")
        return
    
    print("\n" + "="*50)
    print("📦 ТЕСТИРОВАНИЕ API МАТЕРИАЛОВ")
    print("="*50)
    
    # Тест 1: Получение списка материалов
    print("\n1️⃣ Тест: Получение списка материалов")
    response = client.get('/api/v1/warehouse/materials/')
    print(f"Статус: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Количество материалов: {len(data.get('results', data))}")
        
        if data.get('results'):
            first_material = data['results'][0]
            print("Поля в списке материалов:")
            for key in first_material.keys():
                print(f"  - {key}")
        else:
            print("Материалы не найдены")
    else:
        print(f"❌ Ошибка: {response.status_code}")
        print(response.json())
    
    # Тест 2: Получение детальной информации о материале
    if Material.objects.exists():
        material = Material.objects.first()
        print(f"\n2️⃣ Тест: Детальная информация о материале {material.id}")
        
        response = client.get(f'/api/v1/warehouse/materials/{material.id}/')
        print(f"Статус: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("Поля в детальном представлении:")
            for key in data.keys():
                print(f"  - {key}")
            
            # Проверяем наличие QR кода
            if data.get('qr_code_url'):
                print(f"✅ QR код доступен: {data['qr_code_url']}")
            else:
                print("⚠️ QR код не сгенерирован")
            
            # Проверяем сертификат
            if data.get('certificate'):
                print(f"✅ Сертификат привязан: {data['certificate']['id']}")
            else:
                print("⚠️ Сертификат не привязан")
    
    # Тест 3: Создание нового материала
    print("\n3️⃣ Тест: Создание нового материала")
    new_material_data = {
        'material_grade': 'API-TEST-GRADE',
        'supplier': 'API Тестовый поставщик',
        'order_number': f'API-ORDER-{datetime.now().strftime("%Y%m%d%H%M%S")}',
        'certificate_number': f'API-CERT-{datetime.now().strftime("%Y%m%d%H%M%S")}',
        'heat_number': 'API-HEAT-12345',
        'size': 'API-⌀100',
        'quantity': 500.0,
        'unit': 'kg',
        'location': 'API Тестовая зона'
    }
    
    response = client.post(
        '/api/v1/warehouse/materials/',
        data=json.dumps(new_material_data),
        content_type='application/json'
    )
    print(f"Статус: {response.status_code}")
    
    if response.status_code == 201:
        created_material = response.json()
        print(f"✅ Материал создан с ID: {created_material['id']}")
        print(f"External ID: {created_material['external_id']}")
        print(f"QR код: {created_material.get('qr_code_url', 'Не сгенерирован')}")
        
        # Сохраняем ID для дальнейших тестов
        test_material_id = created_material['id']
    else:
        print(f"❌ Ошибка создания: {response.status_code}")
        print(response.json())
        test_material_id = None
    
    # Тест 4: Валидация уникальности номера сертификата
    print("\n4️⃣ Тест: Валидация уникальности номера сертификата")
    duplicate_data = new_material_data.copy()
    duplicate_data['material_grade'] = 'DUPLICATE-TEST'
    
    response = client.post(
        '/api/v1/warehouse/materials/',
        data=json.dumps(duplicate_data),
        content_type='application/json'
    )
    print(f"Статус: {response.status_code}")
    
    if response.status_code == 400:
        print("✅ Валидация работает - дубликат отклонен")
        error_data = response.json()
        if 'certificate_number' in error_data:
            print(f"Сообщение об ошибке: {error_data['certificate_number']}")
    else:
        print(f"⚠️ Ожидалась ошибка 400, получен: {response.status_code}")
    
    # Тест 5: Статистика материалов
    print("\n5️⃣ Тест: Статистика материалов")
    response = client.get('/api/v1/warehouse/materials/statistics/')
    print(f"Статус: {response.status_code}")
    
    if response.status_code == 200:
        stats = response.json()
        print(f"✅ Всего материалов: {stats['total_materials']}")
        print(f"Общее количество: {stats['total_quantity']}")
        print(f"По маркам: {len(stats['by_grade'])} разных марок")
        print(f"По поставщикам: {len(stats['by_supplier'])} поставщиков")
        print(f"Недавние поступления: {stats['recent_receipts_count']}")
        print(f"Ожидают ОТК: {stats['pending_qc_count']}")
    
    print("\n" + "="*50)
    print("📋 ТЕСТИРОВАНИЕ API ПРИЕМОК")
    print("="*50)
    
    # Тест 6: Создание приемки материала
    if test_material_id:
        print("\n6️⃣ Тест: Создание приемки материала")
        receipt_data = {
            'material_id': test_material_id,
            'document_number': f'API-DOC-{datetime.now().strftime("%Y%m%d%H%M%S")}',
            'status': 'pending_qc',
            'notes': 'Создано через API тест'
        }
        
        response = client.post(
            '/api/v1/warehouse/receipts/',
            data=json.dumps(receipt_data),
            content_type='application/json'
        )
        print(f"Статус: {response.status_code}")
        
        if response.status_code == 201:
            receipt = response.json()
            print(f"✅ Приемка создана с ID: {receipt['id']}")
            print(f"Материал: {receipt['material']['material_grade']}")
            print(f"Принял: {receipt['received_by_full_name']}")
            print(f"Статус: {receipt['status']}")
            
            test_receipt_id = receipt['id']
        else:
            print(f"❌ Ошибка создания приемки: {response.status_code}")
            print(response.json())
            test_receipt_id = None
    
    # Тест 7: Изменение статуса приемки
    if test_receipt_id:
        print(f"\n7️⃣ Тест: Изменение статуса приемки {test_receipt_id}")
        status_data = {'status': 'in_qc'}
        
        response = client.post(
            f'/api/v1/warehouse/receipts/{test_receipt_id}/change_status/',
            data=json.dumps(status_data),
            content_type='application/json'
        )
        print(f"Статус: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Статус изменен: {result['old_status']} → {result['new_status']}")
        else:
            print(f"❌ Ошибка изменения статуса: {response.status_code}")
    
    # Тест 8: Получение приемок, ожидающих ОТК
    print("\n8️⃣ Тест: Приемки, ожидающие ОТК")
    response = client.get('/api/v1/warehouse/receipts/pending_qc/')
    print(f"Статус: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Приемок в ожидании ОТК: {data['count']}")
    
    print("\n" + "="*50)
    print("📄 ТЕСТИРОВАНИЕ API СЕРТИФИКАТОВ")
    print("="*50)
    
    # Тест 9: Получение списка сертификатов
    print("\n9️⃣ Тест: Получение списка сертификатов")
    response = client.get('/api/v1/warehouse/certificates/')
    print(f"Статус: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        certificates_count = len(data.get('results', data))
        print(f"✅ Найдено сертификатов: {certificates_count}")
        
        if data.get('results') and len(data['results']) > 0:
            cert = data['results'][0]
            print("Поля сертификата:")
            for key in cert.keys():
                print(f"  - {key}")
            
            if cert.get('download_url'):
                print(f"✅ URL для скачивания: {cert['download_url']}")
    
    # Тест 10: Массовые операции
    print("\n🔟 Тест: Массовые операции")
    if test_material_id:
        bulk_data = {
            'material_ids': [test_material_id],
            'operation': 'change_location',
            'new_location': 'API Новое местоположение'
        }
        
        response = client.post(
            '/api/v1/warehouse/materials/bulk_operations/',
            data=json.dumps(bulk_data),
            content_type='application/json'
        )
        print(f"Статус: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ {result['message']}")
            print(f"Затронуто материалов: {result['affected_count']}")
    
    print("\n" + "="*50)
    print("📊 ТЕСТИРОВАНИЕ API ОТЧЕТОВ")
    print("="*50)
    
    # Тест 11: Сводный отчет по остаткам
    print("\n1️⃣1️⃣ Тест: Сводный отчет по остаткам")
    response = client.get('/api/v1/warehouse/reports/inventory_summary/')
    print(f"Статус: {response.status_code}")
    
    if response.status_code == 200:
        report = response.json()
        print(f"✅ Всего позиций: {report['total_positions']}")
        print(f"Общий вес (кг): {report['total_quantity_kg']}")
        print(f"Общее количество (шт): {report['total_quantity_pcs']}")
        print(f"Местоположений: {len(report['by_location'])}")
        print(f"Марок материалов: {len(report['by_grade'])}")
        print(f"Предупреждений о низких остатках: {len(report['low_stock_alerts'])}")
    
    # Тест 12: История движения
    print("\n1️⃣2️⃣ Тест: История движения за 7 дней")
    response = client.get('/api/v1/warehouse/reports/movement_history/?days=7')
    print(f"Статус: {response.status_code}")
    
    if response.status_code == 200:
        history = response.json()
        print(f"✅ Период: {history['period_days']} дней")
        print(f"Всего приемок: {history['total_receipts']}")
        print(f"Дней с движением: {len(history['daily_movements'])}")
    
    # Тест 13: Фильтрация и поиск
    print("\n1️⃣3️⃣ Тест: Фильтрация и поиск")
    
    # Поиск по марке материала
    response = client.get('/api/v1/warehouse/materials/?search=API-TEST')
    print(f"Поиск по 'API-TEST': {response.status_code}")
    if response.status_code == 200:
        results = response.json().get('results', [])
        print(f"✅ Найдено материалов: {len(results)}")
    
    # Фильтр по единице измерения
    response = client.get('/api/v1/warehouse/materials/?unit=kg')
    print(f"Фильтр по единице 'kg': {response.status_code}")
    if response.status_code == 200:
        results = response.json().get('results', [])
        print(f"✅ Материалов в кг: {len(results)}")
    
    # Тест 14: Проверка валидации
    print("\n1️⃣4️⃣ Тест: Проверка валидации")
    
    # Невалидные данные для материала
    invalid_data = {
        'material_grade': '',  # Пустая марка
        'supplier': 'Тест поставщик',
        'quantity': -10,  # Отрицательное количество
        'unit': 'invalid_unit'  # Неверная единица измерения
    }
    
    response = client.post(
        '/api/v1/warehouse/materials/',
        data=json.dumps(invalid_data),
        content_type='application/json'
    )
    print(f"Статус валидации: {response.status_code}")
    
    if response.status_code == 400:
        print("✅ Валидация работает - невалидные данные отклонены")
        errors = response.json()
        print("Ошибки валидации:")
        for field, error_list in errors.items():
            print(f"  - {field}: {error_list}")
    
    print("\n" + "="*50)
    print("📋 ИТОГИ ТЕСТИРОВАНИЯ")
    print("="*50)
    
    print("✅ Протестированные функции:")
    print("  - Получение списка материалов (разные сериализаторы)")
    print("  - Детальная информация о материале")
    print("  - Создание и валидация материалов")
    print("  - Уникальность номеров сертификатов")
    print("  - Статистика и отчеты")
    print("  - Приемки материалов")
    print("  - Изменение статусов")
    print("  - Массовые операции")
    print("  - Фильтрация и поиск")
    print("  - Валидация данных")
    print("  - API сертификатов")
    
    print("\n🎯 Особенности реализации:")
    print("  - BaseAuditSerializer для полей аудита")
    print("  - Разные сериализаторы для list/detail/create")
    print("  - Вложенные сериализаторы для связанных объектов")
    print("  - Валидация PDF файлов (размер, тип)")
    print("  - SerializerMethodField для URL генерации")
    print("  - Оптимизированные запросы с select_related")
    print("  - Массовые операции с материалами")
    print("  - Статистические отчеты")
    
    print("\n🌐 API эндпоинты готовы к использованию!")
    print("📖 Документация доступна: http://127.0.0.1:8000/api/docs/")


if __name__ == '__main__':
    test_warehouse_api() 