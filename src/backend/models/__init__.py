from ...utils.database import get_db_connection
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class BaseModel:
    """Базовый класс для всех моделей"""
    
    @classmethod
    def _execute_query(cls, query, params=None, fetch=False):
        """Выполнить SQL запрос с обработкой ошибок"""
        conn = get_db_connection()
        cur = conn.cursor()
        
        try:
            cur.execute(query, params or ())
            if fetch:
                result = cur.fetchall()
            else:
                result = cur.rowcount
                
            conn.commit()
            return result
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error in {cls.__name__}: {str(e)}")
            raise e
        finally:
            cur.close()
            conn.close()
    
    @classmethod
    def _dict_to_model(cls, row, fields):
        """Преобразовать строку БД в словарь"""
        if not row:
            return None
        return dict(zip(fields, row))