"""
Сериализаторы для модуля контроля качества
"""
from rest_framework import serializers
from .models import QCInspection, QCChecklist, QCChecklistItem, QCInspectionResult


class QCInspectionSerializer(serializers.ModelSerializer):
    """Основной сериализатор для инспекций ОТК"""
    
    material_info = serializers.SerializerMethodField()
    inspector_name = serializers.CharField(source='inspector.get_full_name', read_only=True)
    completion_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = QCInspection
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    
    def get_material_info(self, obj):
        material = obj.material_receipt.material
        return {
            'id': material.id,
            'grade': material.material_grade,
            'supplier': material.supplier,
            'certificate_number': material.certificate_number,
            'heat_number': material.heat_number,
        }
    
    def get_completion_percentage(self, obj):
        return obj.get_completion_percentage()


class QCChecklistItemSerializer(serializers.ModelSerializer):
    """Сериализатор для пунктов чек-листа"""
    
    class Meta:
        model = QCChecklistItem
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')


class QCChecklistSerializer(serializers.ModelSerializer):
    """Сериализатор для чек-листов"""
    
    checklist_items = QCChecklistItemSerializer(many=True, read_only=True)
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = QCChecklist
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    
    def get_items_count(self, obj):
        return obj.checklist_items.count()


class QCInspectionResultSerializer(serializers.ModelSerializer):
    """Сериализатор для результатов инспекции"""
    
    checklist_item_description = serializers.CharField(
        source='checklist_item.description', 
        read_only=True
    )
    is_critical = serializers.BooleanField(
        source='checklist_item.is_critical', 
        read_only=True
    )
    
    class Meta:
        model = QCInspectionResult
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    
    def validate(self, attrs):
        """Валидация результата"""
        if 'checklist_item' in attrs and 'result' in attrs:
            if attrs['checklist_item'].is_critical and attrs['result'] == 'na':
                raise serializers.ValidationError({
                    'result': 'Критические пункты не могут быть отмечены как "Не применимо"'
                })
        
        if attrs.get('result') == 'failed' and not attrs.get('notes'):
            raise serializers.ValidationError({
                'notes': 'При отрицательном результате примечания обязательны'
            })
        
        return attrs
