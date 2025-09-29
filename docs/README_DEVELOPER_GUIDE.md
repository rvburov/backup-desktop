# Руководство разработчика Backup Application

## Содержание
1. [Установка для разработки](#установка-для-разработки)
2. [Архитектура проекта](#архитектура-проекта)
3. [Процесс сборки](#процесс-сборки)
4. [Тестирование](#тестирование)
5. [Вклад в проект](#вклад-в-проект)

## Установка для разработки

### Клонирование репозитория
```bash
git clone https://github.com/yourusername/backup-app.git
cd backup-app
```

### Создание виртуального окружения
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

### Установка зависимостей
```bash
pip install -r requirements.txt

# Или установка вручную
pip install PyQt5==5.15.9
```

### Запуск в режиме разработки
```bash
python backup_app.py
```

## Архитектура проекта

### Структура проекта
```bash
backup-app/
├── backup_app.py          # Основной класс приложения
├── main.py                # Точка входа
├── requirements.txt       # Зависимости
├── README.md
├── USER_GUIDE.md
└── DEVELOPER_GUIDE.md
```

### Ключевые классы

#### BackupApp (QMainWindow)
Главный класс приложения, отвечающий за:
- Управление интерфейсом
- Обработку событий
- Координацию компонентов
- Управление настройками

```python
class BackupApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("MyCompany", "BackupApp")
        self.init_ui()
        self.load_settings()
```

#### BackupWorker (QThread)
Класс для выполнения резервного копирования в отдельном потоке:
- Многопоточное копирование
- Отслеживание прогресса
- Безопасная отмена операции

```python
class BackupWorker(QThread):
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)
```

### Основные методы BackupApp

- `init_ui()` - инициализация пользовательского интерфейса
- `setup_custom_statusbar()` - создание статус-бара с прогрессом
- `start_backup_thread()` - запуск резервного копирования в потоке
- `calculate_total_backup_size()` - расчет общего размера файлов
- `load_settings()` / `save_settings()` - управление настройками
- `toggle_auto_start()` - управление автозапуском

### Модули и зависимости
- **PyQt5** - графический интерфейс
- **shutil** - операции с файлами
- **os/sys** - системные функции
- **platform** - определение платформы
- **datetime** - работа с датами и временем

### События и сигналы

#### Сигналы BackupWorker
- `progress_updated(int)` - обновление прогресса (0-100%)
- `status_updated(str)` - обновление статуса операции
- `finished_signal(bool, str)` - завершение операции (успех/ошибка, сообщение)

#### Таймеры и обработчики
- `backup_timer.timeout` - таймер проверки времени автоматического копирования
- `button.clicked` - обработка нажатий кнопок
- `comboBox.currentTextChanged` - изменение настроек

### Методы управления автозапуском

#### Кросс-платформенный автозапуск
```python
def toggle_auto_start(self, state):
    """Включает/выключает автозапуск при старте системы"""

def enable_auto_start(self) -> bool:
    """Добавляет приложение в автозагрузку"""

def disable_auto_start(self):
    """Удаляет приложение из автозагрузки"""
```

#### Платформенно-специфичные реализации
- `_enable_auto_start_windows()` - реализация для Windows
- `_enable_auto_start_linux()` - реализация для Linux  
- `_enable_auto_start_macos()` - реализация для macOS

## Процесс сборки

### Сборка с PyInstaller
```bash
pip install pyinstaller

# Сборка для Windows
pyinstaller --onefile --noconsole --icon=icon.ico --name="BackupApp" backup_app.py

# Сборка для Linux
pyinstaller --onefile --noconsole --name="BackupApp" backup_app.py

# Сборка для macOS
pyinstaller --onefile --noconsole --name="BackupApp" backup_app.py
```

### Конфигурация PyInstaller
Создайте файл `backup_app.spec`:
```python
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['backup_app.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='BackupApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
```

### Особенности сборки для разных платформ

#### Windows
```bash
pyinstaller --onefile --noconsole --icon=icon.ico --name="BackupApp" backup_app.py
```

#### Linux
```bash
pyinstaller --onefile --noconsole --name="BackupApp" backup_app.py
```

#### macOS
```bash
pyinstaller --onefile --noconsole --name="BackupApp" backup_app.py
```

## Тестирование

### Установка тестовых зависимостей
```bash
pip install pytest pytest-qt coverage pytest-cov
```

### Структура тестов
```
tests/
├── __init__.py
├── test_backup.py
├── test_ui.py
├── test_worker.py
└── conftest.py
```

### Запуск тестов
```bash
# Все тесты
pytest tests/

# С покрытием кода
pytest --cov=backup_app tests/

# Конкретный тест
pytest tests/test_backup.py::TestBackupApp::test_add_folder

# Тесты с выводом подробной информации
pytest -v tests/
```

### Примеры тестов

#### Тестирование UI
```python
# tests/test_ui.py
import pytest
from PyQt5.QtWidgets import QApplication
from backup_app import BackupApp

class TestBackupAppUI:
    @pytest.fixture
    def app(self):
        application = QApplication([])
        window = BackupApp()
        yield window
        application.quit()
    
    def test_initial_state(self, app):
        assert app.folders_list.count() == 0
        assert app.files_list.count() == 0
        assert app.dest_edit.text() == ""
    
    def test_add_folder(self, app):
        initial_count = app.folders_list.count()
        # Симуляция добавления папки через мок
        app.source_folders.append("/test/path")
        app.folders_list.addItem("/test/path")
        assert app.folders_list.count() == initial_count + 1
```

#### Тестирование логики резервного копирования
```python
# tests/test_backup.py
import pytest
import tempfile
import os
from backup_app import BackupWorker

class TestBackupWorker:
    def test_calculate_total_backup_size(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            # Создаем тестовые файлы
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, 'w') as f:
                f.write("test content")
            
            worker = BackupWorker([temp_dir], [], temp_dir, False, False, False)
            size = worker.calculate_total_backup_size()
            assert size > 0
    
    def test_backup_validation(self, app):
        # Тестируем проверку условий
        assert not app.validate_backup_conditions()
        
        # Добавляем тестовые данные и проверяем снова
        app.source_folders.append("/test/path")
        app.destination_folder = "/test/dest"
        # Мокаем os.path.exists чтобы возвращать True
        # ...
```

#### Тестирование автозапуска
```python
# tests/test_autostart.py
import pytest
from unittest.mock import patch, MagicMock

class TestAutoStart:
    @patch('platform.system')
    def test_auto_start_windows(self, mock_system):
        mock_system.return_value = 'Windows'
        # Тестируем логику автозапуска для Windows
        # ...
```

### Интеграционное тестирование

#### GitHub Actions
```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: [3.8, 3.9, 3.10]
    
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-qt coverage pytest-cov
    
    - name: Run tests
      run: pytest --cov=backup_app tests/
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

## Вклад в проект

### Процесс разработки
1. Форкните репозиторий
2. Создайте feature-ветку: `git checkout -b feature/amazing-feature`
3. Закоммитьте изменения: `git commit -m 'Add amazing feature'`
4. Запушьте ветку: `git push origin feature/amazing-feature`
5. Откройте Pull Request

### Стандарты кода
- Соблюдайте PEP8
- Документируйте публичные методы с использованием docstrings
- Пишите тесты для новой функциональности
- Обновляйте документацию
- Используйте type hints для аргументов и возвращаемых значений

### Структура коммитов
```
feat: добавление новой функциональности
fix: исправление ошибки
docs: обновление документации
test: добавление тестов
refactor: рефакторинг кода без изменения функциональности
style: исправление форматирования (пробелы, запятые и т.д.)
perf: изменения улучшающие производительность
```

### Code Review процесс
1. Проверка соответствия стандартам кодирования
2. Тестирование функциональности на разных платформах
3. Проверка документации и комментариев
4. Проверка покрытия тестами
5. Одобрение двумя участниками проекта

### Особенности разработки для разных платформ

#### Windows
- Используйте обратные слеши в путях
- Учитывайте ограничения длины путей
- Тестируйте работу с автозапуском через реестр

#### Linux
- Используйте прямые слеши в путях
- Учитывайте права доступа к файлам
- Тестируйте работу с .desktop файлами

#### macOS
- Учитывайте sandbox ограничения
- Тестируйте работу с LaunchAgents
- Проверяйте совместимость с разными версиями macOS

### Отладка и диагностика

#### Включение отладочного режима
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### Мониторинг использования памяти
```python
import psutil
process = psutil.Process()
memory_info = process.memory_info()
```
