"""
BPMN workflow flows для системы управления качеством металлов
"""
from viewflow import Flow, this
from viewflow.contrib import celery
from viewflow.views import CreateProcessView, UpdateProcessView
from django.contrib.auth.models import User, Group
from django.utils import timezone
from datetime import timedelta

from .models import MaterialInspectionProcess, WorkflowTaskLog
from .handlers import (
    MaterialReceiptHandler, QCInspectionHandler, 
    LaboratoryTestHandler, ProductionPrepHandler,
    ProcessCompletionHandler
)
from .permissions import (
    WarehousePermission, QCPermission, LabPermission, 
    ProductionPermission, ProcessOwnerPermission
)


class MaterialInspectionFlow(Flow):
    """
    BPMN процесс инспекции материала
    
    Workflow:
    1. Start: Material receipt
    2. Task: QC inspection  
    3. Gateway: Needs PPSD?
    4. Task: Lab testing (if needed)
    5. Gateway: Needs ultrasonic?
    6. Task: Ultrasonic testing (if needed)
    7. Task: Production prep
    8. End: Material approved
    """
    
    process_class = MaterialInspectionProcess
    
    # ===== START NODES =====
    
    start = (
        Flow.Start(CreateProcessView)
        .Permission(auto_create=True)  # Автоматическое создание
        .Next(this.material_received)
    )
    
    # ===== TASK NODES =====
    
    material_received = (
        Flow.View(MaterialReceiptHandler)
        .Permission(WarehousePermission)
        .Assign(this.auto_assign_warehouse)
        .Next(this.qc_inspection_required)
    )
    
    qc_inspection_required = (
        Flow.If(this.check_qc_required)
        .Then(this.qc_inspection)
        .Else(this.production_prep)
    )
    
    qc_inspection = (
        Flow.View(QCInspectionHandler)
        .Permission(QCPermission)
        .Assign(this.auto_assign_qc)
        .Next(this.ppsd_required)
    )
    
    # ===== GATEWAY NODES =====
    
    ppsd_required = (
        Flow.If(this.check_ppsd_required)
        .Then(this.ppsd_testing)
        .Else(this.ultrasonic_required)
    )
    
    ppsd_testing = (
        Flow.View(LaboratoryTestHandler)
        .Permission(LabPermission)
        .Assign(this.auto_assign_lab)
        .Next(this.ultrasonic_required)
    )
    
    ultrasonic_required = (
        Flow.If(this.check_ultrasonic_required)
        .Then(this.ultrasonic_testing)
        .Else(this.production_prep)
    )
    
    ultrasonic_testing = (
        Flow.View(LaboratoryTestHandler)
        .Permission(LabPermission)
        .Assign(this.auto_assign_lab)
        .Next(this.production_prep)
    )
    
    production_prep = (
        Flow.View(ProductionPrepHandler)
        .Permission(ProductionPermission)
        .Assign(this.auto_assign_production)
        .Next(this.approve_material)
    )
    
    # ===== END NODES =====
    
    approve_material = (
        Flow.View(ProcessCompletionHandler)
        .Permission(ProcessOwnerPermission)
        .Assign(this.auto_assign_manager)
        .Next(this.end)
    )
    
    end = Flow.End()
    
    # ===== BUSINESS LOGIC METHODS =====
    
    def check_qc_required(self, activation):
        """Проверка необходимости QC инспекции"""
        process = activation.process
        material = process.material_receipt.material
        
        # QC всегда требуется для новых материалов
        # В будущем можно добавить логику исключений
        WorkflowTaskLog.log_task_action(
            process=process,
            task_name="QC Required Check",
            task_id="qc_required_check",
            action="completed",
            performer=activation.task.owner,
            comment=f"QC инспекция требуется для материала {material.material_grade}"
        )
        
        return True
    
    def check_ppsd_required(self, activation):
        """Проверка необходимости ППСД"""
        process = activation.process
        
        # Импортируем сервис для проверки
        from apps.warehouse.services import MaterialInspectionService
        
        material = process.material_receipt.material
        
        ppsd_response = MaterialInspectionService.check_ppsd_requirement(
            material.material_grade, material.size
        )
        
        requires_ppsd = ppsd_response.success and ppsd_response.data.get('requires_ppsd', False)
        
        # Обновляем процесс
        process.requires_ppsd = requires_ppsd
        process.save()
        
        # Логируем решение
        WorkflowTaskLog.log_task_action(
            process=process,
            task_name="PPSD Required Check",
            task_id="ppsd_required_check",
            action="completed",
            performer=activation.task.owner,
            comment=f"ППСД {'требуется' if requires_ppsd else 'не требуется'} для {material.material_grade}",
            metadata={'ppsd_response': ppsd_response.to_dict()}
        )
        
        return requires_ppsd
    
    def check_ultrasonic_required(self, activation):
        """Проверка необходимости УЗК"""
        process = activation.process
        
        # Импортируем сервис для проверки
        from apps.warehouse.services import MaterialInspectionService
        
        material = process.material_receipt.material
        
        ultrasonic_response = MaterialInspectionService.check_ultrasonic_requirement(
            material.material_grade, material.size
        )
        
        requires_ultrasonic = (
            ultrasonic_response.success and 
            ultrasonic_response.data.get('requires_ultrasonic', False)
        )
        
        # Обновляем процесс
        process.requires_ultrasonic = requires_ultrasonic
        process.save()
        
        # Логируем решение
        WorkflowTaskLog.log_task_action(
            process=process,
            task_name="Ultrasonic Required Check", 
            task_id="ultrasonic_required_check",
            action="completed",
            performer=activation.task.owner,
            comment=f"УЗК {'требуется' if requires_ultrasonic else 'не требуется'} для {material.material_grade}",
            metadata={'ultrasonic_response': ultrasonic_response.to_dict()}
        )
        
        return requires_ultrasonic
    
    # ===== AUTO-ASSIGNMENT METHODS =====
    
    def auto_assign_warehouse(self, activation):
        """Автоматическое назначение на склад"""
        warehouse_groups = ['warehouse', 'warehouse_staff', 'склад']
        return self._auto_assign_by_groups(activation, warehouse_groups, 'warehouse')
    
    def auto_assign_qc(self, activation):
        """Автоматическое назначение на ОТК"""
        qc_groups = ['qc', 'quality_control', 'отк', 'inspector']
        return self._auto_assign_by_groups(activation, qc_groups, 'qc')
    
    def auto_assign_lab(self, activation):
        """Автоматическое назначение в лабораторию"""
        lab_groups = ['lab', 'laboratory', 'лаборатория', 'technician', 'chemist']
        return self._auto_assign_by_groups(activation, lab_groups, 'lab')
    
    def auto_assign_production(self, activation):
        """Автоматическое назначение на производство"""
        production_groups = ['production', 'производство', 'operator']
        return self._auto_assign_by_groups(activation, production_groups, 'production')
    
    def auto_assign_manager(self, activation):
        """Автоматическое назначение менеджеру процесса"""
        process = activation.process
        
        # Назначаем на инициатора процесса или админа
        if process.initiator and process.initiator.is_active:
            assignee = process.initiator
        else:
            # Резервный вариант - первый активный админ
            assignee = User.objects.filter(
                is_active=True, is_staff=True
            ).first()
        
        if assignee:
            activation.assign(assignee)
            
            # Обновляем текущего исполнителя в процессе
            process.current_assignee = assignee
            process.save()
            
            # Логируем назначение
            WorkflowTaskLog.log_task_action(
                process=process,
                task_name="Process Completion",
                task_id="process_completion",
                action="assigned",
                performer=assignee,
                assignee=assignee,
                comment=f"Процесс назначен менеджеру {assignee.username}"
            )
        
        return assignee
    
    def _auto_assign_by_groups(self, activation, group_names, role_name):
        """Общий метод автоматического назначения по группам"""
        process = activation.process
        
        # Ищем группы по именам
        groups = Group.objects.filter(name__in=group_names)
        
        if not groups.exists():
            # Если групп нет, назначаем на инициатора
            assignee = process.initiator
        else:
            # Ищем активных пользователей в группах
            assignee = User.objects.filter(
                groups__in=groups,
                is_active=True
            ).order_by('?').first()  # Случайный выбор для балансировки нагрузки
            
            if not assignee:
                # Если в группах нет активных пользователей
                assignee = process.initiator
        
        if assignee:
            activation.assign(assignee)
            
            # Обновляем текущего исполнителя в процессе
            process.current_assignee = assignee
            process.save()
            
            # Логируем назначение
            WorkflowTaskLog.log_task_action(
                process=process,
                task_name=f"{role_name.title()} Task",
                task_id=f"{role_name}_task",
                action="assigned",
                performer=assignee,
                assignee=assignee,
                comment=f"Задача назначена пользователю {assignee.username} из роли {role_name}"
            )
        
        return assignee
    
    # ===== SLA METHODS =====
    
    def calculate_task_sla(self, task_type: str, priority: str = 'normal'):
        """Вычисляет SLA для конкретной задачи"""
        
        # Базовые SLA для разных типов задач (в часах)
        base_sla = {
            'material_received': 2,    # 2 часа на оформление приемки
            'qc_inspection': 24,       # 1 день на ОТК
            'ppsd_testing': 72,        # 3 дня на ППСД
            'ultrasonic_testing': 48,  # 2 дня на УЗК
            'production_prep': 24,     # 1 день на подготовку к производству
            'approve_material': 8,     # 8 часов на утверждение
        }
        
        # Корректировка по приоритету
        priority_multipliers = {
            'urgent': 0.5,   # Ускоряем в 2 раза
            'high': 0.75,    # Ускоряем в 1.33 раза
            'normal': 1.0,   # Базовое время
            'low': 1.5,      # Замедляем в 1.5 раза
        }
        
        hours = base_sla.get(task_type, 24)  # По умолчанию 1 день
        multiplier = priority_multipliers.get(priority, 1.0)
        
        return int(hours * multiplier)
    
    def setup_task_sla(self, activation, task_type: str):
        """Настройка SLA для задачи"""
        process = activation.process
        hours = self.calculate_task_sla(task_type, process.priority)
        
        # Устанавливаем deadline для задачи
        deadline = timezone.now() + timedelta(hours=hours)
        activation.task.due_date = deadline
        activation.task.save()
        
        # Логируем установку SLA
        WorkflowTaskLog.log_task_action(
            process=process,
            task_name=task_type,
            task_id=f"{task_type}_sla",
            action="created",
            performer=activation.task.owner,
            comment=f"Установлен SLA: {hours} часов (до {deadline.strftime('%d.%m.%Y %H:%M')})",
            metadata={
                'sla_hours': hours,
                'deadline': deadline.isoformat(),
                'priority': process.priority
            }
        )


# Регистрируем flow
flow = MaterialInspectionFlow()


class ExpressInspectionFlow(MaterialInspectionFlow):
    """
    Экспресс-процесс для срочных материалов
    Пропускает некоторые этапы для ускорения
    """
    
    # Переопределяем проверки для ускорения процесса
    def check_ppsd_required(self, activation):
        """Для экспресс-процесса ППСД не требуется"""
        process = activation.process
        process.requires_ppsd = False
        process.save()
        
        WorkflowTaskLog.log_task_action(
            process=process,
            task_name="Express PPSD Check",
            task_id="express_ppsd_check",
            action="completed",
            performer=activation.task.owner,
            comment="ППСД пропущено в экспресс-режиме"
        )
        
        return False
    
    def calculate_task_sla(self, task_type: str, priority: str = 'urgent'):
        """Ускоренные SLA для экспресс-процесса"""
        # Все задачи выполняются в 2 раза быстрее
        base_hours = super().calculate_task_sla(task_type, priority)
        return max(1, base_hours // 2)  # Минимум 1 час


# Регистрируем экспресс-flow
express_flow = ExpressInspectionFlow()