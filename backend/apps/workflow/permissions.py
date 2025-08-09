"""
Permissions для BPMN workflow
"""
from django.contrib.auth.models import User, Group
from viewflow.contrib.auth import AuthViewMixin
from apps.warehouse.permissions import (
    is_warehouse_staff, is_qc_inspector, is_lab_technician, get_user_role
)


class WorkflowPermissionMixin:
    """Базовый миксин для проверки прав в workflow"""
    
    def has_object_permission(self, user, obj=None):
        """Базовая проверка прав на объект"""
        if not user.is_authenticated:
            return False
        
        # Суперпользователи всегда имеют доступ
        if user.is_superuser:
            return True
        
        return True
    
    def has_perm(self, user):
        """Общая проверка прав пользователя"""
        return self.has_object_permission(user)


class WarehousePermission(WorkflowPermissionMixin):
    """Права доступа для складских операций"""
    
    def has_object_permission(self, user, obj=None):
        if not super().has_object_permission(user, obj):
            return False
        
        # Проверяем принадлежность к складским группам
        return is_warehouse_staff(user)


class QCPermission(WorkflowPermissionMixin):
    """Права доступа для операций ОТК"""
    
    def has_object_permission(self, user, obj=None):
        if not super().has_object_permission(user, obj):
            return False
        
        # Проверяем принадлежность к группам ОТК
        return is_qc_inspector(user)


class LabPermission(WorkflowPermissionMixin):
    """Права доступа для лабораторных операций"""
    
    def has_object_permission(self, user, obj=None):
        if not super().has_object_permission(user, obj):
            return False
        
        # Проверяем принадлежность к лабораторным группам
        return is_lab_technician(user)


class ProductionPermission(WorkflowPermissionMixin):
    """Права доступа для производственных операций"""
    
    def has_object_permission(self, user, obj=None):
        if not super().has_object_permission(user, obj):
            return False
        
        # Проверяем принадлежность к производственным группам
        production_groups = ['production', 'производство', 'operator']
        user_groups = user.groups.values_list('name', flat=True)
        
        return any(
            group_name.lower() in [g.lower() for g in production_groups]
            for group_name in user_groups
        )


class ProcessOwnerPermission(WorkflowPermissionMixin):
    """Права доступа для владельца процесса"""
    
    def has_object_permission(self, user, obj=None):
        if not super().has_object_permission(user, obj):
            return False
        
        # Владелец процесса, менеджеры или администраторы
        if obj and hasattr(obj, 'process'):
            process = obj.process
            
            # Инициатор процесса
            if process.initiator == user:
                return True
            
            # Текущий исполнитель
            if process.current_assignee == user:
                return True
        
        # Менеджеры и администраторы
        return user.is_staff or user.groups.filter(
            name__in=['manager', 'менеджер', 'supervisor']
        ).exists()


class FlexibleWorkflowPermission(WorkflowPermissionMixin):
    """Гибкие права доступа с возможностью настройки"""
    
    def __init__(self, required_roles=None, allow_process_owner=True, 
                 allow_staff=True, custom_check=None):
        self.required_roles = required_roles or []
        self.allow_process_owner = allow_process_owner
        self.allow_staff = allow_staff
        self.custom_check = custom_check
    
    def has_object_permission(self, user, obj=None):
        if not super().has_object_permission(user, obj):
            return False
        
        # Пользовательская проверка
        if self.custom_check and callable(self.custom_check):
            return self.custom_check(user, obj)
        
        # Проверка по ролям
        if self.required_roles:
            user_role = get_user_role(user)
            if user_role not in self.required_roles:
                return False
        
        # Владелец процесса
        if self.allow_process_owner and obj and hasattr(obj, 'process'):
            process = obj.process
            if process.initiator == user or process.current_assignee == user:
                return True
        
        # Персонал
        if self.allow_staff and user.is_staff:
            return True
        
        return True


# Предопределенные разрешения для разных ролей

class WarehouseStaffOnly(FlexibleWorkflowPermission):
    """Только складской персонал"""
    
    def __init__(self):
        super().__init__(
            required_roles=['warehouse', 'admin'],
            allow_process_owner=False,
            allow_staff=True
        )


class QCInspectorOnly(FlexibleWorkflowPermission):
    """Только инспекторы ОТК"""
    
    def __init__(self):
        super().__init__(
            required_roles=['qc', 'admin'],
            allow_process_owner=False,
            allow_staff=True
        )


class LabTechnicianOnly(FlexibleWorkflowPermission):
    """Только лабораторные техники"""
    
    def __init__(self):
        super().__init__(
            required_roles=['lab', 'admin'],
            allow_process_owner=False,
            allow_staff=True
        )


class ProcessStakeholder(FlexibleWorkflowPermission):
    """Участники процесса (владелец + исполнители)"""
    
    def __init__(self):
        super().__init__(
            allow_process_owner=True,
            allow_staff=True,
            custom_check=self._check_stakeholder
        )
    
    def _check_stakeholder(self, user, obj):
        """Проверка принадлежности к участникам процесса"""
        if not obj or not hasattr(obj, 'process'):
            return True
        
        process = obj.process
        
        # Инициатор процесса
        if process.initiator == user:
            return True
        
        # Текущий исполнитель
        if process.current_assignee == user:
            return True
        
        # Любой, кто участвовал в процессе (по логам)
        if process.task_logs.filter(performer=user).exists():
            return True
        
        return False


# Функции-помощники для проверки ролей в workflow

def can_initiate_process(user):
    """Может ли пользователь инициировать процесс"""
    if not user.is_authenticated:
        return False
    
    # Складской персонал может инициировать процессы
    return is_warehouse_staff(user) or user.is_staff


def can_view_all_processes(user):
    """Может ли пользователь видеть все процессы"""
    if not user.is_authenticated:
        return False
    
    # Администраторы и менеджеры видят все процессы
    return (
        user.is_superuser or 
        user.is_staff or
        user.groups.filter(name__in=['manager', 'менеджер', 'supervisor']).exists()
    )


def can_escalate_process(user, process=None):
    """Может ли пользователь эскалировать процесс"""
    if not user.is_authenticated:
        return False
    
    # Администраторы и менеджеры могут эскалировать любые процессы
    if user.is_staff or user.groups.filter(name__in=['manager', 'менеджер']).exists():
        return True
    
    # Участники процесса могут эскалировать свои процессы
    if process:
        return (
            process.initiator == user or 
            process.current_assignee == user or
            process.task_logs.filter(performer=user).exists()
        )
    
    return False


def can_modify_sla(user):
    """Может ли пользователь изменять SLA"""
    if not user.is_authenticated:
        return False
    
    # Только администраторы и менеджеры
    return (
        user.is_superuser or
        user.groups.filter(name__in=['manager', 'менеджер', 'admin']).exists()
    )


def get_accessible_processes(user):
    """Получить процессы, доступные пользователю"""
    from .models import MaterialInspectionProcess
    
    if not user.is_authenticated:
        return MaterialInspectionProcess.objects.none()
    
    # Администраторы видят все
    if can_view_all_processes(user):
        return MaterialInspectionProcess.objects.all()
    
    # Пользователи видят только свои процессы
    return MaterialInspectionProcess.objects.filter(
        models.Q(initiator=user) |
        models.Q(current_assignee=user) |
        models.Q(task_logs__performer=user)
    ).distinct()


def get_assignable_users_for_role(role_name):
    """Получить пользователей, которых можно назначить на роль"""
    
    role_groups = {
        'warehouse': ['warehouse', 'warehouse_staff', 'склад'],
        'qc': ['qc', 'quality_control', 'отк', 'inspector'],
        'lab': ['lab', 'laboratory', 'лаборатория', 'technician', 'chemist'],
        'production': ['production', 'производство', 'operator'],
        'manager': ['manager', 'менеджер', 'supervisor'],
    }
    
    groups = role_groups.get(role_name, [])
    
    if not groups:
        return User.objects.none()
    
    return User.objects.filter(
        is_active=True,
        groups__name__in=groups
    ).distinct()


# Декораторы для проверки прав

def require_workflow_permission(permission_class):
    """Декоратор для проверки прав в workflow views"""
    
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            permission = permission_class()
            
            if not permission.has_perm(request.user):
                from django.http import HttpResponseForbidden
                return HttpResponseForbidden("У вас нет прав для выполнения этого действия")
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def require_process_permission(permission_check):
    """Декоратор для проверки прав на конкретный процесс"""
    
    def decorator(view_func):
        def wrapper(request, process_id=None, *args, **kwargs):
            if process_id:
                from django.shortcuts import get_object_or_404
                from .models import MaterialInspectionProcess
                
                process = get_object_or_404(MaterialInspectionProcess, id=process_id)
                
                if not permission_check(request.user, process):
                    from django.http import HttpResponseForbidden
                    return HttpResponseForbidden("У вас нет прав для работы с этим процессом")
            
            return view_func(request, process_id=process_id, *args, **kwargs)
        
        return wrapper
    return decorator