"""
Модели для работы с сертификатами
"""
from django.db import models
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex


class CertificateSearchIndex(models.Model):
    """Поисковый индекс для сертификатов"""
    
    certificate = models.OneToOneField(
        'warehouse.Certificate',
        on_delete=models.CASCADE,
        related_name='search_index',
        verbose_name='Сертификат'
    )
    
    search_vector = SearchVectorField(
        null=True,
        blank=True,
        verbose_name='Поисковый вектор'
    )
    
    extracted_text = models.TextField(
        blank=True,
        verbose_name='Извлеченный текст'
    )
    
    grade = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Марка материала'
    )
    
    heat_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Номер плавки'
    )
    
    certificate_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Номер сертификата'
    )
    
    supplier = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Поставщик'
    )
    
    chemical_composition = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Химический состав'
    )
    
    mechanical_properties = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Механические свойства'
    )
    
    test_results = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Результаты испытаний'
    )
    
    indexed_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата индексации'
    )
    
    processing_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Ожидает обработки'),
            ('processing', 'Обрабатывается'),
            ('completed', 'Обработан'),
            ('failed', 'Ошибка обработки'),
        ],
        default='pending',
        verbose_name='Статус обработки'
    )
    
    error_message = models.TextField(
        blank=True,
        verbose_name='Сообщение об ошибке'
    )

    class Meta:
        verbose_name = 'Поисковый индекс сертификата'
        verbose_name_plural = 'Поисковые индексы сертификатов'
        indexes = [
            GinIndex(fields=['search_vector']),
        ]

    def __str__(self):
        return f"Индекс для {self.certificate}"


class CertificatePreview(models.Model):
    """Превью сертификата (первая страница как изображение)"""
    
    certificate = models.OneToOneField(
        'warehouse.Certificate',
        on_delete=models.CASCADE,
        related_name='preview',
        verbose_name='Сертификат'
    )
    
    preview_image = models.ImageField(
        upload_to='certificates/previews/',
        null=True,
        blank=True,
        verbose_name='Превью изображение'
    )
    
    thumbnail = models.ImageField(
        upload_to='certificates/thumbnails/',
        null=True,
        blank=True,
        verbose_name='Миниатюра'
    )
    
    generated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата генерации'
    )
    
    generation_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Ожидает генерации'),
            ('generating', 'Генерируется'),
            ('completed', 'Сгенерировано'),
            ('failed', 'Ошибка генерации'),
        ],
        default='pending',
        verbose_name='Статус генерации'
    )
    
    error_message = models.TextField(
        blank=True,
        verbose_name='Сообщение об ошибке'
    )

    class Meta:
        verbose_name = 'Превью сертификата'
        verbose_name_plural = 'Превью сертификатов'

    def __str__(self):
        return f"Превью для {self.certificate}"


class ProcessingLog(models.Model):
    """Лог обработки сертификатов"""
    
    certificate = models.ForeignKey(
        'warehouse.Certificate',
        on_delete=models.CASCADE,
        related_name='processing_logs',
        verbose_name='Сертификат'
    )
    
    operation = models.CharField(
        max_length=50,
        choices=[
            ('text_extraction', 'Извлечение текста'),
            ('data_parsing', 'Парсинг данных'),
            ('preview_generation', 'Генерация превью'),
            ('search_indexing', 'Поисковая индексация'),
        ],
        verbose_name='Операция'
    )
    
    status = models.CharField(
        max_length=20,
        choices=[
            ('started', 'Начата'),
            ('completed', 'Завершена'),
            ('failed', 'Ошибка'),
        ],
        verbose_name='Статус'
    )
    
    started_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Время начала'
    )
    
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Время завершения'
    )
    
    duration_seconds = models.FloatField(
        null=True,
        blank=True,
        verbose_name='Длительность (сек)'
    )
    
    error_message = models.TextField(
        blank=True,
        verbose_name='Сообщение об ошибке'
    )
    
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Метаданные операции'
    )

    class Meta:
        verbose_name = 'Лог обработки'
        verbose_name_plural = 'Логи обработки'
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.operation} - {self.status} ({self.certificate})"