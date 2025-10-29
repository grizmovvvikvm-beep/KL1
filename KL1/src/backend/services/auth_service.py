from . import BaseService
from ..models.user import UserModel
from ..models.group import GroupModel
from ..utils.radius import RadiusClient
import logging

logger = logging.getLogger(__name__)

class AuthService(BaseService):
    """Сервис для аутентификации и авторизации"""
    
    def __init__(self):
        self.radius_client = None
    
    def login(self, username, password, use_radius=False):
        """Аутентификация пользователя"""
        try:
            # Проверка обязательных полей
            self.validate_required_fields({'username': username, 'password': password}, ['username', 'password'])
            
            # Проверка блокировки аккаунта
            if UserModel.is_locked(username):
                return None, "Account temporarily locked. Try again later."
            
            # RADIUS аутентификация
            if use_radius and self.radius_client:
                radius_result = self.radius_client.authenticate(username, password)
                if not radius_result['success']:
                    UserModel.update_login_attempts(username, False)
                    return None, f"RADIUS authentication failed: {radius_result['message']}"
            
            # Локальная аутентификация
            is_valid, user = UserModel.verify_password(username, password)
            
            if not is_valid:
                UserModel.update_login_attempts(username, False)
                return None, "Invalid credentials"
            
            # Успешная аутентификация
            UserModel.update_login_attempts(username, True)
            
            user_data = {
                'id': user['id'],
                'username': user['username'],
                'role': user['role'],
                'full_name': user['full_name'],
                'email': user['email']
            }
            
            logger.info(f"User logged in successfully: {username}")
            return user_data, None
            
        except ValueError as e:
            return None, str(e)
        except Exception as e:
            logger.error(f"Login error for user {username}: {str(e)}")
            return None, "Authentication service error"
    
    def change_password(self, user_id, current_password, new_password):
        """Смена пароля пользователя"""
        try:
            self.validate_required_fields({
                'current_password': current_password,
                'new_password': new_password
            }, ['current_password', 'new_password'])
            
            self.validate_password_strength(new_password)
            
            # Получить пользователя
            user = UserModel.get_by_id(user_id)
            if not user:
                return False, "User not found"
            
            # Проверить текущий пароль
            is_valid, _ = UserModel.verify_password(user['username'], current_password)
            if not is_valid:
                return False, "Current password is incorrect"
            
            # Обновить пароль
            success = UserModel.change_password(user_id, new_password)
            if success:
                logger.info(f"Password changed for user ID: {user_id}")
                return True, "Password changed successfully"
            else:
                return False, "Failed to change password"
                
        except ValueError as e:
            return False, str(e)
        except Exception as e:
            logger.error(f"Password change error for user {user_id}: {str(e)}")
            return False, "Password change service error"
    
    def initialize_radius(self, radius_config):
        """Инициализация RADIUS клиента"""
        try:
            if radius_config.get('enabled', False):
                self.radius_client = RadiusClient(
                    server=radius_config.get('server', 'localhost'),
                    secret=radius_config.get('secret', ''),
                    port=int(radius_config.get('port', 1812)),
                    timeout=int(radius_config.get('timeout', 5))
                )
                logger.info("RADIUS client initialized successfully")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to initialize RADIUS client: {str(e)}")
            self.radius_client = None
            return False