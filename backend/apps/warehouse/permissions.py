from rest_framework import permissions
from django.contrib.auth.models import User


class IsWarehouseStaff(permissions.BasePermission):
    """
    Разрешение только для персонала склада.
    Может создавать материалы и приемки.
    """
    
    def has_permission(self, request, view):
        """Проверка на уровне представления"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Администратор имеет полный доступ
        if request.user.is_superuser:
            return True
        
        # Проверяем группы пользователя
        user_groups = request.user.groups.values_list('name', flat=True)
        warehouse_groups = ['warehouse', 'warehouse_staff', 'склад']
        
        return any(group.lower() in [g.lower() for g in warehouse_groups] for group in user_groups)
    
    def has_object_permission(self, request, view, obj):
        """Проверка на уровне объекта"""
        # Базовая проверка разрешения
        if not self.has_permission(request, view):
            return False
        
        # Чтение доступно всем авторизованным пользователям склада
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Изменение/удаление только для создателя или администратора
        if hasattr(obj, 'created_by'):
            return obj.created_by == request.user or request.user.is_superuser
        
        return request.user.is_superuser


class IsQCInspector(permissions.BasePermission):
    """
    Разрешение для инспекторов ОТК.
    Может просматривать материалы и управлять проверками качества.
    """
    
    def has_permission(self, request, view):
        """Проверка на уровне представления"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Администратор имеет полный доступ
        if request.user.is_superuser:
            return True
        
        # Проверяем группы пользователя
        user_groups = request.user.groups.values_list('name', flat=True)
        qc_groups = ['qc', 'quality_control', 'отк', 'inspector']
        
        return any(group.lower() in [g.lower() for g in qc_groups] for group in user_groups)
    
    def has_object_permission(self, request, view, obj):
        """Проверка на уровне объекта"""
        if not self.has_permission(request, view):
            return False
        
        # ОТК может читать все материалы и приемки
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Может изменять только связанные с ОТК объекты
        # (например, статус приемки, результаты проверок)
        return request.user.is_superuser


class IsLabTechnician(permissions.BasePermission):
    """
    Разрешение для лаборантов.
    Может просматривать материалы и управлять лабораторными испытаниями.
    """
    
    def has_permission(self, request, view):
        """Проверка на уровне представления"""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Администратор имеет полный доступ
        if request.user.is_superuser:
            return True
        
        # Проверяем группы пользователя
        user_groups = request.user.groups.values_list('name', flat=True)
        lab_groups = ['lab', 'laboratory', 'лаборатория', 'technician', 'chemist']
        
        return any(group.lower() in [g.lower() for g in lab_groups] for group in user_groups)
    
    def has_object_permission(self, request, view, obj):
        """Проверка на уровне объекта"""
        if not self.has_permission(request, view):
            return False
        
        # Лаборанты могут читать материалы и сертификаты
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Могут изменять только лабораторные данные
        return request.user.is_superuser


class IsWarehouseOrReadOnly(permissions.BasePermission):
    """
    Комбинированное разрешение: склад может изменять, остальные только читать.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Чтение доступно всем авторизованным
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Изменение только для склада
        return IsWarehouseStaff().has_permission(request, view)
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Чтение доступно всем авторизованным
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Изменение только для склада
        return IsWarehouseStaff().has_object_permission(request, view, obj)


class IsOwnerOrWarehouseStaff(permissions.BasePermission):
    """
    Разрешение для владельца объекта или персонала склада.
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Администратор имеет полный доступ
        if request.user.is_superuser:
            return True
        
        # Владелец объекта
        if hasattr(obj, 'created_by') and obj.created_by == request.user:
            return True
        
        # Персонал склада
        return IsWarehouseStaff().has_permission(request, view)


class CanCreateMaterials(permissions.BasePermission):
    """
    Разрешение на создание материалов - только склад.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Только для действий создания
        if view.action != 'create':
            return True
        
        return (
            request.user.is_superuser or 
            IsWarehouseStaff().has_permission(request, view)
        )


class CanModifyReceipts(permissions.BasePermission):
    """
    Разрешение на изменение приемок - склад и ОТК.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Чтение доступно всем
        if request.method in permissions.SAFE_METHODS:
            return True
        
        return (
            request.user.is_superuser or
            IsWarehouseStaff().has_permission(request, view) or
            IsQCInspector().has_permission(request, view)
        )
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Чтение доступно всем авторизованным
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Администратор
        if request.user.is_superuser:
            return True
        
        # Создатель приемки (склад)
        if hasattr(obj, 'created_by') and obj.created_by == request.user:
            return True
        
        # ОТК может изменять статус
        if IsQCInspector().has_permission(request, view):
            return True
        
        return False


class RoleBasedPermission(permissions.BasePermission):
    """
    Универсальное разрешение на основе ролей.
    Настраивается через атрибуты ViewSet.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Администратор имеет полный доступ
        if request.user.is_superuser:
            return True
        
        # Получаем требуемые роли из ViewSet
        required_roles = getattr(view, 'required_roles', {})
        
        # Если роли не заданы, разрешаем всем авторизованным
        if not required_roles:
            return True
        
        # Проверяем роли для конкретного действия
        action = view.action
        if action in required_roles:
            return self._check_user_roles(request.user, required_roles[action])
        
        # Проверяем роли по методу HTTP
        method = request.method.lower()
        if method in required_roles:
            return self._check_user_roles(request.user, required_roles[method])
        
        # По умолчанию проверяем роли для 'default'
        if 'default' in required_roles:
            return self._check_user_roles(request.user, required_roles['default'])
        
        return True
    
    def _check_user_roles(self, user, allowed_roles):
        """Проверка ролей пользователя"""
        if isinstance(allowed_roles, str):
            allowed_roles = [allowed_roles]
        
        user_groups = user.groups.values_list('name', flat=True)
        
        for role in allowed_roles:
            if role.lower() in [group.lower() for group in user_groups]:
                return True
        
        return False


# Удобные функции для проверки ролей

def is_warehouse_staff(user):
    """Проверка, является ли пользователь персоналом склада"""
    if not user or not user.is_authenticated:
        return False
    
    if user.is_superuser:
        return True
    
    user_groups = user.groups.values_list('name', flat=True)
    warehouse_groups = ['warehouse', 'warehouse_staff', 'склад']
    
    return any(group.lower() in [g.lower() for g in warehouse_groups] for group in user_groups)


def is_qc_inspector(user):
    """Проверка, является ли пользователь инспектором ОТК"""
    if not user or not user.is_authenticated:
        return False
    
    if user.is_superuser:
        return True
    
    user_groups = user.groups.values_list('name', flat=True)
    qc_groups = ['qc', 'quality_control', 'отк', 'inspector']
    
    return any(group.lower() in [g.lower() for g in qc_groups] for group in user_groups)


def is_lab_technician(user):
    """Проверка, является ли пользователь лаборантом"""
    if not user or not user.is_authenticated:
        return False
    
    if user.is_superuser:
        return True
    
    user_groups = user.groups.values_list('name', flat=True)
    lab_groups = ['lab', 'laboratory', 'лаборатория', 'technician', 'chemist']
    
    return any(group.lower() in [g.lower() for g in lab_groups] for group in user_groups)


def get_user_role(user):
    """Получение основной роли пользователя"""
    if not user or not user.is_authenticated:
        return None
    
    if user.is_superuser:
        return 'admin'
    
    if is_warehouse_staff(user):
        return 'warehouse'
    
    if is_qc_inspector(user):
        return 'qc'
    
    if is_lab_technician(user):
        return 'lab'
    
    return 'user'


# Миксин для ViewSets с проверкой ролей

class RoleBasedViewSetMixin:
    """
    Миксин для ViewSets с автоматической проверкой ролей.
    Определите required_roles в вашем ViewSet.
    """
    
    required_roles = {}
    
    def get_permissions(self):
        """Автоматическое добавление RoleBasedPermission"""
        permission_classes = list(self.permission_classes)
        
        if hasattr(self, 'required_roles') and self.required_roles:
            permission_classes.append(RoleBasedPermission)
        
        return [permission() for permission in permission_classes]
    
    def check_permissions(self, request):
        """Расширенная проверка разрешений с логированием"""
        try:
            super().check_permissions(request)
        except Exception as e:
            # Можно добавить логирование неудачных попыток доступа
            user_role = get_user_role(request.user)
            print(f"Access denied for user {request.user.username} (role: {user_role}) to {self.__class__.__name__}.{self.action}")
            raise 