"""
Окно регистрации нового пользователя
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QLineEdit, QPushButton, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from database import Database
from config import WINDOW_TITLE, PRIMARY_COLOR, PASSWORD_MIN_LENGTH

class SignupWindow(QWidget):
    signup_successful = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle(f"Sign Up - {WINDOW_TITLE}")
        self.setFixedSize(500, 600)
        
        # Основной layout
        layout = QVBoxLayout()
        layout.setContentsMargins(50, 50, 50, 50)
        self.setLayout(layout)
        
        # Иконка
        icon_label = QLabel("👤")
        icon_label.setFont(QFont("Arial", 60))
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)
        
        # Заголовок
        title = QLabel("Sign Up")
        title.setFont(QFont("Arial", 28, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        layout.addSpacing(30)
        
        # Поля ввода
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.username_input.setStyleSheet(self.get_input_style())
        layout.addWidget(self.username_input)
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email")
        self.email_input.setStyleSheet(self.get_input_style())
        layout.addWidget(self.email_input)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet(self.get_input_style())
        layout.addWidget(self.password_input)
        
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setPlaceholderText("Confirm Password")
        self.confirm_password_input.setEchoMode(QLineEdit.Password)
        self.confirm_password_input.setStyleSheet(self.get_input_style())
        layout.addWidget(self.confirm_password_input)
        
        layout.addSpacing(20)
        
        # Кнопка регистрации
        self.register_button = QPushButton("Register")
        self.register_button.setFont(QFont("Arial", 14, QFont.Bold))
        self.register_button.setCursor(Qt.PointingHandCursor)
        self.register_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {PRIMARY_COLOR};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #2d4aa3;
            }}
        """)
        self.register_button.clicked.connect(self.handle_signup)
        layout.addWidget(self.register_button)
        
        # Ссылка на вход
        login_layout = QHBoxLayout()
        login_layout.setAlignment(Qt.AlignCenter)
        
        login_text = QLabel("Already a User?")
        login_text.setStyleSheet("color: #666;")
        login_layout.addWidget(login_text)
        
        login_link = QPushButton("Login")
        login_link.setCursor(Qt.PointingHandCursor)
        login_link.setStyleSheet("""
            QPushButton {
                background: none;
                border: none;
                color: #667eea;
                font-weight: bold;
                text-decoration: underline;
            }
            QPushButton:hover {
                color: #4c5fd8;
            }
        """)
        login_link.clicked.connect(self.close)
        login_layout.addWidget(login_link)
        
        layout.addLayout(login_layout)
        
        # Стиль окна
        self.setStyleSheet("""
            QWidget {
                background-color: white;
            }
        """)
        
        # Enter для регистрации
        self.username_input.returnPressed.connect(self.handle_signup)
        self.email_input.returnPressed.connect(self.handle_signup)
        self.password_input.returnPressed.connect(self.handle_signup)
        self.confirm_password_input.returnPressed.connect(self.handle_signup)
    
    def get_input_style(self):
        """Стиль для полей ввода"""
        return """
            QLineEdit {
                padding: 12px;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                font-size: 14px;
                background-color: #f8f9fa;
                margin-bottom: 10px;
            }
            QLineEdit:focus {
                border-color: #667eea;
                background-color: white;
            }
        """
    
    def handle_signup(self):
        """Обработка регистрации"""
        username = self.username_input.text().strip()
        email = self.email_input.text().strip()
        password = self.password_input.text()
        confirm_password = self.confirm_password_input.text()
        
        # Проверка полей
        if not all([username, email, password, confirm_password]):
            QMessageBox.warning(self, "Error", "Please fill in all fields")
            return
        
        # Проверка email
        if '@' not in email or '.' not in email:
            QMessageBox.warning(self, "Error", "Please enter a valid email address")
            return
        
        # Проверка длины пароля
        if len(password) < PASSWORD_MIN_LENGTH:
            QMessageBox.warning(self, "Error", f"Password must be at least {PASSWORD_MIN_LENGTH} characters long")
            return
        
        # Проверка совпадения паролей
        if password != confirm_password:
            QMessageBox.warning(self, "Error", "Passwords do not match")
            return
        
        # Создание пользователя
        if self.db.create_user(username, email, password):
            self.signup_successful.emit()
            self.close()
        else:
            QMessageBox.warning(self, "Error", "Username or email already exists")
    
    def keyPressEvent(self, event):
        """Обработка нажатий клавиш"""
        if event.key() == Qt.Key_Escape:
            self.close()