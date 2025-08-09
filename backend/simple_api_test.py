#!/usr/bin/env python
import os
import django
import json
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from rest_framework.test import APIClient
from django.contrib.auth.models import User

def test_api():
    client = APIClient()
    admin = User.objects.get(username='admin')
    client.force_authenticate(user=admin)

    # Тест списка материалов
    print("📦 Тест API материалов...")
    response = client.get('/api/v1/warehouse/materials/')
    print(f"Статус: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        count = len(data.get('results', data))
        print(f"Материалов найдено: {count}")
        
        if count > 0:
            print("Поля MaterialListSerializer:")
            for field in sorted(data['results'][0].keys()):
                print(f"  - {field}")
    
    # Тест создания материала
    print("\n📝 Тест создания материала...")
    timestamp = datetime.now().strftime("%H%M%S")
    material_data = {
        'material_grade': f'API-TEST-{timestamp}',
        'supplier': 'API Поставщик',
        'order_number': f'ORDER-{timestamp}',
        'certificate_number': f'CERT-{timestamp}',
        'heat_number': 'HEAT-123456',
        'size': '⌀100',
        'quantity': 250.5,
        'unit': 'kg',
        'location': 'Зона А1'
    }
    
    response = client.post(
        '/api/v1/warehouse/materials/',
        data=json.dumps(material_data),
        content_type='application/json'
    )
    print(f"Статус создания: {response.status_code}")
    
    if response.status_code == 201:
        created = response.json()
        print(f"✅ Материал создан с ID: {created['id']}")
        print(f"External ID: {created['external_id']}")
        print(f"QR код: {created.get('qr_code_url', 'Не сгенерирован')}")
        
        # Тест приемки
        print("\n📋 Тест создания приемки...")
        receipt_data = {
            'material_id': created['id'],
            'document_number': f'DOC-{timestamp}',
            'status': 'pending_qc',
            'notes': 'API тест приемки'
        }
        
        receipt_response = client.post(
            '/api/v1/warehouse/receipts/',
            data=json.dumps(receipt_data),
            content_type='application/json'
        )
        print(f"Статус приемки: {receipt_response.status_code}")
        
        if receipt_response.status_code == 201:
            receipt = receipt_response.json()
            print(f"✅ Приемка создана с ID: {receipt['id']}")
            print(f"Принял: {receipt['received_by_full_name']}")
    
    # Тест статистики
    print("\n📊 Тест статистики...")
    response = client.get('/api/v1/warehouse/materials/statistics/')
    print(f"Статус: {response.status_code}")
    
    if response.status_code == 200:
        stats = response.json()
        print(f"Всего материалов: {stats['total_materials']}")
        print(f"Общее количество: {stats['total_quantity']}")
        print(f"По маркам: {len(stats['by_grade'])} разных марок")
    
    print("\n✅ API тестирование завершено!")

if __name__ == '__main__':
    test_api() 