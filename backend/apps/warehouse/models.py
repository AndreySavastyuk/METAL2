import os
import uuid
import qrcode
from io import BytesIO
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.core.files import File
from django.utils import timezone
from django.urls import reverse
from apps.common.models import AuditMixin


class SoftDeleteManager(models.Manager):
    """Менеджер для мягкого удаления"""
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class SoftDeleteMixin(models.Model):
    """Миксин для мягкого удаления"""
    is_deleted = models.BooleanField(default=False, verbose_name='Удалено')
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата удаления')
    deleted_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='%(class)s_deleted',
        verbose_name='Удалено пользователем'
    )

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    def delete(self, user=None, *args, **kwargs):
        """Мягкое удаление"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        if user:
            self.deleted_by = user
        self.save()

    def restore(self):
        """Восстановление после удаления"""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save()

    class Meta:
        abstract = True


class Material(AuditMixin, SoftDeleteMixin):
    """Модель материала на складе"""
    
    UNIT_CHOICES = [
        ('kg', 'Килограммы'),
        ('pcs', 'Штуки'),
        ('meters', 'Метры'),
    ]

    # Основные характеристики материала
    material_grade = models.CharField(
        max_length=100, 
        verbose_name='Марка материала'
    )
    supplier = models.CharField(
        max_length=200, 
        verbose_name='Поставщик'
    )
    order_number = models.CharField(
        max_length=100, 
        verbose_name='Номер заказа'
    )
    certificate_number = models.CharField(
        max_length=100, 
        verbose_name='Номер сертификата'
    )
    heat_number = models.CharField(
        max_length=100, 
        verbose_name='Номер плавки'
    )
    size = models.CharField(
        max_length=100, 
        verbose_name='Размер'
    )
    
    # Количественные характеристики
    quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=3, 
        verbose_name='Количество'
    )
    unit = models.CharField(
        max_length=10, 
        choices=UNIT_CHOICES, 
        verbose_name='Единица измерения'
    )
    
    # Дополнительные поля
    receipt_date = models.DateTimeField(
        default=timezone.now, 
        verbose_name='Дата поступления'
    )
    location = models.CharField(
        max_length=200, 
        blank=True, 
        verbose_name='Местоположение на складе'
    )
    
    # QR код
    qr_code = models.ImageField(
        upload_to='qr_codes/', 
        blank=True, 
        null=True, 
        verbose_name='QR код'
    )
    
    # Уникальный идентификатор для внешних систем
    external_id = models.UUIDField(
        default=uuid.uuid4, 
        unique=True, 
        verbose_name='Внешний идентификатор'
    )

    def generate_qr_code(self):
        """Генерация QR кода для материала"""
        qr_data = {
            'id': str(self.external_id),
            'grade': self.material_grade,
            'supplier': self.supplier,
            'certificate': self.certificate_number,
            'heat': self.heat_number,
            'quantity': str(self.quantity),
            'unit': self.unit
        }
        
        qr_string = f"Material ID: {qr_data['id']}\n"
        qr_string += f"Grade: {qr_data['grade']}\n"
        qr_string += f"Supplier: {qr_data['supplier']}\n"
        qr_string += f"Certificate: {qr_data['certificate']}\n"
        qr_string += f"Heat: {qr_data['heat']}\n"
        qr_string += f"Quantity: {qr_data['quantity']} {qr_data['unit']}"
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_string)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        filename = f'material_{self.external_id}.png'
        
        self.qr_code.save(filename, File(buffer), save=False)
        buffer.close()

    def save(self, *args, **kwargs):
        """Переопределение сохранения для автогенерации QR кода"""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new or not self.qr_code:
            self.generate_qr_code()
            super().save(update_fields=['qr_code'])

    def __str__(self):
        return f"{self.material_grade} - {self.supplier} ({self.certificate_number})"

    class Meta:
        verbose_name = 'Материал'
        verbose_name_plural = 'Материалы'
        ordering = ['-receipt_date']
        indexes = [
            models.Index(fields=['material_grade']),
            models.Index(fields=['supplier']),
            models.Index(fields=['certificate_number']),
            models.Index(fields=['heat_number']),
            models.Index(fields=['receipt_date']),
        ]


class MaterialReceipt(AuditMixin):
    """Модель поступления материала"""
    
    STATUS_CHOICES = [
        ('pending_qc', 'Ожидает ОТК'),
        ('in_qc', 'В ОТК'),
        ('approved', 'Одобрено'),
        ('rejected', 'Отклонено'),
    ]

    material = models.ForeignKey(
        Material, 
        on_delete=models.CASCADE,
        related_name='receipts',
        verbose_name='Материал'
    )
    received_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL,
        null=True,
        related_name='received_materials',
        verbose_name='Принял'
    )
    receipt_date = models.DateTimeField(
        default=timezone.now, 
        verbose_name='Дата приемки'
    )
    document_number = models.CharField(
        max_length=100, 
        verbose_name='Номер документа'
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending_qc',
        verbose_name='Статус'
    )
    notes = models.TextField(
        blank=True, 
        verbose_name='Примечания'
    )

    def __str__(self):
        return f"Поступление {self.material} - {self.document_number}"

    class Meta:
        verbose_name = 'Поступление материала'
        verbose_name_plural = 'Поступления материалов'
        ordering = ['-receipt_date']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['receipt_date']),
            models.Index(fields=['document_number']),
        ]


class Certificate(AuditMixin):
    """Модель сертификата материала"""
    
    material = models.OneToOneField(
        Material, 
        on_delete=models.CASCADE,
        related_name='certificate',
        verbose_name='Материал'
    )
    pdf_file = models.FileField(
        upload_to='certificates/', 
        verbose_name='PDF файл сертификата'
    )
    uploaded_at = models.DateTimeField(
        auto_now_add=True, 
        verbose_name='Дата загрузки'
    )
    parsed_data = models.JSONField(
        default=dict, 
        blank=True,
        verbose_name='Извлеченные данные'
    )
    file_size = models.PositiveIntegerField(
        null=True, 
        blank=True,
        verbose_name='Размер файла (байт)'
    )
    file_hash = models.CharField(
        max_length=64, 
        blank=True,
        verbose_name='Хеш файла'
    )

    def extract_text_from_pdf(self):
        """Извлечение текста из PDF сертификата"""
        try:
            import pypdf
            import hashlib
            
            if not self.pdf_file:
                return None
                
            # Вычисление хеша файла
            self.pdf_file.seek(0)
            file_content = self.pdf_file.read()
            self.file_hash = hashlib.sha256(file_content).hexdigest()
            self.file_size = len(file_content)
            
            # Извлечение текста
            self.pdf_file.seek(0)
            reader = pypdf.PdfReader(self.pdf_file)
            
            extracted_text = ""
            for page in reader.pages:
                extracted_text += page.extract_text() + "\n"
            
            # Сохранение извлеченных данных
            self.parsed_data = {
                'extracted_text': extracted_text,
                'num_pages': len(reader.pages),
                'extraction_date': timezone.now().isoformat(),
                'file_hash': self.file_hash,
                'file_size': self.file_size
            }
            
            return extracted_text
            
        except Exception as e:
            self.parsed_data = {
                'error': str(e),
                'extraction_date': timezone.now().isoformat()
            }
            return None

    def save(self, *args, **kwargs):
        """Переопределение сохранения для автоматического извлечения текста"""
        is_new = self.pk is None
        file_changed = False
        
        # Проверяем, изменился ли файл
        if not is_new and self.pk:
            try:
                old_instance = Certificate.objects.get(pk=self.pk)
                file_changed = old_instance.pdf_file != self.pdf_file
            except Certificate.DoesNotExist:
                file_changed = True
        
        super().save(*args, **kwargs)
        
        # Запускаем обработку для новых файлов или при изменении файла
        if (is_new or file_changed) and self.pdf_file:
            # Запускаем асинхронную обработку через Celery
            try:
                from apps.certificates.tasks import process_uploaded_certificate
                process_uploaded_certificate.delay(self.id)
            except ImportError:
                # Fallback на синхронное извлечение если Celery недоступен
                self.extract_text_from_pdf()
                super().save(update_fields=['parsed_data', 'file_size', 'file_hash'])

    def __str__(self):
        return f"Сертификат {self.material.certificate_number}"

    class Meta:
        verbose_name = 'Сертификат'
        verbose_name_plural = 'Сертификаты'
        ordering = ['-uploaded_at'] 