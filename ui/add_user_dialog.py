"""
Упрощенный диалог добавления пользователя
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QLineEdit, QPushButton, QFileDialog, QMessageBox,
                           QFrame, QTabWidget, QWidget)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap
import os
import cv2
import face_recognition
import numpy as np
from datetime import datetime

from config import USER_PHOTOS_DIR, PRIMARY_COLOR, SECONDARY_COLOR
from camera_manager import camera_manager

class CameraThread(QThread):
    """Упрощенный поток для работы с камерой в диалоге"""
    frame_ready = pyqtSignal(np.ndarray)
    face_detected = pyqtSignal(np.ndarray, list)
    
    def __init__(self):
        super().__init__()
        self.is_running = False
        self.cap = None
    
    def run(self):
        """Простой цикл захвата кадров без использования QTimer"""
        self.is_running = True
        
        try:
            # Открытие камеры
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                return
            
            # Настройка камеры
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            while self.is_running:
                try:
                    ret, frame = self.cap.read()
                    if not ret or frame is None:
                        if self.is_running:
                            self.msleep(50)
                            continue
                        else:
                            break
                    
                    if self.is_running:
                        self.frame_ready.emit(frame.copy())
                        
                        # Поиск лиц каждые несколько кадров
                        if hasattr(self, '_frame_count'):
                            self._frame_count += 1
                        else:
                            self._frame_count = 0
                            
                        if self._frame_count % 10 == 0:  # Каждый 10-й кадр
                            try:
                                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                                face_locations = face_recognition.face_locations(rgb_frame)
                                
                                if face_locations and self.is_running:
                                    self.face_detected.emit(frame.copy(), face_locations)
                            except Exception as e:
                                print(f"Ошибка поиска лиц: {e}")
                    
                    # Контроль частоты кадров
                    self.msleep(33)  # ~30 FPS
                    
                except Exception as e:
                    if self.is_running:
                        print(f"Ошибка захвата кадра: {e}")
                        self.msleep(100)
                    else:
                        break
                        
        except Exception as e:
            print(f"Ошибка инициализации камеры: {e}")
        finally:
            if self.cap:
                try:
                    self.cap.release()
                except:
                    pass
                self.cap = None
    
    def stop(self):
        """Остановка потока"""
        self.is_running = False
        
        if self.cap:
            try:
                self.cap.release()
            except:
                pass
            self.cap = None
        
        # Ожидание завершения с таймаутом
        if not self.wait(2000):
            self.terminate()
            self.wait(1000)

class AddUserDialog(QDialog):
    """Упрощенный диалог добавления пользователя"""
    
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
        """Инициализация интерфейса"""
        self.setWindowTitle("Добавить пользователя")
        self.setModal(True)
        self.resize(700, 500)
        
        # Основной layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)