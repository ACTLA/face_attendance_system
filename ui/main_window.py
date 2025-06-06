"""
Главное окно приложения
"""
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                           QLabel, QPushButton, QStackedWidget, QFrame,
                           QTableWidget, QTableWidgetItem, QHeaderView,
                           QMessageBox, QFileDialog, QGraphicsDropShadowEffect)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QDateTime
from PyQt5.QtGui import QFont, QPixmap, QIcon, QColor

import cv2
import numpy as np
from datetime import datetime

from database import Database
from config import WINDOW_TITLE, PRIMARY_COLOR, SECONDARY_COLOR, COMPANY_NAME
from .add_employee_dialog import AddEmployeeDialog
from .face_attendance_widget import FaceAttendanceWidget

class MainWindow(QMainWindow):
    def __init__(self, user_data):
        super().__init__()
        self.user_data = user_data
        self.db = Database()
        self.init_ui()
        
        # Таймер для обновления времени
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)
    
    def init_ui(self):
        self.setWindowTitle(WINDOW_TITLE)
        self.setGeometry(100, 100, 1200, 800)
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Главный layout
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Боковая панель
        self.create_sidebar()
        main_layout.addWidget(self.sidebar)
        
        # Область контента
        self.content_area = QStackedWidget()
        main_layout.addWidget(self.content_area, 1)
        
        # Создание страниц
        self.create_dashboard()
        self.create_employees_page()
        self.create_face_attendance_page()
        self.create_reports_page()
        
        # Установка стилей
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QLabel {
                color: #333;
            }
        """)
    
    def create_sidebar(self):
        """Создание боковой панели"""
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(250)
        self.sidebar.setStyleSheet(f"""
            QFrame {{
                background-color: {PRIMARY_COLOR};
                border: none;
            }}
        """)
        
        sidebar_layout = QVBoxLayout()
        self.sidebar.setLayout(sidebar_layout)
        
        # Логотип и название компании
        company_label = QLabel(COMPANY_NAME)
        company_label.setFont(QFont("Arial", 16, QFont.Bold))
        company_label.setStyleSheet("color: white; padding: 20px;")
        company_label.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(company_label)
        
        # Информация о пользователе
        user_info = QFrame()
        user_info.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                margin: 10px;
                padding: 10px;
            }
        """)
        user_layout = QVBoxLayout()
        user_info.setLayout(user_layout)
        
        user_icon = QLabel("👤")
        user_icon.setFont(QFont("Arial", 24))
        user_icon.setAlignment(Qt.AlignCenter)
        user_icon.setStyleSheet("color: white;")
        user_layout.addWidget(user_icon)
        
        username_label = QLabel(self.user_data['username'])
        username_label.setFont(QFont("Arial", 12, QFont.Bold))
        username_label.setStyleSheet("color: white;")
        username_label.setAlignment(Qt.AlignCenter)
        user_layout.addWidget(username_label)
        
        sidebar_layout.addWidget(user_info)
        
        # Кнопки навигации
        nav_buttons = [
            ("📊", "Dashboard", self.show_dashboard),
            ("👥", "Employees", self.show_employees),
            ("📷", "Face Attendance", self.show_face_attendance),
            ("📈", "Reports", self.show_reports)
        ]
        
        for icon, text, callback in nav_buttons:
            btn = QPushButton(f"{icon}  {text}")
            btn.setFont(QFont("Arial", 12))
            btn.setCursor(Qt.PointingHandCursor)
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
        logout_btn = QPushButton("🚪  Logout")
        logout_btn.setFont(QFont("Arial", 12))
        logout_btn.setCursor(Qt.PointingHandCursor)
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
        layout = QVBoxLayout()
        dashboard.setLayout(layout)
        
        # Заголовок
        header_layout = QHBoxLayout()
        title = QLabel("Dashboard")
        title.setFont(QFont("Arial", 24, QFont.Bold))
        header_layout.addWidget(title)
        
        # Время
        self.time_label = QLabel()
        self.time_label.setFont(QFont("Arial", 14))
        self.time_label.setAlignment(Qt.AlignRight)
        header_layout.addWidget(self.time_label)
        
        layout.addLayout(header_layout)
        
        # Статистика
        stats_layout = QHBoxLayout()
        
        # Карточки статистики
        stats = [
            ("Total Employees", self.db.get_all_employees().__len__(), "👥", "#3498db"),
            ("Present Today", self.db.get_today_attendance_count(), "✅", "#2ecc71"),
            ("On Leave", 0, "🏖️", "#e74c3c"),
            ("Late Arrivals", 0, "⏰", "#f39c12")
        ]
        
        for title, value, icon, color in stats:
            card = self.create_stat_card(title, str(value), icon, color)
            stats_layout.addWidget(card)
        
        layout.addLayout(stats_layout)
        
        # Последние отметки
        recent_label = QLabel("Recent Attendance")
        recent_label.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(recent_label)
        
        # Таблица последних отметок
        self.recent_table = QTableWidget()
        self.recent_table.setColumnCount(5)
        self.recent_table.setHorizontalHeaderLabels(["Employee ID", "Name", "Time", "Type", "Confidence"])
        self.recent_table.horizontalHeader().setStretchLastSection(True)
        self.recent_table.setAlternatingRowColors(True)
        self.recent_table.setStyleSheet("""
            QTableWidget {
                border: none;
                background-color: white;
                border-radius: 10px;
            }
            QTableWidget::item {
                padding: 10px;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 10px;
                border: none;
                font-weight: bold;
            }
        """)
        
        self.update_recent_attendance()
        layout.addWidget(self.recent_table)
        
        self.content_area.addWidget(dashboard)
    
    def create_stat_card(self, title, value, icon, color):
        """Создание карточки статистики"""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-radius: 10px;
                padding: 20px;
                border-left: 4px solid {color};
            }}
        """)
        
        # Эффект тени
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 3)
        card.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout()
        card.setLayout(layout)
        
        # Иконка и значение
        top_layout = QHBoxLayout()
        
        icon_label = QLabel(icon)
        icon_label.setFont(QFont("Arial", 32))
        icon_label.setStyleSheet(f"color: {color};")
        top_layout.addWidget(icon_label)
        
        value_label = QLabel(value)
        value_label.setFont(QFont("Arial", 28, QFont.Bold))
        value_label.setAlignment(Qt.AlignRight)
        top_layout.addWidget(value_label)
        
        layout.addLayout(top_layout)
        
        # Заголовок
        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 12))
        title_label.setStyleSheet("color: #666;")
        layout.addWidget(title_label)
        
        return card
    
    def create_employees_page(self):
        """Создание страницы сотрудников"""
        employees_page = QWidget()
        layout = QVBoxLayout()
        employees_page.setLayout(layout)
        
        # Заголовок и кнопка добавления
        header_layout = QHBoxLayout()
        
        title = QLabel("Employees")
        title.setFont(QFont("Arial", 24, QFont.Bold))
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        add_btn = QPushButton("➕ Add Employee")
        add_btn.setFont(QFont("Arial", 12))
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {SECONDARY_COLOR};
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 8px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #4cae4c;
            }}
        """)
        add_btn.clicked.connect(self.show_add_employee_dialog)
        header_layout.addWidget(add_btn)
        
        layout.addLayout(header_layout)
        
        # Таблица сотрудников
        self.employees_table = QTableWidget()
        self.employees_table.setColumnCount(7)
        self.employees_table.setHorizontalHeaderLabels([
            "ID", "Employee ID", "Name", "Designation", "Department", "Email", "Actions"
        ])
        self.employees_table.horizontalHeader().setStretchLastSection(True)
        self.employees_table.setAlternatingRowColors(True)
        self.employees_table.setStyleSheet("""
            QTableWidget {
                border: none;
                background-color: white;
                border-radius: 10px;
            }
            QTableWidget::item {
                padding: 10px;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 10px;
                border: none;
                font-weight: bold;
            }
        """)
        
        self.update_employees_table()
        layout.addWidget(self.employees_table)
        
        self.content_area.addWidget(employees_page)
    
    def create_face_attendance_page(self):
        """Создание страницы распознавания лиц"""
        self.face_attendance_widget = FaceAttendanceWidget(self.db, self.user_data)
        self.content_area.addWidget(self.face_attendance_widget)
    
    def create_reports_page(self):
        """Создание страницы отчетов"""
        reports_page = QWidget()
        layout = QVBoxLayout()
        reports_page.setLayout(layout)
        
        title = QLabel("Attendance Reports")
        title.setFont(QFont("Arial", 24, QFont.Bold))
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
        filters_layout = QHBoxLayout()
        filters_frame.setLayout(filters_layout)
        
        # Здесь можно добавить фильтры по дате, сотрудникам и т.д.
        
        layout.addWidget(filters_frame)
        
        # Таблица отчетов
        self.reports_table = QTableWidget()
        self.reports_table.setColumnCount(6)
        self.reports_table.setHorizontalHeaderLabels([
            "Date", "Employee ID", "Name", "Time In", "Time Out", "Total Hours"
        ])
        self.reports_table.horizontalHeader().setStretchLastSection(True)
        self.reports_table.setAlternatingRowColors(True)
        
        layout.addWidget(self.reports_table)
        
        self.content_area.addWidget(reports_page)
    
    def show_dashboard(self):
        self.content_area.setCurrentIndex(0)
        self.update_recent_attendance()
    
    def show_employees(self):
        self.content_area.setCurrentIndex(1)
        self.update_employees_table()
    
    def show_face_attendance(self):
        self.content_area.setCurrentIndex(2)
    
    def show_reports(self):
        self.content_area.setCurrentIndex(3)
    
    def show_add_employee_dialog(self):
        dialog = AddEmployeeDialog(self, self.db, self.user_data)
        if dialog.exec_():
            self.update_employees_table()
            QMessageBox.information(self, "Success", "Employee added successfully!")
    
    def update_time(self):
        current_time = QDateTime.currentDateTime()
        self.time_label.setText(current_time.toString("dddd, MMMM d, yyyy - hh:mm:ss"))
    
    def update_recent_attendance(self):
        """Обновление таблицы последних отметок"""
        records = self.db.get_attendance_report()[:10]  # Последние 10 записей
        
        self.recent_table.setRowCount(len(records))
        for i, record in enumerate(records):
            self.recent_table.setItem(i, 0, QTableWidgetItem(record['employee_code']))
            self.recent_table.setItem(i, 1, QTableWidgetItem(record['full_name']))
            self.recent_table.setItem(i, 2, QTableWidgetItem(record['timestamp']))
            self.recent_table.setItem(i, 3, QTableWidgetItem(record['attendance_type']))
            confidence = f"{record['confidence']*100:.1f}%" if record['confidence'] else "N/A"
            self.recent_table.setItem(i, 4, QTableWidgetItem(confidence))
    
    def update_employees_table(self):
        """Обновление таблицы сотрудников"""
        employees = self.db.get_all_employees()
        
        self.employees_table.setRowCount(len(employees))
        for i, emp in enumerate(employees):
            self.employees_table.setItem(i, 0, QTableWidgetItem(str(emp['id'])))
            self.employees_table.setItem(i, 1, QTableWidgetItem(emp['employee_id']))
            self.employees_table.setItem(i, 2, QTableWidgetItem(emp['full_name']))
            self.employees_table.setItem(i, 3, QTableWidgetItem(emp['designation']))
            self.employees_table.setItem(i, 4, QTableWidgetItem(emp['department']))
            self.employees_table.setItem(i, 5, QTableWidgetItem(emp['email']))
            
            # Кнопка удаления
            delete_btn = QPushButton("🗑️")
            delete_btn.setCursor(Qt.PointingHandCursor)
            delete_btn.clicked.connect(lambda _, emp_id=emp['id']: self.delete_employee(emp_id))
            self.employees_table.setCellWidget(i, 6, delete_btn)
    
    def delete_employee(self, employee_id):
        reply = QMessageBox.question(self, "Confirm Delete", 
                                   "Are you sure you want to delete this employee?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.db.delete_employee(employee_id)
            self.update_employees_table()
            QMessageBox.information(self, "Success", "Employee deleted successfully!")
    
    def logout(self):
        reply = QMessageBox.question(self, "Logout", 
                                   "Are you sure you want to logout?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.close()
            from .login_window import LoginWindow
            self.login_window = LoginWindow()
            self.login_window.show()
        