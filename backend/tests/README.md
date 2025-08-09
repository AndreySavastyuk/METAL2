# MetalQMS Test Suite

Комплексная система тестов для Django backend приложения MetalQMS.

## 🎯 Обзор

Система тестов покрывает:
- **Model tests** - валидация моделей и бизнес-логика
- **API tests** - CRUD операции, разрешения, фильтрация
- **Service tests** - workflow, PPSD логика, уведомления
- **Integration tests** - полные сценарии работы системы

## 📊 Цель покрытия кода: 80%+

## 🚀 Быстрый старт

### Установка зависимостей

```bash
pip install -r tests/requirements_test.txt
```

### Запуск всех тестов

```bash
python run_tests.py
```

### Запуск с покрытием

```bash
python run_tests.py --coverage
```

## 📋 Структура тестов

```
tests/
├── __init__.py                 # Инициализация пакета тестов
├── conftest.py                 # Pytest конфигурация и фикстуры
├── test_settings.py            # Настройки Django для тестов
├── pytest.ini                 # Конфигурация pytest
├── mixins.py                   # Миксины для тестов
├── utils.py                    # Утилиты для тестов
├── factories.py                # Factory Boy фабрики
├── test_models.py              # Тесты моделей
├── test_api.py                 # Тесты API
├── test_services.py            # Тесты сервисов
└── requirements_test.txt       # Зависимости для тестов
```

## 🧪 Запуск конкретных тестов

### Модели
```bash
python run_tests.py --models
```

### API
```bash
python run_tests.py --api
```

### Сервисы
```bash
python run_tests.py --services
```

### Интеграционные тесты
```bash
python run_tests.py --integration
```

### Быстрые тесты (без медленных)
```bash
python run_tests.py --fast
```

## 🏗️ Factory Boy фабрики

Используются для генерации тестовых данных:

```python
from tests.factories import MaterialFactory, QCInspectionFactory

# Создание материала
material = MaterialFactory()

# Материал с ППСД требованием
ppsd_material = PPSDRequiredMaterialFactory(material_grade='12X18H10T')

# Полный workflow
complete_material = CompleteMaterialWorkflowFactory()
```

### Доступные фабрики

- `UserFactory` - Пользователи
- `WarehouseUserFactory` - Пользователи склада
- `QCUserFactory` - Пользователи ОТК
- `LabUserFactory` - Пользователи лаборатории
- `MaterialFactory` - Материалы
- `PPSDRequiredMaterialFactory` - Материалы с ППСД
- `MaterialReceiptFactory` - Приемки материалов
- `QCInspectionFactory` - Инспекции ОТК
- `LaboratoryTestFactory` - Лабораторные тесты
- `CertificateFactory` - Сертификаты
- `NotificationPreferencesFactory` - Настройки уведомлений

## 🎭 Мокирование внешних сервисов

Автоматически мокируются:
- **QR код генерация** (qrcode library)
- **Telegram Bot API** 
- **PDF обработка** (ReportLab)

```python
def test_with_mocks(self, mock_external_services):
    qr_mock = mock_external_services['qr_code']
    telegram_mock = mock_external_services['telegram_bot']
    # Тест с моками
```

## 📈 Отчеты о покрытии

После запуска тестов:
- **Консольный отчет** - показывает покрытие в терминале
- **HTML отчет** - `htmlcov/index.html`

```bash
# Открыть HTML отчет
start htmlcov/index.html  # Windows
open htmlcov/index.html   # macOS
```

## 🔧 Конфигурация тестов

### test_settings.py
- Используется SQLite in-memory база
- Отключены миграции для скорости
- Моки для внешних сервисов
- Синхронное выполнение Celery задач

### pytest.ini
- Маркеры для категорий тестов
- Настройки покрытия
- Фильтры предупреждений

## 📊 Маркеры тестов

```python
@pytest.mark.unit
def test_model_validation():
    pass

@pytest.mark.api
def test_material_creation():
    pass

@pytest.mark.integration
def test_complete_workflow():
    pass

@pytest.mark.slow
def test_heavy_computation():
    pass
```

Запуск по маркерам:
```bash
pytest -m "unit"              # Только unit тесты
pytest -m "api and not slow"  # API тесты кроме медленных
pytest -m "integration"       # Интеграционные тесты
```

## 🛠️ Утилиты для тестов

### MockHelper
```python
with MockHelper.mock_telegram_bot():
    # Тест с замоканным Telegram
    pass
```

### FileHelper
```python
pdf_file = FileHelper.create_test_pdf()
image_file = FileHelper.create_test_image()
```

### APITestHelper
```python
APITestHelper.assert_paginated_response(self, response)
APITestHelper.assert_api_error(self, response, 400, 'field_name')
```

## 🔒 Тесты разрешений

```python
class PermissionTest(ComprehensiveTestMixin, APITestCase):
    def test_warehouse_permissions(self):
        endpoints = [
            {
                'url': '/api/v1/materials/',
                'method': 'post',
                'allowed_roles': ['warehouse', 'admin'],
                'denied_roles': ['qc', 'lab', 'regular']
            }
        ]
        self.test_endpoint_permissions(endpoints)
```

## 📝 Workflow тесты

Тестирование бизнес-процессов:

```python
def test_ppsd_workflow(self):
    # 1. Создать материал с ППСД
    material = PPSDRequiredMaterialFactory()
    
    # 2. Проверить требование ППСД
    response = MaterialInspectionService.check_ppsd_requirement(
        material.material_grade
    )
    self.assertTrue(response.data['requires_ppsd'])
    
    # 3. Создать инспекцию
    inspection = QCInspectionFactory(requires_ppsd=True)
    
    # 4. Проверить уведомления
    self.assert_notification_sent()
```

## 🚨 Проблемы и решения

### Медленные тесты
```bash
pytest --durations=10  # Показать 10 самых медленных тестов
```

### Отладка тестов
```bash
pytest -v -s --tb=long  # Подробный вывод
pytest --pdb            # Запуск PDB при ошибке
```

### Проблемы с базой данных
```bash
pytest --reuse-db      # Переиспользовать тестовую БД
pytest --create-db     # Пересоздать тестовую БД
```

## 📈 Цели покрытия по модулям

| Модуль | Цель | Статус |
|--------|------|--------|
| warehouse.models | 90%+ | ✅ |
| warehouse.views | 85%+ | ✅ |
| warehouse.services | 90%+ | ✅ |
| quality.models | 85%+ | ✅ |
| laboratory.models | 85%+ | ✅ |
| notifications.services | 80%+ | ✅ |
| workflow.flows | 75%+ | ✅ |

## 🎯 Лучшие практики

1. **Один тест - одна проверка**
2. **Используйте фабрики вместо фикстур**
3. **Мокайте внешние сервисы**
4. **Тестируйте граничные случаи**
5. **Проверяйте разрешения для каждого endpoint**
6. **Тестируйте полные workflow сценарии**

## 🔄 CI/CD Integration

```yaml
# .github/workflows/tests.yml
- name: Run tests
  run: |
    python run_tests.py --coverage
    
- name: Upload coverage
  run: |
    codecov -f coverage.xml
```

## 📞 Поддержка

При проблемах с тестами:
1. Проверьте настройки в `test_settings.py`
2. Убедитесь что все зависимости установлены
3. Проверьте моки для внешних сервисов
4. Изучите логи в консоли