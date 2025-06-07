"""
Упрощенное главное окно системы
"""
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                           QLabel, QPushButton, QStackedWidget, QFrame,
                           QTableWidget, QTableWidgetItem, QHeaderView,
                           QMessageBox, QSizePolicy, QDesktopWidget)
from PyQt5.QtCore import Qt, QTimer, QDateTime
from PyQt5.QtGui import QFont

from datetime import datetime

from database import Database
from config import (WINDOW_TITLE, PRIMARY_COLOR, SECONDARY_COLOR,
                   WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
from .add_user_dialog import AddUserDialog
from .face_recognition_widget import FaceRecognitionWidget

class MainWindow(QMainWindow):
    """Упрощенное главное окно"""
    
    def __init__(self, admin_data):
        super().__init__()
        self.admin_data = admin_data
        self.db = Database()
        self.current_page = 0
        
        self.init_ui()
        
        # Таймер для обновления времени
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)
    
    def init_ui(self):
        """Инициализация интерфейса"""
        self.setWindowTitle(WINDOW_TITLE)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.resize(1200, 800)
        
        # Центрирование на экране
        self.center_on_screen()
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Главный layout
        main_layout = QHBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        central_widget.setLayout(main_layout)
        
        # Боковая панель
        sidebar = self.create_sidebar()
        main_layout.addWidget(sidebar)
        
        # Область контента
        self.content_area = QStackedWidget()
        self.content_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_layout.addWidget(self.content_area, 1)
        
        # Создание страниц
        self.create_dashboard()
        self.create_users_page()
        self.create_face_recognition_page()
        self.create_reports_page()
        
        # Стили
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QWidget {
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
        
        # Показать dashboard по умолчанию
        self.show_dashboard()
    
    def center_on_screen(self):
        """Центрирование окна на экране"""
        desktop = QDesktopWidget()
        screen_rect = desktop.screenGeometry()
        window_rect = self.geometry()
        
        x = (screen_rect.width() - window_rect.width()) // 2
        y = (screen_rect.height() - window_rect.height()) // 2
        
        self.move(max(0, x), max(0, y))
    
    def create_sidebar(self):
        """Создание боковой панели"""
        sidebar = QFrame()
        sidebar.setFixedWidth(250)
        sidebar.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        sidebar.setStyleSheet(f"""
            QFrame {{
                background-color: {PRIMARY_COLOR};
                border: none;
            }}
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        sidebar.setLayout(layout)
        
        # Заголовок
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: rgba(255, 255, 255, 0.1);")
        header_layout = QVBoxLayout()
        header_frame.setLayout(header_layout)
        
        # Информация о пользователе
        user_label = QLabel(f"{self.admin_data['username']}")
        user_label.setFont(QFont("Arial", 12))
        user_label.setStyleSheet("color: white; padding: 10px 20px;")
        user_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(user_label)
        
        layout.addWidget(header_frame)
        
        # Навигация
        nav_buttons = [
            ("Панель управления", self.show_dashboard),
            ("Пользователи", self.show_users),
            ("Распознавание лиц", self.show_face_recognition),
            ("Отчеты", self.show_reports)
        ]
        
        for text, callback in nav_buttons:
            btn = QPushButton(f"{text}")
            btn.setFont(QFont("Arial", 11))
            btn.setCursor(Qt.PointingHandCursor)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setMinimumHeight(50)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: white;
                    border: none;
                    padding: 15px 20px;
                    text-align: left;
                    border-radius: 0;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.1);
                }
                QPushButton:pressed {
                    background-color: rgba(255, 255, 255, 0.2);
                }
            """)
            btn.clicked.connect(callback)
            layout.addWidget(btn)
        
        layout.addStretch()
        
        # Кнопка выхода
        logout_btn = QPushButton("Выход")
        logout_btn.setFont(QFont("Arial", 11))
        logout_btn.setCursor(Qt.PointingHandCursor)
        logout_btn.setMinimumHeight(50)
        logout_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
                border: none;
                padding: 15px 20px;
                margin: 10px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.2);
            }
        """)
        logout_btn.clicked.connect(self.logout)
        layout.addWidget(logout_btn)
        
        return sidebar
    
    def create_dashboard(self):
        """Создание страницы панели управления"""
        dashboard = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        dashboard.setLayout(layout)
        
        # Заголовок
        header_layout = QHBoxLayout()
        
        title = QLabel("Панель управления")
        title.setFont(QFont("Arial", 24, QFont.Bold))
        title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        header_layout.addWidget(title)
        
        # Время
        self.time_label = QLabel()
        self.time_label.setFont(QFont("Arial", 14))
        self.time_label.setAlignment(Qt.AlignRight)
        header_layout.addWidget(self.time_label)
        
        layout.addLayout(header_layout)
        
        # Статистика
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(20)
        
        # Карточки статистики
        stats = [
            ("Всего пользователей", len(self.db.get_all_users()), "👥", "#3498db"),
            ("Распознано сегодня", self.db.get_today_recognition_count(), "🔍", "#2ecc71"),
            ("Уникальных сегодня", self.db.get_unique_users_today(), "✅", "#e74c3c"),
            ("Система активна", "ДА", "⚡", "#f39c12")
        ]
        
        for title_text, value, icon, color in stats:
            card = self.create_stat_card(title_text, str(value), icon, color)
            stats_layout.addWidget(card)
        
        layout.addLayout(stats_layout)
        
        # Последние распознавания
        recent_label = QLabel("Последние распознавания")
        recent_label.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(recent_label)
        
        # Таблица
        self.recent_table = QTableWidget()
        self.recent_table.setColumnCount(5)
        self.recent_table.setHorizontalHeaderLabels([
            "ID пользователя", "Имя", "Время", "Уверенность", "Статус"
        ])
        
        # Настройка таблицы
        header = self.recent_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.recent_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.recent_table.setAlternatingRowColors(True)
        self.recent_table.setStyleSheet("""
            QTableWidget {
                border: none;
                background-color: white;
                border-radius: 8px;
                gridline-color: #f0f0f0;
            }
            QTableWidget::item {
                padding: 12px;
                border-bottom: 1px solid #f0f0f0;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 12px;
                border: none;
                font-weight: bold;
                border-bottom: 2px solid #e9ecef;
            }
        """)
        
        self.update_recent_recognitions()
        layout.addWidget(self.recent_table)
        
        self.content_area.addWidget(dashboard)
    
    def create_stat_card(self, title, value, icon, color):
        """Создание карточки статистики"""
        card = QFrame()
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        card.setMinimumHeight(120)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-radius: 10px;
                padding: 20px;
                border-left: 4px solid {color};
                border: 1px solid #e9ecef;
            }}
        """)
        
        layout = QVBoxLayout()
        card.setLayout(layout)
        
        # Верхняя часть - иконка и значение
        top_layout = QHBoxLayout()
        
        icon_label = QLabel(icon)
        icon_label.setFont(QFont("Arial", 30))
        icon_label.setStyleSheet(f"color: {color};")
        top_layout.addWidget(icon_label)
        
        top_layout.addStretch()
        
        value_label = QLabel(value)
        value_label.setFont(QFont("Arial", 28, QFont.Bold))
        value_label.setAlignment(Qt.AlignRight)
        top_layout.addWidget(value_label)
        
        layout.addLayout(top_layout)
        
        # Заголовок
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 12))
        title_label.setStyleSheet("color: #666;")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)
        
        return card
    
    def create_users_page(self):
        """Создание страницы пользователей"""
        users_page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        users_page.setLayout(layout)
        
        # Заголовок и кнопка добавления
        header_layout = QHBoxLayout()
        
        title = QLabel("Управление пользователями")
        title.setFont(QFont("Arial", 24, QFont.Bold))
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        add_btn = QPushButton("➕ Добавить пользователя")
        add_btn.setFont(QFont("Arial", 12))
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setMinimumHeight(40)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {SECONDARY_COLOR};
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #218838;
            }}
        """)
        add_btn.clicked.connect(self.show_add_user_dialog)
        header_layout.addWidget(add_btn)
        
        layout.addLayout(header_layout)
        
        # Таблица пользователей
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(5)
        self.users_table.setHorizontalHeaderLabels([
            "ID", "Имя", "Email", "Дата создания", "Действия"
        ])
        
        # Настройка таблицы
        header = self.users_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        
        self.users_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.users_table.setAlternatingRowColors(True)
        self.users_table.setStyleSheet("""
            QTableWidget {
                border: none;
                background-color: white;
                border-radius: 8px;
                gridline-color: #f0f0f0;
            }
            QTableWidget::item {
                padding: 12px;
                border-bottom: 1px solid #f0f0f0;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 12px;
                border: none;
                font-weight: bold;
                border-bottom: 2px solid #e9ecef;
            }
        """)
        
        self.update_users_table()
        layout.addWidget(self.users_table)
        
        self.content_area.addWidget(users_page)
    
    def create_face_recognition_page(self):
        """Создание страницы распознавания лиц"""
        self.face_recognition_widget = FaceRecognitionWidget(self.db, self.admin_data)
        self.content_area.addWidget(self.face_recognition_widget)
    
    def create_reports_page(self):
        """Создание страницы отчетов"""
        reports_page = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        reports_page.setLayout(layout)
        
        title = QLabel("Отчеты по распознаванию")
        title.setFont(QFont("Arial", 24, QFont.Bold))
        layout.addWidget(title)
        
        # Таблица отчетов
        self.reports_table = QTableWidget()
        self.reports_table.setColumnCount(5)
        self.reports_table.setHorizontalHeaderLabels([
            "Дата/Время", "ID пользователя", "Имя", "Уверенность", "Статус"
        ])
        
        # Настройка таблицы
        header = self.reports_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.reports_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.reports_table.setAlternatingRowColors(True)
        self.reports_table.setStyleSheet("""
            QTableWidget {
                border: none;
                background-color: white;
                border-radius: 8px;
                gridline-color: #f0f0f0;
            }
            QTableWidget::item {
                padding: 12px;
                border-bottom: 1px solid #f0f0f0;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 12px;
                border: none;
                font-weight: bold;
                border-bottom: 2px solid #e9ecef;
            }
        """)
        
        self.update_reports_table()
        layout.addWidget(self.reports_table)
        
        self.content_area.addWidget(reports_page)
    
    def show_dashboard(self):
        """Показать панель управления"""
        self.current_page = 0
        self.content_area.setCurrentIndex(0)
        self.update_recent_recognitions()
    
    def show_users(self):
        """Показать страницу пользователей"""
        self.current_page = 1
        self.content_area.setCurrentIndex(1)
        self.update_users_table()
    
    def show_face_recognition(self):
        """Показать страницу распознавания лиц"""
        self.current_page = 2
        self.content_area.setCurrentIndex(2)
    
    def show_reports(self):
        """Показать страницу отчетов"""
        self.current_page = 3
        self.content_area.setCurrentIndex(3)
        self.update_reports_table()
    
    def show_add_user_dialog(self):
        """Показать диалог добавления пользователя"""
        dialog = AddUserDialog(self, self.db, self.admin_data)
        if dialog.exec_():
            self.update_users_table()
            
            # Обновляем кэш распознавания лиц
            if hasattr(self, 'face_recognition_widget'):
                self.face_recognition_widget.recognition_engine.reload_face_encodings()
            
            QMessageBox.information(self, "Успех", "Пользователь успешно добавлен!")
    
    def update_time(self):
        """Обновление времени"""
        current_time = QDateTime.currentDateTime()
        self.time_label.setText(current_time.toString("dd.MM.yyyy - hh:mm:ss"))
    
    def update_recent_recognitions(self):
        """Обновление таблицы последних распознаваний"""
        try:
            records = self.db.get_recognition_report()[:10]
            
            self.recent_table.setRowCount(len(records))
            for i, record in enumerate(records):
                self.recent_table.setItem(i, 0, QTableWidgetItem(record['user_code']))
                self.recent_table.setItem(i, 1, QTableWidgetItem(record['full_name']))
                self.recent_table.setItem(i, 2, QTableWidgetItem(record['timestamp']))
                
                confidence = f"{record['confidence']*100:.1f}%" if record['confidence'] else "N/A"
                self.recent_table.setItem(i, 3, QTableWidgetItem(confidence))
                self.recent_table.setItem(i, 4, QTableWidgetItem(record['recognition_type']))
        except Exception as e:
            print(f"Ошибка обновления таблицы распознаваний: {e}")
    
    def update_users_table(self):
        """Обновление таблицы пользователей"""
        try:
            users = self.db.get_all_users()
            
            self.users_table.setRowCount(len(users))
            for i, user in enumerate(users):
                self.users_table.setItem(i, 0, QTableWidgetItem(user['user_id']))
                self.users_table.setItem(i, 1, QTableWidgetItem(user['full_name']))
                self.users_table.setItem(i, 2, QTableWidgetItem(user.get('email', '')))
                
                # Форматирование даты
                created_at = user['created_at']
                if isinstance(created_at, str):
                    try:
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        formatted_date = dt.strftime('%d.%m.%Y %H:%M')
                    except:
                        formatted_date = created_at
                else:
                    formatted_date = str(created_at)
                
                self.users_table.setItem(i, 3, QTableWidgetItem(formatted_date))
                
                # Кнопка удаления
                delete_btn = QPushButton("🗑️ Удалить")
                delete_btn.setCursor(Qt.PointingHandCursor)
                delete_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #dc3545;
                        color: white;
                        border: none;
                        padding: 6px 12px;
                        border-radius: 4px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #c82333;
                    }
                """)
                delete_btn.clicked.connect(lambda _, user_id=user['id']: self.delete_user(user_id))
                self.users_table.setCellWidget(i, 4, delete_btn)
        except Exception as e:
            print(f"Ошибка обновления таблицы пользователей: {e}")
    
    def update_reports_table(self):
        """Обновление таблицы отчетов"""
        try:
            records = self.db.get_recognition_report()[:50]
            
            self.reports_table.setRowCount(len(records))
            for i, record in enumerate(records):
                self.reports_table.setItem(i, 0, QTableWidgetItem(record['timestamp']))
                self.reports_table.setItem(i, 1, QTableWidgetItem(record['user_code']))
                self.reports_table.setItem(i, 2, QTableWidgetItem(record['full_name']))
                
                confidence = f"{record['confidence']*100:.1f}%" if record['confidence'] else "N/A"
                self.reports_table.setItem(i, 3, QTableWidgetItem(confidence))
                self.reports_table.setItem(i, 4, QTableWidgetItem(record['recognition_type']))
        except Exception as e:
            print(f"Ошибка обновления таблицы отчетов: {e}")
    
    def delete_user(self, user_id):
        """Удаление пользователя"""
        reply = QMessageBox.question(
            self, "Подтверждение удаления", 
            "Вы уверены, что хотите удалить этого пользователя?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.db.delete_user(user_id)
                self.update_users_table()
                
                # Обновляем кэш распознавания лиц
                if hasattr(self, 'face_recognition_widget'):
                    self.face_recognition_widget.recognition_engine.remove_face(user_id)
                
                QMessageBox.information(self, "Успех", "Пользователь успешно удален!")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка удаления пользователя: {str(e)}")
    
    def logout(self):
        """Выход из системы"""
        reply = QMessageBox.question(
            self, "Выход", 
            "Вы уверены, что хотите выйти?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Остановка камеры если она активна
            if hasattr(self, 'face_recognition_widget'):
                if self.face_recognition_widget.is_camera_active:
                    self.face_recognition_widget.stop_recognition()
            
            self.close()
            
            # Показ окна входа
            from .login_window import LoginWindow
            self.login_window = LoginWindow()
            self.login_window.show()
    
    def closeEvent(self, event):
        """Обработка закрытия окна"""
        # Остановка камеры если она активна
        if hasattr(self, 'face_recognition_widget'):
            if self.face_recognition_widget.is_camera_active:
                self.face_recognition_widget.stop_recognition()
        
        event.accept()