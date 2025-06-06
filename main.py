"""
Главный файл запуска приложения системы распознавания лиц
"""
import sys
import os
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt

# Добавление текущей директории в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ui.login_window import LoginWindow
from ui.main_window import MainWindow
from config import WINDOW_TITLE, COMPANY_NAME

class FaceAttendanceApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setApplicationName(WINDOW_TITLE)
        self.app.setOrganizationName(COMPANY_NAME)
        
        # Установка стиля приложения
        self.app.setStyle('Fusion')
        
        # Глобальные стили
        self.app.setStyleSheet("""
            QWidget {
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QMessageBox {
                background-color: white;
            }
            QMessageBox QPushButton {
                min-width: 80px;
                min-height: 30px;
            }
        """)
        
        self.login_window = None
        self.main_window = None
    
    def run(self):
        """Запуск приложения"""
        self.show_login()
        return self.app.exec_()
    
    def show_login(self):
        """Показать окно входа"""
        self.login_window = LoginWindow()
        self.login_window.login_successful.connect(self.on_login_success)
        self.login_window.show()
    
    def on_login_success(self, user_data):
        """Обработка успешного входа"""
        self.login_window.close()
        self.main_window = MainWindow(user_data)
        self.main_window.show()

def main():
    """Точка входа в приложение"""
    # Проверка зависимостей
    try:
        import cv2
        import face_recognition
        import numpy
    except ImportError as e:
        QMessageBox.critical(None, "Missing Dependencies", 
                           f"Required libraries are not installed.\n\n"
                           f"Please install requirements:\n"
                           f"pip install -r requirements.txt\n\n"
                           f"Error: {str(e)}")
        sys.exit(1)
    
    # Создание необходимых директорий
    from config import DATA_DIR, EMPLOYEE_PHOTOS_DIR, RESOURCES_DIR
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(EMPLOYEE_PHOTOS_DIR, exist_ok=True)
    os.makedirs(RESOURCES_DIR / 'icons', exist_ok=True)
    
    # Запуск приложения
    app = FaceAttendanceApp()
    sys.exit(app.run())

if __name__ == "__main__":
    main()