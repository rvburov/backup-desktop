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
                             QSizePolicy)
from PyQt5.QtCore import QTimer, Qt, QTime, QSettings


class BackupApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("MyCompany", "BackupApp")
        self.setWindowTitle("Резервное копирование файлов")
        self.setGeometry(100, 100, 900, 700)
        
        self.source_folders = []  # Список выбранных папок
        self.source_files = []    # Список выбранных файлов
        self.destination_folder = ""
        self.backup_timer = QTimer()
        self.backup_timer.timeout.connect(self.check_backup_time)
        self.last_backup_date = None
        
        self.init_ui()
        self.load_settings()  
        
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Создаем вкладки
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)
        
        # Вкладка выбора файлов
        files_tab = QWidget()
        files_layout = QVBoxLayout(files_tab)
        files_layout.setAlignment(Qt.AlignTop)
        tab_widget.addTab(files_tab, "Выбор файлов")

        # Список выбранных папок
        folders_group = QGroupBox("Список выбранных папок")
        folders_layout = QVBoxLayout(folders_group)

        self.folders_list = QListWidget()
        folders_layout.addWidget(self.folders_list)

        # Кнопки управления папками
        folder_buttons_layout = QHBoxLayout()
        self.add_folder_btn = QPushButton("Добавить папку")
        self.add_folder_btn.clicked.connect(self.add_folder)
        self.remove_folder_btn = QPushButton("Удалить выбранную")
        self.remove_folder_btn.clicked.connect(self.remove_selected_folder)
        self.clear_folders_btn = QPushButton("Очистить список")
        self.clear_folders_btn.clicked.connect(self.clear_folders_list)

        folder_buttons_layout.addWidget(self.add_folder_btn)
        folder_buttons_layout.addWidget(self.remove_folder_btn)
        folder_buttons_layout.addWidget(self.clear_folders_btn)
        folders_layout.addLayout(folder_buttons_layout)

        files_layout.addWidget(folders_group)

        # Список выбранных файлов
        files_group = QGroupBox("Список выбранных файлов")
        files_selection_layout = QVBoxLayout(files_group)

        self.files_list = QListWidget()
        files_selection_layout.addWidget(self.files_list)

        # Кнопки управления файлами
        file_buttons_layout = QHBoxLayout()
        self.add_files_btn = QPushButton("Добавить файлы")
        self.add_files_btn.clicked.connect(self.add_files)
        self.remove_file_btn = QPushButton("Удалить выбранный")
        self.remove_file_btn.clicked.connect(self.remove_selected_file)
        self.clear_files_btn = QPushButton("Очистить список")
        self.clear_files_btn.clicked.connect(self.clear_files_list)

        file_buttons_layout.addWidget(self.add_files_btn)
        file_buttons_layout.addWidget(self.remove_file_btn)
        file_buttons_layout.addWidget(self.clear_files_btn)
        files_selection_layout.addLayout(file_buttons_layout)

        files_layout.addWidget(files_group)

        # Папка сохранения
        dest_group = QGroupBox("Папка сохранения")
        dest_layout = QHBoxLayout(dest_group)
        self.dest_edit = QLineEdit()
        self.dest_edit.setReadOnly(True)
        dest_layout.addWidget(self.dest_edit)
        self.dest_btn = QPushButton("Выбрать папку")
        self.dest_btn.clicked.connect(self.select_destination_folder)
        dest_layout.addWidget(self.dest_btn)
        files_layout.addWidget(dest_group)

        # Добавляем растягивающийся элемент, чтобы группы прижимались к верху
        files_layout.addStretch()
        
       # Вкладка настроек
        settings_tab = QWidget()
        settings_layout = QVBoxLayout(settings_tab)
        settings_layout.setAlignment(Qt.AlignTop)  # Выравнивание к верху
        tab_widget.addTab(settings_tab, "Настройки")

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

        # Сохранять историю копий
        self.keep_history = QCheckBox("Добавить дату к имени сохраненной копии файла")
        self.keep_history.setChecked(True)
        additional_layout.addWidget(self.keep_history, 0, 0, 1, 2)

        # Создавать отдельную папку "Резервное копирование" + дата
        self.create_backup_folder = QCheckBox('Создавать отдельную папку с названием «Резервное копирование дд-мм-гггг» при каждом копировании')
        self.create_backup_folder.setChecked(True)
        additional_layout.addWidget(self.create_backup_folder, 1, 0, 1, 2)

        # Автозапуск при старте системы
        self.auto_start_cb = QCheckBox("Запускать приложение при старте системы")
        self.auto_start_cb.stateChanged.connect(self.toggle_auto_start)
        additional_layout.addWidget(self.auto_start_cb, 2, 0, 1, 2)

        settings_layout.addWidget(additional_group)

        # Добавляем растягивающийся элемент, чтобы группы прижимались к верху
        settings_layout.addStretch()
        
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
        
        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.stop_btn)
        button_layout.addWidget(self.manual_btn)
        layout.addLayout(button_layout)
        
        # Информация о следующем копировании
        self.next_backup_label = QLabel("Следующее копирование: не запланировано")
        self.next_backup_label.setStyleSheet("background-color: #e3f2fd; padding: 5px; border: 1px solid #bbdefb;")
        layout.addWidget(self.next_backup_label)
        
        # Лог операций
        log_group = QGroupBox()
        self.log_text = QTextEdit("История операций:")
        self.log_text.setReadOnly(True)
        log_group.setLayout(QVBoxLayout())  # Создаем простой макет
        log_group.layout().addWidget(self.log_text)
        layout.addWidget(log_group)
        
        # Изначально скрываем все дополнительные элементы
        self.hide_all_additional_elements()
        
        # Статус бар
        self.statusBar().showMessage("Готов к работе")
    
    def add_folder(self):
        """Добавление папки в список"""
        folder_path = QFileDialog.getExistingDirectory(self, "Выберите папку для копирования")
        if folder_path and folder_path not in self.source_folders:
            self.source_folders.append(folder_path)
            self.folders_list.addItem(folder_path)
            self.save_settings()
            self.log_message(f"Добавлена папка для копирования: {folder_path}")
    
    def remove_selected_folder(self):
        """Удаление выбранной папки из списка"""
        current_row = self.folders_list.currentRow()
        if current_row >= 0:
            item = self.folders_list.takeItem(current_row)
            folder_path = item.text()
            if folder_path in self.source_folders:
                self.source_folders.remove(folder_path)
            self.save_settings()
            self.log_message(f"Удалена папка из списка: {folder_path}")
    
    def clear_folders_list(self):
        """Очистка списка папок"""
        self.folders_list.clear()
        self.source_folders.clear()
        self.save_settings()
        self.log_message("Список папок очищен")
    
    def add_files(self):
        """Добавление файлов в список"""
        files, _ = QFileDialog.getOpenFileNames(self, "Выберите файлы для копирования")
        if files:
            for file_path in files:
                if file_path not in self.source_files:
                    self.source_files.append(file_path)
                    self.files_list.addItem(file_path)
            
            self.save_settings()
            self.log_message(f"Добавлено {len(files)} файлов в список копирования")
    
    def remove_selected_file(self):
        """Удаление выбранного файла из списка"""
        current_row = self.files_list.currentRow()
        if current_row >= 0:
            item = self.files_list.takeItem(current_row)
            file_path = item.text()
            if file_path in self.source_files:
                self.source_files.remove(file_path)
            self.save_settings()
            self.log_message(f"Удален файл из списка: {file_path}")
    
    def clear_files_list(self):
        """Очистка списка файлов"""
        self.files_list.clear()
        self.source_files.clear()
        self.save_settings()
        self.log_message("Список файлов очищен")
    
    def get_files_to_copy(self):
        """Получает список всех файлов для копирования"""
        files_to_copy = []
        
        # Добавляем файлы из выбранных папок (рекурсивно)
        for folder_path in self.source_folders:
            if os.path.isdir(folder_path):
                for root, dirs, files in os.walk(folder_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        files_to_copy.append(file_path)
        
        # Добавляем отдельно выбранные файлы
        for file_path in self.source_files:
            if os.path.isfile(file_path):
                files_to_copy.append(file_path)
        
        return files_to_copy
    
    def toggle_auto_start(self, state):
        """Включает/выключает автозапуск при старте системы"""
        if state == Qt.Checked:
            self.enable_auto_start()
        else:
            self.disable_auto_start()
    
    def enable_auto_start(self):
        """Добавляет приложение в автозагрузку"""
        try:
            system = platform.system()
            
            if system == "Windows":
                self._enable_auto_start_windows()
            elif system == "Linux":
                self._enable_auto_start_linux()
            elif system == "Darwin":  # macOS
                self._enable_auto_start_macos()
            else:
                QMessageBox.warning(self, "Предупреждение", 
                                  f"Автозапуск для ОС {system} не поддерживается")
                return
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось включить автозапуск: {str(e)}")
            self.auto_start_cb.setChecked(False)
    
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
            QMessageBox.critical(self, "Ошибка", f"Не удалось отключить автозапуск: {str(e)}")
            self.auto_start_cb.setChecked(True)
    
    def _enable_auto_start_windows(self):
        """Реализация автозапуска для Windows"""
        import winreg
        
        # Получаем путь к исполняемому файлу Python и текущему скрипту
        python_exe = sys.executable
        script_path = os.path.abspath(__file__)
        
        # Создаем команду для запуска
        cmd = f'"{python_exe}" "{script_path}"'
        
        # Открываем ключ автозагрузки
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        
        # Добавляем приложение в автозагрузку
        winreg.SetValueEx(key, "BackupApp", 0, winreg.REG_SZ, cmd)
        winreg.CloseKey(key)
    
    def _disable_auto_start_windows(self):
        """Удаление из автозагрузки Windows"""
        import winreg
        
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE
            )
            winreg.DeleteValue(key, "BackupApp")
            winreg.CloseKey(key)
        except FileNotFoundError:
            pass  # Значение уже удалено
    
    def _enable_auto_start_linux(self):
        """Реализация автозапуска для Linux"""
        autostart_dir = os.path.expanduser("~/.config/autostart")
        desktop_file = os.path.join(autostart_dir, "backupapp.desktop")
        
        # Создаем директорию, если она не существует
        os.makedirs(autostart_dir, exist_ok=True)
        
        python_exe = sys.executable
        script_path = os.path.abspath(__file__)
        
        # Создаем .desktop файл
        desktop_content = f"""[Desktop Entry]
        Type=Application
        Name=BackupApp
        Exec={python_exe} {script_path}
        Hidden=false
        NoDisplay=false
        X-GNOME-Autostart-enabled=true
        """
        
        with open(desktop_file, 'w') as f:
            f.write(desktop_content)
        
        # Делаем файл исполняемым
        os.chmod(desktop_file, 0o755)
    
    def _disable_auto_start_linux(self):
        """Удаление из автозагрузки Linux"""
        desktop_file = os.path.expanduser("~/.config/autostart/backupapp.desktop")
        try:
            if os.path.exists(desktop_file):
                os.remove(desktop_file)
        except OSError:
            pass
    
    def _enable_auto_start_macos(self):
        """Реализация автозапуска для macOS"""
        plist_dir = os.path.expanduser("~/Library/LaunchAgents")
        plist_file = os.path.join(plist_dir, "com.mycompany.backupapp.plist")
        
        os.makedirs(plist_dir, exist_ok=True)
        
        python_exe = sys.executable
        script_path = os.path.abspath(__file__)
        
        plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
        <plist version="1.0">
        <dict>
            <key>Label</key>
            <string>com.mycompany.backupapp</string>
            <key>ProgramArguments</key>
            <array>
                <string>{python_exe}</string>
                <string>{script_path}</string>
            </array>
            <key>RunAtLoad</key>
            <true/>
        </dict>
        </plist>
        """
        
        with open(plist_file, 'w') as f:
            f.write(plist_content)
    
    def _disable_auto_start_macos(self):
        """Удаление из автозагрузки macOS"""
        plist_file = os.path.expanduser("~/Library/LaunchAgents/com.mycompany.backupapp.plist")
        try:
            if os.path.exists(plist_file):
                os.remove(plist_file)
        except OSError:
            pass
    
    def check_auto_start_status(self):
        """Проверяет статус автозапуска"""
        system = platform.system()
        
        try:
            if system == "Windows":
                return self._check_auto_start_windows()
            elif system == "Linux":
                return self._check_auto_start_linux()
            elif system == "Darwin":
                return self._check_auto_start_macos()
        except Exception:
            return False
        
        return False
    
    def _check_auto_start_windows(self):
        """Проверяет автозапуск в Windows"""
        import winreg
        
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_READ
            )
            winreg.QueryValueEx(key, "BackupApp")
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
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
        # Загружаем список папок
        source_folders = self.settings.value("source_folders", [])
        if isinstance(source_folders, str) and source_folders:
            source_folders = [source_folders]
        
        self.source_folders = []
        for folder_path in source_folders:
            if os.path.exists(folder_path) and os.path.isdir(folder_path):
                self.source_folders.append(folder_path)
                self.folders_list.addItem(folder_path)
        
        # Загружаем список файлов
        source_files = self.settings.value("source_files", [])
        if isinstance(source_files, str) and source_files:
            source_files = [source_files]
        
        self.source_files = []
        for file_path in source_files:
            if os.path.exists(file_path) and os.path.isfile(file_path):
                self.source_files.append(file_path)
                self.files_list.addItem(file_path)
        
        # Загружаем папку назначения
        destination_folder = self.settings.value("destination_folder", "")
        if destination_folder and os.path.exists(destination_folder):
            self.destination_folder = destination_folder
            self.dest_edit.setText(destination_folder)
        
        # Загружаем настройки планирования
        period_type = self.settings.value("period_type", "Ежедневно")
        index = self.period_type_combo.findText(period_type)
        if index >= 0:
            self.period_type_combo.setCurrentIndex(index)
        
        time_str = self.settings.value("backup_time", "00:00")
        time = QTime.fromString(time_str, "hh:mm")
        if time.isValid():
            self.time_edit.setTime(time)
        
        weekday = self.settings.value("weekday", 0, type=int)
        if 0 <= weekday < self.weekday_combo.count():
            self.weekday_combo.setCurrentIndex(weekday)
        
        monthday = self.settings.value("monthday", 1, type=int)
        self.monthday_spin.setValue(monthday)
        
        keep_history = self.settings.value("keep_history", True, type=bool)
        self.keep_history.setChecked(keep_history)
        
        # ЗАГРУЖАЕМ НОВУЮ НАСТРОЙКУ: создание папки резервного копирования
        create_backup_folder = self.settings.value("create_backup_folder", True, type=bool)
        self.create_backup_folder.setChecked(create_backup_folder)
        
        auto_start = self.settings.value("auto_start", False, type=bool)
        self.auto_start_cb.setChecked(auto_start)
        
        actual_auto_start = self.check_auto_start_status()
        if auto_start != actual_auto_start:
            self.auto_start_cb.setChecked(actual_auto_start)
        
        timer_active = self.settings.value("timer_active", False, type=bool)
        if timer_active:
            self.start_backup()  # Запускаем копирование при загрузке настроек
        
        self.log_message("Настройки загружены")
    
    def save_settings(self):
        """Сохраняет текущие настройки"""
        # Сохраняем списки папок и файлов
        self.settings.setValue("source_folders", self.source_folders)
        self.settings.setValue("source_files", self.source_files)
        
        # Сохраняем папку назначения
        self.settings.setValue("destination_folder", self.destination_folder)
        
        # Сохраняем настройки планирования
        self.settings.setValue("period_type", self.period_type_combo.currentText())
        self.settings.setValue("backup_time", self.time_edit.time().toString("hh:mm"))
        self.settings.setValue("weekday", self.weekday_combo.currentIndex())
        self.settings.setValue("monthday", self.monthday_spin.value())
        self.settings.setValue("keep_history", self.keep_history.isChecked())
        
        # СОХРАНЯЕМ НОВУЮ НАСТРОЙКУ: создание папки резервного копирования
        self.settings.setValue("create_backup_folder", self.create_backup_folder.isChecked())
        
        self.settings.setValue("auto_start", self.auto_start_cb.isChecked())
        self.settings.setValue("timer_active", self.backup_timer.isActive())
        
        self.settings.sync()
    
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
        
        self.save_settings()
            
    def select_destination_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Выберите папку для резервных копий")
        if folder_path:
            self.destination_folder = folder_path
            self.dest_edit.setText(folder_path)
            self.save_settings()
            self.log_message(f"Выбрана папка назначения: {folder_path}")
            
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
        if not (self.source_folders or self.source_files) or not self.destination_folder:
            QMessageBox.warning(self, "Ошибка", "Выберите исходные файлы/папки и папку назначения!")
            return
            
        self.save_settings()
        self.backup_timer.start(60000)  # Проверка каждую минуту
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        next_time = self.calculate_next_backup_time()
        self.next_backup_time = next_time
        self.update_next_backup_label()
        
        period_type = self.period_type_combo.currentText()
        self.log_message(f"Автоматическое копирование запущено. Период: {period_type}")
        self.statusBar().showMessage("Копирование запущено")
        
    def stop_backup(self):
        self.backup_timer.stop()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.next_backup_label.setText("Следующее копирование: не запланировано")
        self.save_settings()
        self.log_message("Автоматическое копирование остановлено")
        self.statusBar().showMessage("Копирование остановлено")
        
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
        if not (self.source_folders or self.source_files) or not self.destination_folder:
            QMessageBox.warning(self, "Ошибка", "Выберите исходные файлы/папки и папку назначения!")
            return
            
        self.perform_backup()
        
    def perform_backup(self):
        try:
            if not (self.source_folders or self.source_files) or not self.destination_folder:
                self.log_message("Ошибка: не выбраны исходные файлы/папки или папка назначения!")
                return
            
            # ОПРЕДЕЛЯЕМ ПАПКУ НАЗНАЧЕНИЯ С УЧЕТОМ НОВОЙ НАСТРОЙКИ
            actual_destination = self.destination_folder
            
            if self.create_backup_folder.isChecked():
                # Создаем папку с названием "Резервное копирование" + дата
                current_date = datetime.now().strftime("%d-%m-%Y")
                backup_folder_name = f"Резервное копирование {current_date}"
                actual_destination = os.path.join(self.destination_folder, backup_folder_name)
                
                # Создаем папку, если она не существует
                if not os.path.exists(actual_destination):
                    os.makedirs(actual_destination)
                    self.log_message(f"Создана папка для резервного копирования: {backup_folder_name}")
            
            if not os.path.exists(actual_destination):
                os.makedirs(actual_destination)
            
            files_to_copy = self.get_files_to_copy()
            
            if not files_to_copy:
                self.log_message("Нет файлов для копирования")
                return
            
            copied_count = 0
            total_size = 0
            
            for file_path in files_to_copy:
                try:
                    if not os.path.exists(file_path):
                        continue
                    
                    # Определяем путь назначения
                    # Для файлов из папок сохраняем структуру каталогов
                    dest_path = file_path
                    for folder_path in self.source_folders:
                        if file_path.startswith(folder_path):
                            rel_path = os.path.relpath(file_path, folder_path)
                            dest_path = os.path.join(actual_destination, rel_path)
                            break
                    else:
                        # Для отдельных файлов сохраняем только имя файла
                        dest_path = os.path.join(actual_destination, os.path.basename(file_path))
                    
                    # Создаем папки если нужно
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    
                    # Добавляем timestamp если нужно
                    if self.keep_history.isChecked():
                        name, ext = os.path.splitext(dest_path)
                        timestamp = datetime.now().strftime("%d.%m.%Y_%H-%M")
                        dest_path = f"{name}_{timestamp}{ext}"
                    
                    shutil.copy2(file_path, dest_path)
                    file_size = os.path.getsize(dest_path) / 1024
                    total_size += file_size
                    copied_count += 1
                    
                except Exception as e:
                    self.log_message(f"✗ Ошибка при копировании {os.path.basename(file_path)}: {str(e)}")
            
            if copied_count > 0:
                self.log_message(f"✓ Скопировано {copied_count} файлов ({total_size:.2f} KB)")
                self.statusBar().showMessage(f"Последнее копирование: {datetime.now().strftime('%H:%M:%S')}")
                self.last_backup_date = datetime.now()
            else:
                self.log_message("✗ Не удалось скопировать ни одного файла")
                
        except Exception as e:
            self.log_message(f"✗ Ошибка при копировании: {str(e)}")
            
    def log_message(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        
    def closeEvent(self, event):
        """Сохраняем настройки при закрытии приложения"""
        self.save_settings()
        if self.backup_timer.isActive():
            self.backup_timer.stop()
        event.accept()

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = BackupApp()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
