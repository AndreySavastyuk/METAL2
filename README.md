# MetalQMS - Система управления качеством металлообработки

🏭 Комплексная система управления качеством для предприятий металлообработки с полным циклом контроля материалов: от поступления на склад до отгрузки готовой продукции.

## 🚀 Быстрый старт

```bash
# Клонирование проекта
git clone https://github.com/AndreySavastyuk/METAL2.git
cd METAL2

# Запуск системы одной командой
python start_metalqms.py
```

## 📋 Описание проекта

MetalQMS - это система качества для металлургических предприятий, которая автоматизирует процесс контроля материалов через все этапы производства:

**Warehouse → QC (ОТК) → Laboratory (ЦЗЛ) → Production → Laboratory → QC → Warehouse**

### 🎯 Ключевые возможности

- **📦 Управление складом**: Приемка, хранение и учет материалов с QR-кодами
- **🔍 Контроль качества (ОТК)**: Чек-листы, инспекции, ППСД процедуры
- **🧪 Лабораторные испытания**: Химический анализ, механические свойства, УЗК
- **🏭 Производственный контроль**: Отслеживание материалов в производстве
- **📊 BPMN Workflow**: Автоматизированные процессы с SLA мониторингом
- **📱 Telegram уведомления**: Мгновенные уведомления о статусах
- **📈 Аналитика и отчеты**: Дашборды, метрики качества, статистика

## 🛠 Технический стек

### Backend
- **Django 5.0+** - основной фреймворк
- **Django REST Framework** - API
- **PostgreSQL 15+** - основная БД (с fallback на SQLite)
- **Redis** - кеш и очереди
- **Celery** - фоновые задачи
- **django-viewflow** - BPMN workflow engine

### Frontend
- **React 18+** - интерфейс
- **TypeScript** - типизация
- **Material-UI** - UI компоненты
- **Vite** - сборщик
- **React Query** - управление состоянием API

### DevOps
- **Docker + Docker Compose** - контейнеризация
- **Prometheus + Grafana** - мониторинг
- **Nginx** - веб-сервер (production)

## 🏗 Архитектура системы

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   Database      │
│   React + TS    │◄──►│   Django + DRF  │◄──►│   PostgreSQL    │
│   Port: 3000    │    │   Port: 8000    │    │   Port: 5432    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                    ┌─────────┼─────────┐
                    │         │         │
            ┌───────▼───┐ ┌───▼───┐ ┌───▼────┐
            │   Redis   │ │Celery │ │Telegram│
            │   Cache   │ │Workers│ │  Bot   │
            └───────────┘ └───────┘ └────────┘
```

## 📁 Структура проекта

```
METAL2/
├── backend/                 # Django backend
│   ├── apps/               # Django приложения
│   │   ├── common/         # Общие компоненты
│   │   ├── warehouse/      # Управление складом
│   │   ├── quality/        # Контроль качества (ОТК)
│   │   ├── laboratory/     # Лабораторные испытания
│   │   ├── production/     # Производственный контроль
│   │   ├── certificates/   # Управление сертификатами
│   │   ├── workflow/       # BPMN процессы
│   │   └── notifications/  # Telegram уведомления
│   ├── config/             # Настройки Django
│   └── manage.py
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/     # React компоненты
│   │   ├── pages/          # Страницы приложения
│   │   ├── services/       # API сервисы
│   │   └── types/          # TypeScript типы
│   ├── package.json
│   └── vite.config.ts
├── start_metalqms.py       # 🚀 Скрипт запуска системы
├── requirements.txt        # Python зависимости
├── docker-compose.yml      # Docker конфигурация
└── README.md              # Этот файл
```

## ⚙️ Установка и настройка

### Требования
- **Python 3.12+**
- **Node.js 18+ и npm**
- **PostgreSQL 15+** (опционально, для production)
- **Redis** (опционально, для Celery)

### Локальная разработка

1. **Клонирование репозитория**
```bash
git clone https://github.com/AndreySavastyuk/METAL2.git
cd METAL2
```

2. **Автоматический запуск** (рекомендуется)
```bash
python start_metalqms.py
```
Скрипт автоматически:
- Проверит зависимости
- Создаст виртуальное окружение (если нужно)
- Установит Python и Node.js пакеты
- Настроит базу данных и миграции
- Создаст тестовых пользователей
- Запустит backend и frontend

3. **Ручная установка** (для разработчиков)
```bash
# Python окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate     # Windows

# Установка зависимостей
pip install -r requirements.txt
cd frontend && npm install && cd ..

# База данных
cd backend
python manage.py migrate
python manage.py createsuperuser

# Запуск сервисов
python manage.py runserver &    # Backend на :8000
cd ../frontend && npm run dev   # Frontend на :3000
```

### 🐳 Docker (Production)

```bash
# Запуск всех сервисов
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Остановка
docker-compose down
```

## 🔐 Доступы по умолчанию

### Системные пользователи
- **Администратор**: `admin` / `admin123`

### Тестовые роли (для демонстрации)
- **Склад**: `warehouse` / `test123`
- **ОТК**: `qc` / `test123`
- **Лаборатория**: `lab` / `test123`

### Доступные URL
- **Frontend**: http://localhost:3000
- **Backend API**: http://127.0.0.1:8000
- **Admin панель**: http://127.0.0.1:8000/admin
- **API документация**: http://127.0.0.1:8000/api/docs/
- **Health check**: http://127.0.0.1:8000/health/

## 📊 Основные модули

### 1. Склад (Warehouse)
- Приемка материалов с сертификатами
- Генерация QR-кодов для маркировки
- Управление поставщиками и марками материалов
- Интеграция со сканерами штрих-кодов

### 2. Контроль качества - ОТК (Quality)
- Настраиваемые чек-листы для инспекций
- Автоопределение требований ППСД и УЗК
- Фиксация несоответствий
- Workflow процессы утверждения

### 3. Лаборатория (Laboratory)
- Заявки на испытания
- Химический анализ
- Механические испытания
- УЗК дефектоскопия
- Калибровка оборудования

### 4. Производство (Production)
- Подготовка материалов к производству
- Контроль расхода
- Batch обработка
- Интеграция с производственными системами

### 5. Workflow (BPMN)
- Визуальное проектирование процессов
- SLA мониторинг и эскалации
- Автоматическое назначение задач
- Аудит всех действий

### 6. Уведомления (Notifications)
- Telegram интеграция
- Email рассылки
- SMS уведомления (через API)
- Настройка подписок по ролям

## 🧪 Тестирование

```bash
# Backend тесты
cd backend
python manage.py test

# Frontend тесты
cd frontend
npm test

# Покрытие кода
pytest --cov=apps
```

## 📈 Мониторинг и логирование

### Логи
- **Файлы логов**: `logs/metalqms.log`, `logs/api.log`
- **Структурированное логирование**: JSON формат
- **Ротация логов**: автоматическая по размеру

### Метрики
- **Prometheus**: http://127.0.0.1:8000/metrics/
- **Health check**: встроенный endpoint для мониторинга
- **Performance**: отслеживание времени ответа API

## 🔒 Безопасность

- JWT токены для аутентификации
- CORS настройки для production
- Валидация всех входных данных
- Rate limiting для API
- Аудит критических действий
- Роли и права доступа

## 🚀 Развертывание в production

1. **Переменные окружения**
```bash
export DEBUG=False
export DATABASE_URL=postgresql://user:pass@host:5432/metalqms
export REDIS_URL=redis://localhost:6379/0
export SECRET_KEY=your-secret-key
export TELEGRAM_BOT_TOKEN=your-bot-token
```

2. **Сборка frontend**
```bash
cd frontend
npm run build
```

3. **Сбор статических файлов**
```bash
cd backend
python manage.py collectstatic
```

4. **Миграции**
```bash
python manage.py migrate
```

## 🤝 Участие в разработке

1. Fork репозитория
2. Создайте feature branch (`git checkout -b feature/amazing-feature`)
3. Commit изменения (`git commit -m 'Add amazing feature'`)
4. Push в branch (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

### Стандарты кода
- **Python**: PEP 8, type hints
- **JavaScript/TypeScript**: ESLint + Prettier
- **Коммиты**: Conventional Commits
- **Тестирование**: минимум 80% покрытия

## 📞 Поддержка

- **Issues**: https://github.com/AndreySavastyuk/METAL2/issues
- **Документация**: `docs/` директория
- **Wiki**: https://github.com/AndreySavastyuk/METAL2/wiki

## 📄 Лицензия

Этот проект распространяется под лицензией MIT. См. файл `LICENSE` для деталей.

## 🏆 Благодарности

- Django team за отличный фреймворк
- React team за современный UI фреймворк
- Material-UI team за красивые компоненты
- Viewflow team за BPMN движок

---

**MetalQMS** - Качество металла под контролем! 🔧⚙️🏭