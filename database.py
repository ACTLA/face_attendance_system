"""
Упрощенная база данных без сложных миграций
"""
import sqlite3
import hashlib
import json
import logging
import os
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from contextlib import contextmanager
import secrets

from config import DATABASE_PATH, DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD

logger = logging.getLogger(__name__)

class Database:
    """Упрощенная база данных с автоматической инициализацией"""
    
    def __init__(self):
        self.db_path = str(DATABASE_PATH)
        self._lock = threading.RLock()
        
        # Создание БД и таблиц
        self._create_database()
        self._create_default_admin()
        
        logger.info(f"База данных инициализирована: {self.db_path}")
    
    @contextmanager
    def get_connection(self):
        """Получение соединения с базой данных"""
        with self._lock:
            try:
                conn = sqlite3.connect(self.db_path, timeout=30.0)
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA foreign_keys = ON")
                yield conn
            except Exception as e:
                logger.error(f"Ошибка подключения к БД: {e}")
                raise
            finally:
                conn.close()
    
    def _create_database(self):
        """Создание таблиц базы данных"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Таблица администраторов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS admins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP NULL
                )
            ''')
            
            # Таблица пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT UNIQUE NOT NULL,
                    full_name TEXT NOT NULL,
                    email TEXT DEFAULT '',
                    phone TEXT DEFAULT '',
                    photo_path TEXT,
                    face_encoding TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by INTEGER,
                    FOREIGN KEY (created_by) REFERENCES admins (id)
                )
            ''')
            
            # Таблица логов распознавания
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS recognition_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    confidence REAL NOT NULL,
                    recognition_type TEXT DEFAULT 'SUCCESS',
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            
            # Индексы для оптимизации
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_active ON users (is_active)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_user_id ON users (user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_recognition_timestamp ON recognition_logs (timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_recognition_user ON recognition_logs (user_id)')
            
            conn.commit()
            logger.info("Таблицы базы данных созданы/проверены")
    
    def _hash_password(self, password: str, salt: str) -> str:
        """Хеширование пароля"""
        return hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        ).hex()
    
    def _create_default_admin(self):
        """Создание администратора по умолчанию"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Проверка существования администратора
            cursor.execute("SELECT id FROM admins WHERE username = ?", (DEFAULT_ADMIN_USERNAME,))
            
            if not cursor.fetchone():
                salt = secrets.token_hex(32)
                password_hash = self._hash_password(DEFAULT_ADMIN_PASSWORD, salt)
                
                cursor.execute('''
                    INSERT INTO admins (username, email, password_hash, salt)
                    VALUES (?, ?, ?, ?)
                ''', (
                    DEFAULT_ADMIN_USERNAME,
                    'admin@company.com',
                    password_hash,
                    salt
                ))
                
                conn.commit()
                logger.info("Создан администратор по умолчанию")
    
    def authenticate_admin(self, username: str, password: str) -> Optional[Dict]:
        """Аутентификация администратора"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, username, email, password_hash, salt, is_active
                    FROM admins WHERE username = ?
                ''', (username,))
                
                admin = cursor.fetchone()
                
                if not admin:
                    return None
                
                admin_dict = dict(admin)
                
                # Проверка активности
                if not admin_dict['is_active']:
                    return None
                
                # Проверка пароля
                password_hash = self._hash_password(password, admin_dict['salt'])
                if password_hash != admin_dict['password_hash']:
                    return None
                
                # Обновление времени последнего входа
                cursor.execute('''
                    UPDATE admins SET last_login = ? WHERE id = ?
                ''', (datetime.now(), admin_dict['id']))
                
                conn.commit()
                
                return {
                    'id': admin_dict['id'],
                    'username': admin_dict['username'],
                    'email': admin_dict['email']
                }
                
        except Exception as e:
            logger.error(f"Ошибка аутентификации: {e}")
            return None
    
    def add_user(self, user_data: Dict, created_by: int) -> Optional[int]:
        """Добавление нового пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO users 
                    (user_id, full_name, email, phone, photo_path, face_encoding, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_data['user_id'],
                    user_data['full_name'],
                    user_data.get('email', ''),
                    user_data.get('phone', ''),
                    user_data.get('photo_path', ''),
                    json.dumps(user_data.get('face_encoding', [])),
                    created_by
                ))
                
                user_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"Добавлен пользователь: {user_data['full_name']}")
                return user_id
                
        except sqlite3.IntegrityError:
            logger.warning(f"Пользователь {user_data['user_id']} уже существует")
            return None
        except Exception as e:
            logger.error(f"Ошибка добавления пользователя: {e}")
            return None
    
    def get_all_users(self, active_only: bool = True) -> List[Dict]:
        """Получение всех пользователей"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM users"
                if active_only:
                    query += " WHERE is_active = 1"
                query += " ORDER BY full_name"
                
                cursor.execute(query)
                users = cursor.fetchall()
                
                result = []
                for user in users:
                    user_dict = dict(user)
                    try:
                        user_dict['face_encoding'] = json.loads(user_dict['face_encoding'] or '[]')
                    except:
                        user_dict['face_encoding'] = []
                    result.append(user_dict)
                
                return result
                
        except Exception as e:
            logger.error(f"Ошибка получения пользователей: {e}")
            return []
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Получение пользователя по ID"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
                user = cursor.fetchone()
                
                if user:
                    user_dict = dict(user)
                    try:
                        user_dict['face_encoding'] = json.loads(user_dict['face_encoding'] or '[]')
                    except:
                        user_dict['face_encoding'] = []
                    return user_dict
                
                return None
                
        except Exception as e:
            logger.error(f"Ошибка получения пользователя: {e}")
            return None
    
    def delete_user(self, user_id: int):
        """Удаление пользователя (мягкое удаление)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET is_active = 0 WHERE id = ?", (user_id,))
                conn.commit()
                logger.info(f"Пользователь ID {user_id} деактивирован")
        except Exception as e:
            logger.error(f"Ошибка удаления пользователя: {e}")
    
    def add_recognition_log(self, user_id: int, confidence: float, recognition_type: str = 'SUCCESS') -> Optional[int]:
        """Добавление лога распознавания"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO recognition_logs (user_id, confidence, recognition_type)
                    VALUES (?, ?, ?)
                ''', (user_id, confidence, recognition_type))
                
                log_id = cursor.lastrowid
                conn.commit()
                return log_id
                
        except Exception as e:
            logger.error(f"Ошибка добавления лога распознавания: {e}")
            return None
    
    def get_recognition_report(self, limit: int = 100) -> List[Dict]:
        """Получение отчета по распознаванию"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT r.*, u.full_name, u.user_id as user_code
                    FROM recognition_logs r
                    JOIN users u ON r.user_id = u.id
                    ORDER BY r.timestamp DESC
                    LIMIT ?
                ''', (limit,))
                
                records = cursor.fetchall()
                return [dict(rec) for rec in records]
                
        except Exception as e:
            logger.error(f"Ошибка получения отчета: {e}")
            return []
    
    def get_today_recognition_count(self) -> int:
        """Получение количества распознаваний за сегодня"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) 
                    FROM recognition_logs 
                    WHERE DATE(timestamp) = DATE('now')
                ''')
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Ошибка получения счетчика за сегодня: {e}")
            return 0
    
    def get_unique_users_today(self) -> int:
        """Получение количества уникальных пользователей за сегодня"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(DISTINCT user_id) 
                    FROM recognition_logs 
                    WHERE DATE(timestamp) = DATE('now')
                ''')
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Ошибка получения уникальных пользователей: {e}")
            return 0