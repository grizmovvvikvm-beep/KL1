import os
import subprocess
from ..config import config
import logging

logger = logging.getLogger(__name__)

def generate_self_signed_cert():
    """Сгенерировать самоподписанные SSL сертификаты"""
    try:
        # Создать директорию SSL если не существует
        config.SSL_DIR.mkdir(parents=True, exist_ok=True)
        
        # Генерация приватного ключа
        subprocess.run([
            'openssl', 'genrsa', '-out', str(config.SSL_KEY), '2048'
        ], check=True, capture_output=True)
        
        # Генерация самоподписанного сертификата
        subprocess.run([
            'openssl', 'req', '-new', '-x509', '-key', str(config.SSL_KEY),
            '-out', str(config.SSL_CERT), '-days', '365',
            '-subj', '/C=RU/ST=Moscow/L=Moscow/O=KursLight/CN=localhost'
        ], check=True, capture_output=True)
        
        # Установить правильные права
        os.chmod(config.SSL_KEY, 0o600)
        os.chmod(config.SSL_CERT, 0o644)
        
        logger.info("Self-signed SSL certificates generated successfully")
        
    except subprocess.CalledProcessError as e:
        logger.error(f"OpenSSL command failed: {e.stderr.decode() if e.stderr else 'Unknown error'}")
        raise
    except Exception as e:
        logger.error(f"Failed to generate SSL certificates: {str(e)}")
        raise