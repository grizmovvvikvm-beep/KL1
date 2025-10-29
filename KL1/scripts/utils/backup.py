#!/usr/bin/env python3
import os
import shutil
import tarfile
import datetime
import subprocess
import json
from pathlib import Path

class BackupManager:
    def __init__(self, app_dir="/opt/kurs-light"):
        self.app_dir = Path(app_dir)
        self.backup_dir = self.app_dir / "backups"
        self.backup_dir.mkdir(exist_ok=True)
    
    def create_backup(self, include_database=True, include_certs=True, include_configs=True):
        """Create comprehensive backup"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"backup_{timestamp}"
        backup_path.mkdir()
        
        backup_info = {
            "timestamp": timestamp,
            "version": "1.0.0",
            "components": []
        }
        
        try:
            # Backup database
            if include_database:
                self._backup_database(backup_path)
                backup_info["components"].append("database")
            
            # Backup certificates
            if include_certs:
                self._backup_certificates(backup_path)
                backup_info["components"].append("certificates")
            
            # Backup configurations
            if include_configs:
                self._backup_configurations(backup_path)
                backup_info["components"].append("configurations")
            
            # Create backup info file
            with open(backup_path / "backup_info.json", "w") as f:
                json.dump(backup_info, f, indent=2)
            
            # Create archive
            archive_name = f"kurslight_backup_{timestamp}.tar.gz"
            self._create_archive(backup_path, archive_name)
            
            # Cleanup
            shutil.rmtree(backup_path)
            
            return {"success": True, "archive": archive_name, "components": backup_info["components"]}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _backup_database(self, backup_path):
        """Backup PostgreSQL database"""
        db_backup_path = backup_path / "database"
        db_backup_path.mkdir()
        
        # Backup main database
        subprocess.run([
            "pg_dump", "-U", "kurslight_user", "-d", "kurslight_db",
            "-f", str(db_backup_path / "kurslight_db.sql")
        ], check=True)
        
        # Backup RADIUS database
        subprocess.run([
            "pg_dump", "-U", "kurslight_radius", "-d", "kurslight_radius",
            "-f", str(db_backup_path / "kurslight_radius.sql")
        ], check=True)
    
    def _backup_certificates(self, backup_path):
        """Backup SSL and VPN certificates"""
        certs_backup_path = backup_path / "certificates"
        shutil.copytree(self.app_dir / "ca", certs_backup_path / "ca")
        shutil.copytree(self.app_dir / "ssl", certs_backup_path / "ssl")
        shutil.copytree(self.app_dir / "certs", certs_backup_path / "certs")
    
    def _backup_configurations(self, backup_path):
        """Backup system configurations"""
        config_backup_path = backup_path / "configurations"
        config_backup_path.mkdir()
        
        # Backup app config
        shutil.copy2(self.app_dir / "config.xml", config_backup_path)
        
        # Backup system configs
        shutil.copytree("/etc/raddb", config_backup_path / "raddb")
        shutil.copytree("/etc/openvpn", config_backup_path / "openvpn")
        shutil.copy2("/etc/nginx/conf.d/kurs-light.conf", config_backup_path)
    
    def _create_archive(self, backup_path, archive_name):
        """Create compressed archive"""
        with tarfile.open(self.backup_dir / archive_name, "w:gz") as tar:
            tar.add(backup_path, arcname="backup")
    
    def list_backups(self):
        """List available backups"""
        backups = []
        for file in self.backup_dir.glob("kurslight_backup_*.tar.gz"):
            stats = file.stat()
            backups.append({
                "name": file.name,
                "size": stats.st_size,
                "created": datetime.datetime.fromtimestamp(stats.st_ctime).isoformat()
            })
        
        return sorted(backups, key=lambda x: x["created"], reverse=True)
    
    def restore_backup(self, archive_name, components=None):
        """Restore from backup"""
        # Implementation for restore
        pass

if __name__ == "__main__":
    manager = BackupManager()
    result = manager.create_backup()
    print(json.dumps(result, indent=2))