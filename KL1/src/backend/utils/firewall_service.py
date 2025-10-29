from typing import Optional, List, Dict, Any
from .database import execute_query, get_db_connection
import logging
logger = logging.getLogger(__name__)

# Aliases
def list_aliases() -> List[Dict[str, Any]]:
    rows = execute_query("SELECT id, enabled, name, type, hosts, categories, content, stats, description, created_at FROM firewall_aliases ORDER BY name", fetch=True)
    return [dict(id=r[0], enabled=r[1], name=r[2], type=r[3], hosts=r[4], categories=r[5], content=r[6], stats=r[7], description=r[8], created_at=r[9]) for r in rows]

def get_alias(alias_id: int) -> Optional[Dict[str, Any]]:
    rows = execute_query("SELECT id, enabled, name, type, hosts, categories, content, stats, description, created_at FROM firewall_aliases WHERE id = %s", (alias_id,), fetch=True)
    if not rows: return None
    r = rows[0]
    return dict(id=r[0], enabled=r[1], name=r[2], type=r[3], hosts=r[4], categories=r[5], content=r[6], stats=r[7], description=r[8], created_at=r[9])

def create_alias(data: Dict[str, Any]) -> int:
    q = """
    INSERT INTO firewall_aliases (enabled, name, type, hosts, categories, content, stats, description)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
    """
    stats = data.get('stats') or {}
    rows = execute_query(q, (data.get('enabled', True), data['name'], data.get('type','Host'), data.get('hosts',''), data.get('categories',''), data.get('content',''), json_dumps(stats), data.get('description','')), fetch=True)
    return rows[0][0]

def update_alias(alias_id:int, data:Dict[str,Any]) -> bool:
    q = """
    UPDATE firewall_aliases SET enabled=%s,name=%s,type=%s,hosts=%s,categories=%s,content=%s,stats=%s,description=%s,updated_at=NOW()
    WHERE id=%s
    """
    stats = data.get('stats') or {}
    execute_query(q, (data.get('enabled', True), data['name'], data.get('type','Host'), data.get('hosts',''), data.get('categories',''), data.get('content',''), json_dumps(stats), data.get('description',''), alias_id))
    return True

def delete_alias(alias_id:int) -> bool:
    execute_query("DELETE FROM firewall_aliases WHERE id = %s", (alias_id,))
    return True

# Rules
def list_rules() -> List[Dict[str, Any]]:
    rows = execute_query("""SELECT r.id,r.enabled,r.name,r.action,r.protocol,r.source,r.destination,r.vpn_instance_id,r.description,
                             v.name as vpn_name FROM firewall_rules r
                             LEFT JOIN vpn_instances v ON r.vpn_instance_id = v.id ORDER BY r.created_at""", fetch=True)
    result = []
    for r in rows:
        result.append({
            'id': r[0], 'enabled': r[1], 'name': r[2], 'action': r[3], 'protocol': r[4],
            'source': r[5], 'destination': r[6], 'vpn_instance_id': r[7], 'description': r[8],
            'vpn_instance_name': r[9]
        })
    return result

def get_rule(rule_id:int) -> Optional[Dict[str,Any]]:
    rows = execute_query("SELECT id,enabled,name,action,protocol,source,destination,vpn_instance_id,description FROM firewall_rules WHERE id=%s", (rule_id,), fetch=True)
    if not rows: return None
    r = rows[0]
    return {'id':r[0],'enabled':r[1],'name':r[2],'action':r[3],'protocol':r[4],'source':r[5],'destination':r[6],'vpn_instance_id':r[7],'description':r[8]}

def create_rule(data:Dict[str,Any]) -> int:
    q = """INSERT INTO firewall_rules (enabled,name,action,protocol,source,destination,vpn_instance_id,description)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id"""
    rows = execute_query(q, (data.get('enabled',True), data['name'], data['action'], data.get('protocol','any'),
                             data.get('source',''), data.get('destination',''), data.get('vpn_instance_id'), data.get('description','')), fetch=True)
    rule_id = rows[0][0]
    # placeholder: apply_rule(rule_id)
    return rule_id

def update_rule(rule_id:int, data:Dict[str,Any]) -> bool:
    q = """UPDATE firewall_rules SET enabled=%s,name=%s,action=%s,protocol=%s,source=%s,destination=%s,vpn_instance_id=%s,description=%s,updated_at=NOW()
           WHERE id=%s"""
    execute_query(q, (data.get('enabled',True), data['name'], data['action'], data.get('protocol','any'),
                      data.get('source',''), data.get('destination',''), data.get('vpn_instance_id'), data.get('description',''), rule_id))
    # placeholder: reapply
    return True

def delete_rule(rule_id:int) -> bool:
    execute_query("DELETE FROM firewall_rules WHERE id=%s", (rule_id,))
    return True

# Small helper to avoid importing json in many places
import json
def json_dumps(o):
    return json.dumps(o)