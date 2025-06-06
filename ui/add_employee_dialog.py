"""
Диалог добавления нового сотрудника
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QLineEdit, QPushButton, QFileDialog, QMessageBox,
                           QFormLayout, QFrame)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap, QPainter, QBrush

import os
import cv2
import face_recognition
import numpy as np
from datetime import datetime

from config import EMPLOYEE_PHOTOS_DIR, PRIMARY_COLOR, SECONDARY_COLOR

class AddEmployeeDialog(QDialog):
    def __init__(self, parent, database, user_data):
        super().__init__(parent)
        self.db = database
        self.user_data = user_data
        self.photo_path = None
        self.face_encoding = None
        self.init_ui()
    
    def init_ui(self):
        """Инициализация интерфейса"""
        self.setWindowTitle("Add Employee")
        self.setFixedSize(800, 600)
        
        # Основной layout
        main_layout = QHBoxLayout()
        self.setLayout(main_layout)
        
        # Левая часть - форма
        form_widget = QWidget()
        form_layout = QVBoxLayout()
        form_widget.setLayout(form_layout)
        
        # Заголовок
        title = QLabel("Add User")
        title.setFont(QFont("Arial", 24, QFont.Bold))
        form_layout.addWidget(title)
        
        # Форма данных
        data_form = QFormLayout()
        
        # Поля ввода
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter full name")
        self.name_input.setStyleSheet(self.get_input_style())
        
        self.designation_input = QLineEdit()
        self.designation_input.setPlaceholderText("Enter designation")
        self.designation_input.setStyleSheet(self.get_input_style())
        
        self.employee_id_input = QLineEdit()
        self.employee_id_input.setPlaceholderText("Enter employee ID")
        self.employee_id_input.setStyleSheet(self.get_input_style())
        
        self.department_input = QLineEdit()
        self.department_input.setPlaceholderText("Enter department")
        self.department_input.setStyleSheet(self.get_input_style())
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Enter email")
        self.email_input.setStyleSheet(self.get_input_style())
        
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("Enter phone number")
        self.phone_input.setStyleSheet(self.get_input_style())
        
        # Добавление полей в форму
        data_form.addRow("Full Name:", self.name_input)
        data_form.addRow("Designation:", self.designation_input)
        data_form.addRow("Employee ID:", self.employee_id_input)
        data_form.addRow("Department:", self.department_input)
        data_form.addRow("Email:", self.email_input)
        data_form.addRow("Phone:", self.phone_input)
        
        form_layout.addLayout(data_form)
        
        # Кнопка добавления
        self.add_button = QPushButton("📝 ADD")
        self.add_button.setFont(QFont("Arial", 14, QFont.Bold))
        self.add_button.setCursor(Qt.PointingHandCursor)
        self.add_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {SECONDARY_COLOR};
                color: white;
                border: none;
                padding: 15px 40px;
                border-radius: 8px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #4cae4c;
            }}
            QPushButton:disabled {{
                background-color: #95a5a6;
            }}
        """)
        self.add_button.clicked.connect(self.add_employee)
        form_layout.addWidget(self.add_button, alignment=Qt.AlignCenter)
        
        main_layout.addWidget(form_widget)
        
        # Правая часть - фото
        photo_widget = QWidget()
        photo_layout = QVBoxLayout()
        photo_widget.setLayout(photo_layout)
        
        # Заголовок
        photo_title = QLabel("Employee Photo")
        photo_title.setFont(QFont("Arial", 18, QFont.Bold))
        photo_title.setAlignment(Qt.AlignCenter)
        photo_layout.addWidget(photo_title)
        
        # Область для фото
        self.photo_label = QLabel()
        self.photo_label.setFixedSize(300, 300)
        self.photo_label.setAlignment(Qt.AlignCenter)
        self.photo_label.setStyleSheet("""
            QLabel {
                border: 3px dashed #ddd;
                border-radius: 15px;
                background-color: #f8f9fa;
            }
        """)
        self.photo_label.setText("📷\nNo photo selected")
        self.photo_label.setFont(QFont("Arial", 16))
        photo_layout.addWidget(self.photo_label, alignment=Qt.AlignCenter)
        
        # Кнопка выбора фото
        self.choose_photo_button = QPushButton("Choose Image")
        self.choose_photo_button.setCursor(Qt.PointingHandCursor)
        self.choose_photo_button.setStyleSheet("""
            QPushButton {
                background-color: #f8f9fa;
                border: 1px solid #ddd;
                padding: 10px 30px;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e9ecef;
            }
        """)
        self.choose_photo_button.clicked.connect(self.choose_photo)
        photo_layout.addWidget(self.choose_photo_button, alignment=Qt.AlignCenter)
        
        # Требования к фото
        requirements_frame = QFrame()
        requirements_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        requirements_layout = QVBoxLayout()
        requirements_frame.setLayout(requirements_layout)
        
        req_title = QLabel("Photo Requirements:")
        req_title.setFont(QFont("Arial", 12, QFont.Bold))
        requirements_layout.addWidget(req_title)
        
        requirements = [
            "• Clear frontal view of face",
            "• Good lighting conditions",
            "• No sunglasses or face coverings",
            "• One person per photo",
            "• JPG or PNG format"
        ]
        
        for req in requirements:
            req_label = QLabel(req)
            req_label.setStyleSheet("color: #666;")
            requirements_layout.addWidget(req_label)
        
        photo_layout.addWidget(requirements_frame)
        
        main_layout.addWidget(photo_widget)
    
    def get_input_style(self):
        """Стиль для полей ввода"""
        return """
            QLineEdit {
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 8px;
                font-size: 14px;
                background-color: #f8f9fa;
            }
            QLineEdit:focus {
                border-color: #667eea;
                background-color: white;
            }
        """
    
    def choose_photo(self):
        """Выбор фото сотрудника"""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self, 
            "Choose Employee Photo", 
            "", 
            "Image Files (*.png *.jpg *.jpeg)"
        )
        
        if file_path:
            # Проверка и обработка изображения
            image = cv2.imread(file_path)
            if image is None:
                QMessageBox.warning(self, "Error", "Failed to load image")
                return
            
            # Поиск лица на фото
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_image)
            
            if len(face_locations) == 0:
                QMessageBox.warning(self, "Error", "No face detected in the photo")
                return
            
            if len(face_locations) > 1:
                QMessageBox.warning(self, "Error", "Multiple faces detected. Please use a photo with only one face")
                return
            
            # Создание кодировки лица
            face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
            if face_encodings:
                self.face_encoding = face_encodings[0].tolist()
                self.photo_path = file_path
                
                # Отображение фото
                pixmap = QPixmap(file_path)
                scaled_pixmap = pixmap.scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.photo_label.setPixmap(scaled_pixmap)
                self.photo_label.setStyleSheet("""
                    QLabel {
                        border: 3px solid #4cae4c;
                        border-radius: 15px;
                    }
                """)
    
    def add_employee(self):
        """Добавление сотрудника в базу данных"""
        # Проверка полей
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Error", "Please enter employee name")
            return
        
        if not self.employee_id_input.text().strip():
            QMessageBox.warning(self, "Error", "Please enter employee ID")
            return
        
        if not self.photo_path:
            QMessageBox.warning(self, "Error", "Please select employee photo")
            return
        
        # Сохранение фото
        employee_id = self.employee_id_input.text().strip()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        photo_filename = f"{employee_id}_{timestamp}.jpg"
        photo_save_path = os.path.join(EMPLOYEE_PHOTOS_DIR, photo_filename)
        
        # Копирование фото
        image = cv2.imread(self.photo_path)
        cv2.imwrite(photo_save_path, image)
        
        # Подготовка данных
        employee_data = {
            'employee_id': employee_id,
            'full_name': self.name_input.text().strip(),
            'designation': self.designation_input.text().strip(),
            'department': self.department_input.text().strip(),
            'email': self.email_input.text().strip(),
            'phone': self.phone_input.text().strip(),
            'photo_path': photo_filename,
            'face_encoding': self.face_encoding
        }
        
        # Добавление в базу данных
        result = self.db.add_employee(employee_data, self.user_data['id'])
        
        if result:
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "Employee ID already exists")
    
    def keyPressEvent(self, event):
        """Обработка нажатий клавиш"""
        if event.key() == Qt.Key_Escape:
            self.reject()