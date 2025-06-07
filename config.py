"""
Упрощенная конфигурация системы распознавания лиц
"""
import os
from pathlib import Path

# Базовые пути
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / 'data'
LOGS_DIR = BASE_DIR / 'logs'

# Создание директорий
for directory in [DATA_DIR, LOGS_DIR]:
    directory.mkdir(exist_ok=True)

# Поддиректории
USER_PHOTOS_DIR = DATA_DIR / 'user_photos'
USER_PHOTOS_DIR.mkdir(exist_ok=True)

# База данных
DATABASE_PATH = DATA_DIR / 'database.db'

# Настройки камеры
CAMERA_INDEX = 0
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 30

# Настройки распознавания лиц
FACE_RECOGNITION_TOLERANCE = 0.6
RESIZE_SCALE = 0.25  # Уменьшение кадра для ускорения
MIN_FACE_SIZE = 50
RECOGNITION_COOLDOWN = 3  # Секунды между распознаваниями одного лица

# Настройки UI
WINDOW_TITLE = "Система распознавания лиц"
WINDOW_MIN_WIDTH = 1000
WINDOW_MIN_HEIGHT = 700

# Цвета
PRIMARY_COLOR = "#3b5dd4"
SECONDARY_COLOR = "#28a745"
DANGER_COLOR = "#dc3545"
WARNING_COLOR = "#ffc107"
SUCCESS_COLOR = "#28a745"

# Безопасность
DEFAULT_ADMIN_USERNAME = 'admin'
DEFAULT_ADMIN_PASSWORD = 'admin123'
PASSWORD_MIN_LENGTH = 6

# Логирование
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5

# Производительность
MAX_RECOGNITION_WORKERS = 2
FRAME_SKIP = 3  # Обрабатывать каждый N-й кадр
MAX_FACE_ENCODINGS_CACHE = 1000