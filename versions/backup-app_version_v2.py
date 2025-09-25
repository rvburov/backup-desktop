import sys
import os
import shutil
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QFileDialog, QTextEdit, QSpinBox, QComboBox,
                             QGroupBox, QMessageBox, QCheckBox, QTimeEdit, QGridLayout)
from PyQt5.QtCore import QTimer, QTime, QSettings

class BackupApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("MyCompany", "BackupApp")  # Организация и название приложения
        self.setWindowTitle("Резервное копирование файлов")
        self.setGeometry(100, 100, 900, 700)
        
        self.source_file = ""
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
        
        # Группа выбора файлов
        file_group = QGroupBox("Выбор файлов")
        file_layout = QGridLayout(file_group)  

        # Исходный файл
        file_layout.addWidget(QLabel("Исходный файл:"), 0, 0) 
        self.source_edit = QLineEdit()
        self.source_edit.setReadOnly(True)
        file_layout.addWidget(self.source_edit, 0, 1)  
        self.source_btn = QPushButton("Выбрать файл")
        self.source_btn.clicked.connect(self.select_source_file)
        file_layout.addWidget(self.source_btn, 0, 2)  

        # Папка назначения
        file_layout.addWidget(QLabel("Папка назначения:"), 1, 0)  
        self.dest_edit = QLineEdit()
        self.dest_edit.setReadOnly(True)
        file_layout.addWidget(self.dest_edit, 1, 1)  
        self.dest_btn = QPushButton("Выбрать папку")
        self.dest_btn.clicked.connect(self.select_destination_folder)
        file_layout.addWidget(self.dest_btn, 1, 2) 

        layout.addWidget(file_group)
        
        # Группа настроек резервного копирования
        settings_group = QGroupBox("Настройки планирования")
        settings_layout = QGridLayout(settings_group)
        
        # Тип периода
        settings_layout.addWidget(QLabel("Тип периода:"), 0, 0)
        self.period_type_combo = QComboBox()
        self.period_type_combo.addItems(["Ежедневно", "Еженедельно", "Ежемесячно"])
        self.period_type_combo.currentTextChanged.connect(self.update_ui_for_period)
        settings_layout.addWidget(self.period_type_combo, 0, 1)
        
        # Время копирования
        settings_layout.addWidget(QLabel("Время копирования:"), 1, 0)
        self.time_edit = QTimeEdit()
        self.time_edit.setTime(QTime.currentTime())
        settings_layout.addWidget(self.time_edit, 1, 1)
        
        # День недели (для еженедельного) - строка 2
        self.weekday_label = QLabel("День недели:")
        self.weekday_combo = QComboBox()
        self.weekday_combo.addItems(["Понедельник", "Вторник", "Среда", "Четверг", 
                                   "Пятница", "Суббота", "Воскресенье"])
        
        settings_layout.addWidget(self.weekday_label, 2, 0)
        settings_layout.addWidget(self.weekday_combo, 2, 1)
        
        # День месяца (для ежемесячного) - строка 3
        self.monthday_label = QLabel("День месяца:")
        self.monthday_spin = QSpinBox()
        self.monthday_spin.setRange(1, 31)
        self.monthday_spin.setValue(1)
        
        settings_layout.addWidget(self.monthday_label, 3, 0)
        settings_layout.addWidget(self.monthday_spin, 3, 1)
        
        # Сохранять историю копий - строка 4
        self.keep_history = QCheckBox("Сохранять историю копий (добавлять дату к имени файла)")
        self.keep_history.setChecked(True)
        settings_layout.addWidget(self.keep_history, 4, 0, 1, 2)  # Занимает 2 колонки
        
        # Изначально скрываем все дополнительные элементы
        self.hide_all_additional_elements()
        
        layout.addWidget(settings_group)
        
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
        log_group = QGroupBox("История копирование файлов")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        layout.addWidget(log_group)
        
        # Статус бар
        self.statusBar().showMessage("Готов к работе")
    
    def load_settings(self):
        """Загружает сохраненные настройки"""
        # Загружаем пути к файлам и папкам
        source_file = self.settings.value("source_file", "")
        destination_folder = self.settings.value("destination_folder", "")
        
        if source_file and os.path.exists(source_file):
            self.source_file = source_file
            self.source_edit.setText(source_file)
            
        if destination_folder and os.path.exists(destination_folder):
            self.destination_folder = destination_folder
            self.dest_edit.setText(destination_folder)
        
        # Загружаем настройки планирования
        period_type = self.settings.value("period_type", "Ежедневно")
        index = self.period_type_combo.findText(period_type)
        if index >= 0:
            self.period_type_combo.setCurrentIndex(index)
        
        # Загружаем время
        time_str = self.settings.value("backup_time", "00:00")
        time = QTime.fromString(time_str, "hh:mm")
        if time.isValid():
            self.time_edit.setTime(time)
        
        # Загружаем день недели
        weekday = self.settings.value("weekday", 0, type=int)
        if 0 <= weekday < self.weekday_combo.count():
            self.weekday_combo.setCurrentIndex(weekday)
        
        # Загружаем день месяца
        monthday = self.settings.value("monthday", 1, type=int)
        self.monthday_spin.setValue(monthday)
        
        # Загружаем настройку истории
        keep_history = self.settings.value("keep_history", True, type=bool)
        self.keep_history.setChecked(keep_history)
        
        # Загружаем состояние таймера
        timer_active = self.settings.value("timer_active", False, type=bool)
        if timer_active:
            self.start_backup_from_settings()
        
        self.log_message("Настройки загружены")
        
    def save_settings(self):
        """Сохраняет текущие настройки"""
        # Сохраняем пути
        self.settings.setValue("source_file", self.source_file)
        self.settings.setValue("destination_folder", self.destination_folder)
        
        # Сохраняем настройки планирования
        self.settings.setValue("period_type", self.period_type_combo.currentText())
        self.settings.setValue("backup_time", self.time_edit.time().toString("hh:mm"))
        self.settings.setValue("weekday", self.weekday_combo.currentIndex())
        self.settings.setValue("monthday", self.monthday_spin.value())
        self.settings.setValue("keep_history", self.keep_history.isChecked())
        
        # Сохраняем состояние таймера
        self.settings.setValue("timer_active", self.backup_timer.isActive())
        
        # Принудительно сохраняем настройки
        self.settings.sync()
        
    def start_backup_from_settings(self):
        """Запускает копирование из сохраненных настроек"""
        if not self.source_file or not self.destination_folder:
            return
            
        self.backup_timer.start(60000)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        next_time = self.calculate_next_backup_time()
        self.next_backup_time = next_time
        self.update_next_backup_label()
        
        period_type = self.period_type_combo.currentText()
        self.log_message(f"Автоматическое копирование восстановлено. Период: {period_type}")
        self.statusBar().showMessage("Копирование запущено")
    
    def hide_all_additional_elements(self):
        """Скрывает все дополнительные элементы"""
        self.weekday_label.setVisible(False)
        self.weekday_combo.setVisible(False)
        self.monthday_label.setVisible(False)
        self.monthday_spin.setVisible(False)
        
    def update_ui_for_period(self, period_type):
        """Обновляет интерфейс в зависимости от выбранного типа периода"""
        # Сначала скрываем все дополнительные элементы
        self.hide_all_additional_elements()
        
        if period_type == "Еженедельно":
            self.weekday_label.setVisible(True)
            self.weekday_combo.setVisible(True)
            # Скрываем день месяца
            self.monthday_label.setVisible(False)
            self.monthday_spin.setVisible(False)
        elif period_type == "Ежемесячно":
            self.monthday_label.setVisible(True)
            self.monthday_spin.setVisible(True)
            # Скрываем день недели
            self.weekday_label.setVisible(False)
            self.weekday_combo.setVisible(False)
        else:  # Ежедневно
            # Скрываем все дополнительные элементы
            self.hide_all_additional_elements()
        
        # Сохраняем настройки при изменении
        self.save_settings()
            
    def select_source_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите файл для копирования")
        if file_path:
            self.source_file = file_path
            self.source_edit.setText(file_path)
            self.save_settings()  # Сохраняем после выбора
            self.log_message(f"Выбран исходный файл: {file_path}")
            
    def select_destination_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Выберите папку для резервных копий")
        if folder_path:
            self.destination_folder = folder_path
            self.dest_edit.setText(folder_path)
            self.save_settings()  # Сохраняем после выбора
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
            weekday = self.weekday_combo.currentIndex()  # 0=понедельник, 6=воскресенье
            current_weekday = now.weekday()  # 0=понедельник, 6=воскресенье
            
            days_ahead = (weekday - current_weekday) % 7
            if days_ahead == 0 and backup_time_dt > now:
                next_time = backup_time_dt
            else:
                if days_ahead == 0:
                    days_ahead = 7
                next_time = backup_time_dt + timedelta(days=days_ahead)
                
        elif period_type == "Ежемесячно":
            day_of_month = self.monthday_spin.value()
            
            # Проверяем, существует ли такой день в текущем месяце
            try:
                test_date = datetime(now.year, now.month, day_of_month)
                next_time = datetime(now.year, now.month, day_of_month, 
                                   backup_time.hour(), backup_time.minute(), backup_time.second())
            except ValueError:
                # Если дня не существует (например, 31 февраля), используем последний день месяца
                next_month = now.replace(day=28) + timedelta(days=4)  # Переходим к следующему месяцу
                next_month = next_month.replace(day=1)
                last_day = (next_month - timedelta(days=1)).day
                day_of_month = min(day_of_month, last_day)
                next_time = datetime(now.year, now.month, day_of_month, 
                                   backup_time.hour(), backup_time.minute(), backup_time.second())
            
            if next_time < now:
                # Переходим к следующему месяцу
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
        if not self.source_file or not self.destination_folder:
            QMessageBox.warning(self, "Ошибка", "Выберите исходный файл и папку назначения!")
            return
            
        self.save_settings()  # Сохраняем перед запуском
        
        # Запускаем таймер, который проверяет время каждую минуту
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
        self.save_settings()  # Сохраняем при остановке
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
        if not self.source_file or not self.destination_folder:
            QMessageBox.warning(self, "Ошибка", "Выберите исходный файл и папку назначения!")
            return
            
        self.perform_backup()
        
    def perform_backup(self):
        try:
            if not os.path.exists(self.source_file):
                self.log_message("Ошибка: исходный файл не существует!")
                return
                
            if not os.path.exists(self.destination_folder):
                os.makedirs(self.destination_folder)
                
            filename = os.path.basename(self.source_file)
            name, ext = os.path.splitext(filename)
            
            if self.keep_history.isChecked():
                timestamp = datetime.now().strftime("%d.%m.%Y_%H-%M")
                dest_filename = f"{name}_{timestamp}{ext}"
            else:
                dest_filename = filename
                
            dest_path = os.path.join(self.destination_folder, dest_filename)
            shutil.copy2(self.source_file, dest_path)
            
            file_size = os.path.getsize(dest_path) / 1024  # KB
            self.log_message(f"✓ Файл скопирован: {dest_filename} ({file_size:.2f} KB)")
            self.statusBar().showMessage(f"Последнее копирование: {datetime.now().strftime('%H:%M:%S')}")
            self.last_backup_date = datetime.now()
            
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
