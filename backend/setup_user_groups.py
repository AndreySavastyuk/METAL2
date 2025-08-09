#!/usr/bin/env python
"""
Скрипт для настройки групп пользователей и ролевой модели
"""
import os
import sys
import django

# Настройка Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from apps.warehouse.models import Material, MaterialReceipt, Certificate


def create_user_groups():
    """Создание групп пользователей для системы QMS"""
    
    print("🔧 Настройка групп пользователей для MetalQMS...")
    
    # Группы и их описания
    groups_config = {
        'warehouse': {
            'verbose_name': 'Персонал склада',
            'description': 'Может создавать и управлять материалами и приемками',
            'permissions': ['add', 'change', 'view', 'delete']
        },
        'warehouse_staff': {
            'verbose_name': 'Сотрудники склада',
            'description': 'Расширенные права склада (алиас для warehouse)',
            'permissions': ['add', 'change', 'view', 'delete']
        },
        'qc': {
            'verbose_name': 'Отдел ОТК',
            'description': 'Может просматривать материалы и управлять проверками качества',
            'permissions': ['view', 'change']
        },
        'quality_control': {
            'verbose_name': 'Контроль качества',
            'description': 'Расширенные права ОТК (алиас для qc)',
            'permissions': ['view', 'change']
        },
        'lab': {
            'verbose_name': 'Лаборатория',
            'description': 'Может просматривать материалы и работать с сертификатами',
            'permissions': ['view', 'change']
        },
        'laboratory': {
            'verbose_name': 'Центральная заводская лаборатория',
            'description': 'Расширенные права лаборатории (алиас для lab)',
            'permissions': ['view', 'change']
        }
    }
    
    # Создаем группы
    created_groups = []
    for group_name, config in groups_config.items():
        group, created = Group.objects.get_or_create(name=group_name)
        if created:
            print(f"✅ Создана группа: {group_name} ({config['verbose_name']})")
            created_groups.append(group_name)
        else:
            print(f"ℹ️ Группа уже существует: {group_name}")
    
    print(f"\n📋 Создано новых групп: {len(created_groups)}")
    return created_groups


def assign_permissions():
    """Назначение разрешений группам"""
    
    print("\n🔐 Назначение разрешений группам...")
    
    # Получаем типы контента для наших моделей
    material_ct = ContentType.objects.get_for_model(Material)
    receipt_ct = ContentType.objects.get_for_model(MaterialReceipt)
    certificate_ct = ContentType.objects.get_for_model(Certificate)
    
    # Разрешения для каждой группы
    permissions_config = {
        'warehouse': {
            'Material': ['add', 'change', 'view', 'delete'],
            'MaterialReceipt': ['add', 'change', 'view', 'delete'],
            'Certificate': ['add', 'change', 'view', 'delete']
        },
        'warehouse_staff': {
            'Material': ['add', 'change', 'view', 'delete'],
            'MaterialReceipt': ['add', 'change', 'view', 'delete'],
            'Certificate': ['add', 'change', 'view', 'delete']
        },
        'qc': {
            'Material': ['view'],
            'MaterialReceipt': ['view', 'change'],
            'Certificate': ['view']
        },
        'quality_control': {
            'Material': ['view'],
            'MaterialReceipt': ['view', 'change'],
            'Certificate': ['view']
        },
        'lab': {
            'Material': ['view'],
            'MaterialReceipt': ['view'],
            'Certificate': ['view', 'change']
        },
        'laboratory': {
            'Material': ['view'],
            'MaterialReceipt': ['view'],
            'Certificate': ['view', 'change']
        }
    }
    
    for group_name, group_permissions in permissions_config.items():
        try:
            group = Group.objects.get(name=group_name)
            
            for model_name, actions in group_permissions.items():
                for action in actions:
                    # Формируем имя разрешения
                    perm_codename = f"{action}_{model_name.lower()}"
                    
                    try:
                        # Ищем разрешение
                        if model_name == 'Material':
                            permission = Permission.objects.get(
                                codename=perm_codename,
                                content_type=material_ct
                            )
                        elif model_name == 'MaterialReceipt':
                            permission = Permission.objects.get(
                                codename=perm_codename,
                                content_type=receipt_ct
                            )
                        elif model_name == 'Certificate':
                            permission = Permission.objects.get(
                                codename=perm_codename,
                                content_type=certificate_ct
                            )
                        
                        # Добавляем разрешение группе
                        group.permissions.add(permission)
                        print(f"  ✅ {group_name}: {action}_{model_name}")
                        
                    except Permission.DoesNotExist:
                        print(f"  ⚠️ Разрешение не найдено: {perm_codename}")
                        
        except Group.DoesNotExist:
            print(f"❌ Группа не найдена: {group_name}")


def assign_users_to_groups():
    """Назначение существующих пользователей в группы"""
    
    print("\n👥 Назначение пользователей в группы...")
    
    # Маппинг пользователей на группы (по username)
    user_group_mapping = {
        'admin': ['warehouse', 'qc', 'lab'],  # Админ во всех группах
        'warehouse_operator': ['warehouse_staff'],
        'qc_inspector': ['qc', 'quality_control'],
        'lab_manager': ['lab', 'laboratory'],
        'lab_technician': ['lab'],
        'chemist': ['laboratory']
    }
    
    for username, group_names in user_group_mapping.items():
        try:
            user = User.objects.get(username=username)
            
            for group_name in group_names:
                try:
                    group = Group.objects.get(name=group_name)
                    user.groups.add(group)
                    print(f"  ✅ {username} → {group_name}")
                except Group.DoesNotExist:
                    print(f"  ❌ Группа не найдена: {group_name}")
                    
        except User.DoesNotExist:
            print(f"  ⚠️ Пользователь не найден: {username}")


def create_test_users():
    """Создание тестовых пользователей если их нет"""
    
    print("\n👤 Проверка/создание тестовых пользователей...")
    
    test_users = [
        {
            'username': 'warehouse_operator',
            'email': 'warehouse@metalqms.local',
            'first_name': 'Складской',
            'last_name': 'Оператор',
            'groups': ['warehouse_staff']
        },
        {
            'username': 'qc_inspector',
            'email': 'qc@metalqms.local',
            'first_name': 'Инспектор',
            'last_name': 'ОТК',
            'groups': ['qc', 'quality_control']
        },
        {
            'username': 'lab_manager',
            'email': 'lab@metalqms.local',
            'first_name': 'Начальник',
            'last_name': 'Лаборатории',
            'groups': ['lab', 'laboratory']
        }
    ]
    
    for user_data in test_users:
        username = user_data['username']
        groups = user_data.pop('groups')
        
        user, created = User.objects.get_or_create(
            username=username,
            defaults=user_data
        )
        
        if created:
            user.set_password('metalqms123')  # Простой пароль для тестирования
            user.save()
            print(f"  ✅ Создан пользователь: {username}")
        else:
            print(f"  ℹ️ Пользователь существует: {username}")
        
        # Добавляем в группы
        for group_name in groups:
            try:
                group = Group.objects.get(name=group_name)
                user.groups.add(group)
            except Group.DoesNotExist:
                print(f"    ❌ Группа не найдена: {group_name}")


def show_groups_summary():
    """Показать итоговую информацию о группах"""
    
    print("\n" + "="*60)
    print("📋 ИТОГОВАЯ ИНФОРМАЦИЯ О ГРУППАХ")
    print("="*60)
    
    for group in Group.objects.all().order_by('name'):
        print(f"\n🏷️ Группа: {group.name}")
        
        # Показываем пользователей в группе
        users = group.user_set.all()
        if users:
            print(f"   👥 Пользователи ({users.count()}):")
            for user in users:
                print(f"      - {user.username} ({user.get_full_name() or 'без имени'})")
        else:
            print("   👥 Пользователей нет")
        
        # Показываем разрешения
        permissions = group.permissions.all()
        if permissions:
            print(f"   🔐 Разрешения ({permissions.count()}):")
            for perm in permissions[:5]:  # Показываем первые 5
                print(f"      - {perm.codename}")
            if permissions.count() > 5:
                print(f"      ... и еще {permissions.count() - 5}")
        else:
            print("   🔐 Разрешений нет")


def test_permissions():
    """Тестирование разрешений"""
    
    print("\n" + "="*60)
    print("🧪 ТЕСТИРОВАНИЕ РАЗРЕШЕНИЙ")
    print("="*60)
    
    from apps.warehouse.permissions import is_warehouse_staff, is_qc_inspector, is_lab_technician
    
    test_users = ['admin', 'warehouse_operator', 'qc_inspector', 'lab_manager']
    
    for username in test_users:
        try:
            user = User.objects.get(username=username)
            print(f"\n👤 {username}:")
            print(f"   📦 Склад: {'✅' if is_warehouse_staff(user) else '❌'}")
            print(f"   🔍 ОТК: {'✅' if is_qc_inspector(user) else '❌'}")
            print(f"   🧪 Лаборатория: {'✅' if is_lab_technician(user) else '❌'}")
            print(f"   🔒 Суперпользователь: {'✅' if user.is_superuser else '❌'}")
            
        except User.DoesNotExist:
            print(f"❌ Пользователь не найден: {username}")


def main():
    """Основная функция настройки"""
    
    print("🚀 Запуск настройки ролевой модели MetalQMS")
    print("="*60)
    
    # Создаем группы
    created_groups = create_user_groups()
    
    # Назначаем разрешения
    assign_permissions()
    
    # Создаем тестовых пользователей
    create_test_users()
    
    # Назначаем пользователей в группы
    assign_users_to_groups()
    
    # Показываем итоги
    show_groups_summary()
    
    # Тестируем разрешения
    test_permissions()
    
    print("\n" + "="*60)
    print("✅ НАСТРОЙКА РОЛЕВОЙ МОДЕЛИ ЗАВЕРШЕНА")
    print("="*60)
    print("\n📚 Созданные роли:")
    print("   📦 warehouse/warehouse_staff - Персонал склада")
    print("   🔍 qc/quality_control - Отдел ОТК")
    print("   🧪 lab/laboratory - Лаборатория")
    print("\n🔑 Доступы:")
    print("   - admin / admin (все права)")
    print("   - warehouse_operator / metalqms123 (склад)")
    print("   - qc_inspector / metalqms123 (ОТК)")
    print("   - lab_manager / metalqms123 (лаборатория)")
    print("\n🌐 Тестирование API с ролями готово!")


if __name__ == '__main__':
    main() 