import time
import psutil
from datetime import datetime, timedelta
from typing import Dict, List
import threading
import statistics

class PerformanceMonitor:
    def __init__(self):
        self.metrics = {
            "system": [],
            "network": [], 
            "vpn": [],
            "database": []
        }
        self.retention_hours = 24
        self.collection_interval = 60  # seconds
        
    def start_monitoring(self):
        """Start background performance monitoring"""
        def monitor_loop():
            while True:
                try:
                    self.collect_metrics()
                    self.cleanup_old_metrics()
                except Exception as e:
                    logger.error(f"Performance monitoring error: {e}")
                time.sleep(self.collection_interval)
        
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
    
    def collect_metrics(self):
        """Collect performance metrics"""
        timestamp = datetime.now()
        
        # System metrics
        system_metrics = {
            "timestamp": timestamp,
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage("/").percent,
            "load_avg": psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0,
            "swap_percent": psutil.swap_memory().percent
        }
        self.metrics["system"].append(system_metrics)
        
        # Network metrics
        net_io = psutil.net_io_counters()
        network_metrics = {
            "timestamp": timestamp,
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv,
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv
        }
        self.metrics["network"].append(network_metrics)
        
        # VPN metrics
        vpn_metrics = {
            "timestamp": timestamp,
            "active_connections": self._get_vpn_connections(),
            "active_servers": self._get_active_vpn_servers()
        }
        self.metrics["vpn"].append(vpn_metrics)
    
    def _get_vpn_connections(self):
        """Get number of active VPN connections"""
        try:
            # Count OpenVPN processes
            result = subprocess.run(["pgrep", "-c", "openvpn"], 
                                  capture_output=True, text=True)
            return int(result.stdout.strip() or 0)
        except:
            return 0
    
    def _get_active_vpn_servers(self):
        """Get number of active VPN servers"""
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM vpn_instances WHERE status = 'running'")
            count = cur.fetchone()[0]
            cur.close()
            conn.close()
            return count
        except:
            return 0
    
    def cleanup_old_metrics(self):
        """Remove metrics older than retention period"""
        cutoff = datetime.now() - timedelta(hours=self.retention_hours)
        
        for metric_type in self.metrics:
            self.metrics[metric_type] = [
                m for m in self.metrics[metric_type] 
                if m["timestamp"] > cutoff
            ]
    
    def get_performance_report(self, hours: int = 1) -> Dict:
        """Get performance report for specified period"""
        cutoff = datetime.now() - timedelta(hours=hours)
        
        report = {}
        
        for metric_type, metrics in self.metrics.items():
            recent_metrics = [m for m in metrics if m["timestamp"] > cutoff]
            
            if not recent_metrics:
                continue
            
            # Calculate statistics
            if metric_type == "system":
                report[metric_type] = {
                    "cpu_avg": statistics.mean(m["cpu_percent"] for m in recent_metrics),
                    "cpu_max": max(m["cpu_percent"] for m in recent_metrics),
                    "memory_avg": statistics.mean(m["memory_percent"] for m in recent_metrics),
                    "disk_avg": statistics.mean(m["disk_usage"] for m in recent_metrics),
                    "sample_count": len(recent_metrics)
                }
            elif metric_type == "network":
                if len(recent_metrics) > 1:
                    bytes_sent_rate = (recent_metrics[-1]["bytes_sent"] - recent_metrics[0]["bytes_sent"]) / hours
                    bytes_recv_rate = (recent_metrics[-1]["bytes_recv"] - recent_metrics[0]["bytes_recv"]) / hours
                    
                    report[metric_type] = {
                        "bytes_sent_per_hour": bytes_sent_rate,
                        "bytes_recv_per_hour": bytes_recv_rate,
                        "sample_count": len(recent_metrics)
                    }
        
        return report
    
    def get_alerts(self) -> List[Dict]:
        """Get performance-based alerts"""
        alerts = []
        recent_metrics = self.metrics["system"][-10:]  # Last 10 samples
        
        if not recent_metrics:
            return alerts
        
        # Check for high CPU
        cpu_values = [m["cpu_percent"] for m in recent_metrics]
        if statistics.mean(cpu_values) > 80:
            alerts.append({
                "type": "high_cpu",
                "message": f"High CPU usage: {statistics.mean(cpu_values):.1f}% average",
                "level": "warning"
            })
        
        # Check for high memory
        memory_values = [m["memory_percent"] for m in recent_metrics]
        if statistics.mean(memory_values) > 85:
            alerts.append({
                "type": "high_memory", 
                "message": f"High memory usage: {statistics.mean(memory_values):.1f}% average",
                "level": "warning"
            })
        
        return alerts

# Global performance monitor
performance_monitor = PerformanceMonitor()