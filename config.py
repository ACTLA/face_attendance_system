"""
Конфигурация автоматизированной системы распознавания лиц
Централизованное управление настройками системы
"""
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

# Базовые пути
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / 'data'
RESOURCES_DIR = BASE_DIR / 'resources'
LOGS_DIR = BASE_DIR / 'logs'
CONFIG_DIR = BASE_DIR / 'config'

# Создание директорий
for directory in [DATA_DIR, RESOURCES_DIR, LOGS_DIR, CONFIG_DIR]:
    directory.mkdir(exist_ok=True)

# Поддиректории
USER_PHOTOS_DIR = DATA_DIR / 'user_photos'
ENCODINGS_DIR = DATA_DIR / 'encodings'
BACKUP_DIR = DATA_DIR / 'backups'
TEMP_DIR = DATA_DIR / 'temp'

for directory in [USER_PHOTOS_DIR, ENCODINGS_DIR, BACKUP_DIR, TEMP_DIR]:
    directory.mkdir(exist_ok=True)

class LogLevel(Enum):
    """Уровни логирования"""
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL

class RecognitionModel(Enum):
    """Модели распознавания лиц"""
    HOG = 'hog'
    CNN = 'cnn'

@dataclass
class DatabaseConfig:
    """Конфигурация базы данных"""
    path: str = str(DATA_DIR / 'database.db')
    url: str = None
    backup_enabled: bool = True
    backup_interval_hours: int = 24
    
    def __post_init__(self):
        if self.url is None:
            self.url = f'sqlite:///{self.path}'

@dataclass
class CameraConfig:
    """Конфигурация камеры"""
    index: int = 0
    width: int = 640
    height: int = 480
    fps: int = 30
    buffer_size: int = 1
    auto_exposure: bool = True
    brightness: int = 128
    contrast: int = 128

@dataclass
class RecognitionConfig:
    """Конфигурация распознавания лиц"""
    tolerance: float = 0.6
    model: RecognitionModel = RecognitionModel.HOG
    resize_scale: float = 0.25
    min_face_size: int = 50
    max_faces_per_frame: int = 10
    recognition_interval_seconds: int = 2
    confidence_threshold: float = 0.5
    use_gpu: bool = False

@dataclass
class PerformanceConfig:
    """Конфигурация производительности"""
    max_workers: int = 2
    frame_skip: int = 3
    queue_size: int = 5
    enable_multithreading: bool = True
    memory_limit_mb: int = 512
    cache_size: int = 1000

@dataclass
class UIConfig:
    """Конфигурация интерфейса"""
    window_title: str = "Автоматизированная система распознавания лиц - Fast Solutions LLC"
    company_name: str = "Fast Solutions LLC"
    window_min_width: int = 1000
    window_min_height: int = 700
    window_default_width: int = 1200
    window_default_height: int = 800
    theme: str = "light"
    language: str = "ru"
    auto_save_layout: bool = True

@dataclass
class ColorConfig:
    """Конфигурация цветов"""
    primary_color: str = "#3b5dd4"
    secondary_color: str = "#5cb85c"
    danger_color: str = "#d9534f"
    warning_color: str = "#f39c12"
    success_color: str = "#28a745"
    info_color: str = "#17a2b8"
    dark_color: str = "#343a40"
    light_color: str = "#f8f9fa"

@dataclass
class SecurityConfig:
    """Конфигурация безопасности"""
    default_admin_username: str = 'admin'
    default_admin_password: str = 'admin123'
    password_min_length: int = 6
    session_timeout_minutes: int = 30
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15
    enable_encryption: bool = False
    salt_rounds: int = 12

@dataclass
class LoggingConfig:
    """Конфигурация логирования"""
    level: LogLevel = LogLevel.INFO
    file_enabled: bool = True
    console_enabled: bool = True
    max_file_size_mb: int = 10
    backup_count: int = 5
    format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format: str = '%Y-%m-%d %H:%M:%S'

class ConfigManager:
    """Менеджер конфигурации системы"""
    
    def __init__(self, config_file: str = None):
        self.config_file = config_file or str(CONFIG_DIR / 'settings.json')
        self.logger = self._setup_logger()
        
        # Инициализация конфигураций
        self.database = DatabaseConfig()
        self.camera = CameraConfig()
        self.recognition = RecognitionConfig()
        self.performance = PerformanceConfig()
        self.ui = UIConfig()
        self.colors = ColorConfig()
        self.security = SecurityConfig()
        self.logging = LoggingConfig()
        
        # Загрузка настроек из файла
        self.load_config()
        
        # Применение настроек логирования
        self._apply_logging_config()
    
    def _setup_logger(self) -> logging.Logger:
        """Базовая настройка логгера"""
        logger = logging.getLogger(__name__)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def load_config(self):
        """Загрузка конфигурации из файла"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    self._apply_config_data(config_data)
                self.logger.info(f"Конфигурация загружена из {self.config_file}")
            else:
                self.logger.info("Файл конфигурации не найден, используются настройки по умолчанию")
                self.save_config()
        except Exception as e:
            self.logger.error(f"Ошибка загрузки конфигурации: {e}")
    
    def save_config(self):
        """Сохранение конфигурации в файл"""
        try:
            config_data = {
                'database': asdict(self.database),
                'camera': asdict(self.camera),
                'recognition': {
                    **asdict(self.recognition),
                    'model': self.recognition.model.value
                },
                'performance': asdict(self.performance),
                'ui': asdict(self.ui),
                'colors': asdict(self.colors),
                'security': asdict(self.security),
                'logging': {
                    **asdict(self.logging),
                    'level': self.logging.level.value
                }
            }
            
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)
            
            self.logger.info(f"Конфигурация сохранена в {self.config_file}")
        except Exception as e:
            self.logger.error(f"Ошибка сохранения конфигурации: {e}")
    
    def _apply_config_data(self, config_data: Dict[str, Any]):
        """Применение данных конфигурации"""
        try:
            if 'database' in config_data:
                self.database = DatabaseConfig(**config_data['database'])
            
            if 'camera' in config_data:
                self.camera = CameraConfig(**config_data['camera'])
            
            if 'recognition' in config_data:
                rec_data = config_data['recognition'].copy()
                if 'model' in rec_data:
                    rec_data['model'] = RecognitionModel(rec_data['model'])
                self.recognition = RecognitionConfig(**rec_data)
            
            if 'performance' in config_data:
                self.performance = PerformanceConfig(**config_data['performance'])
            
            if 'ui' in config_data:
                self.ui = UIConfig(**config_data['ui'])
            
            if 'colors' in config_data:
                self.colors = ColorConfig(**config_data['colors'])
            
            if 'security' in config_data:
                self.security = SecurityConfig(**config_data['security'])
            
            if 'logging' in config_data:
                log_data = config_data['logging'].copy()
                if 'level' in log_data:
                    log_data['level'] = LogLevel(log_data['level'])
                self.logging = LoggingConfig(**log_data)
                
        except Exception as e:
            self.logger.error(f"Ошибка применения конфигурации: {e}")
    
    def _apply_logging_config(self):
        """Применение настроек логирования"""
        try:
            # Настройка корневого логгера
            root_logger = logging.getLogger()
            root_logger.setLevel(self.logging.level.value)
            
            # Очистка существующих обработчиков
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)
            
            formatter = logging.Formatter(
                self.logging.format,
                datefmt=self.logging.date_format
            )
            
            # Консольный обработчик
            if self.logging.console_enabled:
                console_handler = logging.StreamHandler()
                console_handler.setFormatter(formatter)
                root_logger.addHandler(console_handler)
            
            # Файловый обработчик
            if self.logging.file_enabled:
                from logging.handlers import RotatingFileHandler
                
                log_file = LOGS_DIR / 'face_recognition.log'
                file_handler = RotatingFileHandler(
                    log_file,
                    maxBytes=self.logging.max_file_size_mb * 1024 * 1024,
                    backupCount=self.logging.backup_count,
                    encoding='utf-8'
                )
                file_handler.setFormatter(formatter)
                root_logger.addHandler(file_handler)
            
        except Exception as e:
            print(f"Ошибка настройки логирования: {e}")
    
    def get_database_url(self) -> str:
        """Получение URL базы данных"""
        return self.database.url
    
    def get_user_photos_dir(self) -> Path:
        """Получение директории фотографий пользователей"""
        return USER_PHOTOS_DIR
    
    def get_encodings_file(self) -> Path:
        """Получение файла кодировок лиц"""
        return ENCODINGS_DIR / 'face_encodings.pkl'
    
    def validate_config(self) -> Dict[str, list]:
        """Валидация конфигурации"""
        errors = {}
        
        # Проверка камеры
        if self.camera.width <= 0 or self.camera.height <= 0:
            errors.setdefault('camera', []).append("Неверные размеры кадра")
        
        if self.camera.fps <= 0:
            errors.setdefault('camera', []).append("Неверная частота кадров")
        
        # Проверка распознавания
        if not 0 < self.recognition.tolerance <= 1:
            errors.setdefault('recognition', []).append("Толерантность должна быть от 0 до 1")
        
        if not 0 < self.recognition.resize_scale <= 1:
            errors.setdefault('recognition', []).append("Масштаб должен быть от 0 до 1")
        
        # Проверка производительности
        if self.performance.max_workers <= 0:
            errors.setdefault('performance', []).append("Количество воркеров должно быть больше 0")
        
        # Проверка безопасности
        if len(self.security.default_admin_password) < self.security.password_min_length:
            errors.setdefault('security', []).append("Пароль администратора слишком короткий")
        
        return errors
    
    def reset_to_defaults(self):
        """Сброс к настройкам по умолчанию"""
        self.database = DatabaseConfig()
        self.camera = CameraConfig()
        self.recognition = RecognitionConfig()
        self.performance = PerformanceConfig()
        self.ui = UIConfig()
        self.colors = ColorConfig()
        self.security = SecurityConfig()
        self.logging = LoggingConfig()
        
        self.save_config()
        self._apply_logging_config()
        self.logger.info("Конфигурация сброшена к значениям по умолчанию")

# Глобальный экземпляр менеджера конфигурации
config = ConfigManager()

# Обратная совместимость - экспорт основных настроек
DATABASE_PATH = config.database.path
DATABASE_URL = config.database.url
CAMERA_INDEX = config.camera.index
CAMERA_WIDTH = config.camera.width
CAMERA_HEIGHT = config.camera.height
FPS = config.camera.fps
FACE_RECOGNITION_TOLERANCE = config.recognition.tolerance
FACE_RECOGNITION_MODEL = config.recognition.model.value
RESIZE_SCALE = config.recognition.resize_scale
MIN_SECONDS_BETWEEN_RECOGNITION = config.recognition.recognition_interval_seconds
USER_PHOTOS_DIR = config.get_user_photos_dir()
ENCODINGS_FILE = config.get_encodings_file()
WINDOW_TITLE = config.ui.window_title
COMPANY_NAME = config.ui.company_name
PRIMARY_COLOR = config.colors.primary_color
SECONDARY_COLOR = config.colors.secondary_color
DANGER_COLOR = config.colors.danger_color
WARNING_COLOR = config.colors.warning_color
DEFAULT_ADMIN_USERNAME = config.security.default_admin_username
DEFAULT_ADMIN_PASSWORD = config.security.default_admin_password
WINDOW_MIN_WIDTH = config.ui.window_min_width
WINDOW_MIN_HEIGHT = config.ui.window_min_height
VIDEO_WIDGET_MIN_WIDTH = 480
VIDEO_WIDGET_MIN_HEIGHT = 360