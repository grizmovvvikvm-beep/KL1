from ..utils.database import get_db_connection
import bcrypt
from datetime import datetime

class UserModel:
    @staticmethod
    def create_user(username, password, role='user', full_name='', email='', is_active=True):
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            cur.execute('''
                INSERT INTO users (username, password_hash, role, full_name, email, is_active) 
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
            ''', (username, password_hash, role, full_name, email, is_active))
            
            user_id = cur.fetchone()[0]
            conn.commit()
            return user_id
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cur.close()
            conn.close()
    
    @staticmethod
    def get_user_by_username(username):
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute('''
            SELECT id, username, password_hash, role, full_name, email, 
                   created_at, is_active, last_login, failed_attempts, locked_until
            FROM users WHERE username = %s
        ''', (username,))
        
        user = cur.fetchone()
        cur.close()
        conn.close()
        return user
    
    @staticmethod
    def update_login_attempts(username, success):
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            if success:
                cur.execute('''
                    UPDATE users 
                    SET failed_attempts = 0, locked_until = NULL, last_login = CURRENT_TIMESTAMP 
                    WHERE username = %s
                ''', (username,))
            else:
                cur.execute('''
                    UPDATE users SET failed_attempts = failed_attempts + 1 
                    WHERE username = %s RETURNING failed_attempts
                ''', (username,))
                
                result = cur.fetchone()
                if result and result[0] >= 5:
                    lock_time = datetime.now() + timedelta(minutes=30)
                    cur.execute('''
                        UPDATE users SET locked_until = %s WHERE username = %s
                    ''', (lock_time, username))
            
            conn.commit()
        finally:
            cur.close()
            conn.close()