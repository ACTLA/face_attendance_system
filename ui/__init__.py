"""
Пакет пользовательского интерфейса для системы распознавания лиц
"""
from .login_window import LoginWindow
from .main_window import MainWindow
from .add_user_dialog import AddUserDialog
from .face_recognition_widget import FaceRecognitionWidget

__all__ = [
    'LoginWindow',
    'MainWindow', 
    'AddUserDialog',
    'FaceRecognitionWidget'
]