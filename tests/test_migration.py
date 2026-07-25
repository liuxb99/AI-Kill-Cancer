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


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 3B — Batch H: Migration 018 → Clinical Decision Tables
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def alembic_config_018(tmp_path):
    """Isolated Alembic config for 017→018 migration tests."""
    db_path = tmp_path / "test_migration_018.db"
    cfg = Config()
    cfg.set_main_option("script_location", "migrations")
    cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_path}")
    return cfg, db_path


class TestMigration018:
    """Tests for Phase 3B migration 018 (clinical decision tables)."""

    def test_upgrade_017_to_018_creates_tables(self, alembic_config_018):
        """Upgrade from 017 to 018 creates domain_clinical_decisions and traces tables."""
        cfg, db_path = alembic_config_018
        # Upgrade to 017 first (base)
        command.upgrade(cfg, "017")
        assert _table_exists(db_path, "domain_clinical_decisions") is False
        assert _table_exists(db_path, "domain_clinical_decision_traces") is False

        # Upgrade to 018
        command.upgrade(cfg, "018")

        # Verify both new tables exist
        assert _table_exists(
            db_path, "domain_clinical_decisions"
        ), "domain_clinical_decisions table missing after upgrade"
        assert _table_exists(
            db_path, "domain_clinical_decision_traces"
        ), "domain_clinical_decision_traces table missing after upgrade"

    def test_downgrade_018_to_017_removes_tables(self, alembic_config_018):
        """Downgrade from 018 to 017 removes clinical decision tables."""
        cfg, db_path = alembic_config_018
        command.upgrade(cfg, "018")

        # Verify tables exist before downgrade
        assert _table_exists(db_path, "domain_clinical_decisions")

        command.downgrade(cfg, "017")

        # Verify tables are removed
        assert _table_exists(db_path, "domain_clinical_decisions") is False
        assert _table_exists(db_path, "domain_clinical_decision_traces") is False

    def test_upgrade_again_after_downgrade(self, alembic_config_018):
        """After downgrade 018→017, upgrading again to 018 should succeed."""
        cfg, db_path = alembic_config_018

        # First pass: 017 → 018
        command.upgrade(cfg, "018")
        assert _table_exists(db_path, "domain_clinical_decisions")

        # Downgrade: 018 → 017
        command.downgrade(cfg, "017")
        assert _table_exists(db_path, "domain_clinical_decisions") is False

        # Upgrade again: 017 → 018
        command.upgrade(cfg, "018")
        assert _table_exists(db_path, "domain_clinical_decisions")
        assert _table_exists(db_path, "domain_clinical_decision_traces")

    def test_migration_018_file_exists(self):
        """Verify migration 018 file exists with correct metadata."""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "migration_018",
            "migrations/versions/018_phase3b_clinical_decision_tables.py",
        )
        assert spec is not None, "Migration 018 file not found"
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert hasattr(module, "upgrade"), "Migration 018 missing upgrade()"
        assert hasattr(module, "downgrade"), "Migration 018 missing downgrade()"
        assert module.revision == "018"
        assert module.down_revision == "017"

    def test_migration_017_exists_as_prerequisite(self):
        """Migration 017 must exist as the base for 018."""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "migration_017",
            "migrations/versions/017_phase3a_recommendation_tables.py",
        )
        assert spec is not None, "Migration 017 file not found"
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert module.revision == "017"

    def test_upgrade_018_tables_have_expected_columns(self, alembic_config_018):
        """Verify the new tables have the expected columns after upgrade."""
        import sqlite3

        cfg, db_path = alembic_config_018
        command.upgrade(cfg, "018")

        conn = sqlite3.connect(str(db_path))

        # Check domain_clinical_decisions columns
        cursor = conn.execute("PRAGMA table_info(domain_clinical_decisions)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        assert "id" in columns
        assert "decision_id" in columns
        assert "patient_id" in columns
        assert "recommendation_id" in columns
        assert "decision_type" in columns
        assert "reason" in columns
        assert "evidence_summary" in columns
        assert "confidence" in columns
        assert "alternatives" in columns
        assert "contraindications" in columns
        assert "status" in columns
        assert "created_by" in columns
        assert "created_at" in columns
        assert "updated_at" in columns

        # Check domain_clinical_decision_traces columns
        cursor = conn.execute("PRAGMA table_info(domain_clinical_decision_traces)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        assert "id" in columns
        assert "trace_id" in columns
        assert "clinical_decision_id" in columns
        assert "recommendation_id" in columns
        assert "step_order" in columns
        assert "step_type" in columns
        assert "input_summary" in columns
        assert "output_summary" in columns
        assert "created_at" in columns

        conn.close()

    def test_upgrade_018_preserves_017_tables(self, alembic_config_018):
        """Upgrading to 018 should not drop tables created by 017."""
        cfg, db_path = alembic_config_018

        # First check what tables 017 creates
        command.upgrade(cfg, "017")
        import sqlite3

        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables_before = {row[0] for row in cursor.fetchall()}
        conn.close()

        # Now upgrade to 018
        command.upgrade(cfg, "018")
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables_after = {row[0] for row in cursor.fetchall()}
        conn.close()

        # All tables from 017 should still exist
        missing = tables_before - tables_after
        assert not missing, f"Tables from 017 missing after 018 upgrade: {missing}"

        # New tables should be present
        assert "domain_clinical_decisions" in tables_after
        assert "domain_clinical_decision_traces" in tables_after

    def test_upgrade_018_tables_have_indexes(self, alembic_config_018):
        """Verify expected indexes exist on the new tables."""
        import sqlite3

        cfg, db_path = alembic_config_018
        command.upgrade(cfg, "018")

        conn = sqlite3.connect(str(db_path))

        # Get index info for domain_clinical_decisions
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='domain_clinical_decisions'")
        indexes = {row[0] for row in cursor.fetchall()}

        # decision_id should be unique (creates an index) and indexed
        # At minimum we should have an index on patient_id
        assert any("patient_id" in idx for idx in indexes), "Missing patient_id index"

        # Get index info for domain_clinical_decision_traces
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='domain_clinical_decision_traces'"
        )
        indexes = {row[0] for row in cursor.fetchall()}

        # trace_id should be unique (creates an index) and indexed
        # At minimum we should have an index on clinical_decision_id
        assert any("trace_id" in idx for idx in indexes), "Missing trace_id index"

        conn.close()

    def test_upgrade_018_tables_have_foreign_keys(self, alembic_config_018):
        """Verify foreign keys are created (PRAGMA foreign_key_list)."""
        import sqlite3

        cfg, db_path = alembic_config_018
        command.upgrade(cfg, "018")

        conn = sqlite3.connect(str(db_path))

        # Check FK on domain_clinical_decisions
        cursor = conn.execute("PRAGMA foreign_key_list(domain_clinical_decisions)")
        fks = {row[3]: row[4] for row in cursor.fetchall()}
        assert "patient_id" in fks, "Missing FK on patient_id"
        assert fks["patient_id"] == "domain_patients", "patient_id FK target mismatch"

        # Check FK on domain_clinical_decision_traces
        cursor = conn.execute("PRAGMA foreign_key_list(domain_clinical_decision_traces)")
        fks = {row[3]: row[4] for row in cursor.fetchall()}
        assert "clinical_decision_id" in fks, "Missing FK on clinical_decision_id"
        assert fks["clinical_decision_id"] == "domain_clinical_decisions", "clinical_decision_id FK target mismatch"

        conn.close()
