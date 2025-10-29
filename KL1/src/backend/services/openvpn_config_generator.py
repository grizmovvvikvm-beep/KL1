import os
import logging
from pathlib import Path
from ..config import config
from ..models.vpn import VPNModel

logger = logging.getLogger(__name__)

class OpenVPNConfigGenerator:
    """Генератор конфигурационных файлов OpenVPN"""
    
    def __init__(self):
        self.config_templates = {
            'server': self._get_server_template(),
            'client': self._get_client_template()
        }
    
    def generate_server_config(self, vpn_instance):
        """Сгенерировать конфигурационный файл сервера"""
        try:
            template = self.config_templates['server']
            config_content = self._render_server_config(template, vpn_instance)
            
            # Создать директорию для инстанса
            instance_dir = config.OPENVPN_DIR / 'servers' / vpn_instance['name']
            instance_dir.mkdir(parents=True, exist_ok=True)
            
            # Сохранить конфиг
            config_file = instance_dir / 'server.conf'
            with open(config_file, 'w') as f:
                f.write(config_content)
            
            # Установить правильные права
            os.chmod(config_file, 0o600)
            
            logger.info(f"Server config generated for {vpn_instance['name']}")
            return True, config_file
            
        except Exception as e:
            logger.error(f"Failed to generate server config for {vpn_instance['name']}: {str(e)}")
            return False, str(e)
    
    def generate_client_config(self, vpn_instance, client_name, client_cert, client_key, ca_cert):
        """Сгенерировать конфигурационный файл клиента"""
        try:
            template = self.config_templates['client']
            config_content = self._render_client_config(
                template, vpn_instance, client_name, client_cert, client_key, ca_cert
            )
            
            # Сохранить конфиг клиента
            clients_dir = config.OPENVPN_DIR / 'clients' / vpn_instance['name']
            clients_dir.mkdir(parents=True, exist_ok=True)
            
            config_file = clients_dir / f'{client_name}.ovpn'
            with open(config_file, 'w') as f:
                f.write(config_content)
            
            logger.info(f"Client config generated: {client_name} for {vpn_instance['name']}")
            return True, config_file
            
        except Exception as e:
            logger.error(f"Failed to generate client config for {client_name}: {str(e)}")
            return False, str(e)
    
    def _render_server_config(self, template, instance):
        """Заполнить шаблон конфигурации сервера"""
        config_lines = []
        
        # Базовые настройки
        config_lines.append(f"port {instance['port']}")
        config_lines.append(f"proto {instance['protocol']}")
        config_lines.append(f"dev {instance['interface_type']}")
        config_lines.append(f"topology {instance['topology']}")
        
        # Сертификаты и безопасность
        config_lines.append(f"ca {config.CA_DIR / 'ca.crt'}")
        config_lines.append(f"cert {config.CERTS_DIR / 'server.crt'}")
        config_lines.append(f"key {config.CERTS_DIR / 'server.key'}")
        config_lines.append(f"dh {config.CA_DIR / 'dh.pem'}")
        
        if instance.get('tls_auth'):
            config_lines.append(f"tls-auth {config.CA_DIR / 'ta.key'} 0")
        
        if instance.get('crl_enabled'):
            config_lines.append(f"crl-verify {config.CA_DIR / 'crl.pem'}")
        
        # Настройки сервера
        config_lines.append(f"server {instance['subnet'].replace('/24', '')} 255.255.255.0")
        config_lines.append(f"ifconfig-pool-persist ipp.txt")
        
        # Keepalive
        config_lines.append("keepalive 10 120")
        
        # Шифрование
        config_lines.append("cipher AES-256-CBC")
        config_lines.append("auth SHA256")
        
        # Привилегии
        config_lines.append("user nobody")
        config_lines.append("group nobody")
        config_lines.append("persist-key")
        config_lines.append("persist-tun")
        
        # Логирование
        log_file = config.LOGS_DIR / f"openvpn-{instance['name']}.log"
        config_lines.append(f"status {log_file}")
        config_lines.append("status-version 3")
        config_lines.append("log-append /var/log/openvpn.log")
        config_lines.append("verb 3")
        
        # Дополнительные опции
        if instance.get('verify_client'):
            config_lines.append("verify-client-cert require")
        
        if instance.get('verify_remote_cert'):
            config_lines.append("remote-cert-tls client")
        
        if instance.get('strict_user_cn'):
            config_lines.append("username-as-common-name")
        
        if instance.get('renegotiate_time'):
            config_lines.append(f"reneg-sec {instance['renegotiate_time']}")
        
        # OpenVPN опции
        openvpn_options = VPNModel.get_openvpn_options(instance)
        config_lines.extend(openvpn_options)
        
        # Push опции
        push_options = VPNModel.get_push_options(instance)
        config_lines.extend(push_options)
        
        # Локальная сеть
        if instance.get('local_network'):
            local_nets = instance['local_network'].split(',')
            for net in local_nets:
                net = net.strip()
                if net:
                    config_lines.append(f'push "route {net}"')
        
        return '\n'.join(config_lines) + '\n'
    
    def _render_client_config(self, template, instance, client_name, client_cert, client_key, ca_cert):
        """Заполнить шаблон конфигурации клиента"""
        config_lines = []
        
        # Базовые настройки клиента
        config_lines.append("client")
        config_lines.append(f"dev {instance['interface_type']}")
        config_lines.append(f"proto {instance['protocol']}")
        config_lines.append("resolv-retry infinite")
        config_lines.append("nobind")
        config_lines.append("persist-key")
        config_lines.append("persist-tun")
        
        # Сертификаты (встроенные в конфиг)
        config_lines.append("<ca>")
        config_lines.append(ca_cert)
        config_lines.append("</ca>")
        
        config_lines.append("<cert>")
        config_lines.append(client_cert)
        config_lines.append("</cert>")
        
        config_lines.append("<key>")
        config_lines.append(client_key)
        config_lines.append("</key>")
        
        if instance.get('tls_auth'):
            config_lines.append("<tls-auth>")
            # Здесь должен быть ta.key
            config_lines.append("</tls-auth>")
            config_lines.append("key-direction 1")
        
        # Шифрование
        config_lines.append("remote-cert-tls server")
        config_lines.append("cipher AES-256-CBC")
        config_lines.append("auth SHA256")
        
        # Дополнительные настройки
        config_lines.append("verb 3")
        
        return '\n'.join(config_lines) + '\n'
    
    def _get_server_template(self):
        """Шаблон конфигурации сервера"""
        return """# OpenVPN Server Configuration
# Generated by KursLight VPN Management System
# Server: {name}

"""
    
    def _get_client_template(self):
        """Шаблон конфигурации клиента"""
        return """# OpenVPN Client Configuration
# Generated by KursLight VPN Management System
# Client: {client_name}
# Server: {server_name}

"""