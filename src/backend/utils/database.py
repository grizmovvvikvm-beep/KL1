from ..config import config
import psycopg2

def get_db_connection():
    return psycopg2.connect(**config.DB_CONFIG)

def init_db():
    """Инициализация таблиц БД"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Перенести сюда SQL из оригинального init_db()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                -- ... остальные таблицы
            )
        ''')
        conn.commit()
    finally:
        cur.close()
        conn.close()