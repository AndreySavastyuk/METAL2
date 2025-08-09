"""
Views для модуля контроля качества (ОТК)
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from .models import QCInspection, QCChecklist, QCChecklistItem, QCInspectionResult
from apps.warehouse.permissions import IsQCInspector, IsWarehouseStaff, get_user_role
from apps.warehouse.services import MaterialInspectionService, NotificationService
from .serializers import (
    QCInspectionSerializer, 
    QCChecklistSerializer, 
    QCInspectionResultSerializer
)


class QCInspectionViewSet(viewsets.ModelViewSet):
    """ViewSet для управления инспекциями ОТК"""
    
    queryset = QCInspection.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'status': ['exact', 'in'],
        'requires_ppsd': ['exact'],
        'requires_ultrasonic': ['exact'],
        'inspector': ['exact'],
        'inspection_date': ['gte', 'lte', 'date'],
        'material_receipt__material__material_grade': ['exact', 'icontains'],
        'material_receipt__material__supplier': ['exact', 'icontains'],
    }
    
    search_fields = [
        'material_receipt__material__material_grade',
        'material_receipt__material__supplier', 
        'material_receipt__material__certificate_number',
        'comments'
    ]
    
    ordering_fields = ['inspection_date', 'status', 'created_at', 'updated_at']
    ordering = ['-inspection_date', '-created_at']
    
    def get_queryset(self):
        """Оптимизированные запросы"""
        queryset = super().get_queryset()
        
        # Базовая оптимизация
        queryset = queryset.select_related(
            'material_receipt__material',
            'inspector', 
            'created_by', 
            'updated_by'
        )
        
        if self.action == 'retrieve':
            # Для детального просмотра загружаем результаты инспекции
            queryset = queryset.prefetch_related(
                'inspection_results__checklist_item__checklist'
            )
        
        return queryset
    
    def perform_create(self, serializer):
        """Автоматическое заполнение полей при создании"""
        serializer.save(
            created_by=self.request.user,
            updated_by=self.request.user
        )
    
    def perform_update(self, serializer):
        """Автоматическое заполнение полей при обновлении"""
        serializer.save(updated_by=self.request.user)
    
    @action(detail=True, methods=['post'],
            permission_classes=[permissions.IsAuthenticated, IsQCInspector])
    def transition_status(self, request, pk=None):
        """Переход статуса инспекции с использованием service layer"""
        inspection = self.get_object()
        new_status = request.data.get('status')
        comment = request.data.get('comment', '')
        
        if not new_status:
            return Response({
                'error': 'Поле status обязательно'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Используем сервис для перехода статуса
        service_response = MaterialInspectionService.transition_status(
            inspection_id=inspection.id,
            new_status=new_status,
            user=request.user,
            comment=comment
        )
        
        if service_response.success:
            # Отправляем уведомление об изменении статуса
            notification_response = NotificationService.send_status_change_notification(
                inspection_id=inspection.id,
                old_status=service_response.data['transition']['from'],
                new_status=service_response.data['transition']['to'],
                user=request.user
            )
            
            result = service_response.to_dict()
            if notification_response.success:
                result['notification'] = notification_response.data
            else:
                result['notification_warning'] = notification_response.error
            
            return Response(result)
        else:
            return Response(
                service_response.to_dict(),
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'],
            permission_classes=[permissions.IsAuthenticated, IsQCInspector])
    def assign_to_laboratory(self, request, pk=None):
        """Назначение материала в лабораторию"""
        inspection = self.get_object()
        
        # Используем сервис для назначения в лабораторию
        service_response = MaterialInspectionService.assign_to_laboratory(
            inspection_id=inspection.id
        )
        
        if service_response.success:
            return Response(service_response.to_dict())
        else:
            return Response(
                service_response.to_dict(),
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def completion_stats(self, request, pk=None):
        """Статистика выполнения инспекции"""
        inspection = self.get_object()
        
        total_items = inspection.inspection_results.count()
        completed_items = inspection.inspection_results.exclude(result='').count()
        critical_failures = inspection.get_critical_failures()
        completion_percentage = inspection.get_completion_percentage()
        
        return Response({
            'inspection_id': inspection.id,
            'total_items': total_items,
            'completed_items': completed_items,
            'completion_percentage': completion_percentage,
            'critical_failures_count': len(critical_failures),
            'critical_failures': [str(item) for item in critical_failures],
            'can_complete': inspection.can_complete(),
            'status': inspection.status,
            'requires_ppsd': inspection.requires_ppsd,
            'requires_ultrasonic': inspection.requires_ultrasonic
        })
    
    @action(detail=False, methods=['get'])
    def my_inspections(self, request):
        """Инспекции текущего пользователя"""
        if not IsQCInspector().has_permission(request, self):
            return Response({
                'error': 'Доступно только инспекторам ОТК'
            }, status=status.HTTP_403_FORBIDDEN)
        
        inspections = self.get_queryset().filter(inspector=request.user)
        
        # Группируем по статусам
        stats = {
            'total': inspections.count(),
            'by_status': {}
        }
        
        for choice_value, choice_label in QCInspection.STATUS_CHOICES:
            count = inspections.filter(status=choice_value).count()
            stats['by_status'][choice_value] = {
                'count': count,
                'label': choice_label
            }
        
        # Последние инспекции
        recent_inspections = inspections.order_by('-inspection_date')[:5]
        serializer = self.get_serializer(recent_inspections, many=True)
        
        return Response({
            'inspector': {
                'id': request.user.id,
                'username': request.user.username,
                'full_name': request.user.get_full_name()
            },
            'statistics': stats,
            'recent_inspections': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Дашборд для ОТК с общей статистикой"""
        queryset = self.get_queryset()
        
        # Общая статистика
        total_inspections = queryset.count()
        active_inspections = queryset.filter(status__in=['draft', 'in_progress']).count()
        completed_today = queryset.filter(
            completion_date__date=timezone.now().date()
        ).count()
        
        # Статистика по статусам
        status_stats = {}
        for choice_value, choice_label in QCInspection.STATUS_CHOICES:
            count = queryset.filter(status=choice_value).count()
            status_stats[choice_value] = {
                'count': count,
                'label': choice_label
            }
        
        # Статистика по требованиям
        ppsd_required = queryset.filter(requires_ppsd=True).count()
        ultrasonic_required = queryset.filter(requires_ultrasonic=True).count()
        
        # Просроченные инспекции (старше 3 дней в статусе draft/in_progress)
        overdue_threshold = timezone.now() - timezone.timedelta(days=3)
        overdue_inspections = queryset.filter(
            status__in=['draft', 'in_progress'],
            created_at__lt=overdue_threshold
        ).count()
        
        return Response({
            'summary': {
                'total_inspections': total_inspections,
                'active_inspections': active_inspections,
                'completed_today': completed_today,
                'overdue_inspections': overdue_inspections
            },
            'status_distribution': status_stats,
            'requirements': {
                'ppsd_required': ppsd_required,
                'ultrasonic_required': ultrasonic_required
            },
            'user_role': get_user_role(request.user)
        })




# Сокращенные сериализаторы для API (можно вынести в отдельный файл)
from rest_framework import serializers
from .models import QCInspection


class QCInspectionListSerializer(serializers.ModelSerializer):
    """Сериализатор для списка инспекций"""
    
    material_grade = serializers.CharField(source='material_receipt.material.material_grade', read_only=True)
    material_supplier = serializers.CharField(source='material_receipt.material.supplier', read_only=True)
    inspector_name = serializers.CharField(source='inspector.get_full_name', read_only=True)
    completion_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = QCInspection
        fields = [
            'id', 'material_grade', 'material_supplier', 'inspector_name',
            'inspection_date', 'status', 'requires_ppsd', 'requires_ultrasonic',
            'completion_percentage', 'created_at'
        ]
    
    def get_completion_percentage(self, obj):
        return obj.get_completion_percentage()




# Регистрируем ViewSets в __init__.py или urls.py
QCInspectionViewSet.serializer_class = QCInspectionListSerializer


class QCChecklistViewSet(viewsets.ModelViewSet):
    """ViewSet для управления чек-листами ОТК"""
    
    queryset = QCChecklist.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'material_grade']
    search_fields = ['name', 'description', 'material_grade']
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['name']
    
    def get_queryset(self):
        """Фильтрация по активности"""
        queryset = super().get_queryset()
        
        # По умолчанию показываем только активные
        if self.request.query_params.get('show_all') != 'true':
            queryset = queryset.filter(is_active=True)
            
        return queryset.prefetch_related('checklist_items')


class QCInspectionResultViewSet(viewsets.ModelViewSet):
    """ViewSet для управления результатами инспекций"""
    
    queryset = QCInspectionResult.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['inspection', 'result', 'checklist_item__is_critical']
    ordering_fields = ['checklist_item__order', 'created_at']
    ordering = ['checklist_item__order']
    
    def get_queryset(self):
        """Оптимизированные запросы"""
        return super().get_queryset().select_related(
            'inspection__material_receipt__material',
            'checklist_item__checklist',
            'created_by',
            'updated_by'
        )