"""
Конфигурация автоматизированной системы распознавания лиц
"""
import os
from pathlib import Path

# Базовые пути
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / 'data'
RESOURCES_DIR = BASE_DIR / 'resources'

# Создание директорий если их нет
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(DATA_DIR / 'user_photos', exist_ok=True)
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

# Настройки распознавания лиц (оригинальные значения)
FACE_RECOGNITION_TOLERANCE = 0.6  # Вернул оригинальное значение
FACE_RECOGNITION_MODEL = 'hog'  # 'hog' или 'cnn'
RESIZE_SCALE = 0.25  # Вернул оригинальное значение

# Настройки системы распознавания
MIN_SECONDS_BETWEEN_RECOGNITION = 2  # Вернул оригинальное значение
RECOGNITION_TIME_FORMAT = '%Y-%m-%d %H:%M:%S'
RECOGNITION_UPDATE_INTERVAL = 500  # мс для обновления UI

# UI настройки
WINDOW_TITLE = "Автоматизированная система распознавания лиц - Fast Solutions LLC"
COMPANY_NAME = "Fast Solutions LLC"
PRIMARY_COLOR = "#3b5dd4"
SECONDARY_COLOR = "#5cb85c"
DANGER_COLOR = "#d9534f"
WARNING_COLOR = "#f39c12"

# Пути к фото
USER_PHOTOS_DIR = DATA_DIR / 'user_photos'
ENCODINGS_FILE = DATA_DIR / 'encodings' / 'face_encodings.pkl'

# Настройки безопасности
DEFAULT_ADMIN_USERNAME = 'admin'
DEFAULT_ADMIN_PASSWORD = 'admin123'
PASSWORD_MIN_LENGTH = 6
SESSION_TIMEOUT_MINUTES = 30

# Настройки интерфейса
WINDOW_MIN_WIDTH = 1000
WINDOW_MIN_HEIGHT = 700
WINDOW_DEFAULT_WIDTH = 1200
WINDOW_DEFAULT_HEIGHT = 800
VIDEO_WIDGET_MIN_WIDTH = 480
VIDEO_WIDGET_MIN_HEIGHT = 360

# Размеры диалогов
DIALOG_MIN_WIDTH = 800
DIALOG_MIN_HEIGHT = 600
LOGIN_WINDOW_WIDTH = 800
LOGIN_WINDOW_HEIGHT = 500