"""
Обработчики для узлов BPMN workflow
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.urls import reverse
from django.http import JsonResponse
from django.utils import timezone
from viewflow.views import FlowViewMixin, UpdateProcessView
from django.views.generic import UpdateView, DetailView

from .models import MaterialInspectionProcess, WorkflowTaskLog, WorkflowSLAViolation
from apps.warehouse.models import MaterialReceipt
from apps.quality.models import QCInspection
from apps.laboratory.models import LabTestRequest
from apps.warehouse.services import MaterialInspectionService, NotificationService


@method_decorator(login_required, name='dispatch')
class MaterialReceiptHandler(FlowViewMixin, UpdateProcessView):
    """
    Обработчик узла поступления материала
    """
    
    template_name = 'workflow/material_receipt.html'
    model = MaterialInspectionProcess
    fields = ['priority', 'comments']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        process = self.object
        
        context.update({
            'material': process.material_receipt.material,
            'receipt': process.material_receipt,
            'task_name': 'Обработка поступления материала',
            'task_description': 'Проверка документов и оформление приемки материала',
            'sla_deadline': process.sla_deadline,
            'sla_status': process.get_sla_status(),
            'time_remaining': process.get_time_remaining(),
        })
        
        return context
    
    def form_valid(self, form):
        process = form.instance
        
        # Логируем начало задачи
        WorkflowTaskLog.log_task_action(
            process=process,
            task_name="Material Receipt Processing",
            task_id="material_receipt",
            action="started",
            performer=self.request.user,
            comment="Начата обработка поступления материала"
        )
        
        # Выполняем базовую логику
        response = super().form_valid(form)
        
        # Логируем завершение
        WorkflowTaskLog.log_task_action(
            process=process,
            task_name="Material Receipt Processing",
            task_id="material_receipt",
            action="completed",
            performer=self.request.user,
            comment=f"Материал принят, приоритет: {process.get_priority_display()}"
        )
        
        messages.success(
            self.request, 
            f"Материал {process.material_receipt.material.material_grade} успешно принят"
        )
        
        return response


@method_decorator(login_required, name='dispatch')
class QCInspectionHandler(FlowViewMixin, UpdateProcessView):
    """
    Обработчик узла инспекции ОТК
    """
    
    template_name = 'workflow/qc_inspection.html'
    model = MaterialInspectionProcess
    fields = ['comments']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        process = self.object
        material = process.material_receipt.material
        
        # Получаем или создаем инспекцию ОТК
        qc_inspection, created = QCInspection.objects.get_or_create(
            material_receipt=process.material_receipt,
            defaults={
                'inspector': self.request.user,
                'status': 'draft',
                'created_by': self.request.user,
                'updated_by': self.request.user,
            }
        )
        
        # Автоматически определяем требования
        if created:
            ppsd_response = MaterialInspectionService.check_ppsd_requirement(
                material.material_grade, material.size
            )
            ultrasonic_response = MaterialInspectionService.check_ultrasonic_requirement(
                material.material_grade, material.size
            )
            
            qc_inspection.requires_ppsd = (
                ppsd_response.success and ppsd_response.data.get('requires_ppsd', False)
            )
            qc_inspection.requires_ultrasonic = (
                ultrasonic_response.success and ultrasonic_response.data.get('requires_ultrasonic', False)
            )
            qc_inspection.save()
        
        context.update({
            'material': material,
            'receipt': process.material_receipt,
            'qc_inspection': qc_inspection,
            'task_name': 'Инспекция ОТК',
            'task_description': 'Контроль качества поступившего материала',
            'inspection_results': qc_inspection.inspection_results.all(),
            'completion_percentage': qc_inspection.get_completion_percentage(),
            'critical_failures': qc_inspection.get_critical_failures(),
            'can_complete': qc_inspection.can_complete(),
        })
        
        return context
    
    def form_valid(self, form):
        process = form.instance
        
        # Получаем инспекцию
        qc_inspection = QCInspection.objects.get(material_receipt=process.material_receipt)
        
        # Проверяем готовность к завершению
        if not qc_inspection.can_complete():
            messages.error(
                self.request,
                'Нельзя завершить инспекцию с невыполненными критическими пунктами'
            )
            return self.form_invalid(form)
        
        # Завершаем инспекцию через service layer
        transition_response = MaterialInspectionService.transition_status(
            inspection_id=qc_inspection.id,
            new_status='completed',
            user=self.request.user,
            comment=form.cleaned_data.get('comments', '')
        )
        
        if not transition_response.success:
            messages.error(self.request, f"Ошибка завершения инспекции: {transition_response.error}")
            return self.form_invalid(form)
        
        # Обновляем процесс
        process.requires_ppsd = qc_inspection.requires_ppsd
        process.requires_ultrasonic = qc_inspection.requires_ultrasonic
        process.save()
        
        # Логируем завершение
        WorkflowTaskLog.log_task_action(
            process=process,
            task_name="QC Inspection",
            task_id="qc_inspection",
            action="completed",
            performer=self.request.user,
            comment=f"Инспекция завершена, ППСД: {process.requires_ppsd}, УЗК: {process.requires_ultrasonic}",
            metadata={
                'qc_inspection_id': qc_inspection.id,
                'completion_percentage': qc_inspection.get_completion_percentage(),
                'requires_ppsd': process.requires_ppsd,
                'requires_ultrasonic': process.requires_ultrasonic,
            }
        )
        
        # Отправляем уведомления
        NotificationService.send_status_change_notification(
            inspection_id=qc_inspection.id,
            old_status='in_progress',
            new_status='completed',
            user=self.request.user
        )
        
        messages.success(self.request, "Инспекция ОТК успешно завершена")
        
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch') 
class LaboratoryTestHandler(FlowViewMixin, UpdateProcessView):
    """
    Обработчик узла лабораторных испытаний
    """
    
    template_name = 'workflow/laboratory_test.html'
    model = MaterialInspectionProcess
    fields = ['comments']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        process = self.object
        
        # Определяем тип испытания из URL или из процесса
        test_type = self.request.GET.get('test_type', 'ppsd')
        
        if test_type == 'ppsd':
            task_name = 'Испытания ППСД'
            task_description = 'Химический анализ и механические испытания'
            required_tests = ['chemical_analysis', 'mechanical_properties']
        else:  # ultrasonic
            task_name = 'Ультразвуковой контроль'
            task_description = 'Ультразвуковая дефектоскопия'
            required_tests = ['ultrasonic']
        
        # Получаем существующие заявки или создаем новые
        test_requests = []
        for test_type_code in required_tests:
            test_request, created = LabTestRequest.objects.get_or_create(
                material_receipt=process.material_receipt,
                test_type=test_type_code,
                defaults={
                    'requested_by': self.request.user,
                    'status': 'pending',
                    'priority': 'normal',
                    'internal_testing': True,
                    'created_by': self.request.user,
                    'updated_by': self.request.user,
                }
            )
            test_requests.append(test_request)
        
        context.update({
            'material': process.material_receipt.material,
            'receipt': process.material_receipt,
            'test_requests': test_requests,
            'task_name': task_name,
            'task_description': task_description,
            'test_type': test_type,
        })
        
        return context
    
    def form_valid(self, form):
        process = form.instance
        test_type = self.request.GET.get('test_type', 'ppsd')
        
        # Получаем заявки на испытания
        if test_type == 'ppsd':
            test_types = ['chemical_analysis', 'mechanical_properties']
        else:
            test_types = ['ultrasonic']
        
        test_requests = LabTestRequest.objects.filter(
            material_receipt=process.material_receipt,
            test_type__in=test_types
        )
        
        # Проверяем завершенность всех испытаний
        incomplete_tests = test_requests.exclude(status='completed')
        if incomplete_tests.exists():
            incomplete_names = [req.get_test_type_display() for req in incomplete_tests]
            messages.error(
                self.request,
                f"Необходимо завершить испытания: {', '.join(incomplete_names)}"
            )
            return self.form_invalid(form)
        
        # Логируем завершение
        WorkflowTaskLog.log_task_action(
            process=process,
            task_name=f"Laboratory Test - {test_type.upper()}",
            task_id=f"lab_test_{test_type}",
            action="completed",
            performer=self.request.user,
            comment=f"Завершены лабораторные испытания: {test_type}",
            metadata={
                'test_requests': [req.id for req in test_requests],
                'test_type': test_type,
                'completed_tests': len(test_requests),
            }
        )
        
        messages.success(
            self.request, 
            f"Лабораторные испытания ({test_type.upper()}) успешно завершены"
        )
        
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class ProductionPrepHandler(FlowViewMixin, UpdateProcessView):
    """
    Обработчик узла подготовки к производству
    """
    
    template_name = 'workflow/production_prep.html'
    model = MaterialInspectionProcess
    fields = ['comments']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        process = self.object
        material = process.material_receipt.material
        
        # Информация о материале для производства
        context.update({
            'material': material,
            'receipt': process.material_receipt,
            'task_name': 'Подготовка к производству',
            'task_description': 'Подготовка материала для передачи в производство',
            'material_location': material.location,
            'available_quantity': material.quantity,
            'qr_code_url': material.qr_code.url if material.qr_code else None,
            'has_certificate': hasattr(material, 'certificate'),
        })
        
        return context
    
    def form_valid(self, form):
        process = form.instance
        material = process.material_receipt.material
        
        # Обновляем статус материала и приемки
        process.material_receipt.status = 'approved'
        process.material_receipt.save()
        
        # Логируем подготовку к производству
        WorkflowTaskLog.log_task_action(
            process=process,
            task_name="Production Preparation",
            task_id="production_prep",
            action="completed",
            performer=self.request.user,
            comment=f"Материал {material.material_grade} подготовлен к производству",
            metadata={
                'material_id': material.id,
                'material_grade': material.material_grade,
                'quantity': str(material.quantity),
                'location': material.location,
            }
        )
        
        messages.success(
            self.request,
            f"Материал {material.material_grade} готов к передаче в производство"
        )
        
        return super().form_valid(form)


@method_decorator(login_required, name='dispatch')
class ProcessCompletionHandler(FlowViewMixin, UpdateProcessView):
    """
    Обработчик узла завершения процесса
    """
    
    template_name = 'workflow/process_completion.html'
    model = MaterialInspectionProcess
    fields = ['comments']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        process = self.object
        
        # Сбор статистики процесса
        total_duration = None
        if process.started_at and process.completed_at:
            total_duration = process.completed_at - process.started_at
        
        # Получаем все логи процесса
        task_logs = process.task_logs.order_by('timestamp')
        
        # Статистика по задачам
        task_stats = {}
        for log in task_logs:
            task_name = log.task_name
            if task_name not in task_stats:
                task_stats[task_name] = {
                    'actions': [],
                    'duration': None,
                    'performer': None,
                }
            
            task_stats[task_name]['actions'].append(log)
            if log.action == 'completed':
                task_stats[task_name]['performer'] = log.performer
                if log.duration_seconds:
                    task_stats[task_name]['duration'] = log.duration_seconds
        
        context.update({
            'material': process.material_receipt.material,
            'receipt': process.material_receipt,
            'task_name': 'Завершение процесса',
            'task_description': 'Финальное утверждение материала',
            'total_duration': total_duration,
            'task_stats': task_stats,
            'task_logs': task_logs,
            'sla_violations': process.sla_violations.all(),
            'progress_percentage': process.progress_percentage,
            'is_overdue': process.is_overdue(),
            'sla_status': process.get_sla_status(),
        })
        
        return context
    
    def form_valid(self, form):
        process = form.instance
        
        # Завершаем процесс
        process.complete(self.request.user)
        
        # Логируем завершение всего процесса
        WorkflowTaskLog.log_task_action(
            process=process,
            task_name="Process Completion",
            task_id="process_completion",
            action="completed",
            performer=self.request.user,
            comment=f"Процесс инспекции материала завершен успешно",
            metadata={
                'material_grade': process.material_receipt.material.material_grade,
                'total_duration_seconds': (
                    (process.completed_at - process.started_at).total_seconds()
                    if process.completed_at and process.started_at else None
                ),
                'sla_status': process.get_sla_status(),
                'was_overdue': process.is_overdue(),
                'progress_percentage': str(process.progress_percentage),
            }
        )
        
        # Уведомления о завершении
        NotificationService.send_status_change_notification(
            inspection_id=None,  # Это завершение всего процесса
            old_status='active',
            new_status='completed', 
            user=self.request.user
        )
        
        messages.success(
            self.request,
            f"Процесс инспекции материала {process.material_receipt.material.material_grade} завершен успешно!"
        )
        
        return super().form_valid(form)


# Дополнительные представления для работы с процессом

class ProcessDetailView(DetailView):
    """Детальный просмотр процесса"""
    
    model = MaterialInspectionProcess
    template_name = 'workflow/process_detail.html'
    context_object_name = 'process'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        process = self.object
        
        context.update({
            'material': process.material_receipt.material,
            'receipt': process.material_receipt,
            'task_logs': process.task_logs.order_by('timestamp'),
            'sla_violations': process.sla_violations.all(),
            'active_tasks': process.task_set.filter(status='NEW'),
            'completed_tasks': process.task_set.filter(status='DONE'),
        })
        
        return context


def escalate_process(request, process_id):
    """Эскалация процесса"""
    
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    process = get_object_or_404(MaterialInspectionProcess, id=process_id)
    reason = request.POST.get('reason', 'Manual escalation')
    
    # Выполняем эскалацию
    process.escalate(reason, request.user)
    
    # Создаем нарушение SLA если его еще нет
    if not process.sla_violations.filter(status='active').exists():
        WorkflowSLAViolation.objects.create(
            process=process,
            violation_type='warning',
            message=f"Процесс эскалирован: {reason}",
            created_by=request.user,
            updated_by=request.user
        )
    
    # Логируем эскалацию
    WorkflowTaskLog.log_task_action(
        process=process,
        task_name="Process Escalation",
        task_id="escalation",
        action="escalated",
        performer=request.user,
        comment=f"Процесс эскалирован: {reason}"
    )
    
    messages.success(request, f"Процесс #{process.id} эскалирован")
    
    return redirect('workflow:process_detail', pk=process.id)