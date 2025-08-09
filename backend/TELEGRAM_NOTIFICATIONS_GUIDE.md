# Система Telegram уведомлений для MetalQMS

## Обзор

Система Telegram уведомлений интегрирована в MetalQMS для автоматической отправки уведомлений о важных событиях в процессе контроля качества металлов.

## Возможности

### 🔄 Уведомления о статусах
- Изменение статуса материала (pending_qc → in_qc → approved/rejected)
- Переход между этапами workflow
- Срочные уведомления при отклонении материалов

### 📋 Назначение задач
- Уведомления о новых задачах для сотрудников
- Информация о материале и требуемых действиях
- Приоритизация срочных задач

### 📊 Ежедневные сводки
- Статистика по поступлениям
- Количество проведенных проверок
- Итоги лабораторных испытаний

### 🚨 Срочные оповещения
- Критические ошибки в процессе
- Нарушения SLA
- Экстренные ситуации

## Архитектура

### Компоненты

1. **TelegramNotificationService** - основной сервис для отправки уведомлений
2. **Celery Tasks** - асинхронная обработка с retry логикой
3. **UserNotificationPreferences** - настройки пользователей
4. **NotificationLog** - лог всех отправленных уведомлений

### Схема работы

```
Изменение в системе → TelegramNotificationService → Celery Task → Telegram Bot API → Пользователь
                                ↓
                      NotificationLog (аудит)
```

## Настройка

### 1. Создание Telegram бота

```bash
# 1. Найдите @BotFather в Telegram
# 2. Отправьте /start
# 3. Отправьте /newbot
# 4. Следуйте инструкциям
# 5. Скопируйте токен
```

### 2. Конфигурация переменных окружения

```bash
# .env файл
TELEGRAM_BOT_TOKEN=your_bot_token_here
REDIS_URL=redis://localhost:6379/0
```

### 3. Получение Chat ID

```bash
# 1. Напишите сообщение своему боту
# 2. Откройте в браузере:
# https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
# 3. Найдите "chat":{"id": YOUR_CHAT_ID}
```

### 4. Настройка пользователя

В админке Django:
1. Перейдите в "Настройки уведомлений пользователей"
2. Найдите или создайте пользователя
3. Укажите Telegram Chat ID
4. Включите "Включить Telegram уведомления"
5. Настройте типы уведомлений

## Использование

### Отправка уведомления о статусе

```python
from apps.notifications.services import telegram_service

telegram_service.send_status_update(
    user_id=user.id,
    material=material_instance,
    old_status='pending_qc',
    new_status='in_qc',
    is_urgent=False
)
```

### Уведомление о назначении задачи

```python
telegram_service.send_task_assignment(
    user_id=user.id,
    task_type='qc_inspection',
    material=material_instance,
    additional_info="Требуется проверка ППСД",
    is_urgent=True
)
```

### Ежедневная сводка

```python
telegram_service.send_daily_summary(
    user_id=user.id,
    summary_date=date.today()
)
```

### Срочное оповещение

```python
telegram_service.send_urgent_alert(
    user_ids=[1, 2, 3],
    alert_type="Нарушение SLA",
    message="Превышено время обработки материала",
    material=material_instance
)
```

## Celery задачи

### Основные задачи

- **send_telegram_message** - отправка одного сообщения
- **send_daily_summaries** - рассылка ежедневных сводок
- **send_bulk_notifications** - массовая рассылка
- **retry_failed_notifications** - повтор неудачных отправок
- **cleanup_old_notification_logs** - очистка старых логов

### Запуск Celery

```bash
# Воркер
celery -A config worker -l info

# Beat (планировщик)
celery -A config beat -l info

# Flower (мониторинг)
celery -A config flower
```

## Настройки уведомлений

### Типы уведомлений

```python
NOTIFICATION_TYPES = [
    ('status_update', 'Изменение статуса материала'),
    ('task_assignment', 'Назначение задачи'),
    ('daily_summary', 'Ежедневная сводка'),
    ('urgent_alert', 'Срочные уведомления'),
    ('sla_warning', 'Предупреждение о нарушении SLA'),
    ('quality_alert', 'Уведомления о качестве'),
    ('workflow_complete', 'Завершение процесса'),
]
```

### Настройки пользователя

```python
{
    "status_update": {"enabled": True, "urgent_only": False},
    "task_assignment": {"enabled": True, "urgent_only": False},
    "urgent_alert": {"enabled": True, "urgent_only": False},
    "daily_summary": {"enabled": False, "urgent_only": False}
}
```

### Тихие часы

Настройка периодов, когда не отправлять несрочные уведомления:

```python
quiet_hours_start = "22:00"
quiet_hours_end = "08:00"
```

## Retry логика

### Exponential backoff

- 1-я попытка: через 1 минуту
- 2-я попытка: через 2 минуты  
- 3-я попытка: через 4 минуты
- 4-я попытка: через 8 минут
- 5-я попытка: через 16 минут

### Обработка ошибок

- **Forbidden**: пользователь заблокировал бота - отключаем уведомления
- **BadRequest**: неверный формат - не повторяем
- **TimedOut/NetworkError**: сетевые проблемы - повторяем
- **TelegramError**: другие ошибки API - повторяем с ограничением

## Rate Limiting

Соблюдение ограничений Telegram API:
- Максимум 30 сообщений в секунду
- Автоматические задержки при массовых рассылках
- Мониторинг и логирование скорости отправки

## Мониторинг

### Логирование

Все уведомления сохраняются в модель `NotificationLog`:

```python
{
    "user": "username",
    "notification_type": "status_update",
    "status": "sent|failed|pending|retry",
    "error_message": "описание ошибки",
    "retry_count": 3,
    "sent_at": "2024-01-15 10:30:00"
}
```

### Админка

- Просмотр логов уведомлений
- Повтор неудачных отправок
- Тестирование подключения к боту
- Отправка тестовых уведомлений
- Статистика отправок

### Метрики

- Успешность доставки
- Время отклика
- Количество повторов
- Активные пользователи

## Тестирование

### Скрипт тестирования

```bash
cd backend
python test_telegram_notifications.py
```

Скрипт выполняет:
1. Создание тестового пользователя
2. Проверку подключения к боту
3. Создание тестового материала
4. Отправку пробного уведомления
5. Вывод инструкций по настройке

### Проверка через админку

1. Войдите в админку Django
2. Перейдите в "Настройки уведомлений пользователей"
3. Нажмите "Test Telegram" для проверки бота
4. Выберите пользователя и нажмите "Send test notification"

## Безопасность

### Токен бота

- Храните токен в переменных окружения
- Не коммитьте токен в git
- Регулярно ротируйте токены

### Chat ID

- Валидация формата Chat ID
- Проверка принадлежности пользователю
- Шифрование чувствительных данных

### Контроль доступа

- Роли и группы пользователей
- Ограничения по типам уведомлений
- Аудит всех действий

## Производственное развертывание

### Docker Compose

```yaml
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    
  celery_worker:
    build: .
    command: celery -A config worker -l info
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
      
  celery_beat:
    build: .
    command: celery -A config beat -l info
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
```

### Мониторинг в продакшене

- Prometheus метрики
- Grafana дашборды
- Алерты при сбоях
- Логирование в ELK/EFK

## FAQ

### Q: Бот не отвечает на сообщения
A: Проверьте:
- Корректность токена
- Активность бота
- Сетевое подключение
- Логи Celery

### Q: Уведомления не приходят
A: Проверьте:
- Chat ID пользователя
- Включены ли уведомления
- Статус Celery worker
- Логи отправки

### Q: Дублирование уведомлений
A: Возможные причины:
- Несколько воркеров Celery
- Повторные вызовы в коде
- Проблемы с Redis

### Q: Производительность
A: Оптимизация:
- Масштабирование воркеров
- Кэширование настроек
- Батчинг уведомлений
- Мониторинг очередей

## Развитие

### Планируемые функции

- [ ] WebApp интеграция
- [ ] Файловые уведомления  
- [ ] Групповые чаты
- [ ] Callback кнопки
- [ ] Интерактивные отчеты
- [ ] Голосовые уведомления
- [ ] Интеграция с другими мессенджерами

### Контрибьюция

1. Форкните репозиторий
2. Создайте feature branch
3. Добавьте тесты
4. Обновите документацию
5. Создайте Pull Request

---

*Последнее обновление: 2024-01-15*