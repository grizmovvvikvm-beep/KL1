import os
import subprocess
import logging
from pathlib import Path
from ..config import config

logger = logging.getLogger(__name__)

class CertificateService:
    """Сервис для управления SSL сертификатами"""
    
    def __init__(self):
        self.openssl_bin = self._find_openssl()
    
    def _find_openssl(self):
        """Найти бинарник OpenSSL"""
        for path in ['/usr/bin/openssl', '/bin/openssl', '/usr/local/bin/openssl']:
            if Path(path).exists():
                return path
        raise RuntimeError("OpenSSL not found")
    
    def generate_ca(self):
        """Сгенерировать корневой сертификат (CA)"""
        try:
            config.CA_DIR.mkdir(parents=True, exist_ok=True)
            
            # Генерация приватного ключа CA
            ca_key = config.CA_DIR / 'ca.key'
            subprocess.run([
                self.openssl_bin, 'genrsa', '-out', str(ca_key), '2048'
            ], check=True, capture_output=True)
            
            # Генерация сертификата CA
            ca_crt = config.CA_DIR / 'ca.crt'
            subprocess.run([
                self.openssl_bin, 'req', '-new', '-x509', '-days', '3650',
                '-key', str(ca_key), '-out', str(ca_crt),
                '-subj', '/C=RU/ST=Moscow/L=Moscow/O=KursLight/CN=KursLight CA'
            ], check=True, capture_output=True)
            
            # Генерация DH параметров
            dh_pem = config.CA_DIR / 'dh.pem'
            subprocess.run([
                self.openssl_bin, 'dhparam', '-out', str(dh_pem), '2048'
            ], check=True, capture_output=True)
            
            # Генерация TLS static key
            ta_key = config.CA_DIR / 'ta.key'
            openvpn_bin = config.OPENVPN_BIN
            if Path(openvpn_bin).exists():
                subprocess.run([
                    openvpn_bin, '--genkey', '--secret', str(ta_key)
                ], check=True, capture_output=True)
            
            logger.info("CA certificates generated successfully")
            return True, None
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to generate CA: {e.stderr.decode() if e.stderr else str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            logger.error(f"Error generating CA: {str(e)}")
            return False, str(e)
    
    def generate_server_certificate(self, server_name):
        """Сгенерировать серверный сертификат"""
        try:
            config.CERTS_DIR.mkdir(parents=True, exist_ok=True)
            
            # Генерация приватного ключа сервера
            server_key = config.CERTS_DIR / 'server.key'
            subprocess.run([
                self.openssl_bin, 'genrsa', '-out', str(server_key), '2048'
            ], check=True, capture_output=True)
            
            # Создание запроса на сертификат
            server_csr = config.CERTS_DIR / 'server.csr'
            subprocess.run([
                self.openssl_bin, 'req', '-new',
                '-key', str(server_key), '-out', str(server_csr),
                '-subj', f'/C=RU/ST=Moscow/L=Moscow/O=KursLight/CN={server_name}'
            ], check=True, capture_output=True)
            
            # Подписание сертификата CA
            server_crt = config.CERTS_DIR / 'server.crt'
            subprocess.run([
                self.openssl_bin, 'x509', '-req', '-days', '3650',
                '-in', str(server_csr), '-CA', str(config.CA_DIR / 'ca.crt'),
                '-CAkey', str(config.CA_DIR / 'ca.key'), '-CAcreateserial',
                '-out', str(server_crt)
            ], check=True, capture_output=True)
            
            # Очистка временных файлов
            server_csr.unlink(missing_ok=True)
            
            logger.info(f"Server certificate generated for {server_name}")
            return True, None
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to generate server certificate: {e.stderr.decode() if e.stderr else str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            logger.error(f"Error generating server certificate: {str(e)}")
            return False, str(e)
    
    def generate_client_certificate(self, client_name, server_name):
        """Сгенерировать клиентский сертификат"""
        try:
            clients_dir = config.CERTS_DIR / 'clients' / server_name
            clients_dir.mkdir(parents=True, exist_ok=True)
            
            # Генерация приватного ключа клиента
            client_key = clients_dir / f'{client_name}.key'
            subprocess.run([
                self.openssl_bin, 'genrsa', '-out', str(client_key), '2048'
            ], check=True, capture_output=True)
            
            # Создание запроса на сертификат
            client_csr = clients_dir / f'{client_name}.csr'
            subprocess.run([
                self.openssl_bin, 'req', '-new',
                '-key', str(client_key), '-out', str(client_csr),
                '-subj', f'/C=RU/ST=Moscow/L=Moscow/O=KursLight/CN={client_name}'
            ], check=True, capture_output=True)
            
            # Подписание сертификата CA
            client_crt = clients_dir / f'{client_name}.crt'
            subprocess.run([
                self.openssl_bin, 'x509', '-req', '-days', '3650',
                '-in', str(client_csr), '-CA', str(config.CA_DIR / 'ca.crt'),
                '-CAkey', str(config.CA_DIR / 'ca.key'), '-CAcreateserial',
                '-out', str(client_crt)
            ], check=True, capture_output=True)
            
            # Очистка временных файлов
            client_csr.unlink(missing_ok=True)
            
            # Чтение сертификатов для возврата
            with open(client_key, 'r') as f:
                key_content = f.read()
            with open(client_crt, 'r') as f:
                cert_content = f.read()
            with open(config.CA_DIR / 'ca.crt', 'r') as f:
                ca_content = f.read()
            
            logger.info(f"Client certificate generated: {client_name}")
            return True, {
                'key': key_content,
                'cert': cert_content,
                'ca': ca_content
            }
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to generate client certificate: {e.stderr.decode() if e.stderr else str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            logger.error(f"Error generating client certificate: {str(e)}")
            return False, str(e)
    
    def revoke_client_certificate(self, client_name, server_name):
        """Отозвать клиентский сертификат"""
        try:
            # Создать CRL если не существует
            crl_file = config.CA_DIR / 'crl.pem'
            if not crl_file.exists():
                subprocess.run([
                    self.openssl_bin, 'ca', '-gencrl',
                    '-keyfile', str(config.CA_DIR / 'ca.key'),
                    '-cert', str(config.CA_DIR / 'ca.crt'),
                    '-out', str(crl_file)
                ], check=True, capture_output=True)
            
            # Отозвать сертификат
            client_crt = config.CERTS_DIR / 'clients' / server_name / f'{client_name}.crt'
            if client_crt.exists():
                subprocess.run([
                    self.openssl_bin, 'ca', '-revoke', str(client_crt),
                    '-keyfile', str(config.CA_DIR / 'ca.key'),
                    '-cert', str(config.CA_DIR / 'ca.crt')
                ], check=True, capture_output=True)
                
                # Обновить CRL
                subprocess.run([
                    self.openssl_bin, 'ca', '-gencrl',
                    '-keyfile', str(config.CA_DIR / 'ca.key'),
                    '-cert', str(config.CA_DIR / 'ca.crt'),
                    '-out', str(crl_file)
                ], check=True, capture_output=True)
                
                logger.info(f"Client certificate revoked: {client_name}")
                return True, None
            else:
                return False, "Client certificate not found"
                
        except subprocess.CalledProcessError as e:
            error_msg = f"Failed to revoke certificate: {e.stderr.decode() if e.stderr else str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            logger.error(f"Error revoking certificate: {str(e)}")
            return False, str(e)
    
    def get_crl(self):
        """Получить текущий CRL"""
        crl_file = config.CA_DIR / 'crl.pem'
        if crl_file.exists():
            with open(crl_file, 'r') as f:
                return f.read()
        return None