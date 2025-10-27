from flask import Blueprint, request, session, jsonify
from ..services.auth_service import AuthService
from ..middleware.auth import login_required
from ..utils.logging import logger

auth_bp = Blueprint('auth', __name__)
auth_service = AuthService()

@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    """Аутентификация пользователя"""
    try:
        data = request.get_json(silent=True) or {}
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({"error": "Username and password are required"}), 400
        
        # Аутентификация
        user_data, error = auth_service.login(username, password)
        
        if error:
            logger.warning(f"Failed login attempt for user: {username}")
            return jsonify({"error": error}), 401
        
        # Установка сессии
        session['user_id'] = user_data['id']
        session['username'] = user_data['username']
        session['role'] = user_data['role']
        session['full_name'] = user_data.get('full_name', '')
        
        logger.info(f"User logged in successfully: {username}")
        return jsonify({
            "message": "Login successful",
            "user": user_data
        })
        
    except Exception as e:
        logger.error(f"Login endpoint error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@auth_bp.route('/api/auth/logout', methods=['POST'])
@login_required
def logout():
    """Выход пользователя"""
    try:
        username = session.get('username', 'unknown')
        session.clear()
        
        logger.info(f"User logged out: {username}")
        return jsonify({"message": "Logout successful"})
        
    except Exception as e:
        logger.error(f"Logout endpoint error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@auth_bp.route('/api/auth/me', methods=['GET'])
@login_required
def get_current_user():
    """Получить информацию о текущем пользователе"""
    try:
        user_data = {
            "user": {
                "id": session['user_id'],
                "username": session['username'],
                "role": session['role'],
                "full_name": session.get('full_name', '')
            }
        }
        return jsonify(user_data)
        
    except Exception as e:
        logger.error(f"Get current user endpoint error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@auth_bp.route('/api/auth/change-password', methods=['POST'])
@login_required
def change_password():
    """Смена пароля текущего пользователя"""
    try:
        data = request.get_json(silent=True) or {}
        current_password = data.get('current_password', '')
        new_password = data.get('new_password', '')
        
        if not current_password or not new_password:
            return jsonify({"error": "Current and new password are required"}), 400
        
        success, message = auth_service.change_password(
            session['user_id'], current_password, new_password
        )
        
        if success:
            logger.info(f"Password changed for user: {session['username']}")
            return jsonify({"message": message})
        else:
            return jsonify({"error": message}), 400
            
    except Exception as e:
        logger.error(f"Change password endpoint error for user {session.get('username', 'unknown')}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@auth_bp.route('/api/auth/radius/config', methods=['GET'])
@login_required
def get_radius_config():
    """Получить конфигурацию RADIUS"""
    try:
        # TODO: Реализовать получение конфигурации RADIUS из БД или файла
        return jsonify({
            "enabled": False,
            "server": "localhost",
            "port": 1812,
            "timeout": 5
        })
        
    except Exception as e:
        logger.error(f"Get RADIUS config endpoint error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@auth_bp.route('/api/auth/radius/config', methods=['POST'])
@login_required
def update_radius_config():
    """Обновить конфигурацию RADIUS"""
    try:
        data = request.get_json(silent=True) or {}
        
        # TODO: Реализовать сохранение конфигурации RADIUS
        success = auth_service.initialize_radius(data)
        
        if success:
            logger.info("RADIUS configuration updated")
            return jsonify({"message": "RADIUS configuration updated successfully"})
        else:
            return jsonify({"error": "Failed to initialize RADIUS client"}), 400
            
    except Exception as e:
        logger.error(f"Update RADIUS config endpoint error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500