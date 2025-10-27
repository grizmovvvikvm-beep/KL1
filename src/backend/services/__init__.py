import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class BaseService:
    """Базовый класс для всех сервисов"""
    
    @staticmethod
    def validate_required_fields(data, required_fields):
        """Проверить обязательные поля"""
        missing_fields = [field for field in required_fields if field not in data or not data[field]]
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
        return True
    
    @staticmethod
    def validate_password_strength(password):
        """Проверить сложность пароля"""
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        # Можно добавить больше проверок
        return True