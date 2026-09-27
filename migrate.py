#!/usr/bin/env python3
"""
Database Migration CLI Tool for Bible API
Usage:
    python migrate.py migrate        # Run all pending migrations
    python migrate.py create <name>  # Create new migration
    python migrate.py status         # Show migration status
    python migrate.py rollback <file># Rollback specific migration
    python migrate.py mark-executed <file> # Mark migration as executed (for existing DB)
"""
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from migrations.migration_manager import MigrationManager


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1]
    manager = MigrationManager()
    
    if command == 'migrate':
        if not manager.run_migrations():
            sys.exit(1)
    
    elif command == 'create':
        if len(sys.argv) < 3:
            print("Error: Migration name is required")
            print("Usage: python migrate.py create <migration_name>")
            sys.exit(1)
        name = sys.argv[2]
        manager.create_migration(name)
    
    elif command == 'status':
        manager.status()
    
    elif command == 'rollback':
        if len(sys.argv) < 3:
            print("Error: Migration file is required")
            print("Usage: python migrate.py rollback <migration_file>")
            sys.exit(1)
        filename = sys.argv[2]
        manager.rollback_migration(filename)
    
    elif command == 'mark-executed':
        if len(sys.argv) < 3:
            print("Error: Migration file is required")
            print("Usage: python migrate.py mark-executed <migration_file>")
            sys.exit(1)
        filename = sys.argv[2]
        manager.mark_as_executed(filename)
    
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
