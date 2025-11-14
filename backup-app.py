import sys
import os
import shutil
import platform
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QFileDialog, QTextEdit, QSpinBox, QComboBox,
                             QGroupBox, QMessageBox, QCheckBox, QTimeEdit, 
                             QGridLayout, QListWidget, QTabWidget,
                             QSizePolicy, QProgressBar, QStackedWidget, 
                             QToolBar, QAction, QFrame, QTabBar)
from PyQt5.QtCore import QTimer, Qt, QTime, QSettings, QSize
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor
from PyQt5.QtCore import QThread, pyqtSignal


class BackupWorker(QThread):
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, source_folders, source_files, destination_folder, 
                 copy_folder_contents, keep_history, create_backup_folder):
        super().__init__()
        self.source_folders = source_folders
        self.source_files = source_files
        self.destination_folder = destination_folder
        self.copy_folder_contents = copy_folder_contents
        self.keep_history = keep_history
        self.create_backup_folder = create_backup_folder
        self.cancelled = False
        self.total_size = 0

    def cancel(self):
        self.cancelled = True

    def run(self):
        try:
            if self.total_size == 0:
                self.total_size = self.calculate_total_backup_size()
            
            if self.total_size == 0:
                self.finished_signal.emit(False, "Нет файлов для копирования")
                return
                
            self.status_updated.emit(f"Начинаем копирование ({self.total_size/1024/1024:.1f} MB)")
            
            success, message = self.perform_backup_safe()
            self.finished_signal.emit(success, message)
            
        except Exception as e:
            self.finished_signal.emit(False, f"Ошибка: {str(e)}")

    def calculate_total_backup_size(self):
        total_size = 0
        for folder_path in self.source_folders:
            if os.path.isdir(folder_path) and not self.cancelled:
                try:
                    for root, dirs, files in os.walk(folder_path):
                        for file in files:
                            if self.cancelled:
                                return total_size
                            file_path = os.path.join(root, file)
                            if os.path.exists(file_path):
                                total_size += os.path.getsize(file_path)
                except OSError:
                    continue
        
        for file_path in self.source_files:
            if not self.cancelled and os.path.isfile(file_path) and os.path.exists(file_path):
                total_size += os.path.getsize(file_path)
        
        return total_size

    def perform_backup_safe(self):
        """БЕЗОПАСНОЕ выполнение резервного копирования БЕЗ удаления каких-либо файлов"""
        if self.cancelled:
            return False, "Операция отменена"

        try:
            if not self.check_disk_space(self.total_size):
                return False, "Недостаточно свободного места"

            actual_destination = self.destination_folder
            if self.create_backup_folder:
                current_date = datetime.now().strftime("%d-%m-%Y")
                backup_folder_name = f"Резервное копирование {current_date}"
                actual_destination = os.path.join(self.destination_folder, backup_folder_name)
                if not os.path.exists(actual_destination):
                    os.makedirs(actual_destination)

            copied_count = 0
            copied_size = 0

            # Копируем папки (БЕЗОПАСНО)
            for folder_path in self.source_folders:
                if self.cancelled:
                    return False, "Операция отменена"
                    
                if not os.path.exists(folder_path):
                    continue

                try:
                    if self.copy_folder_contents:
                        # Безопасное копирование содержимого папки
                        for root, dirs, files in os.walk(folder_path):
                            for file in files:
                                if self.cancelled:
                                    return False, "Операция отменена"
                                    
                                source_file_path = os.path.join(root, file)
                                rel_path = os.path.relpath(source_file_path, folder_path)
                                dest_file_path = os.path.join(actual_destination, rel_path)
                                
                                # Создаем папки назначения
                                os.makedirs(os.path.dirname(dest_file_path), exist_ok=True)
                                
                                # Безопасное именование файлов
                                dest_file_path = self.get_safe_destination_path(dest_file_path)
                                
                                # КОПИРУЕМ файл (исходный файл не изменяется)
                                shutil.copy2(source_file_path, dest_file_path)
                                file_size = os.path.getsize(source_file_path)
                                copied_size += file_size
                                copied_count += 1
                                
                                # Обновляем прогресс
                                self.update_progress_stats(copied_size, copied_count)
                                
                    else:
                        # Безопасное копирование всей папки
                        folder_name = os.path.basename(folder_path)
                        dest_folder_path = os.path.join(actual_destination, folder_name)
                        
                        # Безопасное именование папки назначения
                        dest_folder_path = self.get_safe_destination_path(dest_folder_path, is_folder=True)
                        
                        # Копируем всю папку БЕЗ предварительного удаления
                        copied_count, copied_size = self.copy_tree_safe(
                            folder_path, dest_folder_path, copied_count, copied_size
                        )
                        
                except Exception as e:
                    self.status_updated.emit(f"Ошибка при копировании папки {folder_path}: {str(e)}")

            # Копируем отдельные файлы (БЕЗОПАСНО)
            for file_path in self.source_files:
                if self.cancelled:
                    return False, "Операция отменена"
                    
                if not os.path.exists(file_path):
                    continue

                try:
                    dest_file_path = os.path.join(actual_destination, os.path.basename(file_path))
                    
                    # Безопасное именование файла
                    dest_file_path = self.get_safe_destination_path(dest_file_path)
                    
                    # КОПИРУЕМ файл (исходный файл не изменяется)
                    shutil.copy2(file_path, dest_file_path)
                    file_size = os.path.getsize(file_path)
                    copied_size += file_size
                    copied_count += 1
                    
                    # Обновляем прогресс
                    self.update_progress_stats(copied_size, copied_count)
                    
                except Exception as e:
                    self.status_updated.emit(f"Ошибка при копировании файла {file_path}: {str(e)}")

            return True, f"Успешно скопировано {copied_count} файлов"

        except Exception as e:
            return False, f"Критическая ошибка: {str(e)}"

    def get_safe_destination_path(self, original_path, is_folder=False):
        """Создает безопасное имя для файла/папки назначения без перезаписи"""
        if not os.path.exists(original_path):
            return original_path
            
        # Если файл/папка уже существует и включено ведение истории
        if self.keep_history:
            name, ext = os.path.splitext(original_path)
            timestamp = datetime.now().strftime("%d.%m.%Y_%H-%M-%S")
            return f"{name}_{timestamp}{ext}"
        # Если ведение истории отключено, добавляем числовой суффикс
        else:
            counter = 1
            name, ext = os.path.splitext(original_path)
            new_path = original_path
            while os.path.exists(new_path):
                new_path = f"{name}_({counter}){ext}"
                counter += 1
            return new_path

    def copy_tree_safe(self, src, dst, current_count, copied_size):
        """БЕЗОПАСНОЕ рекурсивное копирование дерева папок"""
        names = os.listdir(src)
        os.makedirs(dst, exist_ok=True)
        
        for name in names:
            if self.cancelled:
                return current_count, copied_size
                
            srcname = os.path.join(src, name)
            dstname = os.path.join(dst, name)
            
            if os.path.isdir(srcname):
                current_count, copied_size = self.copy_tree_safe(srcname, dstname, current_count, copied_size)
            else:
                # Безопасное именование для каждого файла
                dstname = self.get_safe_destination_path(dstname)
                shutil.copy2(srcname, dstname)
                file_size = os.path.getsize(srcname)
                copied_size += file_size
                current_count += 1
                
                # Обновляем прогресс
                self.update_progress_stats(copied_size, current_count)
                    
        return current_count, copied_size

    def update_progress_stats(self, copied_size, copied_count):
        """Обновление прогресса и статуса"""
        if self.total_size > 0:
            progress = int((copied_size / self.total_size) * 100)
            self.progress_updated.emit(progress)
            copied_mb = copied_size / (1024 * 1024)
            total_mb = self.total_size / (1024 * 1024)
            status_text = f"Копирование... ({copied_mb:.1f} MB / {total_mb:.1f} MB) | Файлов: {copied_count}"
            self.status_updated.emit(status_text)

    def check_disk_space(self, required_size):
        try:
            if hasattr(os, 'statvfs'):
                stat = os.statvfs(self.destination_folder)
                free_space = stat.f_bavail * stat.f_frsize
            else:
                import ctypes
                free_bytes = ctypes.c_ulonglong(0)
                ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                    ctypes.c_wchar_p(self.destination_folder), 
                    None, None, ctypes.pointer(free_bytes)
                )
                free_space = free_bytes.value
            
            return free_space >= required_size
        except:
            return True

class MultiTabBackupWorker(QThread):
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, tabs_data, copy_folder_contents, keep_history, create_backup_folder):
        super().__init__()
        self.tabs_data = tabs_data  # Список словарей с данными каждой вкладки
        self.copy_folder_contents = copy_folder_contents
        self.keep_history = keep_history
        self.create_backup_folder = create_backup_folder
        self.cancelled = False
        self.total_size = 0

    def cancel(self):
        self.cancelled = True

    def run(self):
        try:
            if self.total_size == 0:
                self.total_size = self.calculate_total_backup_size()
            
            if self.total_size == 0:
                self.finished_signal.emit(False, "Нет файлов для копирования")
                return
                
            self.status_updated.emit(f"Начинаем копирование из {len(self.tabs_data)} вкладок ({self.total_size/1024/1024:.1f} MB)")
            
            success, message = self.perform_multi_tab_backup()
            self.finished_signal.emit(success, message)
            
        except Exception as e:
            self.finished_signal.emit(False, f"Ошибка: {str(e)}")

    def calculate_total_backup_size(self):
        """Вычисляет общий размер всех файлов из всех вкладок"""
        total_size = 0
        for tab in self.tabs_data:
            for folder_path in tab['folders']:
                if os.path.isdir(folder_path) and not self.cancelled:
                    try:
                        for root, dirs, files in os.walk(folder_path):
                            for file in files:
                                if self.cancelled:
                                    return total_size
                                file_path = os.path.join(root, file)
                                if os.path.exists(file_path):
                                    total_size += os.path.getsize(file_path)
                    except OSError:
                        continue
            
            for file_path in tab['files']:
                if not self.cancelled and os.path.isfile(file_path) and os.path.exists(file_path):
                    total_size += os.path.getsize(file_path)
        
        return total_size

    def perform_multi_tab_backup(self):
        """Выполняет резервное копирование для всех вкладок с их папками назначения"""
        if self.cancelled:
            return False, "Операция отменена"

        try:
            copied_count = 0
            copied_size = 0
            total_files = 0

            # Проходим по каждой вкладке
            for i, tab in enumerate(self.tabs_data):
                if self.cancelled:
                    return False, "Операция отменена"
                
                tab_name = tab['name']
                destination_folder = tab['destination']
                source_folders = tab['folders']
                source_files = tab['files']

                self.status_updated.emit(f"Копирование вкладки '{tab_name}'...")

                # Проверяем место на диске для этой папки назначения
                if not self.check_disk_space(destination_folder, tab['size']):
                    self.status_updated.emit(f"Недостаточно места для вкладки '{tab_name}'")
                    continue

                actual_destination = destination_folder
                if self.create_backup_folder:
                    current_date = datetime.now().strftime("%d-%m-%Y")
                    backup_folder_name = f"Резервное копирование {current_date}"
                    actual_destination = os.path.join(destination_folder, backup_folder_name)
                    if not os.path.exists(actual_destination):
                        os.makedirs(actual_destination)

                # Копируем папки для этой вкладки
                for folder_path in source_folders:
                    if self.cancelled:
                        return False, "Операция отменена"
                        
                    if not os.path.exists(folder_path):
                        continue

                    try:
                        if self.copy_folder_contents:
                            # Копирование содержимого папки
                            for root, dirs, files in os.walk(folder_path):
                                for file in files:
                                    if self.cancelled:
                                        return False, "Операция отменена"
                                        
                                    source_file_path = os.path.join(root, file)
                                    rel_path = os.path.relpath(source_file_path, folder_path)
                                    dest_file_path = os.path.join(actual_destination, rel_path)
                                    
                                    # Создаем папки назначения
                                    os.makedirs(os.path.dirname(dest_file_path), exist_ok=True)
                                    
                                    # Безопасное именование файлов
                                    dest_file_path = self.get_safe_destination_path(dest_file_path)
                                    
                                    # Копируем файл
                                    shutil.copy2(source_file_path, dest_file_path)
                                    file_size = os.path.getsize(source_file_path)
                                    copied_size += file_size
                                    copied_count += 1
                                    
                                    # Обновляем прогресс
                                    self.update_progress_stats(copied_size, copied_count)
                                    
                        else:
                            # Копирование всей папки
                            folder_name = os.path.basename(folder_path)
                            dest_folder_path = os.path.join(actual_destination, folder_name)
                            
                            # Безопасное именование папки назначения
                            dest_folder_path = self.get_safe_destination_path(dest_folder_path, is_folder=True)
                            
                            # Копируем всю папку
                            copied_count, copied_size = self.copy_tree_safe(
                                folder_path, dest_folder_path, copied_count, copied_size
                            )
                            
                    except Exception as e:
                        self.status_updated.emit(f"Ошибка при копировании папки {folder_path}: {str(e)}")

                # Копируем отдельные файлы для этой вкладки
                for file_path in source_files:
                    if self.cancelled:
                        return False, "Операция отменена"
                        
                    if not os.path.exists(file_path):
                        continue

                    try:
                        dest_file_path = os.path.join(actual_destination, os.path.basename(file_path))
                        
                        # Безопасное именование файла
                        dest_file_path = self.get_safe_destination_path(dest_file_path)
                        
                        # Копируем файл
                        shutil.copy2(file_path, dest_file_path)
                        file_size = os.path.getsize(file_path)
                        copied_size += file_size
                        copied_count += 1
                        
                        # Обновляем прогресс
                        self.update_progress_stats(copied_size, copied_count)
                        
                    except Exception as e:
                        self.status_updated.emit(f"Ошибка при копировании файла {file_path}: {str(e)}")

            return True, f"Успешно скопировано {copied_count} файлов из {len(self.tabs_data)} вкладок"

        except Exception as e:
            return False, f"Критическая ошибка: {str(e)}"

    def get_safe_destination_path(self, original_path, is_folder=False):
        """Создает безопасное имя для файла/папки назначения без перезаписи"""
        if not os.path.exists(original_path):
            return original_path
            
        # Если файл/папка уже существует и включено ведение истории
        if self.keep_history:
            name, ext = os.path.splitext(original_path)
            timestamp = datetime.now().strftime("%d.%m.%Y_%H-%M-%S")
            return f"{name}_{timestamp}{ext}"
        # Если ведение истории отключено, добавляем числовой суффикс
        else:
            counter = 1
            name, ext = os.path.splitext(original_path)
            new_path = original_path
            while os.path.exists(new_path):
                new_path = f"{name}_({counter}){ext}"
                counter += 1
            return new_path

    def copy_tree_safe(self, src, dst, current_count, copied_size):
        """Безопасное рекурсивное копирование дерева папок"""
        names = os.listdir(src)
        os.makedirs(dst, exist_ok=True)
        
        for name in names:
            if self.cancelled:
                return current_count, copied_size
                
            srcname = os.path.join(src, name)
            dstname = os.path.join(dst, name)
            
            if os.path.isdir(srcname):
                current_count, copied_size = self.copy_tree_safe(srcname, dstname, current_count, copied_size)
            else:
                # Безопасное именование для каждого файла
                dstname = self.get_safe_destination_path(dstname)
                shutil.copy2(srcname, dstname)
                file_size = os.path.getsize(srcname)
                copied_size += file_size
                current_count += 1
                
                # Обновляем прогресс
                self.update_progress_stats(copied_size, current_count)
                    
        return current_count, copied_size

    def update_progress_stats(self, copied_size, copied_count):
        """Обновление прогресса и статуса"""
        if self.total_size > 0:
            progress = int((copied_size / self.total_size) * 100)
            self.progress_updated.emit(progress)
            copied_mb = copied_size / (1024 * 1024)
            total_mb = self.total_size / (1024 * 1024)
            status_text = f"Копирование... ({copied_mb:.1f} MB / {total_mb:.1f} MB) | Файлов: {copied_count}"
            self.status_updated.emit(status_text)

    def check_disk_space(self, destination_folder, required_size):
        """Проверяет свободное место на диске"""
        try:
            if hasattr(os, 'statvfs'):
                stat = os.statvfs(destination_folder)
                free_space = stat.f_bavail * stat.f_frsize
            else:
                import ctypes
                free_bytes = ctypes.c_ulonglong(0)
                ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                    ctypes.c_wchar_p(destination_folder), 
                    None, None, ctypes.pointer(free_bytes)
                )
                free_space = free_bytes.value
            
            return free_space >= required_size
        except:
            return True  # Если не удалось проверить, продолжаем

class BackupApp(QMainWindow):
    def __init__(self):
        super().__init__()
        # Инициализация настроек приложения
        self.settings = QSettings("MyCompany", "BackupApp")
        # Основные настройки окна
        self.setWindowTitle("Резервное копирование файлов")
        self.setGeometry(100, 100, 900, 700)
        self.setWindowIcon(QIcon('icon.ico'))
        # Инициализация переменных для хранения данных
        # УДАЛЕНО: больше не храним глобальные списки файлов и папок
        # Таймер для автоматического копирования
        self.backup_timer = QTimer()
        self.backup_timer.timeout.connect(self.check_backup_time)
        # Переменные для отслеживания состояния копирования
        self.last_backup_date = None
        self.current_backup_size = 0  
        self.copied_size = 0  
        # Инициализация пользовательского интерфейса
        self.init_ui()
        # Загрузка сохраненных настроек
        self.load_settings()

        self.backup_worker = None
        
    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        # Создание центрального виджета
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Убираем отступы у центрального layout
        layout.setContentsMargins(10, 16, 10, 10)
        layout.setSpacing(6)

        # Создание панели инструментов
        self.create_toolbar_with_icons()
        
        # Создание stacked widget для переключения между разделами
        self.stacked_widget = QStackedWidget()
        layout.addWidget(self.stacked_widget)
        
        # Создание виджета для выбора файлов
        self.files_widget = QWidget()
        files_layout = QVBoxLayout(self.files_widget)
        files_layout.setAlignment(Qt.AlignTop)
        files_layout.setContentsMargins(0, 0, 0, 0)
        files_layout.setSpacing(5)
        
        # Создание виджета для настроек
        self.settings_widget = QWidget()
        settings_layout = QVBoxLayout(self.settings_widget)
        settings_layout.setAlignment(Qt.AlignTop)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        settings_layout.setSpacing(5)
        
        # Добавляем виджеты в stacked widget
        self.stacked_widget.addWidget(self.files_widget)
        self.stacked_widget.addWidget(self.settings_widget)
        
        # Инициализация содержимого разделов
        self.init_files_section()
        self.init_settings_section()
        
        # Показываем раздел выбора файлов по умолчанию
        self.stacked_widget.setCurrentIndex(0)
        
        # Кнопки управления
        button_layout = QHBoxLayout()
        self.start_btn = QPushButton("Запустить")
        self.start_btn.clicked.connect(self.start_backup)
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        
        self.stop_btn = QPushButton("Остановить")
        self.stop_btn.clicked.connect(self.stop_backup)
        self.stop_btn.setStyleSheet("background-color: #f44336; color: white;")
        self.stop_btn.setEnabled(False)
        
        self.manual_btn = QPushButton("Копировать")
        self.manual_btn.clicked.connect(self.manual_backup)
        self.manual_btn.setStyleSheet("background-color: #2196F3; color: white;")

        self.cancel_btn = QPushButton("Отменить")
        self.cancel_btn.clicked.connect(self.cancel_backup)
        self.cancel_btn.setStyleSheet("background-color: #FF9800; color: white;")
        self.cancel_btn.setVisible(False)  
        
        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.stop_btn)
        button_layout.addWidget(self.manual_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
        
        # Информация о следующем копировании
        self.next_backup_label = QLabel("Следующее копирование: остановлено")
        self.next_backup_label.setStyleSheet("background-color: #e3f2fd; padding: 5px; border: 1px solid #bbdefb;")
        layout.addWidget(self.next_backup_label)
        
        # История операций (Лог)
        log_group = QGroupBox()
        self.log_text = QTextEdit("История операций:")
        self.log_text.setReadOnly(True)
        log_group.setLayout(QVBoxLayout())  
        log_group.layout().addWidget(self.log_text)
        layout.addWidget(log_group)
        
        # Изначально скрываем все дополнительные элементы
        self.hide_all_additional_elements()
        
        # Кастомный статус бар с прогрессом
        self.setup_custom_statusbar()
    
    def create_toolbar_with_icons(self):
        """Создание панели инструментов с иконками"""
        # Основная панель инструментов
        toolbar = QToolBar("Main Toolbar")
        toolbar.setIconSize(QSize(24, 24))
        
        # Делаем панель неперемещаемой
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        
        # Устанавливаем вертикальную ориентацию для правой панели
        toolbar.setOrientation(Qt.Vertical)
        
        # Добавляем панель в правую область и закрепляем
        self.addToolBar(Qt.RightToolBarArea, toolbar)
        
        # Используем стандартные иконки Qt
        style = self.style()
        
        # Разделитель
        toolbar.addSeparator()

        # Выбор файлов - используем свою иконку
        files_icon = QIcon('icons/files_icon.png')  
        files_action = QAction(files_icon, "Выбор файлов", self)
        files_action.triggered.connect(self.show_files_section)
        toolbar.addAction(files_action)
        
        # Настройки - используем свою иконку
        settings_icon = QIcon('icons/settings_icon.png')  
        settings_action = QAction(settings_icon, "Настройки", self)
        settings_action.triggered.connect(self.show_settings_section)
        toolbar.addAction(settings_action)
        
        # Разделитель 
        toolbar.addSeparator()

    def init_files_section(self):
        """Инициализация раздела выбора файлов с вкладками"""
        files_layout = self.files_widget.layout()

        # Заголовок
        title_label = QLabel("Выбор файлов и папок")
        title_label.setStyleSheet("font-weight: bold;")
        files_layout.addWidget(title_label)

        # Разделительная линия
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        files_layout.addWidget(separator)

        # Создаем QTabWidget для вкладок
        self.tabs_widget = QTabWidget()
        self.tabs_widget.setTabsClosable(True)
        self.tabs_widget.tabCloseRequested.connect(self.close_tab)
        
        # Устанавливаем фиксированную ширину вкладок
        tab_width = 140 
        self.tabs_widget.setStyleSheet(f"""
            QTabBar::tab {{
                width: {tab_width}px;
                min-width: {tab_width}px;
                max-width: {tab_width}px;
            }}
        """)

        # Кнопка для добавления новой вкладки
        self.add_tab_btn = QPushButton("+ Добавить вкладку")
        self.add_tab_btn.clicked.connect(self.add_new_tab)
        self.add_tab_btn.setStyleSheet("font-weight: bold;")
        self.add_tab_btn.setFixedHeight(40)

        # Добавляем первую вкладку по умолчанию с названием "Без названия"
        self.add_new_tab("Без названия")

        # Размещаем виджеты напрямую в files_layout (без GroupBox)
        files_layout.addWidget(self.tabs_widget)
        files_layout.addWidget(self.add_tab_btn)

    def add_new_tab(self, name=None):
        """Добавление новой вкладки с полным функционалом"""
        try:
            # Упрощенная логика создания имени вкладки
            if name is None or not isinstance(name, str):
                name = "Без названия"
            
            # Обрезаем название для отображения во вкладке
            display_name = self.truncate_tab_title(name)

            # Создаем виджет для вкладки
            tab_widget = QWidget()
            tab_layout = QVBoxLayout(tab_widget)
            
            # ДОБАВЛЯЕМ РЕДАКТИРУЕМЫЙ ЗАГОЛОВОК ВНУТРИ ВКЛАДКИ
            tab_title_edit = QLineEdit(name)
            tab_title_edit.setStyleSheet("""
                QLineEdit {
                    font-weight: bold; 
                    border: none;
                    background: transparent;
                }
                """)
            tab_title_edit.setAlignment(Qt.AlignCenter)
            tab_layout.addWidget(tab_title_edit)
            
            # Создаем структуру данных для хранения состояния вкладки
            tab_data = {
                'source_folders': [],
                'source_files': [],
                'destination_folder': '',
                'folders_list': QListWidget(),
                'files_list': QListWidget(),
                'dest_edit': QLineEdit(),
                'title_edit': tab_title_edit
            }
            
            # Подключаем сигнал завершения редактирования (когда поле теряет фокус или нажат Enter)
            tab_title_edit.editingFinished.connect(lambda: self.on_tab_title_finished(tab_data))

            # Добавляем вкладку с обрезанным названием для отображения
            index = self.tabs_widget.addTab(tab_widget, display_name)
            self.tabs_widget.setCurrentIndex(index)

            # Блок 1: Список выбранных папок
            folders_group = QGroupBox("Список папок")
            folders_layout = QVBoxLayout(folders_group)

            folders_layout.addWidget(tab_data['folders_list'])

            # Кнопки управления папками
            folder_buttons_layout = QHBoxLayout()
            add_folder_btn = QPushButton("Добавить папку")
            add_folder_btn.clicked.connect(lambda: self.add_folder_to_tab(tab_data))
            remove_folder_btn = QPushButton("Удалить папку")
            remove_folder_btn.clicked.connect(lambda: self.remove_selected_folder_from_tab(tab_data))
            clear_folders_btn = QPushButton("Очистить список")
            clear_folders_btn.clicked.connect(lambda: self.clear_folders_list_in_tab(tab_data))

            folder_buttons_layout.addWidget(add_folder_btn)
            folder_buttons_layout.addWidget(remove_folder_btn)
            folder_buttons_layout.addWidget(clear_folders_btn)
            folders_layout.addLayout(folder_buttons_layout)

            tab_layout.addWidget(folders_group)

            # Блок 2: Список выбранных файлов
            files_group = QGroupBox("Список файлов")
            files_selection_layout = QVBoxLayout(files_group)

            files_selection_layout.addWidget(tab_data['files_list'])

            # Кнопки управления файлами
            file_buttons_layout = QHBoxLayout()
            add_files_btn = QPushButton("Добавить файл")
            add_files_btn.clicked.connect(lambda: self.add_files_to_tab(tab_data))
            remove_file_btn = QPushButton("Удалить файл")
            remove_file_btn.clicked.connect(lambda: self.remove_selected_file_from_tab(tab_data))
            clear_files_btn = QPushButton("Очистить список")
            clear_files_btn.clicked.connect(lambda: self.clear_files_list_in_tab(tab_data))

            file_buttons_layout.addWidget(add_files_btn)
            file_buttons_layout.addWidget(remove_file_btn)
            file_buttons_layout.addWidget(clear_files_btn)
            files_selection_layout.addLayout(file_buttons_layout)
            
            tab_layout.addWidget(files_group)

            # Блок 3: Папка сохранения
            dest_group = QGroupBox("Папка сохранения")
            dest_layout = QHBoxLayout(dest_group)
            tab_data['dest_edit'].setReadOnly(True)
            dest_layout.addWidget(tab_data['dest_edit'])
            dest_btn = QPushButton("Выбрать папку")
            dest_btn.clicked.connect(lambda: self.select_destination_folder_for_tab(tab_data))
            dest_layout.addWidget(dest_btn)
            
            tab_layout.addWidget(dest_group)
            tab_layout.addStretch()

            # Сохраняем данные вкладки в свойстве виджета
            tab_widget.tab_data = tab_data
            
            # Загружаем настройки для этой вкладки
            self.load_tab_settings(tab_data, name)
            
            return tab_data
            
        except Exception as e:
            self.log_message(f"Ошибка при создании вкладки: {str(e)}")
            default_name = "Без названия"
            tab_widget = QWidget()
            self.tabs_widget.addTab(tab_widget, default_name)
            return None

    def on_tab_title_finished(self, tab_data):
        """Обрабатывает завершение редактирования заголовка вкладки"""
        try:
            new_title = tab_data['title_edit'].text().strip()
            if not new_title:
                new_title = "Без названия"
                tab_data['title_edit'].setText(new_title)
            
            # Обрезаем название если оно слишком длинное
            display_title = self.truncate_tab_title(new_title)
            
            # Находим индекс вкладки, к которой принадлежит этот tab_data
            tab_index = self.find_tab_index_by_data(tab_data)
            if tab_index >= 0:
                # Получаем текущее название вкладки
                old_title = self.tabs_widget.tabText(tab_index)
                
                # Если название не изменилось, ничего не делаем
                if display_title == old_title:
                    return
                    
                # Обновляем текст вкладки (используем обрезанное название для отображения)
                self.tabs_widget.setTabText(tab_index, display_title)
                
                # Сохраняем полное название в настройках
                self.save_tab_settings(tab_data, new_title)
            
        except Exception as e:
            self.log_message(f"Ошибка при изменении названия вкладки: {str(e)}")

    def truncate_tab_title(self, title):
        """Обрезает длинное название вкладки и добавляет ... в конце"""
        if len(title) > 14:
            return title[:11] + " ..."
        return title

    def find_tab_index_by_data(self, tab_data):
        """Находит индекс вкладки по данным tab_data"""
        for i in range(self.tabs_widget.count()):
            widget = self.tabs_widget.widget(i)
            if hasattr(widget, 'tab_data') and widget.tab_data == tab_data:
                return i
        return -1

    def close_tab(self, index):
        """Закрытие вкладки"""
        if self.tabs_widget.count() > 1:  # Не позволяем закрыть последнюю вкладку
            # Сохраняем настройки перед закрытием
            current_widget = self.tabs_widget.widget(index)
            if hasattr(current_widget, 'tab_data'):
                tab_name = self.tabs_widget.tabText(index)
                self.save_tab_settings(current_widget.tab_data, tab_name)
            
            self.tabs_widget.removeTab(index)

    def get_current_tab_data(self):
        """Получение данных текущей активной вкладки"""
        current_widget = self.tabs_widget.currentWidget()
        if current_widget and hasattr(current_widget, 'tab_data'):
            return current_widget.tab_data
        return None

    def add_folder_to_tab(self, tab_data):
        """Добавление папки в конкретную вкладку"""
        folder_path = QFileDialog.getExistingDirectory(self, "Выберите папку для копирования")
        if folder_path and folder_path not in tab_data['source_folders']:
            tab_data['source_folders'].append(folder_path)
            tab_data['folders_list'].addItem(folder_path)
            self.save_current_tab_settings()
            self.log_message(f"Добавлена папка для копирования: {folder_path}")

    def remove_selected_folder_from_tab(self, tab_data):
        """Удаление выбранной папки из конкретной вкладки"""
        current_row = tab_data['folders_list'].currentRow()
        if current_row >= 0:
            item = tab_data['folders_list'].takeItem(current_row)
            folder_path = item.text()
            if folder_path in tab_data['source_folders']:
                tab_data['source_folders'].remove(folder_path)
            self.save_current_tab_settings()
            self.log_message(f"Удалена папка из списка: {folder_path}")

    def clear_folders_list_in_tab(self, tab_data):
        """Очистка списка папок в конкретной вкладке"""
        tab_data['folders_list'].clear()
        tab_data['source_folders'].clear()
        self.save_current_tab_settings()
        self.log_message("Список папок очищен")

    def add_files_to_tab(self, tab_data):
        """Добавление файлов в конкретную вкладку"""
        files, _ = QFileDialog.getOpenFileNames(self, "Выберите файлы для копирования")
        if files:
            for file_path in files:
                if file_path not in tab_data['source_files']:
                    tab_data['source_files'].append(file_path)
                    tab_data['files_list'].addItem(file_path)
            
            self.save_current_tab_settings()
            self.log_message(f"Добавлено {len(files)} файлов в список копирования")

    def remove_selected_file_from_tab(self, tab_data):
        """Удаление выбранного файла из конкретной вкладки"""
        current_row = tab_data['files_list'].currentRow()
        if current_row >= 0:
            item = tab_data['files_list'].takeItem(current_row)
            file_path = item.text()
            if file_path in tab_data['source_files']:
                tab_data['source_files'].remove(file_path)
            self.save_current_tab_settings()
            self.log_message(f"Удален файл из списка: {file_path}")

    def clear_files_list_in_tab(self, tab_data):
        """Очистка списка файлов в конкретной вкладке"""
        tab_data['files_list'].clear()
        tab_data['source_files'].clear()
        self.save_current_tab_settings()
        self.log_message("Список файлов очищен")

    def select_destination_folder_for_tab(self, tab_data):
        """Выбор папки для сохранения для конкретной вкладки"""
        folder_path = QFileDialog.getExistingDirectory(self, "Выберите папку для резервных копий")
        if folder_path:
            tab_data['destination_folder'] = folder_path
            tab_data['dest_edit'].setText(folder_path)
            self.save_current_tab_settings()
            self.log_message(f"Выбрана папка назначения: {folder_path}")

    def save_current_tab_settings(self):
        """Сохранение настроек текущей активной вкладки"""
        tab_data = self.get_current_tab_data()
        if tab_data:
            current_index = self.tabs_widget.currentIndex()
            tab_name = self.tabs_widget.tabText(current_index)
            self.save_tab_settings(tab_data, tab_name)

    def save_tab_settings(self, tab_data, tab_name):
        """Сохранение настроек конкретной вкладки"""
        self.settings.beginGroup(f"Tab_{tab_name}")
        self.settings.setValue("source_folders", tab_data['source_folders'])
        self.settings.setValue("source_files", tab_data['source_files'])
        self.settings.setValue("destination_folder", tab_data['destination_folder'])
        self.settings.setValue("tab_title", tab_data['title_edit'].text())
        self.settings.endGroup()

    def load_tab_settings(self, tab_data, tab_name):
        """Загрузка настроек конкретной вкладки"""
        self.settings.beginGroup(f"Tab_{tab_name}")
        
        # Загружаем заголовок вкладки
        saved_title = self.settings.value("tab_title", tab_name)
        if saved_title and isinstance(saved_title, str):
            tab_data['title_edit'].setText(saved_title)
            # Обрезаем длинное название для отображения
            display_title = self.truncate_tab_title(saved_title)
            # Находим индекс этой вкладки и обновляем заголовок
            tab_index = self.find_tab_index_by_data(tab_data)
            if tab_index >= 0:
                self.tabs_widget.setTabText(tab_index, display_title)

        # Загружаем список папок
        source_folders = self.settings.value("source_folders", [])
        if isinstance(source_folders, str) and source_folders:
            source_folders = [source_folders]
        elif source_folders is None:
            source_folders = []
        
        tab_data['source_folders'] = []
        tab_data['folders_list'].clear()
        for folder_path in source_folders:
            if folder_path and os.path.exists(folder_path) and os.path.isdir(folder_path):
                tab_data['source_folders'].append(folder_path)
                tab_data['folders_list'].addItem(folder_path)
        
        # Загружаем список файлов
        source_files = self.settings.value("source_files", [])
        if isinstance(source_files, str) and source_files:
            source_files = [source_files]
        elif source_files is None:
            source_files = []
        
        tab_data['source_files'] = []
        tab_data['files_list'].clear()
        for file_path in source_files:
            if file_path and os.path.exists(file_path) and os.path.isfile(file_path):
                tab_data['source_files'].append(file_path)
                tab_data['files_list'].addItem(file_path)
        
        # Загружаем папку назначения
        destination_folder = self.settings.value("destination_folder", "")
        if destination_folder and os.path.exists(destination_folder) and os.path.isdir(destination_folder):
            tab_data['destination_folder'] = destination_folder
            tab_data['dest_edit'].setText(destination_folder)
        
        self.settings.endGroup()
    
    def init_settings_section(self):
        """Инициализация раздела настроек (без QGroupBox-контейнера)"""
        settings_layout = self.settings_widget.layout()

        # Заголовок раздела (опционально)
        title_label = QLabel("Настройки")
        title_label.setStyleSheet("font-weight: bold;")
        settings_layout.addWidget(title_label)

        # Разделительная линия
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        settings_layout.addWidget(separator)

        # Блок 1: Планирование
        planning_group = QGroupBox("Планирование")
        planning_layout = QGridLayout(planning_group)
        planning_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)

        # Тип периода
        planning_layout.addWidget(QLabel("Тип периода:"), 0, 0)
        self.period_type_combo = QComboBox()
        self.period_type_combo.addItems(["Ежедневно", "Еженедельно", "Ежемесячно"])
        self.period_type_combo.currentTextChanged.connect(self.update_ui_for_period)
        planning_layout.addWidget(self.period_type_combo, 0, 1)

        # Время копирования
        planning_layout.addWidget(QLabel("Время копирования:"), 1, 0)
        self.time_edit = QTimeEdit()
        self.time_edit.setTime(QTime.currentTime())
        planning_layout.addWidget(self.time_edit, 1, 1)

        # День недели (для еженедельного)
        self.weekday_label = QLabel("День недели:")
        self.weekday_combo = QComboBox()
        self.weekday_combo.addItems(["Понедельник", "Вторник", "Среда", "Четверг",
                                "Пятница", "Суббота", "Воскресенье"])
        planning_layout.addWidget(self.weekday_label, 2, 0)
        planning_layout.addWidget(self.weekday_combo, 2, 1)

        # День месяца (для ежемесячного)
        self.monthday_label = QLabel("День месяца:")
        self.monthday_spin = QSpinBox()
        self.monthday_spin.setRange(1, 31)
        self.monthday_spin.setValue(1)
        planning_layout.addWidget(self.monthday_label, 3, 0)
        planning_layout.addWidget(self.monthday_spin, 3, 1)

        settings_layout.addWidget(planning_group) 

        # Блок 2: Дополнительные настройки
        additional_group = QGroupBox("Дополнительные настройки")
        additional_layout = QGridLayout(additional_group)
        additional_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)

        # ДОБАВЛЯЕМ НОВЫЙ ЧЕКБОКС
        self.copy_all_tabs = QCheckBox("Копировать файлы из всех вкладок")
        self.copy_all_tabs.setChecked(False)
        additional_layout.addWidget(self.copy_all_tabs, 0, 0, 1, 2)  # Добавляем первым

        # Копировать содержимое папки вместо всей папки
        self.copy_folder_contents = QCheckBox("Копировать содержимое папки (без самой папки)")
        self.copy_folder_contents.setChecked(False)
        additional_layout.addWidget(self.copy_folder_contents, 1, 0, 1, 2)  # Сдвигаем остальные

        # Добавить дату к имени сохранённой копии файла
        self.keep_history = QCheckBox("Добавить дату к имени сохранённой копии файла")
        self.keep_history.setChecked(True)
        additional_layout.addWidget(self.keep_history, 2, 0, 1, 2)

        # Создавать отдельную папку «Резервное копирование дд-мм-гггг»
        self.create_backup_folder = QCheckBox(
            'Создавать отдельную папку с названием «Резервное копирование дд-мм-гггг» при каждом копировании'
        )
        self.create_backup_folder.setChecked(True)
        additional_layout.addWidget(self.create_backup_folder, 3, 0, 1, 2)

        # Автозапуск при старте системы
        self.auto_start_cb = QCheckBox("Запускать приложение при старте системы")
        self.auto_start_cb.stateChanged.connect(self.toggle_auto_start)
        additional_layout.addWidget(self.auto_start_cb, 4, 0, 1, 2)  # Сдвигаем

        settings_layout.addWidget(additional_group)

        # Блок 3: Сброс настроек
        reset_group = QGroupBox("Сброс настроек")
        reset_layout = QVBoxLayout(reset_group)
        reset_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)

        # Кнопка сброса настроек
        self.reset_settings_btn = QPushButton("Сбросить все настройки по умолчанию")
        self.reset_settings_btn.setStyleSheet("background-color: #FF5722; color: white; font-weight: bold;")
        self.reset_settings_btn.clicked.connect(self.reset_all_settings)
        reset_layout.addWidget(self.reset_settings_btn)

        # Информационный текст
        reset_info = QLabel("Это действие очистит все настройки и вкладки, восстановив значения по умолчанию. Приложение будет перезапущено.")
        reset_info.setWordWrap(True)
        reset_info.setStyleSheet("color: #666; font-size: 9pt; padding: 5px;")
        reset_layout.addWidget(reset_info)

        settings_layout.addWidget(reset_group)

        # Растягивающий элемент (чтобы элементы прижимались к верху)
        settings_layout.addStretch()

    def show_files_section(self):
        """Показать раздел выбора файлов"""
        self.stacked_widget.setCurrentIndex(0)
    
    def show_settings_section(self):
        """Показать раздел настроек"""
        self.stacked_widget.setCurrentIndex(1)

    def start_backup_thread(self):
        """Запускает резервное копирование для текущей или всех вкладок"""
        if self.copy_all_tabs.isChecked():
            # Копирование из всех вкладок
            self.start_backup_all_tabs()
        else:
            # Копирование только из текущей вкладки (старая логика)
            self.start_backup_current_tab()

    def start_backup_current_tab(self):
        """Запускает резервное копирование для текущей вкладки"""
        tab_data = self.get_current_tab_data()
        if not tab_data:
            QMessageBox.warning(self, "Ошибка", "Нет активной вкладки!")
            return

        if not self.validate_backup_conditions_for_tab(tab_data):
            return

        # Блокируем UI во время копирования
        self.set_ui_enabled(False)
        
        # Предварительно вычисляем размер для отображения
        total_size = self.calculate_total_backup_size_for_tab(tab_data)
        
        # Создаем worker с данными из текущей вкладки
        self.backup_worker = BackupWorker(
            tab_data['source_folders'],
            tab_data['source_files'],
            tab_data['destination_folder'],
            self.copy_folder_contents.isChecked(),
            self.keep_history.isChecked(),
            self.create_backup_folder.isChecked()
        )
        
        # Передаем общий размер в worker
        self.backup_worker.total_size = total_size
        self.backup_worker.progress_updated.connect(self.update_progress)
        self.backup_worker.status_updated.connect(self.status_label.setText)
        self.backup_worker.finished_signal.connect(self.on_backup_finished)
        
        # Показываем прогресс с реальным размером
        self.show_progress_bar(total_size)
        
        # Устанавливаем начальный статус
        if total_size > 0:
            total_mb = total_size / (1024 * 1024)
            self.status_label.setText(f"Копирование текущей вкладки... (0.0 MB / {total_mb:.1f} MB) | Файлов: 0")
        else:
            self.status_label.setText("Подготовка к копированию текущей вкладки...")
        
        # Запускаем
        self.backup_worker.start()

    def start_backup_all_tabs(self):
        """Запускает резервное копирование для всех вкладок с их папками назначения"""
        # Собираем данные из всех вкладок
        tabs_data = []
        valid_tabs_count = 0
        total_size = 0
        
        for i in range(self.tabs_widget.count()):
            widget = self.tabs_widget.widget(i)
            if hasattr(widget, 'tab_data'):
                tab_data = widget.tab_data
                
                # Проверяем, что вкладка имеет необходимые данные
                if (tab_data['source_folders'] or tab_data['source_files']) and tab_data['destination_folder']:
                    # Вычисляем размер для этой вкладки
                    tab_size = self.calculate_total_backup_size_for_tab(tab_data)
                    if tab_size > 0:
                        tabs_data.append({
                            'folders': tab_data['source_folders'],
                            'files': tab_data['source_files'],
                            'destination': tab_data['destination_folder'],
                            'size': tab_size,
                            'name': self.tabs_widget.tabText(i)
                        })
                        total_size += tab_size
                        valid_tabs_count += 1
        
        if valid_tabs_count == 0:
            QMessageBox.warning(self, "Ошибка", "Нет вкладок с данными для копирования!")
            return
        
        # Проверяем условия
        if total_size == 0:
            QMessageBox.warning(self, "Ошибка", "Нет файлов для копирования!")
            return
        
        # Блокируем UI во время копирования
        self.set_ui_enabled(False)
        
        # Создаем специальный worker для множественного копирования
        self.backup_worker = MultiTabBackupWorker(
            tabs_data,
            self.copy_folder_contents.isChecked(),
            self.keep_history.isChecked(),
            self.create_backup_folder.isChecked()
        )
        
        # Передаем общий размер в worker
        self.backup_worker.total_size = total_size
        self.backup_worker.progress_updated.connect(self.update_progress)
        self.backup_worker.status_updated.connect(self.status_label.setText)
        self.backup_worker.finished_signal.connect(self.on_backup_finished)
        
        # Показываем прогресс с реальным размером
        self.show_progress_bar(total_size)
        
        # Устанавливаем начальный статус
        total_mb = total_size / (1024 * 1024)
        self.status_label.setText(f"Копирование из {valid_tabs_count} вкладок... (0.0 MB / {total_mb:.1f} MB) | Файлов: 0")
        
        # Запускаем
        self.backup_worker.start()
        
    def validate_backup_conditions_for_tab(self, tab_data):
        """Проверяет условия для выполнения резервного копирования для конкретной вкладки"""
        if not (tab_data['source_folders'] or tab_data['source_files']):
            self.log_message("Проверка условий: не выбраны исходные файлы/папки")
            return False
        
        if not tab_data['destination_folder']:
            self.log_message("Проверка условий: не выбрана папка назначения")
            return False
        
        total_size = self.calculate_total_backup_size_for_tab(tab_data)
        if total_size == 0:
            self.log_message("Проверка условий: нет файлов для копирования")
            return False
        
        if not os.path.exists(tab_data['destination_folder']):
            try:
                os.makedirs(tab_data['destination_folder'])
                self.log_message(f"Создана папка назначения: {tab_data['destination_folder']}")
            except OSError as e:
                self.log_message(f"Не удалось создать папку назначения: {str(e)}")
                return False
        
        return True

    def calculate_total_backup_size_for_tab(self, tab_data):
        """Вычисляет общий размер файлов для копирования для конкретной вкладки"""
        total_size = 0
        
        # Для папок
        for folder_path in tab_data['source_folders']:
            if os.path.isdir(folder_path):
                try:
                    if self.copy_folder_contents.isChecked():
                        for root, dirs, files in os.walk(folder_path):
                            for file in files:
                                file_path = os.path.join(root, file)
                                if os.path.exists(file_path):
                                    total_size += os.path.getsize(file_path)
                    else:
                        for root, dirs, files in os.walk(folder_path):
                            for file in files:
                                file_path = os.path.join(root, file)
                                if os.path.exists(file_path):
                                    total_size += os.path.getsize(file_path)
                except (OSError, PermissionError):
                    continue
        
        # Для отдельных файлов
        for file_path in tab_data['source_files']:
            if os.path.isfile(file_path) and os.path.exists(file_path):
                try:
                    total_size += os.path.getsize(file_path)
                except (OSError, PermissionError):
                    continue
        
        return total_size

    def calculate_total_backup_size(self, folders, files):
        """Вычисляет общий размер файлов для копирования для всех вкладок"""
        total_size = 0
        
        # Для папок
        for folder_path in folders:
            if os.path.isdir(folder_path):
                try:
                    if self.copy_folder_contents.isChecked():
                        for root, dirs, files_walk in os.walk(folder_path):
                            for file in files_walk:
                                file_path = os.path.join(root, file)
                                if os.path.exists(file_path):
                                    total_size += os.path.getsize(file_path)
                    else:
                        for root, dirs, files_walk in os.walk(folder_path):
                            for file in files_walk:
                                file_path = os.path.join(root, file)
                                if os.path.exists(file_path):
                                    total_size += os.path.getsize(file_path)
                except (OSError, PermissionError):
                    continue
        
        # Для отдельных файлов
        for file_path in files:
            if os.path.isfile(file_path) and os.path.exists(file_path):
                try:
                    total_size += os.path.getsize(file_path)
                except (OSError, PermissionError):
                    continue
        
        return total_size

    def on_backup_finished(self, success, message):
        """Обрабатывает завершение копирования"""
        self.set_ui_enabled(True)
        self.hide_progress_bar()
        
        if success:
            self.log_message(f"✓ {message}")
            self.status_label.setText("Копирование завершено успешно")
        else:
            self.log_message(f"✗ {message}")
            self.status_label.setText("Ошибка копирования")
            
        # Очищаем worker
        self.backup_worker = None
        # Сбрасываем размер
        self.current_backup_size = 0
        
    def set_ui_enabled(self, enabled):
        """Блокирует/разблокирует UI во время копирования"""
        self.start_btn.setEnabled(enabled)
        self.stop_btn.setEnabled(enabled and self.backup_timer.isActive())
        self.manual_btn.setEnabled(enabled)
        self.cancel_btn.setVisible(not enabled)
        
    def cancel_backup(self):
        """Отменяет текущее копирование"""
        if self.backup_worker and self.backup_worker.isRunning():
            self.backup_worker.cancel()
            self.backup_worker.wait(3000)
            self.status_label.setText("Копирование отменено")
            self.hide_progress_bar()
            self.set_ui_enabled(True)

    def setup_custom_statusbar(self):
        """Настраивает кастомный статус бар с прогрессом"""
        
        # Создаем виджет для статус бара
        status_widget = QWidget()
        status_layout = QVBoxLayout(status_widget)
        status_layout.setContentsMargins(10, 5, 10, 5)
        
        # Текстовый лейбл для статуса
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignCenter)
        
        # Прогресс бар (изначально скрыт)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(20)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setAlignment(Qt.AlignCenter)
        
        if platform.system() == "Darwin": # macOS
            self.progress_bar.setMaximumHeight(25)
            self.progress_bar.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #C0C0C0;
                    border-radius: 5px;
                    background-color: #F0F0F0;
                    text-align: center;
                }
                QProgressBar::chunk {
                    background-color: #007AFF;
                    border-radius: 4px;
                }
            """)
        
        status_layout.addWidget(self.status_label)  
        status_layout.addWidget(self.progress_bar)  
        
        layout = self.centralWidget().layout()
        layout.addWidget(status_widget)
    
    def show_progress_bar(self, total_size=100):
        """Показывает прогресс бар для большого копирования"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(100)  # Всегда максимум 100%
        
        # Сохраняем общий размер для отображения
        if total_size > 0:
            self.current_backup_size = total_size
        else:
            self.current_backup_size = 0
        
        self.copied_size = 0
        
        if platform.system() == "Darwin":
            QApplication.processEvents()

    def update_progress(self, progress_percent):
        """Обновляет только прогресс бар, текст статуса теперь управляется из потока"""
        if self.progress_bar.isVisible():
            self.progress_bar.setValue(progress_percent)
            
            if platform.system() == "Darwin":
                QApplication.processEvents()

    def hide_progress_bar(self):
        """Скрывает прогресс бар после завершения копирования"""
        self.progress_bar.setVisible(False)
        self.current_backup_size = 0
        self.copied_size = 0
        self.status_label.setText("Готово")
        
        QTimer.singleShot(2000, lambda: self.status_label.setText(""))
    
    def get_application_path(self):
        """Определяет правильный путь к приложению в зависимости от режима запуска"""
        if getattr(sys, 'frozen', False):
            # Запущен как .exe (pyinstaller)
            return sys.executable
        else:
            # Запущен как .py скрипт
            return os.path.abspath(sys.argv[0])

    def toggle_auto_start(self, state):
        """Включает/выключает автозапуск при старте системы"""
        if state == Qt.Checked:
            success = self.enable_auto_start()
            if not success:
                self.auto_start_cb.setChecked(False)
        else:
            self.disable_auto_start()

    def enable_auto_start(self):
        """Добавляет приложение в автозагрузку"""
        try:
            app_path = self.get_application_path()
            system = platform.system()
            if system == "Windows":
                return self._enable_auto_start_windows(app_path)
            elif system == "Linux":
                return self._enable_auto_start_linux(app_path)
            elif system == "Darwin":  # macOS
                return self._enable_auto_start_macos(app_path)
            else:
                QMessageBox.warning(self, "Предупреждение", 
                                f"Автозапуск для ОС {system} не поддерживается")
                return False
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", 
                            f"Не удалось включить автозапуск:\n{str(e)}")
            return False

    def disable_auto_start(self):
        """Удаляет приложение из автозагрузки"""
        try:
            system = platform.system()
            
            if system == "Windows":
                self._disable_auto_start_windows()
            elif system == "Linux":
                self._disable_auto_start_linux()
            elif system == "Darwin":  # macOS
                self._disable_auto_start_macos()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", 
                            f"Не удалось отключить автозапуск:\n{str(e)}")
    
    def _enable_auto_start_windows(self, app_path):
        """Реализация автозапуска для Windows"""
        try:
            import winreg
            if app_path.endswith('.exe'):
                cmd = f'"{app_path}"'
            else:
                python_exe = sys.executable
                cmd = f'"{python_exe}" "{app_path}"'
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE
            )
            winreg.SetValueEx(key, "BackupApp", 0, winreg.REG_SZ, cmd)
            winreg.CloseKey(key)
            self.log_message("Автозапуск для Windows включен")
            return True
            
        except Exception as e:
            self.log_message(f"Ошибка включения автозапуска Windows: {str(e)}")
            return False

    def _disable_auto_start_windows(self):
        """Удаление из автозагрузки Windows"""
        try:
            import winreg
            
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE
            )
            winreg.DeleteValue(key, "BackupApp")
            winreg.CloseKey(key)
            
            self.log_message("Автозапуск для Windows отключен")
            
        except FileNotFoundError:
            pass  
        except Exception as e:
            self.log_message(f"Ошибка отключения автозапуска Windows: {str(e)}")
            raise
    
    def _enable_auto_start_linux(self, app_path):
        """Реализация автозапуска для Linux"""
        try:
            autostart_dir = os.path.expanduser("~/.config/autostart")
            desktop_file = os.path.join(autostart_dir, "backupapp.desktop")
            
            os.makedirs(autostart_dir, exist_ok=True)
            
            if app_path.endswith('.py'):
                cmd = f"{sys.executable} {app_path}"
            else:
                cmd = app_path
            
            desktop_content = f"""[Desktop Entry]
            Type=Application
            Name=BackupApp
            Exec={cmd}
            Hidden=false
            NoDisplay=false
            X-GNOME-Autostart-enabled=true
            Comment=Automated backup application
            """
            
            with open(desktop_file, 'w') as f:
                f.write(desktop_content)
            
            os.chmod(desktop_file, 0o644)
            
            self.log_message("Автозапуск для Linux включен")
            return True
            
        except Exception as e:
            self.log_message(f"Ошибка включения автозапуска Linux: {str(e)}")
            return False

    def _disable_auto_start_linux(self):
        """Удаление из автозагрузки Linux"""
        try:
            desktop_file = os.path.expanduser("~/.config/autostart/backupapp.desktop")
            if os.path.exists(desktop_file):
                os.remove(desktop_file)
                self.log_message("Автозапуск для Linux отключен")
        except Exception as e:
            self.log_message(f"Ошибка отключения автозапуска Linux: {str(e)}")
            raise
    
    def _enable_auto_start_macos(self, app_path):
        """Реализация автозапуска для macOS"""
        try:
            plist_dir = os.path.expanduser("~/Library/LaunchAgents")
            plist_file = os.path.join(plist_dir, "com.mycompany.backupapp.plist")
            
            os.makedirs(plist_dir, exist_ok=True)
            
            # Определяем команду запуска
            if app_path.endswith('.py'):
                program_args = [sys.executable, app_path]
            else:
                program_args = [app_path]
            
            plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
            <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
            <plist version="1.0">
            <dict>
                <key>Label</key>
                <string>com.mycompany.backupapp</string>
                <key>ProgramArguments</key>
                <array>
                    <string>{program_args[0]}</string>
            """
            
            if len(program_args) > 1:
                plist_content += f'<string>{program_args[1]}</string>\n'
            
            plist_content += """</array>
                <key>RunAtLoad</key>
                <true/>
                <key>KeepAlive</key>
                <false/>
            </dict>
            </plist>
            """
            
            with open(plist_file, 'w') as f:
                f.write(plist_content)
            
            self.log_message("Автозапуск для macOS включен")
            return True
            
        except Exception as e:
            self.log_message(f"Ошибка включения автозапуска macOS: {str(e)}")
            return False

    def _disable_auto_start_macos(self):
        """Удаление из автозагрузки macOS"""
        try:
            plist_file = os.path.expanduser("~/Library/LaunchAgents/com.mycompany.backupapp.plist")
            if os.path.exists(plist_file):
                os.remove(plist_file)
                self.log_message("Автозапуск для macOS отключен")
        except Exception as e:
            self.log_message(f"Ошибка отключения автозапуска macOS: {str(e)}")
            raise

    def check_auto_start_status(self):
        """Проверяет статус автозапуска"""
        try:
            system = platform.system()
            
            if system == "Windows":
                return self._check_auto_start_windows()
            elif system == "Linux":
                return self._check_auto_start_linux()
            elif system == "Darwin":
                return self._check_auto_start_macos()
            else:
                return False
                
        except Exception as e:
            self.log_message(f"Ошибка проверки статуса автозапуска: {str(e)}")
            return False
    
    def _check_auto_start_windows(self):
        """Проверяет автозапуск в Windows"""
        try:
            import winreg
            
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_READ
            )
            
            try:
                value, _ = winreg.QueryValueEx(key, "BackupApp")
                winreg.CloseKey(key)
                
                current_path = self.get_application_path().lower()
                return current_path in value.lower()
                
            except FileNotFoundError:
                winreg.CloseKey(key)
                return False
                
        except Exception:
            return False
    
    def _check_auto_start_linux(self):
        """Проверяет автозапуск в Linux"""
        desktop_file = os.path.expanduser("~/.config/autostart/backupapp.desktop")
        return os.path.exists(desktop_file)
    
    def _check_auto_start_macos(self):
        """Проверяет автозапуск в macOS"""
        plist_file = os.path.expanduser("~/Library/LaunchAgents/com.mycompany.backupapp.plist")
        return os.path.exists(plist_file)
    
    def load_settings(self):
        """Загружает сохраненные настройки"""
        try:
            # Загружаем список вкладок
            tab_count = self.settings.value("tab_count", 1, type=int)
            tab_names = self.settings.value("tab_names", ["Без названия"])  # Изменено на "Без названия"
            
            # Упрощенная проверка tab_names
            if not tab_names or not isinstance(tab_names, list):
                tab_names = ["Без названия"]  # Изменено на "Без названия"
            
            # Очищаем существующие вкладки
            while self.tabs_widget.count() > 0:
                self.tabs_widget.removeTab(0)
            
            # Создаем вкладки
            for i, tab_name in enumerate(tab_names):
                # Упрощенная проверка имени вкладки
                if not tab_name or not isinstance(tab_name, str):
                    tab_name = "Без названия"  # Изменено на "Без названия"
                self.add_new_tab(tab_name)
            
            # Загружаем настройки планирования
            period_type = self.settings.value("period_type", "Ежедневно")
            if period_type and period_type in ["Ежедневно", "Еженедельно", "Ежемесячно"]:
                index = self.period_type_combo.findText(period_type)
                if index >= 0:
                    self.period_type_combo.setCurrentIndex(index)
            
            time_str = self.settings.value("backup_time", "00:00")
            time = QTime.fromString(time_str, "hh:mm")
            if time.isValid():
                self.time_edit.setTime(time)
            else:
                self.time_edit.setTime(QTime.currentTime())
            
            # Загружаем значения дней
            weekday = self.settings.value("weekday", 0, type=int)
            if 0 <= weekday < self.weekday_combo.count():
                self.weekday_combo.setCurrentIndex(weekday)
            else:
                self.weekday_combo.setCurrentIndex(0)
            
            monthday = self.settings.value("monthday", 1, type=int)
            if 1 <= monthday <= 31:
                self.monthday_spin.setValue(monthday)
            else:
                self.monthday_spin.setValue(1)
            
            # Загружаем настройки чекбоксов
            keep_history = self.settings.value("keep_history", True, type=bool)
            self.keep_history.setChecked(bool(keep_history))
            
            create_backup_folder = self.settings.value("create_backup_folder", True, type=bool)
            self.create_backup_folder.setChecked(bool(create_backup_folder))

            copy_folder_contents = self.settings.value("copy_folder_contents", False, type=bool)
            self.copy_folder_contents.setChecked(bool(copy_folder_contents))
            
            # Загрузка и синхронизация автозапуска
            auto_start_setting = self.settings.value("auto_start", False, type=bool)
            actual_auto_start = self.check_auto_start_status()
            
            # Синхронизируем настройки с реальным состоянием системы
            if auto_start_setting != actual_auto_start:
                # Если есть расхождение, исправляем настройки
                self.auto_start_cb.setChecked(actual_auto_start)
                self.settings.setValue("auto_start", actual_auto_start)
                
                if auto_start_setting and not actual_auto_start:
                    self.log_message("Автозапуск был отключен в системе, настройки синхронизированы")
                elif not auto_start_setting and actual_auto_start:
                    self.log_message("Автозапуск был включен в системе, настройки синхронизированы")
            else:
                self.auto_start_cb.setChecked(auto_start_setting)
            
            # Загружаем настройку копирования из всех вкладок
            copy_all_tabs = self.settings.value("copy_all_tabs", False, type=bool)
            self.copy_all_tabs.setChecked(bool(copy_all_tabs))

            # Блокируем сигнал чтобы избежать рекурсивного вызова
            self.period_type_combo.blockSignals(True)
            current_period = self.period_type_combo.currentText()
            self.update_ui_for_period(current_period)
            self.period_type_combo.blockSignals(False)
            
            # Проверяем, нужно ли запускать таймер
            timer_active = self.settings.value("timer_active", False, type=bool)
            
            # Проверяем условия для автозапуска (используем текущую вкладку)
            if timer_active:
                tab_data = self.get_current_tab_data()
                if tab_data and self.validate_backup_conditions_for_tab(tab_data):
                    QTimer.singleShot(100, self.start_backup_from_settings)
                else:
                    self.log_message("Автозапуск отменен: не выполнены условия для копирования")
                    self.settings.setValue("timer_active", False)
                    self.save_settings()
                
            self.log_message("Настройки загружены успешно")
            
        except Exception as e:
            self.log_message(f"Ошибка при загрузке настроек: {str(e)}")
            self.set_default_settings()

    def save_settings(self):
        """Сохраняет текущие настройки"""
        # Сохраняем информацию о вкладках
        tab_count = self.tabs_widget.count()
        tab_names = []
        for i in range(tab_count):
            widget = self.tabs_widget.widget(i)
            if hasattr(widget, 'tab_data'):
                # Получаем полное название из поля редактирования
                full_title = widget.tab_data['title_edit'].text().strip()
                if not full_title:
                    full_title = "Без названия"
                tab_names.append(full_title)
                # Сохраняем настройки каждой вкладки с полным названием
                self.save_tab_settings(widget.tab_data, full_title)
        
        self.settings.setValue("tab_count", tab_count)
        self.settings.setValue("tab_names", tab_names)
        
        # Сохраняем настройки планирования
        self.settings.setValue("period_type", self.period_type_combo.currentText())
        self.settings.setValue("backup_time", self.time_edit.time().toString("hh:mm"))
        self.settings.setValue("weekday", self.weekday_combo.currentIndex())
        self.settings.setValue("monthday", self.monthday_spin.value())
        self.settings.setValue("keep_history", self.keep_history.isChecked())
        
        # Создание папки резервного копирования
        self.settings.setValue("create_backup_folder", self.create_backup_folder.isChecked())
        self.settings.setValue("auto_start", self.auto_start_cb.isChecked())
        self.settings.setValue("timer_active", self.backup_timer.isActive())

        # Сохраняем настройку режима копирования папок
        self.settings.setValue("copy_folder_contents", self.copy_folder_contents.isChecked())

        # Сохраняем настройку копирования из всех вкладок
        self.settings.setValue("copy_all_tabs", self.copy_all_tabs.isChecked())
        
        self.settings.sync()

    def start_backup_from_settings(self):
        """Запускает резервное копирование из настроек с восстановлением интерфейса"""
        tab_data = self.get_current_tab_data()
        if not tab_data or not self.validate_backup_conditions_for_tab(tab_data):
            self.log_message("Автозапуск отменен: не выполнены условия для копирования")
            self.settings.setValue("timer_active", False)
            self.save_settings()
            return
        
        # Восстанавливаем состояние интерфейса
        self.backup_timer.start(60000)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        # Рассчитываем следующее время копирования
        self.next_backup_time = self.calculate_next_backup_time()
        self.update_next_backup_label()
        
        self.start_backup()

    def set_default_settings(self):
        """Устанавливает настройки по умолчанию при ошибке загрузки"""
        
        self.period_type_combo.setCurrentIndex(0)
        self.time_edit.setTime(QTime.currentTime())
        self.weekday_combo.setCurrentIndex(0)
        self.monthday_spin.setValue(1)
        
        self.keep_history.setChecked(True)
        self.create_backup_folder.setChecked(True)
        self.auto_start_cb.setChecked(False)
        self.copy_all_tabs.setChecked(False)
        
        self.log_message("Установлены настройки по умолчанию")
    
    def hide_all_additional_elements(self):
        """Скрывает все дополнительные элементы"""
        self.weekday_label.setVisible(False)
        self.weekday_combo.setVisible(False)
        self.monthday_label.setVisible(False)
        self.monthday_spin.setVisible(False)
        
    def update_ui_for_period(self, period_type):
        """Обновляет интерфейс в зависимости от выбранного типа периода"""
        self.hide_all_additional_elements()
        
        if period_type == "Еженедельно":
            self.weekday_label.setVisible(True)
            self.weekday_combo.setVisible(True)
        elif period_type == "Ежемесячно":
            self.monthday_label.setVisible(True)
            self.monthday_spin.setVisible(True)
            
    def calculate_next_backup_time(self):
        """Рассчитывает время следующего копирования"""
        now = datetime.now()
        backup_time = self.time_edit.time()
        backup_time_dt = datetime(now.year, now.month, now.day, 
                                 backup_time.hour(), backup_time.minute(), backup_time.second())
        
        period_type = self.period_type_combo.currentText()
        
        if period_type == "Ежедневно":
            if backup_time_dt > now:
                next_time = backup_time_dt
            else:
                next_time = backup_time_dt + timedelta(days=1)
                
        elif period_type == "Еженедельно":
            weekday = self.weekday_combo.currentIndex()
            current_weekday = now.weekday()
            
            days_ahead = (weekday - current_weekday) % 7
            if days_ahead == 0 and backup_time_dt > now:
                next_time = backup_time_dt
            else:
                if days_ahead == 0:
                    days_ahead = 7
                next_time = backup_time_dt + timedelta(days=days_ahead)
                
        elif period_type == "Ежемесячно":
            day_of_month = self.monthday_spin.value()
            
            try:
                test_date = datetime(now.year, now.month, day_of_month)
                next_time = datetime(now.year, now.month, day_of_month, 
                                   backup_time.hour(), backup_time.minute(), backup_time.second())
            except ValueError:
                next_month = now.replace(day=28) + timedelta(days=4)
                next_month = next_month.replace(day=1)
                last_day = (next_month - timedelta(days=1)).day
                day_of_month = min(day_of_month, last_day)
                next_time = datetime(now.year, now.month, day_of_month, 
                                   backup_time.hour(), backup_time.minute(), backup_time.second())
            
            if next_time < now:
                next_month = now.replace(day=28) + timedelta(days=4)
                next_month = next_month.replace(day=1)
                try:
                    next_time = datetime(next_month.year, next_month.month, day_of_month,
                                       backup_time.hour(), backup_time.minute(), backup_time.second())
                except ValueError:
                    last_day = (next_month.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
                    day_of_month = min(day_of_month, last_day.day)
                    next_time = datetime(next_month.year, next_month.month, day_of_month,
                                       backup_time.hour(), backup_time.minute(), backup_time.second())
        
        return next_time
    
    def start_backup(self):
        """Запуск автоматического резервного копирования"""
        if not self.validate_backup_conditions():
            return
            
        self.save_settings()
        self.backup_timer.start(60000)  
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        next_time = self.calculate_next_backup_time()
        self.next_backup_time = next_time
        self.update_next_backup_label()
        
        period_type = self.period_type_combo.currentText()
        self.log_message(f"Автоматическое копирование запущено. Период: {period_type}")

        self.settings.setValue("timer_active", True)
        self.save_settings()
        
    def stop_backup(self):
        """Остановка автоматического резервного копирования"""
        self.backup_timer.stop()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.next_backup_label.setText("Следующее копирование: остановлено")
        self.settings.setValue("timer_active", False)
        self.save_settings()
        self.log_message("Автоматическое копирование остановлено")
        
    def check_backup_time(self):
        """Проверяет, настало ли время для копирования"""
        now = datetime.now()
        
        if hasattr(self, 'next_backup_time') and now >= self.next_backup_time:
            self.perform_backup()
            self.next_backup_time = self.calculate_next_backup_time()
            self.update_next_backup_label()
            
    def update_next_backup_label(self):
        """Обновляет информацию о следующем копировании"""
        if hasattr(self, 'next_backup_time'):
            next_time_str = self.next_backup_time.strftime("%d.%m.%Y %H:%M:%S")
            self.next_backup_label.setText(f"Следующее копирование: {next_time_str}")
        
    def manual_backup(self):
        """Выполнение ручного резервного копирования в отдельном потоке с проверкой условий"""
        if not self.validate_backup_conditions():
            return
        
        # Если проверки пройдены, запускаем копирование
        self.start_backup_thread()

    def validate_backup_conditions(self):
        """Проверяет условия для выполнения резервного копирования"""
        if self.copy_all_tabs.isChecked():
            # Проверка для всех вкладок
            valid_tabs_count = 0
            
            for i in range(self.tabs_widget.count()):
                widget = self.tabs_widget.widget(i)
                if hasattr(widget, 'tab_data'):
                    tab_data = widget.tab_data
                    
                    # Проверяем, что вкладка имеет необходимые данные
                    if (tab_data['source_folders'] or tab_data['source_files']) and tab_data['destination_folder']:
                        # Вычисляем размер для этой вкладки
                        tab_size = self.calculate_total_backup_size_for_tab(tab_data)
                        if tab_size > 0:
                            valid_tabs_count += 1
            
            if valid_tabs_count == 0:
                QMessageBox.warning(self, "Ошибка", "Выберите исходные файлы/папки и папку назначения!")
                return False
            return True
        else:
            # Проверка для текущей вкладки
            tab_data = self.get_current_tab_data()
            if not tab_data or not (tab_data['source_folders'] or tab_data['source_files']) or not tab_data['destination_folder']:
                QMessageBox.warning(self, "Ошибка", "Выберите исходные файлы/папки и папку назначения!")
                return False
            return True

    def perform_backup(self):
        """Основная логика выполнения резервного копирования (автоматического)"""
        self.start_backup_thread()

    def log_message(self, message):
        """Логирование сообщений с временной меткой"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        
    def closeEvent(self, event):
        """Сохраняем настройки при закрытии приложения"""
        self.settings.setValue("timer_active", self.backup_timer.isActive())
        self.save_settings()
        
        if self.backup_timer.isActive():
            self.backup_timer.stop()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # Устанавливаем шрифт GOST type A для всего приложения
    font = QFont("Segoe UI Variable", 8)  
    font.setWeight(50)            
    app.setFont(font)

    # Устанавливаем цвет текста для всего приложения
    palette = QPalette()
    palette.setColor(QPalette.WindowText, QColor(0, 0, 0))       # Черный цвет текста
    palette.setColor(QPalette.Text, QColor(0, 0, 0))             # Черный цвет для текстовых полей
    palette.setColor(QPalette.ButtonText, QColor(0, 0, 0))       # Черный цвет для кнопок
    app.setPalette(palette)
    
    window = BackupApp()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
