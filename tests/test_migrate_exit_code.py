"""The migration CLI must report a failed migration through its exit code."""

import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("succeeds, expected_code", [(True, 0), (False, 1)])
def test_migrate_exit_code(succeeds, expected_code):
    script = f"""
import sys
from unittest.mock import patch

import migrate
from migrations.migration_manager import MigrationManager

with (
    patch.object(MigrationManager, 'ensure_migrations_table'),
    patch.object(MigrationManager, 'get_executed_migrations', return_value=[]),
    patch.object(MigrationManager, 'get_migration_files', return_value=['example.sql']),
    patch.object(MigrationManager, 'execute_migration', return_value={succeeds}),
):
    sys.argv = ['migrate.py', 'migrate']
    migrate.main()
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == expected_code, result.stdout + result.stderr
    if succeeds:
        assert "Migrations completed" in result.stdout
    else:
        assert "Migration failed: example.sql" in result.stdout
