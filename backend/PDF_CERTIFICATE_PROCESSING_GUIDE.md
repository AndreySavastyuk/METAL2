# Система обработки PDF сертификатов для MetalQMS

## Обзор

Система обработки PDF сертификатов обеспечивает автоматическое извлечение, парсинг и индексацию данных из PDF документов сертификатов качества металлов. Включает полнотекстовый поиск, генерацию превью и асинхронную обработку через Celery.

## Возможности

### 📄 Обработка PDF документов
- Извлечение текста с помощью pypdf и PyMuPDF
- Обработка поврежденных и сложных PDF файлов
- Автоматическое определение кодировки текста
- Сохранение метаданных файла (размер, хеш)

### 🔍 Парсинг данных сертификатов
- Извлечение марки материала
- Определение номера плавки
- Парсинг номера сертификата
- Извлечение информации о поставщике
- Анализ химического состава
- Парсинг механических свойств
- Извлечение результатов испытаний

### 🖼️ Генерация превью
- Создание изображения первой страницы PDF
- Генерация миниатюр для быстрого просмотра
- Оптимизация размера изображений
- Поддержка высокого разрешения

### 🔎 Полнотекстовый поиск
- Поиск по всему тексту сертификата
- Поиск по структурированным данным
- Автодополнение запросов
- Ранжирование результатов по релевантности
- Поддержка PostgreSQL full-text search

### ⚡ Асинхронная обработка
- Обработка через Celery для больших файлов
- Retry логика с exponential backoff
- Мониторинг статуса обработки
- Пакетная обработка сертификатов

## Архитектура

### Компоненты системы

```
PDF Файл → CertificateProcessor → Celery Tasks → Поисковый индекс
    ↓              ↓                   ↓              ↓
Загрузка → Извлечение текста → Асинхронная → Полнотекстовый
           Парсинг данных      обработка     поиск
           Генерация превью    Уведомления   API
```

### Модели данных

1. **CertificateSearchIndex** - поисковый индекс сертификатов
2. **CertificatePreview** - превью изображения сертификатов  
3. **ProcessingLog** - логи обработки для аудита

### Сервисы

1. **CertificateProcessor** - основной сервис обработки
2. **Celery Tasks** - асинхронные задачи
3. **API ViewSets** - REST API для поиска и управления

## Установка и настройка

### 1. Установка зависимостей

```bash
pip install PyMuPDF>=1.23.0 pypdf>=3.17.0 Pillow>=10.0.0
```

### 2. Миграции базы данных

```bash
python manage.py makemigrations certificates
python manage.py migrate
```

### 3. Настройка Celery

```python
# settings.py
CELERY_BEAT_SCHEDULE = {
    'cleanup-failed-certificate-processing': {
        'task': 'apps.certificates.tasks.cleanup_failed_processing',
        'schedule': 1800.0,  # Каждые 30 минут
    },
    'update-certificate-search-statistics': {
        'task': 'apps.certificates.tasks.update_search_statistics', 
        'schedule': 3600.0,  # Каждый час
    },
}
```

### 4. Запуск Celery

```bash
# Worker для обработки задач
celery -A config worker -l info

# Beat для планировщика
celery -A config beat -l info
```

## Использование

### Загрузка сертификатов

```python
from apps.warehouse.models import Certificate, Material

# Создание сертификата (автоматически запускает обработку)
certificate = Certificate.objects.create(
    material=material,
    pdf_file=uploaded_file
)
# Обработка запускается автоматически через Celery
```

### Поиск в сертификатах

```python
from apps.certificates.services import certificate_processor

# Полнотекстовый поиск
results = certificate_processor.search_in_certificates(
    query="40X плавка",
    limit=20
)

for result in results:
    print(f"Материал: {result['grade']}")
    print(f"Плавка: {result['heat_number']}")
    print(f"Релевантность: {result['match_score']}")
```

### Извлечение данных из PDF

```python
# Извлечение текста
text = certificate_processor.extract_text_from_pdf('/path/to/certificate.pdf')

# Парсинг данных
parsed_data = certificate_processor.parse_certificate_data(text)

print(f"Марка: {parsed_data.get('grade')}")
print(f"Плавка: {parsed_data.get('heat_number')}")
print(f"Химсостав: {parsed_data.get('chemical_composition')}")
```

### Генерация превью

```python
# Генерация превью первой страницы
preview_url = certificate_processor.generate_certificate_preview(pdf_file)
```

## Management команды

### Массовая обработка сертификатов

```bash
# Обработать все необработанные сертификаты
python manage.py reprocess_all_certificates

# Переобработать все сертификаты заново
python manage.py reprocess_all_certificates --force

# Обработать конкретные сертификаты
python manage.py reprocess_all_certificates --ids 1,2,3

# Только извлечение текста
python manage.py reprocess_all_certificates --text-only

# Только генерация превью
python manage.py reprocess_all_certificates --preview-only

# Асинхронная обработка через Celery
python manage.py reprocess_all_certificates --async

# Пакетная обработка
python manage.py reprocess_all_certificates --batch-size 50

# Показать статистику
python manage.py reprocess_all_certificates --stats

# Dry run - показать что будет обработано
python manage.py reprocess_all_certificates --dry-run
```

### Фильтры обработки

```bash
# Только неудачно обработанные
python manage.py reprocess_all_certificates --failed-only

# Только без превью
python manage.py reprocess_all_certificates --missing-preview

# Только без текста
python manage.py reprocess_all_certificates --missing-text
```

## REST API

### Поиск в сертификатах

```http
GET /api/certificates/processing/search/?q=40X&limit=20
```

**Ответ:**
```json
{
  "query": "40X",
  "total_results": 5,
  "results": [
    {
      "certificate_id": 1,
      "grade": "40X",
      "heat_number": "H12345",
      "certificate_number": "CERT-001",
      "supplier": "МеталлТорг",
      "match_score": 10.0,
      "matched_fields": ["grade", "text"],
      "preview_url": "/media/certificates/previews/cert_1_preview.png"
    }
  ]
}
```

### Автодополнение

```http
GET /api/certificates/processing/suggestions/?q=40&type=grade
```

**Ответ:**
```json
{
  "query": "40",
  "suggestions": [
    {"type": "grade", "value": "40X", "label": "Марка: 40X"},
    {"type": "grade", "value": "40XН", "label": "Марка: 40XН"}
  ]
}
```

### Статистика обработки

```http
GET /api/certificates/processing/statistics/
```

**Ответ:**
```json
{
  "total_certificates": 150,
  "unprocessed": 10,
  "processing": {
    "success_rate": 94.3,
    "completed": 133,
    "failed": 7,
    "pending": 10
  },
  "previews": {
    "preview_rate": 89.3,
    "completed_previews": 134
  }
}
```

### Статус обработки сертификата

```http
GET /api/certificates/processing/1/processing_status/
```

### Переобработка сертификата

```http
POST /api/certificates/processing/1/reprocess/
```

### Пакетная переобработка

```http
POST /api/certificates/processing/reprocess_batch/
Content-Type: application/json

{
  "certificate_ids": [1, 2, 3],
  "force": true
}
```

## Celery задачи

### Основные задачи

#### process_uploaded_certificate
Полная обработка загруженного сертификата:
- Извлечение текста
- Парсинг данных  
- Создание поискового индекса
- Генерация превью

```python
from apps.certificates.tasks import process_uploaded_certificate

# Запуск обработки
task = process_uploaded_certificate.delay(certificate_id=1)
```

#### generate_certificate_preview
Генерация превью сертификата:

```python
from apps.certificates.tasks import generate_certificate_preview

task = generate_certificate_preview.delay(certificate_id=1)
```

#### reprocess_certificates_batch
Пакетная обработка сертификатов:

```python
from apps.certificates.tasks import reprocess_certificates_batch

task = reprocess_certificates_batch.delay(
    certificate_ids=[1, 2, 3],
    force_reprocess=True
)
```

### Автоматические задачи

- **cleanup_failed_processing** - очистка зависших обработок (каждые 30 мин)
- **update_search_statistics** - обновление статистики (каждый час)
- **optimize_search_index** - оптимизация индекса (раз в день)

## Администрирование

### Django админка

Доступны админки для:

1. **CertificateSearchIndex** - управление поисковыми индексами
2. **CertificatePreview** - управление превью изображениями
3. **ProcessingLog** - просмотр логов обработки

### Действия в админке

- Переобработка выбранных сертификатов
- Регенерация превью
- Очистка ошибок
- Просмотр статистики

### Мониторинг

#### Логи обработки
Все операции логируются в модель `ProcessingLog`:

```python
# Просмотр логов конкретного сертификата
logs = ProcessingLog.objects.filter(certificate_id=1)

for log in logs:
    print(f"{log.operation}: {log.status} ({log.duration_seconds}s)")
```

#### Метрики производительности
- Время извлечения текста
- Время генерации превью
- Количество успешных/неудачных обработок
- Статистика ошибок

## Обработка ошибок

### Типы ошибок

1. **Поврежденные PDF файлы**
   - Автоматическое переключение между парсерами
   - Логирование проблемных файлов

2. **Ошибки извлечения текста**
   - Retry логика с exponential backoff
   - Fallback на альтернативные методы

3. **Ошибки генерации превью**
   - Обработка файлов без изображений
   - Автоматическое масштабирование

### Мониторинг ошибок

```python
# Частые ошибки
from django.db.models import Count

errors = CertificateSearchIndex.objects.filter(
    processing_status='failed'
).values('error_message').annotate(
    count=Count('id')
).order_by('-count')
```

## Оптимизация производительности

### Настройки для больших файлов

```python
# settings.py
DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024  # 50MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024  # 50MB

# Celery
CELERY_TASK_TIME_LIMIT = 300  # 5 минут на задачу
CELERY_TASK_SOFT_TIME_LIMIT = 240  # 4 минуты предупреждение
```

### Оптимизация поиска

```python
# Использование индексов PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'OPTIONS': {
            'options': '-c default_text_search_config=russian'
        }
    }
}
```

### Кэширование

```python
# Кэширование результатов поиска
from django.core.cache import cache

def cached_search(query, limit=50):
    cache_key = f"cert_search:{query}:{limit}"
    results = cache.get(cache_key)
    
    if results is None:
        results = certificate_processor.search_in_certificates(query, limit)
        cache.set(cache_key, results, 300)  # 5 минут
    
    return results
```

## Безопасность

### Валидация файлов

```python
def validate_pdf_file(file):
    # Проверка расширения
    if not file.name.endswith('.pdf'):
        raise ValidationError('Только PDF файлы разрешены')
    
    # Проверка размера
    if file.size > 50 * 1024 * 1024:  # 50MB
        raise ValidationError('Файл слишком большой')
    
    # Проверка magic number
    file.seek(0)
    header = file.read(4)
    if header != b'%PDF':
        raise ValidationError('Поврежденный PDF файл')
```

### Контроль доступа

```python
# Права доступа в API
class CertificateProcessingViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]
    
    def reprocess(self, request, pk=None):
        if not request.user.has_perm('warehouse.change_certificate'):
            return Response(status=403)
```

## Тестирование

### Тестовый скрипт

```bash
python test_pdf_processing.py
```

Скрипт тестирует:
- Извлечение текста из PDF
- Парсинг данных сертификатов
- Генерацию превью
- Поиск в сертификатах
- Асинхронную обработку

### Unit тесты

```python
class CertificateProcessorTestCase(TestCase):
    def test_text_extraction(self):
        processor = CertificateProcessor()
        text = processor.extract_text_from_pdf('test_certificate.pdf')
        self.assertIsNotNone(text)
        self.assertGreater(len(text), 100)
    
    def test_data_parsing(self):
        text = "Марка стали: 40X\nПлавка № 12345"
        parsed = processor.parse_certificate_data(text)
        self.assertEqual(parsed['grade'], '40X')
        self.assertEqual(parsed['heat_number'], '12345')
```

## Производственное развертывание

### Docker конфигурация

```yaml
version: '3.8'
services:
  app:
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
    volumes:
      - ./media:/app/media
      
  celery_worker:
    command: celery -A config worker -l info
    volumes:
      - ./media:/app/media
      
  celery_beat:
    command: celery -A config beat -l info
```

### Мониторинг в продакшене

```bash
# Flower для мониторинга Celery
celery -A config flower --port=5555

# Логирование
tail -f /var/log/metalqms/certificate_processing.log
```

## FAQ

### Q: PDF не обрабатывается
A: Проверьте:
- Размер файла (макс. 50MB)
- Формат файла (только PDF)
- Статус Celery worker
- Логи в ProcessingLog

### Q: Поиск не работает
A: Проверьте:
- Статус обработки в CertificateSearchIndex
- Наличие извлеченного текста
- Настройки PostgreSQL full-text search

### Q: Медленная обработка
A: Оптимизация:
- Увеличьте количество Celery workers
- Используйте SSD для файлов
- Настройте кэширование
- Оптимизируйте регулярные выражения

### Q: Ошибки парсинга данных
A: Улучшение:
- Дополните регулярные выражения
- Добавьте новые паттерны в CertificateProcessor
- Обучите систему на ваших сертификатах

## Развитие системы

### Планируемые улучшения

- [ ] OCR для отсканированных PDF
- [ ] Машинное обучение для парсинга
- [ ] Поддержка других форматов (Word, Excel)
- [ ] Интеграция с внешними системами
- [ ] Автоматическая категоризация сертификатов
- [ ] Система версионирования документов

### Расширение функциональности

```python
class AdvancedCertificateProcessor(CertificateProcessor):
    def extract_with_ocr(self, file_path):
        """OCR для отсканированных документов"""
        pass
    
    def classify_certificate_type(self, text):
        """Автоматическая классификация типа сертификата"""
        pass
    
    def extract_tables(self, file_path):
        """Извлечение табличных данных"""
        pass
```

---

*Последнее обновление: 2024-01-15*