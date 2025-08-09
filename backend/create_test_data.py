#!/usr/bin/env python
"""
Скрипт для создания тестовых данных для модуля склада
"""
import os
import sys
import django

# Настройка Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from apps.warehouse.models import Material, MaterialReceipt, Certificate
from decimal import Decimal


def create_test_data():
    """Создание тестовых данных"""
    
    print("Создание тестовых данных для модуля склада...")
    
    # Получаем или создаем пользователей
    admin_user, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@metalqms.local',
            'is_staff': True,
            'is_superuser': True
        }
    )
    
    warehouse_user, created = User.objects.get_or_create(
        username='warehouse_operator',
        defaults={
            'email': 'warehouse@metalqms.local',
            'first_name': 'Иван',
            'last_name': 'Складской'
        }
    )
    
    print(f"Пользователи готовы: {admin_user.username}, {warehouse_user.username}")
    
    # Создаем тестовые материалы
    test_materials = [
        {
            'material_grade': '40X',
            'supplier': 'МеталлТорг',
            'order_number': 'ЗК-2024-001',
            'certificate_number': 'СТ-40X-240115',
            'heat_number': 'П-45789',
            'size': '⌀50x6000',
            'quantity': Decimal('1250.500'),
            'unit': 'kg',
            'location': 'Стеллаж А-1-3'
        },
        {
            'material_grade': '20X13',
            'supplier': 'СпецСталь',
            'order_number': 'ЗК-2024-002',
            'certificate_number': 'СТ-20X13-240116',
            'heat_number': 'П-45790',
            'size': '⌀100x3000',
            'quantity': Decimal('850.750'),
            'unit': 'kg',
            'location': 'Стеллаж Б-2-1'
        },
        {
            'material_grade': '12X18H10T',
            'supplier': 'УралМет',
            'order_number': 'ЗК-2024-003',
            'certificate_number': 'СТ-12X18H10T-240117',
            'heat_number': 'П-45791',
            'size': 'Лист 10x1500x6000',
            'quantity': Decimal('25'),
            'unit': 'pcs',
            'location': 'Площадка В-1'
        },
        {
            'material_grade': '09Г2С',
            'supplier': 'МеталлТорг',
            'order_number': 'ЗК-2024-004',
            'certificate_number': 'СТ-09Г2С-240118',
            'heat_number': 'П-45792',
            'size': '⌀150x12000',
            'quantity': Decimal('2100.000'),
            'unit': 'meters',
            'location': 'Стеллаж Г-1-5'
        }
    ]
    
    created_materials = []
    
    for material_data in test_materials:
        material, created = Material.objects.get_or_create(
            certificate_number=material_data['certificate_number'],
            defaults={
                **material_data,
                'created_by': admin_user,
                'updated_by': admin_user
            }
        )
        created_materials.append(material)
        
        if created:
            print(f"✅ Создан материал: {material}")
            
            # Создаем поступление для каждого материала
            receipt, receipt_created = MaterialReceipt.objects.get_or_create(
                material=material,
                document_number=f"ПН-{material_data['order_number'][-3:]}",
                defaults={
                    'received_by': warehouse_user,
                    'status': 'pending_qc',
                    'notes': f'Поступление материала {material.material_grade} от {material.supplier}',
                    'created_by': warehouse_user,
                    'updated_by': warehouse_user
                }
            )
            
            if receipt_created:
                print(f"  📄 Создано поступление: {receipt}")
        else:
            print(f"⚠️  Материал уже существует: {material}")
    
    print(f"\n✅ Создано материалов: {len(created_materials)}")
    
    # Выводим статистику
    print("\n📊 Статистика:")
    print(f"Всего материалов: {Material.objects.count()}")
    print(f"Всего поступлений: {MaterialReceipt.objects.count()}")
    print(f"Всего сертификатов: {Certificate.objects.count()}")
    
    # Выводим примеры QR кодов
    print("\n🔗 QR коды материалов:")
    for material in Material.objects.all()[:2]:
        if material.qr_code:
            print(f"  {material.material_grade}: {material.qr_code.url}")
        else:
            print(f"  {material.material_grade}: QR код не создан")
    
    print("\n🎉 Тестовые данные успешно созданы!")
    print("🌐 Админка доступна по адресу: http://127.0.0.1:8003/admin/")
    print("👤 Логин: admin, Пароль: admin123")


if __name__ == '__main__':
    create_test_data() 