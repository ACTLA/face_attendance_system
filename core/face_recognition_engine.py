"""
Оптимизированный движок распознавания лиц
Обеспечивает высокую производительность и точность распознавания
"""
import cv2
import face_recognition
import numpy as np
import threading
import queue
import time
import logging
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import pickle
import os

from config import (FACE_RECOGNITION_TOLERANCE, RESIZE_SCALE, 
                   MIN_SECONDS_BETWEEN_RECOGNITION, ENCODINGS_FILE)

@dataclass
class FaceMatch:
    """Класс для хранения результата распознавания лица"""
    user_id: int
    user_code: str
    full_name: str
    confidence: float
    face_location: Tuple[int, int, int, int]
    timestamp: float

@dataclass
class FaceDetection:
    """Класс для хранения обнаруженного лица"""
    location: Tuple[int, int, int, int]
    encoding: np.ndarray
    timestamp: float

class FaceRecognitionEngine:
    """
    Высокопроизводительный движок распознавания лиц
    """
    
    def __init__(self, database):
        self.logger = logging.getLogger(__name__)
        self.db = database
        
        # Кэш известных лиц
        self.known_encodings = []
        self.known_users = []
        self.encodings_cache = {}
        
        # Настройки производительности
        self.max_workers = 2  # Количество потоков для обработки
        self.frame_skip = 3   # Обрабатывать каждый N-й кадр
        self.frame_counter = 0
        
        # Кэш последних распознаваний
        self.last_recognitions = {}
        self.recognition_cooldown = MIN_SECONDS_BETWEEN_RECOGNITION
        
        # Очереди для обработки
        self.frame_queue = queue.Queue(maxsize=5)
        self.result_queue = queue.Queue()
        
        # Потоки обработки
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        self.is_processing = False
        
        # Статистика
        self.stats = {
            'frames_processed': 0,
            'faces_detected': 0,
            'faces_recognized': 0,
            'processing_time_avg': 0.0
        }
        
        self.load_known_faces()
        self.logger.info("FaceRecognitionEngine инициализирован")
    
    def load_known_faces(self):
        """Загрузка известных лиц из базы данных с кэшированием"""
        try:
            # Попытка загрузки из кэша
            if os.path.exists(ENCODINGS_FILE):
                cache_time = os.path.getmtime(ENCODINGS_FILE)
                if time.time() - cache_time < 3600:  # Кэш действителен 1 час
                    self._load_from_cache()
                    return
            
            # Загрузка из базы данных
            self._load_from_database()
            self._save_to_cache()
            
        except Exception as e:
            self.logger.error(f"Ошибка загрузки известных лиц: {e}")
            self.known_encodings = []
            self.known_users = []
    
    def _load_from_database(self):
        """Загрузка лиц из базы данных"""
        self.logger.info("Загрузка лиц из базы данных...")
        users = self.db.get_all_users()
        
        self.known_encodings = []
        self.known_users = []
        
        for user in users:
            if user['face_encoding']:
                try:
                    encoding = np.array(user['face_encoding'])
                    if encoding.shape == (128,):  # Проверка размерности
                        self.known_encodings.append(encoding)
                        self.known_users.append({
                            'id': user['id'],
                            'user_id': user['user_id'],
                            'full_name': user['full_name'],
                            'photo_path': user['photo_path']
                        })
                except Exception as e:
                    self.logger.warning(f"Пропуск пользователя {user['user_id']}: {e}")
        
        self.logger.info(f"Загружено {len(self.known_encodings)} лиц")
    
    def _load_from_cache(self):
        """Загрузка из кэша"""
        try:
            with open(ENCODINGS_FILE, 'rb') as f:
                data = pickle.load(f)
                self.known_encodings = data['encodings']
                self.known_users = data['users']
            self.logger.info(f"Загружено {len(self.known_encodings)} лиц из кэша")
        except Exception as e:
            self.logger.error(f"Ошибка загрузки кэша: {e}")
            self._load_from_database()
    
    def _save_to_cache(self):
        """Сохранение в кэш"""
        try:
            os.makedirs(os.path.dirname(ENCODINGS_FILE), exist_ok=True)
            with open(ENCODINGS_FILE, 'wb') as f:
                pickle.dump({
                    'encodings': self.known_encodings,
                    'users': self.known_users,
                    'timestamp': time.time()
                }, f)
            self.logger.debug("Кэш лиц сохранен")
        except Exception as e:
            self.logger.error(f"Ошибка сохранения кэша: {e}")
    
    def reload_faces(self):
        """Принудительная перезагрузка лиц"""
        self.logger.info("Принудительная перезагрузка лиц...")
        self._load_from_database()
        self._save_to_cache()
        self.last_recognitions.clear()
    
    def start_processing(self):
        """Запуск обработки кадров"""
        if self.is_processing:
            return
        
        self.is_processing = True
        self.logger.info("Запуск обработки распознавания лиц")
    
    def stop_processing(self):
        """Остановка обработки кадров"""
        if not self.is_processing:
            return
        
        self.is_processing = False
        
        # Очистка очередей
        self._clear_queues()
        
        self.logger.info("Остановка обработки распознавания лиц")
    
    def process_frame(self, frame: np.ndarray) -> List[FaceMatch]:
        """
        Обработка кадра для поиска лиц
        
        Args:
            frame: Кадр для обработки
            
        Returns:
            List[FaceMatch]: Список найденных совпадений
        """
        if not self.is_processing:
            return []
        
        start_time = time.time()
        
        # Пропуск кадров для производительности
        self.frame_counter += 1
        if self.frame_counter % self.frame_skip != 0:
            return []
        
        try:
            # Детекция лиц
            detections = self._detect_faces(frame)
            if not detections:
                return []
            
            # Распознавание лиц
            matches = []
            for detection in detections:
                match = self._recognize_face(detection)
                if match and self._should_process_recognition(match):
                    matches.append(match)
                    self._update_last_recognition(match)
            
            # Обновление статистики
            processing_time = time.time() - start_time
            self._update_stats(processing_time, len(detections), len(matches))
            
            return matches
            
        except Exception as e:
            self.logger.error(f"Ошибка обработки кадра: {e}")
            return []
    
    def _detect_faces(self, frame: np.ndarray) -> List[FaceDetection]:
        """Детекция лиц на кадре"""
        try:
            # Уменьшение кадра для ускорения
            small_frame = cv2.resize(frame, (0, 0), fx=RESIZE_SCALE, fy=RESIZE_SCALE)
            rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            
            # Поиск лиц
            face_locations = face_recognition.face_locations(rgb_frame, model='hog')
            
            if not face_locations:
                return []
            
            # Создание кодировок
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            
            detections = []
            for location, encoding in zip(face_locations, face_encodings):
                # Масштабирование координат обратно
                top, right, bottom, left = location
                scaled_location = (
                    int(top / RESIZE_SCALE),
                    int(right / RESIZE_SCALE),
                    int(bottom / RESIZE_SCALE),
                    int(left / RESIZE_SCALE)
                )
                
                detections.append(FaceDetection(
                    location=scaled_location,
                    encoding=encoding,
                    timestamp=time.time()
                ))
            
            return detections
            
        except Exception as e:
            self.logger.error(f"Ошибка детекции лиц: {e}")
            return []
    
    def _recognize_face(self, detection: FaceDetection) -> Optional[FaceMatch]:
        """Распознавание конкретного лица"""
        if not self.known_encodings:
            return None
        
        try:
            # Сравнение с известными лицами
            distances = face_recognition.face_distance(
                self.known_encodings, 
                detection.encoding
            )
            
            # Поиск лучшего совпадения
            min_distance_idx = np.argmin(distances)
            min_distance = distances[min_distance_idx]
            
            if min_distance <= FACE_RECOGNITION_TOLERANCE:
                user = self.known_users[min_distance_idx]
                confidence = 1.0 - min_distance
                
                return FaceMatch(
                    user_id=user['id'],
                    user_code=user['user_id'],
                    full_name=user['full_name'],
                    confidence=confidence,
                    face_location=detection.location,
                    timestamp=detection.timestamp
                )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Ошибка распознавания лица: {e}")
            return None
    
    def _should_process_recognition(self, match: FaceMatch) -> bool:
        """Проверка, нужно ли обрабатывать это распознавание"""
        user_id = match.user_id
        current_time = match.timestamp
        
        if user_id in self.last_recognitions:
            last_time = self.last_recognitions[user_id]
            if current_time - last_time < self.recognition_cooldown:
                return False
        
        return True
    
    def _update_last_recognition(self, match: FaceMatch):
        """Обновление времени последнего распознавания"""
        self.last_recognitions[match.user_id] = match.timestamp
        
        # Очистка старых записей
        current_time = time.time()
        to_remove = []
        for user_id, last_time in self.last_recognitions.items():
            if current_time - last_time > self.recognition_cooldown * 2:
                to_remove.append(user_id)
        
        for user_id in to_remove:
            del self.last_recognitions[user_id]
    
    def _update_stats(self, processing_time: float, faces_detected: int, faces_recognized: int):
        """Обновление статистики"""
        self.stats['frames_processed'] += 1
        self.stats['faces_detected'] += faces_detected
        self.stats['faces_recognized'] += faces_recognized
        
        # Скользящее среднее времени обработки
        alpha = 0.1
        self.stats['processing_time_avg'] = (
            alpha * processing_time + 
            (1 - alpha) * self.stats['processing_time_avg']
        )
    
    def _clear_queues(self):
        """Очистка очередей"""
        try:
            while not self.frame_queue.empty():
                self.frame_queue.get_nowait()
        except queue.Empty:
            pass
        
        try:
            while not self.result_queue.empty():
                self.result_queue.get_nowait()
        except queue.Empty:
            pass
    
    def get_stats(self) -> dict:
        """Получение статистики работы"""
        return self.stats.copy()
    
    def add_new_face(self, user_data: dict):
        """Добавление нового лица в базу"""
        try:
            if user_data['face_encoding']:
                encoding = np.array(user_data['face_encoding'])
                if encoding.shape == (128,):
                    self.known_encodings.append(encoding)
                    self.known_users.append({
                        'id': user_data['id'],
                        'user_id': user_data['user_id'],
                        'full_name': user_data['full_name'],
                        'photo_path': user_data.get('photo_path', '')
                    })
                    self._save_to_cache()
                    self.logger.info(f"Добавлено новое лицо: {user_data['full_name']}")
        except Exception as e:
            self.logger.error(f"Ошибка добавления лица: {e}")
    
    def remove_face(self, user_id: int):
        """Удаление лица из базы"""
        try:
            for i, user in enumerate(self.known_users):
                if user['id'] == user_id:
                    del self.known_encodings[i]
                    del self.known_users[i]
                    self._save_to_cache()
                    if user_id in self.last_recognitions:
                        del self.last_recognitions[user_id]
                    self.logger.info(f"Удалено лицо пользователя ID: {user_id}")
                    break
        except Exception as e:
            self.logger.error(f"Ошибка удаления лица: {e}")
    
    def cleanup(self):
        """Очистка ресурсов"""
        self.stop_processing()
        self.executor.shutdown(wait=True)
        self.logger.info("FaceRecognitionEngine очищен")