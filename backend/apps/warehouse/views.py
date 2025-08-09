from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.pagination import PageNumberPagination
from django.db.models import Count, Sum, Q
from django.http import HttpResponse, Http404
from django.utils import timezone
from django.core.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.contrib.auth.models import User
import logging

logger = logging.getLogger(__name__)
from .models import Material, MaterialReceipt, Certificate
from .permissions import (
    IsWarehouseStaff, IsQCInspector, IsLabTechnician,
    IsWarehouseOrReadOnly, CanCreateMaterials, CanModifyReceipts,
    RoleBasedViewSetMixin, get_user_role
)
from .serializers import (
    MaterialSerializer, MaterialListSerializer, MaterialDetailSerializer,
    MaterialReceiptSerializer, MaterialReceiptListSerializer, MaterialReceiptDetailSerializer,
    CertificateSerializer, CertificateSimpleSerializer,
    MaterialStatisticsSerializer, QRCodeDataSerializer, BulkMaterialOperationSerializer
)
from .services import (
    MaterialInspectionService, MaterialService, NotificationService, ServiceResponse
)
import json
import uuid
from datetime import datetime, timedelta


class WarehousePagination(PageNumberPagination):
    """Кастомная пагинация для модуля склада"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class BaseWarehouseViewSet(RoleBasedViewSetMixin, viewsets.ModelViewSet):
    """Базовый ViewSet для модуля склада с ролевыми разрешениями"""
    
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    pagination_class = WarehousePagination
    
    def perform_create(self, serializer):
        """Автоматическое заполнение полей аудита при создании"""
        serializer.save(
            created_by=self.request.user,
            updated_by=self.request.user
        )
    
    def perform_update(self, serializer):
        """Автоматическое заполнение полей аудита при обновлении"""
        serializer.save(updated_by=self.request.user)
    
    def get_queryset(self):
        """Базовый queryset с оптимизацией"""
        return super().get_queryset()
    
    def list(self, request, *args, **kwargs):
        """Переопределение list для добавления метаинформации"""
        response = super().list(request, *args, **kwargs)
        
        # Добавляем информацию о пользователе и его роли
        if hasattr(response, 'data') and isinstance(response.data, dict):
            response.data['user_info'] = {
                'username': request.user.username,
                'role': get_user_role(request.user),
                'permissions': {
                    'can_create': self._can_create(request),
                    'can_edit': self._can_edit(request),
                    'can_delete': self._can_delete(request)
                }
            }
        
        return response
    
    def _can_create(self, request):
        """Проверка права создания"""
        return any(
            perm.has_permission(request, self) 
            for perm in self.get_permissions() 
            if hasattr(perm, 'has_permission')
        )
    
    def _can_edit(self, request):
        """Проверка права редактирования"""
        return request.user.is_authenticated
    
    def _can_delete(self, request):
        """Проверка права удаления"""
        return request.user.is_superuser or IsWarehouseStaff().has_permission(request, self)


class MaterialViewSet(BaseWarehouseViewSet):
    """ViewSet для работы с материалами с полным CRUD и кастомными действиями"""
    
    queryset = Material.objects.filter(is_deleted=False)
    permission_classes = [permissions.IsAuthenticated, CanCreateMaterials]
    
    # Ролевые разрешения - только создание ограничено
    required_roles = {
        'create': ['warehouse', 'warehouse_staff', 'склад'],
        'update': ['warehouse', 'warehouse_staff', 'склад'],
        'partial_update': ['warehouse', 'warehouse_staff', 'склад'],
        'destroy': ['warehouse', 'warehouse_staff', 'склад'],
        'generate_qr_code': ['warehouse', 'warehouse_staff', 'склад'],
        'regenerate_qr': ['warehouse', 'warehouse_staff', 'склад'],
        'bulk_operations': ['warehouse', 'warehouse_staff', 'склад'],
        # Чтение и статистика доступны всем авторизованным
    }
    
    # Расширенная фильтрация
    filterset_fields = {
        'material_grade': ['exact', 'icontains', 'in'],
        'supplier': ['exact', 'icontains', 'in'],
        'unit': ['exact', 'in'],
        'receipt_date': ['gte', 'lte', 'date', 'year', 'month'],
        'location': ['exact', 'icontains'],
        'quantity': ['gte', 'lte', 'exact'],
        'created_at': ['gte', 'lte', 'date'],
        'updated_at': ['gte', 'lte', 'date'],
    }
    
    # Расширенный поиск
    search_fields = [
        'material_grade', 'supplier', 'order_number', 
        'certificate_number', 'heat_number', 'size', 'location',
        'created_by__username', 'updated_by__username'
    ]
    
    ordering_fields = [
        'material_grade', 'supplier', 'receipt_date', 'quantity', 
        'location', 'created_at', 'updated_at'
    ]
    ordering = ['-receipt_date', '-created_at']
    
    def get_serializer_class(self):
        """Выбор сериализатора в зависимости от действия"""
        if self.action == 'list':
            return MaterialListSerializer
        elif self.action == 'retrieve':
            return MaterialDetailSerializer
        return MaterialSerializer
    
    def get_queryset(self):
        """Оптимизированные запросы с prefetch_related и дополнительной фильтрацией"""
        queryset = super().get_queryset()
        
        # Базовая оптимизация для всех действий
        queryset = queryset.select_related('created_by', 'updated_by')
        
        if self.action == 'list':
            # Для списка добавляем информацию о сертификатах
            queryset = queryset.prefetch_related('certificate')
        elif self.action == 'retrieve':
            # Для детального просмотра загружаем все связанные данные
            queryset = queryset.prefetch_related(
                'certificate', 
                'receipts__received_by',
                'receipts__material'
            )
        elif self.action in ['statistics', 'low_stock']:
            # Для статистики не нужны связанные объекты
            queryset = queryset.only(
                'id', 'material_grade', 'supplier', 'quantity', 
                'unit', 'location', 'receipt_date'
            )
        
        # Дополнительная фильтрация по дате (последние 2 года по умолчанию)
        if not self.request.GET.get('show_all'):
            two_years_ago = timezone.now() - timezone.timedelta(days=730)
            queryset = queryset.filter(created_at__gte=two_years_ago)
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def qr_code(self, request, pk=None):
        """Получение данных QR кода материала"""
        material = self.get_object()
        
        qr_data = {
            'material_id': material.id,
            'external_id': material.external_id,
            'material_grade': material.material_grade,
            'supplier': material.supplier,
            'size': material.size,
            'location': material.location,
            'generated_at': timezone.now(),
            'qr_code_url': None
        }
        
        if material.qr_code:
            qr_data['qr_code_url'] = request.build_absolute_uri(material.qr_code.url)
        
        serializer = QRCodeDataSerializer(qr_data)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], 
            permission_classes=[permissions.IsAuthenticated, IsWarehouseStaff])
    def generate_qr_code(self, request, pk=None):
        """Генерация QR кода для материала"""
        material = self.get_object()
        
        # Проверяем права доступа
        if not IsWarehouseStaff().has_object_permission(request, self, material):
            return Response(
                {'error': 'Недостаточно прав для генерации QR кода'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            # Удаляем старый QR код если есть
            if material.qr_code:
                material.qr_code.delete(save=False)
            
            # Генерируем новый
            material.generate_qr_code()
            material.updated_by = request.user
            material.save()
            
            return Response({
                'message': 'QR код успешно сгенерирован',
                'material_id': material.id,
                'external_id': str(material.external_id),
                'qr_code_url': request.build_absolute_uri(material.qr_code.url) if material.qr_code else None,
                'generated_at': timezone.now(),
                'generated_by': request.user.username
            })
        except Exception as e:
            return Response(
                {'error': f'Ошибка генерации QR кода: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'],
            permission_classes=[permissions.IsAuthenticated, IsWarehouseStaff])
    def regenerate_qr(self, request, pk=None):
        """Перегенерация QR кода (алиас для generate_qr_code)"""
        return self.generate_qr_code(request, pk)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Статистика по материалам"""
        queryset = self.get_queryset()
        
        # Общая статистика
        total_materials = queryset.count()
        total_quantity = queryset.aggregate(
            total=Sum('quantity')
        )['total'] or 0
        
        # Статистика по маркам
        by_grade = dict(
            queryset.values('material_grade')
            .annotate(count=Count('id'))
            .values_list('material_grade', 'count')
        )
        
        # Статистика по поставщикам
        by_supplier = dict(
            queryset.values('supplier')
            .annotate(count=Count('id'))
            .values_list('supplier', 'count')
        )
        
        # Статистика по единицам измерения
        by_unit = dict(
            queryset.values('unit')
            .annotate(count=Count('id'))
            .values_list('unit', 'count')
        )
        
        # Недавние поступления (за последние 7 дней)
        week_ago = timezone.now() - timedelta(days=7)
        recent_receipts_count = MaterialReceipt.objects.filter(
            material__in=queryset,
            receipt_date__gte=week_ago
        ).count()
        
        # Ожидающие ОТК
        pending_qc_count = MaterialReceipt.objects.filter(
            material__in=queryset,
            status='pending_qc'
        ).count()
        
        stats_data = {
            'total_materials': total_materials,
            'total_quantity': total_quantity,
            'by_grade': by_grade,
            'by_supplier': by_supplier,
            'by_unit': by_unit,
            'recent_receipts_count': recent_receipts_count,
            'pending_qc_count': pending_qc_count
        }
        
        serializer = MaterialStatisticsSerializer(stats_data)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def bulk_operations(self, request):
        """Массовые операции с материалами"""
        serializer = BulkMaterialOperationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        material_ids = serializer.validated_data['material_ids']
        operation = serializer.validated_data['operation']
        
        materials = Material.objects.filter(
            id__in=material_ids,
            is_deleted=False
        )
        
        if operation == 'delete':
            # Мягкое удаление
            updated_count = materials.update(
                is_deleted=True,
                deleted_at=timezone.now(),
                deleted_by=request.user
            )
            
            return Response({
                'message': f'Удалено материалов: {updated_count}',
                'operation': 'delete',
                'affected_count': updated_count
            })
        
        elif operation == 'change_location':
            new_location = serializer.validated_data['new_location']
            updated_count = materials.update(
                location=new_location,
                updated_by=request.user
            )
            
            return Response({
                'message': f'Изменено местоположение для {updated_count} материалов',
                'operation': 'change_location',
                'new_location': new_location,
                'affected_count': updated_count
            })
        
        elif operation == 'export':
            # Подготовка данных для экспорта
            materials_data = MaterialListSerializer(
                materials, 
                many=True, 
                context={'request': request}
            ).data
            
            return Response({
                'message': f'Данные для экспорта {materials.count()} материалов',
                'operation': 'export',
                'data': materials_data,
                'export_date': timezone.now(),
                'affected_count': materials.count()
            })
    
    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Материалы с низким остатком"""
        # Можно добавить параметр min_quantity
        min_quantity = float(request.query_params.get('min_quantity', 10))
        
        low_stock_materials = self.get_queryset().filter(
            quantity__lt=min_quantity
        ).order_by('quantity')
        
        serializer = self.get_serializer(low_stock_materials, many=True)
        return Response({
            'count': low_stock_materials.count(),
            'min_quantity': min_quantity,
            'materials': serializer.data
        })


class MaterialReceiptViewSet(BaseWarehouseViewSet):
    """ViewSet для работы с приемками материалов с кастомными разрешениями"""
    
    queryset = MaterialReceipt.objects.all()
    permission_classes = [permissions.IsAuthenticated, CanModifyReceipts]
    
    # Ролевые разрешения - только склад может создавать приемки
    required_roles = {
        'create': ['warehouse', 'warehouse_staff', 'склад'],
        'update': ['warehouse', 'warehouse_staff', 'склад', 'qc', 'quality_control', 'отк'],
        'partial_update': ['warehouse', 'warehouse_staff', 'склад', 'qc', 'quality_control', 'отк'],
        'destroy': ['warehouse', 'warehouse_staff', 'склад'],
        'change_status': ['warehouse', 'warehouse_staff', 'склад', 'qc', 'quality_control', 'отк'],
        'transition_status': ['warehouse', 'warehouse_staff', 'склад', 'qc', 'quality_control', 'отк'],
        # Чтение доступно всем авторизованным
    }
    
    # Расширенная фильтрация
    filterset_fields = {
        'status': ['exact', 'in'],
        'receipt_date': ['gte', 'lte', 'date', 'year', 'month'],
        'material__material_grade': ['exact', 'icontains', 'in'],
        'material__supplier': ['exact', 'icontains', 'in'],
        'material__unit': ['exact', 'in'],
        'received_by': ['exact'],
        'received_by__username': ['exact', 'icontains'],
        'created_at': ['gte', 'lte', 'date'],
        'updated_at': ['gte', 'lte', 'date'],
    }
    
    # Расширенный поиск
    search_fields = [
        'document_number', 'notes',
        'material__material_grade', 'material__supplier',
        'material__certificate_number', 'material__heat_number',
        'received_by__username', 'received_by__first_name', 'received_by__last_name'
    ]
    
    ordering_fields = [
        'receipt_date', 'status', 'document_number', 
        'material__material_grade', 'created_at', 'updated_at'
    ]
    ordering = ['-receipt_date', '-created_at']
    
    def get_serializer_class(self):
        """Выбор сериализатора в зависимости от действия"""
        if self.action == 'list':
            return MaterialReceiptListSerializer
        elif self.action == 'retrieve':
            return MaterialReceiptDetailSerializer
        return MaterialReceiptSerializer
    
    def get_queryset(self):
        """Оптимизированные запросы с включением материалов"""
        queryset = super().get_queryset()
        
        # Базовая оптимизация - всегда включаем материал и пользователей
        queryset = queryset.select_related(
            'material', 'received_by', 'created_by', 'updated_by'
        )
        
        if self.action == 'list':
            # Для списка добавляем базовую информацию о материале
            # Сертификат не включаем для экономии запросов
            pass
        elif self.action == 'retrieve':
            # Для детального просмотра загружаем сертификат материала
            queryset = queryset.prefetch_related(
                'material__certificate'
            )
        elif self.action in ['pending_qc', 'daily_report']:
            # Для отчетов используем defer вместо only
            queryset = queryset.defer('notes')
        
        return queryset
    
    def perform_create(self, serializer):
        """Переопределение создания для проверки прав склада"""
        # Проверяем, что пользователь из склада
        if not IsWarehouseStaff().has_permission(self.request, self):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Только персонал склада может создавать приемки")
        
        super().perform_create(serializer)
    
    @action(detail=True, methods=['post'],
            permission_classes=[permissions.IsAuthenticated, CanModifyReceipts])
    def change_status(self, request, pk=None):
        """Изменение статуса приемки"""
        receipt = self.get_object()
        new_status = request.data.get('status')
        comment = request.data.get('comment', '')
        
        if new_status not in dict(MaterialReceipt.STATUS_CHOICES):
            return Response(
                {'error': 'Недопустимый статус'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        old_status = receipt.status
        receipt.status = new_status
        receipt.updated_by = request.user
        
        # Добавляем комментарий к заметкам если указан
        if comment:
            current_notes = receipt.notes or ''
            timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            new_note = f"[{timestamp}] {request.user.username}: {comment}"
            receipt.notes = f"{current_notes}\n{new_note}" if current_notes else new_note
        
        receipt.save()
        
        # Отправляем уведомления о смене статуса
        try:
            from apps.notifications.services import telegram_service
            
            # Определяем получателей уведомления
            recipients = []
            
            # Добавляем пользователей по ролям в зависимости от статуса
            if new_status == 'in_qc':
                # Уведомляем сотрудников ОТК
                qc_users = User.objects.filter(groups__name='QC').values_list('id', flat=True)
                recipients.extend(qc_users)
            elif new_status == 'approved':
                # Уведомляем лабораторию и производство
                lab_users = User.objects.filter(groups__name='Laboratory').values_list('id', flat=True)
                prod_users = User.objects.filter(groups__name='Production').values_list('id', flat=True)
                recipients.extend(lab_users)
                recipients.extend(prod_users)
            elif new_status == 'rejected':
                # Уведомляем склад и администраторов
                warehouse_users = User.objects.filter(groups__name='Warehouse').values_list('id', flat=True)
                admin_users = User.objects.filter(groups__name='Administrators').values_list('id', flat=True)
                recipients.extend(warehouse_users)
                recipients.extend(admin_users)
            
            # Отправляем уведомления
            for user_id in set(recipients):  # убираем дубликаты
                is_urgent = new_status == 'rejected'  # отклонение - срочное уведомление
                telegram_service.send_status_update(
                    user_id=user_id,
                    material=receipt.material,
                    old_status=old_status,
                    new_status=new_status,
                    is_urgent=is_urgent
                )
                
        except Exception as e:
            # Логируем ошибку, но не прерываем основной процесс
            logger.error(f"Ошибка отправки уведомления о смене статуса: {e}")
        
        return Response({
            'message': f'Статус изменен с "{old_status}" на "{new_status}"',
            'old_status': old_status,
            'new_status': new_status,
            'receipt_id': receipt.id,
            'changed_by': request.user.username,
            'changed_at': timezone.now(),
            'comment': comment
        })

    @action(detail=True, methods=['post'],
            permission_classes=[permissions.IsAuthenticated, CanModifyReceipts])
    def transition_status(self, request, pk=None):
        """Переход статуса приемки с валидацией переходов"""
        receipt = self.get_object()
        new_status = request.data.get('status')
        comment = request.data.get('comment', '')
        
        # Определяем допустимые переходы статусов
        status_transitions = {
            'pending_qc': ['in_qc', 'rejected'],
            'in_qc': ['approved', 'rejected', 'pending_qc'],
            'approved': ['rejected'],  # Можно только отклонить
            'rejected': ['pending_qc']  # Можно вернуть на проверку
        }
        
        current_status = receipt.status
        allowed_statuses = status_transitions.get(current_status, [])
        
        if new_status not in allowed_statuses:
            return Response({
                'error': f'Недопустимый переход из статуса "{current_status}" в "{new_status}"',
                'current_status': current_status,
                'allowed_transitions': allowed_statuses
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Дополнительные проверки для определенных статусов
        if new_status == 'approved':
            # Проверяем, что есть все необходимые данные для одобрения
            material = receipt.material
            if not hasattr(material, 'certificate') or not material.certificate:
                return Response({
                    'error': 'Невозможно одобрить приемку без сертификата материала',
                    'material_id': material.id
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Выполняем переход
        old_status = receipt.status
        receipt.status = new_status
        receipt.updated_by = request.user
        
        # Добавляем комментарий к заметкам
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        transition_note = f"[{timestamp}] {request.user.username}: переход {old_status} → {new_status}"
        if comment:
            transition_note += f" ({comment})"
        
        current_notes = receipt.notes or ''
        receipt.notes = f"{current_notes}\n{transition_note}" if current_notes else transition_note
        
        receipt.save()
        
        return Response({
            'message': f'Статус успешно изменен: {old_status} → {new_status}',
            'transition': {
                'from': old_status,
                'to': new_status,
                'performed_by': request.user.username,
                'performed_at': timezone.now(),
                'comment': comment
            },
            'receipt_id': receipt.id,
            'next_possible_transitions': status_transitions.get(new_status, [])
        })

    @action(detail=True, methods=['post'],
            permission_classes=[permissions.IsAuthenticated, IsQCInspector])
    def create_qc_inspection(self, request, pk=None):
        """Создание инспекции ОТК для приемки материала"""
        receipt = self.get_object()
        
        # Используем сервис для создания инспекции
        service_response = MaterialInspectionService.create_inspection(
            material_receipt_id=receipt.id,
            inspector_id=request.user.id,
            auto_assign=True
        )
        
        if service_response.success:
            return Response(service_response.to_dict(), status=status.HTTP_201_CREATED)
        else:
            return Response(
                service_response.to_dict(),
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get'])
    def check_inspection_requirements(self, request, pk=None):
        """Проверка требований ППСД и УЗК для материала"""
        receipt = self.get_object()
        material = receipt.material
        
        # Проверка ППСД
        ppsd_response = MaterialInspectionService.check_ppsd_requirement(
            material.material_grade, material.size
        )
        
        # Проверка УЗК
        ultrasonic_response = MaterialInspectionService.check_ultrasonic_requirement(
            material.material_grade, material.size
        )
        
        result = {
            'material_id': material.id,
            'material_grade': material.material_grade,
            'size': material.size,
            'ppsd': ppsd_response.to_dict() if ppsd_response.success else {'error': ppsd_response.error},
            'ultrasonic': ultrasonic_response.to_dict() if ultrasonic_response.success else {'error': ultrasonic_response.error}
        }
        
        return Response(result)

    @action(detail=False, methods=['post'],
            permission_classes=[permissions.IsAuthenticated, IsWarehouseStaff])
    def process_material_receipt(self, request):
        """Обработка поступления материала с автоматическим созданием инспекции"""
        material_id = request.data.get('material_id')
        document_number = request.data.get('document_number')
        auto_create_qc = request.data.get('auto_create_qc', True)
        
        if not material_id or not document_number:
            return Response({
                'error': 'Обязательные поля: material_id, document_number'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Используем сервис для обработки поступления
        service_response = MaterialService.process_material_receipt(
            material_id=material_id,
            received_by=request.user,
            document_number=document_number,
            auto_create_qc=auto_create_qc
        )
        
        if service_response.success:
            return Response(service_response.to_dict(), status=status.HTTP_201_CREATED)
        else:
            return Response(
                service_response.to_dict(),
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def pending_qc(self, request):
        """Приемки, ожидающие ОТК"""
        pending = self.get_queryset().filter(status='pending_qc')
        serializer = self.get_serializer(pending, many=True)
        
        return Response({
            'count': pending.count(),
            'receipts': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def daily_report(self, request):
        """Ежедневный отчет по приемкам"""
        date_str = request.query_params.get('date')
        
        if date_str:
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Неверный формат даты. Используйте YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            target_date = timezone.now().date()
        
        daily_receipts = self.get_queryset().filter(
            receipt_date__date=target_date
        )
        
        # Статистика по статусам
        status_stats = {}
        for status_code, status_name in MaterialReceipt.STATUS_CHOICES:
            count = daily_receipts.filter(status=status_code).count()
            status_stats[status_code] = {
                'name': status_name,
                'count': count
            }
        
        serializer = self.get_serializer(daily_receipts, many=True)
        
        return Response({
            'date': target_date,
            'total_receipts': daily_receipts.count(),
            'status_breakdown': status_stats,
            'receipts': serializer.data
        })


class CertificateViewSet(BaseWarehouseViewSet):
    """ViewSet для работы с сертификатами с ролевыми разрешениями"""
    
    queryset = Certificate.objects.all()
    serializer_class = CertificateSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    permission_classes = [permissions.IsAuthenticated, IsWarehouseOrReadOnly]
    
    # Ролевые разрешения
    required_roles = {
        'create': ['warehouse', 'warehouse_staff', 'склад'],
        'update': ['warehouse', 'warehouse_staff', 'склад'],
        'partial_update': ['warehouse', 'warehouse_staff', 'склад'],
        'destroy': ['warehouse', 'warehouse_staff', 'склад'],
        'reparse': ['warehouse', 'warehouse_staff', 'склад', 'lab', 'laboratory'],
        # Чтение доступно всем авторизованным
    }
    
    # Фильтрация
    filterset_fields = {
        'uploaded_at': ['gte', 'lte', 'date'],
        'material__material_grade': ['exact', 'icontains'],
        'material__supplier': ['exact', 'icontains'],
    }
    search_fields = [
        'material__material_grade', 'material__supplier',
        'material__certificate_number', 'file_hash'
    ]
    ordering_fields = ['uploaded_at', 'file_size']
    ordering = ['-uploaded_at']
    
    def get_queryset(self):
        """Оптимизированные запросы"""
        return super().get_queryset().select_related(
            'material', 'created_by', 'updated_by'
        )
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Скачивание PDF файла сертификата"""
        certificate = self.get_object()
        
        if not certificate.pdf_file:
            raise Http404("PDF файл не найден")
        
        try:
            # Подготовка HTTP ответа для скачивания файла
            response = HttpResponse(
                certificate.pdf_file.read(),
                content_type='application/pdf'
            )
            
            # Формирование имени файла
            filename = f"certificate_{certificate.material.material_grade}_{certificate.material.certificate_number}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Content-Length'] = certificate.file_size
            
            return response
            
        except Exception as e:
            return Response(
                {'error': f'Ошибка при скачивании файла: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def reparse(self, request, pk=None):
        """Повторное извлечение данных из PDF"""
        certificate = self.get_object()
        
        try:
            # Повторно извлекаем текст и сохраняем
            extracted_text = certificate.extract_text_from_pdf()
            certificate.save()  # save() вызовет повторное извлечение
            
            return Response({
                'message': 'Данные успешно извлечены из PDF',
                'extracted_text_length': len(extracted_text) if extracted_text else 0,
                'parsed_data': certificate.parsed_data
            })
            
        except Exception as e:
            return Response(
                {'error': f'Ошибка при извлечении данных: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def large_files(self, request):
        """Сертификаты с большими файлами"""
        # Файлы больше 5MB
        min_size = int(request.query_params.get('min_size_mb', 5)) * 1024 * 1024
        
        large_files = self.get_queryset().filter(
            file_size__gt=min_size
        ).order_by('-file_size')
        
        serializer = self.get_serializer(large_files, many=True)
        
        return Response({
            'count': large_files.count(),
            'min_size_mb': min_size / 1024 / 1024,
            'total_size_mb': sum(cert.file_size for cert in large_files) / 1024 / 1024,
            'certificates': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def missing_metadata(self, request):
        """Сертификаты без извлеченных метаданных"""
        missing_metadata = self.get_queryset().filter(
            Q(parsed_data__isnull=True) | Q(parsed_data={})
        )
        
        serializer = self.get_serializer(missing_metadata, many=True)
        
        return Response({
            'count': missing_metadata.count(),
            'certificates': serializer.data
        })
    
    def perform_create(self, serializer):
        """Создание сертификата с автоматическим извлечением данных"""
        super().perform_create(serializer)
        
        # После создания запускаем извлечение данных
        certificate = serializer.instance
        try:
            certificate.extract_text_from_pdf()
            certificate.save()
        except Exception as e:
            # Логируем ошибку, но не прерываем создание
            print(f"Ошибка извлечения данных из PDF: {e}")


# Дополнительные ViewSets для вспомогательных операций

class WarehouseReportsViewSet(viewsets.ViewSet):
    """ViewSet для отчетов склада"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def inventory_summary(self, request):
        """Сводный отчет по остаткам"""
        materials = Material.objects.filter(is_deleted=False)
        
        summary = {
            'total_positions': materials.count(),
            'total_quantity_kg': materials.filter(unit='kg').aggregate(
                total=Sum('quantity')
            )['total'] or 0,
            'total_quantity_pcs': materials.filter(unit='pcs').aggregate(
                total=Sum('quantity')
            )['total'] or 0,
            'by_location': {},
            'by_grade': {},
            'low_stock_alerts': []
        }
        
        # По местоположениям
        by_location = materials.values('location').annotate(
            count=Count('id'),
            total_quantity=Sum('quantity')
        )
        
        for item in by_location:
            location = item['location'] or 'Не указано'
            summary['by_location'][location] = {
                'count': item['count'],
                'total_quantity': float(item['total_quantity'] or 0)
            }
        
        # По маркам (топ 10)
        by_grade = materials.values('material_grade').annotate(
            count=Count('id'),
            total_quantity=Sum('quantity')
        ).order_by('-count')[:10]
        
        for item in by_grade:
            summary['by_grade'][item['material_grade']] = {
                'count': item['count'],
                'total_quantity': float(item['total_quantity'] or 0)
            }
        
        # Предупреждения о низких остатках
        low_stock = materials.filter(quantity__lt=10)
        summary['low_stock_alerts'] = MaterialListSerializer(
            low_stock[:10], 
            many=True, 
            context={'request': request}
        ).data
        
        return Response(summary)
    
    @action(detail=False, methods=['get'])
    def movement_history(self, request):
        """История движения материалов"""
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        
        receipts = MaterialReceipt.objects.filter(
            receipt_date__gte=start_date
        ).select_related('material', 'received_by')
        
        # Группировка по дням
        daily_movements = {}
        for receipt in receipts:
            date_key = receipt.receipt_date.date().isoformat()
            if date_key not in daily_movements:
                daily_movements[date_key] = {
                    'date': date_key,
                    'receipts_count': 0,
                    'total_materials': 0,
                    'by_status': {}
                }
            
            daily_movements[date_key]['receipts_count'] += 1
            daily_movements[date_key]['total_materials'] += 1
            
            status = receipt.status
            if status not in daily_movements[date_key]['by_status']:
                daily_movements[date_key]['by_status'][status] = 0
            daily_movements[date_key]['by_status'][status] += 1
        
        return Response({
            'period_days': days,
            'start_date': start_date.date(),
            'end_date': timezone.now().date(),
            'total_receipts': receipts.count(),
            'daily_movements': list(daily_movements.values())
        }) 