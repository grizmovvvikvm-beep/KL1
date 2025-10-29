import os
import platform
from pathlib import Path
from typing import Dict, Any


class ConfigurationError(Exception):
    """Ошибка конфигурации приложения"""
    pass


class Config:
    """Гибкая конфигурация приложения с поддержкой переменных окружения"""

    def __init__(self):
        self._load_from_env()
        self._setup_paths()
        self._setup_database()
        self._setup_security()
        self.validate()

    def _load_from_env(self):
        """Загрузка настроек из переменных окружения"""
        # Базовые настройки
        self.BASE_DIR = Path(os.getenv('KL_BASE_DIR', self._get_default_base_dir()))
        self.WEB_PORT = int(os.getenv('KL_WEB_PORT', '5000'))
        self.ENVIRONMENT = os.getenv('KL_ENV', 'production').lower()

        # Безопасность
        self.SECRET_KEY = os.getenv('KL_SECRET_KEY', '')
        self.SESSION_TIMEOUT = int(os.getenv('KL_SESSION_TIMEOUT', '3600'))

        # База данных (только PostgreSQL)
        self.DB_NAME = os.getenv('KL_DB_NAME', 'kurslight_db')
        self.DB_USER = os.getenv('KL_DB_USER', 'kurslight_user')
        self.DB_PASSWORD = os.getenv('KL_DB_PASSWORD', '')
        self.DB_HOST = os.getenv('KL_DB_HOST', 'localhost')
        self.DB_PORT = os.getenv('KL_DB_PORT', '5432')

        # OpenVPN: кроссплатформенный путь
        default_openvpn_bin = (
            r'C:\Program Files\OpenVPN\bin\openvpn.exe'
            if platform.system() == 'Windows'
            else '/usr/sbin/openvpn'
        )
        self.OPENVPN_BIN = Path(os.getenv('KL_OPENVPN_BIN', default_openvpn_bin))

        # SSL
        self.SSL_ENABLED = os.getenv('KL_SSL_ENABLED', 'true').lower() == 'true'

    def _get_default_base_dir(self) -> str:
        """Определить базовую директорию по умолчанию"""
        # Если проект запущен из исходников — использовать cwd
        if (Path.cwd() / 'src').exists():
            return str(Path.cwd())

        # Попробовать стандартную системную директорию
        default_system_path = Path('/opt/kurs-light')
        if default_system_path.exists():
            return str(default_system_path)

        # Fallback: домашняя директория пользователя
        home_path = Path.home() / 'kurs-light'
        home_path.mkdir(parents=True, exist_ok=True)
        return str(home_path)

    def _setup_paths(self):
        """Настройка путей к директориям"""
        self.CONFIG_DIR = self.BASE_DIR / 'config'
        self.CA_DIR = self.BASE_DIR / 'ca'
        self.OPENVPN_DIR = self.BASE_DIR / 'openvpn'
        self.FRONTEND_DIR = self.BASE_DIR / 'frontend'
        self.SSL_DIR = self.BASE_DIR / 'ssl'
        self.CERTS_DIR = self.BASE_DIR / 'certs'
        self.LOGS_DIR = self.BASE_DIR / 'logs'
        self.BACKUPS_DIR = self.BASE_DIR / 'backups'
        self.TEMP_DIR = self.BASE_DIR / 'temp'

        # Файлы конфигурации
        self.CONFIG_FILE = self.CONFIG_DIR / 'config.xml'
        self.DB_CONFIG_FILE = self.CONFIG_DIR / 'database.conf'

        # SSL файлы (по умолчанию)
        self.SSL_CERT = self.SSL_DIR / 'server.crt'
        self.SSL_KEY = self.SSL_DIR / 'server.key'
        self.SSL_CA_CERT = self.SSL_DIR / 'ca.crt'

        # OpenVPN каталоги
        self.OPENVPN_SERVERS_DIR = self.OPENVPN_DIR / 'servers'
        self.OPENVPN_SCRIPTS_DIR = self.OPENVPN_DIR / 'scripts'

    def _setup_database(self):
        """Настройка конфигурации базы данных (только PostgreSQL)"""
        self.DB_CONFIG = {
            'dbname': self.DB_NAME,
            'user': self.DB_USER,
            'password': self.DB_PASSWORD,
            'host': self.DB_HOST,
            'port': self.DB_PORT
        }
        # Connection string (удобно для логов/передачи в библиотеки)
        self.DB_URL = f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    def _setup_security(self):
        """Настройка параметров безопасности"""
        self.ALLOWED_HOSTS = [h.strip() for h in os.getenv('KL_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')]
        self.CORS_ORIGINS = [u.strip() for u in os.getenv('KL_CORS_ORIGINS', 'http://localhost:3000').split(',')]

        # Rate limiting
        self.RATE_LIMIT_ENABLED = os.getenv('KL_RATE_LIMIT', 'true').lower() == 'true'
        self.RATE_LIMIT_REQUESTS = int(os.getenv('KL_RATE_LIMIT_REQUESTS', '100'))
        self.RATE_LIMIT_WINDOW = int(os.getenv('KL_RATE_LIMIT_WINDOW', '900'))  # 15 минут

    def validate(self):
        """Проверить обязательные настройки. В production — ошибки, в dev — предупреждения."""
        errors = []
        warnings = []

        # SECRET_KEY
        if not self.SECRET_KEY:
            msg = "SECRET_KEY is not set"
            if self.is_production():
                errors.append(msg)
            else:
                warnings.append(msg)

        # DB password
        if self.is_production() and not self.DB_PASSWORD:
            errors.append("DB_PASSWORD must be set in production environment")

        # Ensure base dir exists or can be created
        try:
            self.BASE_DIR.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            errors.append(f"Cannot create BASE_DIR {self.BASE_DIR}: {e}")

        # OpenVPN binary: error in prod, warn in dev
        if not self.OPENVPN_BIN.exists():
            msg = f"OpenVPN binary not found at {self.OPENVPN_BIN}"
            if self.is_production():
                errors.append(msg)
            else:
                warnings.append(msg)

        # Create directories if possible (best-effort)
        try:
            self.ensure_directories()
        except Exception as e:
            warnings.append(f"ensure_directories failed: {e}")

        if errors:
            raise ConfigurationError("\n".join(errors))

        # Log warnings to stderr (caller can use logging)
        if warnings:
            for w in warnings:
                print(f"WARNING: {w}", flush=True)

    def ensure_directories(self):
        """Создать все необходимые директории (idempotent)."""
        directories = [
            self.CONFIG_DIR,
            self.CA_DIR,
            self.OPENVPN_DIR,
            self.OPENVPN_SERVERS_DIR,
            self.OPENVPN_SCRIPTS_DIR,
            self.FRONTEND_DIR,
            self.SSL_DIR,
            self.CERTS_DIR,
            self.LOGS_DIR,
            self.BACKUPS_DIR,
            self.TEMP_DIR
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def is_development(self) -> bool:
        """Проверить, работает ли приложение в режиме разработки"""
        return self.ENVIRONMENT in ('dev', 'development')

    def is_production(self) -> bool:
        """Проверить, работает ли приложение в production режиме"""
        return self.ENVIRONMENT in ('prod', 'production')

    def to_dict(self) -> Dict[str, Any]:
        """Представить конфигурацию в виде словаря (без чувствительных данных)"""
        return {
            'base_dir': str(self.BASE_DIR),
            'web_port': self.WEB_PORT,
            'environment': self.ENVIRONMENT,
            'database': {
                'host': self.DB_HOST,
                'port': self.DB_PORT,
                'name': self.DB_NAME,
                'user': self.DB_USER
            },
            'openvpn_bin': str(self.OPENVPN_BIN),
            'ssl_enabled': self.SSL_ENABLED,
            'rate_limiting': {
                'enabled': self.RATE_LIMIT_ENABLED,
                'requests': self.RATE_LIMIT_REQUESTS,
                'window': self.RATE_LIMIT_WINDOW
            }
        }


# Глобальный экземпляр конфигурации
config = Config()