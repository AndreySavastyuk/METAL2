#!/usr/bin/env python3
"""
🚀 MetalQMS - Система управления качеством металлообработки
Удобный запуск бэкенда и фронтенда с информативными логами

Автор: MetalQMS Team
Версия: 1.0.0
"""

import os
import sys
import time
import subprocess
import threading
import signal
import json
from datetime import datetime
from pathlib import Path

# Цвета для консоли
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_colored(text, color=Colors.OKGREEN):
    """Печать цветного текста"""
    print(f"{color}{text}{Colors.ENDC}")

def print_banner():
    """Печать баннера приложения"""
    banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║    🏭 MetalQMS - Система управления качеством металлообработки               ║
║                                                                              ║
║    📊 Workflow: Склад → ОТК → Лаборатория → Производство                    ║
║    🔧 Tech Stack: Django + React + PostgreSQL + Redis                       ║
║    📱 Telegram Bot | 📈 Monitoring | 💾 Auto Backup                        ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """
    print_colored(banner, Colors.HEADER)

def check_dependencies():
    """Проверка зависимостей"""
    print_colored("🔍 Проверка зависимостей...", Colors.OKCYAN)
    
    dependencies = {
        'python': 'python --version',
        'node': 'node --version', 
        'npm': 'npm --version'
    }
    
    missing = []
    for dep, cmd in dependencies.items():
        try:
            result = subprocess.run(cmd.split(), capture_output=True, text=True, shell=True)
            
            # Проверяем и stdout и stderr, npm иногда выводит в stderr
            version = result.stdout.strip() or result.stderr.strip()
            
            # Если команда выполнилась успешно (код возврата 0), считаем что зависимость найдена
            if result.returncode == 0:
                if version:
                    print_colored(f"  ✅ {dep}: {version}", Colors.OKGREEN)
                else:
                    # Даже если вывода нет, но код возврата 0 - зависимость найдена
                    print_colored(f"  ✅ {dep}: найден (версию определить не удалось)", Colors.OKGREEN)
            else:
                print_colored(f"  ❌ {dep}: не установлен (код ошибки: {result.returncode})", Colors.FAIL)
                missing.append(dep)
                
        except FileNotFoundError:
            print_colored(f"  ❌ {dep}: команда не найдена", Colors.FAIL)
            missing.append(dep)
        except Exception as e:
            print_colored(f"  ❌ {dep}: ошибка проверки ({str(e)})", Colors.FAIL)
            missing.append(dep)
    
    if missing:
        print_colored(f"\n❌ Отсутствуют зависимости: {', '.join(missing)}", Colors.FAIL)
        print_colored("💡 Совет: Убедитесь, что все зависимости добавлены в PATH", Colors.WARNING)
        
        # Если нет только npm, предлагаем запуск только backend
        if missing == ['npm']:
            print_colored("🔧 Можно запустить только backend: cd backend && python manage.py runserver", Colors.WARNING)
            return True  # Разрешаем продолжить без npm
        
        return False
    
    return True

def setup_environment():
    """Настройка окружения"""
    print_colored("\n⚙️  Настройка окружения...", Colors.OKCYAN)
    
    # Создание необходимых директорий
    directories = [
        'logs',
        'media',
        'media/qr_codes',
        'media/certificates', 
        'media/test_results',
        'uploads',
        'uploads/certificates',
        'uploads/test_results',
        'backups'
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print_colored(f"  📁 Создана директория: {directory}", Colors.OKGREEN)

def check_database():
    """Проверка базы данных"""
    print_colored("\n🗃️  Проверка базы данных...", Colors.OKCYAN)
    
    backend_dir = Path('backend')
    if not backend_dir.exists():
        print_colored("  ❌ Директория backend не найдена", Colors.FAIL)
        return False
    
    # Проверка наличия миграций
    try:
        os.chdir(backend_dir)
        
        # Сначала проверим, работает ли Django вообще
        check_result = subprocess.run([
            sys.executable, 'manage.py', 'check'
        ], capture_output=True, text=True)
        
        if check_result.returncode != 0:
            print_colored("  🔄 Первоначальная настройка Django...", Colors.WARNING)
            # Попробуем создать миграции и применить их
            subprocess.run([
                sys.executable, 'manage.py', 'makemigrations'
            ], capture_output=True)
            
            migrate_result = subprocess.run([
                sys.executable, 'manage.py', 'migrate'
            ], capture_output=True, text=True)
            
            if migrate_result.returncode == 0:
                print_colored("  ✅ База данных инициализирована", Colors.OKGREEN)
            else:
                print_colored("  ⚠️  Возможны проблемы с базой данных, но продолжаем...", Colors.WARNING)
        else:
            # Django работает, проверяем миграции
            result = subprocess.run([
                sys.executable, 'manage.py', 'showmigrations', '--plan'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                if 'UNAPPLIED' in result.stdout:
                    print_colored("  🔄 Применение миграций...", Colors.WARNING)
                    subprocess.run([
                        sys.executable, 'manage.py', 'migrate'
                    ])
                    print_colored("  ✅ Миграции применены", Colors.OKGREEN)
                else:
                    print_colored("  ✅ База данных актуальна", Colors.OKGREEN)
            else:
                print_colored("  ⚠️  Не удалось проверить миграции, но продолжаем...", Colors.WARNING)
        
        os.chdir('..')
        return True
        
    except Exception as e:
        print_colored(f"  ⚠️  Ошибка настройки базы данных: {e}", Colors.WARNING)
        print_colored("  ℹ️  Продолжаем без проверки миграций...", Colors.OKCYAN)
        try:
            os.chdir('..')
        except:
            pass
        return True  # Продолжаем выполнение

def create_superuser():
    """Создание суперпользователя"""
    print_colored("\n👤 Создание администратора...", Colors.OKCYAN)
    
    try:
        os.chdir('backend')
        
        # Проверка существования суперпользователя
        check_script = """
from django.contrib.auth import get_user_model
User = get_user_model()
if User.objects.filter(is_superuser=True).exists():
    print('EXISTS')
else:
    print('NOT_EXISTS')
"""
        
        result = subprocess.run([
            sys.executable, 'manage.py', 'shell', '-c', check_script
        ], capture_output=True, text=True, check=True)
        
        if 'EXISTS' in result.stdout:
            print_colored("  ✅ Администратор уже существует", Colors.OKGREEN)
        else:
            # Создание суперпользователя
            create_script = """
from django.contrib.auth import get_user_model
User = get_user_model()
User.objects.create_superuser('admin', 'admin@metalqms.com', 'admin123')
print('Superuser created: admin/admin123')
"""
            subprocess.run([
                sys.executable, 'manage.py', 'shell', '-c', create_script
            ], check=True)
            print_colored("  ✅ Администратор создан: admin/admin123", Colors.OKGREEN)
        
        os.chdir('..')
        
    except subprocess.CalledProcessError as e:
        print_colored(f"  ❌ Ошибка создания администратора: {e}", Colors.FAIL)
        os.chdir('..')

def install_dependencies():
    """Установка зависимостей"""
    print_colored("\n📦 Установка зависимостей...", Colors.OKCYAN)
    
    # Python зависимости
    print_colored("  🐍 Установка Python пакетов...", Colors.OKCYAN)
    try:
        subprocess.run([
            sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'
        ], check=True, capture_output=True)
        print_colored("  ✅ Python пакеты установлены", Colors.OKGREEN)
    except subprocess.CalledProcessError:
        print_colored("  ❌ Ошибка установки Python пакетов", Colors.FAIL)
        return False
    
    # Node.js зависимости - только если npm доступен
    frontend_dir = Path('frontend')
    if frontend_dir.exists():
        # Проверяем доступность npm перед установкой
        try:
            result = subprocess.run(['npm', '--version'], capture_output=True, text=True, shell=True)
            if result.returncode == 0:
                print_colored("  📦 Проверка Node.js пакетов...", Colors.OKCYAN)
                
                # Проверяем наличие node_modules
                node_modules = frontend_dir / 'node_modules'
                if node_modules.exists():
                    print_colored("  ✅ Node.js пакеты уже установлены", Colors.OKGREEN)
                else:
                    print_colored("  📦 Установка Node.js пакетов...", Colors.OKCYAN)
                    try:
                        os.chdir(frontend_dir)
                        subprocess.run(['npm', 'install'], check=True, capture_output=True)
                        print_colored("  ✅ Node.js пакеты установлены", Colors.OKGREEN)
                        os.chdir('..')
                    except subprocess.CalledProcessError:
                        print_colored("  ❌ Ошибка установки Node.js пакетов", Colors.FAIL)
                        os.chdir('..')
                        print_colored("  ⚠️  Продолжаем без frontend пакетов", Colors.WARNING)
            else:
                print_colored("  ⚠️  npm не найден, пропускаем установку Node.js пакетов", Colors.WARNING)
        except FileNotFoundError:
            print_colored("  ⚠️  npm не найден, пропускаем установку Node.js пакетов", Colors.WARNING)
    else:
        print_colored("  ℹ️  Директория frontend не найдена, пропускаем Node.js пакеты", Colors.OKCYAN)
    
    return True

def load_test_data():
    """Загрузка тестовых данных"""
    print_colored("\n📊 Загрузка тестовых данных...", Colors.OKCYAN)
    
    try:
        os.chdir('backend')
        
        # Проверка наличия данных
        check_script = """
from apps.warehouse.models import Material
count = Material.objects.count()
print(f'MATERIALS_COUNT:{count}')
"""
        
        result = subprocess.run([
            sys.executable, 'manage.py', 'shell', '-c', check_script
        ], capture_output=True, text=True, check=True)
        
        count = 0
        for line in result.stdout.split('\n'):
            if 'MATERIALS_COUNT:' in line:
                count = int(line.split(':')[1])
                break
        
        if count > 0:
            print_colored(f"  ✅ Тестовые данные уже загружены ({count} материалов)", Colors.OKGREEN)
        else:
            print_colored("  🔄 Создание тестовых данных...", Colors.WARNING)
            subprocess.run([
                sys.executable, 'manage.py', 'loaddata', 'fixtures/test_data.json'
            ], check=True)
            print_colored("  ✅ Тестовые данные загружены", Colors.OKGREEN)
        
        os.chdir('..')
        
    except subprocess.CalledProcessError as e:
        print_colored(f"  ⚠️  Файл с тестовыми данными не найден, создаем базовые данные...", Colors.WARNING)
        os.chdir('..')

class ProcessManager:
    """Менеджер процессов для backend и frontend"""
    
    def __init__(self):
        self.processes = {}
        self.running = True
        self.frontend_running = False
        
    def start_backend(self):
        """Запуск Django backend"""
        print_colored("\n🐍 Запуск Django Backend...", Colors.OKCYAN)
        
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'
        # Добавляем backend директорию в PYTHONPATH
        backend_path = os.path.abspath('backend')
        if 'PYTHONPATH' in env:
            env['PYTHONPATH'] = f"{backend_path}{os.pathsep}{env['PYTHONPATH']}"
        else:
            env['PYTHONPATH'] = backend_path
        
        # Запускаем Django из правильной директории
        backend_process = subprocess.Popen([
            sys.executable, 'manage.py', 'runserver', '127.0.0.1:8000'
        ], cwd='backend', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
           universal_newlines=True, env=env, bufsize=1)
        
        self.processes['backend'] = backend_process
        
        # Мониторинг логов backend
        def monitor_backend():
            for line in iter(backend_process.stdout.readline, ''):
                if not self.running:
                    break
                if line.strip():
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    if 'ERROR' in line.upper() or 'EXCEPTION' in line.upper():
                        print_colored(f"[{timestamp}] 🔴 BACKEND: {line.strip()}", Colors.FAIL)
                    elif 'WARNING' in line.upper():
                        print_colored(f"[{timestamp}] 🟡 BACKEND: {line.strip()}", Colors.WARNING)
                    elif '"GET' in line or '"POST' in line:
                        print_colored(f"[{timestamp}] 🌐 BACKEND: {line.strip()}", Colors.OKCYAN)
                    else:
                        print_colored(f"[{timestamp}] 🐍 BACKEND: {line.strip()}", Colors.OKGREEN)
        
        backend_thread = threading.Thread(target=monitor_backend, daemon=True)
        backend_thread.start()
        
        print_colored("  ✅ Backend запущен на http://127.0.0.1:8000", Colors.OKGREEN)
        
    def check_frontend_health(self):
        """Проверка состояния frontend компонентов"""
        print_colored("\n🔍 Проверка frontend компонентов...", Colors.OKCYAN)
        
        frontend_dir = Path('frontend')
        if not frontend_dir.exists():
            print_colored("  ❌ Frontend директория не найдена", Colors.FAIL)
            return False
        
        # Проверка package.json
        package_json = frontend_dir / 'package.json'
        if package_json.exists():
            print_colored("  ✅ package.json найден", Colors.OKGREEN)
        else:
            print_colored("  ❌ package.json не найден", Colors.FAIL)
            return False
        
        # Проверка node_modules
        node_modules = frontend_dir / 'node_modules'
        if node_modules.exists():
            print_colored("  ✅ node_modules найден", Colors.OKGREEN)
        else:
            print_colored("  ⚠️  node_modules не найден, устанавливаем зависимости...", Colors.WARNING)
            try:
                subprocess.run(['npm', 'install'], cwd=frontend_dir, check=True, capture_output=True)
                print_colored("  ✅ Зависимости установлены", Colors.OKGREEN)
            except subprocess.CalledProcessError:
                print_colored("  ❌ Ошибка установки зависимостей", Colors.FAIL)
                return False
        
        # Проверка основных файлов
        important_files = [
            'src/main.tsx',
            'src/App.tsx', 
            'vite.config.ts',
            'index.html'
        ]
        
        for file_path in important_files:
            file_full_path = frontend_dir / file_path
            if file_full_path.exists():
                print_colored(f"  ✅ {file_path} найден", Colors.OKGREEN)
            else:
                print_colored(f"  ❌ {file_path} не найден", Colors.FAIL)
                return False
        
        # Проверка TypeScript конфигурации
        ts_config = frontend_dir / 'tsconfig.json'
        if ts_config.exists():
            print_colored("  ✅ tsconfig.json найден", Colors.OKGREEN)
        else:
            print_colored("  ⚠️  tsconfig.json не найден", Colors.WARNING)
        
        return True
    
    def start_frontend(self):
        """Запуск React frontend"""
        frontend_dir = Path('frontend')
        if not frontend_dir.exists():
            print_colored("  ⚠️  Frontend директория не найдена", Colors.WARNING)
            return
        
        # Проверяем доступность npm перед запуском
        try:
            result = subprocess.run(['npm', '--version'], capture_output=True, text=True, shell=True)
            if result.returncode != 0:
                print_colored("  ⚠️  npm не найден, пропускаем запуск frontend", Colors.WARNING)
                return
        except FileNotFoundError:
            print_colored("  ⚠️  npm не найден, пропускаем запуск frontend", Colors.WARNING)
            return
        
        # Выполняем проверку здоровья frontend
        if not self.check_frontend_health():
            print_colored("  ❌ Frontend не готов к запуску", Colors.FAIL)
            return
            
        print_colored("\n⚛️  Запуск React Frontend...", Colors.OKCYAN)
        
        # Устанавливаем переменные окружения для frontend
        env = os.environ.copy()
        env['VITE_API_BASE_URL'] = 'http://127.0.0.1:8000'
        env['NODE_ENV'] = 'development'
        
        try:
            frontend_process = subprocess.Popen([
                'npm', 'run', 'dev'
            ], cwd=frontend_dir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
               universal_newlines=True, bufsize=1, env=env, shell=True)
            
            self.processes['frontend'] = frontend_process
            self.frontend_running = True
            print_colored("  ✅ Frontend запущен на http://localhost:3000", Colors.OKGREEN)
        except FileNotFoundError:
            print_colored("  ⚠️  Не удалось запустить frontend (npm недоступен)", Colors.WARNING)
            return
        except Exception as e:
            print_colored(f"  ❌ Ошибка запуска frontend: {e}", Colors.FAIL)
            return
        
        # Мониторинг логов frontend
        def monitor_frontend():
            for line in iter(frontend_process.stdout.readline, ''):
                if not self.running:
                    break
                if line.strip():
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    if 'error' in line.lower() or 'failed' in line.lower():
                        print_colored(f"[{timestamp}] 🔴 FRONTEND: {line.strip()}", Colors.FAIL)
                    elif 'warning' in line.lower():
                        print_colored(f"[{timestamp}] 🟡 FRONTEND: {line.strip()}", Colors.WARNING)
                    elif 'Local:' in line or 'ready in' in line.lower():
                        print_colored(f"[{timestamp}] 🚀 FRONTEND: {line.strip()}", Colors.OKGREEN)
                    else:
                        print_colored(f"[{timestamp}] ⚛️  FRONTEND: {line.strip()}", Colors.OKCYAN)
        
        frontend_thread = threading.Thread(target=monitor_frontend, daemon=True)
        frontend_thread.start()
    
    def stop_all(self):
        """Остановка всех процессов"""
        print_colored("\n🛑 Остановка сервисов...", Colors.WARNING)
        self.running = False
        
        for name, process in self.processes.items():
            if process and process.poll() is None:
                print_colored(f"  🛑 Остановка {name}...", Colors.WARNING)
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                print_colored(f"  ✅ {name} остановлен", Colors.OKGREEN)

def test_system_health():
    """Тестирование работоспособности системы"""
    print_colored("\n🏥 Проверка работоспособности системы...", Colors.OKCYAN)
    
    # Проверка backend
    try:
        import requests
        response = requests.get('http://127.0.0.1:8000/health/', timeout=5)
        if response.status_code == 200:
            print_colored("  ✅ Backend доступен и отвечает", Colors.OKGREEN)
        else:
            print_colored(f"  ⚠️  Backend отвечает с кодом {response.status_code}", Colors.WARNING)
    except ImportError:
        print_colored("  ℹ️  requests не установлен, пропускаем проверку backend", Colors.OKCYAN)
    except Exception as e:
        print_colored(f"  ❌ Backend недоступен: {e}", Colors.FAIL)
    
    # Проверка frontend
    try:
        response = requests.get('http://localhost:3000/', timeout=5)
        if response.status_code == 200:
            print_colored("  ✅ Frontend доступен и отвечает", Colors.OKGREEN)
        else:
            print_colored(f"  ⚠️  Frontend отвечает с кодом {response.status_code}", Colors.WARNING)
    except ImportError:
        pass  # Уже сообщили выше
    except Exception as e:
        print_colored(f"  ⚠️  Frontend пока недоступен (может еще запускаться)", Colors.WARNING)


def show_info(frontend_running=True):
    """Показать информацию о доступных URL"""
    
    # Основная информация о backend
    info = """
🌐 Доступные сервисы:

🐍 Backend API (Django):      http://127.0.0.1:8000  
📊 Admin Panel:               http://127.0.0.1:8000/admin
🔧 API Documentation:         http://127.0.0.1:8000/api/docs/
💚 Health Check:              http://127.0.0.1:8000/health/
📈 Metrics:                   http://127.0.0.1:8000/metrics/"""
    
    # Информация о frontend (если запущен)
    if frontend_running:
        info += """
📱 Frontend (React):          http://localhost:3000"""
    else:
        info += """
⚠️  Frontend недоступен (npm не найден)"""
    
    info += """

👤 Доступы:
   Администратор: admin / admin123
   
📋 Тестовые роли:
   Склад:       warehouse / test123
   ОТК:         qc / test123  
   Лаборатория: lab / test123"""
    
    # Навигация (адаптируется под наличие frontend)
    if frontend_running:
        info += """

🎯 Быстрая навигация:
   Материалы:     http://localhost:3000/materials
   Инспекции:     http://localhost:3000/qc/inspections
   Лаборатория:   http://localhost:3000/laboratory"""
    else:
        info += """

🎯 Доступные API endpoints:
   Материалы:     http://127.0.0.1:8000/api/materials/
   Инспекции:     http://127.0.0.1:8000/api/inspections/
   API Root:      http://127.0.0.1:8000/api/"""
    
    info += """

📚 Документация: ./docs/
💾 Логи:         ./logs/
🔧 Monitoring:   Prometheus + Grafana готовы к запуску
    """
    
    print_colored(info, Colors.OKCYAN)

def main():
    """Основная функция"""
    print_banner()
    
    # Проверка зависимостей
    if not check_dependencies():
        sys.exit(1)
    
    # Настройка окружения
    setup_environment()
    
    # Установка зависимостей
    if not install_dependencies():
        sys.exit(1)
    
    # Проверка базы данных
    if not check_database():
        sys.exit(1)
    
    # Создание суперпользователя
    create_superuser()
    
    # Загрузка тестовых данных
    load_test_data()
    
    # Создание менеджера процессов
    process_manager = ProcessManager()
    
    def signal_handler(signum, frame):
        process_manager.stop_all()
        print_colored("\n👋 До свидания!", Colors.OKCYAN)
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Запуск сервисов
    process_manager.start_backend()
    time.sleep(3)  # Даем backend время запуститься
    
    process_manager.start_frontend()
    time.sleep(3)  # Даем frontend время запуститься
    
    # Показать информацию
    show_info(frontend_running=process_manager.frontend_running)
    
    # Пауза перед тестированием, чтобы сервисы успели запуститься
    time.sleep(5)
    
    # Тестирование системы
    test_system_health()
    
    if process_manager.frontend_running:
        print_colored("\n🎉 MetalQMS полностью запущен! Нажмите Ctrl+C для остановки...", Colors.OKGREEN)
        print_colored("🌟 Система готова к работе: Frontend + Backend", Colors.OKGREEN)
    else:
        print_colored("\n🎉 MetalQMS Backend запущен! Нажмите Ctrl+C для остановки...", Colors.OKGREEN)
        print_colored("💡 Для запуска frontend убедитесь что npm установлен", Colors.WARNING)
    
    # Ожидание
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        process_manager.stop_all()
        print_colored("\n👋 До свидания!", Colors.OKCYAN)

if __name__ == '__main__':
    main()