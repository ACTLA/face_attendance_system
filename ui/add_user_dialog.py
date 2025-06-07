"""
Диалог добавления нового пользователя в систему распознавания лиц
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QLineEdit, QPushButton, QFileDialog, QMessageBox,
                           QFormLayout, QFrame, QWidget, QTabWidget, QSizePolicy,
                           QScrollArea)
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
            # Принудительное использование DirectShow
            self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            
            if not self.cap.isOpened():
                # Попробуем без DirectShow
                self.cap = cv2.VideoCapture(0)
                
            if not self.cap.isOpened():
                return
            
            # Настройка буферизации
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
                
                # Отправка кадра для отображения
                if self.is_running:
                    self.frame_ready.emit(frame.copy())
                
                # Поиск лиц
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
        
        # Финальная очистка
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
        
        # Ожидание завершения потока с таймаутом
        if not self.wait(2000):  # 2 секунды таймаут
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
        from PyQt5.QtWidgets import QDesktopWidget
        desktop = QDesktopWidget()
        screen_rect = desktop.screenGeometry()
        
        if screen_rect.width() >= 1920:
            dialog_width, dialog_height = 850, 600
            photo_size, camera_width, camera_height = 250, 450, 340
        elif screen_rect.width() >= 1366:
            dialog_width, dialog_height = 800, 550
            photo_size, camera_width, camera_height = 220, 400, 300
        else:
            dialog_width, dialog_height = 750, 500
            photo_size, camera_width, camera_height = 200, 350, 260
        
        self.setMinimumSize(700, 450)
        self.resize(dialog_width, dialog_height)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Центрирование
        x = (screen_rect.width() - dialog_width) // 2
        y = (screen_rect.height() - dialog_height) // 2
        self.move(max(0, x), max(0, y))
        
        # Сохраняем размеры для адаптивности
        self.photo_size = photo_size
        self.camera_width = camera_width
        self.camera_height = camera_height
        
        # Основной layout с прокруткой
        main_scroll = QScrollArea()
        main_scroll.setWidgetResizable(True)
        main_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        main_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        main_widget.setLayout(main_layout)
        
        main_scroll.setWidget(main_widget)
        
        # Финальный layout
        final_layout = QVBoxLayout()
        final_layout.setContentsMargins(0, 0, 0, 0)
        final_layout.addWidget(main_scroll)
        self.setLayout(final_layout)
        
        # Заголовок
        title = QLabel("Добавление нового пользователя")
        title.setFont(QFont("Arial", 24, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        # Форма данных
        form_frame = QFrame()
        form_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                padding: 20px;
                margin: 10px;
            }
        """)
        form_layout = QFormLayout()
        form_frame.setLayout(form_layout)
        
        # Поля ввода
        self.user_id_input = QLineEdit()
        self.user_id_input.setPlaceholderText("Введите уникальный идентификатор")
        self.user_id_input.setStyleSheet(self.get_input_style())
        self.user_id_input.setMinimumHeight(40)
        
        self.full_name_input = QLineEdit()
        self.full_name_input.setPlaceholderText("Введите полное имя")
        self.full_name_input.setStyleSheet(self.get_input_style())
        self.full_name_input.setMinimumHeight(40)
        
        # Добавление полей в форму
        form_layout.addRow("Идентификатор пользователя:", self.user_id_input)
        form_layout.addRow("Полное имя:", self.full_name_input)
        
        main_layout.addWidget(form_frame)
        
        # Вкладки для выбора способа добавления фото
        self.tab_widget = QTabWidget()
        self.tab_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Вкладка с файлом
        self.file_tab = self.create_file_tab()
        self.tab_widget.addTab(self.file_tab, "📁 Загрузить файл")
        
        # Вкладка с камерой
        self.camera_tab = self.create_camera_tab()
        self.tab_widget.addTab(self.camera_tab, "📷 Снять с камеры")
        
        main_layout.addWidget(self.tab_widget)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        
        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.setFont(QFont("Arial", 14))
        self.cancel_button.setCursor(Qt.PointingHandCursor)
        self.cancel_button.setMinimumHeight(45)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 12px 30px;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        self.cancel_button.clicked.connect(self.reject)
        
        self.add_button = QPushButton("➕ Добавить пользователя")
        self.add_button.setFont(QFont("Arial", 14, QFont.Bold))
        self.add_button.setCursor(Qt.PointingHandCursor)
        self.add_button.setMinimumHeight(45)
        self.add_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {SECONDARY_COLOR};
                color: white;
                border: none;
                padding: 12px 30px;
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
        self.add_button.clicked.connect(self.add_user)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.cancel_button)
        buttons_layout.addWidget(self.add_button)
        
        main_layout.addLayout(buttons_layout)
        
        # Обработка смены вкладок
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
    
    def create_file_tab(self):
        """Создание вкладки загрузки файла"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        # Область для фото
        self.photo_label = QLabel()
        self.photo_label.setFixedSize(self.photo_size, self.photo_size)
        self.photo_label.setAlignment(Qt.AlignCenter)
        self.photo_label.setStyleSheet("""
            QLabel {
                border: 3px dashed #ddd;
                border-radius: 15px;
                background-color: #f8f9fa;
            }
        """)
        self.photo_label.setText("📷\nФото не выбрано")
        self.photo_label.setFont(QFont("Arial", 16))
        layout.addWidget(self.photo_label, 0, Qt.AlignCenter)
        
        # Кнопка выбора фото
        self.choose_photo_button = QPushButton("Выбрать изображение")
        self.choose_photo_button.setCursor(Qt.PointingHandCursor)
        self.choose_photo_button.setMinimumHeight(40)
        self.choose_photo_button.setStyleSheet("""
            QPushButton {
                background-color: #f8f9fa;
                border: 1px solid #ddd;
                padding: 12px 30px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
            }
        """)
        self.choose_photo_button.clicked.connect(self.choose_photo)
        layout.addWidget(self.choose_photo_button, 0, Qt.AlignCenter)
        
        # Требования к фото
        requirements_frame = QFrame()
        requirements_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 8px;
                padding: 15px;
                margin: 10px;
            }
        """)
        requirements_layout = QVBoxLayout()
        requirements_frame.setLayout(requirements_layout)
        
        req_title = QLabel("Требования к фотографии:")
        req_title.setFont(QFont("Arial", 12, QFont.Bold))
        requirements_layout.addWidget(req_title)
        
        requirements = [
            "• Четкое изображение лица в анфас",
            "• Хорошее освещение",
            "• Без солнцезащитных очков",
            "• Один человек на фото",
            "• Формат JPG или PNG"
        ]
        
        for req in requirements:
            req_label = QLabel(req)
            req_label.setStyleSheet("color: #666; margin-left: 10px;")
            requirements_layout.addWidget(req_label)
        
        layout.addWidget(requirements_frame)
        
        return tab
    
    def create_camera_tab(self):
        """Создание вкладки с камерой"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        # Область видео
        self.camera_label = QLabel()
        self.camera_label.setFixedSize(self.camera_width, self.camera_height)
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setStyleSheet("""
            QLabel {
                border: 2px solid #ddd;
                border-radius: 10px;
                background-color: #000;
            }
        """)
        self.camera_label.setText("📷\nКамера выключена")
        self.camera_label.setFont(QFont("Arial", 20))
        self.camera_label.setStyleSheet("""
            QLabel {
                border: 2px solid #ddd;
                border-radius: 10px;
                background-color: #000;
                color: #666;
            }
        """)
        layout.addWidget(self.camera_label, 0, Qt.AlignCenter)
        
        # Кнопки управления камерой
        camera_controls = QHBoxLayout()
        
        self.start_camera_button = QPushButton("▶️ Включить камеру")
        self.start_camera_button.setFont(QFont("Arial", 12))
        self.start_camera_button.setCursor(Qt.PointingHandCursor)
        self.start_camera_button.setMinimumHeight(40)
        self.start_camera_button.setStyleSheet(f"""
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
        self.start_camera_button.clicked.connect(self.start_camera)
        
        self.stop_camera_button = QPushButton("⏹️ Выключить камеру")
        self.stop_camera_button.setFont(QFont("Arial", 12))
        self.stop_camera_button.setCursor(Qt.PointingHandCursor)
        self.stop_camera_button.setMinimumHeight(40)
        self.stop_camera_button.setEnabled(False)
        self.stop_camera_button.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 8px;
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
        
        self.capture_button = QPushButton("📸 Захватить лицо")
        self.capture_button.setFont(QFont("Arial", 12))
        self.capture_button.setCursor(Qt.PointingHandCursor)
        self.capture_button.setMinimumHeight(40)
        self.capture_button.setEnabled(False)
        self.capture_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {PRIMARY_COLOR};
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 8px;
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
        
        # Статус
        self.camera_status_label = QLabel("Камера выключена")
        self.camera_status_label.setFont(QFont("Arial", 14))
        self.camera_status_label.setAlignment(Qt.AlignCenter)
        self.camera_status_label.setStyleSheet("""
            QLabel {
                background-color: #6c757d;
                color: white;
                padding: 10px;
                border-radius: 8px;
                margin: 10px;
            }
        """)
        layout.addWidget(self.camera_status_label)
        
        return tab
    
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
    
    def on_tab_changed(self, index):
        """Обработка смены вкладок"""
        if index == 0:  # Вкладка файла
            self.stop_camera()
        elif index == 1:  # Вкладка камеры
            pass  # Камеру включаем только по кнопке
    
    def choose_photo(self):
        """Выбор фото из файла"""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self, 
            "Выберите фото пользователя", 
            "", 
            "Image Files (*.png *.jpg *.jpeg)"
        )
        
        if file_path:
            self.process_image_file(file_path)
    
    def process_image_file(self, file_path):
        """Обработка выбранного изображения"""
        # Проверка и обработка изображения
        image = cv2.imread(file_path)
        if image is None:
            QMessageBox.warning(self, "Ошибка", "Не удалось загрузить изображение")
            return
        
        # Поиск лица на фото
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_image)
        
        if len(face_locations) == 0:
            QMessageBox.warning(self, "Ошибка", "На фотографии не обнаружено лицо")
            return
        
        if len(face_locations) > 1:
            QMessageBox.warning(self, "Ошибка", "На фотографии обнаружено несколько лиц. Используйте фото с одним лицом")
            return
        
        # Создание кодировки лица
        face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
        if face_encodings:
            self.face_encoding = face_encodings[0].tolist()
            self.photo_path = file_path
            
            # Отображение фото с рамкой вокруг лица
            self.display_image_with_face_box(image, face_locations[0])
            
            QMessageBox.information(self, "Успех", "Лицо успешно обнаружено и обработано!")
    
    def display_image_with_face_box(self, image, face_location):
        """Отображение изображения с рамкой вокруг лица"""
        # Копируем изображение
        display_image = image.copy()
        
        # Рисуем рамку вокруг лица
        top, right, bottom, left = face_location
        cv2.rectangle(display_image, (left, top), (right, bottom), (0, 255, 0), 3)
        
        # Конвертируем для отображения в Qt
        rgb_image = cv2.cvtColor(display_image, cv2.COLOR_BGR2RGB)
        height, width, channel = rgb_image.shape
        bytes_per_line = 3 * width
        
        from PyQt5.QtGui import QImage
        q_image = QImage(rgb_image.data, width, height, bytes_per_line, QImage.Format_RGB888)
        
        # Масштабируем для отображения
        pixmap = QPixmap.fromImage(q_image)
        scaled_pixmap = pixmap.scaled(self.photo_size, self.photo_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        self.photo_label.setPixmap(scaled_pixmap)
        self.photo_label.setStyleSheet("""
            QLabel {
                border: 3px solid #4cae4c;
                border-radius: 15px;
            }
        """)
    
    def start_camera(self):
        """Запуск камеры"""
        self.camera_thread = CameraThread()
        self.camera_thread.frame_ready.connect(self.update_camera_frame)
        self.camera_thread.face_detected.connect(self.on_face_detected)
        self.camera_thread.start()
        
        self.start_camera_button.setEnabled(False)
        self.stop_camera_button.setEnabled(True)
        self.capture_button.setEnabled(True)
        
        self.camera_status_label.setText("Камера включена - ищем лица...")
        self.camera_status_label.setStyleSheet("""
            QLabel {
                background-color: #28a745;
                color: white;
                padding: 10px;
                border-radius: 8px;
                margin: 10px;
            }
        """)
    
    def stop_camera(self):
        """Остановка камеры"""
        print("Останавливаем камеру в диалоге...")
        
        # Отключаем кнопки сразу
        self.start_camera_button.setEnabled(True)
        self.stop_camera_button.setEnabled(False)
        self.capture_button.setEnabled(False)
        
        if self.camera_thread:
            print("Останавливаем поток камеры...")
            self.camera_thread.stop()
            self.camera_thread = None
        
        # Показываем заглушку вместо последнего кадра
        self.camera_label.clear()
        self.camera_label.setText("📷\nКамера выключена")
        self.camera_label.setFont(QFont("Arial", 20))
        self.camera_label.setStyleSheet("""
            QLabel {
                border: 2px solid #ddd;
                border-radius: 10px;
                background-color: #000;
                color: #666;
            }
        """)
        
        self.camera_status_label.setText("Камера выключена")
        self.camera_status_label.setStyleSheet("""
            QLabel {
                background-color: #6c757d;
                color: white;
                padding: 10px;
                border-radius: 8px;
                margin: 10px;
            }
        """)
        
        self.current_frame = None
        self.detected_faces = []
        print("Камера в диалоге остановлена")
    
    def update_camera_frame(self, frame):
        """Обновление кадра с камеры"""
        self.current_frame = frame.copy()
        
        # Конвертация кадра в QImage
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width, channel = rgb_frame.shape
        bytes_per_line = 3 * width
        
        from PyQt5.QtGui import QImage
        q_image = QImage(rgb_frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
        
        # Масштабирование для отображения
        pixmap = QPixmap.fromImage(q_image)
        scaled_pixmap = pixmap.scaled(self.camera_width, self.camera_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        self.camera_label.setPixmap(scaled_pixmap)
        self.camera_label.setStyleSheet("""
            QLabel {
                border: 2px solid #ddd;
                border-radius: 10px;
            }
        """)
    
    def on_face_detected(self, frame, face_locations):
        """Обработка обнаруженных лиц"""
        self.detected_faces = face_locations
        
        if len(face_locations) == 1:
            # Одно лицо обнаружено
            self.camera_status_label.setText("✅ Лицо обнаружено - готово к захвату")
            self.camera_status_label.setStyleSheet("""
                QLabel {
                    background-color: #28a745;
                    color: white;
                    padding: 10px;
                    border-radius: 8px;
                    margin: 10px;
                }
            """)
            
            # Рисуем рамку на кадре
            display_frame = frame.copy()
            top, right, bottom, left = face_locations[0]
            cv2.rectangle(display_frame, (left, top), (right, bottom), (0, 255, 0), 3)
            
            # Обновляем отображение
            rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
            height, width, channel = rgb_frame.shape
            bytes_per_line = 3 * width
            
            from PyQt5.QtGui import QImage
            q_image = QImage(rgb_frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(q_image)
            scaled_pixmap = pixmap.scaled(640, 480, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            self.camera_label.setPixmap(scaled_pixmap)
            
        elif len(face_locations) > 1:
            # Несколько лиц
            self.camera_status_label.setText("⚠️ Обнаружено несколько лиц")
            self.camera_status_label.setStyleSheet("""
                QLabel {
                    background-color: #ffc107;
                    color: black;
                    padding: 10px;
                    border-radius: 8px;
                    margin: 10px;
                }
            """)
        else:
            # Лица не обнаружены
            self.camera_status_label.setText("🔍 Поиск лица...")
            self.camera_status_label.setStyleSheet("""
                QLabel {
                    background-color: #17a2b8;
                    color: white;
                    padding: 10px;
                    border-radius: 8px;
                    margin: 10px;
                }
            """)
    
    def capture_face(self):
        """Захват лица с камеры"""
        if not self.current_frame is None and len(self.detected_faces) == 1:
            # Обработка кадра
            rgb_frame = cv2.cvtColor(self.current_frame, cv2.COLOR_BGR2RGB)
            face_encodings = face_recognition.face_encodings(rgb_frame, self.detected_faces)
            
            if face_encodings:
                self.face_encoding = face_encodings[0].tolist()
                
                # Сохранение изображения во временный файл
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                temp_filename = f"temp_capture_{timestamp}.jpg"
                temp_path = os.path.join(USER_PHOTOS_DIR, temp_filename)
                
                # Сохраняем кадр с рамкой
                display_frame = self.current_frame.copy()
                top, right, bottom, left = self.detected_faces[0]
                cv2.rectangle(display_frame, (left, top), (right, bottom), (0, 255, 0), 3)
                cv2.imwrite(temp_path, display_frame)
                
                self.photo_path = temp_path
                
                # Остановка камеры
                self.stop_camera()
                
                # Переключение на вкладку файла для показа результата
                self.tab_widget.setCurrentIndex(0)
                self.display_image_with_face_box(self.current_frame, self.detected_faces[0])
                
                QMessageBox.information(self, "Успех", "Лицо успешно захвачено!")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось создать кодировку лица")
        else:
            if self.current_frame is None:
                QMessageBox.warning(self, "Ошибка", "Кадр с камеры не получен")
            elif len(self.detected_faces) == 0:
                QMessageBox.warning(self, "Ошибка", "Лицо не обнаружено. Убедитесь, что ваше лицо хорошо видно в кадре")
            elif len(self.detected_faces) > 1:
                QMessageBox.warning(self, "Ошибка", "Обнаружено несколько лиц. Убедитесь, что в кадре только одно лицо")
            else:
                QMessageBox.warning(self, "Ошибка", "Неизвестная ошибка при захвате лица")
    
    def add_user(self):
        """Добавление пользователя в базу данных"""
        # Проверка полей
        if not self.user_id_input.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите идентификатор пользователя")
            return
        
        if not self.full_name_input.text().strip():
            QMessageBox.warning(self, "Ошибка", "Введите полное имя пользователя")
            return
        
        if not self.face_encoding:
            QMessageBox.warning(self, "Ошибка", "Добавьте фотографию пользователя")
            return
        
        # Сохранение фото
        user_id = self.user_id_input.text().strip()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        photo_filename = f"{user_id}_{timestamp}.jpg"
        photo_save_path = os.path.join(USER_PHOTOS_DIR, photo_filename)
        
        # Копирование фото
        if self.photo_path:
            image = cv2.imread(self.photo_path)
            cv2.imwrite(photo_save_path, image)
        
        # Подготовка данных
        user_data = {
            'user_id': user_id,
            'full_name': self.full_name_input.text().strip(),
            'photo_path': photo_filename,
            'face_encoding': self.face_encoding
        }
        
        # Добавление в базу данных
        result = self.db.add_user(user_data, self.admin_data['id'])
        
        if result:
            # Удаление временного файла если он был создан
            if self.photo_path and 'temp_capture_' in self.photo_path:
                try:
                    os.remove(self.photo_path)
                except:
                    pass
            
            self.accept()
        else:
            QMessageBox.warning(self, "Ошибка", "Пользователь с таким идентификатором уже существует")
    
    def closeEvent(self, event):
        """Обработка закрытия диалога"""
        self.stop_camera()
        
        # Удаление временного файла если он был создан
        if self.photo_path and 'temp_capture_' in self.photo_path:
            try:
                os.remove(self.photo_path)
            except:
                pass
        
        event.accept()
    
    def reject(self):
        """Обработка отмены"""
        self.stop_camera()
        
        # Удаление временного файла если он был создан
        if self.photo_path and 'temp_capture_' in self.photo_path:
            try:
                os.remove(self.photo_path)
            except:
                pass
        
        super().reject()
    
    def keyPressEvent(self, event):
        """Обработка нажатий клавиш"""
        if event.key() == Qt.Key_Escape:
            self.reject()