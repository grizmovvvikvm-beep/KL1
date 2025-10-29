from functools import wraps
from flask import request, session, jsonify, g
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def login_required(f):
    """Декоратор для проверки аутентификации пользователя"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Проверить наличие user_id в сессии
        if 'user_id' not in session:
            logger.warning(f"Unauthorized access attempt to {request.endpoint} from {request.remote_addr}")
            return jsonify({"error": "Authentication required"}), 401
        
        # Проверить срок действия сессии (опционально)
        if not _is_session_valid():
            session.clear()
            logger.warning(f"Expired session for user {session.get('username', 'unknown')}")
            return jsonify({"error": "Session expired"}), 401
        
        # Добавить информацию о пользователе в контекст запроса
        g.user = {
            'id': session['user_id'],
            'username': session['username'],
            'role': session['role'],
            'full_name': session.get('full_name', '')
        }
        
        # Обновить время последней активности
        session['last_activity'] = datetime.now().isoformat()
        
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Декоратор для проверки прав администратора"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Сначала проверить аутентификацию
        if 'user_id' not in session:
            return jsonify({"error": "Authentication required"}), 401
        
        # Затем проверить роль администратора
        if session.get('role') != 'admin':
            logger.warning(
                f"Admin access denied for user {session.get('username', 'unknown')} "
                f"to endpoint {request.endpoint}"
            )
            return jsonify({"error": "Admin access required"}), 403
        
        # Добавить информацию о пользователе в контекст запроса
        g.user = {
            'id': session['user_id'],
            'username': session['username'],
            'role': session['role'],
            'full_name': session.get('full_name', '')
        }
        
        # Обновить время последней активности
        session['last_activity'] = datetime.now().isoformat()
        
        return f(*args, **kwargs)
    return decorated_function

def _is_session_valid():
    """Проверить валидность сессии (время жизни)"""
    last_activity = session.get('last_activity')
    if not last_activity:
        return False
    
    try:
        last_activity_time = datetime.fromisoformat(last_activity)
        # Сессия действительна 1 час
        return datetime.now() - last_activity_time < timedelta(hours=1)
    except (ValueError, TypeError):
        return False

def api_key_required(f):
    """Декоратор для проверки API ключа (для внешних интеграций)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        
        if not api_key:
            logger.warning(f"API key missing for endpoint {request.endpoint}")
            return jsonify({"error": "API key required"}), 401
        
        # TODO: Реализовать проверку API ключа в БД
        # Временная заглушка
        valid_keys = []  # Будет загружаться из БД или конфига
        
        if api_key not in valid_keys:
            logger.warning(f"Invalid API key used for endpoint {request.endpoint}")
            return jsonify({"error": "Invalid API key"}), 401
        
        return f(*args, **kwargs)
    return decorated_function

def rate_limit(max_requests=100, window_minutes=15):
    """Декоратор для ограничения частоты запросов"""
    def decorator(f):
        request_counts = {}
        
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Использовать IP адрес как идентификатор
            client_id = request.remote_addr
            current_window = datetime.now().strftime('%Y%m%d%H%M')
            window_key = f"{client_id}:{current_window}"
            
            # Инициализировать счетчик для окна
            if window_key not in request_counts:
                request_counts[window_key] = 0
            
            # Проверить лимит
            if request_counts[window_key] >= max_requests:
                logger.warning(f"Rate limit exceeded for {client_id}")
                return jsonify({
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {max_requests} requests per {window_minutes} minutes"
                }), 429
            
            # Увеличить счетчик
            request_counts[window_key] += 1
            
            # Очистить старые окна (простая реализация)
            _clean_old_windows(request_counts, window_minutes)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def _clean_old_windows(request_counts, window_minutes):
    """Очистить старые окна запросов"""
    current_time = datetime.now()
    keys_to_remove = []
    
    for key in request_counts.keys():
        try:
            client_id, window_str = key.split(':')
            window_time = datetime.strptime(window_str, '%Y%m%d%H%M')
            
            if current_time - window_time > timedelta(minutes=window_minutes):
                keys_to_remove.append(key)
        except (ValueError, AttributeError):
            keys_to_remove.append(key)
    
    for key in keys_to_remove:
        del request_counts[key]