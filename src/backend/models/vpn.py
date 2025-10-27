from . import BaseModel
import subprocess
import os
from ...config import config

class VPNModel(BaseModel):
    """Модель для работы с VPN инстансами"""
    
    FIELDS = ['id', 'name', 'description', 'config', 'status', 'created_at', 'port', 'protocol', 'subnet', 'active_clients', 'max_clients']
    
    @classmethod
    def create(cls, name, description='', port=1194, protocol='udp', subnet='10.8.0.0/24', max_clients=100):
        """Создать новый VPN инстанс"""
        query = '''
            INSERT INTO vpn_instances (name, description, port, protocol, subnet, max_clients) 
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
        '''
        
        result = cls._execute_query(query, (name, description, port, protocol, subnet, max_clients), fetch=True)
        return result[0][0] if result else None
    
    @classmethod
    def get_all(cls):
        """Получить все VPN инстансы"""
        query = '''
            SELECT id, name, description, config, status, created_at, port, protocol, subnet, active_clients, max_clients
            FROM vpn_instances 
            ORDER BY created_at DESC
        '''
        
        result = cls._execute_query(query, fetch=True)
        instances = [cls._dict_to_model(row, cls.FIELDS) for row in result]
        
        # Обновить статус на основе реальных процессов
        for instance in instances:
            instance['status'] = cls._get_actual_status(instance['name'])
            
        return instances
    
    @classmethod
    def _get_actual_status(cls, instance_name):
        """Получить реальный статус VPN инстанса"""
        try:
            conf_path = os.path.join(config.OPENVPN_DIR, 'servers', instance_name, 'server.conf')
            result = subprocess.run(['pgrep', '-f', f'openvpn.*{conf_path}'], 
                                  capture_output=True, text=True)
            return 'running' if result.stdout.strip() else 'stopped'
        except:
            return 'unknown'
    
    @classmethod
    def update_status(cls, instance_id, status):
        """Обновить статус VPN инстанса"""
        query = "UPDATE vpn_instances SET status = %s WHERE id = %s"
        return cls._execute_query(query, (status, instance_id)) > 0
    
    @classmethod
    def update_client_count(cls, instance_name, client_count):
        """Обновить количество активных клиентов"""
        query = "UPDATE vpn_instances SET active_clients = %s WHERE name = %s"
        return cls._execute_query(query, (client_count, instance_name)) > 0