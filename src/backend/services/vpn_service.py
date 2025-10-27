from . import BaseService
from ..models.vpn import VPNModel
import logging
import subprocess
import os
from ...config import config

logger = logging.getLogger(__name__)

class VPNService(BaseService):
    """Сервис для управления VPN инстансами"""
    
    def get_all_instances(self):
        """Получить все VPN инстансы"""
        try:
            instances = VPNModel.get_all()
            
            result = []
            for instance in instances:
                instance_data = {
                    'id': instance['id'],
                    'name': instance['name'],
                    'description': instance['description'],
                    'status': instance['status'],
                    'port': instance['port'],
                    'protocol': instance['protocol'],
                    'subnet': instance['subnet'],
                    'active_clients': instance['active_clients'],
                    'max_clients': instance['max_clients'],
                    'created_at': instance['created_at'].isoformat() if instance['created_at'] else None
                }
                result.append(instance_data)
            
            return result, None
            
        except Exception as e:
            logger.error(f"Error getting VPN instances: {str(e)}")
            return None, "Failed to retrieve VPN instances"
    
    def start_instance(self, instance_name):
        """Запустить VPN инстанс"""
        try:
            # Логика запуска OpenVPN
            conf_path = os.path.join(config.OPENVPN_DIR, 'servers', instance_name, 'server.conf')
            
            if not os.path.exists(conf_path):
                return False, f"Configuration file not found: {conf_path}"
            
            # Запуск OpenVPN процесса
            result = subprocess.run([
                'openvpn', '--config', conf_path, '--daemon'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                VPNModel.update_status(instance_name, 'running')
                logger.info(f"VPN instance started: {instance_name}")
                return True, None
            else:
                logger.error(f"Failed to start VPN instance {instance_name}: {result.stderr}")
                return False, f"Failed to start: {result.stderr}"
                
        except Exception as e:
            logger.error(f"Error starting VPN instance {instance_name}: {str(e)}")
            return False, f"Start error: {str(e)}"
    
    def stop_instance(self, instance_name):
        """Остановить VPN инстанс"""
        try:
            # Найти и убить процесс OpenVPN
            conf_path = os.path.join(config.OPENVPN_DIR, 'servers', instance_name, 'server.conf')
            result = subprocess.run([
                'pkill', '-f', f'openvpn.*{conf_path}'
            ], capture_output=True, text=True)
            
            VPNModel.update_status(instance_name, 'stopped')
            logger.info(f"VPN instance stopped: {instance_name}")
            return True, None
            
        except Exception as e:
            logger.error(f"Error stopping VPN instance {instance_name}: {str(e)}")
            return False, f"Stop error: {str(e)}"