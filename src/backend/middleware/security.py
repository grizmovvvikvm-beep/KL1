from flask import request, jsonify
import logging

logger = logging.getLogger(__name__)

def security_headers(app):
    """Добавить security headers ко всем ответам"""
    
    @app.after_request
    def set_security_headers(response):
        # Basic security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # CSP - Content Security Policy
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self'"
        )
        
        # Remove server information
        if 'Server' in response.headers:
            del response.headers['Server']
        
        return response

def validate_json_content_type(f):
    """Проверить что Content-Type = application/json для JSON запросов"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ['POST', 'PUT', 'PATCH']:
            if not request.is_json:
                return jsonify({
                    "error": "Unsupported Media Type",
                    "message": "Content-Type must be application/json"
                }), 415
        
        return f(*args, **kwargs)
    return decorated_function

def prevent_brute_force(max_attempts=5, lockout_minutes=30):
    """Защита от brute force атак"""
    failed_attempts = {}
    
    def decorator(f):
        from functools import wraps
        
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = request.remote_addr
            current_time = time.time()
            
            # Очистить старые попытки
            _clean_old_attempts(failed_attempts, lockout_minutes)
            
            # Проверить блокировку
            if client_ip in failed_attempts:
                attempts, first_attempt = failed_attempts[client_ip]
                if attempts >= max_attempts:
                    lockout_time = first_attempt + (lockout_minutes * 60)
                    if current_time < lockout_time:
                        remaining = int(lockout_time - current_time) // 60
                        logger.warning(f"Brute force protection triggered for IP {client_ip}")
                        return jsonify({
                            "error": "Too many failed attempts",
                            "message": f"Account temporarily locked. Try again in {remaining} minutes."
                        }), 429
                    else:
                        # Сбросить счетчик после истечения времени блокировки
                        del failed_attempts[client_ip]
            
            # Выполнить оригинальную функцию
            response = f(*args, **kwargs)
            
            # Если аутентификация неуспешна, увеличить счетчик
            if (hasattr(response, 'status_code') and 
                response.status_code in [401, 403] and 
                request.endpoint in ['auth.login']):
                
                if client_ip not in failed_attempts:
                    failed_attempts[client_ip] = [1, current_time]
                else:
                    failed_attempts[client_ip][0] += 1
                
                logger.warning(f"Failed authentication attempt from {client_ip}. "
                              f"Attempts: {failed_attempts[client_ip][0]}")
            
            return response
        return decorated_function
    return decorator

def _clean_old_attempts(failed_attempts, lockout_minutes):
    """Очистить старые записи о неудачных попытках"""
    current_time = time.time()
    expired_ips = []
    
    for ip, (attempts, first_attempt) in failed_attempts.items():
        if current_time - first_attempt > (lockout_minutes * 60 * 2):  # Удалить после двойного времени блокировки
            expired_ips.append(ip)
    
    for ip in expired_ips:
        del failed_attempts[ip]