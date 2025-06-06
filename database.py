"""
Модуль работы с базой данных SQLite
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
        
        # Таблица пользователей (администраторов)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')
        
        # Таблица сотрудников
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                designation TEXT,
                department TEXT,
                email TEXT,
                phone TEXT,
                photo_path TEXT,
                face_encoding TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER,
                FOREIGN KEY (created_by) REFERENCES users (id)
            )
        ''')
        
        # Таблица посещаемости
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                attendance_type TEXT DEFAULT 'IN',
                confidence REAL,
                FOREIGN KEY (employee_id) REFERENCES employees (id)
            )
        ''')
        
        # Таблица логов системы
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                event_type TEXT,
                user_id INTEGER,
                details TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
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
        cursor.execute("SELECT id FROM users WHERE username = ?", (DEFAULT_ADMIN_USERNAME,))
        if not cursor.fetchone():
            password_hash = hashlib.sha256(DEFAULT_ADMIN_PASSWORD.encode()).hexdigest()
            cursor.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                (DEFAULT_ADMIN_USERNAME, 'admin@example.com', password_hash)
            )
            conn.commit()
        
        conn.close()
    
    # === Методы для работы с пользователями ===
    
    def authenticate_user(self, username, password):
        """Аутентификация пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        cursor.execute(
            "SELECT id, username, email FROM users WHERE username = ? AND password_hash = ?",
            (username, password_hash)
        )
        user = cursor.fetchone()
        
        if user:
            # Обновление времени последнего входа
            cursor.execute(
                "UPDATE users SET last_login = ? WHERE id = ?",
                (datetime.now(), user[0])
            )
            conn.commit()
            
            # Логирование
            self.add_log('login', user[0], f'User {username} logged in')
        
        conn.close()
        return user
    
    def create_user(self, username, email, password):
        """Создание нового пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        try:
            cursor.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                (username, email, password_hash)
            )
            conn.commit()
            result = True
        except sqlite3.IntegrityError:
            result = False
        
        conn.close()
        return result
    
    # === Методы для работы с сотрудниками ===
    
    def add_employee(self, employee_data, created_by):
        """Добавление нового сотрудника"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO employees 
                (employee_id, full_name, designation, department, email, phone, 
                 photo_path, face_encoding, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                employee_data['employee_id'],
                employee_data['full_name'],
                employee_data.get('designation', ''),
                employee_data.get('department', ''),
                employee_data.get('email', ''),
                employee_data.get('phone', ''),
                employee_data.get('photo_path', ''),
                json.dumps(employee_data.get('face_encoding', [])),
                created_by
            ))
            conn.commit()
            employee_id = cursor.lastrowid
            
            # Логирование
            self.add_log('employee_added', created_by, 
                        f'Added employee: {employee_data["full_name"]}')
            
            result = employee_id
        except sqlite3.IntegrityError:
            result = None
        
        conn.close()
        return result
    
    def get_all_employees(self, active_only=True):
        """Получить всех сотрудников"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM employees"
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY full_name"
        
        cursor.execute(query)
        employees = cursor.fetchall()
        
        # Преобразование в словари
        result = []
        for emp in employees:
            result.append({
                'id': emp[0],
                'employee_id': emp[1],
                'full_name': emp[2],
                'designation': emp[3],
                'department': emp[4],
                'email': emp[5],
                'phone': emp[6],
                'photo_path': emp[7],
                'face_encoding': json.loads(emp[8]) if emp[8] else [],
                'is_active': emp[9],
                'created_at': emp[10]
            })
        
        conn.close()
        return result
    
    def get_employee_by_id(self, employee_id):
        """Получить сотрудника по ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM employees WHERE id = ?", (employee_id,))
        emp = cursor.fetchone()
        
        if emp:
            result = {
                'id': emp[0],
                'employee_id': emp[1],
                'full_name': emp[2],
                'designation': emp[3],
                'department': emp[4],
                'email': emp[5],
                'phone': emp[6],
                'photo_path': emp[7],
                'face_encoding': json.loads(emp[8]) if emp[8] else [],
                'is_active': emp[9],
                'created_at': emp[10]
            }
        else:
            result = None
        
        conn.close()
        return result
    
    def delete_employee(self, employee_id):
        """Удалить сотрудника (мягкое удаление)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE employees SET is_active = 0 WHERE id = ?",
            (employee_id,)
        )
        conn.commit()
        conn.close()
    
    # === Методы для работы с посещаемостью ===
    
    def add_attendance(self, employee_id, attendance_type='IN', confidence=None):
        """Добавить запись посещаемости"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO attendance (employee_id, attendance_type, confidence)
            VALUES (?, ?, ?)
        ''', (employee_id, attendance_type, confidence))
        
        conn.commit()
        attendance_id = cursor.lastrowid
        
        conn.close()
        return attendance_id
    
    def get_last_attendance(self, employee_id):
        """Получить последнюю отметку сотрудника"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT timestamp FROM attendance 
            WHERE employee_id = ? 
            ORDER BY timestamp DESC 
            LIMIT 1
        ''', (employee_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    
    def get_attendance_report(self, date_from=None, date_to=None, employee_id=None):
        """Получить отчет по посещаемости"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT a.*, e.full_name, e.employee_id, e.designation 
            FROM attendance a
            JOIN employees e ON a.employee_id = e.id
            WHERE 1=1
        '''
        params = []
        
        if date_from:
            query += " AND DATE(a.timestamp) >= ?"
            params.append(date_from)
        
        if date_to:
            query += " AND DATE(a.timestamp) <= ?"
            params.append(date_to)
        
        if employee_id:
            query += " AND a.employee_id = ?"
            params.append(employee_id)
        
        query += " ORDER BY a.timestamp DESC"
        
        cursor.execute(query, params)
        records = cursor.fetchall()
        
        result = []
        for rec in records:
            result.append({
                'id': rec[0],
                'employee_id': rec[1],
                'timestamp': rec[2],
                'attendance_type': rec[3],
                'confidence': rec[4],
                'full_name': rec[5],
                'employee_code': rec[6],
                'designation': rec[7]
            })
        
        conn.close()
        return result
    
    def get_today_attendance_count(self):
        """Получить количество отметок за сегодня"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(DISTINCT employee_id) 
            FROM attendance 
            WHERE DATE(timestamp) = DATE('now')
        ''')
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count
    
    # === Методы для работы с логами ===
    
    def add_log(self, event_type, user_id, details):
        """Добавить запись в лог"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO system_logs (event_type, user_id, details)
            VALUES (?, ?, ?)
        ''', (event_type, user_id, details))
        
        conn.commit()
        conn.close()
    
    def get_recent_logs(self, limit=10):
        """Получить последние записи логов"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT l.*, u.username 
            FROM system_logs l
            LEFT JOIN users u ON l.user_id = u.id
            ORDER BY l.timestamp DESC
            LIMIT ?
        ''', (limit,))
        
        logs = cursor.fetchall()
        conn.close()
        
        return logs