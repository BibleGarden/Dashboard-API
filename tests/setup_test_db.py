#!/usr/bin/env python3
"""
Script for initializing the cep_test test database.

Creates the cep_test database, applies all migrations, loads seed data.
Run inside the container:
    python tests/setup_test_db.py
"""
import os
import sys
import re

# Project paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'app'))

# Set DB_NAME before importing app modules (so that config.py reads the correct value)
os.environ["DB_NAME"] = "cep_test"

import mysql.connector
from mysql.connector import Error
from app.config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD

TEST_DB_NAME = "cep_test"


def create_database():
    """Creates (recreates) the test database"""
    print(f"Creating database {TEST_DB_NAME}...")
    conn = mysql.connector.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD
    )
    cursor = conn.cursor()
    cursor.execute(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}")
    cursor.execute(
        f"CREATE DATABASE {TEST_DB_NAME} "
        f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    cursor.close()
    conn.close()
    print(f"Database {TEST_DB_NAME} created")


def run_migrations():
    """Applies all migrations to the test database"""
    print("Running migrations...")

    conn = mysql.connector.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD,
        database=TEST_DB_NAME
    )
    cursor = conn.cursor()

    # Disable FK checks — the initial migration creates tables out of FK dependency order
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")

    # Migration tracking table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS migrations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            migration_name VARCHAR(255) NOT NULL UNIQUE,
            executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_migration_name (migration_name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    conn.commit()

    # Collect migration files
    migrations_dir = os.path.join(PROJECT_ROOT, 'migrations')
    migration_files = sorted([
        f for f in os.listdir(migrations_dir)
        if f.endswith('.sql') and re.match(r'^\d{4}_\d{2}_\d{2}_\d{6}_.*\.sql$', f)
    ])

    applied = 0
    for migration_file in migration_files:
        filepath = os.path.join(migrations_dir, migration_file)
        with open(filepath, 'r', encoding='utf-8') as f:
            sql = f.read()

        # Remove hardcoded DB name from old migrations
        sql = sql.replace('`bible_pause`.', '')
        sql = sql.replace('`cep`.', '')

        # Production uses utf8mb3, where varchar(10000) fits within the row size limit.
        # With utf8mb4, two varchar(10000) exceed 65535 bytes, so replace with text.
        sql = sql.replace('varchar(10000)', 'text')

        # Split into individual SQL statements
        statements = [s.strip() for s in sql.split(';') if s.strip()]
        for stmt in statements:
            # Skip lines consisting only of comments
            non_comment = '\n'.join(
                line for line in stmt.split('\n')
                if line.strip() and not line.strip().startswith('--')
            )
            if not non_comment.strip():
                continue
            try:
                cursor.execute(stmt)
            except Error as e:
                # Non-critical errors: duplicate index, column already exists, etc.
                print(f"  Warning in {migration_file}: {e}")

        # Record the migration as executed
        cursor.execute(
            "INSERT INTO migrations (migration_name) VALUES (%s)",
            (migration_file,)
        )
        conn.commit()
        applied += 1

    # Re-enable FK checks
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    conn.commit()

    cursor.close()
    conn.close()
    print(f"Applied {applied} migrations")


def load_seed_data():
    """Loads seed data from the SQL file"""
    print("Loading seed data...")

    seed_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'seed_test_data.sql')
    if not os.path.exists(seed_file):
        print(f"Seed file not found: {seed_file}")
        sys.exit(1)

    with open(seed_file, 'r', encoding='utf-8') as f:
        sql = f.read()

    conn = mysql.connector.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD,
        database=TEST_DB_NAME
    )
    cursor = conn.cursor()

    statements = [s.strip() for s in sql.split(';') if s.strip()]
    for stmt in statements:
        non_comment = '\n'.join(
            line for line in stmt.split('\n')
            if line.strip() and not line.strip().startswith('--')
        )
        if not non_comment.strip():
            continue
        try:
            cursor.execute(stmt)
        except Error as e:
            print(f"  Error loading seed data: {e}")
            print(f"  Statement: {stmt[:200]}...")
            sys.exit(1)

    conn.commit()
    cursor.close()
    conn.close()
    print("Seed data loaded")


def main():
    create_database()
    run_migrations()
    load_seed_data()
    print(f"\nTest database {TEST_DB_NAME} is ready!")
    print("Run tests: pytest tests/ -v")


if __name__ == "__main__":
    main()
