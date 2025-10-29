from flask import Blueprint, request, jsonify, abort
from ..utils import firewall as fw
import logging

logger = logging.getLogger(__name__)
firewall_bp = Blueprint('firewall_bp', __name__)

# Aliases
@firewall_bp.route('/firewall/aliases', methods=['GET'])
def api_list_aliases():
    return jsonify(fw.list_aliases())

@firewall_bp.route('/firewall/aliases/<int:alias_id>', methods=['GET'])
def api_get_alias(alias_id):
    a = fw.get_alias(alias_id)
    if not a: abort(404)
    return jsonify(a)

@firewall_bp.route('/firewall/aliases', methods=['POST'])
def api_create_alias():
    data = request.get_json() or {}
    if 'name' not in data:
        return "name required", 400
    try:
        new_id = fw.create_alias(data)
        return jsonify({'id': new_id}), 201
    except Exception as e:
        logger.exception("create_alias failed")
        return str(e), 500

@firewall_bp.route('/firewall/aliases/<int:alias_id>', methods=['PUT'])
def api_update_alias(alias_id):
    data = request.get_json() or {}
    try:
        fw.update_alias(alias_id, data)
        return '', 204
    except Exception as e:
        logger.exception("update_alias failed")
        return str(e), 500

@firewall_bp.route('/firewall/aliases/<int:alias_id>', methods=['DELETE'])
def api_delete_alias(alias_id):
    try:
        fw.delete_alias(alias_id)
        return '', 204
    except Exception as e:
        logger.exception("delete_alias failed")
        return str(e), 500

# Rules
@firewall_bp.route('/firewall/rules', methods=['GET'])
def api_list_rules():
    return jsonify(fw.list_rules())

@firewall_bp.route('/firewall/rules/<int:rule_id>', methods=['GET'])
def api_get_rule(rule_id):
    r = fw.get_rule(rule_id)
    if not r: abort(404)
    return jsonify(r)

@firewall_bp.route('/firewall/rules', methods=['POST'])
def api_create_rule():
    data = request.get_json() or {}
    if 'name' not in data or 'action' not in data:
        return "name and action required", 400
    try:
        new_id = fw.create_rule(data)
        return jsonify({'id': new_id}), 201
    except Exception as e:
        logger.exception("create_rule failed")
        return str(e), 500

@firewall_bp.route('/firewall/rules/<int:rule_id>', methods=['PUT'])
def api_update_rule(rule_id):
    data = request.get_json() or {}
    try:
        fw.update_rule(rule_id, data)
        return '', 204
    except Exception as e:
        logger.exception("update_rule failed")
        return str(e), 500

@firewall_bp.route('/firewall/rules/<int:rule_id>', methods=['DELETE'])
def api_delete_rule(rule_id):
    try:
        fw.delete_rule(rule_id)
        return '', 204
    except Exception as e:
        logger.exception("delete_rule failed")
        return str(e), 500