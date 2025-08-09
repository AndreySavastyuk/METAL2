"""
Скрипт для тестирования системы Telegram уведомлений
"""
import os
import sys
import django
from django.conf import settings

# Настройка Django
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User, Group
from apps.notifications.models import UserNotificationPreferences
from apps.notifications.services import telegram_service
from apps.notifications.tasks import test_telegram_connection
from apps.warehouse.models import Material

def create_test_user_with_notifications():
    """Создать тестового пользователя с настройками уведомлений"""
    
    # Создаем группы если их нет
    groups = ['QC', 'Laboratory', 'Production', 'Warehouse', 'Administrators']
    for group_name in groups:
        group, created = Group.objects.get_or_create(name=group_name)
        if created:
            print(f"✅ Создана группа: {group_name}")
    
    # Создаем тестового пользователя
    user, created = User.objects.get_or_create(
        username='test_telegram_user',
        defaults={
            'first_name': 'Тест',
            'last_name': 'Телеграм',
            'email': 'test@example.com',
            'is_active': True
        }
    )
    
    if created:
        print(f"✅ Создан тестовый пользователь: {user.username}")
    else:
        print(f"📋 Пользователь уже существует: {user.username}")
    
    # Добавляем в группу QC
    qc_group = Group.objects.get(name='QC')
    user.groups.add(qc_group)
    
    # Создаем настройки уведомлений
    preferences, created = UserNotificationPreferences.objects.get_or_create(
        user=user,
        defaults={
            'telegram_chat_id': '',  # Нужно будет указать вручную
            'is_telegram_enabled': False,  # Включится после указания chat_id
            'notification_types': {
                'status_update': {'enabled': True, 'urgent_only': False},
                'task_assignment': {'enabled': True, 'urgent_only': False},
                'urgent_alert': {'enabled': True, 'urgent_only': False},
                'daily_summary': {'enabled': True, 'urgent_only': False},
            },
            'language': 'ru',
            'timezone': 'Europe/Moscow'
        }
    )
    
    if created:
        print(f"✅ Созданы настройки уведомлений для {user.username}")
    else:
        print(f"📋 Настройки уведомлений уже существуют для {user.username}")
    
    return user, preferences

def test_bot_connection():
    """Тестировать подключение к Telegram Bot"""
    print("\n🤖 Тестирование подключения к Telegram Bot...")
    
    if not settings.TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN не настроен в переменных окружения")
        print("💡 Добавьте TELEGRAM_BOT_TOKEN=your_bot_token в .env файл")
        return False
    
    try:
        result = test_telegram_connection.delay()
        result_data = result.get(timeout=10)
        
        if result_data['status'] == 'success':
            bot_info = result_data['bot_info']
            print(f"✅ Бот подключен успешно:")
            print(f"   • Username: @{bot_info['username']}")
            print(f"   • Name: {bot_info['first_name']}")
            print(f"   • ID: {bot_info['id']}")
            return True
        else:
            print(f"❌ Ошибка подключения: {result_data['message']}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        return False

def test_notifications_with_mock_material():
    """Тестировать уведомления с мок-материалом"""
    print("\n📦 Создание тестового материала...")
    
    # Создаем тестовый материал
    material, created = Material.objects.get_or_create(
        material_grade='40X',
        supplier='Тестовый поставщик',
        certificate_number='TEST-001',
        heat_number='TEST-HEAT-001',
        defaults={
            'size': '⌀100',
            'quantity': 1000,
            'unit': 'kg',
            'order_number': 'ORDER-TEST-001',
            'created_by_id': 1,
            'updated_by_id': 1
        }
    )
    
    if created:
        print(f"✅ Создан тестовый материал: {material}")
    else:
        print(f"📋 Тестовый материал уже существует: {material}")
    
    return material

def print_setup_instructions():
    """Вывести инструкции по настройке"""
    print("\n📋 ИНСТРУКЦИИ ПО НАСТРОЙКЕ TELEGRAM УВЕДОМЛЕНИЙ:")
    print("=" * 60)
    
    print("\n1. Создание Telegram бота:")
    print("   • Отправьте /start боту @BotFather")
    print("   • Отправьте /newbot и следуйте инструкциям")
    print("   • Скопируйте токен бота")
    print("   • Добавьте в .env файл: TELEGRAM_BOT_TOKEN=your_token_here")
    
    print("\n2. Получение Chat ID:")
    print("   • Напишите сообщение своему боту")
    print("   • Перейдите по ссылке:")
    print("     https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates")
    print("   • Найдите 'chat':{'id': ВАШИ_ЦИФРЫ}")
    
    print("\n3. Настройка в админке:")
    print("   • Войдите в админку Django")
    print("   • Перейдите в 'Настройки уведомлений пользователей'")
    print("   • Найдите пользователя 'test_telegram_user'")
    print("   • Укажите Telegram Chat ID")
    print("   • Включите 'Включить Telegram уведомления'")
    
    print("\n4. Тестирование:")
    print("   • В админке нажмите 'Отправить тестовое уведомление'")
    print("   • Или запустите: python test_telegram_notifications.py")

def main():
    """Основная функция тестирования"""
    print("🚀 ТЕСТИРОВАНИЕ СИСТЕМЫ TELEGRAM УВЕДОМЛЕНИЙ")
    print("=" * 50)
    
    # 1. Создаем тестового пользователя
    user, preferences = create_test_user_with_notifications()
    
    # 2. Тестируем подключение к боту
    bot_connected = test_bot_connection()
    
    # 3. Создаем тестовый материал
    material = test_notifications_with_mock_material()
    
    # 4. Проверяем настройки
    print(f"\n⚙️  Настройки пользователя {user.username}:")
    print(f"   • Chat ID: {preferences.telegram_chat_id or 'НЕ УКАЗАН'}")
    print(f"   • Уведомления включены: {preferences.is_telegram_enabled}")
    print(f"   • Язык: {preferences.language}")
    print(f"   • Часовой пояс: {preferences.timezone}")
    
    # 5. Тестируем отправку уведомления (если настройки корректные)
    if bot_connected and preferences.telegram_chat_id and preferences.is_telegram_enabled:
        print(f"\n📱 Отправка тестового уведомления...")
        try:
            success = telegram_service.send_status_update(
                user_id=user.id,
                material=material,
                old_status='pending_qc',
                new_status='in_qc',
                is_urgent=False
            )
            
            if success:
                print("✅ Тестовое уведомление отправлено!")
                print("📱 Проверьте свой Telegram")
            else:
                print("❌ Не удалось отправить уведомление")
                
        except Exception as e:
            print(f"❌ Ошибка отправки: {e}")
    else:
        print("\n⚠️  Тестовое уведомление не отправлено:")
        if not bot_connected:
            print("   • Бот не подключен")
        if not preferences.telegram_chat_id:
            print("   • Не указан Chat ID")
        if not preferences.is_telegram_enabled:
            print("   • Уведомления отключены")
    
    # 6. Выводим инструкции
    print_setup_instructions()
    
    print(f"\n✨ Тестирование завершено!")
    print(f"📊 Статистика:")
    print(f"   • Пользователей с уведомлениями: {UserNotificationPreferences.objects.count()}")
    print(f"   • Активных уведомлений: {UserNotificationPreferences.objects.filter(is_telegram_enabled=True).count()}")

if __name__ == '__main__':
    main()