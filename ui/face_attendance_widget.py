"""
Виджет для распознавания лиц и учета посещаемости
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QFrame, QListWidget, QListWidgetItem)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QDateTime
from PyQt5.QtGui import QFont, QPixmap, QImage, QPainter, QBrush, QColor, QRegion

import cv2
import numpy as np
import face_recognition
import pickle
from datetime import datetime, timedelta
import os

from config import (CAMERA_INDEX, FACE_RECOGNITION_TOLERANCE, 
                   ENCODINGS_FILE, EMPLOYEE_PHOTOS_DIR, 
                   MIN_SECONDS_BETWEEN_ATTENDANCE, PRIMARY_COLOR, SECONDARY_COLOR)

class FaceRecognitionThread(QThread):
    """Поток для распознавания лиц"""
    frame_ready = pyqtSignal(np.ndarray)
    face_recognized = pyqtSignal(dict)
    face_unknown = pyqtSignal()
    
    def __init__(self, database):
        super().__init__()
        self.db = database
        self.is_running = False
        self.cap = None
        self.known_face_encodings = []
        self.known_face_ids = []
        self.load_encodings()
    
    def load_encodings(self):
        """Загрузка кодировок лиц"""
        self.known_face_encodings = []
        self.known_face_ids = []
        
        employees = self.db.get_all_employees()
        for emp in employees:
            if emp['face_encoding']:
                self.known_face_encodings.append(np.array(emp['face_encoding']))
                self.known_face_ids.append(emp['id'])
    
    def run(self):
        """Основной цикл распознавания"""
        self.is_running = True
        self.cap = cv2.VideoCapture(CAMERA_INDEX)
        
        frame_count = 0
        
        while self.is_running:
            ret, frame = self.cap.read()
            if not ret:
                continue
            
            # Отправка кадра для отображения
            self.frame_ready.emit(frame)
            
            # Распознавание каждый 10-й кадр для производительности
            frame_count += 1
            if frame_count % 10 != 0:
                continue
            
            # Уменьшение размера для ускорения
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            
            # Поиск лиц
            face_locations = face_recognition.face_locations(rgb_small_frame)
            
            if face_locations:
                face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
                
                for face_encoding in face_encodings:
                    # Сравнение с известными лицами
                    matches = face_recognition.compare_faces(
                        self.known_face_encodings, 
                        face_encoding, 
                        tolerance=FACE_RECOGNITION_TOLERANCE
                    )
                    
                    if True in matches:
                        # Найдено совпадение
                        face_distances = face_recognition.face_distance(
                            self.known_face_encodings, 
                            face_encoding
                        )
                        best_match_index = np.argmin(face_distances)
                        
                        if matches[best_match_index]:
                            employee_id = self.known_face_ids[best_match_index]
                            confidence = 1 - face_distances[best_match_index]
                            
                            employee = self.db.get_employee_by_id(employee_id)
                            if employee:
                                employee['confidence'] = confidence
                                self.face_recognized.emit(employee)
                    else:
                        self.face_unknown.emit()
    
    def stop(self):
        """Остановка потока"""
        self.is_running = False
        if self.cap:
            self.cap.release()
        self.wait()

class FaceAttendanceWidget(QWidget):
    def __init__(self, database, user_data):
        super().__init__()
        self.db = database
        self.user_data = user_data
        self.recognition_thread = None
        self.last_recognized_id = None
        self.last_recognition_time = None
        self.init_ui()
    
    def init_ui(self):
        """Инициализация интерфейса"""
        layout = QHBoxLayout()
        self.setLayout(layout)
        
        # Левая часть - видео и управление
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_panel.setLayout(left_layout)
        
        # Заголовок
        title = QLabel("Face Attendance")
        title.setFont(QFont("Arial", 24, QFont.Bold))
        left_layout.addWidget(title)
        
        # Видео
        self.video_label = QLabel()
        self.video_label.setFixedSize(640, 480)
        self.video_label.setStyleSheet("""
            QLabel {
                background-color: #000;
                border: 2px solid #ddd;
                border-radius: 10px;
            }
        """)
        self.video_label.setAlignment(Qt.AlignCenter)
        
        # Текст по умолчанию
        self.video_label.setText("📷 Camera Off")
        self.video_label.setFont(QFont("Arial", 24))
        self.video_label.setStyleSheet("""
            QLabel {
                background-color: #000;
                color: #666;
                border: 2px solid #ddd;
                border-radius: 10px;
            }
        """)
        
        left_layout.addWidget(self.video_label)
        
        # Статус
        self.status_label = QLabel("UNKNOWN")
        self.status_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #e74c3c;
                color: white;
                padding: 10px;
                border-radius: 8px;
            }
        """)
        left_layout.addWidget(self.status_label)
        
        # Кнопки управления
        controls_layout = QHBoxLayout()
        
        self.start_button = QPushButton("▶️ Start")
        self.start_button.setFont(QFont("Arial", 14, QFont.Bold))
        self.start_button.setCursor(Qt.PointingHandCursor)
        self.start_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {SECONDARY_COLOR};
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 8px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #4cae4c;
            }}
        """)
        self.start_button.clicked.connect(self.start_recognition)
        
        self.stop_button = QPushButton("⏹️ Stop")
        self.stop_button.setFont(QFont("Arial", 14, QFont.Bold))
        self.stop_button.setCursor(Qt.PointingHandCursor)
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        self.stop_button.clicked.connect(self.stop_recognition)
        self.stop_button.setEnabled(False)
        
        controls_layout.addWidget(self.start_button)
        controls_layout.addWidget(self.stop_button)
        left_layout.addLayout(controls_layout)
        
        layout.addWidget(left_panel)
        
        # Правая часть - информация
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_panel.setLayout(right_layout)
        
        # Время
        self.time_label = QLabel()
        self.time_label.setFont(QFont("Arial", 32, QFont.Bold))
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setStyleSheet(f"color: {SECONDARY_COLOR};")
        right_layout.addWidget(self.time_label)
        
        # Информация о сотруднике
        self.employee_info_frame = QFrame()
        self.employee_info_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                padding: 20px;
            }
        """)
        employee_info_layout = QVBoxLayout()
        self.employee_info_frame.setLayout(employee_info_layout)
        
        # Фото сотрудника
        self.employee_photo = QLabel()
        self.employee_photo.setFixedSize(150, 150)
        self.employee_photo.setScaledContents(True)
        self.employee_photo.setAlignment(Qt.AlignCenter)
        self.employee_photo.setStyleSheet("""
            QLabel {
                border: 3px solid #ddd;
                border-radius: 75px;
                background-color: #f0f0f0;
            }
        """)
        employee_info_layout.addWidget(self.employee_photo, 0, Qt.AlignCenter)
        
        # Имя сотрудника
        self.employee_name = QLabel("---")
        self.employee_name.setFont(QFont("Arial", 18, QFont.Bold))
        self.employee_name.setAlignment(Qt.AlignCenter)
        employee_info_layout.addWidget(self.employee_name)
        
        # Должность
        self.employee_designation = QLabel("---")
        self.employee_designation.setFont(QFont("Arial", 14))
        self.employee_designation.setAlignment(Qt.AlignCenter)
        self.employee_designation.setStyleSheet("color: #666;")
        employee_info_layout.addWidget(self.employee_designation)
        
        # ID сотрудника
        self.employee_id = QLabel("---")
        self.employee_id.setFont(QFont("Arial", 12))
        self.employee_id.setAlignment(Qt.AlignCenter)
        self.employee_id.setStyleSheet("color: #999;")
        employee_info_layout.addWidget(self.employee_id)
        
        right_layout.addWidget(self.employee_info_frame)
        
        # Последние отметки
        recent_label = QLabel("Recent Logs")
        recent_label.setFont(QFont("Arial", 16, QFont.Bold))
        right_layout.addWidget(recent_label)
        
        self.recent_logs_list = QListWidget()
        self.recent_logs_list.setStyleSheet("""
            QListWidget {
                background-color: white;
                border: none;
                border-radius: 10px;
                padding: 10px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #eee;
            }
        """)
        right_layout.addWidget(self.recent_logs_list)
        
        layout.addWidget(right_panel)
        
        # Таймер для обновления времени
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)
        self.update_time()
    
    def update_time(self):
        """Обновление времени"""
        current_time = QDateTime.currentDateTime()
        self.time_label.setText(current_time.toString("hh:mm AP"))
    
    def start_recognition(self):
        """Запуск распознавания"""
        self.recognition_thread = FaceRecognitionThread(self.db)
        self.recognition_thread.frame_ready.connect(self.update_video_frame)
        self.recognition_thread.face_recognized.connect(self.on_face_recognized)
        self.recognition_thread.face_unknown.connect(self.on_face_unknown)
        self.recognition_thread.start()
        
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status_label.setText("SCANNING...")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #f39c12;
                color: white;
                padding: 10px;
                border-radius: 8px;
            }
        """)
    
    def stop_recognition(self):
        """Остановка распознавания"""
        if self.recognition_thread:
            self.recognition_thread.stop()
            self.recognition_thread = None
        
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
        self.video_label.setText("📷 Camera Off")
        self.video_label.setFont(QFont("Arial", 24))
        self.video_label.setStyleSheet("""
            QLabel {
                background-color: #000;
                color: #666;
                border: 2px solid #ddd;
                border-radius: 10px;
            }
        """)
        
        self.status_label.setText("STOPPED")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #95a5a6;
                color: white;
                padding: 10px;
                border-radius: 8px;
            }
        """)
    
    def update_video_frame(self, frame):
        """Обновление видео кадра"""
        # Конвертация кадра в QImage
        height, width, channel = frame.shape
        bytes_per_line = 3 * width
        
        # Конвертация BGR в RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Создание QImage
        q_image = QImage(frame_rgb.data, width, height, bytes_per_line, QImage.Format_RGB888)
        
        # Масштабирование для отображения
        pixmap = QPixmap.fromImage(q_image)
        scaled_pixmap = pixmap.scaled(self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        
        self.video_label.setPixmap(scaled_pixmap)
        self.video_label.setStyleSheet("""
            QLabel {
                border: 2px solid #ddd;
                border-radius: 10px;
            }
        """)
    
    def on_face_recognized(self, employee):
        """Обработка распознанного лица"""
        current_time = datetime.now()
        
        # Проверка, не было ли недавно отмечено это лицо
        if (self.last_recognized_id == employee['id'] and 
            self.last_recognition_time and 
            (current_time - self.last_recognition_time).seconds < MIN_SECONDS_BETWEEN_ATTENDANCE):
            return
        
        # Обновление информации о сотруднике
        self.update_employee_info(employee)
        
        # Добавление записи посещаемости
        self.db.add_attendance(employee['id'], 'IN', employee['confidence'])
        
        # Обновление статуса
        self.status_label.setText(f"RECOGNIZED ({employee['confidence']*100:.1f}%)")
        self.status_label.setStyleSheet(f"""
            QLabel {{
                background-color: {SECONDARY_COLOR};
                color: white;
                padding: 10px;
                border-radius: 8px;
            }}
        """)
        
        # Добавление в лог
        log_text = f"{current_time.strftime('%H:%M:%S')} - {employee['full_name']} - IN"
        self.add_to_recent_logs(log_text)
        
        # Сохранение последнего распознавания
        self.last_recognized_id = employee['id']
        self.last_recognition_time = current_time
        
        # Сброс статуса через 3 секунды
        QTimer.singleShot(3000, self.reset_status)
    
    def on_face_unknown(self):
        """Обработка неизвестного лица"""
        self.status_label.setText("UNKNOWN")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #e74c3c;
                color: white;
                padding: 10px;
                border-radius: 8px;
            }
        """)
        
        # Очистка информации о сотруднике
        self.clear_employee_info()
        
        # Сброс статуса через 2 секунды
        QTimer.singleShot(2000, self.reset_status)
    
    def update_employee_info(self, employee):
        """Обновление информации о сотруднике"""
        # Имя
        self.employee_name.setText(employee['full_name'])
        
        # Должность
        self.employee_designation.setText(employee['designation'] or 'N/A')
        
        # ID
        self.employee_id.setText(f"ID: {employee['employee_id']}")
        
        # Фото
        if employee['photo_path']:
            photo_path = os.path.join(EMPLOYEE_PHOTOS_DIR, employee['photo_path'])
            if os.path.exists(photo_path):
                pixmap = QPixmap(photo_path)
                scaled_pixmap = pixmap.scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                
                # Создание круглой маски
                mask = QPixmap(150, 150)
                mask.fill(Qt.transparent)
                
                painter = QPainter(mask)
                painter.setRenderHint(QPainter.Antialiasing)
                painter.setBrush(QBrush(Qt.black))
                painter.drawEllipse(0, 0, 150, 150)
                painter.end()
                
                # Применение маски
                rounded_pixmap = QPixmap(150, 150)
                rounded_pixmap.fill(Qt.transparent)
                
                painter = QPainter(rounded_pixmap)
                painter.setRenderHint(QPainter.Antialiasing)
                painter.setClipRegion(QRegion(mask.createMaskFromColor(Qt.transparent)))
                painter.drawPixmap(0, 0, scaled_pixmap)
                painter.end()
                
                self.employee_photo.setPixmap(rounded_pixmap)
            else:
                self.employee_photo.setText("👤")
                self.employee_photo.setFont(QFont("Arial", 48))
                self.employee_photo.setStyleSheet("""
                    QLabel {
                        border: 3px solid #ddd;
                        border-radius: 75px;
                        background-color: #f0f0f0;
                        color: #999;
                    }
                """)
    
    def clear_employee_info(self):
        """Очистка информации о сотруднике"""
        self.employee_name.setText("---")
        self.employee_designation.setText("---")
        self.employee_id.setText("---")
        self.employee_photo.clear()
        self.employee_photo.setText("👤")
        self.employee_photo.setFont(QFont("Arial", 48))
        self.employee_photo.setStyleSheet("""
            QLabel {
                border: 3px solid #ddd;
                border-radius: 75px;
                background-color: #f0f0f0;
                color: #999;
            }
        """)
    
    def reset_status(self):
        """Сброс статуса"""
        if self.recognition_thread and self.recognition_thread.is_running:
            self.status_label.setText("SCANNING...")
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: #f39c12;
                    color: white;
                    padding: 10px;
                    border-radius: 8px;
                }
            """)
    
    def add_to_recent_logs(self, log_text):
        """Добавление записи в список последних логов"""
        self.recent_logs_list.insertItem(0, log_text)
        
        # Ограничение количества записей
        while self.recent_logs_list.count() > 10:
            self.recent_logs_list.takeItem(10)
    
    def closeEvent(self, event):
        """Обработка закрытия виджета"""
        self.stop_recognition()
        event.accept()