"""
Улучшенный адаптивный диалог добавления пользователя
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QLineEdit, QPushButton, QFileDialog, QMessageBox,
                           QFormLayout, QFrame, QWidget, QTabWidget, QSizePolicy,
                           QScrollArea, QDesktopWidget, QSplitter)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap, QPainter, QBrush

import os
import cv2
import face_recognition
import numpy as np
from datetime import datetime

from config import USER_PHOTOS_DIR, PRIMARY_COLOR, SECONDARY_COLOR

class CameraThread(QThread):
    """Поток для работы с камерой"""
    frame_ready = pyqtSignal(np.ndarray)
    face_detected = pyqtSignal(np.ndarray, list)
    
    def __init__(self):
        super().__init__()
        self.is_running = False
        self.cap = None
    
    def run(self):
        self.is_running = True
        
        try:
            self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                return
            
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception as e:
            return
        
        while self.is_running:
            try:
                ret, frame = self.cap.read()
                if not ret:
                    if self.is_running:
                        continue
                    else:
                        break
                
                if self.is_running:
                    self.frame_ready.emit(frame.copy())
                
                if self.is_running:
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    face_locations = face_recognition.face_locations(rgb_frame)
                    
                    if face_locations and self.is_running:
                        self.face_detected.emit(frame.copy(), face_locations)
                        
            except Exception as e:
                if self.is_running:
                    continue
                else:
                    break
        
        if self.cap:
            try:
                self.cap.release()
            except:
                pass
            self.cap = None
    
    def stop(self):
        self.is_running = False
        
        if self.cap:
            try:
                self.cap.release()
            except Exception as e:
                print(f"Ошибка при освобождении камеры: {e}")
            self.cap = None
        
        if not self.wait(2000):
            self.terminate()
            self.wait(1000)

class AddUserDialog(QDialog):
    def __init__(self, parent, database, admin_data):
        super().__init__(parent)
        self.db = database
        self.admin_data = admin_data
        self.photo_path = None
        self.face_encoding = None
        self.camera_thread = None
        self.current_frame = None
        self.detected_faces = []
        self.init_ui()
    
    def init_ui(self):
        """Инициализация адаптивного интерфейса"""
        self.setWindowTitle("Добавить пользователя")
        
        # Адаптивные размеры
        desktop = QDesktopWidget()
        screen_rect = desktop.screenGeometry()
        
        # Более компактные размеры
        dialog_width = min(800, screen_rect.width() - 100)
        dialog_height = min(600, screen_rect.height() - 100)
        
        self.setMinimumSize(600, 400)
        self.resize(dialog_width, dialog_height)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Центрирование
        x = (screen_rect.width() - dialog_width) // 2
        y = (screen_rect.height() - dialog_height) // 2
        self.move(max(0, x), max(0, y))
        
        # Основной layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        self.setLayout(main_layout)
        
        # Заголовок
        title = QLabel("Добавление нового пользователя")
        title.setFont(QFont("Arial", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        main_layout.addWidget(title)
        
        # Создание разделителя для адаптивности
        content_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(content_splitter)
        
        # Левая часть - форма данных
        left_widget = self.create_form_section()
        content_splitter.addWidget(left_widget)
        
        # Правая часть - фото/камера
        right_widget = self.create_photo_section()
        content_splitter.addWidget(right_widget)
        
        # Пропорции (40% форма / 60% фото)
        content_splitter.setSizes([320, 480])
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.setFont(QFont("Arial", 12))
        self.cancel_button.setCursor(Qt.PointingHandCursor)
        self.cancel_button.setMinimumHeight(35)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        self.cancel_button.clicked.connect(self.reject)
        
        self.add_button = QPushButton("Добавить пользователя")
        self.add_button.setFont(QFont("Arial", 12, QFont.Bold))
        self.add_button.setCursor(Qt.PointingHandCursor)
        self.add_button.setMinimumHeight(35)
        self.add_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {SECONDARY_COLOR};
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #4cae4c;
            }}
            QPushButton:disabled {{
                background-color: #95a5a6;
            }}
        """)
        self.add_button.clicked.connect(self.add_user)
        
        buttons_layout.addWidget(self.cancel_button)
        buttons_layout.addWidget(self.add_button)
        
        main_layout.addLayout(buttons_layout)
    
    def create_form_section(self):
        """Создание секции формы"""
        form_widget = QWidget()
        form_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        form_widget.setLayout(layout)
        
        # Форма данных
        form_frame = QFrame()
        form_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 8px;
                padding: 15px;
                border: 1px solid #e0e0e0;
            }
        """)
        form_layout = QFormLayout()
        form_frame.setLayout(form_layout)
        
        # Компактные поля ввода
        self.user_id_input = QLineEdit()
        self.user_id_input.setPlaceholderText("Введите ID")
        self.user_id_input.setStyleSheet(self.get_input_style())
        self.user_id_input.setMinimumHeight(35)
        self.user_id_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        self.full_name_input = QLineEdit()
        self.full_name_input.setPlaceholderText("Введите полное имя")
        self.full_name_input.setStyleSheet(self.get_input_style())
        self.full_name_input.setMinimumHeight(35)
        self.full_name_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        # Добавление полей в форму
        form_layout.addRow("ID пользователя:", self.user_id_input)
        form_layout.addRow("Полное имя:", self.full_name_input)
        
        layout.addWidget(form_frame)
        
        # Требования к фото
        requirements_frame = QFrame()
        requirements_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 6px;
                padding: 10px;
                border: 1px solid #e9ecef;
            }
        """)
        requirements_layout = QVBoxLayout()
        requirements_frame.setLayout(requirements_layout)
        
        req_title = QLabel("Требования к фотографии:")
        req_title.setFont(QFont("Arial", 11, QFont.Bold))
        requirements_layout.addWidget(req_title)
        
        requirements = [
            "• Четкое изображение лица",
            "• Хорошее освещение",
            "• Без очков",
            "• Один человек на фото"
        ]
        
        for req in requirements:
            req_label = QLabel(req)
            req_label.setFont(QFont("Arial", 9))
            req_label.setStyleSheet("color: #666; margin-left: 10px;")
            requirements_layout.addWidget(req_label)
        
        layout.addWidget(requirements_frame)
        layout.addStretch()
        
        return form_widget
    
    def create_photo_section(self):
        """Создание секции фото/камеры"""
        photo_widget = QWidget()
        photo_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        photo_widget.setLayout(layout)
        
        # Вкладки для выбора способа добавления фото
        self.tab_widget = QTabWidget()
        self.tab_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Вкладка с файлом
        self.file_tab = self.create_file_tab()
        self.tab_widget.addTab(self.file_tab, "Загрузить файл")
        
        # Вкладка с камерой
        self.camera_tab = self.create_camera_tab()
        self.tab_widget.addTab(self.camera_tab, "Снять с камеры")
        
        layout.addWidget(self.tab_widget)
        
        # Обработка смены вкладок
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        
        return photo_widget
    
    def create_file_tab(self):
        """Создание вкладки загрузки файла"""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        tab.setLayout(layout)
        
        # Компактная область для фото
        self.photo_label = QLabel()
        self.photo_label.setMinimumSize(200, 200)
        self.photo_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.photo_label.setAlignment(Qt.AlignCenter)
        self.photo_label.setStyleSheet("""
            QLabel {
                border: 2px dashed #ddd;
                border-radius: 8px;
                background-color: #f8f9fa;
                font-size: 12px;
                color: #666;
            }
        """)
        self.photo_label.setText("Фото не выбрано\nНажмите кнопку ниже")
        layout.addWidget(self.photo_label)
        
        # Компактная кнопка выбора фото
        self.choose_photo_button = QPushButton("Выбрать изображение")
        self.choose_photo_button.setCursor(Qt.PointingHandCursor)
        self.choose_photo_button.setMinimumHeight(35)
        self.choose_photo_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.choose_photo_button.setStyleSheet("""
            QPushButton {
                background-color: #f8f9fa;
                border: 1px solid #ddd;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
            }
        """)
        self.choose_photo_button.clicked.connect(self.choose_photo)
        layout.addWidget(self.choose_photo_button)
        
        return tab
    
    def create_camera_tab(self):
        """Создание вкладки с камерой"""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        tab.setLayout(layout)
        
        # Компактная область видео
        self.camera_label = QLabel()
        self.camera_label.setMinimumSize(300, 200)
        self.camera_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setStyleSheet("""
            QLabel {
                border: 2px solid #ddd;
                border-radius: 8px;
                background-color: #000;
                color: #666;
                font-size: 12px;
            }
        """)
        self.camera_label.setText("Камера выключена")
        layout.addWidget(self.camera_label)
        
        # Компактные кнопки управления камерой
        camera_controls = QHBoxLayout()
        
        self.start_camera_button = QPushButton("Включить")
        self.start_camera_button.setFont(QFont("Arial", 10))
        self.start_camera_button.setCursor(Qt.PointingHandCursor)
        self.start_camera_button.setMinimumHeight(30)
        self.start_camera_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {SECONDARY_COLOR};
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #4cae4c;
            }}
        """)
        self.start_camera_button.clicked.connect(self.start_camera)
        
        self.stop_camera_button = QPushButton("Выключить")
        self.stop_camera_button.setFont(QFont("Arial", 10))
        self.stop_camera_button.setCursor(Qt.PointingHandCursor)
        self.stop_camera_button.setMinimumHeight(30)
        self.stop_camera_button.setEnabled(False)
        self.stop_camera_button.setStyleSheet("""
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
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        self.stop_camera_button.clicked.connect(self.stop_camera)
        
        self.capture_button = QPushButton("Захватить")
        self.capture_button.setFont(QFont("Arial", 10))
        self.capture_button.setCursor(Qt.PointingHandCursor)
        self.capture_button.setMinimumHeight(30)
        self.capture_button.setEnabled(False)
        self.capture_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {PRIMARY_COLOR};
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #2d4aa3;
            }}
            QPushButton:disabled {{
                background-color: #6c757d;
            }}
        """)
        self.capture_button.clicked.connect(self.capture_face)
        
        camera_controls.addWidget(self.start_camera_button)
        camera_controls.addWidget(self.stop_camera_button)
        camera_controls.addWidget(self.capture_button)
        
        layout.addLayout(camera_controls)
        
        # Компактный статус
        self.camera_status_label = QLabel("Камера выключена")
        self.camera_status_label.setFont(QFont("Arial", 10))
        self.camera_status_label.setAlignment(Qt.AlignCenter)
        self.camera_status_label.setMinimumHeight(25)
        self.camera_status_label.setStyleSheet("""
            QLabel {
                background-color: #6c757d;
                color: white;
                padding: 5px;
                border-radius: 4px;
                margin: 5px;
            }
        """)
        layout.addWidget(self.camera_status_label)
        
        return tab
    
    def get_input_style(self):
        """Стиль для полей ввода"""
        return """
            QLineEdit {
                padding: 8px 12px;
                border: 1px solid #ddd;
                border-radius: 6px;
                font-size: 12px;
                background-color: #f8f9fa;
            }
            QLineEdit:focus {
                border-color: #667eea;
                background-color: white;
            }
        """
    
    # Остальные методы остаются без изменений
    def on_tab_changed(self, index):
        if index == 0:
            self.stop_camera()
    
    def choose_photo(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self, "Выберите фото пользователя", "", 
            "Image Files (*.png *.jpg *.jpeg)"
        )
        
        if file_path:
            self.process_image_file(file_path)
    
    def process_image_file(self, file_path):
        image = cv2.imread(file_path)
        if image is None:
            QMessageBox.warning(self, "Ошибка", "Не удалось загрузить изображение")
            return
        
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_image)
        
        if len(face_locations) == 0:
            QMessageBox.warning(self, "Ошибка", "На фотографии не обнаружено лицо")
            return
        
        if len(face_locations) > 1:
            QMessageBox.warning(self, "Ошибка", "На фотографии обнаружено несколько лиц")
            return
        
        face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
        if face_encodings:
            self.face_encoding = face_encodings[0].tolist()
            self.photo_path = file_path
            self.display_image_with_face_box(image, face_locations[0])
            QMessageBox.information(self, "Успех", "Лицо успешно обнаружено!")
    
    def display_image_with_face_box(self, image, face_location):
        display_image = image.copy()
        top, right, bottom, left = face_location
        cv2.rectangle(display_image, (left, top), (right, bottom), (0, 255, 0), 3)
        
        rgb_image = cv2.cvtColor(display_image, cv2.COLOR_BGR2RGB)
        height, width, channel = rgb_image.shape
        bytes_per_line = 3 * width
        
        from PyQt5.QtGui import QImage
        q_image = QImage(rgb_image.data, width, height, bytes_per_line, QImage.Format_RGB888)
        
        pixmap = QPixmap.fromImage(q_image)
        scaled_pixmap = pixmap.scaled(
            self.photo_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        
        self.photo_label.setPixmap(scaled_pixmap)
        self.photo_label.setStyleSheet("""
            QLabel {
                border: 2px solid #4cae4c;
                border-radius: 8px;
            }
        """)
    
    def start_camera(self):
        self.camera_thread = CameraThread()
        self.camera_thread.frame_ready.connect(self.update_camera_frame)
        self.camera_thread.face_detected.connect(self.on_face_detected)
        self.camera_thread.start()
        
        self.start_camera_button.setEnabled(False)
        self.stop_camera_button.setEnabled(True)
        self.capture_button.setEnabled(True)
        
        self.camera_status_label.setText("Поиск лица...")
        self.camera_status_label.setStyleSheet("""
            QLabel {
                background-color: #28a745;
                color: white;
                padding: 5px;
                border-radius: 4px;
                margin: 5px;
            }
        """)
    
    def stop_camera(self):
        self.start_camera_button.setEnabled(True)
        self.stop_camera_button.setEnabled(False)
        self.capture_button.setEnabled(False)
        
        if self.camera_thread:
            self.camera_thread.stop()
            self.camera_thread = None
        
        self.camera_label.clear()
        self.camera_label.setText("Камера выключена")
        self.camera_label.setStyleSheet("""
            QLabel {
                border: 2px solid #ddd;
                border-radius: 8px;
                background-color: #000;
                color: #666;
                font-size: 12px;
            }
        """)
        
        self.camera_status_label.setText("Камера выключена")
        self.camera_status_label.setStyleSheet("""
            QLabel {
                background-color: #6c757d;
                color: white;
                padding: 5px;
                border-radius: 4px;
                margin: 5px;
            }
        """)
        
        self.current_frame = None
        self.detected_faces = []
    
    def update_camera_frame(self, frame):
        self.current_frame = frame.copy()
        
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, channel = rgb_frame.shape
        bytes_per_line = 3 * width
        
        from PyQt5.QtGui import QImage
        q_image = QImage(rgb_frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
        
        pixmap = QPixmap.fromImage(q_image)
        scaled_pixmap = pixmap.scaled(
            self.camera_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        
        self.camera_label.setPixmap(scaled_pixmap)
    
    def on_face_detected(self, frame, face_locations):
        self.detected_faces = face_locations
        
        if len(face_locations) == 1:
            self.camera_status_label.setText("Лицо найдено!")
            self.camera_status_label.setStyleSheet("""
                QLabel {
                    background-color: #28a745;
                    color: white;
                    padding: 5px;
                    border-radius: 4px;
                    margin: 5px;
                }
            """)
        elif len(face_locations) > 1:
            self.camera_status_label.setText("Несколько лиц")
            self.camera_status_label.setStyleSheet("""
                QLabel {
                    background-color: #ffc107;
                    color: black;
                    padding: 5px;
                    border-radius: 4px;
                    margin: 5px;
                }
            """)
        else:
            self.camera_status_label.setText("Поиск лица...")
            self.camera_status_label.setStyleSheet("""
                QLabel {
                    background-color: #17a2b8;
                    color: white;
                    padding: 5px;
                    border-radius: 4px;
                    margin: 5px;
                }
            """)
    
    def capture_face(self):
        if not self.current_frame is None and len(self.detected_faces) == 1:
            rgb_frame = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2RGB)
            face_encodings = face_recognition.face_encodings(rgb_frame, self.detected_faces)
            
            if face_encodings:
                self.face_encoding = face_encodings[0].tolist()
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                temp_filename = f"temp_capture_{timestamp}.jpg"
                temp_path = os.path.join(USER_PHOTOS_DIR, temp_filename)
                
                display_frame = self.current_frame.copy()
                top, right, bottom, left = self.detected_faces[0]
                cv2.rectangle(display_frame, (left, top), (right, bottom), (0, 255, 0), 3)
                cv2.imwrite(temp_path, display_frame)
                
                self.photo_path = temp_path
                self.stop_camera()
                self.tab_widget.setCurrentIndex(0)
                self.display_image_with_face_box(self.current_frame, self.detected_faces[0])
                
                QMessageBox.information(self, "Успех", "Лицо успешно захвачено!")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось создать кодировку лица")
        else:
            QMessageBox.warning(self, "Ошибка", "Убедитесь, что в кадре только одно лицо")
    
    def add_user(self):
        if not self.user_id_input.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите идентификатор пользователя")
            return
        
        if not self.full_name_input.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите полное имя пользователя")
            return
        
        if not self.face_encoding:
            QMessageBox.warning(self, "Ошибка", "Добавьте фотографию пользователя")
            return
        
        user_id = self.user_id_input.text().strip()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        photo_filename = f"{user_id}_{timestamp}.jpg"
        photo_save_path = os.path.join(USER_PHOTOS_DIR, photo_filename)
        
        if self.photo_path:
            image = cv2.imread(self.photo_path)
            cv2.imwrite(photo_save_path, image)
        
        user_data = {
            'user_id': user_id,
            'full_name': self.full_name_input.text().strip(),
            'photo_path': photo_filename,
            'face_encoding': self.face_encoding
        }
        
        result = self.db.add_user(user_data, self.admin_data['id'])
        
        if result:
            if self.photo_path and 'temp_capture_' in self.photo_path:
                try:
                    os.remove(self.photo_path)
                except:
                    pass
            
            self.accept()
        else:
            QMessageBox.warning(self, "Ошибка", "Пользователь с таким идентификатором уже существует")
    
    def closeEvent(self, event):
        self.stop_camera()
        
        if self.photo_path and 'temp_capture_' in self.photo_path:
            try:
                os.remove(self.photo_path)
            except:
                pass
        
        event.accept()
    
    def reject(self):
        self.stop_camera()
        
        if self.photo_path and 'temp_capture_' in self.photo_path:
            try:
                os.remove(self.photo_path)
            except:
                pass
        
        super().reject()
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.reject()