import os
import psycopg2
import logging
from datetime import datetime
from pathlib import Path
from ..config import config

logger = logging.getLogger(__name__)

def get_db_connection():
    try:
        return psycopg2.connect(**config.DB_CONFIG)
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        raise

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
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
                revoked_at TIMESTAMP NULL
            )
        ''')
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
        # firewall alias table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS firewall_aliases (
                id SERIAL PRIMARY KEY,
                enabled BOOLEAN DEFAULT TRUE,
                name VARCHAR(128) UNIQUE NOT NULL,
                type VARCHAR(32) DEFAULT 'Host',
                hosts TEXT,
                categories TEXT,
                content TEXT,
                stats JSONB DEFAULT '{}'::jsonb,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # firewall rules table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS firewall_rules (
                id SERIAL PRIMARY KEY,
                enabled BOOLEAN DEFAULT TRUE,
                name VARCHAR(128) NOT NULL,
                action VARCHAR(16) NOT NULL, -- allow/deny
                protocol VARCHAR(16) DEFAULT 'any',
                source TEXT,
                destination TEXT,
                vpn_instance_id INTEGER REFERENCES vpn_instances(id) ON DELETE SET NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
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

def execute_query(query, params=None, fetch=False):
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
    try:
        conn = get_db_connection()
        cur = conn.cursor()
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
    try:
        if backup_path is None:
            backup_path = Path(config.BACKUPS_DIR) / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        import subprocess
        env = os.environ.copy()
        env['PGPASSWORD'] = config.DB_PASSWORD
        subprocess.run([
            'pg_dump',
            '-h', str(config.DB_HOST),
            '-p', str(config.DB_PORT),
            '-U', config.DB_USER,
            '-d', config.DB_NAME,
            '-f', str(backup_path),
            '--clean'
        ], env=env, check=True)
        logger.info(f"Database backup created: {backup_path}")
        return True, str(backup_path)
    except Exception as e:
        logger.error(f"Database backup failed: {str(e)}")
        return False, str(e)

def get_database_size():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT pg_database_size(%s)", (config.DB_NAME,))
        size_bytes = cur.fetchone()[0]
        cur.close()
        conn.close()
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"
    except Exception as e:
        logger.error(f"Failed to get database size: {str(e)}")
        return "Unknown"