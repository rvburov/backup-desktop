# Руководство разработчика Backup Application

## Содержание
1. [Установка для разработки](#установка-для-разработки)
2. [Архитектура проекта](#архитектура-проекта)
3. [API документация](#api-документация)
4. [Процесс сборки](#процесс-сборки)
5. [Тестирование](#тестирование)
6. [Вклад в проект](#вклад-в-проект)

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
python backup_app.py --debug
```

## Архитектура проекта

### Структура проекта
```bash
backup-app/
├── backup-app.py          # Основной класс приложения
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

```python
class BackupApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("MyCompany", "BackupApp")
        self.init_ui()
        self.load_settings()
```

#### Основные методы BackupApp
- `init_ui()` - инициализация интерфейса
- `setup_custom_statusbar()` - создание статус-бара
- `perform_backup()` - выполнение резервного копирования
- `calculate_next_backup_time()` - расчет времени следующего копирования

### Модули и зависимости
- **PyQt5** - графический интерфейс
- **shutil** - операции с файлами
- **os/sys** - системные функции
- **platform** - определение платформы

## API документация

### Основные публичные методы

#### `add_folder()`
Добавляет папку в список для копирования
```python
def add_folder(self):
    """Добавление папки в список для резервного копирования"""
```

#### `perform_backup()`
Выполняет резервное копирование
```python
def perform_backup(self):
    """Основной метод выполнения резервного копирования"""
```

#### `calculate_total_backup_size()`
Рассчитывает общий размер файлов для копирования
```python
def calculate_total_backup_size(self) -> int:
    """Возвращает общий размер в байтах"""
```

### События и сигналы
- `backup_timer.timeout` - таймер проверки времени копирования
- `button.clicked` - обработка нажатий кнопок
- `comboBox.currentTextChanged` - изменение настроек

## Процесс сборки

### Сборка с PyInstaller
```bash
pip install pyinstaller

# Сборка для Windows
pyinstaller --onefile --noconsole --icon=icon.ico --name="Backup" backup_app.py

# Сборка для Linux
pyinstaller --onefile --noconsole --name="Backup" backup_app.py

# Сборка для macOS
pyinstaller --onefile --noconsole --name="Backup" backup_app.py
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

### Кросс-платформенная сборка
Для сборки под разные платформы используйте соответствующие окружения:
- **Windows**: Visual Studio Build Tools
- **Linux**: GCC, glibc
- **macOS**: Xcode Command Line Tools

## Тестирование

### Установка тестовых зависимостей
```bash
pip install pytest pytest-qt coverage
```

### Запуск тестов
```bash
# Все тесты
pytest tests/

# С покрытием кода
coverage run -m pytest tests/
coverage report -m

# Конкретный тест
pytest tests/test_backup.py::TestBackupApp::test_add_folder
```

### Пример теста
```python
# tests/test_backup.py
import pytest
from PyQt5.QtWidgets import QApplication
from backup_app import BackupApp

class TestBackupApp:
    @pytest.fixture
    def app(self):
        application = QApplication([])
        window = BackupApp()
        yield window
        application.quit()
    
    def test_add_folder(self, app):
        initial_count = app.folders_list.count()
        app.add_folder()  # Симулируем добавление
        assert app.folders_list.count() == initial_count + 1
    
    def test_backup_size_calculation(self, app):
        size = app.calculate_total_backup_size()
        assert isinstance(size, int)
        assert size >= 0
```

### Тестирование на разных платформах
Используйте GitHub Actions для автоматического тестирования:
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
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-qt
    
    - name: Run tests
      run: pytest tests/
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
- Документируйте публичные методы
- Пишите тесты для новой функциональности
- Обновляйте документацию

### Структура коммитов
```
feat: добавление новой функциональности
fix: исправление ошибки
docs: обновление документации
test: добавление тестов
refactor: рефакторинг кода
```

### Code Review процесс
1. Проверка соответствия стандартам
2. Тестирование функциональности
3. Проверка документации
4. Одобрение двумя участниками
