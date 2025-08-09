from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Material, MaterialReceipt, Certificate


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    """Админка для модели Material"""
    
    list_display = [
        'material_grade', 
        'supplier', 
        'certificate_number', 
        'heat_number', 
        'quantity_with_unit',
        'receipt_date',
        'location',
        'qr_code_preview',
        'status_display'
    ]
    
    list_filter = [
        'material_grade',
        'supplier', 
        'unit',
        'receipt_date',
        'is_deleted',
        'created_at'
    ]
    
    search_fields = [
        'material_grade',
        'supplier',
        'order_number',
        'certificate_number',
        'heat_number',
        'size'
    ]
    
    readonly_fields = [
        'external_id',
        'qr_code_preview',
        'created_at',
        'updated_at',
        'created_by',
        'updated_by'
    ]
    
    fieldsets = (
        ('Основная информация', {
            'fields': (
                'material_grade',
                'supplier',
                'order_number',
                'certificate_number',
                'heat_number',
                'size'
            )
        }),
        ('Количество и расположение', {
            'fields': (
                'quantity',
                'unit',
                'location',
                'receipt_date'
            )
        }),
        ('QR код', {
            'fields': (
                'external_id',
                'qr_code',
                'qr_code_preview'
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
    
    ordering = ['-receipt_date']
    date_hierarchy = 'receipt_date'
    
    def quantity_with_unit(self, obj):
        """Отображение количества с единицей измерения"""
        return f"{obj.quantity} {obj.get_unit_display()}"
    quantity_with_unit.short_description = 'Количество'
    
    def qr_code_preview(self, obj):
        """Предпросмотр QR кода"""
        if obj.qr_code:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 100px;" />',
                obj.qr_code.url
            )
        return "Нет QR кода"
    qr_code_preview.short_description = 'Предпросмотр QR'
    
    def status_display(self, obj):
        """Отображение статуса материала"""
        if obj.is_deleted:
            return format_html('<span style="color: red;">Удален</span>')
        
        # Проверяем есть ли активные поступления
        latest_receipt = obj.receipts.first()
        if latest_receipt:
            status_colors = {
                'pending_qc': 'orange',
                'in_qc': 'blue', 
                'approved': 'green',
                'rejected': 'red'
            }
            color = status_colors.get(latest_receipt.status, 'black')
            return format_html(
                '<span style="color: {};">{}</span>',
                color,
                latest_receipt.get_status_display()
            )
        return "Нет поступлений"
    status_display.short_description = 'Статус'

    def save_model(self, request, obj, form, change):
        """Сохранение с указанием пользователя"""
        if not change:  # Новый объект
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(MaterialReceipt)
class MaterialReceiptAdmin(admin.ModelAdmin):
    """Админка для модели MaterialReceipt"""
    
    list_display = [
        'document_number',
        'material_link',
        'received_by',
        'receipt_date',
        'status_colored',
        'notes_preview'
    ]
    
    list_filter = [
        'status',
        'receipt_date',
        'received_by',
        'material__material_grade',
        'material__supplier'
    ]
    
    search_fields = [
        'document_number',
        'material__material_grade',
        'material__supplier',
        'material__certificate_number',
        'notes'
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at',
        'created_by',
        'updated_by'
    ]
    
    autocomplete_fields = ['material']
    
    fieldsets = (
        ('Основная информация', {
            'fields': (
                'material',
                'received_by',
                'receipt_date',
                'document_number',
                'status'
            )
        }),
        ('Дополнительно', {
            'fields': ('notes',)
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
    
    ordering = ['-receipt_date']
    date_hierarchy = 'receipt_date'
    
    def material_link(self, obj):
        """Ссылка на материал"""
        url = reverse('admin:warehouse_material_change', args=[obj.material.pk])
        return format_html('<a href="{}">{}</a>', url, obj.material)
    material_link.short_description = 'Материал'
    
    def status_colored(self, obj):
        """Цветной статус"""
        colors = {
            'pending_qc': 'orange',
            'in_qc': 'blue',
            'approved': 'green', 
            'rejected': 'red'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_colored.short_description = 'Статус'
    
    def notes_preview(self, obj):
        """Превью примечаний"""
        if obj.notes:
            return obj.notes[:50] + ('...' if len(obj.notes) > 50 else '')
        return '-'
    notes_preview.short_description = 'Примечания'

    def save_model(self, request, obj, form, change):
        """Сохранение с указанием пользователя"""
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    """Админка для модели Certificate"""
    
    list_display = [
        'material_link',
        'file_info',
        'uploaded_at',
        'file_size_formatted',
        'extraction_status'
    ]
    
    list_filter = [
        'uploaded_at',
        'material__material_grade',
        'material__supplier'
    ]
    
    search_fields = [
        'material__certificate_number',
        'material__material_grade',
        'material__supplier'
    ]
    
    readonly_fields = [
        'uploaded_at',
        'file_size',
        'file_hash',
        'parsed_data_preview',
        'created_at',
        'updated_at',
        'created_by',
        'updated_by'
    ]
    
    fieldsets = (
        ('Основная информация', {
            'fields': (
                'material',
                'pdf_file',
                'uploaded_at'
            )
        }),
        ('Метаданные файла', {
            'fields': (
                'file_size',
                'file_hash'
            ),
            'classes': ('collapse',)
        }),
        ('Извлеченные данные', {
            'fields': ('parsed_data_preview',),
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
    
    ordering = ['-uploaded_at']
    
    def material_link(self, obj):
        """Ссылка на материал"""
        url = reverse('admin:warehouse_material_change', args=[obj.material.pk])
        return format_html('<a href="{}">{}</a>', url, obj.material)
    material_link.short_description = 'Материал'
    
    def file_info(self, obj):
        """Информация о файле"""
        if obj.pdf_file:
            return format_html(
                '<a href="{}" target="_blank">{}</a>',
                obj.pdf_file.url,
                obj.pdf_file.name.split('/')[-1]
            )
        return "Нет файла"
    file_info.short_description = 'Файл'
    
    def file_size_formatted(self, obj):
        """Форматированный размер файла"""
        if obj.file_size:
            if obj.file_size < 1024:
                return f"{obj.file_size} байт"
            elif obj.file_size < 1024 * 1024:
                return f"{obj.file_size / 1024:.1f} КБ"
            else:
                return f"{obj.file_size / (1024 * 1024):.1f} МБ"
        return "-"
    file_size_formatted.short_description = 'Размер'
    
    def extraction_status(self, obj):
        """Статус извлечения данных"""
        if not obj.parsed_data:
            return format_html('<span style="color: gray;">Не обработан</span>')
        elif 'error' in obj.parsed_data:
            return format_html('<span style="color: red;">Ошибка</span>')
        elif 'extracted_text' in obj.parsed_data:
            text_len = len(obj.parsed_data.get('extracted_text', ''))
            return format_html(
                '<span style="color: green;">Извлечено {} символов</span>',
                text_len
            )
        return format_html('<span style="color: orange;">Частично</span>')
    extraction_status.short_description = 'Извлечение текста'
    
    def parsed_data_preview(self, obj):
        """Превью извлеченных данных"""
        if not obj.parsed_data:
            return "Нет данных"
        
        if 'error' in obj.parsed_data:
            return format_html(
                '<div style="color: red;">Ошибка: {}</div>',
                obj.parsed_data['error']
            )
        
        if 'extracted_text' in obj.parsed_data:
            text = obj.parsed_data['extracted_text'][:500]
            if len(obj.parsed_data['extracted_text']) > 500:
                text += '...'
            return format_html('<pre style="white-space: pre-wrap;">{}</pre>', text)
        
        return str(obj.parsed_data)
    parsed_data_preview.short_description = 'Превью данных'

    def save_model(self, request, obj, form, change):
        """Сохранение с указанием пользователя"""
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change) 