# Database Migrations

Migration system for Bible API that allows managing database schema changes.

## Usage

### Running Migrations
```bash
python migrate.py migrate
```

### Creating a New Migration
```bash
python migrate.py create "migration_name"
```

### Viewing Migration Status
```bash
python migrate.py status
```

### Rolling Back a Migration (table record only)
```bash
python migrate.py rollback "migration_file.sql"
```

### Marking a Migration as Executed (for existing databases)
```bash
python migrate.py mark-executed "migration_file.sql"
```

## Structure

- `migration_manager.py` - main class for managing migrations
- `migrations/` - folder with migration files
- `migrate.py` - CLI tool for managing migrations

## Migration File Format

Migration files follow the format: `YYYY_MM_DD_HHMMSS_migration_name.sql`

Example:
```sql
-- Migration: create_users_table
-- Created: 2025-07-23 23:12:32

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_users_email ON users(email);
```

## Migrations Table

The system automatically creates a `migrations` table for tracking executed migrations:

```sql
CREATE TABLE migrations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    migration_name VARCHAR(255) NOT NULL UNIQUE,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_migration_name (migration_name)
);
```

## Important Notes

1. Each SQL statement must end with a semicolon
2. Migrations are executed in alphabetical order by file name
3. Rolling back a migration only removes the record from the migrations table - the schema must be rolled back manually
4. It is recommended to back up the database before running migrations

## For Existing Databases

If you are introducing the migration system into an existing project with an already-created database schema:

1. Create the first migration with a dump of the current structure
2. Mark it as executed: `python migrate.py mark-executed "migration_file.sql"`
3. Now all new migrations will be executed normally
