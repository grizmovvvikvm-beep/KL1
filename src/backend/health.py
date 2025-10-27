import psutil
import time
import threading
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MimeText

class HealthMonitor:
    def __init__(self):
        self.metrics = {
            "system": {},
            "services": {},
            "vpn": {},
            "database": {}
        }
        self.alerts = []
        self.alert_config = {
            "cpu_threshold": 80,
            "memory_threshold": 85,
            "disk_threshold": 90,
            "vpn_connections_threshold": 1000
        }
    
    def collect_metrics(self):
        """Collect system and service metrics"""
        # System metrics
        self.metrics["system"] = {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
            "load_avg": os.getloadavg(),
            "uptime": time.time() - psutil.boot_time()
        }
        
        # Service metrics
        self.metrics["services"] = {
            "postgresql": self._check_service("postgresql"),
            "nginx": self._check_service("nginx"),
            "radiusd": self._check_service("radiusd"),
            "kurs-light": self._check_service("kurs-light")
        }
        
        # VPN metrics
        self.metrics["vpn"] = self._get_vpn_metrics()
        
        # Check for alerts
        self._check_alerts()
    
    def _check_service(self, service_name):
        """Check if service is running"""
        try:
            result = subprocess.run(
                ["systemctl", "is-active", service_name],
                capture_output=True, text=True
            )
            return result.stdout.strip() == "active"
        except:
            return False
    
    def _get_vpn_metrics(self):
        """Get VPN-specific metrics"""
        metrics = {
            "total_connections": 0,
            "active_servers": 0,
            "bandwidth_usage": 0
        }
        
        try:
            # Count OpenVPN processes
            result = subprocess.run(["pgrep", "-c", "openvpn"], capture_output=True, text=True)
            metrics["active_servers"] = int(result.stdout.strip() or 0)
            
            # Get connection count from database
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM vpn_connection_logs WHERE action = 'connect'")
            metrics["total_connections"] = cur.fetchone()[0]
            cur.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error getting VPN metrics: {e}")
        
        return metrics
    
    def _check_alerts(self):
        """Check metrics against thresholds and trigger alerts"""
        current_time = datetime.now()
        
        # CPU alert
        if self.metrics["system"]["cpu_percent"] > self.alert_config["cpu_threshold"]:
            self._trigger_alert("high_cpu", f"CPU usage is {self.metrics['system']['cpu_percent']}%")
        
        # Memory alert
        if self.metrics["system"]["memory_percent"] > self.alert_config["memory_threshold"]:
            self._trigger_alert("high_memory", f"Memory usage is {self.metrics['system']['memory_percent']}%")
        
        # Service alerts
        for service, status in self.metrics["services"].items():
            if not status:
                self._trigger_alert("service_down", f"Service {service} is down")
    
    def _trigger_alert(self, alert_type, message):
        """Trigger an alert"""
        alert = {
            "type": alert_type,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "resolved": False
        }
        
        self.alerts.append(alert)
        logger.warning(f"ALERT: {message}")
        
        # Send notification (email, webhook, etc.)
        self._send_notification(alert)
    
    def _send_notification(self, alert):
        """Send alert notification"""
        # Implement email, Slack, webhook notifications
        pass
    
    def get_health_status(self):
        """Get overall health status"""
        critical_services = ["postgresql", "kurs-light"]
        services_ok = all(self.metrics["services"].get(s, False) for s in critical_services)
        
        system_ok = (
            self.metrics["system"]["cpu_percent"] < 90 and
            self.metrics["system"]["memory_percent"] < 95 and
            self.metrics["system"]["disk_percent"] < 95
        )
        
        return {
            "status": "healthy" if (services_ok and system_ok) else "unhealthy",
            "services_ok": services_ok,
            "system_ok": system_ok,
            "active_alerts": len([a for a in self.alerts if not a["resolved"]]),
            "timestamp": datetime.now().isoformat()
        }

# Global health monitor instance
health_monitor = HealthMonitor()

def start_health_monitoring():
    """Start background health monitoring"""
    def monitor_loop():
        while True:
            try:
                health_monitor.collect_metrics()
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
            time.sleep(60)  # Check every minute
    
    monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
    monitor_thread.start()