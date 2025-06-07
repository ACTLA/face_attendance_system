"""
Упрощенный виджет распознавания лиц с надежным управлением камерой
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QFrame, QListWidget, QListWidgetItem,
                           QSizePolicy, QMessageBox)
from PyQt5.QtCore import Qt, QTimer, QDateTime
from PyQt5.QtGui import QFont, QPixmap, QImage
import cv2
import numpy as np
import os
from datetime import datetime

from config import (PRIMARY_COLOR, SECONDARY_COLOR, WARNING_COLOR, 
                   USER_PHOTOS_DIR)
from camera_manager import camera_manager
from face_recognition_engine import FaceRecognitionEngine

class FaceRecognitionWidget(QWidget):
    """Упрощенный виджет распознавания лиц"""
    
    def __init__(self, database, admin_data):
        super().__init__()
        self.db = database
        self.admin_data = admin_data
        
        # Движок распознавания лиц
        self.recognition_engine = FaceRecognitionEngine(database)
        
        # Состояние
        self.is_camera_active = False
        self.current_user_info = None
        
        # Флаг для предотвращения множественных обработок
        self._processing_frame = False
        
        self.init_ui()
        
        # УБИРАЕМ подключение к frame_ready сигналу - он вызывает вылеты
        # Используем только прямые callbacks
        camera_manager.camera_error.connect(self.on_camera_error)
    
    def init_ui(self):
        """Инициализация интерфейса"""
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Основной layout
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        self.setLayout(main_layout)
        
        # Левая панель - камера и управление
        left_panel = self.create_camera_panel()
        main_layout.addWidget(left_panel, 2)
        
        # Правая панель - информация
        right_panel = self.create_info_panel()
        main_layout.addWidget(right_panel, 1)
    
    def create_camera_panel(self):
        """Создание панели камеры"""
        panel = QWidget()
        panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QVBoxLayout()
        panel.setLayout(layout)
        
        # Заголовок
        title = QLabel("Распознавание лиц")
        title.setFont(QFont("Arial", 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Видео область
        self.video_label = QLabel()
        self.video_label.resize(0, 0)
        self.video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("""
            QLabel {
                border: 3px solid #ddd;
                border-radius: 10px;
                background-color: #2c3e50;
                color: #95a5a6;
                font-size: 16px;
            }
        """)
        self.show_camera_placeholder()
        layout.addWidget(self.video_label)
        
        # Статус
        self.status_label = QLabel("КАМЕРА ВЫКЛЮЧЕНА")
        self.status_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.resize(640, 40)
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #6c757d;
                color: white;
                padding: 10px;
                border-radius: 8px;
                margin: 10px 0;
            }
        """)
        layout.addWidget(self.status_label)
        
        # Кнопки управления
        controls_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Запустить")
        self.start_button.setFont(QFont("Arial", 12, QFont.Bold))
        self.start_button.setMinimumHeight(45)
        self.start_button.setCursor(Qt.PointingHandCursor)
        self.start_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {SECONDARY_COLOR};
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 8px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #218838;
            }}
            QPushButton:disabled {{
                background-color: #6c757d;
            }}
        """)
        self.start_button.clicked.connect(self.start_recognition)
        
        self.stop_button = QPushButton("Остановить")
        self.stop_button.setFont(QFont("Arial", 12, QFont.Bold))
        self.stop_button.setMinimumHeight(45)
        self.stop_button.setCursor(Qt.PointingHandCursor)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("""
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
        self.stop_button.clicked.connect(self.stop_recognition)
        
        controls_layout.addWidget(self.start_button)
        controls_layout.addWidget(self.stop_button)
        layout.addLayout(controls_layout)
        
        return panel
    
    def create_info_panel(self):
        """Создание информационной панели"""
        panel = QWidget()
        panel.setFixedWidth(300)
        panel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        layout = QVBoxLayout()
        panel.setLayout(layout)
        
        # Время
        self.time_label = QLabel()
        self.time_label.setFont(QFont("Arial", 16, QFont.Bold))
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setStyleSheet(f"color: {PRIMARY_COLOR}; padding: 10px;")
        layout.addWidget(self.time_label)
        
        # Информация о пользователе
        user_frame = QFrame()
        user_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                padding: 20px;
                border: 1px solid #ddd;
                margin: 10px 0;
            }
        """)
        user_layout = QVBoxLayout()
        user_frame.setLayout(user_layout)
        
        # Фото пользователя
        self.user_photo = QLabel()
        self.user_photo.setFixedSize(200, 200)
        self.user_photo.setAlignment(Qt.AlignCenter)
        self.user_photo.setStyleSheet("""
            QLabel {
                border: 2px solid #ddd;
                border-radius: 50px;
                background-color: #f8f9fa;
                font-size: 40px;
            }
        """)
        self.clear_user_photo()
        user_layout.addWidget(self.user_photo, 0, Qt.AlignCenter)
        
        # Информация о пользователе
        self.user_name = QLabel("---")
        self.user_name.setFont(QFont("Arial", 14, QFont.Bold))
        self.user_name.setAlignment(Qt.AlignCenter)
        self.user_name.setWordWrap(True)
        user_layout.addWidget(self.user_name)
        
        self.user_id = QLabel("---")
        self.user_id.setFont(QFont("Arial", 11))
        self.user_id.setAlignment(Qt.AlignCenter)
        self.user_id.setStyleSheet("color: #666;")
        user_layout.addWidget(self.user_id)
        
        self.confidence_label = QLabel("Уверенность: 0%")
        self.confidence_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.confidence_label.setAlignment(Qt.AlignCenter)
        self.confidence_label.setStyleSheet(f"color: {PRIMARY_COLOR};")
        user_layout.addWidget(self.confidence_label)
        
        layout.addWidget(user_frame)
        
        # Последние распознавания
        logs_label = QLabel("Последние распознавания")
        logs_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(logs_label)
        
        self.logs_list = QListWidget()
        self.logs_list.setStyleSheet("""
            QListWidget {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f0f0f0;
                margin: 2px 0;
            }
            QListWidget::item:hover {
                background-color: #f8f9fa;
            }
        """)
        layout.addWidget(self.logs_list)
        
        # Таймер для обновления времени
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)
        self.update_time()
        
        return panel
    
    def show_camera_placeholder(self):
        """Показать заглушку камеры"""
        try:
            self.video_label.clear()
            self.video_label.setText("📷\n\nКамера выключена\n\nНажмите 'Запустить'\nдля начала распознавания")
        except Exception as e:
            print(f"Ошибка отображения заглушки: {e}")
    
    def start_recognition(self):
        """Запуск распознавания лиц"""
        if self.is_camera_active:
            return
        
        try:
            # Подписка на кадры камеры для распознавания
            camera_manager.subscribe_to_frames(self.process_frame_for_recognition)
            # Подписка на кадры для отображения
            camera_manager.subscribe_to_frames(self.on_frame_ready)
            
            # Запуск камеры
            if camera_manager.start_camera():
                self.is_camera_active = True
                self.start_button.setEnabled(False)
                self.stop_button.setEnabled(True)
                
                self.status_label.setText("ПОИСК ЛИЦ...")
                self.status_label.setStyleSheet(f"""
                    QLabel {{
                        background-color: {WARNING_COLOR};
                        color: white;
                        padding: 10px;
                        border-radius: 8px;
                        margin: 10px 0;
                    }}
                """)
            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось запустить камеру")
        except Exception as e:
            print(f"Ошибка запуска распознавания: {e}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка запуска: {str(e)}")
    
    def stop_recognition(self):
        """Остановка распознавания лиц"""
        if not self.is_camera_active:
            return
        
        try:
            self.is_camera_active = False
            
            # Отписка от кадров
            camera_manager.unsubscribe_from_frames(self.process_frame_for_recognition)
            camera_manager.unsubscribe_from_frames(self.on_frame_ready)
            
            # Остановка камеры
            camera_manager.stop_camera()
            
            # Обновление UI
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            
            self.show_camera_placeholder()
            
            self.status_label.setText("КАМЕРА ВЫКЛЮЧЕНА")
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: #6c757d;
                    color: white;
                    padding: 10px;
                    border-radius: 8px;
                    margin: 10px 0;
                }
            """)
            
            # Очистка информации о пользователе
            self.clear_user_info()
        except Exception as e:
            print(f"Ошибка остановки распознавания: {e}")
    
    def on_frame_ready(self, frame):
        """Обработка нового кадра с камеры"""
        if not self.is_camera_active:
            return
        
        try:
            # Отображение кадра - ПРОСТОЕ без сложных проверок
            self.display_frame_simple(frame)
            
        except Exception as e:
            print(f"Ошибка отображения кадра: {e}")
    
    def display_frame_simple(self, frame):
        """Простое отображение кадра без сложных проверок"""
        try:
            if frame is None or frame.size == 0:
                return
                
            # Простая конвертация
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            height, width, channel = rgb_frame.shape
            bytes_per_line = 3 * width
            
            # Создание изображения
            q_image = QImage(rgb_frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(q_image)
            
            # Масштабирование
            label_size = self.video_label.size()
            if label_size.width() > 0 and label_size.height() > 0:
                scaled_pixmap = pixmap.scaled(label_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.video_label.setPixmap(scaled_pixmap)
            
        except Exception as e:
            # При любой ошибке просто пропускаем кадр
            pass
    
    def process_frame_for_recognition(self, frame):
        """Обработка кадра для распознавания лиц"""
        if not self.is_camera_active or self._processing_frame:
            return
        
        try:
            # Установка флага обработки
            self._processing_frame = True
            
            # Проверка валидности кадра
            if frame is None or frame.size == 0:
                return
            
            # Распознавание лиц
            matches = self.recognition_engine.process_frame(frame)
            
            if matches:
                # Берем первое найденное лицо
                match = matches[0]
                self.on_face_recognized(match)
            else:
                # Сброс статуса если долго нет распознаваний
                if self.current_user_info is None:
                    self.update_status("ПОИСК ЛИЦ...")
                
        except Exception as e:
            print(f"Ошибка распознавания: {e}")
        finally:
            # Сброс флага обработки
            self._processing_frame = False
    
    def on_face_recognized(self, match):
        """Обработка распознанного лица"""
        try:
            # Получение полной информации о пользователе
            user = self.db.get_user_by_id(match.user_id)
            if not user:
                return
            
            # Обновление информации о пользователе
            self.update_user_info(user, match.confidence)
            
            # Добавление записи в базу данных
            try:
                self.db.add_recognition_log(match.user_id, match.confidence, 'SUCCESS')
            except Exception as e:
                print(f"Ошибка записи в БД: {e}")
            
            # Обновление статуса
            self.update_status(f"РАСПОЗНАН ({match.confidence*100:.1f}%)", success=True)
            
            # Добавление в лог
            self.add_to_logs(f"{datetime.now().strftime('%H:%M:%S')} - {user['full_name']} ({match.confidence*100:.1f}%)")
            
            # Сброс статуса через 3 секунды
            QTimer.singleShot(3000, lambda: self.update_status("ПОИСК ЛИЦ..."))
            
        except Exception as e:
            print(f"Ошибка обработки распознанного лица: {e}")
    
    def update_user_info(self, user, confidence):
        """Обновление информации о пользователе"""
        try:
            self.current_user_info = user
            
            # Имя
            self.user_name.setText(user['full_name'])
            
            # ID
            self.user_id.setText(f"ID: {user['user_id']}")
            
            # Уверенность
            self.confidence_label.setText(f"Уверенность: {int(confidence * 100)}%")
            
            # Фото
            self.load_user_photo(user.get('photo_path'))
        except Exception as e:
            print(f"Ошибка обновления информации о пользователе: {e}")
    
    def load_user_photo(self, photo_path):
        """Загрузка фото пользователя"""
        try:
            if photo_path:
                full_path = os.path.join(USER_PHOTOS_DIR, photo_path)
                if os.path.exists(full_path):
                    try:
                        pixmap = QPixmap(full_path)
                        if not pixmap.isNull():
                            scaled_pixmap = pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                            self.user_photo.setPixmap(scaled_pixmap)
                            self.user_photo.setStyleSheet("""
                                QLabel {
                                    border: 2px solid #28a745;
                                    border-radius: 50px;
                                    background-color: white;
                                }
                            """)
                            return
                    except Exception as e:
                        print(f"Ошибка загрузки фото: {e}")
            
            # Фото по умолчанию
            self.set_default_user_photo()
        except Exception as e:
            print(f"Ошибка в load_user_photo: {e}")
            self.set_default_user_photo()
    
    def set_default_user_photo(self):
        """Установка фото по умолчанию"""
        try:
            self.user_photo.clear()
            self.user_photo.setText("👤")
            self.user_photo.setStyleSheet("""
                QLabel {
                    border: 2px solid #28a745;
                    border-radius: 50px;
                    background-color: #f8f9fa;
                    font-size: 40px;
                    color: #28a745;
                }
            """)
        except Exception as e:
            print(f"Ошибка установки фото по умолчанию: {e}")
    
    def clear_user_photo(self):
        """Очистка фото пользователя"""
        try:
            self.user_photo.clear()
            self.user_photo.setText("❓")
            self.user_photo.setStyleSheet("""
                QLabel {
                    border: 2px solid #ddd;
                    border-radius: 50px;
                    background-color: #f8f9fa;
                    font-size: 40px;
                    color: #999;
                }
            """)
        except Exception as e:
            print(f"Ошибка очистки фото: {e}")
    
    def clear_user_info(self):
        """Очистка информации о пользователе"""
        try:
            self.current_user_info = None
            self.user_name.setText("---")
            self.user_id.setText("---")
            self.confidence_label.setText("Уверенность: 0%")
            self.clear_user_photo()
        except Exception as e:
            print(f"Ошибка очистки информации о пользователе: {e}")
    
    def update_status(self, text, success=False):
        """Обновление статуса"""
        try:
            self.status_label.setText(text)
            
            if success:
                color = SECONDARY_COLOR
            elif "ПОИСК" in text:
                color = WARNING_COLOR
            else:
                color = "#6c757d"
            
            self.status_label.setStyleSheet(f"""
                QLabel {{
                    background-color: {color};
                    color: white;
                    padding: 10px;
                    border-radius: 8px;
                    margin: 10px 0;
                }}
            """)
        except Exception as e:
            print(f"Ошибка обновления статуса: {e}")
    
    def add_to_logs(self, log_text):
        """Добавление записи в список логов"""
        try:
            item = QListWidgetItem(log_text)
            item.setFont(QFont("Arial", 9))
            self.logs_list.insertItem(0, item)
            
            # Ограничение количества записей
            while self.logs_list.count() > 10:
                self.logs_list.takeItem(10)
        except Exception as e:
            print(f"Ошибка добавления в лог: {e}")
    
    def update_time(self):
        """Обновление времени"""
        try:
            current_time = QDateTime.currentDateTime()
            self.time_label.setText(current_time.toString("hh:mm:ss\ndd.MM.yyyy"))
        except Exception as e:
            print(f"Ошибка обновления времени: {e}")
    
    def on_camera_error(self, error_message):
        """Обработка ошибки камеры"""
        try:
            print(f"Ошибка камеры: {error_message}")
            self.stop_recognition()
            QMessageBox.critical(self, "Ошибка камеры", error_message)
        except Exception as e:
            print(f"Ошибка обработки ошибки камеры: {e}")
    
    def closeEvent(self, event):
        """Обработка закрытия виджета"""
        try:
            if self.is_camera_active:
                self.stop_recognition()
            event.accept()
        except Exception as e:
            print(f"Ошибка при закрытии виджета: {e}")
            event.accept()