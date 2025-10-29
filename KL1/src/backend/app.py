from flask import Flask, send_from_directory
from pathlib import Path
import logging
import os

from .config import config
from .utils.logging import setup_logging
from .utils.database import init_db

setup_logging()
logger = logging.getLogger(__name__)

app = None

def _create_required_directories():
    """Создать необходимые директории (использует config.ensure_directories если есть)."""
    try:
        if hasattr(config, "ensure_directories"):
            config.ensure_directories()
            return
    except Exception as e:
        logger.warning(f"config.ensure_directories() failed: {e}")

    dirs = [
        getattr(config, "CONFIG_DIR", Path(config.BASE_DIR) / "config"),
        getattr(config, "CA_DIR", Path(config.BASE_DIR) / "ca"),
        getattr(config, "OPENVPN_DIR", Path(config.BASE_DIR) / "openvpn"),
        getattr(config, "FRONTEND_DIR", Path(config.BASE_DIR) / "frontend"),
        getattr(config, "SSL_DIR", Path(config.BASE_DIR) / "ssl"),
        getattr(config, "CERTS_DIR", Path(config.BASE_DIR) / "certs"),
        getattr(config, "LOGS_DIR", Path(config.BASE_DIR) / "logs"),
        getattr(config, "BACKUPS_DIR", Path(config.BASE_DIR) / "backups"),
        getattr(config, "TEMP_DIR", Path(config.BASE_DIR) / "temp"),
    ]
    for d in dirs:
        try:
            Path(d).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Failed to create directory {d}: {e}")

def _initialize_database():
    """Инициализация базы данных (обёртка init_db)."""
    try:
        init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database init failed: {e}")
        raise

def _setup_static_routes(app):
    """Отдача фронтенда (SPA)."""
    frontend_dir = Path(getattr(config, "FRONTEND_DIR", Path(config.BASE_DIR) / "frontend"))
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_frontend(path):
        target = frontend_dir / path
        if path and target.exists():
            return send_from_directory(str(frontend_dir), path)
        index = frontend_dir / 'index.html'
        if index.exists():
            return send_from_directory(str(frontend_dir), 'index.html')
        return "Frontend not found", 404

def _start_background_tasks():
    """Заглушка для фоновых задач (по необходимости добавить реализацию)."""
    # Например: запуск периодических задач через threading/apscheduler
    return

def _generate_self_signed_cert():
    """Генерация самоподписанного сертификата (требует cryptography)."""
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        import datetime
    except Exception as e:
        logger.error(f"cryptography not available: {e}")
        raise

    ssl_dir = Path(getattr(config, "SSL_DIR", Path(config.BASE_DIR) / "ssl"))
    ssl_dir.mkdir(parents=True, exist_ok=True)
    cert_path = Path(getattr(config, "SSL_CERT", ssl_dir / "server.crt"))
    key_path = Path(getattr(config, "SSL_KEY", ssl_dir / "server.key"))

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"RU"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"KursLight"),
        x509.NameAttribute(NameOID.COMMON_NAME, u"localhost"),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow())
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName(u"localhost")]), critical=False)
        .sign(key, hashes.SHA256())
    )

    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    with open(key_path, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))
    logger.info(f"Generated self-signed cert: {cert_path}, key: {key_path}")

def create_app():
    """Фабрика Flask-приложения."""
    global app
    if app is not None:
        return app

    app = Flask(__name__, static_folder=None)

    # Конфигурация
    try:
        app.config['SECRET_KEY'] = getattr(config, "SECRET_KEY", os.getenv("KL_SECRET_KEY", ""))
    except Exception:
        app.config['SECRET_KEY'] = os.getenv("KL_SECRET_KEY", "")

    app.config['JSON_SORT_KEYS'] = False
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

    if hasattr(config, "is_development") and callable(config.is_development) and config.is_development():
        app.config['DEBUG'] = True
        app.config['TESTING'] = True

    _create_required_directories()
    _register_middleware(app)
    _register_error_handlers(app)
    _initialize_database()
    _register_blueprints(app)
    _setup_static_routes(app)
    _start_background_tasks()

    logger.info("Application factory finished")
    return app

def get_app():
    global app
    if app is None:
        app = create_app()
    return app

def _register_error_handlers(app):
    """Попытаться подключить модуль обработки ошибок, если есть."""
    try:
        from .middleware.error_handling import register_error_handlers
        register_error_handlers(app)
    except Exception as e:
        logger.debug(f"No custom error handlers registered: {e}")

def _register_middleware(app):
    """Попытаться зарегистрировать стандартные middleware (без фатальной ошибки)."""
    try:
        from .middleware.request_logging import log_requests
        log_requests(app)
    except Exception:
        logger.debug("request_logging middleware not available")

    try:
        from .middleware.security import security_headers
        security_headers(app)
    except Exception:
        logger.debug("security middleware not available")

    try:
        from .middleware.cors import setup_cors
        setup_cors(app)
    except Exception:
        logger.debug("CORS middleware not available")

def _register_blueprints(app):
    """Регистрация blueprints — импортируется по модулю, отсутствие не фатально."""
    candidates = [
        ("routes.auth", "auth_bp"),
        ("routes.users", "users_bp"),
        ("routes.groups", "groups_bp"),
        ("routes.vpn", "vpn_bp"),
        ("routes.certificates", "certificates_bp"),
        ("routes.system", "system_bp"),
    ]
    for module_path, bp_name in candidates:
        try:
            module = __import__(f".{module_path}", fromlist=[bp_name])
            bp = getattr(module, bp_name)
            app.register_blueprint(bp, url_prefix='/api')
            logger.debug(f"Registered blueprint {bp_name} from {module_path}")
        except Exception:
            logger.debug(f"Blueprint {bp_name} not registered (module {module_path} missing or error)")

# ================== Запуск ==================
if __name__ == "__main__":
    logger.info("Starting application")
    app = create_app()

    use_ssl = getattr(config, "SSL_ENABLED", False)
    cert = Path(getattr(config, "SSL_CERT", config.SSL_DIR / "server.crt"))
    key = Path(getattr(config, "SSL_KEY", config.SSL_DIR / "server.key"))

    if use_ssl:
        if not cert.exists() or not key.exists():
            logger.warning("SSL enabled but cert/key not found — generating self-signed")
            _generate_self_signed_cert()
        ssl_context = (str(cert), str(key))
    else:
        ssl_context = None

    host = "0.0.0.0"
    port = int(getattr(config, "WEB_PORT", 5000))
    logger.info(f"Running on https://{host}:{port} (ssl={'on' if ssl_context else 'off'})")
    app.run(host=host, port=port, ssl_context=ssl_context, threaded=True, debug=app.config.get("DEBUG", False))