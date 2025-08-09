# Правила работы с Git репозиторием MetalQMS

## 🔧 Настройка рабочей среды

### Первоначальная настройка

```bash
# Клонирование репозитория
git clone https://github.com/AndreySavastyuk/METAL2.git
cd METAL2

# Настройка git
git config user.name "Ваше Имя"
git config user.email "your.email@example.com"

# Автоматический запуск системы
python start_metalqms.py
```

## 📋 Правила коммитов

### Формат коммитов (Conventional Commits)

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Типы коммитов

- **feat**: новая функциональность
- **fix**: исправление ошибки
- **docs**: изменения в документации
- **style**: форматирование, отсутствующие точки с запятой и т.д.
- **refactor**: рефакторинг кода
- **test**: добавление тестов
- **chore**: обновление задач сборки, настроек менеджера пакетов и т.д.

### Примеры коммитов

```bash
# Новая функция
git commit -m "feat(warehouse): add QR code generation for materials"

# Исправление ошибки
git commit -m "fix(api): resolve CORS issue in production"

# Документация
git commit -m "docs(readme): update installation instructions"

# Рефакторинг
git commit -m "refactor(quality): optimize inspection workflow logic"
```

## 🌿 Работа с ветками

### Стратегия ветвления

- **main** - стабильная production-готовая версия
- **develop** - основная ветка разработки
- **feature/*** - новые функции
- **hotfix/*** - критические исправления
- **release/*** - подготовка релизов

### Создание веток

```bash
# Создание feature ветки
git checkout -b feature/material-inspection-improvements
git checkout -b feature/telegram-notifications-enhancement

# Создание hotfix ветки
git checkout -b hotfix/critical-security-fix

# Создание release ветки
git checkout -b release/v1.2.0
```

## 🔍 Перед коммитом

### Обязательные проверки

1. **Запуск тестов**
```bash
cd backend
python manage.py test
cd ../frontend
npm test
```

2. **Проверка линтеров**
```bash
# Backend
cd backend
python manage.py check
flake8 apps/

# Frontend
cd frontend
npm run lint
```

3. **Проверка безопасности**
```bash
# Проверка на секреты в коде
git secrets --scan

# Проверка зависимостей
pip-audit
npm audit
```

## 🚀 Деплой правила

### Staging окружение

```bash
# Пуш в staging ветку
git push origin develop

# Автоматический деплой через GitHub Actions
# Доступ: https://staging.metalqms.local
```

### Production деплой

```bash
# Создание тега релиза
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0

# Пуш в main для production
git checkout main
git merge develop
git push origin main
```

## 📦 Управление зависимостями

### Python зависимости

```bash
# Добавление новой зависимости
pip install новый-пакет
pip freeze > requirements.txt

# Коммит изменений
git add requirements.txt
git commit -m "feat(deps): add новый-пакет for enhanced functionality"
```

### Node.js зависимости

```bash
# Добавление новой зависимости
cd frontend
npm install новый-пакет
# package.json и package-lock.json обновятся автоматически

git add package*.json
git commit -m "feat(frontend): add новый-пакет for UI improvements"
```

## 🔐 Безопасность

### Что НИКОГДА не коммитить

- ❌ Пароли и API ключи
- ❌ Файлы `.env` с реальными данными
- ❌ База данных SQLite (`metalqms.db`)
- ❌ Директории `node_modules/`, `__pycache__/`
- ❌ Персональные конфигурации IDE
- ❌ Логи и временные файлы

### Файлы для проверки перед коммитом

```bash
# Проверка на секреты
git diff --cached | grep -E "(password|secret|key|token)" --color=always

# Проверка .env файлов
git status | grep -E "\.env"
```

## 🧪 Тестирование

### Перед каждым Pull Request

```bash
# Полная проверка системы
python start_metalqms.py

# Ждем успешного запуска обоих сервисов
# Проверяем основные страницы:
# - http://localhost:3000 (frontend)
# - http://127.0.0.1:8000/admin (backend admin)
# - http://127.0.0.1:8000/api/docs/ (API docs)
```

### Автоматические тесты

```bash
# Backend тесты
cd backend
python -m pytest tests/ -v --cov=apps

# Frontend тесты
cd frontend
npm run test:ci
npm run build  # Проверка сборки
```

## 📝 Pull Request правила

### Шаблон PR

```markdown
## Описание изменений
Краткое описание того, что изменено

## Тип изменения
- [ ] Новая функция (feature)
- [ ] Исправление ошибки (bugfix)
- [ ] Критическое исправление (hotfix)
- [ ] Документация
- [ ] Рефакторинг

## Проверочный список
- [ ] Код протестирован локально
- [ ] Добавлены/обновлены тесты
- [ ] Документация обновлена
- [ ] Нет конфликтов с main веткой
- [ ] start_metalqms.py запускается без ошибок

## Скриншоты (если применимо)
Добавить скриншоты новой функциональности

## Связанные задачи
Closes #123
```

### Процесс ревью

1. Автоматические проверки (CI/CD)
2. Ревью кода (минимум 1 человек)
3. Тестирование функциональности
4. Merge в develop/main

## 🚨 Экстренные процедуры

### Откат изменений

```bash
# Откат последнего коммита
git revert HEAD

# Откат к конкретному коммиту
git revert <commit-hash>

# Силовой откат (ОСТОРОЖНО!)
git reset --hard HEAD~1
```

### Исправление конфликтов

```bash
# При конфликте слияния
git status
# Редактируем конфликтующие файлы
git add .
git commit -m "fix: resolve merge conflicts"
```

## 📊 Мониторинг репозитория

### Полезные команды

```bash
# История коммитов
git log --oneline --graph

# Статистика по авторам
git shortlog -s -n

# Изменения в файлах
git diff --stat

# Размер репозитория
git count-objects -vH
```

---

**Помните**: Хороший коммит - это небольшой, логически завершенный коммит с понятным описанием! 🎯
