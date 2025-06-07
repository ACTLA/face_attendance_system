"""
Главное окно автоматизированной системы распознавания лиц
"""
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                           QLabel, QPushButton, QStackedWidget, QFrame,
                           QTableWidget, QTableWidgetItem, QHeaderView,
                           QMessageBox, QSizePolicy, QScrollArea, QDesktopWidget)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QDateTime, QSize
from PyQt5.QtGui import QFont, QPixmap, QIcon, QColor

import cv2
import numpy as np
from datetime import datetime

from database import Database
from config import (WINDOW_TITLE, PRIMARY_COLOR, SECONDARY_COLOR, COMPANY_NAME,
                   WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
from .add_user_dialog import AddUserDialog
from .face_recognition_widget import FaceRecognitionWidget

class MainWindow(QMainWindow):
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
        """Инициализация адаптивного интерфейса"""
        self.setWindowTitle(WINDOW_TITLE)
        
        # Адаптивные размеры под экран
        desktop = QDesktopWidget()
        screen_rect = desktop.screenGeometry()
        
        if screen_rect.width() >= 1920:
            window_width, window_height = 1200, 800
            sidebar_width = 250
        elif screen_rect.width() >= 1366:
            window_width, window_height = 1100, 700
            sidebar_width = 220
        else:
            window_width, window_height = 900, 600
            sidebar_width = 200
        
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.resize(window_width, window_height)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Сохраняем размеры для адаптивности
        self.sidebar_width = sidebar_width
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Главный layout
        main_layout = QHBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        central_widget.setLayout(main_layout)
        
        # Боковая панель
        self.create_sidebar()
        main_layout.addWidget(self.sidebar)
        
        # Область контента с прокруткой
        self.content_scroll = QScrollArea()
        self.content_scroll.setWidgetResizable(True)
        self.content_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.content_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.content_area = QStackedWidget()
        self.content_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        self.content_scroll.setWidget(self.content_area)
        main_layout.addWidget(self.content_scroll, 1)
        
        # Создание страниц
        self.create_dashboard()
        self.create_users_page()
        self.create_face_recognition_page()
        self.create_reports_page()
        
        # Установка стилей
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QLabel {
                color: #333;
            }
            QScrollArea {
                border: none;
                background-color: #f5f5f5;
            }
        """)
        
        # Показать dashboard по умолчанию
        self.show_dashboard()
    
    def create_sidebar(self):
        """Создание боковой панели"""
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(self.sidebar_width)
        self.sidebar.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.sidebar.setStyleSheet(f"""
            QFrame {{
                background-color: {PRIMARY_COLOR};
                border: none;
            }}
        """)
        
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        self.sidebar.setLayout(sidebar_layout)
        
        # Логотип и название компании
        company_label = QLabel(COMPANY_NAME)
        company_label.setFont(QFont("Arial", 16, QFont.Bold))
        company_label.setStyleSheet("color: white; padding: 20px;")
        company_label.setAlignment(Qt.AlignCenter)
        company_label.setWordWrap(True)
        sidebar_layout.addWidget(company_label)
        
        # Информация о пользователе
        user_info = QFrame()
        user_info.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                margin: 10px;
                padding: 15px;
            }
        """)
        user_layout = QVBoxLayout()
        user_info.setLayout(user_layout)
        
        user_icon = QLabel("👤")
        user_icon.setFont(QFont("Arial", 28))
        user_icon.setAlignment(Qt.AlignCenter)
        user_icon.setStyleSheet("color: white;")
        user_layout.addWidget(user_icon)
        
        username_label = QLabel(self.admin_data['username'])
        username_label.setFont(QFont("Arial", 12, QFont.Bold))
        username_label.setStyleSheet("color: white;")
        username_label.setAlignment(Qt.AlignCenter)
        username_label.setWordWrap(True)
        user_layout.addWidget(username_label)
        
        sidebar_layout.addWidget(user_info)
        
        # Кнопки навигации
        nav_buttons = [
            ("📊", "Панель управления", self.show_dashboard),
            ("👥", "Пользователи", self.show_users),
            ("🔍", "Распознавание лиц", self.show_face_recognition),
            ("📈", "Отчеты", self.show_reports)
        ]
        
        for icon, text, callback in nav_buttons:
            btn = QPushButton(f"{icon}  {text}")
            btn.setFont(QFont("Arial", 12))
            btn.setCursor(Qt.PointingHandCursor)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.setMinimumHeight(50)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: white;
                    border: none;
                    padding: 15px;
                    text-align: left;
                    border-radius: 8px;
                    margin: 5px 10px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.1);
                }
                QPushButton:pressed {
                    background-color: rgba(255, 255, 255, 0.2);
                }
            """)
            btn.clicked.connect(callback)
            sidebar_layout.addWidget(btn)
        
        sidebar_layout.addStretch()
        
        # Кнопка выхода
        logout_btn = QPushButton("🚪  Выход")
        logout_btn.setFont(QFont("Arial", 12))
        logout_btn.setCursor(Qt.PointingHandCursor)
        logout_btn.setMinimumHeight(50)
        logout_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
                border: none;
                padding: 15px;
                margin: 10px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.2);
            }
        """)
        logout_btn.clicked.connect(self.logout)
        sidebar_layout.addWidget(logout_btn)
    
    def create_dashboard(self):
        """Создание страницы Dashboard"""
        dashboard = QWidget()
        dashboard.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        dashboard.setLayout(layout)
        
        # Заголовок
        header_layout = QHBoxLayout()
        title = QLabel("Панель управления")
        title.setFont(QFont("Arial", 28, QFont.Bold))
        title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        header_layout.addWidget(title)
        
        # Время
        self.time_label = QLabel()
        self.time_label.setFont(QFont("Arial", 16))
        self.time_label.setAlignment(Qt.AlignRight)
        self.time_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
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
            ("Активных сессий", 1, "⚡", "#f39c12")
        ]
        
        for title, value, icon, color in stats:
            card = self.create_stat_card(title, str(value), icon, color)
            stats_layout.addWidget(card)
        
        layout.addLayout(stats_layout)
        
        # Последние распознавания
        recent_label = QLabel("Последние распознавания")
        recent_label.setFont(QFont("Arial", 18, QFont.Bold))
        layout.addWidget(recent_label)
        
        # Таблица последних распознаваний
        self.recent_table = QTableWidget()
        self.recent_table.setColumnCount(5)
        self.recent_table.setHorizontalHeaderLabels(["ID пользователя", "Имя", "Время", "Уверенность", "Статус"])
        
        # Настройка таблицы для адаптивности
        header = self.recent_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.recent_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        self.recent_table.setAlternatingRowColors(True)
        self.recent_table.setStyleSheet("""
            QTableWidget {
                border: none;
                background-color: white;
                border-radius: 10px;
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
                border-radius: 12px;
                padding: 20px;
                border-left: 5px solid {color};
            }}
        """)
        
        layout = QVBoxLayout()
        card.setLayout(layout)
        
        # Иконка и значение
        top_layout = QHBoxLayout()
        
        icon_label = QLabel(icon)
        icon_label.setFont(QFont("Arial", 36))
        icon_label.setStyleSheet(f"color: {color};")
        icon_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        top_layout.addWidget(icon_label)
        
        top_layout.addStretch()
        
        value_label = QLabel(value)
        value_label.setFont(QFont("Arial", 32, QFont.Bold))
        value_label.setAlignment(Qt.AlignRight)
        value_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        top_layout.addWidget(value_label)
        
        layout.addLayout(top_layout)
        
        # Заголовок
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 14))
        title_label.setStyleSheet("color: #666;")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)
        
        return card
    
    def create_users_page(self):
        """Создание страницы пользователей"""
        users_page = QWidget()
        users_page.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        users_page.setLayout(layout)
        
        # Заголовок и кнопка добавления
        header_layout = QHBoxLayout()
        
        title = QLabel("Управление пользователями")
        title.setFont(QFont("Arial", 28, QFont.Bold))
        title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        header_layout.addWidget(title)
        
        add_btn = QPushButton("➕ Добавить пользователя")
        add_btn.setFont(QFont("Arial", 14))
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        add_btn.setMinimumHeight(45)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {SECONDARY_COLOR};
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #4cae4c;
            }}
        """)
        add_btn.clicked.connect(self.show_add_user_dialog)
        header_layout.addWidget(add_btn)
        
        layout.addLayout(header_layout)
        
        # Таблица пользователей
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(5)
        self.users_table.setHorizontalHeaderLabels([
            "ID", "Идентификатор", "Имя", "Дата создания", "Действия"
        ])
        
        # Настройка таблицы для адаптивности
        header = self.users_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        
        self.users_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.users_table.setAlternatingRowColors(True)
        self.users_table.setStyleSheet("""
            QTableWidget {
                border: none;
                background-color: white;
                border-radius: 10px;
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
        self.face_recognition_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.content_area.addWidget(self.face_recognition_widget)
    
    def create_reports_page(self):
        """Создание страницы отчетов"""
        reports_page = QWidget()
        reports_page.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        reports_page.setLayout(layout)
        
        title = QLabel("Отчеты по распознаванию")
        title.setFont(QFont("Arial", 28, QFont.Bold))
        layout.addWidget(title)
        
        # Фильтры
        filters_frame = QFrame()
        filters_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                padding: 20px;
            }
        """)
        filters_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        filters_layout = QHBoxLayout()
        filters_frame.setLayout(filters_layout)
        
        filters_label = QLabel("Фильтры будут добавлены в следующих версиях")
        filters_label.setFont(QFont("Arial", 12))
        filters_label.setStyleSheet("color: #666;")
        filters_layout.addWidget(filters_label)
        
        layout.addWidget(filters_frame)
        
        # Таблица отчетов
        self.reports_table = QTableWidget()
        self.reports_table.setColumnCount(5)
        self.reports_table.setHorizontalHeaderLabels([
            "Дата/Время", "ID пользователя", "Имя", "Уверенность", "Статус"
        ])
        
        # Настройка таблицы для адаптивности
        header = self.reports_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.reports_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.reports_table.setAlternatingRowColors(True)
        self.reports_table.setStyleSheet("""
            QTableWidget {
                border: none;
                background-color: white;
                border-radius: 10px;
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
        self.current_page = 0
        self.content_area.setCurrentIndex(0)
        self.update_recent_recognitions()
    
    def show_users(self):
        self.current_page = 1
        self.content_area.setCurrentIndex(1)
        self.update_users_table()
    
    def show_face_recognition(self):
        self.current_page = 2
        self.content_area.setCurrentIndex(2)
    
    def show_reports(self):
        self.current_page = 3
        self.content_area.setCurrentIndex(3)
        self.update_reports_table()
    
    def show_add_user_dialog(self):
        dialog = AddUserDialog(self, self.db, self.admin_data)
        if dialog.exec_():
            self.update_users_table()
            QMessageBox.information(self, "Успех", "Пользователь успешно добавлен!")
    
    def update_time(self):
        """Обновление времени"""
        current_time = QDateTime.currentDateTime()
        self.time_label.setText(current_time.toString("dddd, d MMMM yyyy - hh:mm:ss"))
    
    def update_recent_recognitions(self):
        """Обновление таблицы последних распознаваний"""
        records = self.db.get_recognition_report()[:10]  # Последние 10 записей
        
        self.recent_table.setRowCount(len(records))
        for i, record in enumerate(records):
            self.recent_table.setItem(i, 0, QTableWidgetItem(record['user_code']))
            self.recent_table.setItem(i, 1, QTableWidgetItem(record['full_name']))
            self.recent_table.setItem(i, 2, QTableWidgetItem(record['timestamp']))
            confidence = f"{record['confidence']*100:.1f}%" if record['confidence'] else "N/A"
            self.recent_table.setItem(i, 3, QTableWidgetItem(confidence))
            self.recent_table.setItem(i, 4, QTableWidgetItem(record['recognition_type']))
    
    def update_users_table(self):
        """Обновление таблицы пользователей"""
        users = self.db.get_all_users()
        
        self.users_table.setRowCount(len(users))
        for i, user in enumerate(users):
            self.users_table.setItem(i, 0, QTableWidgetItem(str(user['id'])))
            self.users_table.setItem(i, 1, QTableWidgetItem(user['user_id']))
            self.users_table.setItem(i, 2, QTableWidgetItem(user['full_name']))
            
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
                    padding: 8px 16px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #c82333;
                }
            """)
            delete_btn.clicked.connect(lambda _, user_id=user['id']: self.delete_user(user_id))
            self.users_table.setCellWidget(i, 4, delete_btn)
    
    def update_reports_table(self):
        """Обновление таблицы отчетов"""
        records = self.db.get_recognition_report()[:50]  # Последние 50 записей
        
        self.reports_table.setRowCount(len(records))
        for i, record in enumerate(records):
            self.reports_table.setItem(i, 0, QTableWidgetItem(record['timestamp']))
            self.reports_table.setItem(i, 1, QTableWidgetItem(record['user_code']))
            self.reports_table.setItem(i, 2, QTableWidgetItem(record['full_name']))
            confidence = f"{record['confidence']*100:.1f}%" if record['confidence'] else "N/A"
            self.reports_table.setItem(i, 3, QTableWidgetItem(confidence))
            self.reports_table.setItem(i, 4, QTableWidgetItem(record['recognition_type']))
    
    def delete_user(self, user_id):
        reply = QMessageBox.question(self, "Подтверждение удаления", 
                                   "Вы уверены, что хотите удалить этого пользователя?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.db.delete_user(user_id)
            self.update_users_table()
            QMessageBox.information(self, "Успех", "Пользователь успешно удален!")
    
    def logout(self):
        reply = QMessageBox.question(self, "Выход", 
                                   "Вы уверены, что хотите выйти?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # Мягкая остановка камеры только если она активна
            if hasattr(self, 'face_recognition_widget') and self.face_recognition_widget.is_camera_active:
                self.face_recognition_widget.is_camera_active = False
                if self.face_recognition_widget.recognition_thread:
                    self.face_recognition_widget.recognition_thread.is_running = False
            
            self.close()
            from .login_window import LoginWindow
            self.login_window = LoginWindow()
            self.login_window.show()
    
    def resizeEvent(self, event):
        """Обработка изменения размера окна"""
        super().resizeEvent(event)
    
    def closeEvent(self, event):
        """Обработка закрытия окна"""
        # Мягкая остановка камеры только если она активна
        if hasattr(self, 'face_recognition_widget') and self.face_recognition_widget.is_camera_active:
            self.face_recognition_widget.is_camera_active = False
            if self.face_recognition_widget.recognition_thread:
                self.face_recognition_widget.recognition_thread.is_running = False
        
        event.accept()