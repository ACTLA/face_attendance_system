"""
Адаптивное окно входа в автоматизированную систему распознавания лиц
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QLineEdit, QPushButton, QCheckBox, QFrame,
                           QMessageBox, QSizePolicy, QSpacerItem,
                           QDesktopWidget)
from PyQt5.QtCore import Qt, pyqtSignal, QPropertyAnimation, QPoint
from PyQt5.QtGui import QFont

from database import Database
from config import PRIMARY_COLOR

class LoginWindow(QWidget):
    login_successful = pyqtSignal(dict)  # Сигнал успешного входа
    
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.init_ui()
    
    def init_ui(self):
        """Инициализация адаптивного интерфейса"""
        self.setWindowTitle("Вход - Система распознавания лиц")
        
        # Фиксированные размеры для предсказуемого отображения
        window_width, window_height = 500, 600
        
        self.resize(window_width, window_height)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)  # Разрешаем изменение размера
        
        # Центрирование на экране
        self.center_on_screen()
        
        # Убираем скролл - простой layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setLayout(main_layout)
        
        # Панель входа на весь экран
        login_panel = self.create_left_panel()
        main_layout.addWidget(login_panel)
        
        # Enter для входа
        self.username_input.returnPressed.connect(self.handle_login)
        self.password_input.returnPressed.connect(self.handle_login)
        
        # Фокус на поле username
        self.username_input.setFocus()
    
    def create_left_panel(self):
        """Создание панели с формой"""
        panel = QFrame()
        panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        panel.setStyleSheet("""
            QFrame {
                background-color: white;
                border: none;
            }
        """)
        
        # Главный layout с фиксированными отступами
        layout = QVBoxLayout()
        layout.setContentsMargins(50, 30, 50, 30)
        layout.setSpacing(20)
        panel.setLayout(layout)
        
        # Заголовок
        title_label = QLabel("Авторизация")
        title_label.setFont(QFont("Arial", 32, QFont.Bold))
        title_label.setStyleSheet("color: #333; margin-bottom: 10px;")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        # Подзаголовок
        subtitle_label = QLabel("Авторизация администратора")
        subtitle_label.setFont(QFont("Arial", 16))
        subtitle_label.setStyleSheet("color: #666; margin-bottom: 30px;")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        subtitle_label.setWordWrap(True)
        
        # Добавляем заголовки
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        
        # Растягивающийся элемент для центрирования
        layout.addSpacerItem(QSpacerItem(20, 30, QSizePolicy.Minimum, QSizePolicy.Fixed))
        
        # Форма в контейнере
        form_container = QFrame()
        form_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        form_layout = QVBoxLayout()
        form_layout.setSpacing(20)
        form_container.setLayout(form_layout)
        
        # Username
        username_label = QLabel("Имя пользователя")
        username_label.setFont(QFont("Arial", 14, QFont.Bold))
        username_label.setStyleSheet("color: #333;")
        username_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Введите имя пользователя")
        self.username_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.username_input.setMinimumHeight(50)
        self.username_input.setStyleSheet(self.get_input_style())
        
        # Password
        password_label = QLabel("Пароль")
        password_label.setFont(QFont("Arial", 14, QFont.Bold))
        password_label.setStyleSheet("color: #333;")
        password_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Введите пароль")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.password_input.setMinimumHeight(50)
        self.password_input.setStyleSheet(self.get_input_style())
        
        # Remember me
        self.remember_checkbox = QCheckBox("Запомнить меня")
        self.remember_checkbox.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.remember_checkbox.setStyleSheet(self.get_checkbox_style())
        
        # Login button
        self.login_button = QPushButton("🔐 Войти в систему")
        self.login_button.setFont(QFont("Arial", 16, QFont.Bold))
        self.login_button.setCursor(Qt.PointingHandCursor)
        self.login_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.login_button.setMinimumHeight(55)
        self.login_button.setStyleSheet(self.get_button_style())
        self.login_button.clicked.connect(self.handle_login)
        
        # Добавляем элементы формы
        form_layout.addWidget(username_label)
        form_layout.addWidget(self.username_input)
        form_layout.addWidget(password_label)
        form_layout.addWidget(self.password_input)
        form_layout.addWidget(self.remember_checkbox)
        form_layout.addSpacing(20)
        form_layout.addWidget(self.login_button)
        
        layout.addWidget(form_container)
        
        # Растягивающийся элемент в конце
        layout.addSpacerItem(QSpacerItem(20, 30, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        return panel
    
    def get_input_style(self):
        """Стиль для полей ввода"""
        return """
            QLineEdit {
                padding: 12px 15px;
                border: 2px solid #e0e0e0;
                border-radius: 10px;
                font-size: 14px;
                background-color: #f8f9fa;
                color: #333;
            }
            QLineEdit:focus {
                border-color: #667eea;
                background-color: white;
                outline: none;
            }
            QLineEdit:hover {
                border-color: #bbb;
            }
        """
    
    def get_checkbox_style(self):
        """Стиль для чекбокса"""
        return """
            QCheckBox {
                color: #666;
                font-size: 14px;
                spacing: 10px;
                padding: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                background-color: #667eea;
                border-color: #667eea;
            }
            QCheckBox::indicator:hover {
                border-color: #888;
            }
        """
    
    def get_button_style(self):
        """Стиль для кнопки"""
        return f"""
            QPushButton {{
                background-color: {PRIMARY_COLOR};
                color: white;
                border: none;
                border-radius: 10px;
                padding: 15px;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: #2d4aa3;
            }}
            QPushButton:pressed {{
                background-color: #1e3670;
            }}
            QPushButton:disabled {{
                background-color: #95a5a6;
            }}
        """
    
    def center_on_screen(self):
        """Центрирование окна на экране"""
        desktop = QDesktopWidget()
        screen_rect = desktop.screenGeometry()
        window_rect = self.geometry()
        
        x = (screen_rect.width() - window_rect.width()) // 2
        y = (screen_rect.height() - window_rect.height()) // 2
        
        self.move(max(0, x), max(0, y))
    
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
            
            # Анимация встряхивания при ошибке
            self.shake_animation()
    
    def shake_animation(self):
        """Простая анимация встряхивания при ошибке"""
        try:
            self.animation = QPropertyAnimation(self, b"pos")
            self.animation.setDuration(100)
            self.animation.setLoopCount(3)
            
            start_pos = self.pos()
            self.animation.setStartValue(start_pos)
            self.animation.setKeyValueAt(0.25, QPoint(start_pos.x() + 10, start_pos.y()))
            self.animation.setKeyValueAt(0.75, QPoint(start_pos.x() - 10, start_pos.y()))
            self.animation.setEndValue(start_pos)
            
            self.animation.start()
        except:
            pass  # Если анимация не работает, просто пропускаем
    
    def resizeEvent(self, event):
        """Обработка изменения размера окна - убираем так как размер фиксированный"""
        super().resizeEvent(event)
    
    def keyPressEvent(self, event):
        """Обработка нажатий клавиш"""
        if event.key() == Qt.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)