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
                    interface_type VARCHAR(10) DEFAULT 'tun',
                    topology VARCHAR(20) DEFAULT 'subnet',
                    tls_auth BOOLEAN DEFAULT 0,
                    crl_enabled BOOLEAN DEFAULT 0,
                    verify_client BOOLEAN DEFAULT 1,
                    ocsp_enabled BOOLEAN DEFAULT 0,
                    cert_depth INTEGER DEFAULT 1,
                    renegotiate_time INTEGER DEFAULT 3600,
                    auth_token_lifetime INTEGER DEFAULT 3600,
                    redirect_gateway BOOLEAN DEFAULT 0,
                    dns_servers TEXT DEFAULT '',
                    ntp_servers TEXT DEFAULT '',
                    push_options TEXT DEFAULT '',
                    openvpn_options TEXT DEFAULT '',
                    local_network TEXT DEFAULT '',
                    verify_remote_cert BOOLEAN DEFAULT 1,
                    strict_user_cn BOOLEAN DEFAULT 0,
                    remote_random BOOLEAN DEFAULT 0,
                    client_to_client BOOLEAN DEFAULT 0,
                    block_ipv6 BOOLEAN DEFAULT 0,
                    duplicate_cn BOOLEAN DEFAULT 0,
                    float BOOLEAN DEFAULT 0,
                    passtos BOOLEAN DEFAULT 0,
                    persist_remote_ip BOOLEAN DEFAULT 0,
                    route_noexec BOOLEAN DEFAULT 0,
                    route_nopull BOOLEAN DEFAULT 0,
                    explicit_exit_notify BOOLEAN DEFAULT 1,
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
                    interface_type VARCHAR(10) DEFAULT 'tun',
                    topology VARCHAR(20) DEFAULT 'subnet',
                    tls_auth BOOLEAN DEFAULT FALSE,
                    crl_enabled BOOLEAN DEFAULT FALSE,
                    verify_client BOOLEAN DEFAULT TRUE,
                    ocsp_enabled BOOLEAN DEFAULT FALSE,
                    cert_depth INTEGER DEFAULT 1,
                    renegotiate_time INTEGER DEFAULT 3600,
                    auth_token_lifetime INTEGER DEFAULT 3600,
                    redirect_gateway BOOLEAN DEFAULT FALSE,
                    dns_servers TEXT DEFAULT '',
                    ntp_servers TEXT DEFAULT '',
                    push_options TEXT DEFAULT '',
                    openvpn_options TEXT DEFAULT '',
                    local_network TEXT DEFAULT '',
                    verify_remote_cert BOOLEAN DEFAULT TRUE,
                    strict_user_cn BOOLEAN DEFAULT FALSE,
                    remote_random BOOLEAN DEFAULT FALSE,
                    client_to_client BOOLEAN DEFAULT FALSE,
                    block_ipv6 BOOLEAN DEFAULT FALSE,
                    duplicate_cn BOOLEAN DEFAULT FALSE,
                    float BOOLEAN DEFAULT FALSE,
                    passtos BOOLEAN DEFAULT FALSE,
                    persist_remote_ip BOOLEAN DEFAULT FALSE,
                    route_noexec BOOLEAN DEFAULT FALSE,
                    route_nopull BOOLEAN DEFAULT FALSE,
                    explicit_exit_notify BOOLEAN DEFAULT TRUE,
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
                    certificate_data TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    revoked_at TIMESTAMP NULL,
                    FOREIGN KEY (vpn_instance_id) REFERENCES vpn_instances(id) ON DELETE CASCADE
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
                    certificate_data TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    revoked_at TIMESTAMP NULL,
                    FOREIGN KEY (vpn_instance_id) REFERENCES vpn_instances(id) ON DELETE CASCADE
                )
            ''')
        
        # Таблица для отслеживания активных сессий
        if is_sqlite:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS vpn_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vpn_instance_id INTEGER REFERENCES vpn_instances(id),
                    client_name VARCHAR(100),
                    client_ip VARCHAR(45),
                    connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    disconnected_at TIMESTAMP NULL,
                    bytes_received INTEGER DEFAULT 0,
                    bytes_sent INTEGER DEFAULT 0,
                    FOREIGN KEY (vpn_instance_id) REFERENCES vpn_instances(id) ON DELETE CASCADE
                )
            ''')
        else:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS vpn_sessions (
                    id SERIAL PRIMARY KEY,
                    vpn_instance_id INTEGER REFERENCES vpn_instances(id),
                    client_name VARCHAR(100),
                    client_ip VARCHAR(45),
                    connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    disconnected_at TIMESTAMP NULL,
                    bytes_received INTEGER DEFAULT 0,
                    bytes_sent INTEGER DEFAULT 0,
                    FOREIGN KEY (vpn_instance_id) REFERENCES vpn_instances(id) ON DELETE CASCADE
                )
            ''')
        
        # Таблица для API ключей
        if is_sqlite:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER REFERENCES users(id),
                    api_key VARCHAR(64) UNIQUE NOT NULL,
                    description TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP NULL,
                    expires_at TIMESTAMP NULL
                )
            ''')
        else:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS api_keys (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id),
                    api_key VARCHAR(64) UNIQUE NOT NULL,
                    description TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP NULL,
                    expires_at TIMESTAMP NULL
                )
            ''')
        
        # Таблица для системных логов
        if is_sqlite:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level VARCHAR(20) NOT NULL,
                    module VARCHAR(100),
                    message TEXT NOT NULL,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
        else:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS system_logs (
                    id SERIAL PRIMARY KEY,
                    level VARCHAR(20) NOT NULL,
                    module VARCHAR(100),
                    message TEXT NOT NULL,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
        
        # Создаем тестового пользователя для разработки
        if is_sqlite and config.is_development():
            from werkzeug.security import generate_password_hash
            try:
                cur.execute(
                    "INSERT OR IGNORE INTO users (username, password_hash, role, email, full_name) VALUES (?, ?, ?, ?, ?)",
                    ('admin', generate_password_hash('admin'), 'admin', 'admin@kurslight.local', 'System Administrator')
                )
                
                # Создаем тестовый VPN инстанс
                cur.execute('''
                    INSERT OR IGNORE INTO vpn_instances 
                    (name, description, port, protocol, subnet, interface_type, topology, max_clients) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    'default-vpn', 
                    'Default VPN Server for testing', 
                    1194, 
                    'udp', 
                    '10.8.0.0/24', 
                    'tun', 
                    'subnet', 
                    100
                ))
                
                logger.info("Test admin user and default VPN instance created for development")
            except Exception as e:
                logger.warning(f"Could not create test data: {str(e)}")
        
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
        
        # Проверяем тип БД
        is_sqlite = 'sqlite' in str(conn)
        
        if is_sqlite:
            cur.execute("SELECT 1")
        else:
            cur.execute("SELECT 1")
            
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result[0] == 1
    except Exception as e:
        logger.error(f"Database connection test failed: {str(e)}")
        return False

def execute_query(query, params=None, fetch=False):
    """Выполнить произвольный SQL запрос"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(query, params or ())
        
        if fetch:
            result = cur.fetchall()
        else:
            result = cur.rowcount
            
        conn.commit()
        return result
        
    except Exception as e:
        logger.error(f"Query execution failed: {str(e)}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def get_table_info(table_name):
    """Получить информацию о таблице"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        is_sqlite = 'sqlite' in str(conn)
        
        if is_sqlite:
            cur.execute(f"PRAGMA table_info({table_name})")
            columns = cur.fetchall()
            result = []
            for col in columns:
                result.append({
                    'name': col[1],
                    'type': col[2],
                    'not_null': bool(col[3]),
                    'default_value': col[4],
                    'primary_key': bool(col[5])
                })
        else:
            cur.execute('''
                SELECT column_name, data_type, is_nullable, column_default 
                FROM information_schema.columns 
                WHERE table_name = %s
            ''', (table_name,))
            columns = cur.fetchall()
            result = []
            for col in columns:
                result.append({
                    'name': col[0],
                    'type': col[1],
                    'is_nullable': col[2] == 'YES',
                    'default_value': col[3]
                })
        
        cur.close()
        conn.close()
        return result
        
    except Exception as e:
        logger.error(f"Failed to get table info for {table_name}: {str(e)}")
        return []

def backup_database(backup_path=None):
    """Создать резервную копию базы данных"""
    try:
        if backup_path is None:
            backup_path = config.BACKUPS_DIR / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        
        conn = get_db_connection()
        is_sqlite = 'sqlite' in str(conn)
        
        if is_sqlite:
            # Для SQLite просто копируем файл
            import shutil
            db_path = config.BASE_DIR / 'kurslight.db'
            shutil.copy2(db_path, backup_path)
        else:
            # Для PostgreSQL используем pg_dump
            import subprocess
            env = os.environ.copy()
            env['PGPASSWORD'] = config.DB_PASSWORD
            
            subprocess.run([
                'pg_dump',
                '-h', config.DB_HOST,
                '-p', config.DB_PORT,
                '-U', config.DB_USER,
                '-d', config.DB_NAME,
                '-f', str(backup_path),
                '--clean'
            ], env=env, check=True)
        
        logger.info(f"Database backup created: {backup_path}")
        return True, backup_path
        
    except Exception as e:
        logger.error(f"Database backup failed: {str(e)}")
        return False, str(e)

def get_database_size():
    """Получить размер базы данных"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        is_sqlite = 'sqlite' in str(conn)
        
        if is_sqlite:
            cur.execute("SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size()")
            size_bytes = cur.fetchone()[0]
        else:
            cur.execute("SELECT pg_database_size(%s)", (config.DB_NAME,))
            size_bytes = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        # Конвертируем в читаемый формат
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        
        return f"{size_bytes:.2f} TB"
        
    except Exception as e:
        logger.error(f"Failed to get database size: {str(e)}")
        return "Unknown"

# Импорт здесь чтобы избежать циклических импортов
from datetime import datetime