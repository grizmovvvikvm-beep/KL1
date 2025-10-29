import json
import yaml
from pathlib import Path
from typing import Dict, Any
from .config import config, ConfigurationError

class ConfigManager:
    """Менеджер для работы с конфигурационными файлами"""
    
    @staticmethod
    def save_config(data: Dict[str, Any]) -> bool:
        """Сохранить конфигурацию в файл"""
        try:
            config.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            
            # Сохранить в JSON
            with open(config.CONFIG_FILE.with_suffix('.json'), 'w') as f:
                json.dump(data, f, indent=2)
            
            # Сохранить в YAML
            with open(config.CONFIG_FILE.with_suffix('.yaml'), 'w') as f:
                yaml.dump(data, f, default_flow_style=False)
            
            return True
            
        except Exception as e:
            raise ConfigurationError(f"Failed to save config: {str(e)}")
    
    @staticmethod
    def load_config() -> Dict[str, Any]:
        """Загрузить конфигурацию из файла"""
        try:
            json_file = config.CONFIG_FILE.with_suffix('.json')
            yaml_file = config.CONFIG_FILE.with_suffix('.yaml')
            
            if json_file.exists():
                with open(json_file, 'r') as f:
                    return json.load(f)
            elif yaml_file.exists():
                with open(yaml_file, 'r') as f:
                    return yaml.safe_load(f)
            else:
                return {}
                
        except Exception as e:
            raise ConfigurationError(f"Failed to load config: {str(e)}")
    
    @staticmethod
    def export_env_file() -> str:
        """Экспортировать текущую конфигурацию в .env формат"""
        env_lines = []
        
        for key, value in config.to_dict().items():
            if isinstance(value, dict):
                for subkey, subvalue in value.items():
                    env_lines.append(f"KL_{key.upper()}_{subkey.upper()}={subvalue}")
            else:
                env_lines.append(f"KL_{key.upper()}={value}")
        
        return "\n".join(env_lines)