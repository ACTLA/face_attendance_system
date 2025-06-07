"""
Окно входа в автоматизированную систему распознавания лиц
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QLineEdit, QPushButton, QCheckBox, QFrame,
                           QMessageBox, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from database import Database
from config import WINDOW_TITLE, PRIMARY_COLOR, COMPANY_NAME

class LoginWindow(QWidget):
    login_successful = pyqtSignal(dict)  # Сигнал успешного входа
    
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle(f"Вход - {WINDOW_TITLE}")
        self.setMinimumSize(900, 600)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Основной layout
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setLayout(main_layout)
        
        # Левая панель (форма входа)
        left_panel = QFrame()
        left_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left_panel.setStyleSheet("""
            QFrame {
                background-color: white;
                border: none;
            }
        """)
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(60, 60, 60, 60)
        left_layout.setSpacing(20)
        
        # Заголовок
        title_label = QLabel("Авторизация")
        title_label.setFont(QFont("Arial", 32, QFont.Bold))
        title_label.setStyleSheet("color: #333; margin-bottom: 20px;")
        title_label.setAlignment(Qt.AlignCenter)
        
        # Подзаголовок
        subtitle_label = QLabel("Войдите в систему распознавания лиц")
        subtitle_label.setFont(QFont("Arial", 14))
        subtitle_label.setStyleSheet("color: #666; margin-bottom: 30px;")
        subtitle_label.setAlignment(Qt.AlignCenter)
        
        # Форма
        form_layout = QVBoxLayout()
        form_layout.setSpacing(20)
        
        # Username/Email
        username_label = QLabel("Имя пользователя")
        username_label.setFont(QFont("Arial", 12, QFont.Bold))
        username_label.setStyleSheet("color: #333;")
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Введите имя пользователя")
        self.username_input.setMinimumHeight(50)
        self.username_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.username_input.setStyleSheet("""
            QLineEdit {
                padding: 15px;
                border: 2px solid #e0e0e0;
                border-radius: 10px;
                font-size: 16px;
                background-color: #f8f9fa;
            }
            QLineEdit:focus {
                border-color: #667eea;
                background-color: white;
                outline: none;
            }
        """)
        
        # Password
        password_label = QLabel("Пароль")
        password_label.setFont(QFont("Arial", 12, QFont.Bold))
        password_label.setStyleSheet("color: #333;")
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Введите пароль")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(50)
        self.password_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.password_input.setStyleSheet("""
            QLineEdit {
                padding: 15px;
                border: 2px solid #e0e0e0;
                border-radius: 10px;
                font-size: 16px;
                background-color: #f8f9fa;
            }
            QLineEdit:focus {
                border-color: #667eea;
                background-color: white;
                outline: none;
            }
        """)
        
        # Remember me
        self.remember_checkbox = QCheckBox("Запомнить меня")
        self.remember_checkbox.setStyleSheet("""
            QCheckBox {
                color: #666;
                font-size: 14px;
                spacing: 10px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 2px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                background-color: #667eea;
                border-color: #667eea;
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOSIgdmlld0JveD0iMCAwIDEyIDkiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0xMC42IDFMMy44IDguNkwxIDUuNCIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz4KPC9zdmc+);
            }
        """)
        
        # Login button
        self.login_button = QPushButton("🔐 Войти в систему")
        self.login_button.setFont(QFont("Arial", 16, QFont.Bold))
        self.login_button.setCursor(Qt.PointingHandCursor)
        self.login_button.setMinimumHeight(55)
        self.login_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.login_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {PRIMARY_COLOR};
                color: white;
                border: none;
                border-radius: 10px;
                padding: 15px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #2d4aa3;
                transform: translateY(-2px);
            }}
            QPushButton:pressed {{
                background-color: #1e3670;
                transform: translateY(0px);
            }}
        """)
        self.login_button.clicked.connect(self.handle_login)
        
        # Сборка формы
        form_layout.addWidget(username_label)
        form_layout.addWidget(self.username_input)
        form_layout.addWidget(password_label)
        form_layout.addWidget(self.password_input)
        form_layout.addWidget(self.remember_checkbox)
        form_layout.addSpacing(20)
        form_layout.addWidget(self.login_button)
        
        # Сборка левой панели
        left_layout.addWidget(title_label)
        left_layout.addWidget(subtitle_label)
        left_layout.addLayout(form_layout)
        left_layout.addStretch()
        
        # Информация по умолчанию
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 10px;
                padding: 20px;
                border: 1px solid #e9ecef;
            }
        """)
        info_layout = QVBoxLayout()
        info_frame.setLayout(info_layout)
        
        info_title = QLabel("Данные для входа по умолчанию:")
        info_title.setFont(QFont("Arial", 12, QFont.Bold))
        info_title.setStyleSheet("color: #495057;")
        info_layout.addWidget(info_title)
        
        default_creds = QLabel("Логин: admin\nПароль: admin123")
        default_creds.setFont(QFont("Arial", 11))
        default_creds.setStyleSheet("color: #6c757d; margin-top: 5px;")
        info_layout.addWidget(default_creds)
        
        left_layout.addWidget(info_frame)
        
        left_panel.setLayout(left_layout)
        
        # Правая панель (декоративная)
        right_panel = QFrame()
        right_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        right_panel.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #667eea, stop:1 #764ba2);
                border: none;
            }
        """)
        
        right_layout = QVBoxLayout()
        right_layout.setAlignment(Qt.AlignCenter)
        right_layout.setContentsMargins(50, 50, 50, 50)
        
        # Логотип компании
        company_label = QLabel(COMPANY_NAME)
        company_label.setFont(QFont("Arial", 28, QFont.Bold))
        company_label.setStyleSheet("color: white; margin-bottom: 20px;")
        company_label.setAlignment(Qt.AlignCenter)
        company_label.setWordWrap(True)
        
        # Описание
        desc_label = QLabel("Автоматизированная система\nраспознавания лиц")
        desc_label.setFont(QFont("Arial", 18))
        desc_label.setStyleSheet("color: rgba(255, 255, 255, 0.9); margin-bottom: 30px;")
        desc_label.setAlignment(Qt.AlignCenter)
        
        # Иконка
        icon_label = QLabel("🔍")
        icon_label.setFont(QFont("Arial", 120))
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("color: rgba(255, 255, 255, 0.8); margin-bottom: 30px;")
        
        # Возможности системы
        features_label = QLabel("✓ Распознавание лиц в реальном времени\n"
                               "✓ Управление базой пользователей\n"
                               "✓ Детальная отчетность\n"
                               "✓ Высокая точность распознавания")
        features_label.setFont(QFont("Arial", 14))
        features_label.setStyleSheet("color: rgba(255, 255, 255, 0.8); line-height: 1.6;")
        features_label.setAlignment(Qt.AlignLeft)
        
        right_layout.addWidget(icon_label)
        right_layout.addWidget(company_label)
        right_layout.addWidget(desc_label)
        right_layout.addWidget(features_label)
        right_layout.addStretch()
        
        right_panel.setLayout(right_layout)
        
        # Сборка главного layout
        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_panel, 1)
        
        # Enter для входа
        self.username_input.returnPressed.connect(self.handle_login)
        self.password_input.returnPressed.connect(self.handle_login)
        
        # Фокус на поле username
        self.username_input.setFocus()
        
        # Заполнение полей по умолчанию для удобства тестирования
        self.username_input.setText("admin")
        self.password_input.setText("admin123")
    
    def handle_login(self):
        """Обработка входа в систему"""
        username = self.username_input.text().strip()
        password = self.password_input.text()
        
        if not username or not password:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, заполните все поля")
            return
        
        # Блокировка кнопки на время проверки
        self.login_button.setEnabled(False)
        self.login_button.setText("Проверка...")
        
        # Проверка в базе данных
        admin_data = self.db.authenticate_admin(username, password)
        
        # Восстановление кнопки
        self.login_button.setEnabled(True)
        self.login_button.setText("🔐 Войти в систему")
        
        if admin_data:
            self.login_successful.emit(admin_data)
            self.close()
        else:
            QMessageBox.critical(self, "Ошибка", "Неверное имя пользователя или пароль")
            self.password_input.clear()
            self.password_input.setFocus()
            
            # Анимация встряхивания (опционально)
            self.shake_animation()
    
    def shake_animation(self):
        """Простая анимация встряхивания при ошибке"""
        from PyQt5.QtCore import QPropertyAnimation, QPoint
        
        self.animation = QPropertyAnimation(self, b"pos")
        self.animation.setDuration(100)
        self.animation.setLoopCount(3)
        
        start_pos = self.pos()
        self.animation.setStartValue(start_pos)
        self.animation.setKeyValueAt(0.25, QPoint(start_pos.x() + 10, start_pos.y()))
        self.animation.setKeyValueAt(0.75, QPoint(start_pos.x() - 10, start_pos.y()))
        self.animation.setEndValue(start_pos)
        
        self.animation.start()
    
    def keyPressEvent(self, event):
        """Обработка нажатий клавиш"""
        if event.key() == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)
    
    def resizeEvent(self, event):
        """Обработка изменения размера окна"""
        super().resizeEvent(event)
        # Дополнительная логика масштабирования при необходимости