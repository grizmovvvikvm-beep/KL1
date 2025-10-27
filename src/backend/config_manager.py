import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

class ConfigManager:
    def __init__(self, config_dir: str = "/opt/kurs-light/config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
    def load_config(self, config_type: str) -> Dict[str, Any]:
        """Load configuration from file"""
        config_file = self.config_dir / f"{config_type}.json"
        if config_file.exists():
            with open(config_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_config(self, config_type: str, config: Dict[str, Any]) -> bool:
        """Save configuration to file"""
        try:
            config_file = self.config_dir / f"{config_type}.json"
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            # Backup current config
            self._backup_config(config_type)
            return True
        except Exception as e:
            logger.error(f"Failed to save config {config_type}: {e}")
            return False
    
    def _backup_config(self, config_type: str):
        """Create backup of configuration"""
        config_file = self.config_dir / f"{config_type}.json"
        backup_file = self.config_dir / f"backups/{config_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        backup_file.parent.mkdir(exist_ok=True)
        if config_file.exists():
            import shutil
            shutil.copy2(config_file, backup_file)
    
    def validate_config(self, config_type: str, config: Dict[str, Any]) -> tuple[bool, str]:
        """Validate configuration schema"""
        schemas = {
            "vpn_server": {
                "required": ["name", "port", "protocol", "subnet"],
                "types": {
                    "name": str, "port": int, "protocol": str, "subnet": str,
                    "max_clients": int, "encryption": str
                }
            },
            "radius": {
                "required": ["enabled", "server", "port"],
                "types": {
                    "enabled": bool, "server": str, "port": int, 
                    "secret": str, "timeout": int
                }
            }
        }
        
        if config_type not in schemas:
            return True, "No validation schema"
        
        schema = schemas[config_type]
        
        # Check required fields
        for field in schema["required"]:
            if field not in config:
                return False, f"Missing required field: {field}"
        
        # Check field types
        for field, expected_type in schema["types"].items():
            if field in config and not isinstance(config[field], expected_type):
                return False, f"Field {field} should be {expected_type.__name__}"
        
        return True, "Configuration is valid"

config_manager = ConfigManager()