from flask import jsonify, request
import logging
import traceback
from functools import wraps

logger = logging.getLogger(__name__)

def register_error_handlers(app):
    """Зарегистрировать обработчики ошибок для приложения"""
    
    @app.errorhandler(400)
    def bad_request(error):
        logger.warning(f"Bad request from {request.remote_addr}: {str(error)}")
        return jsonify({
            "error": "Bad Request",
            "message": "The request could not be understood by the server",
            "path": request.path
        }), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        logger.warning(f"Unauthorized access from {request.remote_addr} to {request.path}")
        return jsonify({
            "error": "Unauthorized",
            "message": "Authentication is required to access this resource",
            "path": request.path
        }), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        logger.warning(f"Forbidden access from {request.remote_addr} to {request.path}")
        return jsonify({
            "error": "Forbidden", 
            "message": "You don't have permission to access this resource",
            "path": request.path
        }), 403
    
    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith('/api/'):
            return jsonify({
                "error": "Not Found",
                "message": "The requested API endpoint was not found",
                "path": request.path
            }), 404
        # Для не-API запросов вернуть HTML страницу
        from flask import send_from_directory
        from ..config import config
        return send_from_directory(config.FRONTEND_DIR, 'index.html')
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        logger.warning(f"Method not allowed from {request.remote_addr}: {request.method} {request.path}")
        return jsonify({
            "error": "Method Not Allowed",
            "message": f"The {request.method} method is not allowed for this endpoint",
            "path": request.path
        }), 405
    
    @app.errorhandler(429)
    def too_many_requests(error):
        return jsonify({
            "error": "Too Many Requests",
            "message": "Rate limit exceeded. Please try again later.",
            "path": request.path
        }), 429
    
    @app.errorhandler(500)
    def internal_server_error(error):
        # Логировать детали ошибки для администратора
        logger.error(f"Internal server error: {str(error)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Для пользователя вернуть общее сообщение
        return jsonify({
            "error": "Internal Server Error",
            "message": "An unexpected error occurred on the server",
            "path": request.path
        }), 500
    
    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Обработчик для непредвиденных ошибок"""
        logger.error(f"Unexpected error: {str(error)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        return jsonify({
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "path": request.path
        }), 500

def catch_exceptions(f):
    """Декоратор для перехвата исключений в маршрутах"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Unhandled exception in {f.__name__}: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            return jsonify({
                "error": "Internal Server Error",
                "message": "An unexpected error occurred"
            }), 500
    return decorated_function