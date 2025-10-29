import logging
import logging.handlers
import json
from datetime import datetime
from pathlib import Path
import gzip
import shutil

class StructuredLogger:
    def __init__(self, app_dir: str = "/opt/kurs-light"):
        self.app_dir = Path(app_dir)
        self.log_dir = self.app_dir / "logs"
        self.log_dir.mkdir(exist_ok=True)
        
        self.setup_logging()
    
    def setup_logging(self):
        """Setup structured logging with multiple handlers"""
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        
        # Clear existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # JSON formatter for structured logging
        json_formatter = logging.Formatter(
            '{"time": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", '
            '"message": "%(message)s", "module": "%(module)s", "function": "%(funcName)s"}'
        )
        
        # Standard formatter
        standard_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # File handlers for different log types
        handlers = {
            "application": {
                "filename": self.log_dir / "app.log",
                "maxBytes": 10 * 1024 * 1024,  # 10MB
                "backupCount": 5
            },
            "security": {
                "filename": self.log_dir / "security.log", 
                "maxBytes": 5 * 1024 * 1024,   # 5MB
                "backupCount": 10
            },
            "vpn": {
                "filename": self.log_dir / "vpn.log",
                "maxBytes": 20 * 1024 * 1024,  # 20MB
                "backupCount": 3
            },
            "database": {
                "filename": self.log_dir / "database.log",
                "maxBytes": 5 * 1024 * 1024,   # 5MB
                "backupCount": 5
            }
        }
        
        for log_type, config in handlers.items():
            handler = logging.handlers.RotatingFileHandler(
                filename=config["filename"],
                maxBytes=config["maxBytes"],
                backupCount=config["backupCount"]
            )
            
            if log_type == "application":
                handler.setFormatter(json_formatter)
            else:
                handler.setFormatter(standard_formatter)
            
            # Add filter for log type
            handler.addFilter(LogTypeFilter(log_type))
            logger.addHandler(handler)
        
        # Console handler for development
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(standard_formatter)
        logger.addHandler(console_handler)
    
    def log_structured(self, level: str, message: str, **extra):
        """Log structured data with extra fields"""
        log_data = {
            "message": message,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level.upper(),
            **extra
        }
        
        logger = logging.getLogger("kurslight")
        
        if level == "info":
            logger.info(json.dumps(log_data))
        elif level == "warning":
            logger.warning(json.dumps(log_data))
        elif level == "error":
            logger.error(json.dumps(log_data))
        elif level == "critical":
            logger.critical(json.dumps(log_data))
    
    def cleanup_old_logs(self, days: int = 30):
        """Clean up log files older than specified days"""
        cutoff_time = datetime.now().timestamp() - (days * 24 * 60 * 60)
        
        for log_file in self.log_dir.rglob("*.log*"):
            if log_file.stat().st_mtime < cutoff_time:
                log_file.unlink()
                self.log_structured("info", f"Removed old log file", 
                                  file_path=str(log_file))
    
    def compress_old_logs(self):
        """Compress log files older than 7 days"""
        cutoff_time = datetime.now().timestamp() - (7 * 24 * 60 * 60)
        
        for log_file in self.log_dir.glob("*.log.*"):  # Rotated logs
            if log_file.stat().st_mtime < cutoff_time and not log_file.suffix == ".gz":
                compressed_file = log_file.with_suffix('.gz')
                
                with open(log_file, 'rb') as f_in:
                    with gzip.open(compressed_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                log_file.unlink()
                self.log_structured("info", f"Compressed log file", 
                                  original=str(log_file), compressed=str(compressed_file))

class LogTypeFilter(logging.Filter):
    def __init__(self, log_type):
        super().__init__()
        self.log_type = log_type
    
    def filter(self, record):
        record.log_type = self.log_type
        return True

# Global logger instance
log_manager = StructuredLogger()