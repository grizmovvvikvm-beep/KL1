#!/usr/bin/env python3
import sys
import os
import psycopg2
from datetime import datetime
import logging

# Add the parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import get_db_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseMigrator:
    def __init__(self):
        self.migrations_dir = Path(__file__).parent / "migrations"
        self.migrations_dir.mkdir(exist_ok=True)
    
    def create_migration_table(self):
        """Create migrations table if it doesn't exist"""
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute('''
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id SERIAL PRIMARY KEY,
                version VARCHAR(50) UNIQUE NOT NULL,
                name VARCHAR(255) NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        cur.close()
        conn.close()
    
    def get_applied_migrations(self):
        """Get list of applied migrations"""
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT version FROM schema_migrations ORDER BY applied_at")
        migrations = [row[0] for row in cur.fetchall()]
        
        cur.close()
        conn.close()
        return migrations
    
    def generate_migration(self, name: str):
        """Generate a new migration file"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        version = f"{timestamp}_{name}"
        
        migration_file = self.migrations_dir / f"{version}.sql"
        
        template = f"""-- Migration: {name}
-- Version: {version}
-- Created at: {datetime.now().isoformat()}

-- UP Migration
BEGIN;

-- Add your SQL here


COMMIT;

-- DOWN Migration (rollback)
BEGIN;

-- Add rollback SQL here


COMMIT;
"""
        with open(migration_file, 'w') as f:
            f.write(template)
        
        logger.info(f"Created migration: {migration_file}")
        return migration_file
    
    def apply_migrations(self):
        """Apply all pending migrations"""
        self.create_migration_table()
        applied = self.get_applied_migrations()
        
        # Find all migration files
        migration_files = sorted(self.migrations_dir.glob("*.sql"))
        
        for migration_file in migration_files:
            version = migration_file.stem
            
            if version in applied:
                continue
            
            logger.info(f"Applying migration: {version}")
            
            try:
                # Read and parse migration file
                with open(migration_file, 'r') as f:
                    content = f.read()
                
                # Split into UP and DOWN sections
                sections = content.split('-- DOWN Migration')
                up_sql = sections[0].replace('-- UP Migration', '').replace('BEGIN;', '').replace('COMMIT;', '').strip()
                
                # Apply UP migration
                conn = get_db_connection()
                cur = conn.cursor()
                
                # Execute UP migration
                for statement in up_sql.split(';'):
                    statement = statement.strip()
                    if statement:
                        cur.execute(statement)
                
                # Record migration
                cur.execute(
                    "INSERT INTO schema_migrations (version, name) VALUES (%s, %s)",
                    (version, migration_file.stem.split('_', 1)[1])
                )
                
                conn.commit()
                cur.close()
                conn.close()
                
                logger.info(f"Successfully applied migration: {version}")
                
            except Exception as e:
                logger.error(f"Failed to apply migration {version}: {e}")
                raise
    
    def rollback_migration(self, version: str):
        """Rollback a specific migration"""
        # Implementation for rollback
        pass

def main():
    migrator = DatabaseMigrator()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "create":
            if len(sys.argv) > 2:
                migrator.generate_migration(sys.argv[2])
            else:
                print("Usage: python migrate.py create <migration_name>")
        elif sys.argv[1] == "apply":
            migrator.apply_migrations()
        elif sys.argv[1] == "status":
            applied = migrator.get_applied_migrations()
            print(f"Applied migrations: {len(applied)}")
            for migration in applied:
                print(f"  - {migration}")
    else:
        migrator.apply_migrations()

if __name__ == "__main__":
    main()