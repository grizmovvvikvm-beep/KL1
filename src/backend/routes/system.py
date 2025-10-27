from flask import Blueprint, jsonify
from ..middleware.auth import login_required, admin_required
from ..utils.logging import logger
import psutil
import os
import time

system_bp = Blueprint('system', __name__)

@system_bp.route('/api/system/info', methods=['GET'])
@login_required
def get_system_info():
    """Получить информацию о системе"""
    try:
        # Системная нагрузка
        load_avg = os.getloadavg()
        
        # Память
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # Диск
        disk = psutil.disk_usage('/')
        
        # Сеть
        net_io = psutil.net_io_counters()
        
        # VPN процессы
        vpn_processes = len([p for p in psutil.process_iter(['name']) 
                           if 'openvpn' in p.info.get('name', '') or 
                           any('openvpn' in arg for arg in p.cmdline())])
        
        system_info = {
            "system": {
                "load_average": [round(load, 2) for load in load_avg],
                "cpu_cores": psutil.cpu_count(),
                "uptime": int(time.time() - psutil.boot_time())
            },
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "percent": memory.percent
            },
            "swap": {
                "total": swap.total,
                "used": swap.used,
                "percent": swap.percent
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent
            },
            "network": {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv
            },
            "services": {
                "vpn_processes": vpn_processes
            },
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return jsonify(system_info)
        
    except Exception as e:
        logger.error(f"Get system info endpoint error: {str(e)}")
        return jsonify({"error": "Failed to get system information"}), 500

@system_bp.route('/api/system/health', methods=['GET'])
@login_required
def health_check():
    """Проверка здоровья системы"""
    try:
        # Проверить доступность БД
        from ..utils.database import get_db_connection
        conn = get_db_connection()
        conn.close()
        
        # Проверить системные ресурсы
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        health_status = {
            "status": "healthy",
            "database": "connected",
            "memory_usage": memory.percent,
            "disk_usage": disk.percent,
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Если использование памяти или диска критическое
        if memory.percent > 90 or disk.percent > 90:
            health_status["status"] = "warning"
            health_status["message"] = "High resource usage detected"
        
        return jsonify(health_status)
        
    except Exception as e:
        logger.error(f"Health check endpoint error: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        }), 500

@system_bp.route('/api/system/audit-logs', methods=['GET'])
@admin_required
def get_audit_logs():
    """Получить аудит-логи"""
    try:
        # TODO: Реализовать получение аудит-логов из БД
        return jsonify({"error": "Not implemented yet"}), 501
        
    except Exception as e:
        logger.error(f"Get audit logs endpoint error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@system_bp.route('/api/system/backups', methods=['GET'])
@admin_required
def get_backups():
    """Получить список бэкапов"""
    try:
        # TODO: Реализовать получение списка бэкапов
        return jsonify({"error": "Not implemented yet"}), 501
        
    except Exception as e:
        logger.error(f"Get backups endpoint error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500