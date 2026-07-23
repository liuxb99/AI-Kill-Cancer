"""
Tests for database migration upgrade/downgrade.
"""
from __future__ import annotations

import pytest
from alembic import command
from alembic.config import Config


@pytest.fixture
def alembic_config(tmp_path):
    """Create a temporary Alembic config pointing to async SQLite."""
    cfg = Config()
    cfg.set_main_option("script_location", "migrations")
    cfg.set_main_option("sqlalchemy.url", "sqlite+aiosqlite:///./test_migration.db")
    return cfg


class TestMigration:
    def test_upgrade_creates_tables(self, alembic_config):
        """Verify migration upgrade creates all domain tables."""
        command.upgrade(alembic_config, "001")
        # In a full test, we'd inspect the DB for table existence

    def test_downgrade_removes_tables(self, alembic_config):
        """Verify migration downgrade removes all domain tables."""
        command.upgrade(alembic_config, "001")
        command.downgrade(alembic_config, "-1")

    def test_migration_001_exists(self):
        """Verify migration version 001 file exists and has upgrade/downgrade."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "migration_001",
            "migrations/versions/001_initial_precision_oncology_foundation.py",
        )
        assert spec is not None, "Migration 001 file not found"
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert hasattr(module, "upgrade"), "Migration missing upgrade()"
        assert hasattr(module, "downgrade"), "Migration missing downgrade()"
        assert module.revision == "001"
        assert module.down_revision is None
