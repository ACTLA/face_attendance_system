"""
Оптимизированный движок распознавания лиц с кэшированием
"""
import cv2
import face_recognition
import numpy as np
import threading
import time
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import pickle
import os

from config import (
    FACE_RECOGNITION_TOLERANCE, RESIZE_SCALE, 
    RECOGNITION_COOLDOWN, FRAME_SKIP, MAX_FACE_ENCODINGS_CACHE,
    DATA_DIR
)

logger = logging.getLogger(__name__)

@dataclass
class FaceMatch:
    """Результат распознавания лица"""
    user_id: int
    user_code: str
    full_name: str
    confidence: float
    face_location: Tuple[int, int, int, int]
    timestamp: float

@dataclass
class CachedUser:
    """Кэшированные данные пользователя"""
    id: int
    user_id: str
    full_name: str
    encoding: np.ndarray

class FaceRecognitionEngine:
    """
    Оптимизированный движок распознавания лиц с кэшированием
    """
    
    def __init__(self, database):
        self.db = database
        self.logger = logging.getLogger(__name__)
        
        # Кэш известных лиц
        self._cached_users: List[CachedUser] = []
        self._cache_lock = threading.RLock()
        self._cache_file = DATA_DIR / 'face_encodings_cache.pkl'
        
        # Кэш последних распознаваний для cooldown
        self._last_recognitions: Dict[int, float] = {}
        
        # Счетчик кадров для пропуска
        self._frame_counter = 0
        
        # Статистика
        self._stats = {
            'frames_processed': 0,
            'faces_detected': 0,
            'faces_recognized': 0,
            'cache_hits': 0,
            'processing_time_avg': 0.0
        }
        
        # Загрузка кэша
        self._load_face_encodings()
        
        self.logger.info("FaceRecognitionEngine инициализирован")
    
    def _load_face_encodings(self):
        """Загрузка кодировок лиц с кэшированием"""
        try:
            # Попытка загрузки из кэша
            if self._cache_file.exists():
                cache_time = os.path.getmtime(self._cache_file)
                if time.time() - cache_time < 3600:  # Кэш действителен 1 час
                    self._load_from_cache()
                    return
            
            # Загрузка из базы данных
            self._load_from_database()
            self._save_to_cache()
            
        except Exception as e:
            self.logger.error(f"Ошибка загрузки кодировок лиц: {e}")
            self._cached_users = []
    
    def _load_from_database(self):
        """Загрузка лиц из базы данных"""
        self.logger.info("Загрузка кодировок лиц из базы данных...")
        
        with self._cache_lock:
            self._cached_users = []
            
            try:
                users = self.db.get_all_users()
                
                for user in users:
                    if user['face_encoding']:
                        try:
                            encoding = np.array(user['face_encoding'])
                            if encoding.shape == (128,):  # Проверка размерности
                                cached_user = CachedUser(
                                    id=user['id'],
                                    user_id=user['user_id'],
                                    full_name=user['full_name'],
                                    encoding=encoding
                                )
                                self._cached_users.append(cached_user)
                        except Exception as e:
                            self.logger.warning(f"Пропуск пользователя {user['user_id']}: {e}")
                
                self.logger.info(f"Загружено {len(self._cached_users)} кодировок лиц")
            except Exception as e:
                self.logger.error(f"Ошибка доступа к базе данных: {e}")
    
    def _load_from_cache(self):
        """Загрузка из кэша"""
        try:
            with open(self._cache_file, 'rb') as f:
                data = pickle.load(f)
                with self._cache_lock:
                    self._cached_users = data['users']
            self.logger.info(f"Загружено {len(self._cached_users)} кодировок из кэша")
        except Exception as e:
            self.logger.error(f"Ошибка загрузки кэша: {e}")
            self._load_from_database()
    
    def _save_to_cache(self):
        """Сохранение в кэш"""
        try:
            os.makedirs(os.path.dirname(self._cache_file), exist_ok=True)
            with open(self._cache_file, 'wb') as f:
                pickle.dump({
                    'users': self._cached_users,
                    'timestamp': time.time()
                }, f)
            self.logger.debug("Кэш кодировок лиц сохранен")
        except Exception as e:
            self.logger.error(f"Ошибка сохранения кэша: {e}")
    
    def reload_face_encodings(self):
        """Принудительная перезагрузка кодировок лиц"""
        self.logger.info("Перезагрузка кодировок лиц...")
        try:
            self._load_from_database()
            self._save_to_cache()
            self._last_recognitions.clear()
        except Exception as e:
            self.logger.error(f"Ошибка перезагрузки кодировок: {e}")
    
    def process_frame(self, frame: np.ndarray) -> List[FaceMatch]:
        """
        Обработка кадра для распознавания лиц
        """
        if frame is None or frame.size == 0:
            return []
        
        start_time = time.time()
        
        # Пропуск кадров для производительности
        self._frame_counter += 1
        if self._frame_counter % FRAME_SKIP != 0:
            return []
        
        try:
            # Детекция лиц
            face_locations, face_encodings = self._detect_faces(frame)
            
            if not face_locations:
                return []
            
            # Распознавание каждого лица
            matches = []
            for location, encoding in zip(face_locations, face_encodings):
                try:
                    match = self._recognize_face(location, encoding)
                    if match and self._should_process_recognition(match):
                        matches.append(match)
                        self._update_last_recognition(match)
                except Exception as e:
                    self.logger.error(f"Ошибка распознавания отдельного лица: {e}")
                    continue
            
            # Обновление статистики
            processing_time = time.time() - start_time
            self._update_stats(processing_time, len(face_locations), len(matches))
            
            return matches
            
        except Exception as e:
            self.logger.error(f"Ошибка обработки кадра: {e}")
            return []
    
    def _detect_faces(self, frame: np.ndarray) -> Tuple[List, List]:
        """Детекция лиц на кадре"""
        try:
            # Проверка валидности кадра
            if frame is None or frame.size == 0:
                return [], []
            
            # Уменьшение кадра для ускорения
            try:
                small_frame = cv2.resize(frame, (0, 0), fx=RESIZE_SCALE, fy=RESIZE_SCALE)
                if small_frame.size == 0:
                    return [], []
                
                rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            except Exception as e:
                self.logger.error(f"Ошибка обработки кадра: {e}")
                return [], []
            
            # Поиск лиц (используем быстрый HOG детектор)
            try:
                face_locations = face_recognition.face_locations(rgb_frame, model='hog')
            except Exception as e:
                self.logger.error(f"Ошибка поиска лиц: {e}")
                return [], []
            
            if not face_locations:
                return [], []
            
            # Создание кодировок
            try:
                face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
            except Exception as e:
                self.logger.error(f"Ошибка создания кодировок: {e}")
                return [], []
            
            # Масштабирование координат обратно
            scaled_locations = []
            for top, right, bottom, left in face_locations:
                try:
                    scaled_location = (
                        int(top / RESIZE_SCALE),
                        int(right / RESIZE_SCALE),
                        int(bottom / RESIZE_SCALE),
                        int(left / RESIZE_SCALE)
                    )
                    scaled_locations.append(scaled_location)
                except Exception as e:
                    self.logger.error(f"Ошибка масштабирования координат: {e}")
                    continue
            
            return scaled_locations, face_encodings
            
        except Exception as e:
            self.logger.error(f"Ошибка детекции лиц: {e}")
            return [], []
    
    def _recognize_face(self, location: Tuple[int, int, int, int], 
                       encoding: np.ndarray) -> Optional[FaceMatch]:
        """Распознавание конкретного лица"""
        try:
            with self._cache_lock:
                if not self._cached_users:
                    return None
                
                # Создаем копию для безопасности
                cached_users = self._cached_users.copy()
            
            if not cached_users:
                return None
            
            # Извлечение кодировок для сравнения
            try:
                known_encodings = [user.encoding for user in cached_users]
            except Exception as e:
                self.logger.error(f"Ошибка извлечения кодировок: {e}")
                return None
            
            # Быстрое сравнение с использованием векторизации
            try:
                distances = face_recognition.face_distance(known_encodings, encoding)
            except Exception as e:
                self.logger.error(f"Ошибка сравнения лиц: {e}")
                return None
            
            if len(distances) == 0:
                return None
            
            # Поиск лучшего совпадения
            try:
                min_distance_idx = np.argmin(distances)
                min_distance = distances[min_distance_idx]
                
                if min_distance <= FACE_RECOGNITION_TOLERANCE:
                    user = cached_users[min_distance_idx]
                    confidence = 1.0 - min_distance
                    
                    return FaceMatch(
                        user_id=user.id,
                        user_code=user.user_id,
                        full_name=user.full_name,
                        confidence=confidence,
                        face_location=location,
                        timestamp=time.time()
                    )
            except Exception as e:
                self.logger.error(f"Ошибка поиска совпадения: {e}")
                return None
            
            return None
            
        except Exception as e:
            self.logger.error(f"Ошибка распознавания лица: {e}")
            return None
    
    def _should_process_recognition(self, match: FaceMatch) -> bool:
        """Проверка cooldown для предотвращения спама"""
        try:
            user_id = match.user_id
            current_time = match.timestamp
            
            if user_id in self._last_recognitions:
                last_time = self._last_recognitions[user_id]
                if current_time - last_time < RECOGNITION_COOLDOWN:
                    return False
            
            return True
        except Exception as e:
            self.logger.error(f"Ошибка проверки cooldown: {e}")
            return True  # В случае ошибки разрешаем обработку
    
    def _update_last_recognition(self, match: FaceMatch):
        """Обновление времени последнего распознавания"""
        try:
            self._last_recognitions[match.user_id] = match.timestamp
            
            # Очистка старых записей
            current_time = time.time()
            expired_users = [
                user_id for user_id, last_time in self._last_recognitions.items()
                if current_time - last_time > RECOGNITION_COOLDOWN * 3
            ]
            
            for user_id in expired_users:
                del self._last_recognitions[user_id]
        except Exception as e:
            self.logger.error(f"Ошибка обновления времени распознавания: {e}")
    
    def _update_stats(self, processing_time: float, faces_detected: int, faces_recognized: int):
        """Обновление статистики"""
        try:
            self._stats['frames_processed'] += 1
            self._stats['faces_detected'] += faces_detected
            self._stats['faces_recognized'] += faces_recognized
            
            # Скользящее среднее времени обработки
            alpha = 0.1
            self._stats['processing_time_avg'] = (
                alpha * processing_time + 
                (1 - alpha) * self._stats['processing_time_avg']
            )
        except Exception as e:
            self.logger.error(f"Ошибка обновления статистики: {e}")
    
    def get_stats(self) -> dict:
        """Получение статистики работы"""
        try:
            return self._stats.copy()
        except Exception as e:
            self.logger.error(f"Ошибка получения статистики: {e}")
            return {}
    
    def add_new_face(self, user_data: dict):
        """Добавление нового лица в кэш"""
        try:
            if user_data.get('face_encoding'):
                encoding = np.array(user_data['face_encoding'])
                if encoding.shape == (128,):
                    cached_user = CachedUser(
                        id=user_data['id'],
                        user_id=user_data['user_id'],
                        full_name=user_data['full_name'],
                        encoding=encoding
                    )
                    
                    with self._cache_lock:
                        self._cached_users.append(cached_user)
                        
                        # Ограничение размера кэша
                        if len(self._cached_users) > MAX_FACE_ENCODINGS_CACHE:
                            self._cached_users = self._cached_users[-MAX_FACE_ENCODINGS_CACHE:]
                    
                    self._save_to_cache()
                    self.logger.info(f"Добавлено новое лицо в кэш: {user_data['full_name']}")
        except Exception as e:
            self.logger.error(f"Ошибка добавления лица в кэш: {e}")
    
    def remove_face(self, user_id: int):
        """Удаление лица из кэша"""
        try:
            with self._cache_lock:
                self._cached_users = [
                    user for user in self._cached_users 
                    if user.id != user_id
                ]
            
            if user_id in self._last_recognitions:
                del self._last_recognitions[user_id]
            
            self._save_to_cache()
            self.logger.info(f"Удалено лицо из кэша: user_id={user_id}")
        except Exception as e:
            self.logger.error(f"Ошибка удаления лица из кэша: {e}")
    
    def clear_cache(self):
        """Очистка кэша"""
        try:
            with self._cache_lock:
                self._cached_users.clear()
            self._last_recognitions.clear()
            
            if self._cache_file.exists():
                try:
                    os.remove(self._cache_file)
                except:
                    pass
            
            self.logger.info("Кэш кодировок лиц очищен")
        except Exception as e:
            self.logger.error(f"Ошибка очистки кэша: {e}")