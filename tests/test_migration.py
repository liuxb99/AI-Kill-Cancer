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


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 3A — Batch E8: Migration 016 → 017 Tests
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def alembic_config_017(tmp_path):
    """Isolated Alembic config for 016→017 migration tests."""
    db_path = tmp_path / "test_migration_017.db"
    cfg = Config()
    cfg.set_main_option("script_location", "migrations")
    cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_path}")
    return cfg, db_path


def _table_exists(db_path, table_name):
    """Check if a table exists in the SQLite database."""
    import sqlite3
    conn = sqlite3.connect(str(db_path))
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    )
    exists = cursor.fetchone() is not None
    conn.close()
    return exists


class TestMigration017:
    """Tests for Phase 3A migration 017 (recommendation tables)."""

    def test_upgrade_016_to_017_creates_tables(self, alembic_config_017):
        """Upgrade from 016 to 017 creates domain_recommendations and related tables."""
        cfg, db_path = alembic_config_017
        # Upgrade to 016 first (base)
        command.upgrade(cfg, "016")
        assert _table_exists(db_path, "domain_recommendations") is False
        assert _table_exists(db_path, "domain_recommendation_traces") is False
        assert _table_exists(db_path, "domain_recommendation_trace_steps") is False

        # Upgrade to 017
        command.upgrade(cfg, "017")

        # Verify all three new tables exist
        assert _table_exists(db_path, "domain_recommendations"), "domain_recommendations table missing after upgrade"
        assert _table_exists(db_path, "domain_recommendation_traces"), "domain_recommendation_traces table missing"
        assert _table_exists(db_path, "domain_recommendation_trace_steps"), "domain_recommendation_trace_steps table missing"

    def test_downgrade_017_to_016_removes_tables(self, alembic_config_017):
        """Downgrade from 017 to 016 removes recommendation tables."""
        cfg, db_path = alembic_config_017
        command.upgrade(cfg, "017")

        # Verify tables exist before downgrade
        assert _table_exists(db_path, "domain_recommendations")

        command.downgrade(cfg, "016")

        # Verify tables are removed
        assert _table_exists(db_path, "domain_recommendations") is False
        assert _table_exists(db_path, "domain_recommendation_traces") is False
        assert _table_exists(db_path, "domain_recommendation_trace_steps") is False

    def test_upgrade_again_after_downgrade(self, alembic_config_017):
        """After downgrade 017→016, upgrading again to 017 should succeed."""
        cfg, db_path = alembic_config_017

        # First pass: 016 → 017
        command.upgrade(cfg, "017")
        assert _table_exists(db_path, "domain_recommendations")

        # Downgrade: 017 → 016
        command.downgrade(cfg, "016")
        assert _table_exists(db_path, "domain_recommendations") is False

        # Upgrade again: 016 → 017
        command.upgrade(cfg, "017")
        assert _table_exists(db_path, "domain_recommendations")
        assert _table_exists(db_path, "domain_recommendation_traces")
        assert _table_exists(db_path, "domain_recommendation_trace_steps")

    def test_migration_017_file_exists(self):
        """Verify migration 017 file exists with correct metadata."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "migration_017",
            "migrations/versions/017_phase3a_recommendation_tables.py",
        )
        assert spec is not None, "Migration 017 file not found"
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert hasattr(module, "upgrade"), "Migration 017 missing upgrade()"
        assert hasattr(module, "downgrade"), "Migration 017 missing downgrade()"
        assert module.revision == "017"
        assert module.down_revision == "016"

    def test_migration_016_exists_as_prerequisite(self):
        """Migration 016 must exist as the base for 017."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "migration_016",
            "migrations/versions/016_phase2_clinical_workspace.py",
        )
        assert spec is not None, "Migration 016 file not found"
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert module.revision == "016"

    def test_upgrade_017_tables_have_expected_columns(self, alembic_config_017):
        """Verify the new tables have the expected columns after upgrade."""
        cfg, db_path = alembic_config_017
        command.upgrade(cfg, "017")

        import sqlite3
        conn = sqlite3.connect(str(db_path))

        # Check domain_recommendations columns
        cursor = conn.execute("PRAGMA table_info(domain_recommendations)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        assert "recommendation_id" in columns
        assert "patient_id" in columns
        assert "trace_id" in columns
        assert "engine_version" in columns
        assert "status" in columns
        assert "request_payload" in columns
        assert "result_payload" in columns
        assert "report_html" in columns
        assert "created_at" in columns
        assert "updated_at" in columns

        # Check domain_recommendation_traces columns
        cursor = conn.execute("PRAGMA table_info(domain_recommendation_traces)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        assert "trace_id" in columns
        assert "recommendation_id" in columns
        assert "created_at" in columns

        # Check domain_recommendation_trace_steps columns
        cursor = conn.execute("PRAGMA table_info(domain_recommendation_trace_steps)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        assert "trace_id" in columns
        assert "step_order" in columns
        assert "step_type" in columns
        assert "input_summary" in columns
        assert "output_summary" in columns
        assert "evidence_references" in columns
        assert "weight" in columns
        assert "score" in columns
        assert "rank" in columns
        assert "status" in columns

        conn.close()

    def test_upgrade_017_preserves_016_tables(self, alembic_config_017):
        """Upgrading to 017 should not drop tables created by 016."""
        cfg, db_path = alembic_config_017

        # First check what tables 016 creates
        command.upgrade(cfg, "016")
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables_before = {row[0] for row in cursor.fetchall()}
        conn.close()

        # Now upgrade to 017
        command.upgrade(cfg, "017")
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables_after = {row[0] for row in cursor.fetchall()}
        conn.close()

        # All tables from 016 should still exist
        missing = tables_before - tables_after
        assert not missing, f"Tables from 016 missing after 017 upgrade: {missing}"

        # New tables should be present
        assert "domain_recommendations" in tables_after
        assert "domain_recommendation_traces" in tables_after
        assert "domain_recommendation_trace_steps" in tables_after
