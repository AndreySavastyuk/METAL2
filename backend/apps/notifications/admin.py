"""
Админка для управления уведомлениями
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import path, reverse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect
from django.utils.safestring import mark_safe
from django.utils import timezone
from .models import UserNotificationPreferences, NotificationLog
from .tasks import test_telegram_connection, send_telegram_message
import json


@admin.register(UserNotificationPreferences)
class UserNotificationPreferencesAdmin(admin.ModelAdmin):
    """Админка настроек уведомлений пользователей"""
    
    list_display = [
        'user', 'telegram_chat_id', 'is_telegram_enabled', 
        'get_enabled_notifications', 'quiet_hours_display', 'updated_at'
    ]
    list_filter = ['is_telegram_enabled', 'language', 'created_at']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'telegram_chat_id']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Пользователь', {
            'fields': ('user',)
        }),
        ('Telegram настройки', {
            'fields': ('telegram_chat_id', 'is_telegram_enabled'),
            'description': 'Настройки для отправки уведомлений в Telegram'
        }),
        ('Типы уведомлений', {
            'fields': ('notification_types_display', 'notification_types'),
            'description': 'Настройка типов уведомлений'
        }),
        ('Тихие часы', {
            'fields': ('quiet_hours_start', 'quiet_hours_end'),
            'description': 'Период времени, когда не отправлять несрочные уведомления'
        }),
        ('Общие настройки', {
            'fields': ('timezone', 'language'),
            'classes': ('collapse',)
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_enabled_notifications(self, obj):
        """Отображение включенных типов уведомлений"""
        if not obj.notification_types:
            return "Не настроено"
        
        enabled = []
        for notif_type, settings in obj.notification_types.items():
            if settings.get('enabled', False):
                name = dict(UserNotificationPreferences.NOTIFICATION_TYPES).get(notif_type, notif_type)
                if settings.get('urgent_only', False):
                    name += " (только срочные)"
                enabled.append(name)
        
        if enabled:
            return mark_safe('<br>'.join(enabled))
        return "Все отключены"
    
    get_enabled_notifications.short_description = 'Включенные уведомления'
    
    def quiet_hours_display(self, obj):
        """Отображение тихих часов"""
        if obj.quiet_hours_start and obj.quiet_hours_end:
            return f"{obj.quiet_hours_start.strftime('%H:%M')} - {obj.quiet_hours_end.strftime('%H:%M')}"
        return "Не установлены"
    
    quiet_hours_display.short_description = 'Тихие часы'
    
    def notification_types_display(self, obj):
        """Читаемое отображение настроек уведомлений"""
        if not obj.notification_types:
            return "Настройки не установлены"
        
        display = []
        for notif_type, settings in obj.notification_types.items():
            name = dict(UserNotificationPreferences.NOTIFICATION_TYPES).get(notif_type, notif_type)
            enabled = "✅" if settings.get('enabled', False) else "❌"
            urgent_only = " (только срочные)" if settings.get('urgent_only', False) else ""
            display.append(f"{enabled} {name}{urgent_only}")
        
        return mark_safe('<br>'.join(display))
    
    notification_types_display.short_description = 'Настройки уведомлений'
    
    def get_urls(self):
        """Добавляем дополнительные URL для управления"""
        urls = super().get_urls()
        custom_urls = [
            path('test-telegram/', self.admin_site.admin_view(self.test_telegram_view), 
                 name='notifications_test_telegram'),
            path('<int:object_id>/send-test/', self.admin_site.admin_view(self.send_test_notification), 
                 name='notifications_send_test'),
        ]
        return custom_urls + urls
    
    def test_telegram_view(self, request):
        """Тестирование подключения к Telegram"""
        if request.method == 'POST':
            result = test_telegram_connection.delay()
            result_data = result.get(timeout=10)
            
            if result_data['status'] == 'success':
                messages.success(request, f"Telegram бот подключен успешно: @{result_data['bot_info']['username']}")
            else:
                messages.error(request, f"Ошибка подключения: {result_data['message']}")
            
            return redirect('admin:notifications_usernotificationpreferences_changelist')
        
        return render(request, 'admin/notifications/test_telegram.html')
    
    def send_test_notification(self, request, object_id):
        """Отправка тестового уведомления"""
        preferences = self.get_object(request, object_id)
        
        if not preferences:
            messages.error(request, "Настройки пользователя не найдены")
            return redirect('admin:notifications_usernotificationpreferences_changelist')
        
        if not preferences.telegram_chat_id:
            messages.error(request, "У пользователя не указан Telegram Chat ID")
            return redirect('admin:notifications_usernotificationpreferences_changelist')
        
        # Создаем тестовое уведомление
        from .services import telegram_service
        log = telegram_service._create_notification_log(
            user=preferences.user,
            notification_type='test',
            message=(
                f"🧪 *Тестовое уведомление*\n\n"
                f"Привет, {preferences.user.get_full_name() or preferences.user.username}!\n\n"
                f"Это тестовое сообщение из системы MetalQMS.\n"
                f"Если вы получили это сообщение, значит уведомления настроены правильно.\n\n"
                f"🕐 Время отправки: {timezone.now().strftime('%d.%m.%Y %H:%M')}"
            ),
            chat_id=preferences.telegram_chat_id
        )
        
        # Отправляем через Celery
        send_telegram_message.delay(log.id)
        
        messages.success(request, f"Тестовое уведомление отправлено пользователю {preferences.user.username}")
        return redirect('admin:notifications_usernotificationpreferences_changelist')
    
    actions = ['enable_telegram', 'disable_telegram', 'reset_notification_settings']
    
    def enable_telegram(self, request, queryset):
        """Включить Telegram уведомления для выбранных пользователей"""
        updated = queryset.update(is_telegram_enabled=True)
        messages.success(request, f"Telegram уведомления включены для {updated} пользователей")
    
    enable_telegram.short_description = "Включить Telegram уведомления"
    
    def disable_telegram(self, request, queryset):
        """Отключить Telegram уведомления для выбранных пользователей"""
        updated = queryset.update(is_telegram_enabled=False)
        messages.success(request, f"Telegram уведомления отключены для {updated} пользователей")
    
    disable_telegram.short_description = "Отключить Telegram уведомления"
    
    def reset_notification_settings(self, request, queryset):
        """Сбросить настройки уведомлений до значений по умолчанию"""
        default_settings = {
            'status_update': {'enabled': True, 'urgent_only': False},
            'task_assignment': {'enabled': True, 'urgent_only': False},
            'urgent_alert': {'enabled': True, 'urgent_only': False},
            'daily_summary': {'enabled': False, 'urgent_only': False},
        }
        
        updated = 0
        for preferences in queryset:
            preferences.notification_types = default_settings
            preferences.save()
            updated += 1
        
        messages.success(request, f"Настройки сброшены для {updated} пользователей")
    
    reset_notification_settings.short_description = "Сбросить настройки уведомлений"


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    """Админка логов уведомлений"""
    
    list_display = [
        'user', 'notification_type', 'status', 'telegram_chat_id', 
        'retry_count', 'sent_at', 'created_at'
    ]
    list_filter = [
        'status', 'notification_type', 'created_at', 'sent_at'
    ]
    search_fields = [
        'user__username', 'user__first_name', 'user__last_name', 
        'telegram_chat_id', 'message'
    ]
    readonly_fields = [
        'user', 'notification_type', 'message', 'telegram_chat_id',
        'status', 'error_message', 'retry_count', 'sent_at', 
        'created_at', 'updated_at', 'object_type', 'object_id'
    ]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'notification_type', 'status')
        }),
        ('Telegram', {
            'fields': ('telegram_chat_id', 'message')
        }),
        ('Статус отправки', {
            'fields': ('retry_count', 'sent_at', 'error_message')
        }),
        ('Связанный объект', {
            'fields': ('object_type', 'object_id'),
            'classes': ('collapse',)
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def has_add_permission(self, request):
        """Запрещаем создание логов через админку"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Запрещаем изменение логов через админку"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Разрешаем удаление только суперпользователям"""
        return request.user.is_superuser
    
    actions = ['retry_failed_notifications', 'mark_as_sent']
    
    def retry_failed_notifications(self, request, queryset):
        """Повторить отправку неудачных уведомлений"""
        failed_logs = queryset.filter(status='failed')
        
        retried = 0
        for log in failed_logs:
            # Пропускаем если ошибка была связана с авторизацией
            if 'Forbidden' in log.error_message or 'Bad Request' in log.error_message:
                continue
            
            log.status = 'retry'
            log.retry_count += 1
            log.save()
            
            # Отправляем заново
            send_telegram_message.delay(log.id)
            retried += 1
        
        messages.success(request, f"Повторная отправка запущена для {retried} уведомлений")
    
    retry_failed_notifications.short_description = "Повторить отправку неудачных"
    
    def mark_as_sent(self, request, queryset):
        """Отметить как отправленные (для тестирования)"""
        from django.utils import timezone
        
        updated = queryset.update(
            status='sent',
            sent_at=timezone.now(),
            error_message=''
        )
        messages.success(request, f"Отмечено как отправленные: {updated} уведомлений")
    
    mark_as_sent.short_description = "Отметить как отправленные"


# Кастомные представления
class NotificationStatsAdmin(admin.ModelAdmin):
    """Статистика уведомлений"""
    
    def changelist_view(self, request, extra_context=None):
        """Отображение статистики"""
        from django.db.models import Count, Q
        from datetime import datetime, timedelta
        
        # Статистика за последние 30 дней
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        stats = NotificationLog.objects.filter(
            created_at__gte=thirty_days_ago
        ).aggregate(
            total=Count('id'),
            sent=Count('id', filter=Q(status='sent')),
            failed=Count('id', filter=Q(status='failed')),
            pending=Count('id', filter=Q(status='pending'))
        )
        
        # Статистика по типам
        type_stats = NotificationLog.objects.filter(
            created_at__gte=thirty_days_ago
        ).values('notification_type').annotate(
            count=Count('id'),
            success_rate=Count('id', filter=Q(status='sent')) * 100 / Count('id')
        ).order_by('-count')
        
        extra_context = extra_context or {}
        extra_context.update({
            'stats': stats,
            'type_stats': type_stats,
            'success_rate': round(stats['sent'] * 100 / stats['total'], 2) if stats['total'] > 0 else 0
        })
        
        return render(request, 'admin/notifications/stats.html', extra_context)


# Статистика будет доступна через отдельный URL
# Можно будет добавить в URL patterns если потребуется