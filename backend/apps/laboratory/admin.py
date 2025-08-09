from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db import models
from django.forms import Textarea
from django.utils import timezone
from .models import TestEquipment, LabTestRequest, LabTestResult, TestStandard


@admin.register(TestEquipment)
class TestEquipmentAdmin(admin.ModelAdmin):
    """Админка для испытательного оборудования"""
    
    list_display = [
        'name',
        'equipment_type',
        'model',
        'serial_number',
        'calibration_status_display',
        'days_until_calibration_display',
        'is_active',
        'responsible_person'
    ]
    
    list_filter = [
        'equipment_type',
        'is_active',
        'calibration_date',
        'next_calibration_date',
        'responsible_person'
    ]
    
    search_fields = [
        'name',
        'model',
        'serial_number',
        'manufacturer'
    ]
    
    readonly_fields = [
        'calibration_status_display_detailed',
        'days_until_calibration_display',
        'created_at',
        'updated_at',
        'created_by',
        'updated_by'
    ]
    
    fieldsets = (
        ('Основная информация', {
            'fields': (
                'name',
                'equipment_type',
                'model',
                'serial_number',
                'manufacturer'
            )
        }),
        ('Калибровка', {
            'fields': (
                'calibration_date',
                'next_calibration_date',
                'calibration_interval_months',
                'calibration_status_display_detailed'
            )
        }),
        ('Технические характеристики', {
            'fields': (
                'accuracy_class',
                'measurement_range',
                'location'
            )
        }),
        ('Управление', {
            'fields': (
                'is_active',
                'responsible_person',
                'notes'
            )
        }),
        ('Аудит', {
            'fields': (
                'created_at',
                'created_by',
                'updated_at',
                'updated_by'
            ),
            'classes': ('collapse',)
        })
    )
    
    ordering = ['name']
    actions = ['mark_calibration_needed', 'deactivate_equipment']
    
    def calibration_status_display(self, obj):
        """Цветной статус калибровки"""
        status = obj.get_calibration_status()
        colors = {
            'overdue': 'red',
            'warning': 'orange',
            'valid': 'green'
        }
        color = colors.get(status, 'gray')
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_calibration_status_display()
        )
    calibration_status_display.short_description = 'Статус калибровки'
    
    def days_until_calibration_display(self, obj):
        """Отображение дней до калибровки"""
        days = obj.days_until_calibration()
        
        if days < 0:
            return format_html(
                '<span style="color: red; font-weight: bold;">Просрочено на {} дн.</span>',
                abs(days)
            )
        elif days <= 30:
            return format_html(
                '<span style="color: orange; font-weight: bold;">{} дн.</span>',
                days
            )
        else:
            return format_html('<span style="color: green;">{} дн.</span>', days)
    days_until_calibration_display.short_description = 'До калибровки'
    
    def calibration_status_display_detailed(self, obj):
        """Подробная информация о калибровке"""
        status = obj.get_calibration_status()
        days = obj.days_until_calibration()
        
        if status == 'overdue':
            message = f'⚠️ ПРОСРОЧЕНА на {abs(days)} дней!'
            color = 'red'
        elif status == 'warning':
            message = f'🔔 Требует внимания, осталось {days} дней'
            color = 'orange'
        else:
            message = f'✅ Действительна, осталось {days} дней'
            color = 'green'
        
        return format_html(
            '<div style="color: {}; font-weight: bold; font-size: 14px;">{}</div>',
            color, message
        )
    calibration_status_display_detailed.short_description = 'Статус калибровки'
    
    def mark_calibration_needed(self, request, queryset):
        """Действие: пометить оборудование для калибровки"""
        for equipment in queryset:
            equipment.is_active = False
            equipment.save()
        
        self.message_user(request, f'Оборудование помечено для калибровки: {queryset.count()}')
    mark_calibration_needed.short_description = 'Пометить для калибровки'
    
    def deactivate_equipment(self, request, queryset):
        """Действие: деактивировать оборудование"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'Деактивировано оборудования: {updated}')
    deactivate_equipment.short_description = 'Деактивировать'

    def save_model(self, request, obj, form, change):
        """Сохранение с указанием пользователя"""
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(LabTestRequest)
class LabTestRequestAdmin(admin.ModelAdmin):
    """Админка для запросов на испытания"""
    
    list_display = [
        'test_info',
        'material_info',
        'requested_by',
        'priority_display',
        'status_display',
        'internal_testing_display',
        'request_date',
        'required_completion_date',
        'is_overdue_display'
    ]
    
    list_filter = [
        'test_type',
        'priority',
        'status',
        'internal_testing',
        'request_date',
        'required_completion_date'
    ]
    
    search_fields = [
        'material_receipt__material__material_grade',
        'material_receipt__material__supplier',
        'material_receipt__material__certificate_number',
        'test_requirements'
    ]
    
    readonly_fields = [
        'duration_display',
        'created_at',
        'updated_at',
        'created_by',
        'updated_by'
    ]
    
    fieldsets = (
        ('Основная информация', {
            'fields': (
                'material_receipt',
                'test_type',
                'requested_by',
                'assigned_to'
            )
        }),
        ('Параметры запроса', {
            'fields': (
                'priority',
                'status',
                'internal_testing',
                'external_lab'
            )
        }),
        ('Временные рамки', {
            'fields': (
                'request_date',
                'required_completion_date',
                'actual_start_date',
                'actual_completion_date',
                'estimated_duration_hours',
                'duration_display'
            )
        }),
        ('Требования', {
            'fields': (
                'test_requirements',
                'sample_preparation_notes'
            )
        }),
        ('Аудит', {
            'fields': (
                'created_at',
                'created_by',
                'updated_at',
                'updated_by'
            ),
            'classes': ('collapse',)
        })
    )
    
    ordering = ['-request_date']
    date_hierarchy = 'request_date'
    actions = ['assign_to_me', 'mark_in_progress', 'mark_completed']
    
    def test_info(self, obj):
        """Информация об испытании"""
        return f"{obj.get_test_type_display()}"
    test_info.short_description = 'Тип испытания'
    
    def material_info(self, obj):
        """Информация о материале"""
        material = obj.material_receipt.material
        return format_html(
            '<strong>{}</strong><br/><small>{}</small>',
            material.material_grade,
            material.supplier
        )
    material_info.short_description = 'Материал'
    
    def priority_display(self, obj):
        """Цветной приоритет"""
        colors = {
            'low': 'gray',
            'normal': 'blue',
            'high': 'orange',
            'urgent': 'red'
        }
        color = colors.get(obj.priority, 'black')
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_priority_display()
        )
    priority_display.short_description = 'Приоритет'
    
    def status_display(self, obj):
        """Цветной статус"""
        colors = {
            'pending': 'orange',
            'assigned': 'blue',
            'in_progress': 'purple',
            'completed': 'green',
            'cancelled': 'red',
            'on_hold': 'gray'
        }
        color = colors.get(obj.status, 'black')
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Статус'
    
    def internal_testing_display(self, obj):
        """Отображение типа испытания"""
        if obj.internal_testing:
            return format_html('<span style="color: green;">✓ Внутреннее</span>')
        else:
            return format_html(
                '<span style="color: orange;">⚠ Внешнее<br/><small>{}</small></span>',
                obj.external_lab or 'Не указана'
            )
    internal_testing_display.short_description = 'Тип'
    
    def is_overdue_display(self, obj):
        """Отображение просрочки"""
        if obj.is_overdue():
            return format_html('<span style="color: red; font-weight: bold;">⚠ Просрочено</span>')
        elif obj.required_completion_date:
            days_left = (obj.required_completion_date - timezone.now().date()).days
            if days_left <= 3:
                return format_html('<span style="color: orange;">⏰ {} дн.</span>', days_left)
        return format_html('<span style="color: green;">✓</span>')
    is_overdue_display.short_description = 'Срок'
    
    def duration_display(self, obj):
        """Отображение продолжительности"""
        duration = obj.get_duration()
        if duration:
            return f"{duration:.1f} часов"
        elif obj.estimated_duration_hours:
            return f"Оценка: {obj.estimated_duration_hours} часов"
        return "Не определено"
    duration_display.short_description = 'Продолжительность'
    
    def assign_to_me(self, request, queryset):
        """Действие: назначить себе"""
        updated = queryset.filter(status='pending').update(
            assigned_to=request.user,
            status='assigned'
        )
        self.message_user(request, f'Назначено заданий: {updated}')
    assign_to_me.short_description = 'Назначить себе'
    
    def mark_in_progress(self, request, queryset):
        """Действие: перевести в выполнение"""
        updated = 0
        for test_request in queryset:
            if test_request.status in ['pending', 'assigned']:
                test_request.status = 'in_progress'
                test_request.actual_start_date = timezone.now()
                test_request.save()
                updated += 1
        
        self.message_user(request, f'Переведено в выполнение: {updated}')
    mark_in_progress.short_description = 'Начать выполнение'
    
    def mark_completed(self, request, queryset):
        """Действие: завершить"""
        updated = queryset.filter(status='in_progress').update(
            status='completed',
            actual_completion_date=timezone.now()
        )
        self.message_user(request, f'Завершено заданий: {updated}')
    mark_completed.short_description = 'Завершить'

    def save_model(self, request, obj, form, change):
        """Сохранение с указанием пользователя"""
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(LabTestResult)
class LabTestResultAdmin(admin.ModelAdmin):
    """Админка для результатов испытаний"""
    
    list_display = [
        'certificate_number',
        'test_info',
        'performed_by',
        'test_date',
        'conclusion_display',
        'approval_status',
        'equipment_list'
    ]
    
    list_filter = [
        'conclusion',
        'test_date',
        'performed_by',
        'approved_by',
        'test_request__test_type'
    ]
    
    search_fields = [
        'certificate_number',
        'test_request__material_receipt__material__material_grade',
        'test_method',
        'comments'
    ]
    
    readonly_fields = [
        'formatted_results_display',
        'created_at',
        'updated_at',
        'created_by',
        'updated_by'
    ]
    
    fieldsets = (
        ('Основная информация', {
            'fields': (
                'test_request',
                'certificate_number',
                'performed_by',
                'test_date'
            )
        }),
        ('Результаты', {
            'fields': (
                'conclusion',
                'test_method',
                'sample_description',
                'results',
                'test_conditions',
                'formatted_results_display'
            )
        }),
        ('Оборудование и условия', {
            'fields': (
                'equipment_used',
            )
        }),
        ('Утверждение', {
            'fields': (
                'approved_by',
                'approval_date',
                'comments'
            )
        }),
        ('Дополнительно', {
            'fields': (
                'file_attachments',
            ),
            'classes': ('collapse',)
        }),
        ('Аудит', {
            'fields': (
                'created_at',
                'created_by',
                'updated_at',
                'updated_by'
            ),
            'classes': ('collapse',)
        })
    )
    
    filter_horizontal = ['equipment_used']
    ordering = ['-test_date']
    
    def test_info(self, obj):
        """Информация об испытании"""
        material = obj.test_request.material_receipt.material
        return format_html(
            '<strong>{}</strong><br/><small>{}</small>',
            obj.test_request.get_test_type_display(),
            material.material_grade
        )
    test_info.short_description = 'Испытание'
    
    def conclusion_display(self, obj):
        """Цветное заключение"""
        colors = {
            'passed': 'green',
            'failed': 'red',
            'conditional': 'orange',
            'retest_required': 'blue'
        }
        color = colors.get(obj.conclusion, 'black')
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_conclusion_display()
        )
    conclusion_display.short_description = 'Заключение'
    
    def approval_status(self, obj):
        """Статус утверждения"""
        if obj.is_approved():
            return format_html(
                '<span style="color: green;">✓ Утверждено<br/><small>{}</small></span>',
                obj.approved_by.get_full_name() or obj.approved_by.username
            )
        else:
            return format_html('<span style="color: orange;">⏳ Ожидает утверждения</span>')
    approval_status.short_description = 'Утверждение'
    
    def equipment_list(self, obj):
        """Список использованного оборудования"""
        equipment = obj.equipment_used.all()
        if equipment:
            items = []
            for eq in equipment[:3]:  # Показываем первые 3
                status = eq.get_calibration_status()
                if status == 'valid':
                    icon = '✅'
                elif status == 'warning':
                    icon = '🟡'
                else:
                    icon = '🔴'
                items.append(f'{icon} {eq.name}')
            
            result = '<br/>'.join(items)
            if len(equipment) > 3:
                result += f'<br/>... и еще {len(equipment) - 3}'
            return format_html(result)
        return 'Не указано'
    equipment_list.short_description = 'Оборудование'
    
    def formatted_results_display(self, obj):
        """Форматированное отображение результатов"""
        formatted = obj.format_results_for_certificate()
        if not formatted:
            return "Нет данных для отображения"
        
        html_parts = []
        for section, data in formatted.items():
            html_parts.append(f'<h4>{section}:</h4>')
            if isinstance(data, dict):
                for key, value in data.items():
                    html_parts.append(f'<div><strong>{key}:</strong> {value}</div>')
            else:
                html_parts.append(f'<div>{data}</div>')
        
        return format_html('<div style="max-height: 200px; overflow-y: auto;">{}</div>', ''.join(html_parts))
    formatted_results_display.short_description = 'Форматированные результаты'

    def save_model(self, request, obj, form, change):
        """Сохранение с указанием пользователя"""
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(TestStandard)
class TestStandardAdmin(admin.ModelAdmin):
    """Админка для стандартов испытаний"""
    
    list_display = [
        'standard_number',
        'name',
        'test_type',
        'applicable_grades_display',
        'is_active'
    ]
    
    list_filter = [
        'test_type',
        'is_active'
    ]
    
    search_fields = [
        'name',
        'standard_number',
        'material_grades'
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'created_by',
        'updated_by'
    ]
    
    fieldsets = (
        ('Основная информация', {
            'fields': (
                'standard_number',
                'name',
                'test_type',
                'is_active'
            )
        }),
        ('Применимость', {
            'fields': (
                'material_grades',
            )
        }),
        ('Требования и методика', {
            'fields': (
                'requirements',
                'test_method'
            )
        }),
        ('Аудит', {
            'fields': (
                'created_at',
                'created_by',
                'updated_at',
                'updated_by'
            ),
            'classes': ('collapse',)
        })
    )
    
    def applicable_grades_display(self, obj):
        """Отображение применимых марок"""
        grades = obj.get_applicable_grades()
        if not grades:
            return format_html('<span style="color: blue; font-style: italic;">Универсальный</span>')
        
        if len(grades) <= 3:
            return ', '.join(grades)
        else:
            return f"{', '.join(grades[:3])} ... (+{len(grades) - 3})"
    applicable_grades_display.short_description = 'Применимые марки'

    def save_model(self, request, obj, form, change):
        """Сохранение с указанием пользователя"""
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change) 