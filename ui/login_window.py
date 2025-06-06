"""
Окно входа в систему
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QLineEdit, QPushButton, QCheckBox, QFrame,
                           QMessageBox, QGraphicsDropShadowEffect)
from PyQt5.QtCore import Qt, pyqtSignal, QPropertyAnimation, QRect
from PyQt5.QtGui import QFont, QPalette, QColor, QPixmap, QPainter, QBrush

from database import Database
from config import WINDOW_TITLE, PRIMARY_COLOR, COMPANY_NAME

class LoginWindow(QWidget):
    login_successful = pyqtSignal(dict)  # Сигнал успешного входа
    
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle(f"Login - {WINDOW_TITLE}")
        self.setFixedSize(900, 600)
        
        # Основной layout
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Левая панель (форма входа)
        left_panel = QFrame()
        left_panel.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: none;
            }}
        """)
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(60, 60, 60, 60)
        
        # Заголовок
        title_label = QLabel("Login")
        title_label.setFont(QFont("Arial", 28, QFont.Bold))
        title_label.setStyleSheet("color: #333;")
        
        # Форма
        form_layout = QVBoxLayout()
        form_layout.setSpacing(20)
        
        # Username/Email
        username_label = QLabel("Email / Username")
        username_label.setFont(QFont("Arial", 11))
        username_label.setStyleSheet("color: #666;")
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        self.username_input.setStyleSheet("""
            QLineEdit {
                padding: 12px;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                font-size: 14px;
                background-color: #f8f9fa;
            }
            QLineEdit:focus {
                border-color: #667eea;
                background-color: white;
            }
        """)
        
        # Password
        password_label = QLabel("Password")
        password_label.setFont(QFont("Arial", 11))
        password_label.setStyleSheet("color: #666;")
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet("""
            QLineEdit {
                padding: 12px;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                font-size: 14px;
                background-color: #f8f9fa;
            }
            QLineEdit:focus {
                border-color: #667eea;
                background-color: white;
            }
        """)
        
        # Remember me
        self.remember_checkbox = QCheckBox("Remember Me")
        self.remember_checkbox.setStyleSheet("""
            QCheckBox {
                color: #666;
                font-size: 14px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
        """)
        
        # Login button
        self.login_button = QPushButton("Sign in")
        self.login_button.setFont(QFont("Arial", 14, QFont.Bold))
        self.login_button.setCursor(Qt.PointingHandCursor)
        self.login_button.setStyleSheet(f"""
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
            QPushButton:pressed {{
                background-color: #1e3670;
            }}
        """)
        self.login_button.clicked.connect(self.handle_login)
        
        # Sign up link
        signup_layout = QHBoxLayout()
        signup_layout.setAlignment(Qt.AlignCenter)
        
        signup_text = QLabel("Need an account?")
        signup_text.setStyleSheet("color: #666; font-size: 14px;")
        
        self.signup_button = QPushButton("Sign up")
        self.signup_button.setCursor(Qt.PointingHandCursor)
        self.signup_button.setStyleSheet("""
            QPushButton {
                background: none;
                border: none;
                color: #667eea;
                font-size: 14px;
                font-weight: bold;
                text-decoration: underline;
            }
            QPushButton:hover {
                color: #4c5fd8;
            }
        """)
        self.signup_button.clicked.connect(self.show_signup)
        
        signup_layout.addWidget(signup_text)
        signup_layout.addWidget(self.signup_button)
        
        # Сборка формы
        form_layout.addWidget(username_label)
        form_layout.addWidget(self.username_input)
        form_layout.addWidget(password_label)
        form_layout.addWidget(self.password_input)
        form_layout.addWidget(self.remember_checkbox)
        form_layout.addSpacing(10)
        form_layout.addWidget(self.login_button)
        
        # Сборка левой панели
        left_layout.addWidget(title_label)
        left_layout.addSpacing(40)
        left_layout.addLayout(form_layout)
        left_layout.addSpacing(30)
        left_layout.addLayout(signup_layout)
        left_layout.addStretch()
        
        left_panel.setLayout(left_layout)
        
        # Правая панель (декоративная)
        right_panel = QFrame()
        right_panel.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #667eea, stop:1 #764ba2);
                border: none;
            }
        """)
        
        right_layout = QVBoxLayout()
        right_layout.setAlignment(Qt.AlignCenter)
        
        # Логотип компании
        company_label = QLabel(COMPANY_NAME)
        company_label.setFont(QFont("Arial", 24, QFont.Bold))
        company_label.setStyleSheet("color: white;")
        company_label.setAlignment(Qt.AlignCenter)
        
        # Описание
        desc_label = QLabel("Face Recognition\nAttendance System")
        desc_label.setFont(QFont("Arial", 16))
        desc_label.setStyleSheet("color: rgba(255, 255, 255, 0.9);")
        desc_label.setAlignment(Qt.AlignCenter)
        
        # Иконка
        icon_label = QLabel("👤")
        icon_label.setFont(QFont("Arial", 80))
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("color: rgba(255, 255, 255, 0.8);")
        
        right_layout.addWidget(icon_label)
        right_layout.addSpacing(30)
        right_layout.addWidget(company_label)
        right_layout.addWidget(desc_label)
        
        right_panel.setLayout(right_layout)
        
        # Сборка главного layout
        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_panel, 1)
        
        self.setLayout(main_layout)
        
        # Эффект тени
        self.setGraphicsEffect(self.create_shadow_effect())
        
        # Enter для входа
        self.username_input.returnPressed.connect(self.handle_login)
        self.password_input.returnPressed.connect(self.handle_login)
        
        # Фокус на поле username
        self.username_input.setFocus()
    
    def create_shadow_effect(self):
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 10)
        return shadow
    
    def handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        
        if not username or not password:
            QMessageBox.warning(self, "Warning", "Please fill in all fields")
            return
        
        # Проверка в базе данных
        user = self.db.authenticate_user(username, password)
        
        if user:
            user_data = {
                'id': user[0],
                'username': user[1],
                'email': user[2]
            }
            self.login_successful.emit(user_data)
            self.close()
        else:
            QMessageBox.critical(self, "Error", "Invalid username or password")
            self.password_input.clear()
            self.password_input.setFocus()
    
    def show_signup(self):
        from .signup_window import SignupWindow
        self.signup_window = SignupWindow()
        self.signup_window.signup_successful.connect(self.on_signup_success)
        self.signup_window.show()
    
    def on_signup_success(self):
        QMessageBox.information(self, "Success", "Registration successful! Please login.")
        self.signup_window.close()
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()