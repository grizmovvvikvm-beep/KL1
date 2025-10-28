from .base_model import BaseModel
import logging

logger = logging.getLogger(__name__)

class UserModel(BaseModel):
    """Модель для работы с пользователями"""
    
    FIELDS = ['id', 'username', 'password_hash', 'email', 'full_name', 'role', 'is_active', 'created_at', 'last_login']
    
    @classmethod
    def create(cls, username, password_hash, email='', full_name='', role='user'):
        """Создать нового пользователя"""
        query = '''
            INSERT INTO users (username, password_hash, email, full_name, role) 
            VALUES (%s, %s, %s, %s, %s) RETURNING id
        '''
        result = cls._execute_query(query, (username, password_hash, email, full_name, role), fetch=True)
        return result[0][0] if result else None
    
    @classmethod
    def get_by_id(cls, user_id):
        """Получить пользователя по ID"""
        return cls._get_by_id('users', user_id, cls.FIELDS)
    
    @classmethod
    def get_by_username(cls, username):
        """Получить пользователя по имени"""
        query = 'SELECT * FROM users WHERE username = %s'
        result = cls._execute_query(query, (username,), fetch=True)
        return cls._dict_to_model(result[0], cls.FIELDS) if result else None
    
    @classmethod
    def get_all(cls):
        """Получить всех пользователей"""
        return cls._get_all('users', cls.FIELDS, 'username')
    
    @classmethod
    def update_last_login(cls, user_id):
        """Обновить время последнего входа"""
        query = "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s"
        return cls._execute_query(query, (user_id,)) > 0
    
    @classmethod
    def update_password(cls, user_id, new_password_hash):
        """Обновить пароль пользователя"""
        query = "UPDATE users SET password_hash = %s WHERE id = %s"
        return cls._execute_query(query, (new_password_hash, user_id)) > 0
    
    @classmethod
    def deactivate(cls, user_id):
        """Деактивировать пользователя"""
        query = "UPDATE users SET is_active = FALSE WHERE id = %s"
        return cls._execute_query(query, (user_id,)) > 0
    
    @classmethod
    def activate(cls, user_id):
        """Активировать пользователя"""
        query = "UPDATE users SET is_active = TRUE WHERE id = %s"
        return cls._execute_query(query, (user_id,)) > 0