from flask import Flask, send_from_directory
import os
import logging
from pathlib import Path

# Импорт конфигурации
from .config import config

# Импорт утилит
from .utils.logging import setup_logging
from .utils.database import init_db

# Настройка логирования
setup_logging()
logger = logging.getLogger(__name__)

# Глобальная переменная для приложения
app = None

def create_app():
    """Фабрика для создания приложения Flask"""
    global app
    if app is not None:
        return app
        
    app = Flask(__name__)
    
    # Базовая конфигурация
    app.config['SECRET_KEY'] = config.SECRET_KEY
    app.config['JSON_SORT_KEYS'] = False
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
    
    # Создать необходимые директории
    _create_required_directories()
    
    # Регистрация middleware
    _register_middleware(app)
    
    # Регистрация обработчиков ошибок
    _register_error_handlers(app)
    
    # Инициализация базы данных
    _initialize_database()
    
    # Регистрация маршрутов
    _register_blueprints(app)
    
    # Статические файлы и SPA роутинг
    _setup_static_routes(app)
    
    # Фоновые задачи
    _start_background_tasks()
    
    logger.info("KursLight VPN Management System application initialized successfully")
    return app

def get_app():
    """Получить экземпляр приложения (для импорта из других модулей)"""
    global app
    if app is None:
        app = create_app()
    return app

def _register_error_handlers(app):
    """Регистрация обработчиков ошибок"""
    from .middleware.error_handling import register_error_handlers
    register_error_handlers(app)

def _register_middleware(app):
    """Зарегистрировать все middleware"""
    from .middleware.request_logging import log_requests
    from .middleware.security import security_headers
    from .middleware.cors import setup_cors
    
    # Логирование запросов
    log_requests(app)
    
    # Security headers
    security_headers(app)
    
    # CORS для фронтенда
    setup_cors(app)
    
    logger.info("Middleware registered successfully")

def _register_blueprints(app):
    """Зарегистрировать все blueprint'ы"""
    from .routes.auth import auth_bp
    from .routes.users import users_bp
    from .routes.groups import groups_bp
    from .routes.vpn import vpn_bp
    from .routes.certificates import certificates_bp
    from .routes.system import system_bp
    
    # API routes с префиксом /api
    blueprints = [
        (auth_bp, '/api'),
        (users_bp, '/api'),
        (groups_bp, '/api'),
        (vpn_bp, '/api'),
        (certificates_bp, '/api'),
        (system_bp, '/api')
    ]
    
    for blueprint, url_prefix in blueprints:
        app.register_blueprint(blueprint, url_prefix=url_prefix)
        logger.debug(f"Blueprint registered: {blueprint.name} with prefix {url_prefix}")
    
    logger.info("All blueprints registered successfully")

# ... остальные функции остаются без изменений ...

# Убрали создание app на уровне модуля
# app = create_app()  # <- ЭТУ СТРОКУ УДАЛИТЬ

# ================= ЗАПУСК ПРИЛОЖЕНИЯ =================
if __name__ == '__main__':
    try:
        logger.info("Starting KursLight VPN Management System...")
        
        # Создаем приложение
        app = create_app()
        
        # Проверить наличие SSL сертификатов
        if not config.SSL_CERT.exists() or not config.SSL_KEY.exists():
            logger.warning("SSL certificates not found. Generating self-signed certificates...")
            _generate_self_signed_cert()
        
        # Контекст SSL
        ssl_context = (str(config.SSL_CERT), str(config.SSL_KEY))
        
        # Запуск приложения
        logger.info(f"Server starting on https://0.0.0.0:{config.WEB_PORT}")
        
        app.run(
            host='0.0.0.0',
            port=config.WEB_PORT,
            ssl_context=ssl_context,
            threaded=True,
            debug=False
        )
        
    except Exception as e:
        logger.critical(f"Failed to start application: {str(e)}")
        raise
        def create_app():
    """Фабрика для создания приложения Flask"""
    global app
    if app is not None:
        return app
        
    app = Flask(__name__)
    
    # Базовая конфигурация
    app.config['SECRET_KEY'] = config.SECRET_KEY
    app.config['JSON_SORT_KEYS'] = False
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
    
    # Development settings
    if config.is_development():
        app.config['DEBUG'] = True
        app.config['TESTING'] = True
    
    # Создать необходимые директории
    config.ensure_directories()  # ← ЗАМЕНА: вместо _create_required_directories()
    
    # ... остальной код без изменений ...