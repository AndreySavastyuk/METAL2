#!/usr/bin/env python
"""
Скрипт для создания тестовых данных для модуля контроля качества
"""
import os
import sys
import django

# Настройка Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from apps.warehouse.models import Material, MaterialReceipt
from apps.quality.models import QCInspection, QCChecklist, QCChecklistItem, QCInspectionResult


def create_qc_test_data():
    """Создание тестовых данных для модуля ОТК"""
    
    print("Создание тестовых данных для модуля ОТК...")
    
    # Получаем пользователей
    admin_user = User.objects.get(username='admin')
    qc_inspector, created = User.objects.get_or_create(
        username='qc_inspector',
        defaults={
            'email': 'qc@metalqms.local',
            'first_name': 'Петр',
            'last_name': 'Контролер'
        }
    )
    
    print(f"Инспектор ОТК: {qc_inspector.username}")
    
    # Создаем чек-листы
    print("\n📋 Создание чек-листов...")
    
    # Универсальный чек-лист для всех материалов
    universal_checklist, created = QCChecklist.objects.get_or_create(
        name='Универсальная проверка входящих материалов',
        material_grade='',
        defaults={
            'description': 'Базовая проверка для всех поступающих материалов',
            'version': '1.0',
            'created_by': admin_user,
            'updated_by': admin_user
        }
    )
    
    if created:
        print(f"✅ Создан универсальный чек-лист: {universal_checklist}")
        
        # Пункты универсального чек-листа
        universal_items = [
            {
                'order': 1,
                'description': 'Проверка соответствия марки материала документам',
                'is_critical': True,
                'acceptance_criteria': 'Марка материала на бирке должна соответствовать сертификату'
            },
            {
                'order': 2,
                'description': 'Проверка целостности упаковки',
                'is_critical': False,
                'acceptance_criteria': 'Упаковка должна быть неповрежденной, без признаков коррозии'
            },
            {
                'order': 3,
                'description': 'Проверка комплектности документов',
                'is_critical': True,
                'acceptance_criteria': 'Наличие сертификата качества и паспорта материала'
            },
            {
                'order': 4,
                'description': 'Визуальный контроль поверхности',
                'is_critical': False,
                'acceptance_criteria': 'Отсутствие видимых дефектов, трещин, вмятин'
            },
            {
                'order': 5,
                'description': 'Проверка геометрических размеров (выборочно)',
                'is_critical': False,
                'acceptance_criteria': 'Отклонения не должны превышать допуски ГОСТ'
            }
        ]
        
        for item_data in universal_items:
            QCChecklistItem.objects.create(
                checklist=universal_checklist,
                created_by=admin_user,
                updated_by=admin_user,
                **item_data
            )
    
    # Чек-лист для нержавеющих сталей
    stainless_checklist, created = QCChecklist.objects.get_or_create(
        name='Проверка нержавеющих сталей',
        material_grade='X18H10',
        defaults={
            'description': 'Специальная проверка для нержавеющих сталей',
            'version': '1.0',
            'created_by': admin_user,
            'updated_by': admin_user
        }
    )
    
    if created:
        print(f"✅ Создан чек-лист для нержавеющих сталей: {stainless_checklist}")
        
        stainless_items = [
            {
                'order': 1,
                'description': 'Проверка магнитности материала',
                'is_critical': True,
                'acceptance_criteria': 'Материал должен быть немагнитным или слабомагнитным'
            },
            {
                'order': 2,
                'description': 'Контроль химического состава (по сертификату)',
                'is_critical': True,
                'acceptance_criteria': 'Содержание Cr ≥ 17%, Ni ≥ 8% для аустенитных сталей'
            },
            {
                'order': 3,
                'description': 'Проверка на отсутствие карбидных выделений',
                'is_critical': False,
                'acceptance_criteria': 'Отсутствие видимых карбидных включений'
            }
        ]
        
        for item_data in stainless_items:
            QCChecklistItem.objects.create(
                checklist=stainless_checklist,
                created_by=admin_user,
                updated_by=admin_user,
                **item_data
            )
    
    # Чек-лист для конструкционных сталей
    structural_checklist, created = QCChecklist.objects.get_or_create(
        name='Проверка конструкционных сталей',
        material_grade='40X',
        defaults={
            'description': 'Проверка конструкционных легированных сталей',
            'version': '1.0',
            'created_by': admin_user,
            'updated_by': admin_user
        }
    )
    
    if created:
        print(f"✅ Создан чек-лист для конструкционных сталей: {structural_checklist}")
        
        structural_items = [
            {
                'order': 1,
                'description': 'Контроль твердости (по сертификату)',
                'is_critical': True,
                'acceptance_criteria': 'Твердость в пределах ГОСТ для данной марки'
            },
            {
                'order': 2,
                'description': 'Проверка термообработки',
                'is_critical': True,
                'acceptance_criteria': 'Наличие данных о термообработке в сертификате'
            },
            {
                'order': 3,
                'description': 'Ультразвуковой контроль (при необходимости)',
                'is_critical': False,
                'acceptance_criteria': 'Отсутствие внутренних дефектов по УЗК'
            }
        ]
        
        for item_data in structural_items:
            QCChecklistItem.objects.create(
                checklist=structural_checklist,
                created_by=admin_user,
                updated_by=admin_user,
                **item_data
            )
    
    # Создаем инспекции для существующих поступлений
    print("\n🔍 Создание инспекций...")
    
    material_receipts = MaterialReceipt.objects.all()[:3]  # Берем первые 3 поступления
    
    for receipt in material_receipts:
        inspection, created = QCInspection.objects.get_or_create(
            material_receipt=receipt,
            defaults={
                'inspector': qc_inspector,
                'status': 'in_progress',
                'comments': f'Плановая инспекция материала {receipt.material.material_grade}',
                'created_by': qc_inspector,
                'updated_by': qc_inspector
            }
        )
        
        if created:
            print(f"✅ Создана инспекция: {inspection}")
            
            # Автоматически создаются результаты через сигнал post_save
            results_count = inspection.inspection_results.count()
            print(f"  📝 Создано результатов: {results_count}")
            
            # Заполним некоторые результаты для демонстрации
            results = list(inspection.inspection_results.all())
            
            # Заполняем первые 2-3 результата
            for i, result in enumerate(results[:3]):
                if i == 0:  # Первый результат - пройден
                    result.result = 'passed'
                    result.notes = 'Соответствует требованиям'
                    result.measured_value = 'Соответствует'
                elif i == 1:  # Второй результат - условно пройден
                    result.result = 'passed'
                    result.notes = 'Незначительные замечания по упаковке'
                    result.measured_value = 'Удовлетворительно'
                elif i == 2:  # Третий результат - зависит от критичности
                    if result.checklist_item.is_critical:
                        result.result = 'passed'
                        result.notes = 'Документы в порядке'
                    else:
                        result.result = 'na'
                        result.notes = 'Не применимо для данного типа материала'
                
                result.inspector_signature = f'{qc_inspector.first_name} {qc_inspector.last_name}'
                result.updated_by = qc_inspector
                result.save()
    
    # Выводим статистику
    print("\n📊 Статистика модуля ОТК:")
    print(f"Всего чек-листов: {QCChecklist.objects.count()}")
    print(f"Всего пунктов чек-листов: {QCChecklistItem.objects.count()}")
    print(f"Критических пунктов: {QCChecklistItem.objects.filter(is_critical=True).count()}")
    print(f"Всего инспекций: {QCInspection.objects.count()}")
    print(f"Завершенных инспекций: {QCInspection.objects.filter(status='completed').count()}")
    print(f"В процессе: {QCInspection.objects.filter(status='in_progress').count()}")
    print(f"Всего результатов: {QCInspectionResult.objects.count()}")
    
    # Статистика по требованиям
    ppsd_required = QCInspection.objects.filter(requires_ppsd=True).count()
    uzk_required = QCInspection.objects.filter(requires_ultrasonic=True).count()
    
    print(f"\n🔬 Специальные требования:")
    print(f"Требуют ППСД: {ppsd_required}")
    print(f"Требуют УЗК: {uzk_required}")
    
    # Демонстрация автоопределения требований
    print(f"\n🤖 Автоопределение требований:")
    for inspection in QCInspection.objects.all():
        material = inspection.material_receipt.material
        print(f"  {material.material_grade} ({material.size}):")
        print(f"    ППСД: {'Да' if inspection.requires_ppsd else 'Нет'}")
        print(f"    УЗК: {'Да' if inspection.requires_ultrasonic else 'Нет'}")
    
    print("\n🎉 Тестовые данные для модуля ОТК созданы!")
    print("🌐 Админка доступна по адресу: http://127.0.0.1:8000/admin/")
    print("👤 Логин: admin, Пароль: admin123")


if __name__ == '__main__':
    create_qc_test_data() 