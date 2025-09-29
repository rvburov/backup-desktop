# Базавая программа
import sys
import os
import shutil
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QFileDialog, QTextEdit, QSpinBox, QComboBox,
                             QGroupBox, QMessageBox, QCheckBox)
from PyQt5.QtCore import QTimer


class BackupApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Резервное копирование файлов")
        self.setGeometry(100, 100, 800, 600)
        
        self.source_file = ""
        self.destination_folder = ""
        self.backup_timer = QTimer()
        self.backup_timer.timeout.connect(self.perform_backup)
        
        self.init_ui()
        
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Группа выбора файлов
        file_group = QGroupBox("Выбор файлов")
        file_layout = QVBoxLayout(file_group)
        
        # Исходный файл
        source_layout = QHBoxLayout()
        source_layout.addWidget(QLabel("Исходный файл:"))
        self.source_edit = QLineEdit()
        self.source_edit.setReadOnly(True)
        source_layout.addWidget(self.source_edit)
        self.source_btn = QPushButton("Выбрать файл")
        self.source_btn.clicked.connect(self.select_source_file)
        source_layout.addWidget(self.source_btn)
        file_layout.addLayout(source_layout)
        
        # Папка назначения
        dest_layout = QHBoxLayout()
        dest_layout.addWidget(QLabel("Папка назначения:"))
        self.dest_edit = QLineEdit()
        self.dest_edit.setReadOnly(True)
        dest_layout.addWidget(self.dest_edit)
        self.dest_btn = QPushButton("Выбрать папку")
        self.dest_btn.clicked.connect(self.select_destination_folder)
        dest_layout.addWidget(self.dest_btn)
        file_layout.addLayout(dest_layout)
        
        layout.addWidget(file_group)
        
        # Группа настроек резервного копирования
        settings_group = QGroupBox("Настройки резервного копирования")
        settings_layout = QVBoxLayout(settings_group)
        
        # Период копирования
        period_layout = QHBoxLayout()
        period_layout.addWidget(QLabel("Период копирования:"))
        self.period_spin = QSpinBox()
        self.period_spin.setMinimum(1)
        self.period_spin.setMaximum(999)
        self.period_spin.setValue(60)
        period_layout.addWidget(self.period_spin)
        
        self.period_combo = QComboBox()
        self.period_combo.addItems(["секунд", "минут", "часов"])
        period_layout.addWidget(self.period_combo)
        settings_layout.addLayout(period_layout)
        
        # Сохранять историю копий
        self.keep_history = QCheckBox("Сохранять историю копий (добавлять дату к имени файла)")
        self.keep_history.setChecked(True)
        settings_layout.addWidget(self.keep_history)
        
        layout.addWidget(settings_group)
        
        # Кнопки управления
        button_layout = QHBoxLayout()
        self.start_btn = QPushButton("Запустить копирование")
        self.start_btn.clicked.connect(self.start_backup)
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        
        self.stop_btn = QPushButton("Остановить копирование")
        self.stop_btn.clicked.connect(self.stop_backup)
        self.stop_btn.setStyleSheet("background-color: #f44336; color: white;")
        self.stop_btn.setEnabled(False)
        
        self.manual_btn = QPushButton("Ручное копирование")
        self.manual_btn.clicked.connect(self.manual_backup)
        self.manual_btn.setStyleSheet("background-color: #2196F3; color: white;")
        
        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.stop_btn)
        button_layout.addWidget(self.manual_btn)
        layout.addLayout(button_layout)
        
        # Лог операций
        log_group = QGroupBox("Лог операций")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        layout.addWidget(log_group)
        
        # Статус бар
        self.statusBar().showMessage("Готов к работе")
        
    def select_source_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите файл для копирования")
        if file_path:
            self.source_file = file_path
            self.source_edit.setText(file_path)
            self.log_message(f"Выбран исходный файл: {file_path}")
            
    def select_destination_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Выберите папку для резервных копий")
        if folder_path:
            self.destination_folder = folder_path
            self.dest_edit.setText(folder_path)
            self.log_message(f"Выбрана папка назначения: {folder_path}")
            
    def calculate_interval(self):
        period = self.period_spin.value()
        unit = self.period_combo.currentText()
        
        if unit == "секунд":
            return period * 1000  # мс
        elif unit == "минут":
            return period * 60 * 1000  # мс
        elif unit == "часов":
            return period * 60 * 60 * 1000  # мс
        return 60000  # по умолчанию 1 минута
    
    def start_backup(self):
        if not self.source_file or not self.destination_folder:
            QMessageBox.warning(self, "Ошибка", "Выберите исходный файл и папку назначения!")
            return
            
        interval = self.calculate_interval()
        self.backup_timer.start(interval)
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        unit = self.period_combo.currentText()
        self.log_message(f"Автоматическое копирование запущено. Период: {self.period_spin.value()} {unit}")
        self.statusBar().showMessage("Копирование запущено")
        
        # Сразу выполнить первое копирование
        self.perform_backup()
        
    def stop_backup(self):
        self.backup_timer.stop()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.log_message("Автоматическое копирование остановлено")
        self.statusBar().showMessage("Копирование остановлено")
        
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
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                dest_filename = f"{name}_{timestamp}{ext}"
            else:
                dest_filename = filename
                
            dest_path = os.path.join(self.destination_folder, dest_filename)
            shutil.copy2(self.source_file, dest_path)
            
            file_size = os.path.getsize(dest_path) / 1024  # KB
            self.log_message(f"✓ Файл скопирован: {dest_filename} ({file_size:.2f} KB)")
            self.statusBar().showMessage(f"Последнее копирование: {datetime.now().strftime('%H:%M:%S')}")
            
        except Exception as e:
            self.log_message(f"✗ Ошибка при копировании: {str(e)}")
            
    def log_message(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        
    def closeEvent(self, event):
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
