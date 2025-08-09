"""
Админка для управления обработкой сертификатов
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import path, reverse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.utils.safestring import mark_safe
from django.db.models import Count, Q
from django.utils import timezone
from .models import CertificateSearchIndex, CertificatePreview, ProcessingLog
from .tasks import process_uploaded_certificate, generate_certificate_preview, reprocess_certificates_batch


@admin.register(CertificateSearchIndex)
class CertificateSearchIndexAdmin(admin.ModelAdmin):
    """Админка для поисковых индексов сертификатов"""
    
    list_display = [
        'certificate', 'grade', 'heat_number', 'certificate_number', 
        'processing_status', 'get_text_length', 'indexed_at'
    ]
    list_filter = ['processing_status', 'indexed_at']
    search_fields = [
        'certificate__material__material_grade', 'grade', 'heat_number', 
        'certificate_number', 'supplier', 'extracted_text'
    ]
    readonly_fields = ['indexed_at', 'search_vector']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('certificate', 'processing_status', 'error_message')
        }),
        ('Извлеченные данные', {
            'fields': ('grade', 'heat_number', 'certificate_number', 'supplier'),
            'classes': ('collapse',)
        }),
        ('Технические данные', {
            'fields': ('chemical_composition', 'mechanical_properties', 'test_results'),
            'classes': ('collapse',)
        }),
        ('Поисковая информация', {
            'fields': ('extracted_text_preview', 'search_vector', 'indexed_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_text_length(self, obj):
        """Длина извлеченного текста"""
        if obj.extracted_text:
            length = len(obj.extracted_text)
            if length > 1000:
                return format_html(
                    '<span style="color: green;">{} символов</span>', 
                    length
                )
            elif length > 100:
                return format_html(
                    '<span style="color: orange;">{} символов</span>', 
                    length
                )
            else:
                return format_html(
                    '<span style="color: red;">{} символов</span>', 
                    length
                )
        return format_html('<span style="color: gray;">Нет текста</span>')
    
    get_text_length.short_description = 'Длина текста'
    
    def extracted_text_preview(self, obj):
        """Превью извлеченного текста"""
        if obj.extracted_text:
            preview = obj.extracted_text[:500] + "..." if len(obj.extracted_text) > 500 else obj.extracted_text
            return format_html('<pre style="max-height: 200px; overflow-y: auto;">{}</pre>', preview)
        return "Текст не извлечен"
    
    extracted_text_preview.short_description = 'Превью текста'
    
    def get_urls(self):
        """Дополнительные URL для управления"""
        urls = super().get_urls()
        custom_urls = [
            path('reprocess-selected/', self.admin_site.admin_view(self.reprocess_selected), 
                 name='certificates_reprocess_selected'),
            path('<int:object_id>/reprocess/', self.admin_site.admin_view(self.reprocess_single), 
                 name='certificates_reprocess_single'),
        ]
        return custom_urls + urls
    
    def reprocess_selected(self, request):
        """Переобработка выбранных сертификатов"""
        if request.method == 'POST':
            selected_ids = request.POST.getlist('selected_ids')
            if selected_ids:
                # Получаем ID сертификатов
                certificate_ids = list(CertificateSearchIndex.objects.filter(
                    id__in=selected_ids
                ).values_list('certificate_id', flat=True))
                
                # Запускаем обработку
                reprocess_certificates_batch.delay(certificate_ids, force_reprocess=True)
                
                messages.success(request, f"Запущена переобработка {len(certificate_ids)} сертификатов")
            else:
                messages.error(request, "Не выбраны сертификаты для обработки")
        
        return redirect('admin:certificates_certificatesearchindex_changelist')
    
    def reprocess_single(self, request, object_id):
        """Переобработка одного сертификата"""
        try:
            search_index = self.get_object(request, object_id)
            if search_index:
                process_uploaded_certificate.delay(search_index.certificate_id)
                messages.success(request, f"Запущена переобработка сертификата {search_index.certificate}")
            else:
                messages.error(request, "Сертификат не найден")
        except Exception as e:
            messages.error(request, f"Ошибка: {e}")
        
        return redirect('admin:certificates_certificatesearchindex_changelist')
    
    actions = ['reprocess_certificates', 'clear_errors']
    
    def reprocess_certificates(self, request, queryset):
        """Действие для переобработки сертификатов"""
        certificate_ids = list(queryset.values_list('certificate_id', flat=True))
        reprocess_certificates_batch.delay(certificate_ids, force_reprocess=True)
        messages.success(request, f"Запущена переобработка {len(certificate_ids)} сертификатов")
    
    reprocess_certificates.short_description = "Переобработать выбранные сертификаты"
    
    def clear_errors(self, request, queryset):
        """Очистка ошибок для повторной обработки"""
        updated = queryset.filter(processing_status='failed').update(
            processing_status='pending',
            error_message=''
        )
        messages.success(request, f"Очищены ошибки для {updated} сертификатов")
    
    clear_errors.short_description = "Очистить ошибки и пометить для повторной обработки"


@admin.register(CertificatePreview)
class CertificatePreviewAdmin(admin.ModelAdmin):
    """Админка для превью сертификатов"""
    
    list_display = [
        'certificate', 'generation_status', 'get_preview_thumb', 
        'get_file_sizes', 'generated_at'
    ]
    list_filter = ['generation_status', 'generated_at']
    search_fields = ['certificate__material__material_grade']
    readonly_fields = ['generated_at', 'get_preview_display', 'get_thumbnail_display']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('certificate', 'generation_status', 'error_message')
        }),
        ('Файлы изображений', {
            'fields': ('preview_image', 'thumbnail', 'generated_at')
        }),
        ('Превью', {
            'fields': ('get_preview_display', 'get_thumbnail_display'),
            'classes': ('collapse',)
        })
    )
    
    def get_preview_thumb(self, obj):
        """Миниатюра превью в списке"""
        if obj.thumbnail:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 50px;" title="Превью сертификата" />',
                obj.thumbnail.url
            )
        return format_html('<span style="color: gray;">Нет превью</span>')
    
    get_preview_thumb.short_description = 'Превью'
    
    def get_file_sizes(self, obj):
        """Размеры файлов"""
        info = []
        if obj.preview_image:
            try:
                size = obj.preview_image.size
                info.append(f"Превью: {size // 1024} KB")
            except:
                info.append("Превью: размер неизвестен")
        
        if obj.thumbnail:
            try:
                size = obj.thumbnail.size
                info.append(f"Миниатюра: {size // 1024} KB")
            except:
                info.append("Миниатюра: размер неизвестен")
        
        return " | ".join(info) if info else "Нет файлов"
    
    get_file_sizes.short_description = 'Размеры файлов'
    
    def get_preview_display(self, obj):
        """Отображение превью в админке"""
        if obj.preview_image:
            return format_html(
                '<img src="{}" style="max-width: 400px; max-height: 600px; border: 1px solid #ddd;" />',
                obj.preview_image.url
            )
        return "Превью не сгенерировано"
    
    get_preview_display.short_description = 'Превью изображение'
    
    def get_thumbnail_display(self, obj):
        """Отображение миниатюры в админке"""
        if obj.thumbnail:
            return format_html(
                '<img src="{}" style="max-width: 200px; max-height: 300px; border: 1px solid #ddd;" />',
                obj.thumbnail.url
            )
        return "Миниатюра не сгенерирована"
    
    get_thumbnail_display.short_description = 'Миниатюра'
    
    actions = ['regenerate_previews']
    
    def regenerate_previews(self, request, queryset):
        """Регенерация превью"""
        certificate_ids = list(queryset.values_list('certificate_id', flat=True))
        
        for cert_id in certificate_ids:
            generate_certificate_preview.delay(cert_id)
        
        messages.success(request, f"Запущена регенерация превью для {len(certificate_ids)} сертификатов")
    
    regenerate_previews.short_description = "Регенерировать превью"


@admin.register(ProcessingLog)
class ProcessingLogAdmin(admin.ModelAdmin):
    """Админка для логов обработки"""
    
    list_display = [
        'certificate', 'operation', 'status', 'duration_display',
        'started_at', 'completed_at'
    ]
    list_filter = ['operation', 'status', 'started_at']
    search_fields = ['certificate__material__material_grade', 'error_message']
    readonly_fields = [
        'certificate', 'operation', 'status', 'started_at', 
        'completed_at', 'duration_seconds', 'metadata'
    ]
    
    def duration_display(self, obj):
        """Отображение длительности операции"""
        if obj.duration_seconds is not None:
            if obj.duration_seconds < 1:
                return f"{obj.duration_seconds * 1000:.0f} мс"
            elif obj.duration_seconds < 60:
                return f"{obj.duration_seconds:.1f} сек"
            else:
                return f"{obj.duration_seconds / 60:.1f} мин"
        return "-"
    
    duration_display.short_description = 'Длительность'
    
    def has_add_permission(self, request):
        """Запрещаем создание логов через админку"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Запрещаем изменение логов через админку"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Разрешаем удаление только суперпользователям"""
        return request.user.is_superuser
    
    actions = ['cleanup_old_logs']
    
    def cleanup_old_logs(self, request, queryset):
        """Очистка старых логов"""
        cutoff_date = timezone.now() - timezone.timedelta(days=30)
        old_logs = queryset.filter(started_at__lt=cutoff_date)
        count = old_logs.count()
        old_logs.delete()
        messages.success(request, f"Удалено {count} старых записей логов")
    
    cleanup_old_logs.short_description = "Удалить логи старше 30 дней"


# Кастомные представления для статистики
class CertificateProcessingStatsAdmin:
    """Статистика обработки сертификатов"""
    
    def changelist_view(self, request, extra_context=None):
        """Отображение статистики"""
        from django.db.models import Count, Q, Avg
        from datetime import datetime, timedelta
        from apps.warehouse.models import Certificate
        
        # Общая статистика
        total_certificates = Certificate.objects.count()
        
        # Статистика обработки
        processing_stats = CertificateSearchIndex.objects.aggregate(
            total_processed=Count('id'),
            completed=Count('id', filter=Q(processing_status='completed')),
            failed=Count('id', filter=Q(processing_status='failed')),
            pending=Count('id', filter=Q(processing_status='pending'))
        )
        
        # Статистика превью
        preview_stats = CertificatePreview.objects.aggregate(
            total_previews=Count('id'),
            completed_previews=Count('id', filter=Q(generation_status='completed')),
            failed_previews=Count('id', filter=Q(generation_status='failed'))
        )
        
        # Статистика по времени обработки
        time_stats = ProcessingLog.objects.filter(
            status='completed',
            duration_seconds__isnull=False
        ).aggregate(
            avg_text_time=Avg('duration_seconds', filter=Q(operation='text_extraction')),
            avg_preview_time=Avg('duration_seconds', filter=Q(operation='preview_generation')),
            avg_parsing_time=Avg('duration_seconds', filter=Q(operation='data_parsing'))
        )
        
        # Статистика за последние 7 дней
        week_ago = timezone.now() - timedelta(days=7)
        recent_stats = ProcessingLog.objects.filter(
            started_at__gte=week_ago
        ).values('operation').annotate(
            count=Count('id'),
            success_count=Count('id', filter=Q(status='completed')),
            avg_duration=Avg('duration_seconds')
        )
        
        # Топ ошибок
        top_errors = CertificateSearchIndex.objects.filter(
            processing_status='failed'
        ).values('error_message').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        extra_context = extra_context or {}
        extra_context.update({
            'total_certificates': total_certificates,
            'processing_stats': processing_stats,
            'preview_stats': preview_stats,
            'time_stats': time_stats,
            'recent_stats': recent_stats,
            'top_errors': top_errors,
            'unprocessed_count': total_certificates - processing_stats['total_processed'],
            'success_rate': round(
                processing_stats['completed'] / processing_stats['total_processed'] * 100, 1
            ) if processing_stats['total_processed'] > 0 else 0
        })
        
        return render(request, 'admin/certificates/processing_stats.html', extra_context)


# Регистрируем кастомное представление
try:
    from django.contrib.admin.sites import site
    # Добавляем ссылку на статистику в админку
    site.register_view(
        'certificates/stats/',
        view=CertificateProcessingStatsAdmin().changelist_view,
        name='Статистика обработки сертификатов'
    )
except AttributeError:
    # Если register_view не поддерживается, просто игнорируем
    pass