from rest_framework import serializers
from django.contrib.auth.models import User
from django.core.files.uploadedfile import UploadedFile
from django.conf import settings
from django.urls import reverse
from .models import Material, MaterialReceipt, Certificate
import os


class BaseAuditSerializer(serializers.ModelSerializer):
    """Базовый сериализатор с полями аудита"""
    
    created_by_username = serializers.CharField(
        source='created_by.username', 
        read_only=True
    )
    updated_by_username = serializers.CharField(
        source='updated_by.username', 
        read_only=True
    )
    created_by_full_name = serializers.SerializerMethodField()
    updated_by_full_name = serializers.SerializerMethodField()
    
    class Meta:
        fields = [
            'created_at', 'updated_at',
            'created_by_username', 'updated_by_username',
            'created_by_full_name', 'updated_by_full_name'
        ]
    
    def get_created_by_full_name(self, obj):
        """Полное имя создателя"""
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return None
    
    def get_updated_by_full_name(self, obj):
        """Полное имя последнего редактора"""
        if obj.updated_by:
            return obj.updated_by.get_full_name() or obj.updated_by.username
        return None


class UserSimpleSerializer(serializers.ModelSerializer):
    """Простой сериализатор пользователя"""
    
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'full_name']
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class CertificateSerializer(BaseAuditSerializer):
    """Сериализатор для сертификатов"""
    
    download_url = serializers.SerializerMethodField()
    file_size_mb = serializers.SerializerMethodField()
    material_grade = serializers.CharField(
        source='material.material_grade', 
        read_only=True
    )
    material_supplier = serializers.CharField(
        source='material.supplier', 
        read_only=True
    )
    
    class Meta:
        model = Certificate
        fields = [
            'id', 'material', 'material_grade', 'material_supplier',
            'pdf_file', 'download_url', 'uploaded_at',
            'parsed_data', 'file_size', 'file_size_mb', 'file_hash'
        ] + BaseAuditSerializer.Meta.fields
        read_only_fields = [
            'uploaded_at', 'parsed_data', 'file_size', 'file_hash'
        ]
    
    def get_download_url(self, obj):
        """URL для скачивания PDF файла"""
        if obj.pdf_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.pdf_file.url)
            return obj.pdf_file.url
        return None
    
    def get_file_size_mb(self, obj):
        """Размер файла в мегабайтах"""
        if obj.file_size:
            return round(obj.file_size / 1024 / 1024, 2)
        return None
    
    def validate_pdf_file(self, value):
        """Валидация PDF файла"""
        if not value:
            return value
        
        # Проверка размера файла (максимум 10MB)
        max_size = 10 * 1024 * 1024  # 10MB в байтах
        if value.size > max_size:
            raise serializers.ValidationError(
                f'Размер файла не должен превышать 10MB. '
                f'Текущий размер: {round(value.size / 1024 / 1024, 2)}MB'
            )
        
        # Проверка типа файла
        if not value.name.lower().endswith('.pdf'):
            raise serializers.ValidationError(
                'Допускаются только PDF файлы'
            )
        
        # Проверка MIME типа
        if hasattr(value, 'content_type'):
            allowed_types = ['application/pdf']
            if value.content_type not in allowed_types:
                raise serializers.ValidationError(
                    f'Недопустимый тип файла: {value.content_type}. '
                    f'Допускается: {", ".join(allowed_types)}'
                )
        
        return value


class CertificateSimpleSerializer(serializers.ModelSerializer):
    """Упрощенный сериализатор сертификата для вложенного использования"""
    
    download_url = serializers.SerializerMethodField()
    file_size_mb = serializers.SerializerMethodField()
    
    class Meta:
        model = Certificate
        fields = [
            'id', 'pdf_file', 'download_url', 'uploaded_at',
            'file_size_mb', 'file_hash'
        ]
    
    def get_download_url(self, obj):
        if obj.pdf_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.pdf_file.url)
            return obj.pdf_file.url
        return None
    
    def get_file_size_mb(self, obj):
        if obj.file_size:
            return round(obj.file_size / 1024 / 1024, 2)
        return None


class MaterialListSerializer(BaseAuditSerializer):
    """Сериализатор материала для списка (меньше полей)"""
    
    qr_code_url = serializers.SerializerMethodField()
    has_certificate = serializers.SerializerMethodField()
    receipt_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Material
        fields = [
            'id', 'external_id', 'material_grade', 'supplier',
            'size', 'quantity', 'unit', 'receipt_date',
            'location', 'qr_code_url', 'has_certificate', 'receipt_count'
        ] + BaseAuditSerializer.Meta.fields
    
    def get_qr_code_url(self, obj):
        """URL QR кода"""
        if obj.qr_code:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.qr_code.url)
            return obj.qr_code.url
        return None
    
    def get_has_certificate(self, obj):
        """Проверка наличия сертификата"""
        return hasattr(obj, 'certificate') and obj.certificate is not None
    
    def get_receipt_count(self, obj):
        """Количество приемок материала"""
        return obj.receipts.count()


class MaterialDetailSerializer(BaseAuditSerializer):
    """Подробный сериализатор материала"""
    
    qr_code_url = serializers.SerializerMethodField()
    certificate = CertificateSimpleSerializer(read_only=True)
    receipts = serializers.SerializerMethodField()
    
    class Meta:
        model = Material
        fields = [
            'id', 'external_id', 'material_grade', 'supplier',
            'order_number', 'certificate_number', 'heat_number',
            'size', 'quantity', 'unit', 'receipt_date',
            'location', 'qr_code', 'qr_code_url', 'certificate', 'receipts'
        ] + BaseAuditSerializer.Meta.fields
        read_only_fields = ['external_id', 'qr_code']
    
    def get_qr_code_url(self, obj):
        """URL QR кода"""
        if obj.qr_code:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.qr_code.url)
            return obj.qr_code.url
        return None
    
    def get_receipts(self, obj):
        """Последние приемки материала"""
        recent_receipts = obj.receipts.order_by('-receipt_date')[:5]
        return MaterialReceiptListSerializer(
            recent_receipts, 
            many=True, 
            context=self.context
        ).data


class MaterialSerializer(BaseAuditSerializer):
    """Основной сериализатор материала для создания/обновления"""
    
    qr_code_url = serializers.SerializerMethodField()
    certificate = CertificateSimpleSerializer(read_only=True)
    
    class Meta:
        model = Material
        fields = [
            'id', 'external_id', 'material_grade', 'supplier',
            'order_number', 'certificate_number', 'heat_number',
            'size', 'quantity', 'unit', 'receipt_date',
            'location', 'qr_code', 'qr_code_url', 'certificate'
        ] + BaseAuditSerializer.Meta.fields
        read_only_fields = ['external_id', 'qr_code', 'certificate']
    
    def get_qr_code_url(self, obj):
        """URL QR кода"""
        if obj.qr_code:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.qr_code.url)
            return obj.qr_code.url
        return None
    
    def validate_certificate_number(self, value):
        """Валидация уникальности номера сертификата"""
        if value:
            # Получаем текущий объект для исключения из проверки при обновлении
            instance = getattr(self, 'instance', None)
            
            queryset = Material.objects.filter(certificate_number=value)
            if instance:
                queryset = queryset.exclude(pk=instance.pk)
            
            if queryset.exists():
                raise serializers.ValidationError(
                    f'Материал с номером сертификата "{value}" уже существует'
                )
        
        return value
    
    def validate_heat_number(self, value):
        """Валидация номера плавки"""
        if value:
            # Проверка формата номера плавки (пример: должен содержать цифры)
            if not any(char.isdigit() for char in value):
                raise serializers.ValidationError(
                    'Номер плавки должен содержать цифры'
                )
        return value
    
    def validate(self, attrs):
        """Общая валидация объекта"""
        # Проверка соответствия количества и единицы измерения
        quantity = attrs.get('quantity')
        unit = attrs.get('unit')
        
        if quantity and unit:
            if unit == 'pcs' and quantity != int(quantity):
                raise serializers.ValidationError({
                    'quantity': 'Для штучных материалов количество должно быть целым числом'
                })
        
        return attrs


class MaterialReceiptListSerializer(BaseAuditSerializer):
    """Сериализатор приемки материала для списка"""
    
    material_grade = serializers.CharField(
        source='material.material_grade', 
        read_only=True
    )
    material_supplier = serializers.CharField(
        source='material.supplier', 
        read_only=True
    )
    received_by_username = serializers.CharField(
        source='received_by.username', 
        read_only=True
    )
    received_by_full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = MaterialReceipt
        fields = [
            'id', 'material', 'material_grade', 'material_supplier',
            'received_by', 'received_by_username', 'received_by_full_name',
            'receipt_date', 'document_number', 'status'
        ] + BaseAuditSerializer.Meta.fields
    
    def get_received_by_full_name(self, obj):
        """Полное имя принявшего"""
        if obj.received_by:
            return obj.received_by.get_full_name() or obj.received_by.username
        return None


class MaterialReceiptDetailSerializer(BaseAuditSerializer):
    """Подробный сериализатор приемки материала"""
    
    material = MaterialListSerializer(read_only=True)
    received_by = UserSimpleSerializer(read_only=True)
    
    class Meta:
        model = MaterialReceipt
        fields = [
            'id', 'material', 'received_by', 'receipt_date',
            'document_number', 'status', 'notes'
        ] + BaseAuditSerializer.Meta.fields


class MaterialReceiptSerializer(BaseAuditSerializer):
    """Основной сериализатор приемки материала"""
    
    # Для чтения - полная информация о материале
    material = MaterialListSerializer(read_only=True)
    received_by_username = serializers.CharField(
        source='received_by.username', 
        read_only=True
    )
    received_by_full_name = serializers.SerializerMethodField()
    
    # Для записи - только ID материала
    material_id = serializers.IntegerField(write_only=True)
    received_by_id = serializers.IntegerField(
        write_only=True, 
        required=False
    )
    
    class Meta:
        model = MaterialReceipt
        fields = [
            'id', 'material', 'material_id', 
            'received_by', 'received_by_id', 'received_by_username', 'received_by_full_name',
            'receipt_date', 'document_number', 'status', 'notes'
        ] + BaseAuditSerializer.Meta.fields
        read_only_fields = ['received_by']
    
    def get_received_by_full_name(self, obj):
        """Полное имя принявшего"""
        if obj.received_by:
            return obj.received_by.get_full_name() or obj.received_by.username
        return None
    
    def validate_material_id(self, value):
        """Валидация существования материала"""
        try:
            Material.objects.get(pk=value, is_deleted=False)
        except Material.DoesNotExist:
            raise serializers.ValidationError(
                f'Материал с ID {value} не найден или удален'
            )
        return value
    
    def validate_received_by_id(self, value):
        """Валидация существования пользователя"""
        if value:
            try:
                User.objects.get(pk=value, is_active=True)
            except User.DoesNotExist:
                raise serializers.ValidationError(
                    f'Пользователь с ID {value} не найден или неактивен'
                )
        return value
    
    def validate_document_number(self, value):
        """Валидация номера документа"""
        if value:
            # Проверка уникальности номера документа для активных приемок
            instance = getattr(self, 'instance', None)
            
            queryset = MaterialReceipt.objects.filter(
                document_number=value,
                status__in=['pending_qc', 'in_qc', 'approved']
            )
            if instance:
                queryset = queryset.exclude(pk=instance.pk)
            
            if queryset.exists():
                raise serializers.ValidationError(
                    f'Активная приемка с номером документа "{value}" уже существует'
                )
        
        return value
    
    def create(self, validated_data):
        """Создание приемки материала"""
        material_id = validated_data.pop('material_id')
        received_by_id = validated_data.pop('received_by_id', None)
        
        material = Material.objects.get(pk=material_id)
        validated_data['material'] = material
        
        if received_by_id:
            received_by = User.objects.get(pk=received_by_id)
            validated_data['received_by'] = received_by
        
        # Устанавливаем создателя как принявшего, если не указан
        if not validated_data.get('received_by'):
            validated_data['received_by'] = self.context['request'].user
        
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """Обновление приемки материала"""
        material_id = validated_data.pop('material_id', None)
        received_by_id = validated_data.pop('received_by_id', None)
        
        if material_id:
            material = Material.objects.get(pk=material_id)
            validated_data['material'] = material
        
        if received_by_id:
            received_by = User.objects.get(pk=received_by_id)
            validated_data['received_by'] = received_by
        
        return super().update(instance, validated_data)


# Дополнительные сериализаторы для статистики и отчетов

class MaterialStatisticsSerializer(serializers.Serializer):
    """Сериализатор для статистики материалов"""
    
    total_materials = serializers.IntegerField()
    total_quantity = serializers.DecimalField(max_digits=15, decimal_places=3)
    by_grade = serializers.DictField()
    by_supplier = serializers.DictField()
    by_unit = serializers.DictField()
    recent_receipts_count = serializers.IntegerField()
    pending_qc_count = serializers.IntegerField()


class QRCodeDataSerializer(serializers.Serializer):
    """Сериализатор для данных QR кода"""
    
    material_id = serializers.IntegerField()
    external_id = serializers.UUIDField()
    material_grade = serializers.CharField()
    supplier = serializers.CharField()
    size = serializers.CharField()
    location = serializers.CharField()
    generated_at = serializers.DateTimeField()
    qr_code_url = serializers.URLField()


class BulkMaterialOperationSerializer(serializers.Serializer):
    """Сериализатор для массовых операций с материалами"""
    
    material_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        max_length=100
    )
    operation = serializers.ChoiceField(
        choices=['delete', 'change_location', 'export']
    )
    new_location = serializers.CharField(
        required=False,
        max_length=200
    )
    
    def validate(self, attrs):
        """Валидация массовых операций"""
        operation = attrs.get('operation')
        new_location = attrs.get('new_location')
        
        if operation == 'change_location' and not new_location:
            raise serializers.ValidationError({
                'new_location': 'Обязательно для операции смены местоположения'
            })
        
        # Проверка существования материалов
        material_ids = attrs.get('material_ids', [])
        existing_ids = list(
            Material.objects.filter(
                id__in=material_ids,
                is_deleted=False
            ).values_list('id', flat=True)
        )
        
        missing_ids = set(material_ids) - set(existing_ids)
        if missing_ids:
            raise serializers.ValidationError({
                'material_ids': f'Материалы не найдены: {list(missing_ids)}'
            })
        
        return attrs 