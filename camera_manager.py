"""
Упрощенный менеджер камеры - Singleton с надежным управлением ресурсами
"""
import cv2
import threading
import time
import logging
from typing import Optional, Callable
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal

from config import CAMERA_INDEX, CAMERA_WIDTH, CAMERA_HEIGHT, CAMERA_FPS

logger = logging.getLogger(__name__)

class CameraManager(QObject):
    """
    Singleton менеджер камеры с простой архитектурой
    """
    
    # Сигналы PyQt
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
        
        # Состояние камеры
        self._is_running = False
        self._cap = None
        self._capture_thread = None
        
        # Подписчики на кадры
        self._frame_callbacks = []
        
        # Настройки
        self.camera_index = CAMERA_INDEX
        
        self._initialized = True
        logger.info("CameraManager инициализирован")
    
    def subscribe_to_frames(self, callback: Callable[[np.ndarray], None]):
        """Подписаться на получение кадров"""
        if callback not in self._frame_callbacks:
            self._frame_callbacks.append(callback)
            logger.debug(f"Добавлен подписчик на кадры")
    
    def unsubscribe_from_frames(self, callback: Callable[[np.ndarray], None]):
        """Отписаться от получения кадров"""
        if callback in self._frame_callbacks:
            self._frame_callbacks.remove(callback)
            logger.debug(f"Удален подписчик кадров")
    
    def start_camera(self) -> bool:
        """Запуск камеры"""
        if self._is_running:
            logger.warning("Камера уже запущена")
            return True
        
        try:
            logger.info("Запуск камеры...")
            
            # Попытка открыть камеру с разными backend'ами
            backends = [cv2.CAP_DSHOW, cv2.CAP_ANY]
            
            for backend in backends:
                try:
                    self._cap = cv2.VideoCapture(self.camera_index, backend)
                    if self._cap.isOpened():
                        logger.info(f"Камера открыта с backend: {backend}")
                        break
                    else:
                        if self._cap:
                            self._cap.release()
                        self._cap = None
                except Exception as e:
                    logger.warning(f"Не удалось открыть камеру с backend {backend}: {e}")
                    continue
            
            if not self._cap or not self._cap.isOpened():
                raise RuntimeError("Не удалось открыть камеру")
            
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
            logger.info("Камера успешно запущена")
            return True
            
        except Exception as e:
            error_msg = f"Ошибка запуска камеры: {str(e)}"
            logger.error(error_msg)
            self._cleanup_camera()
            self.camera_error.emit(error_msg)
            return False
    
    def stop_camera(self):
        """Остановка камеры"""
        if not self._is_running:
            logger.info("Камера уже остановлена")
            return
        
        logger.info("Остановка камеры...")
        self._is_running = False
        
        # Ожидание завершения потока
        if self._capture_thread and self._capture_thread.is_alive():
            self._capture_thread.join(timeout=3.0)
            if self._capture_thread.is_alive():
                logger.warning("Поток захвата не завершился в отведенное время")
        
        self._cleanup_camera()
        self.camera_stopped.emit()
        logger.info("Камера остановлена")
    
    def _configure_camera(self):
        """Настройка параметров камеры"""
        if not self._cap:
            return
        
        try:
            # Настройка разрешения
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
            
            # Настройка FPS
            self._cap.set(cv2.CAP_PROP_FPS, CAMERA_FPS)
            
            # Настройка буферизации
            self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Получение реальных параметров
            actual_width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = self._cap.get(cv2.CAP_PROP_FPS)
            
            logger.info(f"Параметры камеры: {actual_width}x{actual_height} @ {actual_fps} FPS")
            
        except Exception as e:
            logger.warning(f"Ошибка настройки камеры: {e}")
    
    def _capture_loop(self):
        """Основной цикл захвата кадров"""
        frame_interval = 1.0 / CAMERA_FPS
        last_frame_time = 0
        
        while self._is_running:
            try:
                current_time = time.time()
                
                # Контроль частоты кадров
                if current_time - last_frame_time < frame_interval:
                    time.sleep(0.001)
                    continue
                
                ret, frame = self._cap.read()
                if not ret or frame is None:
                    if self._is_running:
                        logger.warning("Не удалось получить кадр")
                        time.sleep(0.1)
                    continue
                
                # Отправка кадра подписчикам
                self._distribute_frame(frame.copy())
                
                # Отправка сигнала PyQt
                self.frame_ready.emit(frame.copy())
                
                last_frame_time = current_time
                
            except Exception as e:
                if self._is_running:
                    logger.error(f"Ошибка в цикле захвата: {e}")
                    time.sleep(0.1)
    
    def _distribute_frame(self, frame: np.ndarray):
        """Распространение кадра всем подписчикам"""
        for callback in self._frame_callbacks[:]:  # Копия списка для безопасности
            try:
                callback(frame)
            except Exception as e:
                logger.error(f"Ошибка в callback: {e}")
    
    def _cleanup_camera(self):
        """Очистка ресурсов камеры"""
        if self._cap:
            try:
                self._cap.release()
                logger.debug("Ресурсы камеры освобождены")
            except Exception as e:
                logger.error(f"Ошибка при освобождении камеры: {e}")
            finally:
                self._cap = None
    
    def is_running(self) -> bool:
        """Проверка, работает ли камера"""
        return self._is_running
    
    def get_camera_info(self) -> dict:
        """Получение информации о камере"""
        if not self._cap:
            return {'status': 'not_initialized'}
        
        try:
            return {
                'status': 'running' if self._is_running else 'stopped',
                'width': int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                'height': int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                'fps': self._cap.get(cv2.CAP_PROP_FPS),
                'backend': self._cap.getBackendName() if hasattr(self._cap, 'getBackendName') else 'unknown'
            }
        except:
            return {'status': 'error'}
    
    def __del__(self):
        """Деструктор"""
        try:
            if hasattr(self, '_is_running') and self._is_running:
                self.stop_camera()
        except:
            pass

# Глобальный экземпляр менеджера камеры
camera_manager = CameraManager()