#!/usr/bin/env python
"""
Скрипт для создания тестовых данных для модуля лаборатории
"""
import os
import sys
import django
from datetime import datetime, timedelta

# Настройка Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from apps.warehouse.models import MaterialReceipt
from apps.laboratory.models import TestEquipment, LabTestRequest, LabTestResult, TestStandard


def create_laboratory_test_data():
    """Создание тестовых данных для модуля лаборатории"""
    
    print("Создание тестовых данных для модуля лаборатории (ЦЗЛ)...")
    
    # Получаем пользователей
    admin_user = User.objects.get(username='admin')
    
    # Создаем лабораторных специалистов
    lab_manager, created = User.objects.get_or_create(
        username='lab_manager',
        defaults={
            'email': 'lab_manager@metalqms.local',
            'first_name': 'Анна',
            'last_name': 'Заведующая'
        }
    )
    
    lab_technician, created = User.objects.get_or_create(
        username='lab_technician',
        defaults={
            'email': 'lab_tech@metalqms.local',
            'first_name': 'Игорь',
            'last_name': 'Лаборант'
        }
    )
    
    chemist, created = User.objects.get_or_create(
        username='chemist',
        defaults={
            'email': 'chemist@metalqms.local',
            'first_name': 'Елена',
            'last_name': 'Химик'
        }
    )
    
    print(f"Лабораторный персонал: {lab_manager.username}, {lab_technician.username}, {chemist.username}")
    
    # Создаем испытательное оборудование
    print("\n🔬 Создание испытательного оборудования...")
    
    equipment_data = [
        {
            'name': 'Спектрометр АРЛ 3460',
            'equipment_type': 'spectrometer',
            'model': 'ARL 3460',
            'serial_number': 'SPR-2023-001',
            'manufacturer': 'Thermo Fisher Scientific',
            'calibration_date': datetime.now().date() - timedelta(days=30),
            'calibration_interval_months': 12,
            'location': 'Лаборатория химанализа',
            'responsible_person': chemist,
            'accuracy_class': '0.001%',
            'measurement_range': 'C: 0.008-6.67%, Si: 0.01-4.0%, Mn: 0.10-2.0%'
        },
        {
            'name': 'Разрывная машина Instron 5982',
            'equipment_type': 'tensile_machine',
            'model': 'Instron 5982',
            'serial_number': 'TEN-2023-002',
            'manufacturer': 'Instron',
            'calibration_date': datetime.now().date() - timedelta(days=90),
            'calibration_interval_months': 6,
            'location': 'Зал механических испытаний',
            'responsible_person': lab_technician,
            'accuracy_class': '±0.5%',
            'measurement_range': '0-100 кН'
        },
        {
            'name': 'Твердомер Rockwell HR-430MS',
            'equipment_type': 'hardness_tester',
            'model': 'HR-430MS',
            'serial_number': 'HRD-2023-003',
            'manufacturer': 'Mitutoyo',
            'calibration_date': datetime.now().date() - timedelta(days=200),  # Просрочена!
            'calibration_interval_months': 6,
            'location': 'Лаборатория твердости',
            'responsible_person': lab_technician,
            'accuracy_class': '±1 HRC',
            'measurement_range': '20-70 HRC'
        },
        {
            'name': 'УЗ дефектоскоп УД2-12',
            'equipment_type': 'ultrasonic_detector',
            'model': 'УД2-12',
            'serial_number': 'USD-2023-004',
            'manufacturer': 'КРОПУС',
            'calibration_date': datetime.now().date() - timedelta(days=10),
            'calibration_interval_months': 12,
            'location': 'Участок НК',
            'responsible_person': lab_technician,
            'accuracy_class': '±2%',
            'measurement_range': '0.8-300 мм (сталь)'
        },
        {
            'name': 'Микроскоп Olympus GX53',
            'equipment_type': 'microscope',
            'model': 'GX53',
            'serial_number': 'MIC-2023-005',
            'manufacturer': 'Olympus',
            'calibration_date': datetime.now().date() - timedelta(days=350),  # Скоро калибровка
            'calibration_interval_months': 12,
            'location': 'Металлографическая лаборатория',
            'responsible_person': chemist,
            'accuracy_class': '0.1 мкм',
            'measurement_range': '50x-1000x'
        }
    ]
    
    created_equipment = []
    for eq_data in equipment_data:
        equipment, created = TestEquipment.objects.get_or_create(
            serial_number=eq_data['serial_number'],
            defaults={
                **eq_data,
                'created_by': admin_user,
                'updated_by': admin_user
            }
        )
        created_equipment.append(equipment)
        
        if created:
            print(f"✅ Создано оборудование: {equipment}")
            status = equipment.get_calibration_status()
            print(f"   Статус калибровки: {equipment.get_calibration_status_display()}")
    
    # Создаем стандарты испытаний
    print("\n📋 Создание стандартов испытаний...")
    
    standards_data = [
        {
            'name': 'Сталь углеродистая обыкновенного качества',
            'standard_number': 'ГОСТ 380-2005',
            'test_type': 'chemical_analysis',
            'material_grades': '20, Ст3, 09Г2С',
            'requirements': {
                'C': {'max': 0.22},
                'Si': {'max': 0.17},
                'Mn': {'max': 0.65},
                'P': {'max': 0.040},
                'S': {'max': 0.050}
            },
            'test_method': 'Спектральный анализ по ГОСТ 18895'
        },
        {
            'name': 'Сталь конструкционная легированная',
            'standard_number': 'ГОСТ 4543-2016',
            'test_type': 'chemical_analysis',
            'material_grades': '40X, 30ХГСА, 12X18H10T',
            'requirements': {
                'C': {'min': 0.37, 'max': 0.44},
                'Cr': {'min': 0.80, 'max': 1.10},
                'P': {'max': 0.035},
                'S': {'max': 0.035}
            },
            'test_method': 'Спектральный анализ по ГОСТ 18895'
        },
        {
            'name': 'Механические свойства стали при растяжении',
            'standard_number': 'ГОСТ 1497-84',
            'test_type': 'mechanical_properties',
            'material_grades': '',  # Универсальный
            'requirements': {
                'yield_strength': {'min': 235},
                'tensile_strength': {'min': 380},
                'elongation': {'min': 21}
            },
            'test_method': 'Испытание на растяжение по ГОСТ 1497'
        }
    ]
    
    for std_data in standards_data:
        standard, created = TestStandard.objects.get_or_create(
            standard_number=std_data['standard_number'],
            defaults={
                **std_data,
                'created_by': admin_user,
                'updated_by': admin_user
            }
        )
        
        if created:
            print(f"✅ Создан стандарт: {standard}")
    
    # Создаем запросы на испытания
    print("\n🧪 Создание запросов на испытания...")
    
    material_receipts = MaterialReceipt.objects.all()[:3]
    
    test_requests_data = [
        {
            'material_receipt': material_receipts[0] if len(material_receipts) > 0 else None,
            'test_type': 'chemical_analysis',
            'priority': 'high',
            'test_requirements': 'Полный химический анализ согласно ГОСТ 380-2005',
            'requested_by': lab_manager,
            'assigned_to': chemist,
            'required_completion_date': datetime.now().date() + timedelta(days=2)
        },
        {
            'material_receipt': material_receipts[1] if len(material_receipts) > 1 else None,
            'test_type': 'mechanical_properties',
            'priority': 'normal',
            'test_requirements': 'Испытание на растяжение, определение σ0.2, σв, δ5',
            'requested_by': lab_manager,
            'assigned_to': lab_technician,
            'required_completion_date': datetime.now().date() + timedelta(days=5)
        },
        {
            'material_receipt': material_receipts[2] if len(material_receipts) > 2 else None,
            'test_type': 'ultrasonic',
            'priority': 'urgent',
            'test_requirements': 'УЗК контроль на наличие внутренних дефектов',
            'requested_by': lab_manager,
            'assigned_to': lab_technician,
            'required_completion_date': datetime.now().date() + timedelta(days=1),
            'status': 'in_progress'
        }
    ]
    
    created_requests = []
    for req_data in test_requests_data:
        if req_data['material_receipt']:  # Проверяем что материал есть
            test_request, created = LabTestRequest.objects.get_or_create(
                material_receipt=req_data['material_receipt'],
                test_type=req_data['test_type'],
                defaults={
                    **req_data,
                    'created_by': req_data['requested_by'],
                    'updated_by': req_data['requested_by']
                }
            )
            created_requests.append(test_request)
            
            if created:
                print(f"✅ Создан запрос: {test_request}")
    
    # Создаем результаты для некоторых испытаний
    print("\n📊 Создание результатов испытаний...")
    
    if created_requests:
        # Результат химического анализа
        first_request = created_requests[0]
        if first_request.test_type == 'chemical_analysis':
            chemical_result = {
                'chemical_composition': {
                    'C': 0.19,
                    'Si': 0.15,
                    'Mn': 0.58,
                    'P': 0.028,
                    'S': 0.035,
                    'Cr': 0.02,
                    'Ni': 0.03,
                    'Cu': 0.15
                }
            }
            
            test_result, created = LabTestResult.objects.get_or_create(
                test_request=first_request,
                defaults={
                    'performed_by': chemist,
                    'conclusion': 'passed',
                    'certificate_number': f'XA-{datetime.now().strftime("%Y%m%d")}-001',
                    'results': chemical_result,
                    'test_conditions': {
                        'temperature': '20±2°C',
                        'humidity': '60±5%',
                        'atmosphere': 'argon'
                    },
                    'sample_description': f'Образец стали {first_request.material_receipt.material.material_grade}',
                    'test_method': 'ГОСТ 18895-97 (Спектральный анализ)',
                    'comments': 'Химический состав соответствует требованиям ГОСТ 380-2005',
                    'created_by': chemist,
                    'updated_by': chemist
                }
            )
            
            if created:
                # Привязываем оборудование
                spectrometer = TestEquipment.objects.filter(equipment_type='spectrometer').first()
                if spectrometer:
                    test_result.equipment_used.add(spectrometer)
                
                print(f"✅ Создан результат: {test_result}")
                first_request.status = 'completed'
                first_request.save()
        
        # Результат механических испытаний
        if len(created_requests) > 1:
            second_request = created_requests[1]
            if second_request.test_type == 'mechanical_properties':
                mechanical_result = {
                    'mechanical_properties': {
                        'yield_strength': 380,  # σ0.2, МПа
                        'tensile_strength': 520,  # σв, МПа
                        'elongation': 23,  # δ5, %
                        'reduction_of_area': 65,  # ψ, %
                        'test_temperature': 20
                    }
                }
                
                test_result, created = LabTestResult.objects.get_or_create(
                    test_request=second_request,
                    defaults={
                        'performed_by': lab_technician,
                        'conclusion': 'passed',
                        'certificate_number': f'MP-{datetime.now().strftime("%Y%m%d")}-001',
                        'results': mechanical_result,
                        'test_conditions': {
                            'temperature': '20±2°C',
                            'test_speed': '10 мм/мин'
                        },
                        'sample_description': f'Цилиндрический образец ⌀10мм из {second_request.material_receipt.material.material_grade}',
                        'test_method': 'ГОСТ 1497-84',
                        'comments': 'Механические свойства соответствуют техническим требованиям',
                        'created_by': lab_technician,
                        'updated_by': lab_technician
                    }
                )
                
                if created:
                    # Привязываем оборудование
                    tensile_machine = TestEquipment.objects.filter(equipment_type='tensile_machine').first()
                    if tensile_machine:
                        test_result.equipment_used.add(tensile_machine)
                    
                    print(f"✅ Создан результат: {test_result}")
                    second_request.status = 'completed'
                    second_request.save()
    
    # Выводим статистику
    print("\n📊 Статистика модуля лаборатории:")
    print(f"Всего оборудования: {TestEquipment.objects.count()}")
    print(f"Активного оборудования: {TestEquipment.objects.filter(is_active=True).count()}")
    
    # Статистика калибровки
    overdue_count = sum(1 for eq in TestEquipment.objects.all() if eq.is_overdue())
    warning_count = sum(1 for eq in TestEquipment.objects.all() if eq.needs_calibration() and not eq.is_overdue())
    
    print(f"Просроченная калибровка: {overdue_count}")
    print(f"Требует внимания: {warning_count}")
    
    print(f"Всего стандартов: {TestStandard.objects.count()}")
    print(f"Всего запросов на испытания: {LabTestRequest.objects.count()}")
    print(f"Завершенных испытаний: {LabTestRequest.objects.filter(status='completed').count()}")
    print(f"В процессе: {LabTestRequest.objects.filter(status='in_progress').count()}")
    print(f"Результатов испытаний: {LabTestResult.objects.count()}")
    
    # Статистика по типам испытаний
    print(f"\n🔬 Статистика по типам испытаний:")
    for test_type, display_name in LabTestRequest.TEST_TYPE_CHOICES:
        count = LabTestRequest.objects.filter(test_type=test_type).count()
        if count > 0:
            print(f"  {display_name}: {count}")
    
    # Статистика калибровки оборудования
    print(f"\n⚙️ Статус калибровки оборудования:")
    for equipment in TestEquipment.objects.all():
        status = equipment.get_calibration_status_display()
        days = equipment.days_until_calibration()
        print(f"  {equipment.name}: {status} ({days} дн.)")
    
    print("\n🎉 Тестовые данные для модуля лаборатории созданы!")
    print("🌐 Админка доступна по адресу: http://127.0.0.1:8000/admin/")
    print("👤 Логин: admin, Пароль: admin123")


if __name__ == '__main__':
    create_laboratory_test_data() 