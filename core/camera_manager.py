"""
Централизованный менеджер камеры для автоматизированной системы распознавания лиц
Обеспечивает единую точку доступа к камере и предотвращает конфликты ресурсов
"""
import cv2
import threading
import queue
import time
import logging
from typing import Optional, Callable, Any
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
import numpy as np

from config import CAMERA_INDEX, CAMERA_WIDTH, CAMERA_HEIGHT, FPS

class CameraManager(QObject):
    """
    Singleton класс для управления камерой
    Обеспечивает потокобезопасный доступ к камере
    """
    
    # Сигналы
    frame_ready = pyqtSignal(np.ndarray)
    camera_started = pyqtSignal()
    camera_stopped = pyqtSignal()
    camera_error = pyqtSignal(str)
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Состояние камеры
        self._is_running = False
        self._cap = None
        self._capture_thread = None
        self._frame_queue = queue.Queue(maxsize=2)
        
        # Подписчики на кадры
        self._subscribers = []
        self._subscriber_lock = threading.Lock()
        
        # Настройки
        self.camera_index = CAMERA_INDEX
        self.target_fps = FPS
        self.target_width = CAMERA_WIDTH
        self.target_height = CAMERA_HEIGHT
        
        # Статистика
        self.fps_counter = 0
        self.fps_start_time = time.time()
        self.current_fps = 0
        
        self._initialized = True
        self.logger.info("CameraManager инициализирован")
    
    def subscribe(self, callback: Callable[[np.ndarray], None]):
        """Подписаться на получение кадров"""
        with self._subscriber_lock:
            if callback not in self._subscribers:
                self._subscribers.append(callback)
                self.logger.debug(f"Добавлен подписчик: {callback.__name__}")
    
    def unsubscribe(self, callback: Callable[[np.ndarray], None]):
        """Отписаться от получения кадров"""
        with self._subscriber_lock:
            if callback in self._subscribers:
                self._subscribers.remove(callback)
                self.logger.debug(f"Удален подписчик: {callback.__name__}")
    
    def start_camera(self) -> bool:
        """
        Запуск камеры
        Returns:
            bool: True если камера успешно запущена
        """
        if self._is_running:
            self.logger.warning("Камера уже запущена")
            return True
        
        try:
            self.logger.info("Запуск камеры...")
            
            # Инициализация камеры с разными backend'ами
            backends_to_try = [
                (cv2.CAP_DSHOW, "DirectShow"),
                (cv2.CAP_V4L2, "Video4Linux2"),
                (cv2.CAP_ANY, "Any available")
            ]
            
            for backend, name in backends_to_try:
                try:
                    self._cap = cv2.VideoCapture(self.camera_index, backend)
                    if self._cap.isOpened():
                        self.logger.info(f"Камера открыта с backend: {name}")
                        break
                    else:
                        self._cap.release()
                        self._cap = None
                except Exception as e:
                    self.logger.warning(f"Не удалось открыть камеру с {name}: {e}")
                    continue
            
            if not self._cap or not self._cap.isOpened():
                raise RuntimeError("Не удалось открыть камеру ни с одним backend")
            
            # Настройка параметров камеры
            self._configure_camera()
            
            # Проверка работоспособности
            ret, frame = self._cap.read()
            if not ret or frame is None:
                raise RuntimeError("Не удалось получить кадр с камеры")
            
            # Запуск потока захвата
            self._is_running = True
            self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self._capture_thread.start()
            
            self.camera_started.emit()
            self.logger.info("Камера успешно запущена")
            return True
            
        except Exception as e:
            error_msg = f"Ошибка запуска камеры: {str(e)}"
            self.logger.error(error_msg)
            self._cleanup_camera()
            self.camera_error.emit(error_msg)
            return False
    
    def stop_camera(self):
        """Остановка камеры"""
        if not self._is_running:
            self.logger.info("Камера уже остановлена")
            return
        
        self.logger.info("Остановка камеры...")
        self._is_running = False
        
        # Ожидание завершения потока
        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=3.0)
            if self._capture_thread.is_alive():
                self.logger.warning("Поток захвата не завершился в отведенное время")
        
        self._cleanup_camera()
        self.camera_stopped.emit()
        self.logger.info("Камера остановлена")
    
    def _configure_camera(self):
        """Настройка параметров камеры"""
        if not self._cap:
            return
        
        # Настройка разрешения
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.target_width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.target_height)
        
        # Настройка FPS
        self._cap.set(cv2.CAP_PROP_FPS, self.target_fps)
        
        # Настройка буферизации
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        # Получение реальных параметров
        actual_width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = self._cap.get(cv2.CAP_PROP_FPS)
        
        self.logger.info(f"Параметры камеры: {actual_width}x{actual_height} @ {actual_fps} FPS")
    
    def _capture_loop(self):
        """Основной цикл захвата кадров"""
        frame_interval = 1.0 / self.target_fps
        last_frame_time = 0
        
        while self._is_running:
            try:
                current_time = time.time()
                
                # Контроль частоты кадров
                if current_time - last_frame_time < frame_interval:
                    time.sleep(0.001)  # Короткая пауза
                    continue
                
                ret, frame = self._cap.read()
                if not ret or frame is None:
                    if self._is_running:  # Только если не останавливаемся
                        self.logger.warning("Не удалось получить кадр")
                        time.sleep(0.1)
                    continue
                
                # Обновление статистики FPS
                self._update_fps_stats()
                
                # Отправка кадра подписчикам
                self._distribute_frame(frame.copy())
                
                # Отправка сигнала PyQt
                self.frame_ready.emit(frame.copy())
                
                last_frame_time = current_time
                
            except Exception as e:
                if self._is_running:
                    self.logger.error(f"Ошибка в цикле захвата: {e}")
                    time.sleep(0.1)
    
    def _distribute_frame(self, frame: np.ndarray):
        """Распространение кадра всем подписчикам"""
        with self._subscriber_lock:
            for callback in self._subscribers[:]:  # Копия списка для безопасности
                try:
                    callback(frame)
                except Exception as e:
                    self.logger.error(f"Ошибка в callback {callback.__name__}: {e}")
    
    def _update_fps_stats(self):
        """Обновление статистики FPS"""
        self.fps_counter += 1
        current_time = time.time()
        
        if current_time - self.fps_start_time >= 1.0:
            self.current_fps = self.fps_counter
            self.fps_counter = 0
            self.fps_start_time = current_time
    
    def _cleanup_camera(self):
        """Очистка ресурсов камеры"""
        if self._cap:
            try:
                self._cap.release()
                self.logger.debug("Ресурсы камеры освобождены")
            except Exception as e:
                self.logger.error(f"Ошибка при освобождении камеры: {e}")
            finally:
                self._cap = None
        
        # Очистка очереди кадров
        try:
            while not self._frame_queue.empty():
                self._frame_queue.get_nowait()
        except queue.Empty:
            pass
    
    def get_latest_frame(self) -> Optional[np.ndarray]:
        """
        Получение последнего кадра (неблокирующий)
        Returns:
            Optional[np.ndarray]: Последний кадр или None
        """
        try:
            return self._frame_queue.get_nowait()
        except queue.Empty:
            return None
    
    def is_running(self) -> bool:
        """Проверка, работает ли камера"""
        return self._is_running
    
    def get_camera_info(self) -> dict:
        """Получение информации о камере"""
        if not self._cap:
            return {}
        
        return {
            'width': int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            'height': int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            'fps': self._cap.get(cv2.CAP_PROP_FPS),
            'current_fps': self.current_fps,
            'backend': self._cap.getBackendName(),
            'is_running': self._is_running
        }
    
    def restart_camera(self) -> bool:
        """Перезапуск камеры"""
        self.logger.info("Перезапуск камеры...")
        self.stop_camera()
        time.sleep(1)  # Пауза перед перезапуском
        return self.start_camera()
    
    def __del__(self):
        """Деструктор"""
        if hasattr(self, '_is_running') and self._is_running:
            self.stop_camera()

# Глобальный экземпляр менеджера камеры
camera_manager = CameraManager()