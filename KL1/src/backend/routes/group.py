from flask import Blueprint, request, jsonify
from ..services.group_service import GroupService
from ..middleware.auth import login_required, admin_required
from ..utils.logging import logger

groups_bp = Blueprint('groups', __name__)
group_service = GroupService()

@groups_bp.route('/api/groups', methods=['GET'])
@admin_required
def get_groups():
    """Получить список всех групп"""
    try:
        groups, error = group_service.get_all_groups()
        
        if error:
            return jsonify({"error": error}), 500
        
        return jsonify(groups)
        
    except Exception as e:
        logger.error(f"Get groups endpoint error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@groups_bp.route('/api/groups', methods=['POST'])
@admin_required
def create_group():
    """Создать новую группу"""
    try:
        data = request.get_json(silent=True) or {}
        
        group_id, error = group_service.create_group(data)
        
        if error:
            return jsonify({"error": error}), 400
        
        logger.info(f"Group created by {request.user.get('username', 'unknown')}: {data.get('name')}")
        return jsonify({
            "message": "Group created successfully",
            "group_id": group_id
        }), 201
        
    except Exception as e:
        logger.error(f"Create group endpoint error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@groups_bp.route('/api/groups/<int:group_id>', methods=['GET'])
@admin_required
def get_group(group_id):
    """Получить информацию о конкретной группе"""
    try:
        groups, error = group_service.get_all_groups()
        
        if error:
            return jsonify({"error": error}), 500
        
        group = next((g for g in groups if g['id'] == group_id), None)
        if not group:
            return jsonify({"error": "Group not found"}), 404
        
        return jsonify(group)
        
    except Exception as e:
        logger.error(f"Get group endpoint error for ID {group_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@groups_bp.route('/api/groups/<int:group_id>', methods=['PUT'])
@admin_required
def update_group(group_id):
    """Обновить информацию о группе"""
    try:
        data = request.get_json(silent=True) or {}
        
        success, error = group_service.update_group(group_id, data)
        
        if error:
            return jsonify({"error": error}), 400
        
        logger.info(f"Group updated by {request.user.get('username', 'unknown')}: ID {group_id}")
        return jsonify({"message": "Group updated successfully"})
        
    except Exception as e:
        logger.error(f"Update group endpoint error for ID {group_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@groups_bp.route('/api/groups/<int:group_id>', methods=['DELETE'])
@admin_required
def delete_group(group_id):
    """Удалить группу"""
    try:
        success, error = group_service.delete_group(group_id)
        
        if error:
            return jsonify({"error": error}), 400
        
        logger.info(f"Group deleted by {request.user.get('username', 'unknown')}: ID {group_id}")
        return jsonify({"message": "Group deleted successfully"})
        
    except Exception as e:
        logger.error(f"Delete group endpoint error for ID {group_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@groups_bp.route('/api/groups/<int:group_id>/users', methods=['GET'])
@admin_required
def get_group_users(group_id):
    """Получить пользователей группы"""
    try:
        # TODO: Реализовать получение пользователей группы
        return jsonify({"error": "Not implemented yet"}), 501
        
    except Exception as e:
        logger.error(f"Get group users endpoint error for group {group_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@groups_bp.route('/api/groups/<int:group_id>/users', methods=['POST'])
@admin_required
def add_user_to_group():
    """Добавить пользователя в группу"""
    try:
        # TODO: Реализовать добавление пользователя в группу
        return jsonify({"error": "Not implemented yet"}), 501
        
    except Exception as e:
        logger.error(f"Add user to group endpoint error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500