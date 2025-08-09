from django.contrib import admin
from django.utils.html import format_html
from .models import QCInspection, QCInspectionResult


@admin.register(QCInspection)
class QCInspectionAdmin(admin.ModelAdmin):
    list_display = ['material_info', 'inspector', 'inspection_date', 'status']

    def material_info(self, obj):
        material = obj.material_receipt.material
        return format_html(
            '<strong>{}</strong><br/><small>{} - {}</small>',
            material.material_grade,
            material.supplier,
            material.certificate_number
        )
    material_info.short_description = 'Материал'


@admin.register(QCInspectionResult)
class QCInspectionResultAdmin(admin.ModelAdmin):
    """Админка для результатов инспекции"""
    
    list_display = [
        'inspection_info',
        'checklist_item_short',
        'result_colored',
        'is_critical_display',
        'measured_value',
        'has_notes'
    ]
    
    list_filter = [
        'result',
        'checklist_item__is_critical',
        'inspection__status',
        'created_at'
    ]
    
    search_fields = [
        'inspection__material_receipt__material__material_grade',
        'checklist_item__description',
        'notes',
        'measured_value'
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
                'inspection',
                'checklist_item',
                'result'
            )
        }),
        ('Детали', {
            'fields': (
                'measured_value',
                'notes',
                'inspector_signature'
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
    
    ordering = ['inspection', 'checklist_item__order']
    
    def inspection_info(self, obj):
        """Информация об инспекции"""
        material = obj.inspection.material_receipt.material
        return format_html(
            '<strong>{}</strong><br/><small>{}</small>',
            material.material_grade,
            obj.inspection.get_status_display()
        )
    inspection_info.short_description = 'Инспекция'
    
    def checklist_item_short(self, obj):
        """Краткое описание пункта"""
        critical_mark = " 🔴" if obj.checklist_item.is_critical else ""
        return f"{obj.checklist_item.order}. {obj.checklist_item.description[:40]}...{critical_mark}"
    checklist_item_short.short_description = 'Пункт проверки'
    
    def result_colored(self, obj):
        """Цветной результат"""
        if not obj.result:
            return format_html('<span style="color: orange;">Не проверено</span>')
        
        colors = {
            'passed': 'green',
            'failed': 'red',
            'na': 'gray'
        }
        color = colors.get(obj.result, 'black')
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_result_display()
        )
    result_colored.short_description = 'Результат'
    
    def is_critical_display(self, obj):
        """Отображение критичности пункта"""
        if obj.checklist_item.is_critical:
            return format_html('<span style="color: red;">🔴</span>')
        return format_html('<span style="color: gray;">○</span>')
    is_critical_display.short_description = 'Критический'
    
    def has_notes(self, obj):
        """Наличие примечаний"""
        if obj.notes:
            return format_html('<span style="color: blue;" title="{}">📝</span>', obj.notes[:100])
        return format_html('<span style="color: gray;">—</span>')
    has_notes.short_description = 'Примечания'

    def save_model(self, request, obj, form, change):
        """Сохранение с указанием пользователя"""
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change) 