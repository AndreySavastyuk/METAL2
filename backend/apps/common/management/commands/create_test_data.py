"""
Команда для создания тестовых данных MetalQMS
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone
from datetime import timedelta
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Создание тестовых данных для демонстрации функционала MetalQMS'

    def add_arguments(self, parser):
        parser.add_argument(
            '--materials',
            type=int,
            default=15,
            help='Количество материалов для создания (по умолчанию: 15)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Очистить существующие тестовые данные'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Создание тестовых данных MetalQMS...'))

        if options['clear']:
            self.clear_test_data()

        self.create_users_and_groups()
        self.create_suppliers()
        self.create_material_grades()
        self.create_product_types()
        self.create_test_materials(options['materials'])
        self.create_ppsd_checklists()
        
        self.stdout.write(
            self.style.SUCCESS('✅ Тестовые данные созданы успешно!')
        )
        self.show_access_info()

    def clear_test_data(self):
        """Очистка тестовых данных"""
        self.stdout.write('🧹 Очистка существующих тестовых данных...')
        
        from apps.warehouse.models import Material, MaterialReceipt, Supplier
        from apps.quality.models import QCInspection
        from apps.laboratory.models import LabTestRequest
        
        # Удаляем только тестовые данные
        Material.objects.filter(supplier__name__icontains='Тест').delete()
        Supplier.objects.filter(name__icontains='Тест').delete()
        
        self.stdout.write(self.style.SUCCESS('  ✅ Тестовые данные очищены'))

    def create_users_and_groups(self):
        """Создание пользователей и групп"""
        self.stdout.write('👥 Создание пользователей и групп...')

        # Создание групп
        groups_data = [
            ('Warehouse', 'Сотрудники склада'),
            ('QC', 'Сотрудники ОТК'),
            ('Laboratory', 'Сотрудники лаборатории'),
            ('Production', 'Сотрудники производства'),
            ('Management', 'Руководство')
        ]

        for group_name, description in groups_data:
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                self.stdout.write(f'  ✅ Группа создана: {group_name}')

        # Создание пользователей
        users_data = [
            {
                'username': 'warehouse',
                'email': 'warehouse@metalqms.com',
                'password': 'test123',
                'first_name': 'Иван',
                'last_name': 'Складов',
                'groups': ['Warehouse']
            },
            {
                'username': 'qc_inspector',
                'email': 'qc@metalqms.com',
                'password': 'test123',
                'first_name': 'Петр',
                'last_name': 'Контролев',
                'groups': ['QC']
            },
            {
                'username': 'lab_technician',
                'email': 'lab@metalqms.com',
                'password': 'test123',
                'first_name': 'Мария',
                'last_name': 'Лабораторова',
                'groups': ['Laboratory']
            },
            {
                'username': 'production',
                'email': 'production@metalqms.com',
                'password': 'test123',
                'first_name': 'Сергей',
                'last_name': 'Производов',
                'groups': ['Production']
            },
            {
                'username': 'manager',
                'email': 'manager@metalqms.com',
                'password': 'test123',
                'first_name': 'Анна',
                'last_name': 'Менеджерова',
                'groups': ['Management']
            }
        ]

        for user_data in users_data:
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults={
                    'email': user_data['email'],
                    'first_name': user_data['first_name'],
                    'last_name': user_data['last_name'],
                    'is_active': True
                }
            )
            
            if created:
                user.set_password(user_data['password'])
                user.save()
                
                # Добавление в группы
                for group_name in user_data['groups']:
                    group = Group.objects.get(name=group_name)
                    user.groups.add(group)
                
                self.stdout.write(f'  ✅ Пользователь создан: {user.username}')

    def create_suppliers(self):
        """Создание поставщиков"""
        self.stdout.write('🏭 Создание поставщиков...')
        
        from apps.warehouse.models import Supplier
        
        suppliers_data = [
            {
                'name': 'МеталлТорг',
                'legal_name': 'ООО "МеталлТорг"',
                'inn': '7701234567',
                'kpp': '770101001',
                'address': 'г. Москва, ул. Металлургов, д. 10',
                'contact_person': 'Иванов Иван Иванович',
                'phone': '+7 (495) 123-45-67',
                'email': 'orders@metalltorg.ru'
            },
            {
                'name': 'СпецСталь',
                'legal_name': 'АО "Специальные стали"',
                'inn': '7702345678',
                'kpp': '770201001',
                'address': 'г. Санкт-Петербург, пр. Стальной, д. 25',
                'contact_person': 'Петров Петр Петрович',
                'phone': '+7 (812) 234-56-78',
                'email': 'sales@specstal.ru'
            },
            {
                'name': 'УралМет',
                'legal_name': 'ПАО "Уральский металлургический комбинат"',
                'inn': '6603456789',
                'kpp': '660301001',
                'address': 'г. Екатеринбург, ул. Уральская, д. 50',
                'contact_person': 'Сидоров Сидор Сидорович',
                'phone': '+7 (343) 345-67-89',
                'email': 'metal@uralmet.ru'
            },
            {
                'name': 'СибирьМеталл',
                'legal_name': 'ОАО "Сибирский металлургический завод"',
                'inn': '5404567890',
                'kpp': '540401001',
                'address': 'г. Новосибирск, ул. Металлистов, д. 33',
                'contact_person': 'Козлов Андрей Викторович',
                'phone': '+7 (383) 456-78-90',
                'email': 'supply@sibirmet.ru'
            }
        ]

        for supplier_data in suppliers_data:
            supplier, created = Supplier.objects.get_or_create(
                name=supplier_data['name'],
                defaults=supplier_data
            )
            if created:
                self.stdout.write(f'  ✅ Поставщик создан: {supplier.name}')

    def create_material_grades(self):
        """Создание марок материалов"""
        self.stdout.write('🔬 Создание марок материалов...')
        
        from apps.warehouse.models import MaterialGrade
        
        grades_data = [
            {'name': '40X', 'density': 7.85, 'description': 'Сталь конструкционная легированная'},
            {'name': '20X13', 'density': 7.70, 'description': 'Сталь нержавеющая мартенситного класса'},
            {'name': '12X18H10T', 'density': 7.90, 'description': 'Сталь нержавеющая аустенитного класса'},
            {'name': '09Г2С', 'density': 7.85, 'description': 'Сталь низколегированная'},
            {'name': 'Ст3', 'density': 7.87, 'description': 'Сталь углеродистая обыкновенного качества'},
            {'name': '45', 'density': 7.85, 'description': 'Сталь углеродистая качественная'},
            {'name': '30ХГСА', 'density': 7.85, 'description': 'Сталь легированная улучшаемая'},
            {'name': '65Г', 'density': 7.85, 'description': 'Сталь пружинная'},
        ]

        for grade_data in grades_data:
            grade, created = MaterialGrade.objects.get_or_create(
                name=grade_data['name'],
                defaults=grade_data
            )
            if created:
                self.stdout.write(f'  ✅ Марка создана: {grade.name}')

    def create_product_types(self):
        """Создание типов проката"""
        self.stdout.write('📏 Создание типов проката...')
        
        from apps.warehouse.models import ProductType
        
        types_data = [
            {'name': 'Круг', 'description': 'Прокат круглого сечения'},
            {'name': 'Лист', 'description': 'Листовой прокат'},
            {'name': 'Полоса', 'description': 'Полосовой прокат'},
            {'name': 'Уголок', 'description': 'Угловой профиль'},
            {'name': 'Швеллер', 'description': 'П-образный профиль'},
            {'name': 'Балка', 'description': 'Двутавровая балка'},
            {'name': 'Труба', 'description': 'Трубный прокат'},
        ]

        for type_data in types_data:
            product_type, created = ProductType.objects.get_or_create(
                name=type_data['name'],
                defaults=type_data
            )
            if created:
                self.stdout.write(f'  ✅ Тип проката создан: {product_type.name}')

    def create_test_materials(self, count):
        """Создание тестовых материалов"""
        self.stdout.write(f'📦 Создание {count} тестовых материалов...')
        
        from apps.warehouse.models import (
            Material, MaterialReceipt, Supplier, 
            MaterialGrade, ProductType
        )
        from apps.quality.models import QCInspection
        
        suppliers = list(Supplier.objects.all())
        grades = list(MaterialGrade.objects.all())
        product_types = list(ProductType.objects.all())
        
        if not suppliers or not grades or not product_types:
            self.stdout.write(
                self.style.ERROR('Необходимо сначала создать поставщиков, марки и типы проката')
            )
            return

        # Статусы для разнообразия
        statuses = ['pending_qc', 'in_qc', 'qc_completed', 'in_laboratory', 'approved']
        
        # Размеры для разных типов проката
        sizes_by_type = {
            'Круг': ['⌀12', '⌀16', '⌀20', '⌀25', '⌀32', '⌀40', '⌀50', '⌀63', '⌀80', '⌀100'],
            'Лист': ['2мм', '3мм', '4мм', '5мм', '6мм', '8мм', '10мм', '12мм', '16мм', '20мм'],
            'Полоса': ['20х3', '25х4', '30х4', '40х5', '50х5', '60х6', '80х8', '100х10'],
            'Уголок': ['25х25х3', '32х32х4', '40х40х4', '50х50х5', '63х63х6', '75х75х8'],
            'Швеллер': ['10П', '12П', '14П', '16П', '18П', '20П', '22П', '24П'],
            'Балка': ['10Б1', '12Б1', '14Б1', '16Б1', '18Б1', '20Б1', '22Б1'],
            'Труба': ['⌀32х3', '⌀42х3', '⌀48х3', '⌀57х3', '⌀76х4', '⌀89х4', '⌀108х4'],
        }

        warehouse_user = User.objects.filter(username='warehouse').first()
        qc_user = User.objects.filter(username='qc_inspector').first()

        for i in range(count):
            # Случайный выбор параметров
            supplier = random.choice(suppliers)
            grade = random.choice(grades)
            product_type = random.choice(product_types)
            
            # Размер в зависимости от типа проката
            sizes = sizes_by_type.get(product_type.name, ['размер'])
            size = random.choice(sizes)
            
            # Создание материала
            material = Material.objects.create(
                material_grade=grade.name,
                supplier=supplier.name,
                order_number=f'ЗК-2024-{1000 + i:04d}',
                certificate_number=f'CERT-{2024000 + i:06d}',
                heat_number=f'П{240000 + i:06d}',
                size=size,
                quantity=round(random.uniform(0.1, 10.0), 3),
                unit=random.choice(['т', 'кг', 'шт', 'м']),
                notes=f'Тестовый материал №{i+1}',
                created_by=warehouse_user,
                updated_by=warehouse_user
            )
            
            # Создание поступления
            receipt_date = timezone.now() - timedelta(days=random.randint(0, 30))
            receipt = MaterialReceipt.objects.create(
                material=material,
                document_number=f'ПН-{2024000 + i:06d}',
                receipt_date=receipt_date,
                received_by=warehouse_user,
                notes=f'Поступление материала {material.material_grade}',
                status=random.choice(statuses),
                created_by=warehouse_user,
                updated_by=warehouse_user
            )
            
            # Создание инспекции для части материалов
            if random.random() > 0.3:  # 70% материалов имеют инспекции
                inspection_statuses = ['draft', 'in_progress', 'completed']
                requires_ppsd = random.choice([True, False])
                
                inspection = QCInspection.objects.create(
                    material_receipt=receipt,
                    inspector=qc_user,
                    inspection_date=receipt_date + timedelta(hours=random.randint(1, 48)),
                    status=random.choice(inspection_statuses),
                    requires_ppsd=requires_ppsd,
                    visual_inspection=random.choice(['passed', 'failed', 'conditional']),
                    dimension_check=random.choice(['passed', 'failed', 'conditional']),
                    surface_quality=random.choice(['passed', 'failed', 'conditional']),
                    marking_check=random.choice(['passed', 'failed', 'conditional']),
                    packaging_check=random.choice(['passed', 'failed', 'conditional']),
                    notes=f'Инспекция материала {material.material_grade} - {size}',
                    created_by=qc_user,
                    updated_by=qc_user
                )
            
            if (i + 1) % 5 == 0:
                self.stdout.write(f'  ✅ Создано {i + 1} материалов...')

        self.stdout.write(self.style.SUCCESS(f'  ✅ Создано {count} тестовых материалов'))

    def create_ppsd_checklists(self):
        """Создание чек-листов ППСД"""
        self.stdout.write('📋 Создание чек-листов ППСД...')
        
        from apps.quality.models import PPSDChecklist
        
        checklists_data = [
            {
                'name': 'Стандартная проверка стали',
                'description': 'Базовый чек-лист для проверки стальных изделий',
                'checklist_items': [
                    'Проверка геометрических размеров',
                    'Контроль качества поверхности',
                    'Проверка маркировки',
                    'Контроль упаковки',
                    'Проверка сопроводительной документации'
                ]
            },
            {
                'name': 'Нержавеющие стали',
                'description': 'Специализированный чек-лист для нержавеющих сталей',
                'checklist_items': [
                    'Проверка геометрических размеров',
                    'Контроль качества поверхности',
                    'Проверка химического состава',
                    'Контроль коррозионной стойкости',
                    'Проверка механических свойств',
                    'Проверка маркировки',
                    'Контроль упаковки'
                ]
            },
            {
                'name': 'Листовой прокат',
                'description': 'Чек-лист для контроля листового проката',
                'checklist_items': [
                    'Измерение толщины листа',
                    'Проверка плоскостности',
                    'Контроль кромок',
                    'Проверка качества поверхности',
                    'Контроль размеров листа',
                    'Проверка маркировки'
                ]
            }
        ]

        for checklist_data in checklists_data:
            checklist, created = PPSDChecklist.objects.get_or_create(
                name=checklist_data['name'],
                defaults={
                    'description': checklist_data['description'],
                    'checklist_items': checklist_data['checklist_items']
                }
            )
            if created:
                self.stdout.write(f'  ✅ Чек-лист создан: {checklist.name}')

    def show_access_info(self):
        """Показать информацию о доступах"""
        info = """
🎉 Тестовые данные созданы успешно!

👥 Созданные пользователи:
   👤 admin          / admin123     (Администратор)
   📦 warehouse      / test123      (Сотрудник склада)
   🔍 qc_inspector   / test123      (Инспектор ОТК)
   🧪 lab_technician / test123      (Лаборант)
   🏭 production     / test123      (Производство)
   👔 manager        / test123      (Менеджер)

🏭 Поставщики: МеталлТорг, СпецСталь, УралМет, СибирьМеталл
🔬 Марки стали: 40X, 20X13, 12X18H10T, 09Г2С, Ст3, 45, 30ХГСА, 65Г
📏 Типы проката: Круг, Лист, Полоса, Уголок, Швеллер, Балка, Труба

🚀 Для запуска системы выполните:
   python start_metalqms.py
        """
        
        self.stdout.write(self.style.SUCCESS(info))