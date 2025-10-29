class BaseService:
    """Базовый класс для всех сервисов"""
    
    def __init__(self):
        pass
    
    def validate_parameters(self, **kwargs):
        """Базовая валидация параметров"""
        for key, value in kwargs.items():
            if value is None:
                raise ValueError(f"Parameter {key} cannot be None")
        return True