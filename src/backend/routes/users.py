from flask import Blueprint, request, jsonify
from ..services.user_service import UserService
from ..middleware.auth import login_required, admin_required
from ..utils.logging import logger

users_bp = Blueprint('users', __name__)
user_service = UserService()

@users_bp.route('/api/users', methods=['GET'])
@admin_required
def get_users():
    """Получить список всех пользователей"""
    try:
        users, error = user_service.get_all_users()
        
        if error:
            return jsonify({"error": error}), 500
        
        return jsonify(users)
        
    except Exception as e:
        logger.error(f"Get users endpoint error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@users_bp.route('/api/users', methods=['POST'])
@admin_required
def create_user():
    """Создать нового пользователя"""
    try:
        data = request.get_json(silent=True) or {}
        
        user_id, error = user_service.create_user(data)
        
        if error:
            return jsonify({"error": error}), 400
        
        logger.info(f"User created by {request.user.get('username', 'unknown')}: {data.get('username')}")
        return jsonify({
            "message": "User created successfully",
            "user_id": user_id
        }), 201
        
    except Exception as e:
        logger.error(f"Create user endpoint error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@users_bp.route('/api/users/<int:user_id>', methods=['GET'])
@admin_required
def get_user(user_id):
    """Получить информацию о конкретном пользователе"""
    try:
        # TODO: Реализовать получение конкретного пользователя
        # Временная реализация
        users, error = user_service.get_all_users()
        
        if error:
            return jsonify({"error": error}), 500
        
        user = next((u for u in users if u['id'] == user_id), None)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        return jsonify(user)
        
    except Exception as e:
        logger.error(f"Get user endpoint error for ID {user_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@users_bp.route('/api/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    """Обновить информацию о пользователе"""
    try:
        data = request.get_json(silent=True) or {}
        
        success, error = user_service.update_user(user_id, data)
        
        if error:
            return jsonify({"error": error}), 400
        
        logger.info(f"User updated by {request.user.get('username', 'unknown')}: ID {user_id}")
        return jsonify({"message": "User updated successfully"})
        
    except Exception as e:
        logger.error(f"Update user endpoint error for ID {user_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@users_bp.route('/api/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    """Удалить пользователя"""
    try:
        success, error = user_service.delete_user(user_id)
        
        if error:
            return jsonify({"error": error}), 400
        
        logger.info(f"User deleted by {request.user.get('username', 'unknown')}: ID {user_id}")
        return jsonify({"message": "User deleted successfully"})
        
    except Exception as e:
        logger.error(f"Delete user endpoint error for ID {user_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@users_bp.route('/api/users/<int:user_id>/reset-password', methods=['POST'])
@admin_required
def reset_user_password():
    """Сбросить пароль пользователя (администратором)"""
    try:
        data = request.get_json(silent=True) or {}
        new_password = data.get('new_password', '')
        
        if not new_password:
            return jsonify({"error": "New password is required"}), 400
        
        # TODO: Реализовать сброс пароля администратором
        # Временная реализация
        return jsonify({"error": "Not implemented yet"}), 501
        
    except Exception as e:
        logger.error(f"Reset user password endpoint error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500