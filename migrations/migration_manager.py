"""
Migration Manager for Bible API
Handles database schema migrations
"""
import os
import re
from datetime import datetime
from typing import List, Dict, Any
import mysql.connector
from mysql.connector import Error
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app'))
from app.database import create_connection


class MigrationManager:
    def __init__(self):
        self.migrations_dir = os.path.dirname(os.path.abspath(__file__))
        self.connection = None
        
    def get_connection(self):
        """Get database connection"""
        if not self.connection:
            self.connection = create_connection()
        return self.connection
    
    def ensure_migrations_table(self):
        """Create migrations table if it doesn't exist"""
        connection = self.get_connection()
        cursor = connection.cursor()
        
        create_table_query = """
        CREATE TABLE IF NOT EXISTS migrations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            migration_name VARCHAR(255) NOT NULL UNIQUE,
            executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_migration_name (migration_name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
        
        try:
            cursor.execute(create_table_query)
            connection.commit()
            print("Migrations table ensured")
        except Error as e:
            print(f"Error creating migrations table: {e}")
        finally:
            cursor.close()
    
    def get_executed_migrations(self) -> List[str]:
        """Get list of already executed migrations"""
        connection = self.get_connection()
        cursor = connection.cursor()
        
        try:
            cursor.execute("SELECT migration_name FROM migrations ORDER BY migration_name")
            return [row[0] for row in cursor.fetchall()]
        except Error as e:
            print(f"Error getting executed migrations: {e}")
            return []
        finally:
            cursor.close()
    
    def get_migration_files(self) -> List[str]:
        """Get list of migration files"""
        migration_files = []
        for filename in os.listdir(self.migrations_dir):
            if filename.endswith('.sql') and re.match(r'^\d{4}_\d{2}_\d{2}_\d{6}_.*\.sql$', filename):
                migration_files.append(filename)
        return sorted(migration_files)
    
    def execute_migration(self, migration_file: str) -> bool:
        """Execute a single migration file"""
        migration_path = os.path.join(self.migrations_dir, migration_file)
        
        if not os.path.exists(migration_path):
            print(f"Migration file not found: {migration_file}")
            return False
        
        connection = self.get_connection()
        cursor = connection.cursor()
        
        try:
            # Read migration file
            with open(migration_path, 'r', encoding='utf-8') as f:
                migration_sql = f.read()
            
            # Split by semicolon and execute each statement
            statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]
            
            for statement in statements:
                if statement:
                    cursor.execute(statement)
            
            # Record migration as executed
            cursor.execute(
                "INSERT INTO migrations (migration_name) VALUES (%s)",
                (migration_file,)
            )
            
            connection.commit()
            print(f"Migration executed successfully: {migration_file}")
            return True
            
        except Error as e:
            connection.rollback()
            print(f"Error executing migration {migration_file}: {e}")
            return False
        finally:
            cursor.close()
    
    def run_migrations(self):
        """Run all pending migrations"""
        self.ensure_migrations_table()
        
        executed_migrations = set(self.get_executed_migrations())
        migration_files = self.get_migration_files()
        
        pending_migrations = [f for f in migration_files if f not in executed_migrations]
        
        if not pending_migrations:
            print("No pending migrations")
            return True
        
        print(f"Found {len(pending_migrations)} pending migrations")
        
        for migration_file in pending_migrations:
            print(f"Executing migration: {migration_file}")
            if not self.execute_migration(migration_file):
                print(f"Migration failed: {migration_file}")
                return False
        
        print("Migrations completed")
        return True
    
    def create_migration(self, name: str) -> str:
        """Create a new migration file"""
        timestamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")
        # Clean name for filename
        clean_name = re.sub(r'[^a-zA-Z0-9_]', '_', name.lower())
        filename = f"{timestamp}_{clean_name}.sql"
        filepath = os.path.join(self.migrations_dir, filename)
        
        template = f"""-- Migration: {name}
-- Created: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

-- Add your SQL statements here
-- Each statement should end with a semicolon

-- Example:
-- CREATE TABLE example_table (
--     id INT AUTO_INCREMENT PRIMARY KEY,
--     name VARCHAR(255) NOT NULL
-- ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(template)
        
        print(f"Created migration file: {filename}")
        return filename
    
    def rollback_migration(self, migration_file: str):
        """Rollback a specific migration (removes from migrations table)"""
        connection = self.get_connection()
        cursor = connection.cursor()
        
        try:
            cursor.execute(
                "DELETE FROM migrations WHERE migration_name = %s",
                (migration_file,)
            )
            connection.commit()
            print(f"Migration rollback recorded: {migration_file}")
            print("Note: This only removes the migration record. You need to manually revert schema changes.")
        except Error as e:
            print(f"Error rolling back migration: {e}")
        finally:
            cursor.close()
    
    def mark_as_executed(self, migration_file: str):
        """Mark a migration as executed without running it (for existing databases)"""
        migration_path = os.path.join(self.migrations_dir, migration_file)
        
        if not os.path.exists(migration_path):
            print(f"Migration file not found: {migration_file}")
            return False
        
        connection = self.get_connection()
        cursor = connection.cursor()
        
        try:
            # Check if already executed
            cursor.execute(
                "SELECT COUNT(*) FROM migrations WHERE migration_name = %s",
                (migration_file,)
            )
            if cursor.fetchone()[0] > 0:
                print(f"Migration already marked as executed: {migration_file}")
                return True
            
            # Mark as executed
            cursor.execute(
                "INSERT INTO migrations (migration_name) VALUES (%s)",
                (migration_file,)
            )
            connection.commit()
            print(f"Migration marked as executed: {migration_file}")
            return True
            
        except Error as e:
            print(f"Error marking migration as executed: {e}")
            return False
        finally:
            cursor.close()
    
    def status(self):
        """Show migration status"""
        self.ensure_migrations_table()
        
        executed_migrations = set(self.get_executed_migrations())
        migration_files = self.get_migration_files()
        
        print("Migration Status:")
        print("=" * 50)
        
        if not migration_files:
            print("No migration files found")
            return
        
        for migration_file in migration_files:
            status = "EXECUTED" if migration_file in executed_migrations else "PENDING"
            print(f"{migration_file:<40} {status}")
        
        pending_count = len([f for f in migration_files if f not in executed_migrations])
        print(f"\nTotal migrations: {len(migration_files)}")
        print(f"Executed: {len(executed_migrations)}")
        print(f"Pending: {pending_count}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Database Migration Manager')
    parser.add_argument('command', choices=['migrate', 'create', 'status', 'rollback', 'mark-executed'], 
                       help='Migration command')
    parser.add_argument('--name', help='Migration name (for create command)')
    parser.add_argument('--file', help='Migration file (for rollback command)')
    
    args = parser.parse_args()
    
    manager = MigrationManager()
    
    if args.command == 'migrate':
        manager.run_migrations()
    elif args.command == 'create':
        if not args.name:
            print("Error: --name is required for create command")
            exit(1)
        manager.create_migration(args.name)
    elif args.command == 'status':
        manager.status()
    elif args.command == 'rollback':
        if not args.file:
            print("Error: --file is required for rollback command")
            exit(1)
        manager.rollback_migration(args.file)
    elif args.command == 'mark-executed':
        if not args.file:
            print("Error: --file is required for mark-executed command")
            exit(1)
        manager.mark_as_executed(args.file)
