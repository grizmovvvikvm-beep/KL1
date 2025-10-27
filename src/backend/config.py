import os
from pathlib import Path

class Config:
    # Пути
    BASE_DIR = Path("/opt/kurs-light")
    CONFIG_FILE = BASE_DIR / "config.xml"
    CA_DIR = BASE_DIR / "ca"
    OPENVPN_DIR = BASE_DIR / "openvpn"
    FRONTEND_DIR = BASE_DIR / "frontend"
    SSL_DIR = BASE_DIR / "ssl"
    CERTS_DIR = BASE_DIR / "certs"
    
    # Веб-сервер
    WEB_PORT = 5000
    SSL_CERT = SSL_DIR / "server.crt"
    SSL_KEY = SSL_DIR / "server.key"
    
    # База данных
    DB_CONFIG = {
        'dbname': os.getenv('DB_NAME', 'kurslight_db'),
        'user': os.getenv('DB_USER', 'kurslight_user'),
        'password': os.getenv('DB_PASSWORD', ''),
        'host': os.getenv('DB_HOST', 'localhost')
    }
    
    # Безопасность
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    SESSION_TIMEOUT = 3600  # 1 час
    
config = Config()