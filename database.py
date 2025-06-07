"""
Модуль работы с базой данных SQLite для системы распознавания лиц
"""
import sqlite3
from datetime import datetime
import hashlib
import json
from pathlib import Path
from config import DATABASE_PATH, DEFAULT_ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD

class Database:
    def __init__(self):
        self.db_path = DATABASE_PATH
        self.init_database()
    
    def get_connection(self):
        """Получить соединение с БД"""
        return sqlite3.connect(self.db_path)
    
    def init_database(self):
        """Инициализация базы данных"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Таблица администраторов системы
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')
        
        # Таблица пользователей для распознавания
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
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
                user_id INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                confidence REAL,
                recognition_type TEXT DEFAULT 'SUCCESS',
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Таблица системных логов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                event_type TEXT,
                admin_id INTEGER,
                details TEXT,
                FOREIGN KEY (admin_id) REFERENCES admins (id)
            )
        ''')
        
        conn.commit()
        
        # Создание администратора по умолчанию
        self.create_default_admin()
        
        conn.close()
    
    def create_default_admin(self):
        """Создание администратора по умолчанию"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Проверка существования администратора
        cursor.execute("SELECT id FROM admins WHERE username = ?", (DEFAULT_ADMIN_USERNAME,))
        if not cursor.fetchone():
            password_hash = hashlib.sha256(DEFAULT_ADMIN_PASSWORD.encode()).hexdigest()
            cursor.execute(
                "INSERT INTO admins (username, email, password_hash) VALUES (?, ?, ?)",
                (DEFAULT_ADMIN_USERNAME, 'admin@example.com', password_hash)
            )
            conn.commit()
        
        conn.close()
    
    # === Методы для работы с администраторами ===
    
    def authenticate_admin(self, username, password):
        """Аутентификация администратора"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        cursor.execute(
            "SELECT id, username, email FROM admins WHERE username = ? AND password_hash = ?",
            (username, password_hash)
        )
        admin = cursor.fetchone()
        
        if admin:
            # Обновление времени последнего входа
            cursor.execute(
                "UPDATE admins SET last_login = ? WHERE id = ?",
                (datetime.now(), admin[0])
            )
            conn.commit()
            
            # Логирование
            self.add_system_log('admin_login', admin[0], f'Admin {username} logged in')
            
            result = {
                'id': admin[0],
                'username': admin[1],
                'email': admin[2]
            }
        else:
            result = None
        
        conn.close()
        return result
    
    def create_admin(self, username, email, password):
        """Создание нового администратора"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        try:
            cursor.execute(
                "INSERT INTO admins (username, email, password_hash) VALUES (?, ?, ?)",
                (username, email, password_hash)
            )
            conn.commit()
            result = True
        except sqlite3.IntegrityError:
            result = False
        
        conn.close()
        return result
    
    # === Методы для работы с пользователями ===
    
    def add_user(self, user_data, created_by):
        """Добавление нового пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
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
            conn.commit()
            user_id = cursor.lastrowid
            
            # Логирование
            self.add_system_log('user_added', created_by, 
                        f'Added user: {user_data["full_name"]}')
            
            result = user_id
        except sqlite3.IntegrityError:
            result = None
        
        conn.close()
        return result
    
    def get_all_users(self, active_only=True):
        """Получить всех пользователей"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM users"
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY full_name"
        
        cursor.execute(query)
        users = cursor.fetchall()
        
        # Преобразование в словари
        result = []
        for user in users:
            result.append({
                'id': user[0],
                'user_id': user[1],
                'full_name': user[2],
                'photo_path': user[3],
                'face_encoding': json.loads(user[4]) if user[4] else [],
                'is_active': user[5],
                'created_at': user[6]
            })
        
        conn.close()
        return result
    
    def get_user_by_id(self, user_id):
        """Получить пользователя по ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        
        if user:
            result = {
                'id': user[0],
                'user_id': user[1],
                'full_name': user[2],
                'photo_path': user[3],
                'face_encoding': json.loads(user[4]) if user[4] else [],
                'is_active': user[5],
                'created_at': user[6]
            }
        else:
            result = None
        
        conn.close()
        return result
    
    def delete_user(self, user_id):
        """Удалить пользователя (мягкое удаление)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE users SET is_active = 0 WHERE id = ?",
            (user_id,)
        )
        conn.commit()
        conn.close()
    
    # === Методы для работы с логами распознавания ===
    
    def add_recognition_log(self, user_id, confidence, recognition_type='SUCCESS'):
        """Добавить лог распознавания"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO recognition_logs (user_id, confidence, recognition_type)
            VALUES (?, ?, ?)
        ''', (user_id, confidence, recognition_type))
        
        conn.commit()
        log_id = cursor.lastrowid
        
        conn.close()
        return log_id
    
    def get_last_recognition(self, user_id):
        """Получить последнее распознавание пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT timestamp FROM recognition_logs 
            WHERE user_id = ? 
            ORDER BY timestamp DESC 
            LIMIT 1
        ''', (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    
    def get_recognition_report(self, date_from=None, date_to=None, user_id=None):
        """Получить отчет по распознаванию"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT r.*, u.full_name, u.user_id 
            FROM recognition_logs r
            JOIN users u ON r.user_id = u.id
            WHERE 1=1
        '''
        params = []
        
        if date_from:
            query += " AND DATE(r.timestamp) >= ?"
            params.append(date_from)
        
        if date_to:
            query += " AND DATE(r.timestamp) <= ?"
            params.append(date_to)
        
        if user_id:
            query += " AND r.user_id = ?"
            params.append(user_id)
        
        query += " ORDER BY r.timestamp DESC LIMIT 100"
        
        cursor.execute(query, params)
        records = cursor.fetchall()
        
        result = []
        for rec in records:
            result.append({
                'id': rec[0],
                'user_id': rec[1],
                'timestamp': rec[2],
                'confidence': rec[3],
                'recognition_type': rec[4],
                'full_name': rec[5],
                'user_code': rec[6]
            })
        
        conn.close()
        return result
    
    def get_today_recognition_count(self):
        """Получить количество распознаваний за сегодня"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) 
            FROM recognition_logs 
            WHERE DATE(timestamp) = DATE('now')
        ''')
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count
    
    def get_unique_users_today(self):
        """Получить количество уникальных пользователей за сегодня"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(DISTINCT user_id) 
            FROM recognition_logs 
            WHERE DATE(timestamp) = DATE('now')
        ''')
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count
    
    # === Методы для работы с системными логами ===
    
    def add_system_log(self, event_type, admin_id, details):
        """Добавить запись в системный лог"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO system_logs (event_type, admin_id, details)
            VALUES (?, ?, ?)
        ''', (event_type, admin_id, details))
        
        conn.commit()
        conn.close()
    
    def get_recent_system_logs(self, limit=10):
        """Получить последние системные логи"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT l.*, a.username 
            FROM system_logs l
            LEFT JOIN admins a ON l.admin_id = a.id
            ORDER BY l.timestamp DESC
            LIMIT ?
        ''', (limit,))
        
        logs = cursor.fetchall()
        conn.close()
        
        return logs