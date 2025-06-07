"""
Главный файл запуска автоматизированной системы распознавания лиц
"""
import sys
import os
from PyQt5.QtWidgets import QApplication, QMessageBox, QSplashScreen
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QFont, QColor

# Добавление текущей директории в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ui.login_window import LoginWindow
from ui.main_window import MainWindow
from config import (WINDOW_TITLE, COMPANY_NAME, WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

class FaceRecognitionApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setApplicationName(WINDOW_TITLE)
        self.app.setOrganizationName(COMPANY_NAME)
        
        # Установка стиля приложения
        self.app.setStyle('Fusion')
        
        # Глобальные стили
        self.app.setStyleSheet("""
            QWidget {
                font-family: 'Segoe UI', 'Arial', sans-serif;
            }
            QMessageBox {
                background-color: white;
                min-width: 300px;
            }
            QMessageBox QPushButton {
                min-width: 80px;
                min-height: 35px;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
            }
            QMessageBox QLabel {
                min-height: 50px;
                font-size: 14px;
            }
            QScrollBar:vertical {
                background-color: #f0f0f0;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #c0c0c0;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #a0a0a0;
            }
            QScrollBar:horizontal {
                background-color: #f0f0f0;
                height: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background-color: #c0c0c0;
                border-radius: 6px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #a0a0a0;
            }
        """)
        
        self.login_window = None
        self.main_window = None
        
        # Показ splash screen
        self.show_splash_screen()
    
    def show_splash_screen(self):
        """Показ заставки при запуске"""
        # Создание простой заставки
        splash = QSplashScreen()
        splash.setFixedSize(400, 300)
        
        # Создание pixmap для заставки
        pixmap = QPixmap(400, 300)
        pixmap.fill(Qt.white)
        
        from PyQt5.QtGui import QPainter, QLinearGradient, QBrush, QColor
        painter = QPainter(pixmap)
        
        # Градиентный фон
        gradient = QLinearGradient(0, 0, 400, 300)
        gradient.setColorAt(0, QColor.fromRgb(102, 126, 234))
        gradient.setColorAt(1, QColor.fromRgb(118, 75, 162))
        painter.fillRect(0, 0, 400, 300, QBrush(gradient))
        
        # Текст
        painter.setPen(Qt.white)
        painter.setFont(QFont("Arial", 24, QFont.Bold))
        painter.drawText(20, 100, 360, 50, Qt.AlignCenter, COMPANY_NAME)
        
        painter.setFont(QFont("Arial", 16))
        painter.drawText(20, 150, 360, 30, Qt.AlignCenter, "Автоматизированная система")
        painter.drawText(20, 180, 360, 30, Qt.AlignCenter, "распознавания лиц")
        
        painter.setFont(QFont("Arial", 12))
        painter.drawText(20, 250, 360, 30, Qt.AlignCenter, "Загрузка...")
        
        painter.end()
        
        splash.setPixmap(pixmap)
        splash.show()
        
        # Обработка событий для отображения заставки
        self.app.processEvents()
        
        # Таймер для скрытия заставки
        QTimer.singleShot(2000, lambda: self.hide_splash_and_show_login(splash))
    
    def hide_splash_and_show_login(self, splash):
        """Скрытие заставки и показ окна входа"""
        splash.close()
        self.show_login()
    
    def run(self):
        """Запуск приложения"""
        return self.app.exec_()
    
    def show_login(self):
        """Показать окно входа"""
        self.login_window = LoginWindow()
        self.login_window.login_successful.connect(self.on_login_success)
        self.login_window.show()
    
    def on_login_success(self, admin_data):
        """Обработка успешного входа"""
        self.login_window.close()
        self.main_window = MainWindow(admin_data)
        
        # Центрирование и размеры главного окна
        from PyQt5.QtWidgets import QDesktopWidget
        desktop = QDesktopWidget()
        screen_rect = desktop.screenGeometry()
        
        # Центрирование окна
        window_size = self.main_window.geometry()
        x = max(0, (screen_rect.width() - window_size.width()) // 2)
        y = max(0, (screen_rect.height() - window_size.height()) // 2)
        self.main_window.move(x, y)
        
        self.main_window.show()

def check_dependencies():
    """Проверка зависимостей"""
    missing_deps = []
    
    try:
        import cv2
    except ImportError:
        missing_deps.append("opencv-python")
    
    try:
        import face_recognition
    except ImportError:
        missing_deps.append("face-recognition")
    
    try:
        import numpy
    except ImportError:
        missing_deps.append("numpy")
    
    try:
        from PyQt5 import QtWidgets
    except ImportError:
        missing_deps.append("PyQt5")
    
    if missing_deps:
        app = QApplication(sys.argv)
        error_msg = (
            "Отсутствуют необходимые библиотеки:\n\n" +
            "\n".join(f"• {dep}" for dep in missing_deps) +
            "\n\nУстановите их с помощью команды:\n" +
            f"pip install {' '.join(missing_deps)}"
        )
        QMessageBox.critical(None, "Ошибка зависимостей", error_msg)
        sys.exit(1)

def create_directories():
    """Создание необходимых директорий"""
    from config import USER_PHOTOS_DIR, DATA_DIR, RESOURCES_DIR
    
    directories = [
        DATA_DIR,
        USER_PHOTOS_DIR,
        RESOURCES_DIR / 'icons'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

def main():
    """Точка входа в приложение"""
    print("🚀 Запуск автоматизированной системы распознавания лиц...")
    
    # Проверка зависимостей
    print("📦 Проверка зависимостей...")
    check_dependencies()
    
    # Создание необходимых директорий
    print("📁 Создание директорий...")
    create_directories()
    
    # Проверка камеры
    print("📷 Проверка доступности камеры...")
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("⚠️  Предупреждение: Камера недоступна. Функции распознавания могут не работать.")
        else:
            print("✅ Камера доступна")
        cap.release()
    except Exception as e:
        print(f"⚠️  Предупреждение: Ошибка при проверке камеры: {e}")
    
    # Запуск приложения
    print("🎯 Запуск приложения...")
    app = FaceRecognitionApp()
    
    try:
        exit_code = app.run()
        print("👋 Приложение завершено")
        sys.exit(exit_code)
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()