import os
import psycopg2
import logging
from ..config import config

logger = logging.getLogger(__name__)

def get_db_connection():
    """Получить соединение с БД"""
    try:
        # Для development среды используем SQLite если нет пароля БД
        if config.is_development() and not config.DB_PASSWORD and 'sqlite' not in config.DB_URL:
            logger.info("Using SQLite for development")
            return _get_sqlite_connection()
            
        return psycopg2.connect(**config.DB_CONFIG)
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        raise

def _get_sqlite_connection():
    """Получить соединение с SQLite (для разработки)"""
    try:
        import sqlite3
        db_path = config.BASE_DIR / 'kurslight.db'
        return sqlite3.connect(str(db_path))
    except ImportError:
        logger.error("SQLite3 not available")
        raise

def init_db():
    """Инициализация таблиц БД"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Определяем тип БД
        is_sqlite = 'sqlite' in str(conn)
        
        # Таблица пользователей
        if is_sqlite:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    email VARCHAR(100),
                    full_name VARCHAR(100),
                    role VARCHAR(20) DEFAULT 'user',
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            ''')
        else:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    email VARCHAR(100),
                    full_name VARCHAR(100),
                    role VARCHAR(20) DEFAULT 'user',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            ''')
        
        # Таблица VPN инстансов
        if is_sqlite:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS vpn_instances (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(100) UNIQUE NOT NULL,
                    description TEXT,
                    config TEXT,
                    status VARCHAR(20) DEFAULT 'stopped',
                    port INTEGER DEFAULT 1194,
                    protocol VARCHAR(10) DEFAULT 'udp',
                    subnet VARCHAR(20) DEFAULT '10.8.0.0/24',
                    active_clients INTEGER DEFAULT 0,
                    max_clients INTEGER DEFAULT 100,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
        else:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS vpn_instances (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) UNIQUE NOT NULL,
                    description TEXT,
                    config TEXT,
                    status VARCHAR(20) DEFAULT 'stopped',
                    port INTEGER DEFAULT 1194,
                    protocol VARCHAR(10) DEFAULT 'udp',
                    subnet VARCHAR(20) DEFAULT '10.8.0.0/24',
                    active_clients INTEGER DEFAULT 0,
                    max_clients INTEGER DEFAULT 100,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
        
        # Таблица клиентов VPN
        if is_sqlite:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS vpn_clients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER REFERENCES users(id),
                    vpn_instance_id INTEGER REFERENCES vpn_instances(id),
                    client_name VARCHAR(100),
                    config_file TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
        else:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS vpn_clients (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    vpn_instance_id INTEGER REFERENCES vpn_instances(id),
                    client_name VARCHAR(100),
                    config_file TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
        
        # Создаем тестового пользователя для разработки
        if is_sqlite and config.is_development():
            from werkzeug.security import generate_password_hash
            try:
                cur.execute(
                    "INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                    ('admin', generate_password_hash('admin'), 'admin')
                )
                logger.info("Test admin user created for development")
            except Exception as e:
                logger.warning(f"Could not create test user: {str(e)}")
        
        conn.commit()
        logger.info("Database tables created successfully")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Database initialization failed: {str(e)}")
        raise
    finally:
        cur.close()
        conn.close()

def test_connection():
    """Протестировать соединение с БД"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result[0] == 1
    except Exception as e:
        logger.error(f"Database connection test failed: {str(e)}")
        return False