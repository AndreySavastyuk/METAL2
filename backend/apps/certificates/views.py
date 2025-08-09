"""
API для работы с сертификатами и поиском
"""
import logging
from typing import Dict, Any
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from django.utils import timezone
from apps.warehouse.models import Certificate
from .models import CertificateSearchIndex, CertificatePreview
from .services import certificate_processor
from .tasks import process_uploaded_certificate, reprocess_certificates_batch

logger = logging.getLogger(__name__)


class CertificateSearchPagination(PageNumberPagination):
    """Пагинация для поиска сертификатов"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class CertificateProcessingViewSet(viewsets.ViewSet):
    """
    ViewSet для управления обработкой сертификатов
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        Полнотекстовый поиск в сертификатах
        
        Параметры:
        - q: поисковый запрос (обязательный)
        - limit: количество результатов (по умолчанию 50)
        - include_preview: включать ли URL превью (по умолчанию true)
        """
        query = request.query_params.get('q', '').strip()
        limit = min(int(request.query_params.get('limit', 50)), 100)
        include_preview = request.query_params.get('include_preview', 'true').lower() == 'true'
        
        if not query:
            return Response(
                {'error': 'Параметр q (поисковый запрос) является обязательным'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(query) < 2:
            return Response(
                {'error': 'Поисковый запрос должен содержать минимум 2 символа'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Выполняем поиск через сервис
            results = certificate_processor.search_in_certificates(query, limit=limit)
            
            # Дополняем результаты если нужно
            for result in results:
                if not include_preview:
                    result.pop('preview_url', None)
                
                # Добавляем дополнительную информацию
                try:
                    certificate = Certificate.objects.get(id=result['certificate_id'])
                    result['file_size'] = certificate.file_size
                    result['uploaded_at'] = certificate.uploaded_at
                    result['material_info'] = {
                        'id': certificate.material.id,
                        'size': certificate.material.size,
                        'quantity': str(certificate.material.quantity),
                        'unit': certificate.material.get_unit_display(),
                    }
                except Certificate.DoesNotExist:
                    pass
            
            return Response({
                'query': query,
                'total_results': len(results),
                'results': results,
                'search_time': timezone.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Ошибка поиска в сертификатах: {e}")
            return Response(
                {'error': 'Ошибка выполнения поиска'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def suggestions(self, request):
        """
        Автодополнение для поискового запроса
        
        Параметры:
        - q: начало поискового запроса
        - type: тип подсказок (grade, heat_number, supplier)
        """
        query = request.query_params.get('q', '').strip()
        suggestion_type = request.query_params.get('type', 'all')
        
        if len(query) < 1:
            return Response({'suggestions': []})
        
        suggestions = []
        
        try:
            # Получаем уникальные значения из индекса
            search_indexes = CertificateSearchIndex.objects.filter(
                processing_status='completed'
            )
            
            if suggestion_type in ['grade', 'all']:
                grades = search_indexes.filter(
                    grade__icontains=query
                ).values_list('grade', flat=True).distinct()[:10]
                suggestions.extend([
                    {'type': 'grade', 'value': grade, 'label': f"Марка: {grade}"}
                    for grade in grades if grade
                ])
            
            if suggestion_type in ['heat_number', 'all']:
                heats = search_indexes.filter(
                    heat_number__icontains=query
                ).values_list('heat_number', flat=True).distinct()[:10]
                suggestions.extend([
                    {'type': 'heat_number', 'value': heat, 'label': f"Плавка: {heat}"}
                    for heat in heats if heat
                ])
            
            if suggestion_type in ['supplier', 'all']:
                suppliers = search_indexes.filter(
                    supplier__icontains=query
                ).values_list('supplier', flat=True).distinct()[:10]
                suggestions.extend([
                    {'type': 'supplier', 'value': supplier, 'label': f"Поставщик: {supplier}"}
                    for supplier in suppliers if supplier
                ])
            
            if suggestion_type in ['certificate', 'all']:
                certs = search_indexes.filter(
                    certificate_number__icontains=query
                ).values_list('certificate_number', flat=True).distinct()[:10]
                suggestions.extend([
                    {'type': 'certificate', 'value': cert, 'label': f"Сертификат: {cert}"}
                    for cert in certs if cert
                ])
            
            # Сортируем по релевантности
            suggestions.sort(key=lambda x: x['value'].lower().startswith(query.lower()), reverse=True)
            
            return Response({
                'query': query,
                'suggestions': suggestions[:20]  # Максимум 20 подсказок
            })
            
        except Exception as e:
            logger.error(f"Ошибка получения подсказок: {e}")
            return Response({'suggestions': []})
    
    @action(detail=True, methods=['post'])
    def reprocess(self, request, pk=None):
        """
        Переобработка конкретного сертификата
        """
        try:
            certificate = Certificate.objects.get(id=pk)
            
            # Проверяем права доступа
            if not request.user.has_perm('warehouse.change_certificate'):
                return Response(
                    {'error': 'Недостаточно прав для переобработки сертификата'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Запускаем переобработку
            task = process_uploaded_certificate.delay(certificate.id)
            
            return Response({
                'message': 'Переобработка сертификата запущена',
                'certificate_id': certificate.id,
                'task_id': task.id,
                'material': str(certificate.material)
            })
            
        except Certificate.DoesNotExist:
            return Response(
                {'error': 'Сертификат не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Ошибка переобработки сертификата {pk}: {e}")
            return Response(
                {'error': 'Ошибка запуска переобработки'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def reprocess_batch(self, request):
        """
        Пакетная переобработка сертификатов
        
        Параметры:
        - certificate_ids: список ID сертификатов
        - force: принудительная переобработка (по умолчанию false)
        """
        certificate_ids = request.data.get('certificate_ids', [])
        force = request.data.get('force', False)
        
        if not certificate_ids:
            return Response(
                {'error': 'Список certificate_ids не может быть пустым'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверяем права доступа
        if not request.user.has_perm('warehouse.change_certificate'):
            return Response(
                {'error': 'Недостаточно прав для переобработки сертификатов'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Проверяем существование сертификатов
        existing_ids = list(Certificate.objects.filter(
            id__in=certificate_ids
        ).values_list('id', flat=True))
        
        missing_ids = set(certificate_ids) - set(existing_ids)
        if missing_ids:
            return Response(
                {
                    'error': f'Сертификаты не найдены: {list(missing_ids)}',
                    'existing_ids': existing_ids
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Запускаем пакетную обработку
        try:
            task = reprocess_certificates_batch.delay(existing_ids, force_reprocess=force)
            
            return Response({
                'message': f'Запущена пакетная переобработка {len(existing_ids)} сертификатов',
                'certificate_ids': existing_ids,
                'task_id': task.id,
                'force_reprocess': force
            })
            
        except Exception as e:
            logger.error(f"Ошибка пакетной переобработки: {e}")
            return Response(
                {'error': 'Ошибка запуска пакетной переобработки'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Статистика обработки сертификатов
        """
        try:
            from django.db.models import Count, Q, Avg
            
            # Общая статистика
            total_certificates = Certificate.objects.count()
            
            # Статистика обработки текста
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
            
            # Статистика извлеченных данных
            data_stats = CertificateSearchIndex.objects.filter(
                processing_status='completed'
            ).aggregate(
                with_grade=Count('id', filter=Q(grade__isnull=False, grade__gt='')),
                with_heat_number=Count('id', filter=Q(heat_number__isnull=False, heat_number__gt='')),
                with_supplier=Count('id', filter=Q(supplier__isnull=False, supplier__gt='')),
                with_chemical=Count('id', filter=Q(chemical_composition__isnull=False)),
            )
            
            # Вычисляем проценты
            success_rate = 0
            if processing_stats['total_processed'] > 0:
                success_rate = round(
                    processing_stats['completed'] / processing_stats['total_processed'] * 100, 1
                )
            
            preview_rate = 0
            if total_certificates > 0:
                preview_rate = round(
                    preview_stats['completed_previews'] / total_certificates * 100, 1
                )
            
            return Response({
                'total_certificates': total_certificates,
                'unprocessed': total_certificates - processing_stats['total_processed'],
                'processing': {
                    'success_rate': success_rate,
                    **processing_stats
                },
                'previews': {
                    'preview_rate': preview_rate,
                    **preview_stats
                },
                'extracted_data': data_stats,
                'updated_at': timezone.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики: {e}")
            return Response(
                {'error': 'Ошибка получения статистики'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def processing_status(self, request, pk=None):
        """
        Статус обработки конкретного сертификата
        """
        try:
            certificate = Certificate.objects.get(id=pk)
            
            # Статус обработки текста
            text_status = {
                'status': 'not_processed',
                'error': None,
                'extracted_data': {}
            }
            
            try:
                search_index = certificate.search_index
                text_status['status'] = search_index.processing_status
                text_status['error'] = search_index.error_message
                text_status['indexed_at'] = search_index.indexed_at
                
                if search_index.processing_status == 'completed':
                    text_status['extracted_data'] = {
                        'grade': search_index.grade,
                        'heat_number': search_index.heat_number,
                        'certificate_number': search_index.certificate_number,
                        'supplier': search_index.supplier,
                        'text_length': len(search_index.extracted_text) if search_index.extracted_text else 0,
                        'chemical_elements': len(search_index.chemical_composition) if search_index.chemical_composition else 0,
                        'mechanical_properties': len(search_index.mechanical_properties) if search_index.mechanical_properties else 0
                    }
            except:
                pass
            
            # Статус превью
            preview_status = {
                'status': 'not_generated',
                'error': None,
                'preview_url': None,
                'thumbnail_url': None
            }
            
            try:
                preview = certificate.preview
                preview_status['status'] = preview.generation_status
                preview_status['error'] = preview.error_message
                preview_status['generated_at'] = preview.generated_at
                
                if preview.generation_status == 'completed':
                    preview_status['preview_url'] = preview.preview_image.url if preview.preview_image else None
                    preview_status['thumbnail_url'] = preview.thumbnail.url if preview.thumbnail else None
            except:
                pass
            
            return Response({
                'certificate_id': certificate.id,
                'material': str(certificate.material),
                'uploaded_at': certificate.uploaded_at,
                'file_size': certificate.file_size,
                'file_hash': certificate.file_hash,
                'text_processing': text_status,
                'preview_generation': preview_status
            })
            
        except Certificate.DoesNotExist:
            return Response(
                {'error': 'Сертификат не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Ошибка получения статуса сертификата {pk}: {e}")
            return Response(
                {'error': 'Ошибка получения статуса'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )