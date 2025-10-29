from flask import Blueprint, request, jsonify
from ..services.vpn_service import VPNService
from ..middleware.auth import login_required
from ..utils.logging import logger

vpn_bp = Blueprint('vpn', __name__)
vpn_service = VPNService()

@vpn_bp.route('/api/vpn-instances', methods=['GET'])
@login_required
def get_vpn_instances():
    """Получить список всех VPN инстансов"""
    try:
        instances, error = vpn_service.get_all_instances()
        
        if error:
            return jsonify({"error": error}), 500
        
        return jsonify(instances)
        
    except Exception as e:
        logger.error(f"Get VPN instances endpoint error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@vpn_bp.route('/api/vpn-instances/<instance_name>/start', methods=['POST'])
@login_required
def start_vpn_instance(instance_name):
    """Запустить VPN инстанс"""
    try:
        success, error = vpn_service.start_instance(instance_name)
        
        if error:
            return jsonify({"error": error}), 400
        
        logger.info(f"VPN instance started by {request.user.get('username', 'unknown')}: {instance_name}")
        return jsonify({"message": f"VPN instance '{instance_name}' started successfully"})
        
    except Exception as e:
        logger.error(f"Start VPN instance endpoint error for {instance_name}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@vpn_bp.route('/api/vpn-instances/<instance_name>/stop', methods=['POST'])
@login_required
def stop_vpn_instance(instance_name):
    """Остановить VPN инстанс"""
    try:
        success, error = vpn_service.stop_instance(instance_name)
        
        if error:
            return jsonify({"error": error}), 400
        
        logger.info(f"VPN instance stopped by {request.user.get('username', 'unknown')}: {instance_name}")
        return jsonify({"message": f"VPN instance '{instance_name}' stopped successfully"})
        
    except Exception as e:
        logger.error(f"Stop VPN instance endpoint error for {instance_name}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@vpn_bp.route('/api/vpn-instances/<instance_name>/restart', methods=['POST'])
@login_required
def restart_vpn_instance(instance_name):
    """Перезапустить VPN инстанс"""
    try:
        # Остановить инстанс
        stop_success, stop_error = vpn_service.stop_instance(instance_name)
        if stop_error:
            return jsonify({"error": f"Failed to stop: {stop_error}"}), 400
        
        # Запустить инстанс
        start_success, start_error = vpn_service.start_instance(instance_name)
        if start_error:
            return jsonify({"error": f"Failed to start: {start_error}"}), 400
        
        logger.info(f"VPN instance restarted by {request.user.get('username', 'unknown')}: {instance_name}")
        return jsonify({"message": f"VPN instance '{instance_name}' restarted successfully"})
        
    except Exception as e:
        logger.error(f"Restart VPN instance endpoint error for {instance_name}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@vpn_bp.route('/api/vpn-instances/<instance_name>/status', methods=['GET'])
@login_required
def get_vpn_instance_status(instance_name):
    """Получить статус VPN инстанса"""
    try:
        instances, error = vpn_service.get_all_instances()
        
        if error:
            return jsonify({"error": error}), 500
        
        instance = next((i for i in instances if i['name'] == instance_name), None)
        if not instance:
            return jsonify({"error": "VPN instance not found"}), 404
        
        return jsonify({
            "name": instance['name'],
            "status": instance['status'],
            "active_clients": instance['active_clients'],
            "max_clients": instance['max_clients']
        })
        
    except Exception as e:
        logger.error(f"Get VPN instance status endpoint error for {instance_name}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500