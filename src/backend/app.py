from flask import Flask, send_from_directory
import os
import logging
from pathlib import Path

# Импорт конфигурации
from .config import config

# Импорт утилит
from .utils.logging import setup_logging
from .utils.database import init_db

# Импорт middleware
from .middleware.error_handling import register_error_handlers, catch_exceptions
from .middleware.request_logging import log_requests
from .middleware.security import security_headers, validate_json_content_type
from .middleware.cors import setup_cors

# Импорт blueprint'ов
from .routes.auth import auth_bp
from .routes.users import users_bp
from .routes.groups import groups_bp
from .routes.vpn import vpn_bp
from .routes.certificates import certificates_bp
from .routes.system import system_bp

# Настройка логирования
setup_logging()
logger = logging.getLogger(__name__)

def create_app():
    """Фабрика для создания приложения Flask"""
    app = Flask(__name__)
    
    # Базовая конфигурация
    app.config['SECRET_KEY'] = config.SECRET_KEY
    app.config['JSON_SORT_KEYS'] = False  # Сохранять порядок ключей в JSON
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False  # Не форматировать JSON в продакшене
    
    # Создать необходимые директории
    _create_required_directories()
    
    # Регистрация middleware
    _register_middleware(app)
    
    # Регистрация обработчиков ошибок
    register_error_handlers(app)
    
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

def _create_required_directories():
    """Создать необходимые директории"""
    try:
        directories = [
            config.OPENVPN_DIR,
            config.OPENVPN_DIR / 'servers',
            config.CA_DIR,
            config.SSL_DIR,
            config.CERTS_DIR,
            config.BASE_DIR / 'logs',
            config.BASE_DIR / 'backups'
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Directory ensured: {directory}")
            
    except Exception as e:
        logger.error(f"Failed to create required directories: {str(e)}")
        raise

def _register_middleware(app):
    """Зарегистрировать все middleware"""
    # Логирование запросов
    log_requests(app)
    
    # Security headers
    security_headers(app)
    
    # CORS для фронтенда
    setup_cors(app)
    
    logger.info("Middleware registered successfully")

def _initialize_database():
    """Инициализировать базу данных"""
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        # В зависимости от требований, можно либо завершить приложение,
        # либо продолжить работу в режиме без БД
        raise

def _register_blueprints(app):
    """Зарегистрировать все blueprint'ы"""
    
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

def _setup_static_routes(app):
    """Настроить маршруты для статических файлов и SPA"""
    
    @app.route('/')
    @catch_exceptions
    def serve_index():
        """Обслуживать главную страницу фронтенда"""
        return send_from_directory(config.FRONTEND_DIR, 'index.html')
    
    @app.route('/<path:path>')
    @catch_exceptions
    def serve_static(path):
        """Обслуживать статические файлы фронтенда"""
        # Попробовать найти файл в директории фронтенда
        if os.path.exists(os.path.join(config.FRONTEND_DIR, path)):
            return send_from_directory(config.FRONTEND_DIR, path)
        
        # Если файл не найден, вернуть главную страницу для SPA роутинга
        return send_from_directory(config.FRONTEND_DIR, 'index.html')
    
    logger.info("Static routes configured successfully")

def _start_background_tasks():
    """Запустить фоновые задачи"""
    try:
        from .utils.background_tasks import start_background_tasks
        start_background_tasks()
        logger.info("Background tasks started successfully")
    except Exception as e:
        logger.error(f"Failed to start background tasks: {str(e)}")
        # Фоновые задачи не критичны для работы приложения

# Глобальный экземпляр приложения
app = create_app()

# ================= ЗАПУСК ПРИЛОЖЕНИЯ =================
if __name__ == '__main__':
    try:
        logger.info("Starting KursLight VPN Management System...")
        
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
            debug=False  # В продакшене всегда False
        )
        
    except Exception as e:
        logger.critical(f"Failed to start application: {str(e)}")
        raise

def _generate_self_signed_cert():
    """Сгенерировать самоподписанные SSL сертификаты (для разработки)"""
    try:
        from .utils.ssl_utils import generate_self_signed_cert
        generate_self_signed_cert()
        logger.info("Self-signed SSL certificates generated successfully")
    except Exception as e:
        logger.error(f"Failed to generate SSL certificates: {str(e)}")
        raise