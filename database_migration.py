"""
Исправленная система миграций базы данных
"""
import sqlite3
import logging
import os
import hashlib
import json
from datetime import datetime
from typing import List, Dict

class DatabaseMigration:
    """Класс для выполнения миграций базы данных"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
    def get_connection(self):
        """Получить соединение с БД"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
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
    
    def get_current_version(self) -> int:
        """Получить текущую версию схемы БД"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем, существует ли таблица версий
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='schema_version'
                """)
                
                if not cursor.fetchone():
                    # Если таблицы версий нет, создаем её
                    cursor.execute("""
                        CREATE TABLE schema_version (
                            version INTEGER PRIMARY KEY,
                            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            description TEXT
                        )
                    """)
                    
                    # Определяем версию по существующим колонкам
                    cursor.execute("PRAGMA table_info(admins)")
                    columns = [col[1] for col in cursor.fetchall()]
                    
                    if 'salt' in columns:
                        version = 2  # Новая схема
                    else:
                        version = 1  # Старая схема
                    
                    cursor.execute("""
                        INSERT INTO schema_version (version, description)
                        VALUES (?, ?)
                    """, (version, f"Initial version detected: {version}"))
                    
                    conn.commit()
                    return version
                
                # Получаем последнюю версию
                cursor.execute("SELECT MAX(version) FROM schema_version")
                result = cursor.fetchone()
                return result[0] if result[0] else 1
                
        except Exception as e:
            self.logger.error(f"Ошибка получения версии БД: {e}")
            return 1
    
    def apply_migration(self, version: int, description: str, sql_commands: List[str]):
        """Применить миграцию"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                self.logger.info(f"Применение миграции {version}: {description}")
                
                for command in sql_commands:
                    if command.strip():
                        try:
                            cursor.execute(command)
                        except Exception as e:
                            self.logger.warning(f"Ошибка выполнения команды: {e}")
                            self.logger.warning(f"Команда: {command}")
                            # Продолжаем выполнение остальных команд
                
                # Записываем версию
                cursor.execute("""
                    INSERT INTO schema_version (version, description)
                    VALUES (?, ?)
                """, (version, description))
                
                conn.commit()
                self.logger.info(f"Миграция {version} успешно применена")
                
        except Exception as e:
            self.logger.error(f"Ошибка применения миграции {version}: {e}")
            raise
    
    def migrate_to_v2(self):
        """Миграция со старой схемы (v1) на новую (v2)"""
        
        # Проверяем, нужна ли миграция
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(admins)")
                columns = [col[1] for col in cursor.fetchall()]
                
                if 'salt' in columns:
                    self.logger.info("База данных уже обновлена до версии 2")
                    return
        except Exception as e:
            self.logger.error(f"Ошибка проверки схемы: {e}")
            return
        
        migration_commands = []
        
        # 1. Создаем резервную копию старой таблицы admins
        migration_commands.extend([
            "CREATE TABLE admins_backup AS SELECT * FROM admins",
        ])
        
        # 2. Удаляем старую таблицу admins
        migration_commands.append("DROP TABLE admins")
        
        # 3. Создаем новую таблицу admins с расширенной схемой
        migration_commands.append("""
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
        """)
        
        # 4. Мигрируем данные из резервной копии (исправленный запрос)
        migration_commands.extend([
            """
            INSERT INTO admins (id, username, email, password_hash, salt, created_at, last_login, permissions)
            SELECT 
                id, 
                username, 
                email, 
                password_hash,
                hex(randomblob(16)) as salt,
                created_at,
                last_login,
                '{"admin": true, "manage_users": true, "view_reports": true}' as permissions
            FROM admins_backup
            """,
            
            # Удаляем резервную копию
            "DROP TABLE admins_backup"
        ])
        
        # 5. Добавляем новые колонки в существующие таблицы (безопасно)
        new_columns_users = [
            "ALTER TABLE users ADD COLUMN email TEXT DEFAULT ''",
            "ALTER TABLE users ADD COLUMN phone TEXT DEFAULT ''", 
            "ALTER TABLE users ADD COLUMN department TEXT DEFAULT ''",
            "ALTER TABLE users ADD COLUMN position TEXT DEFAULT ''",
            "ALTER TABLE users ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "ALTER TABLE users ADD COLUMN notes TEXT DEFAULT ''"
        ]
        
        new_columns_recognition = [
            "ALTER TABLE recognition_logs ADD COLUMN face_location TEXT",
            "ALTER TABLE recognition_logs ADD COLUMN processing_time REAL",
            "ALTER TABLE recognition_logs ADD COLUMN camera_id INTEGER DEFAULT 0", 
            "ALTER TABLE recognition_logs ADD COLUMN additional_data TEXT DEFAULT '{}'"
        ]
        
        # Добавляем команды, которые могут не выполниться если колонки уже есть
        migration_commands.extend(new_columns_users)
        migration_commands.extend(new_columns_recognition)
        
        # 6. Создаем новые таблицы
        migration_commands.extend([
            """
            CREATE TABLE IF NOT EXISTS system_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT NOT NULL,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_by INTEGER,
                FOREIGN KEY (updated_by) REFERENCES admins (id)
            )
            """,
            
            # Создаем индексы для оптимизации
            "CREATE INDEX IF NOT EXISTS idx_users_active ON users (is_active)",
            "CREATE INDEX IF NOT EXISTS idx_users_user_id ON users (user_id)",
            "CREATE INDEX IF NOT EXISTS idx_recognition_timestamp ON recognition_logs (timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_recognition_user ON recognition_logs (user_id)",
            "CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp ON system_logs (timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_system_logs_event ON system_logs (event_type)"
        ])
        
        # Применяем миграцию
        self.apply_migration(2, "Обновление до новой схемы БД", migration_commands)
        
        # Обновляем пароли существующих пользователей для совместимости
        self._update_admin_passwords()
    
    def _update_admin_passwords(self):
        """Обновляем пароли администраторов с новой системой хеширования"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Получаем всех администраторов
                cursor.execute("SELECT id, username, password_hash, salt FROM admins")
                admins = cursor.fetchall()
                
                for admin in admins:
                    admin_id, username, old_hash, salt = admin
                    
                    # Для администратора по умолчанию, восстанавливаем пароль
                    if username == 'admin':
                        new_salt = os.urandom(32).hex()
                        new_hash = self._hash_password('admin123', new_salt)
                        
                        cursor.execute("""
                            UPDATE admins 
                            SET password_hash = ?, salt = ?, permissions = ?
                            WHERE id = ?
                        """, (
                            new_hash, 
                            new_salt,
                            json.dumps({'admin': True, 'manage_users': True, 'view_reports': True}),
                            admin_id
                        ))
                
                conn.commit()
                self.logger.info("Пароли администраторов обновлены")
                
        except Exception as e:
            self.logger.error(f"Ошибка обновления паролей: {e}")
    
    def run_migrations(self):
        """Запуск всех необходимых миграций"""
        current_version = self.get_current_version()
        self.logger.info(f"Текущая версия БД: {current_version}")
        
        if current_version < 2:
            self.logger.info("Необходимо обновление до версии 2")
            self.migrate_to_v2()
            self.logger.info("База данных успешно обновлена до версии 2")
        else:
            self.logger.info("База данных актуальна")

def migrate_database(db_path: str):
    """Функция для запуска миграций"""
    migration = DatabaseMigration(db_path)
    migration.run_migrations()