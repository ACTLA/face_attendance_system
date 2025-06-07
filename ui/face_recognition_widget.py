"""
Виджет для распознавания лиц в реальном времени
Основан на оригинальном алгоритме с исправлениями
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QFrame, QListWidget, QListWidgetItem,
                           QSizePolicy, QProgressBar)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QDateTime
from PyQt5.QtGui import QFont, QPixmap, QImage, QPainter, QBrush, QColor, QRegion

import cv2
import numpy as np
import face_recognition
from datetime import datetime, timedelta
import os

from config import (CAMERA_INDEX, FACE_RECOGNITION_TOLERANCE, 
                   USER_PHOTOS_DIR, MIN_SECONDS_BETWEEN_RECOGNITION,
                   PRIMARY_COLOR, SECONDARY_COLOR, WARNING_COLOR,
                   VIDEO_WIDGET_MIN_WIDTH, VIDEO_WIDGET_MIN_HEIGHT,
                   RESIZE_SCALE)

class FaceRecognitionThread(QThread):
    """Поток для распознавания лиц - оригинальный алгоритм"""
    frame_ready = pyqtSignal(np.ndarray)
    face_recognized = pyqtSignal(dict)
    face_unknown = pyqtSignal()
    camera_error = pyqtSignal(str)
    
    def __init__(self, database):
        super().__init__()
        self.db = database
        self.is_running = False
        self.cap = None
        self.known_face_encodings = []
        self.known_face_ids = []
        self.load_encodings()
    
    def load_encodings(self):
        """Загрузка кодировок лиц из базы данных"""
        self.known_face_encodings = []
        self.known_face_ids = []
        
        users = self.db.get_all_users()
        for user in users:
            if user['face_encoding']:
                try:
                    encoding = np.array(user['face_encoding'])
                    self.known_face_encodings.append(encoding)
                    self.known_face_ids.append(user['id'])
                except Exception as e:
                    print(f"Ошибка загрузки кодировки для пользователя {user['user_id']}: {e}")
    
    def run(self):
        """Основной цикл распознавания с улучшенной обработкой ошибок"""
        self.is_running = True
        
        try:
            # Принудительное использование DirectShow вместо MSMF
            self.cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
            
            if not self.cap.isOpened():
                # Попробуем без DirectShow
                self.cap = cv2.VideoCapture(CAMERA_INDEX)
                
            if not self.cap.isOpened():
                self.camera_error.emit("Не удалось подключиться к камере")
                return
            
            # Настройка буферизации
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
        except Exception as e:
            self.camera_error.emit(f"Ошибка инициализации камеры: {str(e)}")
            return
        
        frame_count = 0
        
        while self.is_running:
            try:
                ret, frame = self.cap.read()
                if not ret:
                    if self.is_running:  # Проверяем, что не остановлены
                        continue
                    else:
                        break
                
                # Отправка кадра для отображения
                if self.is_running:
                    self.frame_ready.emit(frame)
                
                # Распознавание каждый 10-й кадр для производительности
                frame_count += 1
                if frame_count % 10 != 0:
                    continue
                
                if not self.is_running:  # Дополнительная проверка
                    break
                
                # Уменьшение размера для ускорения
                small_frame = cv2.resize(frame, (0, 0), fx=RESIZE_SCALE, fy=RESIZE_SCALE)
                rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
                
                # Поиск лиц
                face_locations = face_recognition.face_locations(rgb_small_frame)
                
                if face_locations and self.is_running:
                    face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
                    
                    for face_encoding in face_encodings:
                        if not self.is_running:
                            break
                            
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
                                user_id = self.known_face_ids[best_match_index]
                                confidence = 1 - face_distances[best_match_index]
                                
                                user = self.db.get_user_by_id(user_id)
                                if user and self.is_running:
                                    user['confidence'] = confidence
                                    self.face_recognized.emit(user)
                        else:
                            if self.is_running:
                                self.face_unknown.emit()
                                
            except Exception as e:
                if self.is_running:
                    print(f"Ошибка в цикле распознавания: {e}")
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
        
        print("Цикл распознавания завершен")
    
    def stop(self):
        """Безопасная остановка потока"""
        print("Останавливаем поток распознавания...")
        self.is_running = False
        
        # Принудительное освобождение камеры
        if self.cap:
            try:
                self.cap.release()
                print("Камера освобождена")
            except Exception as e:
                print(f"Ошибка при освобождении камеры: {e}")
            self.cap = None
        
        # Ожидание завершения потока с таймаутом
        if not self.wait(3000):  # 3 секунды таймаут
            print("Принудительное завершение потока...")
            self.terminate()
            self.wait(1000)  # Еще 1 секунда на завершение
        
        print("Поток остановлен")

class FaceRecognitionWidget(QWidget):
    def __init__(self, database, admin_data):
        super().__init__()
        self.db = database
        self.admin_data = admin_data
        self.recognition_thread = None
        self.last_recognized_id = None
        self.last_recognition_time = None
        self.is_camera_active = False  # Важно: камера выключена по умолчанию
        
        print("Инициализация виджета распознавания лиц...")
        self.init_ui()
        print("Виджет распознавания лиц готов")
    
    def init_ui(self):
        """Инициализация адаптивного интерфейса"""
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Адаптивные размеры
        from PyQt5.QtWidgets import QDesktopWidget
        desktop = QDesktopWidget()
        screen_rect = desktop.screenGeometry()
        
        if screen_rect.width() >= 1920:
            right_panel_width = 320
            photo_size = 120
        elif screen_rect.width() >= 1366:
            right_panel_width = 280
            photo_size = 100
        else:
            right_panel_width = 250
            photo_size = 80
        
        # Сохраняем размеры для адаптивности
        self.right_panel_width = right_panel_width
        self.photo_size = photo_size
        
        layout = QHBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        self.setLayout(layout)
        
        # Левая часть - видео и управление
        left_panel = QWidget()
        left_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left_layout = QVBoxLayout()
        left_panel.setLayout(left_layout)
        
        # Заголовок
        title = QLabel("Распознавание лиц")
        title.setFont(QFont("Arial", 24, QFont.Bold))
        title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        left_layout.addWidget(title)
        
        # Видео
        self.video_label = QLabel()
        self.video_label.setMinimumSize(VIDEO_WIDGET_MIN_WIDTH, VIDEO_WIDGET_MIN_HEIGHT)
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_label.setScaledContents(False)
        self.video_label.setAlignment(Qt.AlignCenter)
        
        # Показать заглушку по умолчанию
        self.show_camera_placeholder()
        
        left_layout.addWidget(self.video_label)
        
        # Статус
        self.status_label = QLabel("КАМЕРА ВЫКЛЮЧЕНА")
        self.status_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setMinimumHeight(50)
        self.status_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #95a5a6;
                color: white;
                padding: 12px;
                border-radius: 8px;
            }
        """)
        left_layout.addWidget(self.status_label)
        
        # Кнопки управления
        controls_layout = QHBoxLayout()
        
        self.start_button = QPushButton("▶️ Запустить камеру")
        self.start_button.setFont(QFont("Arial", 14, QFont.Bold))
        self.start_button.setCursor(Qt.PointingHandCursor)
        self.start_button.setMinimumHeight(50)
        self.start_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
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
        
        self.stop_button = QPushButton("⏹️ Остановить камеру")
        self.stop_button.setFont(QFont("Arial", 14, QFont.Bold))
        self.stop_button.setCursor(Qt.PointingHandCursor)
        self.stop_button.setMinimumHeight(50)
        self.stop_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
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
            QPushButton:disabled {
                background-color: #95a5a6;
            }
        """)
        self.stop_button.clicked.connect(self.stop_camera)
        self.stop_button.setEnabled(False)
        
        controls_layout.addWidget(self.start_button)
        controls_layout.addWidget(self.stop_button)
        left_layout.addLayout(controls_layout)
        
        layout.addWidget(left_panel, 2)
        
        # Правая часть - информация
        right_panel = QWidget()
        right_panel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        right_panel.setFixedWidth(self.right_panel_width)
        right_layout = QVBoxLayout()
        right_panel.setLayout(right_layout)
        
        # Время
        self.time_label = QLabel()
        self.time_label.setFont(QFont("Arial", 20, QFont.Bold))
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.time_label.setStyleSheet(f"color: {SECONDARY_COLOR}; padding: 10px;")
        right_layout.addWidget(self.time_label)
        
        # Информация о пользователе
        self.user_info_frame = QFrame()
        self.user_info_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.user_info_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                padding: 20px;
                border: 2px solid #e9ecef;
            }
        """)
        user_info_layout = QVBoxLayout()
        self.user_info_frame.setLayout(user_info_layout)
        
        # Фото пользователя
        self.user_photo = QLabel()
        self.user_photo.setFixedSize(self.photo_size, self.photo_size)
        self.user_photo.setScaledContents(True)
        self.user_photo.setAlignment(Qt.AlignCenter)
        border_radius = self.photo_size // 2
        self.user_photo.setStyleSheet(f"""
            QLabel {{
                border: 3px solid #ddd;
                border-radius: {border_radius}px;
                background-color: #f8f9fa;
            }}
        """)
        self.clear_user_photo()
        user_info_layout.addWidget(self.user_photo, 0, Qt.AlignCenter)
        
        # Имя пользователя
        self.user_name = QLabel("---")
        self.user_name.setFont(QFont("Arial", 16, QFont.Bold))
        self.user_name.setAlignment(Qt.AlignCenter)
        self.user_name.setWordWrap(True)
        user_info_layout.addWidget(self.user_name)
        
        # ID пользователя
        self.user_id = QLabel("---")
        self.user_id.setFont(QFont("Arial", 12))
        self.user_id.setAlignment(Qt.AlignCenter)
        self.user_id.setStyleSheet("color: #666;")
        user_info_layout.addWidget(self.user_id)
        
        # Уверенность
        self.confidence_label = QLabel("Уверенность: 0%")
        self.confidence_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.confidence_label.setAlignment(Qt.AlignCenter)
        self.confidence_label.setStyleSheet(f"color: {PRIMARY_COLOR};")
        user_info_layout.addWidget(self.confidence_label)
        
        right_layout.addWidget(self.user_info_frame)
        
        # Последние распознавания
        recent_label = QLabel("Последние распознавания")
        recent_label.setFont(QFont("Arial", 14, QFont.Bold))
        recent_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        right_layout.addWidget(recent_label)
        
        self.recent_logs_list = QListWidget()
        self.recent_logs_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.recent_logs_list.setStyleSheet("""
            QListWidget {
                background-color: white;
                border: 2px solid #e9ecef;
                border-radius: 10px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f0f0f0;
                border-radius: 5px;
                margin: 2px;
            }
            QListWidget::item:hover {
                background-color: #f8f9fa;
            }
        """)
        right_layout.addWidget(self.recent_logs_list)
        
        layout.addWidget(right_panel, 1)
        
        # Таймер для обновления времени
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)
        self.update_time()
    
    def show_camera_placeholder(self):
        """Показать заглушку камеры"""
        self.video_label.clear()
        self.video_label.setText("📷\n\nКамера выключена\n\nНажмите 'Запустить камеру'\nдля начала распознавания")
        self.video_label.setFont(QFont("Arial", 16))
        self.video_label.setStyleSheet("""
            QLabel {
                background-color: #2c3e50;
                color: #95a5a6;
                border: 3px solid #34495e;
                border-radius: 15px;
                padding: 20px;
            }
        """)
    
    def start_recognition(self):
        """Запуск распознавания"""
        if self.recognition_thread and self.recognition_thread.isRunning():
            return
        
        self.recognition_thread = FaceRecognitionThread(self.db)
        self.recognition_thread.frame_ready.connect(self.update_video_frame)
        self.recognition_thread.face_recognized.connect(self.on_face_recognized)
        self.recognition_thread.face_unknown.connect(self.on_face_unknown)
        self.recognition_thread.camera_error.connect(self.on_camera_error)
        self.recognition_thread.start()
        
        self.is_camera_active = True
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        
        self.status_label.setText("СКАНИРОВАНИЕ...")
        self.status_label.setStyleSheet(f"""
            QLabel {{
                background-color: {WARNING_COLOR};
                color: white;
                padding: 12px;
                border-radius: 8px;
            }}
        """)
    
    def stop_camera(self):
        """Остановка камеры без зависания"""
        # Проверяем, что камера действительно активна
        if not self.is_camera_active:
            return
            
        print("Начинаем остановку камеры...")
        
        # Отключаем кнопки сразу
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.is_camera_active = False
        
        # Показать заглушку сразу
        self.show_camera_placeholder()
        
        self.status_label.setText("ОСТАНОВКА КАМЕРЫ...")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #f39c12;
                color: white;
                padding: 12px;
                border-radius: 8px;
            }
        """)
        
        # Принудительная обработка событий
        from PyQt5.QtWidgets import QApplication
        QApplication.processEvents()
        
        if self.recognition_thread:
            print("Останавливаем поток...")
            # Безопасная остановка потока в отдельном таймере
            QTimer.singleShot(100, self._stop_thread_delayed)
        else:
            self._finalize_camera_stop()
    
    def _stop_thread_delayed(self):
        """Отложенная остановка потока"""
        if self.recognition_thread:
            self.recognition_thread.stop()
            self.recognition_thread = None
            print("Поток остановлен")
        
        self._finalize_camera_stop()
    
    def _finalize_camera_stop(self):
        """Финализация остановки камеры"""
        self.status_label.setText("КАМЕРА ВЫКЛЮЧЕНА")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #95a5a6;
                color: white;
                padding: 12px;
                border-radius: 8px;
            }
        """)
        
        # Очистка информации о пользователе
        self.clear_user_info()
        print("Камера полностью остановлена")
    
    def update_video_frame(self, frame):
        """Обновление видео кадра"""
        if not self.is_camera_active:
            return
        
        # Конвертация кадра в QImage
        height, width, channel = frame.shape
        bytes_per_line = 3 * width
        
        # Конвертация BGR в RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Создание QImage
        q_image = QImage(frame_rgb.data, width, height, bytes_per_line, QImage.Format_RGB888)
        
        # Масштабирование для отображения с сохранением пропорций
        pixmap = QPixmap.fromImage(q_image)
        scaled_pixmap = pixmap.scaled(
            self.video_label.size(), 
            Qt.KeepAspectRatio, 
            Qt.SmoothTransformation
        )
        
        self.video_label.setPixmap(scaled_pixmap)
        self.video_label.setStyleSheet("""
            QLabel {
                border: 3px solid #28a745;
                border-radius: 15px;
                background-color: #000;
            }
        """)
    
    def on_face_recognized(self, user):
        """Обработка распознанного лица - оригинальная логика"""
        current_time = datetime.now()
        
        # Проверка, не было ли недавно отмечено это лицо
        if (self.last_recognized_id == user['id'] and 
            self.last_recognition_time and 
            (current_time - self.last_recognition_time).seconds < MIN_SECONDS_BETWEEN_RECOGNITION):
            return
        
        # Обновление информации о пользователе
        self.update_user_info(user)
        
        # Добавление записи в базу данных
        self.db.add_recognition_log(user['id'], user['confidence'], 'SUCCESS')
        
        # Обновление статуса
        self.status_label.setText(f"РАСПОЗНАН ({user['confidence']*100:.1f}%)")
        self.status_label.setStyleSheet(f"""
            QLabel {{
                background-color: {SECONDARY_COLOR};
                color: white;
                padding: 12px;
                border-radius: 8px;
            }}
        """)
        
        # Добавление в лог
        log_text = f"{current_time.strftime('%H:%M:%S')} - {user['full_name']} - {user['confidence']*100:.1f}%"
        self.add_to_recent_logs(log_text)
        
        # Сохранение последнего распознавания
        self.last_recognized_id = user['id']
        self.last_recognition_time = current_time
        
        # Сброс статуса через 3 секунды
        QTimer.singleShot(3000, self.reset_status)
    
    def on_face_unknown(self):
        """Обработка неизвестного лица"""
        self.status_label.setText("НЕИЗВЕСТНОЕ ЛИЦО")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #e74c3c;
                color: white;
                padding: 12px;
                border-radius: 8px;
            }
        """)
        
        # Очистка информации о пользователе
        self.clear_user_info()
        
        # Сброс статуса через 2 секунды
        QTimer.singleShot(2000, self.reset_status)
    
    def on_camera_error(self, error_message):
        """Обработка ошибки камеры"""
        self.stop_camera()
        self.status_label.setText(f"ОШИБКА КАМЕРЫ")
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #e74c3c;
                color: white;
                padding: 12px;
                border-radius: 8px;
            }
        """)
        
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.critical(self, "Ошибка камеры", error_message)
    
    def update_user_info(self, user):
        """Обновление информации о пользователе"""
        # Имя
        self.user_name.setText(user['full_name'])
        
        # ID
        self.user_id.setText(f"ID: {user['user_id']}")
        
        # Уверенность
        confidence_percent = int(user['confidence'] * 100)
        self.confidence_label.setText(f"Уверенность: {confidence_percent}%")
        
        # Фото
        if user['photo_path']:
            photo_path = os.path.join(USER_PHOTOS_DIR, user['photo_path'])
            if os.path.exists(photo_path):
                self.load_user_photo(photo_path)
            else:
                self.set_default_user_photo()
        else:
            self.set_default_user_photo()
    
    def load_user_photo(self, photo_path):
        """Загрузка фото пользователя"""
        from PyQt5.QtGui import QPainterPath
        
        pixmap = QPixmap(photo_path)
        if not pixmap.isNull():
            # Создание круглой маски
            size = self.photo_size
            scaled_pixmap = pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            # Создание круглого изображения
            rounded_pixmap = QPixmap(size, size)
            rounded_pixmap.fill(Qt.transparent)
            
            painter = QPainter(rounded_pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Создание круглой маски
            path = QPainterPath()
            path.addEllipse(0, 0, size, size)
            painter.setClipPath(path)
            
            # Центрирование изображения
            x = (size - scaled_pixmap.width()) // 2
            y = (size - scaled_pixmap.height()) // 2
            painter.drawPixmap(x, y, scaled_pixmap)
            painter.end()
            
            self.user_photo.setPixmap(rounded_pixmap)
            border_radius = size // 2
            self.user_photo.setStyleSheet(f"""
                QLabel {{
                    border: 3px solid #28a745;
                    border-radius: {border_radius}px;
                    background-color: transparent;
                }}
            """)
        else:
            self.set_default_user_photo()
    
    def set_default_user_photo(self):
        """Установка фото по умолчанию"""
        self.user_photo.clear()
        self.user_photo.setText("👤")
        font_size = max(20, self.photo_size // 3)
        border_radius = self.photo_size // 2
        self.user_photo.setFont(QFont("Arial", font_size))
        self.user_photo.setStyleSheet(f"""
            QLabel {{
                border: 3px solid #ddd;
                border-radius: {border_radius}px;
                background-color: #f8f9fa;
                color: #999;
            }}
        """)
    
    def clear_user_photo(self):
        """Очистка фото пользователя"""
        self.user_photo.clear()
        self.user_photo.setText("❓")
        font_size = max(20, self.photo_size // 3)
        border_radius = self.photo_size // 2
        self.user_photo.setFont(QFont("Arial", font_size))
        self.user_photo.setStyleSheet(f"""
            QLabel {{
                border: 3px solid #ddd;
                border-radius: {border_radius}px;
                background-color: #f8f9fa;
                color: #999;
            }}
        """)
    
    def clear_user_info(self):
        """Очистка информации о пользователе"""
        self.user_name.setText("---")
        self.user_id.setText("---")
        self.confidence_label.setText("Уверенность: 0%")
        self.clear_user_photo()
    
    def reset_status(self):
        """Сброс статуса"""
        if self.recognition_thread and self.recognition_thread.is_running:
            self.status_label.setText("СКАНИРОВАНИЕ...")
            self.status_label.setStyleSheet(f"""
                QLabel {{
                    background-color: {WARNING_COLOR};
                    color: white;
                    padding: 12px;
                    border-radius: 8px;
                }}
            """)
    
    def add_to_recent_logs(self, log_text):
        """Добавление записи в список последних логов"""
        item = QListWidgetItem(log_text)
        item.setFont(QFont("Arial", 10))
        self.recent_logs_list.insertItem(0, item)
        
        # Ограничение количества записей
        while self.recent_logs_list.count() > 15:
            self.recent_logs_list.takeItem(15)
    
    def update_time(self):
        """Обновление времени"""
        current_time = QDateTime.currentDateTime()
        self.time_label.setText(current_time.toString("hh:mm:ss\ndd.MM.yyyy"))
    
    def showEvent(self, event):
        """Обработка показа виджета"""
        super().showEvent(event)
    
    def hideEvent(self, event):
        """Обработка скрытия виджета"""
        # Останавливаем камеру только если виджет действительно скрывается надолго
        # А не при обычных операциях UI
        super().hideEvent(event)
    
    def closeEvent(self, event):
        """Обработка закрытия виджета"""
        self.stop_camera()
        event.accept()