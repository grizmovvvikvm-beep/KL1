import os
from pathlib import Path
from typing import Dict, Any

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
        self.ENVIRONMENT = os.getenv('KL_ENV', 'production')
        
        # Безопасность
        self.SECRET_KEY = os.getenv('KL_SECRET_KEY', '')
        self.SESSION_TIMEOUT = int(os.getenv('KL_SESSION_TIMEOUT', '3600'))
        
        # База данных
        self.DB_NAME = os.getenv('KL_DB_NAME', 'kurslight_db')
        self.DB_USER = os.getenv('KL_DB_USER', 'kurslight_user') 
        self.DB_PASSWORD = os.getenv('KL_DB_PASSWORD', '')
        self.DB_HOST = os.getenv('KL_DB_HOST', 'localhost')
        self.DB_PORT = os.getenv('KL_DB_PORT', '5432')
        
        # OpenVPN
        self.OPENVPN_BIN = os.getenv('KL_OPENVPN_BIN', '/usr/sbin/openvpn')
        
        # SSL
        self.SSL_ENABLED = os.getenv('KL_SSL_ENABLED', 'true').lower() == 'true'
    
    def _get_default_base_dir(self) -> str:
        """Определить базовую директорию по умолчанию"""
        # Если запуск в development mode
        if os.path.exists('src/backend/app.py'):
            return str(Path.cwd())
        
        # Если установлен в системе
        default_system_path = '/opt/kurs-light'
        if Path(default_system_path).exists():
            return default_system_path
        
        # Создать в домашней директории
        home_path = Path.home() / 'kurs-light'
        home_path.mkdir(exist_ok=True)
        return str(home_path)
    
    def _setup_paths(self):
        """Настройка путей к директориям"""
        # Основные директории
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
        
        # SSL файлы
        self.SSL_CERT = self.SSL_DIR / 'server.crt'
        self.SSL_KEY = self.SSL_DIR / 'server.key'
        self.SSL_CA_CERT = self.SSL_DIR / 'ca.crt'
        
        # OpenVPN файлы
        self.OPENVPN_SERVERS_DIR = self.OPENVPN_DIR / 'servers'
        self.OPENVPN_SCRIPTS_DIR = self.OPENVPN_DIR / 'scripts'
    
    def _setup_database(self):
        """Настройка конфигурации базы данных"""
        self.DB_CONFIG = {
            'dbname': self.DB_NAME,
            'user': self.DB_USER,
            'password': self.DB_PASSWORD,
            'host': self.DB_HOST,
            'port': self.DB_PORT
        }
        
        # PostgreSQL connection string
        self.DB_URL = f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        
        # SQLite для development (если PostgreSQL не настроен)
        if not self.DB_PASSWORD and self.ENVIRONMENT == 'development':
            self.DB_URL = f"sqlite:///{self.BASE_DIR / 'kurslight.db'}"
    
    def _setup_security(self):
        """Настройка параметров безопасности"""
        self.ALLOWED_HOSTS = os.getenv('KL_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
        self.CORS_ORIGINS = os.getenv('KL_CORS_ORIGINS', 'http://localhost:3000').split(',')
        
        # Rate limiting
        self.RATE_LIMIT_ENABLED = os.getenv('KL_RATE_LIMIT', 'true').lower() == 'true'
        self.RATE_LIMIT_REQUESTS = int(os.getenv('KL_RATE_LIMIT_REQUESTS', '100'))
        self.RATE_LIMIT_WINDOW = int(os.getenv('KL_RATE_LIMIT_WINDOW', '900'))  # 15 минут
    
    def validate(self):
        """Проверить обязательные настройки"""
        errors = []
        
        # Проверка секретного ключа
        if not self.SECRET_KEY:
            errors.append("SECRET_KEY must be set in environment variables")
        
        # Проверка пароля БД (только для PostgreSQL в production)
        if self.ENVIRONMENT == 'production' and not self.DB_PASSWORD and 'sqlite' not in self.DB_URL:
            errors.append("DB_PASSWORD must be set in production environment")
        
        # Проверка базовой директории
        if not self.BASE_DIR.exists():
            try:
                self.BASE_DIR.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot create base directory {self.BASE_DIR}: {str(e)}")
        
        # Проверка OpenVPN
        if not Path(self.OPENVPN_BIN).exists():
            errors.append(f"OpenVPN binary not found at {self.OPENVPN_BIN}")
        
        if errors:
            raise ConfigurationError("\n".join(errors))
    
    def ensure_directories(self):
        """Создать все необходимые директории"""
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
        return self.ENVIRONMENT == 'development'
    
    def is_production(self) -> bool:
        """Проверить, работает ли приложение в production режиме"""
        return self.ENVIRONMENT == 'production'
    
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
            'openvpn_bin': self.OPENVPN_BIN,
            'ssl_enabled': self.SSL_ENABLED,
            'rate_limiting': {
                'enabled': self.RATE_LIMIT_ENABLED,
                'requests': self.RATE_LIMIT_REQUESTS,
                'window': self.RATE_LIMIT_WINDOW
            }
        }


class ConfigurationError(Exception):
    """Ошибка конфигурации приложения"""
    pass


# Глобальный экземпляр конфигурации
config = Config()