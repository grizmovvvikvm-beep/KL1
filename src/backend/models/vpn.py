from .base_model import BaseModel
import subprocess
import os
import logging
import json
from ..config import config

logger = logging.getLogger(__name__)

class VPNModel(BaseModel):
    """Модель для работы с VPN инстансами"""
    
    FIELDS = [
        'id', 'name', 'description', 'config', 'status', 'created_at', 
        'port', 'protocol', 'subnet', 'active_clients', 'max_clients',
        'interface_type', 'topology', 'tls_auth', 'crl_enabled', 
        'verify_client', 'ocsp_enabled', 'cert_depth', 'renegotiate_time',
        'auth_token_lifetime', 'redirect_gateway', 'dns_servers', 
        'ntp_servers', 'push_options', 'openvpn_options', 'local_network',
        'verify_remote_cert', 'strict_user_cn', 'remote_random',
        'client_to_client', 'block_ipv6', 'duplicate_cn', 'float',
        'passtos', 'persist_remote_ip', 'route_noexec', 'route_nopull',
        'explicit_exit_notify'
    ]
    
    @classmethod
    def create(cls, name, description='', port=1194, protocol='udp', 
               subnet='10.8.0.0/24', max_clients=100, interface_type='tun',
               topology='subnet', tls_auth=False, crl_enabled=False,
               verify_client=True, ocsp_enabled=False, cert_depth=1,
               renegotiate_time=3600, auth_token_lifetime=3600,
               redirect_gateway=False, dns_servers='', ntp_servers='',
               push_options='', openvpn_options='', local_network='',
               verify_remote_cert=True, strict_user_cn=False, remote_random=False,
               client_to_client=False, block_ipv6=False, duplicate_cn=False,
               float=False, passtos=False, persist_remote_ip=False,
               route_noexec=False, route_nopull=False, explicit_exit_notify=True):
        """Создать новый VPN инстанс"""
        query = '''
            INSERT INTO vpn_instances (
                name, description, port, protocol, subnet, max_clients,
                interface_type, topology, tls_auth, crl_enabled, verify_client,
                ocsp_enabled, cert_depth, renegotiate_time, auth_token_lifetime,
                redirect_gateway, dns_servers, ntp_servers, push_options,
                openvpn_options, local_network, verify_remote_cert, strict_user_cn,
                remote_random, client_to_client, block_ipv6, duplicate_cn, float,
                passtos, persist_remote_ip, route_noexec, route_nopull, explicit_exit_notify
            ) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        '''
        
        params = (
            name, description, port, protocol, subnet, max_clients,
            interface_type, topology, tls_auth, crl_enabled, verify_client,
            ocsp_enabled, cert_depth, renegotiate_time, auth_token_lifetime,
            redirect_gateway, dns_servers, ntp_servers, push_options,
            openvpn_options, local_network, verify_remote_cert, strict_user_cn,
            remote_random, client_to_client, block_ipv6, duplicate_cn, float,
            passtos, persist_remote_ip, route_noexec, route_nopull, explicit_exit_notify
        )
        
        result = cls._execute_query(query, params, fetch=True)
        return result[0][0] if result else None
    
    @classmethod
    def get_by_id(cls, instance_id):
        """Получить VPN инстанс по ID"""
        return cls._get_by_id('vpn_instances', instance_id, cls.FIELDS)
    
    @classmethod
    def get_by_name(cls, name):
        """Получить VPN инстанс по имени"""
        query = f'''
            SELECT {', '.join(cls.FIELDS)}
            FROM vpn_instances WHERE name = %s
        '''
        result = cls._execute_query(query, (name,), fetch=True)
        return cls._dict_to_model(result[0], cls.FIELDS) if result else None
    
    @classmethod
    def get_all(cls):
        """Получить все VPN инстансы"""
        query = f'''
            SELECT {', '.join(cls.FIELDS)}
            FROM vpn_instances 
            ORDER BY created_at DESC
        '''
        
        result = cls._execute_query(query, fetch=True)
        if not result:
            return []
            
        instances = [cls._dict_to_model(row, cls.FIELDS) for row in result]
        
        # Обновить статус на основе реальных процессов
        for instance in instances:
            instance['status'] = cls._get_actual_status(instance['name'])
            
        return instances
    
    @classmethod
    def _get_actual_status(cls, instance_name):
        """Получить реальный статус VPN инстанса"""
        try:
            # Проверяем через pgrep
            conf_path = os.path.join(config.OPENVPN_DIR, 'servers', instance_name, 'server.conf')
            result = subprocess.run(
                ['pgrep', '-f', f'openvpn.*{conf_path}'], 
                capture_output=True, 
                text=True,
                timeout=5
            )
            return 'running' if result.stdout.strip() else 'stopped'
        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout checking status for {instance_name}")
            return 'unknown'
        except Exception as e:
            logger.error(f"Error checking status for {instance_name}: {str(e)}")
            return 'unknown'
    
    @classmethod
    def update_status(cls, instance_name, status):
        """Обновить статус VPN инстанса ПО ИМЕНИ"""
        query = "UPDATE vpn_instances SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE name = %s"
        return cls._execute_query(query, (status, instance_name)) > 0
    
    @classmethod
    def update_config(cls, instance_id, config_data):
        """Обновить конфигурацию VPN инстанса"""
        query = "UPDATE vpn_instances SET config = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
        return cls._execute_query(query, (config_data, instance_id)) > 0
    
    @classmethod
    def update_settings(cls, instance_id, **settings):
        """Обновить настройки VPN инстанса"""
        if not settings:
            return False
            
        set_clause = ', '.join([f"{key} = %s" for key in settings.keys()])
        query = f"UPDATE vpn_instances SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
        params = list(settings.values()) + [instance_id]
        
        return cls._execute_query(query, params) > 0
    
    @classmethod
    def update_client_count(cls, instance_name, client_count):
        """Обновить количество активных клиентов"""
        query = "UPDATE vpn_instances SET active_clients = %s, updated_at = CURRENT_TIMESTAMP WHERE name = %s"
        return cls._execute_query(query, (client_count, instance_name)) > 0
    
    @classmethod
    def delete(cls, instance_id):
        """Удалить VPN инстанс"""
        query = "DELETE FROM vpn_instances WHERE id = %s"
        return cls._execute_query(query, (instance_id,)) > 0
    
    @classmethod
    def get_openvpn_options(cls, instance):
        """Получить опции OpenVPN в виде списка"""
        options = []
        
        # Базовые опции
        if instance.get('client_to_client'):
            options.append('client-to-client')
        if instance.get('block_ipv6'):
            options.append('block-ipv6')
        if instance.get('duplicate_cn'):
            options.append('duplicate-cn')
        if instance.get('float'):
            options.append('float')
        if instance.get('passtos'):
            options.append('passtos')
        if instance.get('persist_remote_ip'):
            options.append('persist-remote-ip')
        if instance.get('route_noexec'):
            options.append('route-noexec')
        if instance.get('route_nopull'):
            options.append('route-nopull')
        if instance.get('explicit_exit_notify'):
            options.append('explicit-exit-notify')
        if instance.get('remote_random'):
            options.append('remote-random')
        
        # Дополнительные опции из текстового поля
        if instance.get('openvpn_options'):
            custom_options = instance['openvpn_options'].split('\n')
            options.extend([opt.strip() for opt in custom_options if opt.strip()])
        
        return options
    
    @classmethod
    def get_push_options(cls, instance):
        """Получить push опции в виде списка"""
        push_options = []
        
        # Базовые push опции
        if instance.get('block_ipv6'):
            push_options.append('push "block-ipv6"')
        if instance.get('redirect_gateway'):
            push_options.append('push "redirect-gateway def1 bypass-dhcp"')
        
        # DNS серверы
        if instance.get('dns_servers'):
            dns_servers = instance['dns_servers'].split(',')
            for dns in dns_servers:
                dns = dns.strip()
                if dns:
                    push_options.append(f'push "dhcp-option DNS {dns}"')
        
        # NTP серверы
        if instance.get('ntp_servers'):
            ntp_servers = instance['ntp_servers'].split(',')
            for ntp in ntp_servers:
                ntp = ntp.strip()
                if ntp:
                    push_options.append(f'push "dhcp-option NTP {ntp}"')
        
        # Дополнительные push опции из текстового поля
        if instance.get('push_options'):
            custom_push = instance['push_options'].split('\n')
            push_options.extend([f'push "{opt.strip()}"' for opt in custom_push if opt.strip()])
        
        return push_options