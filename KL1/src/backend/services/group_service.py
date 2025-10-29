from . import BaseService
from ..models.group import GroupModel
import logging

logger = logging.getLogger(__name__)

class GroupService(BaseService):
    """Сервис для управления группами пользователей"""
    
    def get_all_groups(self, include_user_count=True):
        """Получить все группы"""
        try:
            groups = GroupModel.get_all()
            result = []
            
            for group in groups:
                group_data = {
                    'id': group['id'],
                    'name': group['name'],
                    'description': group['description'],
                    'created_at': group['created_at'].isoformat() if group['created_at'] else None,
                    'vpn_access': group['vpn_access'],
                    'max_connections': group['max_connections'],
                    'bandwidth_limit': group['bandwidth_limit'],
                    'access_hours': group['access_hours']
                }
                
                if include_user_count:
                    group_data['user_count'] = self._get_group_user_count(group['id'])
                
                result.append(group_data)
            
            return result, None
            
        except Exception as e:
            logger.error(f"Error getting all groups: {str(e)}")
            return None, "Failed to retrieve groups"
    
    def create_group(self, group_data):
        """Создать новую группу"""
        try:
            self.validate_required_fields(group_data, ['name'])
            
            # Проверить существование группы
            existing_group = GroupModel.get_by_name(group_data['name'])
            if existing_group:
                raise ValueError("Group name already exists")
            
            group_id = GroupModel.create(
                name=group_data['name'],
                description=group_data.get('description', ''),
                vpn_access=group_data.get('vpn_access', True),
                max_connections=group_data.get('max_connections', 5),
                bandwidth_limit=group_data.get('bandwidth_limit', 0),
                access_hours=group_data.get('access_hours', '00:00-23:59')
            )
            
            if not group_id:
                raise Exception("Failed to create group")
            
            logger.info(f"Group created successfully: {group_data['name']} (ID: {group_id})")
            return group_id, None
            
        except ValueError as e:
            return None, str(e)
        except Exception as e:
            logger.error(f"Error creating group {group_data.get('name', 'unknown')}: {str(e)}")
            return None, "Failed to create group"
    
    def update_group(self, group_id, update_data):
        """Обновить данные группы"""
        try:
            group = GroupModel.get_by_id(group_id)
            if not group:
                return False, "Group not found"
            
            # Запретить изменение системных групп
            default_groups = ['vpn_users', 'admins', 'guests', 'restricted']
            if group['name'] in default_groups:
                return False, "Cannot modify default groups"
            
            allowed_fields = ['description', 'vpn_access', 'max_connections', 'bandwidth_limit', 'access_hours']
            update_fields = {k: v for k, v in update_data.items() if k in allowed_fields}
            
            if not update_fields:
                return False, "No valid fields to update"
            
            success = GroupModel.update(group_id, **update_fields)
            if not success:
                return False, "Failed to update group"
            
            logger.info(f"Group updated successfully: {group['name']} (ID: {group_id})")
            return True, None
            
        except Exception as e:
            logger.error(f"Error updating group {group_id}: {str(e)}")
            return False, "Failed to update group"
    
    def delete_group(self, group_id):
        """Удалить группу"""
        try:
            group = GroupModel.get_by_id(group_id)
            if not group:
                return False, "Group not found"
            
            # Запретить удаление системных групп
            default_groups = ['vpn_users', 'admins', 'guests', 'restricted']
            if group['name'] in default_groups:
                return False, "Cannot delete default groups"
            
            success = GroupModel.delete(group_id)
            if not success:
                return False, "Failed to delete group"
            
            logger.info(f"Group deleted successfully: {group['name']} (ID: {group_id})")
            return True, None
            
        except Exception as e:
            logger.error(f"Error deleting group {group_id}: {str(e)}")
            return False, "Failed to delete group"
    
    def _get_group_user_count(self, group_id):
        """Получить количество пользователей в группе"""
        try:
            users = GroupModel.get_group_users(group_id)
            return len(users) if users else 0
        except Exception as e:
            logger.error(f"Error getting user count for group {group_id}: {str(e)}")
            return 0