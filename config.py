"""
Конфигурация системы распознавания лиц
"""
import os
from pathlib import Path

# Базовые пути
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / 'data'
RESOURCES_DIR = BASE_DIR / 'resources'

# Создание директорий если их нет
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(DATA_DIR / 'employee_photos', exist_ok=True)
os.makedirs(DATA_DIR / 'encodings', exist_ok=True)
os.makedirs(RESOURCES_DIR / 'icons', exist_ok=True)

# База данных
DATABASE_PATH = DATA_DIR / 'database.db'
DATABASE_URL = f'sqlite:///{DATABASE_PATH}'

# Настройки камеры
CAMERA_INDEX = 0
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
FPS = 30

# Настройки распознавания лиц
FACE_RECOGNITION_TOLERANCE = 0.6
FACE_RECOGNITION_MODEL = 'hog'  # 'hog' или 'cnn'
RESIZE_SCALE = 0.25

# Настройки посещаемости
MIN_SECONDS_BETWEEN_ATTENDANCE = 30  # Минимум секунд между отметками
ATTENDANCE_TIME_FORMAT = '%Y-%m-%d %H:%M:%S'

# UI настройки
WINDOW_TITLE = "Face Attendance System - Fast Solutions LLC"
COMPANY_NAME = "Fast Solutions LLC"
PRIMARY_COLOR = "#3b5dd4"
SECONDARY_COLOR = "#5cb85c"
DANGER_COLOR = "#d9534f"

# Пути к фото
EMPLOYEE_PHOTOS_DIR = DATA_DIR / 'employee_photos'
ENCODINGS_FILE = DATA_DIR / 'encodings' / 'face_encodings.pkl'

# Настройки безопасности
DEFAULT_ADMIN_USERNAME = 'admin'
DEFAULT_ADMIN_PASSWORD = 'admin123'
PASSWORD_MIN_LENGTH = 6
SESSION_TIMEOUT_MINUTES = 30