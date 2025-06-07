"""
Исправленный модуль работы с базой данных
"""
import sqlite3
import hashlib
import json
import logging
import threading
import time
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from contextlib import contextmanager
from pathlib import Path
import shutil

# Импорт системы миграций
from database_migration import migrate_database

try:
    from config import config
except ImportError:
    # Fallback для совместимости
    class FallbackConfig:
        class database:
            path = "data/database.db"
            backup_enabled = True
            backup_interval_hours = 24
        class security:
            default_admin_username = 'admin'
            default_admin_password = 'admin123'
            max_login_attempts = 5
            lockout_duration_minutes = 15
    
    config = FallbackConfig()

class DatabaseError(Exception):
    """Исключение для ошибок базы данных"""
    pass

class Database:
    """
    Улучшенный класс для работы с базой данных с автоматическими миграциями
    """
    
    def __init__(self):
        self.db_path = getattr(config.database, 'path', 'data/database.db')
        self.logger = logging.getLogger(__name__)
        self._lock = threading.RLock()
        self._connection_pool = {}
        self._pool_lock = threading.Lock()
        
        # Создание директории для БД
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Запуск миграций перед инициализацией
        try:
            migrate_database(self.db_path)
        except Exception as e:
            self.logger.error(f"Ошибка миграции БД: {e}")
        
        # Инициализация БД
        self.init_database()
        
        # Настройка автоматического бэкапа
        backup_enabled = getattr(config.database, 'backup_enabled', True)
        if backup_enabled:
            self._setup_backup_timer()
        
        self.logger.info(f"База данных инициализирована: {self.db_path}")
    
    @contextmanager
    def get_connection(self):
        """Получение соединения с БД через контекстный менеджер"""
        thread_id = threading.get_ident()
        
        with self._pool_lock:
            if thread_id not in self._connection_pool:
                try:
                    conn = sqlite3.connect(
                        self.db_path,
                        check_same_thread=False,
                        timeout=30.0
                    )
                    conn.row_factory = sqlite3.Row
                    conn.execute("PRAGMA foreign_keys = ON")
                    conn.execute("PRAGMA journal_mode = WAL")
                    conn.execute("PRAGMA synchronous = NORMAL")
                    self._connection_pool[thread_id] = conn
                    self.logger.debug(f"Создано новое соединение для потока {thread_id}")
                except Exception as e:
                    self.logger.error(f"Ошибка создания соединения: {e}")
                    raise DatabaseError(f"Не удалось подключиться к базе данных: {e}")
            
            conn = self._connection_pool[thread_id]
        
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Ошибка выполнения запроса: {e}")
            raise
    
    def close_all_connections(self):
        """Закрытие всех соединений"""
        with self._pool_lock:
            for thread_id, conn in self._connection_pool.items():
                try:
                    conn.close()
                    self.logger.debug(f"Закрыто соединение для потока {thread_id}")
                except Exception as e:
                    self.logger.error(f"Ошибка закрытия соединения: {e}")
            self._connection_pool.clear()
    
    def _hash_password(self, password: str, salt: str) -> str:
        """Исправленное хеширование пароля с солью"""
        # Используем pbkdf2_hmac вместо pbkdf2_hex
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # iterations
        )
        return key.hex()  # Конвертируем в hex строку
    
    def init_database(self):
        """Инициализация базы данных (проверка целостности)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Проверяем, что все необходимые таблицы существуют
            required_tables = ['admins', 'users', 'recognition_logs', 'system_logs']
            
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ({})
            """.format(','.join('?' * len(required_tables))), required_tables)
            
            existing_tables = [row[0] for row in cursor.fetchall()]
            
            if len(existing_tables) != len(required_tables):
                self.logger.warning("Не все таблицы существуют, создаем недостающие")
                self._create_missing_tables(cursor, existing_tables)
                conn.commit()
            
            # Создание администратора по умолчанию
            self.create_default_admin()
            
            self.logger.info("База данных инициализирована успешно")
    
    def _create_missing_tables(self, cursor, existing_tables):
        """Создание недостающих таблиц"""
        if 'admins' not in existing_tables:
            cursor.execute('''
                CREATE TABLE admins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    login_attempts INTEGER DEFAULT 0,
                    locked_until TIMESTAMP NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    last_ip TEXT,
                    permissions TEXT DEFAULT '{}',
                    CONSTRAINT valid_email CHECK (email LIKE '%@%')
                )
            ''')
        
        if 'users' not in existing_tables:
            cursor.execute('''
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT UNIQUE NOT NULL,
                    full_name TEXT NOT NULL,
                    email TEXT DEFAULT '',
                    phone TEXT DEFAULT '',
                    department TEXT DEFAULT '',
                    position TEXT DEFAULT '',
                    photo_path TEXT,
                    face_encoding TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by INTEGER,
                    notes TEXT DEFAULT '',
                    FOREIGN KEY (created_by) REFERENCES admins (id)
                )
            ''')
        
        if 'recognition_logs' not in existing_tables:
            cursor.execute('''
                CREATE TABLE recognition_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    confidence REAL NOT NULL,
                    recognition_type TEXT DEFAULT 'SUCCESS',
                    face_location TEXT,
                    processing_time REAL,
                    camera_id INTEGER DEFAULT 0,
                    additional_data TEXT DEFAULT '{}',
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
        
        if 'system_logs' not in existing_tables:
            cursor.execute('''
                CREATE TABLE system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    level TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    admin_id INTEGER,
                    message TEXT NOT NULL,
                    details TEXT DEFAULT '{}',
                    ip_address TEXT,
                    user_agent TEXT,
                    FOREIGN KEY (admin_id) REFERENCES admins (id)
                )
            ''')
    
    def create_default_admin(self):
        """Создание администратора по умолчанию"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            default_username = getattr(config.security, 'default_admin_username', 'admin')
            default_password = getattr(config.security, 'default_admin_password', 'admin123')
            
            # Проверка существования администратора
            cursor.execute("SELECT id FROM admins WHERE username = ?", (default_username,))
            
            if not cursor.fetchone():
                salt = os.urandom(32).hex()
                password_hash = self._hash_password(default_password, salt)
                
                cursor.execute('''
                    INSERT INTO admins (username, email, password_hash, salt, permissions)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    default_username,
                    'admin@company.com',
                    password_hash,
                    salt,
                    json.dumps({'admin': True, 'manage_users': True, 'view_reports': True})
                ))
                conn.commit()
                
                self.add_system_log('INFO', 'admin_created', None, 
                                  'Создан администратор по умолчанию')
    
    # === Методы для работы с администраторами ===
    
    def authenticate_admin(self, username: str, password: str, ip_address: str = None) -> Optional[Dict]:
        """Аутентификация администратора с защитой от брутфорса"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            try:
                # Получение данных администратора
                cursor.execute('''
                    SELECT id, username, email, password_hash, salt, is_active, 
                           login_attempts, locked_until, permissions
                    FROM admins WHERE username = ?
                ''', (username,))
                
                admin = cursor.fetchone()
                
                if not admin:
                    self.add_system_log('WARNING', 'login_failed', None, 
                                      f'Попытка входа с несуществующим пользователем: {username}',
                                      {'ip': ip_address})
                    return None
                
                admin_dict = dict(admin)
                
                # Проверка блокировки
                if admin_dict['locked_until']:
                    locked_until = datetime.fromisoformat(admin_dict['locked_until'])
                    if datetime.now() < locked_until:
                        self.add_system_log('WARNING', 'login_blocked', admin_dict['id'],
                                          f'Попытка входа заблокированного пользователя: {username}',
                                          {'ip': ip_address})
                        return None
                    else:
                        # Разблокировка пользователя
                        cursor.execute('''
                            UPDATE admins SET locked_until = NULL, login_attempts = 0 
                            WHERE id = ?
                        ''', (admin_dict['id'],))
                
                # Проверка активности
                if not admin_dict['is_active']:
                    self.add_system_log('WARNING', 'login_inactive', admin_dict['id'],
                                      f'Попытка входа неактивного пользователя: {username}',
                                      {'ip': ip_address})
                    return None
                
                # Проверка пароля
                password_hash = self._hash_password(password, admin_dict['salt'])
                if password_hash != admin_dict['password_hash']:
                    # Увеличение счетчика неудачных попыток
                    login_attempts = admin_dict['login_attempts'] + 1
                    locked_until = None
                    
                    max_attempts = getattr(config.security, 'max_login_attempts', 5)
                    lockout_duration = getattr(config.security, 'lockout_duration_minutes', 15)
                    
                    if login_attempts >= max_attempts:
                        locked_until = datetime.now() + timedelta(minutes=lockout_duration)
                    
                    cursor.execute('''
                        UPDATE admins SET login_attempts = ?, locked_until = ?
                        WHERE id = ?
                    ''', (login_attempts, locked_until, admin_dict['id']))
                    
                    conn.commit()
                    
                    self.add_system_log('WARNING', 'login_failed', admin_dict['id'],
                                      f'Неверный пароль для пользователя: {username}',
                                      {'ip': ip_address, 'attempts': login_attempts})
                    return None
                
                # Успешная аутентификация
                cursor.execute('''
                    UPDATE admins SET 
                        last_login = ?, 
                        last_ip = ?, 
                        login_attempts = 0, 
                        locked_until = NULL
                    WHERE id = ?
                ''', (datetime.now(), ip_address, admin_dict['id']))
                
                conn.commit()
                
                self.add_system_log('INFO', 'login_success', admin_dict['id'],
                                  f'Успешный вход пользователя: {username}',
                                  {'ip': ip_address})
                
                return {
                    'id': admin_dict['id'],
                    'username': admin_dict['username'],
                    'email': admin_dict['email'],
                    'permissions': json.loads(admin_dict['permissions'] or '{}')
                }
                
            except Exception as e:
                self.logger.error(f"Ошибка аутентификации: {e}")
                return None
    
    # === Остальные методы остаются без изменений ===
    
    def add_user(self, user_data: Dict, created_by: int) -> Optional[int]:
        """Добавление нового пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO users 
                    (user_id, full_name, photo_path, face_encoding, created_by)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    user_data['user_id'],
                    user_data['full_name'],
                    user_data.get('photo_path', ''),
                    json.dumps(user_data.get('face_encoding', [])),
                    created_by
                ))
                
                user_id = cursor.lastrowid
                conn.commit()
                
                self.add_system_log('INFO', 'user_added', created_by,
                                  f'Добавлен пользователь: {user_data["full_name"]}')
                
                return user_id
                
        except sqlite3.IntegrityError:
            return None
        except Exception as e:
            self.logger.error(f"Ошибка добавления пользователя: {e}")
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
            self.logger.error(f"Ошибка получения пользователей: {e}")
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
            self.logger.error(f"Ошибка получения пользователя: {e}")
            return None
    
    def delete_user(self, user_id: int):
        """Удаление пользователя (мягкое удаление)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET is_active = 0 WHERE id = ?", (user_id,))
                conn.commit()
        except Exception as e:
            self.logger.error(f"Ошибка удаления пользователя: {e}")
    
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
            self.logger.error(f"Ошибка добавления лога распознавания: {e}")
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
            self.logger.error(f"Ошибка получения отчета: {e}")
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
            self.logger.error(f"Ошибка получения счетчика за сегодня: {e}")
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
            self.logger.error(f"Ошибка получения уникальных пользователей: {e}")
            return 0
    
    def get_last_recognition(self, user_id: int):
        """Получить последнее распознавание пользователя"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT timestamp FROM recognition_logs 
                    WHERE user_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                ''', (user_id,))
                
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            self.logger.error(f"Ошибка получения последнего распознавания: {e}")
            return None
    
    def add_system_log(self, level: str, event_type: str, admin_id: Optional[int], 
                      message: str, details: Dict = None, ip_address: str = None,
                      user_agent: str = None):
        """Добавление записи в системный лог"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO system_logs 
                    (level, event_type, admin_id, message, details, ip_address, user_agent)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    level,
                    event_type,
                    admin_id,
                    message,
                    json.dumps(details or {}),
                    ip_address,
                    user_agent
                ))
                
                conn.commit()
                
        except Exception as e:
            # Используем стандартный логгер, чтобы избежать рекурсии
            print(f"Ошибка добавления системного лога: {e}")
    
    def get_recent_system_logs(self, limit: int = 10):
        """Получить последние системные логи"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT l.*, a.username 
                    FROM system_logs l
                    LEFT JOIN admins a ON l.admin_id = a.id
                    ORDER BY l.timestamp DESC
                    LIMIT ?
                ''', (limit,))
                
                logs = cursor.fetchall()
                return [dict(log) for log in logs]
        except Exception as e:
            self.logger.error(f"Ошибка получения системных логов: {e}")
            return []
    
    def create_backup(self, backup_path: str = None) -> bool:
        """Создание резервной копии базы данных"""
        try:
            if not backup_path:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_filename = f"database_backup_{timestamp}.db"
                backup_dir = os.path.join(os.path.dirname(self.db_path), 'backups')
                os.makedirs(backup_dir, exist_ok=True)
                backup_path = os.path.join(backup_dir, backup_filename)
            
            shutil.copy2(self.db_path, backup_path)
            
            self.add_system_log('INFO', 'backup_created', None,
                              f'Создана резервная копия: {backup_path}')
            
            self.logger.info(f"Резервная копия создана: {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка создания резервной копии: {e}")
            return False
    
    def _setup_backup_timer(self):
        """Настройка автоматического резервного копирования"""
        import threading
        
        def backup_worker():
            backup_interval = getattr(config.database, 'backup_interval_hours', 24)
            while True:
                try:
                    time.sleep(backup_interval * 3600)
                    self.create_backup()
                except Exception as e:
                    self.logger.error(f"Ошибка в автоматическом бэкапе: {e}")
        
        backup_thread = threading.Thread(target=backup_worker, daemon=True)
        backup_thread.start()
        self.logger.info("Автоматическое резервное копирование настроено")
    
    def get_database_info(self) -> Dict:
        """Получение информации о базе данных"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                info = {
                    'database_path': self.db_path,
                    'database_size': os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0,
                    'tables': {}
                }
                
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                
                for table in tables:
                    table_name = table[0]
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                    info['tables'][table_name] = count
                
                return info
                
        except Exception as e:
            self.logger.error(f"Ошибка получения информации о БД: {e}")
            return {}
    
    def __del__(self):
        """Деструктор - закрытие всех соединений"""
        try:
            self.close_all_connections()
        except:
            pass