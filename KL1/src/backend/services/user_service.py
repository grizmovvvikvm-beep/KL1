from . import BaseService
from ..models.user import UserModel
from ..models.group import GroupModel
from ..utils.radius import create_radius_user
import logging

logger = logging.getLogger(__name__)

class UserService(BaseService):
    """Сервис для управления пользователями"""
    
    def get_all_users(self, include_groups=True, include_certificates=True):
        """Получить всех пользователей с дополнительной информацией"""
        try:
            users = UserModel.get_all()
            result = []
            
            for user in users:
                user_data = {
                    'id': user['id'],
                    'username': user['username'],
                    'role': user['role'],
                    'full_name': user['full_name'],
                    'email': user['email'],
                    'created_at': user['created_at'].isoformat() if user['created_at'] else None,
                    'is_active': user['is_active'],
                    'last_login': user['last_login'].isoformat() if user['last_login'] else None,
                    'failed_attempts': user['failed_attempts']
                }
                
                # Добавить группы пользователя
                if include_groups:
                    user_data['groups'] = self._get_user_groups(user['id'])
                
                # Добавить информацию о сертификатах
                if include_certificates:
                    user_data['certificate_count'] = self._get_user_certificate_count(user['id'])
                
                result.append(user_data)
            
            return result, None
            
        except Exception as e:
            logger.error(f"Error getting all users: {str(e)}")
            return None, "Failed to retrieve users"
    
    def create_user(self, user_data):
        """Создать нового пользователя"""
        try:
            # Валидация
            self.validate_required_fields(user_data, ['username', 'password', 'role'])
            self.validate_password_strength(user_data['password'])
            
            # Проверить существование username
            existing_user = UserModel.get_by_username(user_data['username'])
            if existing_user:
                raise ValueError("Username already exists")
            
            # Создать пользователя
            user_id = UserModel.create(
                username=user_data['username'],
                password=user_data['password'],
                role=user_data['role'],
                full_name=user_data.get('full_name', ''),
                email=user_data.get('email', ''),
                is_active=user_data.get('is_active', True)
            )
            
            if not user_id:
                raise Exception("Failed to create user")
            
            # Добавить в группы
            if 'groups' in user_data and isinstance(user_data['groups'], list):
                for group_name in user_data['groups']:
                    group = GroupModel.get_by_name(group_name)
                    if group:
                        GroupModel.add_user_to_group(user_id, group['id'])
            
            # Создать RADIUS аккаунт если требуется
            if user_data.get('create_radius_account', False):
                create_radius_user(user_data['username'], user_data['password'])
            
            logger.info(f"User created successfully: {user_data['username']} (ID: {user_id})")
            return user_id, None
            
        except ValueError as e:
            return None, str(e)
        except Exception as e:
            logger.error(f"Error creating user {user_data.get('username', 'unknown')}: {str(e)}")
            return None, "Failed to create user"
    
    def update_user(self, user_id, update_data):
        """Обновить данные пользователя"""
        try:
            # Проверить существование пользователя
            user = UserModel.get_by_id(user_id)
            if not user:
                return False, "User not found"
            
            # Запретить изменение роли admin пользователя
            if user['username'] == 'admin' and 'role' in update_data and update_data['role'] != 'admin':
                return False, "Cannot change admin user role"
            
            # Обновить основные данные
            allowed_fields = ['full_name', 'email', 'role', 'is_active']
            update_fields = {k: v for k, v in update_data.items() if k in allowed_fields}
            
            if update_fields:
                success = UserModel.update(user_id, **update_fields)
                if not success:
                    return False, "Failed to update user data"
            
            # Обновить группы
            if 'groups' in update_data:
                self._update_user_groups(user_id, update_data['groups'])
            
            # Обновить RADIUS статус
            if 'radius_enabled' in update_data:
                self._update_radius_status(user['username'], update_data['radius_enabled'])
            
            logger.info(f"User updated successfully: {user['username']} (ID: {user_id})")
            return True, None
            
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {str(e)}")
            return False, "Failed to update user"
    
    def delete_user(self, user_id):
        """Удалить пользователя"""
        try:
            user = UserModel.get_by_id(user_id)
            if not user:
                return False, "User not found"
            
            # Запретить удаление admin пользователя
            if user['username'] == 'admin':
                return False, "Cannot delete admin user"
            
            # Удалить пользователя
            success = UserModel.delete(user_id)
            if not success:
                return False, "Failed to delete user"
            
            # Отключить RADIUS аккаунт
            self._update_radius_status(user['username'], False)
            
            logger.info(f"User deleted successfully: {user['username']} (ID: {user_id})")
            return True, None
            
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {str(e)}")
            return False, "Failed to delete user"
    
    def _get_user_groups(self, user_id):
        """Получить группы пользователя"""
        try:
            # Здесь будет логика получения групп пользователя
            # Временная заглушка
            return []
        except Exception as e:
            logger.error(f"Error getting groups for user {user_id}: {str(e)}")
            return []
    
    def _get_user_certificate_count(self, user_id):
        """Получить количество сертификатов пользователя"""
        try:
            # Здесь будет логика подсчета сертификатов
            # Временная заглушка
            return 0
        except Exception as e:
            logger.error(f"Error getting certificate count for user {user_id}: {str(e)}")
            return 0
    
    def _update_user_groups(self, user_id, groups):
        """Обновить группы пользователя"""
        try:
            # Удалить все текущие группы
            # Добавить новые группы
            # Логика будет реализована позже
            pass
        except Exception as e:
            logger.error(f"Error updating groups for user {user_id}: {str(e)}")
            raise e
    
    def _update_radius_status(self, username, enabled):
        """Обновить RADIUS статус пользователя"""
        try:
            # Логика обновления RADIUS статуса
            # Временная заглушка
            pass
        except Exception as e:
            logger.error(f"Error updating RADIUS status for user {username}: {str(e)}")
            raise e