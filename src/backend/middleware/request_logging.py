from flask import request, g
import time
import logging

logger = logging.getLogger(__name__)

def log_requests(app):
    """Middleware для логирования всех входящих запросов"""
    
    @app.before_request
    def start_timer():
        g.start_time = time.time()
    
    @app.after_request
    def log_request(response):
        # Пропустить статические файлы
        if request.path.startswith('/static/'):
            return response
        
        # Рассчитать время выполнения
        if hasattr(g, 'start_time'):
            response_time = round((time.time() - g.start_time) * 1000, 2)  # в мс
        else:
            response_time = 0
        
        # Информация о пользователе
        user_info = "anonymous"
        if hasattr(g, 'user'):
            user_info = g.user.get('username', 'unknown')
        
        # Логировать запрос
        log_data = {
            'method': request.method,
            'path': request.path,
            'status': response.status_code,
            'response_time_ms': response_time,
            'user': user_info,
            'ip': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', ''),
            'content_length': response.content_length or 0
        }
        
        # Логировать с разным уровнем в зависимости от статуса
        if response.status_code >= 500:
            logger.error(f"HTTP {log_data['method']} {log_data['path']} {log_data['status']} "
                        f"{log_data['response_time_ms']}ms user:{log_data['user']}")
        elif response.status_code >= 400:
            logger.warning(f"HTTP {log_data['method']} {log_data['path']} {log_data['status']} "
                          f"{log_data['response_time_ms']}ms user:{log_data['user']}")
        else:
            logger.info(f"HTTP {log_data['method']} {log_data['path']} {log_data['status']} "
                       f"{log_data['response_time_ms']}ms user:{log_data['user']}")
        
        return response

def sanitize_sensitive_data(data):
    """Очистить чувствительные данные перед логированием"""
    sensitive_fields = ['password', 'token', 'secret', 'key', 'authorization']
    
    if isinstance(data, dict):
        sanitized = data.copy()
        for field in sensitive_fields:
            if field in sanitized:
                sanitized[field] = '***REDACTED***'
        return sanitized
    
    return data