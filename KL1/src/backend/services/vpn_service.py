import logging
import subprocess
import os
import psutil
from pathlib import Path

# Исправляем импорты
from src.backend.services.base_service import BaseService
from src.backend.models.vpn import VPNModel
from src.backend.config import config

logger = logging.getLogger(__name__)

class VPNService(BaseService):
    """Сервис для управления VPN инстансами"""
    
    def __init__(self):
        self.allowed_directories = [
            config.OPENVPN_DIR / 'servers',
            Path('/etc/openvpn'),  # Стандартный путь OpenVPN
        ]
    
    def _validate_instance_name(self, instance_name):
        """Валидация имени инстанса"""
        if not instance_name or not isinstance(instance_name, str):
            raise ValueError("Invalid instance name")
        
        # Запрещенные символы для предотвращения инъекций
        forbidden_chars = ['/', '\\', '..', '|', '&', ';', '$', '`']
        for char in forbidden_chars:
            if char in instance_name:
                raise SecurityError(f"Forbidden character in instance name: {char}")
        
        return instance_name.strip()
    
    def _validate_config_path(self, instance_name, conf_path):
        """Валидация пути к конфигурационному файлу"""
        conf_path = Path(conf_path).resolve()
        
        # Проверить, что путь внутри разрешенных директорий
        allowed = any(allowed_dir in conf_path.parents for allowed_dir in self.allowed_directories)
        if not allowed:
            raise SecurityError(f"Config path outside allowed directories: {conf_path}")
        
        # Проверить существование файла
        if not conf_path.exists():
            raise FileNotFoundError(f"Config file not found: {conf_path}")
        
        return conf_path
    
    def _execute_safe_command(self, command, timeout=30):
        """Безопасное выполнение команды"""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False,  # Никогда не использовать shell=True!
                cwd=str(config.OPENVPN_DIR)  # Рабочая директория
            )
            return result
        except subprocess.TimeoutExpired:
            logger.error(f"Command timeout: {' '.join(command)}")
            raise
        except Exception as e:
            logger.error(f"Command execution failed: {str(e)}")
            raise
    
    def get_all_instances(self):
        """Получить все VPN инстансы"""
        try:
            instances = VPNModel.get_all()
            
            result = []
            for instance in instances:
                # Проверяем реальный статус процесса
                real_status = self._get_real_instance_status(instance['name'])
                
                instance_data = {
                    'id': instance['id'],
                    'name': instance['name'],
                    'description': instance['description'],
                    'status': real_status,  # Используем реальный статус
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
    
    def _get_real_instance_status(self, instance_name):
        """Проверить реальный статус процесса OpenVPN"""
        try:
            instance_name = self._validate_instance_name(instance_name)
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    proc_info = proc.info
                    if proc_info['name'] and 'openvpn' in proc_info['name'].lower():
                        cmdline = ' '.join(proc_info['cmdline'] or [])
                        if instance_name in cmdline:
                            return 'running'
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return 'stopped'
        except Exception as e:
            logger.warning(f"Could not check real status for {instance_name}: {str(e)}")
            return 'unknown'
    
    def start_instance(self, instance_name):
        """Запустить VPN инстанс"""
        try:
            instance_name = self._validate_instance_name(instance_name)
            conf_path = config.OPENVPN_DIR / 'servers' / instance_name / 'server.conf'
            conf_path = self._validate_config_path(instance_name, conf_path)
            
            # Запуск OpenVPN процесса
            result = self._execute_safe_command([
                'openvpn', 
                '--config', str(conf_path),
                '--daemon'
            ])
            
            if result.returncode == 0:
                VPNModel.update_status(instance_name, 'running')
                logger.info(f"VPN instance started: {instance_name}")
                return True, None
            else:
                logger.error(f"Failed to start VPN instance {instance_name}: {result.stderr}")
                return False, f"Failed to start: {result.stderr}"
                
        except SecurityError as e:
            logger.error(f"Security violation while starting {instance_name}: {str(e)}")
            return False, f"Security error: {str(e)}"
        except Exception as e:
            logger.error(f"Error starting VPN instance {instance_name}: {str(e)}")
            return False, f"Start error: {str(e)}"
    
    def stop_instance(self, instance_name):
        """Остановить VPN инстанс"""
        try:
            instance_name = self._validate_instance_name(instance_name)
            
            # Найти PID процесса
            pid = None
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    proc_info = proc.info
                    if proc_info['name'] and 'openvpn' in proc_info['name'].lower():
                        cmdline = ' '.join(proc_info['cmdline'] or [])
                        if instance_name in cmdline:
                            pid = proc_info['pid']
                            break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if pid:
                # Корректное завершение процесса
                result = self._execute_safe_command(['kill', '-TERM', str(pid)])
                if result.returncode == 0:
                    VPNModel.update_status(instance_name, 'stopped')
                    logger.info(f"VPN instance stopped: {instance_name}")
                    return True, None
                else:
                    return False, f"Failed to stop process: {result.stderr}"
            else:
                VPNModel.update_status(instance_name, 'stopped')
                logger.info(f"VPN instance already stopped: {instance_name}")
                return True, None
            
        except SecurityError as e:
            logger.error(f"Security violation while stopping {instance_name}: {str(e)}")
            return False, f"Security error: {str(e)}"
        except Exception as e:
            logger.error(f"Error stopping VPN instance {instance_name}: {str(e)}")
            return False, f"Stop error: {str(e)}"

class SecurityError(Exception):
    """Ошибка безопасности"""
    pass