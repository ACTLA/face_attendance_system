"""
Главный файл запуска упрощенной системы распознавания лиц
"""
import sys
import os
import logging
from pathlib import Path

# Добавление путей для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication, QMessageBox, QSplashScreen, QLabel
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QFont, QPainter, QLinearGradient, QBrush, QColor

from config import (WINDOW_TITLE, LOG_LEVEL, LOG_FORMAT, 
                   LOG_MAX_BYTES, LOG_BACKUP_COUNT, LOGS_DIR)
from ui.login_window import LoginWindow
from ui.main_window import MainWindow

def setup_logging():
    """Настройка логирования"""
    try:
        # Создание директории для логов
        LOGS_DIR.mkdir(exist_ok=True)
        
        # Настройка логирования
        from logging.handlers import RotatingFileHandler
        
        # Корневой логгер
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
        
        # Очистка существующих обработчиков
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Форматтер
        formatter = logging.Formatter(LOG_FORMAT)
        
        # Консольный обработчик
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        # Файловый обработчик
        log_file = LOGS_DIR / 'face_recognition.log'
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        
        logging.info("Логирование настроено успешно")
        
    except Exception as e:
        print(f"Ошибка настройки логирования: {e}")

def check_dependencies():
    """Проверка необходимых зависимостей"""
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
        return missing_deps
    
    return None

def check_camera():
    """Проверка доступности камеры"""
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()
            return ret and frame is not None
        return False
    except Exception:
        return False

class FaceRecognitionApp:
    """Главный класс приложения"""
    
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setApplicationName(WINDOW_TITLE)
        
        # Установка стиля
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
                min-height: 30px;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
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
        """)
        
        self.login_window = None
        self.main_window = None
        
        logging.info("Приложение инициализировано")
    
    def show_splash_screen(self):
        """Показ заставки при запуске"""
        splash = QSplashScreen()
        splash.setFixedSize(400, 250)
        
        # Создание pixmap для заставки
        pixmap = QPixmap(400, 250)
        pixmap.fill(Qt.white)
        
        painter = QPainter(pixmap)
        
        # Градиентный фон
        gradient = QLinearGradient(0, 0, 400, 250)
        gradient.setColorAt(0, QColor.fromRgb(59, 93, 212))
        gradient.setColorAt(1, QColor.fromRgb(118, 75, 162))
        painter.fillRect(0, 0, 400, 250, QBrush(gradient))
        
        
        painter.setFont(QFont("Arial", 14))
        painter.drawText(20, 120, 360, 25, Qt.AlignCenter, "Система распознавания лиц")
        
        painter.setFont(QFont("Arial", 12))
        painter.drawText(20, 200, 360, 25, Qt.AlignCenter, "Загрузка...")
        
        painter.end()
        
        splash.setPixmap(pixmap)
        splash.show()
        
        # Обработка событий
        self.app.processEvents()
        
        # Автоматическое скрытие через 2 секунды
        QTimer.singleShot(2000, lambda: self.hide_splash_and_show_login(splash))
        
        return splash
    
    def hide_splash_and_show_login(self, splash):
        """Скрытие заставки и показ окна входа"""
        splash.close()
        self.show_login()
    
    def show_login(self):
        """Показать окно входа"""
        self.login_window = LoginWindow()
        self.login_window.login_successful.connect(self.on_login_success)
        self.login_window.show()
        logging.info("Показано окно входа")
    
    def on_login_success(self, admin_data):
        """Обработка успешного входа"""
        logging.info(f"Успешный вход пользователя: {admin_data['username']}")
        
        if self.login_window:
            self.login_window.close()
        
        self.main_window = MainWindow(admin_data)
        self.main_window.show()
        
        logging.info("Показано главное окно")
    
    def run(self):
        """Запуск приложения"""
        try:
            # Показ заставки
            splash = self.show_splash_screen()
            
            # Запуск основного цикла
            return self.app.exec_()
            
        except Exception as e:
            logging.error(f"Критическая ошибка приложения: {e}")
            QMessageBox.critical(None, "Критическая ошибка", 
                               f"Произошла критическая ошибка:\n{str(e)}")
            return 1

def main():
    """Точка входа в приложение"""
    print("🚀 Запуск системы распознавания лиц...")
    
    try:
        # Настройка логирования
        setup_logging()
        logging.info("=" * 50)
        logging.info("Запуск системы распознавания лиц")
        logging.info("=" * 50)
        
        # Проверка зависимостей
        print("📦 Проверка зависимостей...")
        missing_deps = check_dependencies()
        
        if missing_deps:
            error_msg = (
                "Отсутствуют необходимые библиотеки:\n\n" +
                "\n".join(f"• {dep}" for dep in missing_deps) +
                "\n\nУстановите их с помощью команды:\n" +
                f"pip install {' '.join(missing_deps)}"
            )
            
            # Показываем ошибку через GUI если возможно
            try:
                app = QApplication(sys.argv)
                QMessageBox.critical(None, "Ошибка зависимостей", error_msg)
            except:
                print(error_msg)
            
            logging.error(f"Отсутствуют зависимости: {missing_deps}")
            return 1
        
        logging.info("Все зависимости найдены")
        
        # Проверка камеры
        print("📷 Проверка камеры...")
        if check_camera():
            print("✅ Камера доступна")
            logging.info("Камера доступна")
        else:
            print("⚠️  Предупреждение: Камера недоступна")
            logging.warning("Камера недоступна - функции распознавания могут не работать")
        
        # Создание необходимых директорий
        from config import DATA_DIR, USER_PHOTOS_DIR
        for directory in [DATA_DIR, USER_PHOTOS_DIR, LOGS_DIR]:
            directory.mkdir(exist_ok=True)
        
        logging.info("Необходимые директории созданы")
        
        # Запуск приложения
        print("🎯 Запуск приложения...")
        app = FaceRecognitionApp()
        exit_code = app.run()
        
        logging.info(f"Приложение завершено с кодом: {exit_code}")
        print("👋 Приложение завершено")
        
        return exit_code
        
    except KeyboardInterrupt:
        print("\n⏹️ Приложение прервано пользователем")
        logging.info("Приложение прервано пользователем")
        return 0
        
    except Exception as e:
        error_msg = f"Критическая ошибка: {str(e)}"
        print(f"❌ {error_msg}")
        logging.critical(error_msg, exc_info=True)
        
        # Показываем ошибку через GUI если возможно
        try:
            app = QApplication(sys.argv)
            QMessageBox.critical(None, "Критическая ошибка", error_msg)
        except:
            pass
        
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)