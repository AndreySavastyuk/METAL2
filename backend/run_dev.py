#!/usr/bin/env python3
"""
🚀 Быстрый запуск MetalQMS в режиме разработки
Альтернативный вариант с минимальными проверками
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Быстрый запуск для разработки"""
    print("🚀 Быстрый запуск MetalQMS...")
    
    # Переход в директорию backend
    backend_dir = Path('backend')
    if not backend_dir.exists():
        print("❌ Директория backend не найдена")
        return
    
    os.chdir(backend_dir)
    
    # Запуск Django сервера
    print("🐍 Запуск Django сервера на http://127.0.0.1:8000...")
    subprocess.run([sys.executable, 'manage.py', 'runserver', '127.0.0.1:8000'])

if __name__ == '__main__':
    main()