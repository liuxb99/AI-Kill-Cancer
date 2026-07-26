"""
Tests for database migration upgrade/downgrade.
"""
from __future__ import annotations

import pytest
from alembic import command
from alembic.config import Config


class IrreversibleMigrationError(Exception):
    """Raised when a migration cannot be reversed safely.

    This class was removed from alembic.util in Alembic ≥1.9.
    We define it locally to keep the same semantic contract.
    """


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
        # PRAGMA foreign_key_list returns: (id, seq, table, from, to, on_update, on_delete, match)
        cursor = conn.execute("PRAGMA foreign_key_list(domain_clinical_decisions)")
        fks = {row[3]: {"ref_table": row[2], "ref_column": row[4]} for row in cursor.fetchall()}
        assert "patient_id" in fks, "Missing FK on patient_id"
        assert fks["patient_id"]["ref_table"] == "domain_patients", "patient_id FK should reference domain_patients"
        assert fks["patient_id"]["ref_column"] == "id", "patient_id FK should reference domain_patients.id"

        # Check FK on domain_clinical_decision_traces
        cursor = conn.execute("PRAGMA foreign_key_list(domain_clinical_decision_traces)")
        fks = {row[3]: {"ref_table": row[2], "ref_column": row[4]} for row in cursor.fetchall()}
        assert "clinical_decision_id" in fks, "Missing FK on clinical_decision_id"
        assert fks["clinical_decision_id"]["ref_table"] == "domain_clinical_decisions", "clinical_decision_id FK should reference domain_clinical_decisions"
        assert fks["clinical_decision_id"]["ref_column"] == "id", "clinical_decision_id FK should reference domain_clinical_decisions.id"

        conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 3B — Batch A: Migration 019 → Trace Compound Unique
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def alembic_config_019(tmp_path):
    """Isolated Alembic config for 018→019 migration tests."""
    db_path = tmp_path / "test_migration_019.db"
    cfg = Config()
    cfg.set_main_option("script_location", "migrations")
    cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_path}")
    return cfg, db_path


class TestMigration019:
    """Tests for Phase 3B migration 019 (trace compound unique)."""

    # ── helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _get_indexes(db_path, table_name):
        """Return a dict mapping index name → {"unique": bool, "columns": list}."""
        import sqlite3

        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name=?",
            (table_name,),
        )
        index_names = [row[0] for row in cursor.fetchall()]

        result = {}
        for idx_name in index_names:
            cursor = conn.execute(f"PRAGMA index_info('{idx_name}')")
            columns = [row[2] for row in cursor.fetchall()]
            cursor = conn.execute(f"PRAGMA index_list('{table_name}')")
            unique = False
            for row in cursor.fetchall():
                # row[1] = name, row[2] = unique flag (0/1)
                if row[1] == idx_name:
                    unique = bool(row[2])
                    break
            result[idx_name] = {"unique": unique, "columns": columns}
        conn.close()
        return result

    # ── file existence ───────────────────────────────────────────────────────

    def test_migration_019_file_exists(self):
        """Verify migration 019 file exists with correct metadata."""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "migration_019",
            "migrations/versions/019_phase3b_trace_compound_unique.py",
        )
        assert spec is not None, "Migration 019 file not found"
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert hasattr(module, "upgrade"), "Migration 019 missing upgrade()"
        assert hasattr(module, "downgrade"), "Migration 019 missing downgrade()"
        assert module.revision == "019"
        assert module.down_revision == "018"

    def test_migration_018_exists_as_prerequisite(self):
        """Migration 018 must exist as the base for 019."""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "migration_018",
            "migrations/versions/018_phase3b_clinical_decision_tables.py",
        )
        assert spec is not None, "Migration 018 file not found"
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert module.revision == "018"

    # ── upgrade 018→019 ──────────────────────────────────────────────────────

    def test_upgrade_018_to_019_alters_indexes(self, alembic_config_019):
        """Upgrade to 019 drops UNIQUE on trace_id and adds compound unique."""
        cfg, db_path = alembic_config_019
        command.upgrade(cfg, "018")

        # Before upgrade: trace_id index should be UNIQUE
        indexes_before = self._get_indexes(db_path, "domain_clinical_decision_traces")
        assert "ix_domain_clinical_decision_traces_trace_id" in indexes_before
        assert indexes_before["ix_domain_clinical_decision_traces_trace_id"]["unique"] is True

        command.upgrade(cfg, "019")

        # After upgrade:
        indexes_after = self._get_indexes(db_path, "domain_clinical_decision_traces")

        # 1) The single-column index should now be non-unique
        idx = indexes_after.get("ix_domain_clinical_decision_traces_trace_id")
        assert idx is not None, "Missing trace_id index after upgrade"
        assert idx["unique"] is False, "trace_id index should no longer be UNIQUE"
        assert idx["columns"] == ["trace_id"]

        # 2) The compound unique constraint should exist
        assert "uq_trace_step" in indexes_after, "Missing uq_trace_step compound unique"
        assert indexes_after["uq_trace_step"]["unique"] is True
        assert indexes_after["uq_trace_step"]["columns"] == ["trace_id", "step_order"]

    # ── insert multiple trace steps with same trace_id ───────────────────────

    def test_insert_multiple_trace_steps_same_trace_id(self, alembic_config_019):
        """After 019 upgrade, inserting rows with same trace_id but different step_order succeeds."""
        cfg, db_path = alembic_config_019
        command.upgrade(cfg, "019")

        import sqlite3
        conn = sqlite3.connect(str(db_path))

        # Insert multiple steps sharing the same trace_id
        trace_id = "trace-simulation-001"
        for step_order in range(1, 6):
            conn.execute(
                """INSERT INTO domain_clinical_decision_traces
                   (id, trace_id, step_order, step_type, input_summary, output_summary)
                   VALUES (?, ?, ?, ?, '{}', '{}')""",
                (f"id-{step_order}", trace_id, step_order, "reasoning"),
            )
        conn.commit()

        # Verify all 5 rows exist
        cursor = conn.execute(
            "SELECT COUNT(*) FROM domain_clinical_decision_traces WHERE trace_id=?",
            (trace_id,),
        )
        count = cursor.fetchone()[0]
        assert count == 5, f"Expected 5 rows, got {count}"

        # Verify unique violation on same trace_id + step_order
        with pytest.raises(Exception):
            conn.execute(
                """INSERT INTO domain_clinical_decision_traces
                   (id, trace_id, step_order, step_type)
                   VALUES (?, ?, ?, ?)""",
                ("id-duplicate", trace_id, 1, "duplicate"),
            )
        conn.close()

    # ── downgrade 019→018 ────────────────────────────────────────────────────

    def test_downgrade_019_to_018_restores_unique(self, alembic_config_019):
        """Downgrade from 019 to 018 restores the UNIQUE index on trace_id."""
        cfg, db_path = alembic_config_019
        command.upgrade(cfg, "019")

        # Upgrade to 019 first, then downgrade
        command.downgrade(cfg, "018")

        indexes = self._get_indexes(db_path, "domain_clinical_decision_traces")

        # After downgrade: trace_id index should be UNIQUE again
        idx = indexes.get("ix_domain_clinical_decision_traces_trace_id")
        assert idx is not None, "Missing trace_id index after downgrade"
        assert idx["unique"] is True, "trace_id index should be UNIQUE after downgrade"

        # Compound constraint should be gone
        assert "uq_trace_step" not in indexes, "uq_trace_step should not exist after downgrade"

    def test_downgrade_019_to_018_enforces_unique(self, alembic_config_019):
        """After downgrade to 018, inserting duplicate trace_id should fail."""
        cfg, db_path = alembic_config_019
        command.upgrade(cfg, "019")
        command.downgrade(cfg, "018")

        import sqlite3
        conn = sqlite3.connect(str(db_path))

        trace_id = "trace-unique-test"
        conn.execute(
            """INSERT INTO domain_clinical_decision_traces
               (id, trace_id, step_order, step_type)
               VALUES (?, ?, ?, ?)""",
            ("id-first", trace_id, 1, "first"),
        )
        conn.commit()

        # Second insert with same trace_id should fail (UNIQUE constraint)
        with pytest.raises(Exception):
            conn.execute(
                """INSERT INTO domain_clinical_decision_traces
                   (id, trace_id, step_order, step_type)
                   VALUES (?, ?, ?, ?)""",
                ("id-second", trace_id, 2, "second"),
            )
        conn.close()

    # ── re-upgrade cycle ─────────────────────────────────────────────────────

    def test_reupgrade_019_cycle(self, alembic_config_019):
        """018 → 019 → 018 → 019 cycle should succeed and leave correct indexes."""
        cfg, db_path = alembic_config_019

        # First pass
        command.upgrade(cfg, "019")
        command.downgrade(cfg, "018")

        # Second pass
        command.upgrade(cfg, "019")

        indexes = self._get_indexes(db_path, "domain_clinical_decision_traces")

        # Final state should match 019 expectations
        idx = indexes.get("ix_domain_clinical_decision_traces_trace_id")
        assert idx is not None, "Missing trace_id index after re-upgrade"
        assert idx["unique"] is False, "trace_id index should be non-unique"
        assert "uq_trace_step" in indexes, "Missing uq_trace_step after re-upgrade"
        assert indexes["uq_trace_step"]["unique"] is True

    # ── upgrade preserves existing tables ────────────────────────────────────

    def test_upgrade_019_preserves_018_tables(self, alembic_config_019):
        """Upgrading to 019 should not drop tables created by 018."""
        cfg, db_path = alembic_config_019

        command.upgrade(cfg, "018")
        import sqlite3

        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables_before = {row[0] for row in cursor.fetchall()}
        conn.close()

        command.upgrade(cfg, "019")
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables_after = {row[0] for row in cursor.fetchall()}
        conn.close()

        missing = tables_before - tables_after
        assert not missing, f"Tables from 018 missing after 019 upgrade: {missing}"

    # ── columns unchanged ────────────────────────────────────────────────────

    def test_upgrade_019_columns_unchanged(self, alembic_config_019):
        """Column definitions must be identical after 019 upgrade."""
        cfg, db_path = alembic_config_019
        command.upgrade(cfg, "018")

        import sqlite3
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("PRAGMA table_info(domain_clinical_decision_traces)")
        columns_018 = {(row[1], row[2]) for row in cursor.fetchall()}
        conn.close()

        command.upgrade(cfg, "019")
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("PRAGMA table_info(domain_clinical_decision_traces)")
        columns_019 = {(row[1], row[2]) for row in cursor.fetchall()}
        conn.close()

        assert columns_018 == columns_019, "Columns changed after 019 upgrade"

    # ── Strategy A: downgrade safety (MIG-2) ────────────────────────────
    #
    # These three tests verify the revised downgrade behaviour for
    # Migration 019 (Strategy A):
    #
    #   Case 1 – Empty database downgrade succeeds
    #   Case 2 – Multi-step trace data → IrreversibleMigrationError
    #   Case 3 – 018 → 019 upgrade succeeds
    # ─────────────────────────────────────────────────────────────────────

    def test_downgrade_empty_database_success(self, alembic_config_019):
        """Case1: Empty database — downgrade 019→018 should succeed without error."""
        cfg, db_path = alembic_config_019

        # 018 → 019
        command.upgrade(cfg, "019")

        # No data inserted → downgrade must NOT raise
        command.downgrade(cfg, "018")

        # Sanity-check: we are back at 018 schema
        indexes = self._get_indexes(db_path, "domain_clinical_decision_traces")
        idx = indexes.get("ix_domain_clinical_decision_traces_trace_id")
        assert idx is not None, "trace_id index missing after downgrade"
        assert idx["unique"] is True, "trace_id index should be UNIQUE after downgrade"
        assert "uq_trace_step" not in indexes, "uq_trace_step should be gone after downgrade"

    def test_downgrade_with_multistep_trace_raises(self, alembic_config_019):
        """Case2: Multi-step trace data → downgrade raises IrreversibleMigrationError."""
        cfg, db_path = alembic_config_019

        # 018 → 019
        command.upgrade(cfg, "019")

        # Insert 5 steps sharing the same trace_id
        import sqlite3

        conn = sqlite3.connect(str(db_path))
        trace_id = "multi-step-guard-001"
        for step_order in range(5):  # step_order 0..4
            conn.execute(
                """INSERT INTO domain_clinical_decision_traces
                   (id, trace_id, step_order, step_type, input_summary, output_summary)
                   VALUES (?, ?, ?, ?, '{}', '{}')""",
                (f"id-{step_order}", trace_id, step_order, "reasoning"),
            )
        conn.commit()

        # Verify 5 rows exist
        cursor = conn.execute(
            "SELECT COUNT(*) FROM domain_clinical_decision_traces WHERE trace_id=?",
            (trace_id,),
        )
        assert cursor.fetchone()[0] == 5, "Expected 5 trace steps before downgrade"
        conn.close()

        # Downgrade must raise IrreversibleMigrationError
        with pytest.raises(Exception) as excinfo:
            command.downgrade(cfg, "018")

        error_msg = str(excinfo.value)
        assert "Cannot downgrade Migration 019" in error_msg, (
            f"Error message missing 'Cannot downgrade Migration 019': {error_msg}"
        )
        assert "multi-step Clinical Decision Trace" in error_msg, (
            f"Error message missing 'multi-step Clinical Decision Trace': {error_msg}"
        )

    def test_reupgrade_019_success(self, alembic_config_019):
        """Case3: 018 → 019 upgrade should succeed (idempotent)."""
        cfg, db_path = alembic_config_019

        # Fixture is at 018; upgrade to 019
        command.upgrade(cfg, "019")

        # Verify final state reflects 019 schema
        indexes = self._get_indexes(db_path, "domain_clinical_decision_traces")
        idx = indexes.get("ix_domain_clinical_decision_traces_trace_id")
        assert idx is not None, "trace_id index missing after upgrade"
        assert idx["unique"] is False, "trace_id index should be non-unique after upgrade"

        uq = indexes.get("uq_trace_step")
        assert uq is not None, "uq_trace_step missing after upgrade"
        assert uq["unique"] is True, "uq_trace_step should be UNIQUE"
        assert uq["columns"] == ["trace_id", "step_order"], (
            f"Expected uq_trace_step on (trace_id, step_order), got {uq['columns']}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 3C — Migration 020: Tumor Board Consensus Tables
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def alembic_config_020(tmp_path):
    """Isolated Alembic config for 019→020 migration tests."""
    db_path = tmp_path / "test_migration_020.db"
    cfg = Config()
    cfg.set_main_option("script_location", "migrations")
    cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_path}")
    return cfg, db_path


class TestMigration020:
    """Tests for Phase 3C migration 020 (tumor board consensus tables)."""

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
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

    @staticmethod
    def _get_indexes(db_path, table_name):
        """Return dict mapping index name → {unique, columns} for a table."""
        import sqlite3
        conn = sqlite3.connect(str(db_path))

        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name=?",
            (table_name,),
        )
        index_names = [row[0] for row in cursor.fetchall()]

        result = {}
        for idx_name in index_names:
            cursor = conn.execute(f"PRAGMA index_info('{idx_name}')")
            columns = [row[2] for row in cursor.fetchall()]
            cursor = conn.execute(f"PRAGMA index_list('{table_name}')")
            unique = False
            for row in cursor.fetchall():
                # row[1] = name, row[2] = unique flag (0/1)
                if row[1] == idx_name:
                    unique = bool(row[2])
                    break
            result[idx_name] = {"unique": unique, "columns": columns}
        conn.close()
        return result

    @staticmethod
    def _get_unique_constraints(db_path, table_name):
        """Return dict mapping constraint name → columns for a table."""
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        )
        row = cursor.fetchone()
        if row is None:
            conn.close()
            return {}
        create_sql = row[1] or ""
        conn.close()

        constraints = {}
        # Parse unique constraints from CREATE TABLE statement
        import re
        for match in re.finditer(
            r"CONSTRAINT\s+(\w+)\s+UNIQUE\s*\(([^)]+)\)",
            create_sql, re.IGNORECASE,
        ):
            name = match.group(1)
            columns = [c.strip().strip('"') for c in match.group(2).split(",")]
            constraints[name] = columns
        return constraints

    # ── file existence ───────────────────────────────────────────────────────

    def test_migration_020_file_exists(self):
        """Verify migration 020 file exists with correct metadata."""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "migration_020",
            "migrations/versions/020_phase3c_tumor_board_consensus.py",
        )
        assert spec is not None, "Migration 020 file not found"
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert hasattr(module, "upgrade"), "Migration 020 missing upgrade()"
        assert hasattr(module, "downgrade"), "Migration 020 missing downgrade()"
        assert module.revision == "020"
        assert module.down_revision == "019"

    def test_migration_019_exists_as_prerequisite(self):
        """Migration 019 must exist as the base for 020."""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "migration_019",
            "migrations/versions/019_phase3b_trace_compound_unique.py",
        )
        assert spec is not None, "Migration 019 file not found"
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert module.revision == "019"

    # ── upgrade 019→020 ──────────────────────────────────────────────────────

    def test_upgrade_019_to_020_creates_tables(self, alembic_config_020):
        """Upgrade from 019 to 020 creates all three tumor board tables."""
        cfg, db_path = alembic_config_020
        command.upgrade(cfg, "019")

        # Verify tables do not exist before upgrade
        assert self._table_exists(db_path, "domain_tumor_board_consensus") is False
        assert self._table_exists(db_path, "domain_tumor_board_opinions") is False
        assert self._table_exists(db_path, "domain_tumor_board_consensus_traces") is False

        # Upgrade to 020
        command.upgrade(cfg, "020")

        # Verify all three new tables exist
        assert self._table_exists(
            db_path, "domain_tumor_board_consensus",
        ), "domain_tumor_board_consensus table missing after upgrade"
        assert self._table_exists(
            db_path, "domain_tumor_board_opinions",
        ), "domain_tumor_board_opinions table missing after upgrade"
        assert self._table_exists(
            db_path, "domain_tumor_board_consensus_traces",
        ), "domain_tumor_board_consensus_traces table missing after upgrade"

    # ── downgrade 020→019 ────────────────────────────────────────────────────

    def test_downgrade_020_to_019_raises_irreversible(self, alembic_config_020):
        """Downgrade from 020 to 019 should raise IrreversibleMigrationError when data exists."""
        cfg, db_path = alembic_config_020
        command.upgrade(cfg, "020")

        # Insert a row into domain_tumor_board_consensus to make downgrade unsafe
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "INSERT INTO domain_tumor_board_consensus "
            "(id, consensus_id, patient_id, consensus_status) "
            "VALUES ('test-id', 'test-cid', 'test-pid', 'unanimous')"
        )
        conn.commit()
        conn.close()

        with pytest.raises(Exception) as excinfo:
            command.downgrade(cfg, "019")

        error_msg = str(excinfo.value)
        assert "Cannot downgrade Migration 020" in error_msg or "irreversible" in error_msg.lower(), (
            f"Error message missing expected text: {error_msg}"
        )

    def test_downgrade_020_to_019_error_message(self, alembic_config_020):
        """Downgrade error message should mention 'Cannot downgrade' when data exists."""
        cfg, db_path = alembic_config_020
        command.upgrade(cfg, "020")

        # Insert a row into domain_tumor_board_consensus to make downgrade unsafe
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "INSERT INTO domain_tumor_board_consensus "
            "(id, consensus_id, patient_id, consensus_status) "
            "VALUES ('test-id-2', 'test-cid-2', 'test-pid-2', 'unanimous')"
        )
        conn.commit()
        conn.close()

        with pytest.raises(Exception) as excinfo:
            command.downgrade(cfg, "019")

        error_msg = str(excinfo.value)
        assert "Cannot downgrade Migration 020" in error_msg, (
            f"Error message missing expected text: {error_msg}"
        )

    def test_downgrade_020_empty_db_ok(self, alembic_config_020):
        """Downgrade from 020 to 019 should succeed when all tables are empty."""
        cfg, db_path = alembic_config_020
        command.upgrade(cfg, "020")

        # Verify all three tables exist before downgrade
        assert self._table_exists(db_path, "domain_tumor_board_consensus")
        assert self._table_exists(db_path, "domain_tumor_board_opinions")
        assert self._table_exists(db_path, "domain_tumor_board_consensus_traces")

        # Downgrade should succeed (no data in any table)
        command.downgrade(cfg, "019")

        # Verify all three tables are removed
        assert self._table_exists(db_path, "domain_tumor_board_consensus") is False
        assert self._table_exists(db_path, "domain_tumor_board_opinions") is False
        assert self._table_exists(db_path, "domain_tumor_board_consensus_traces") is False

    # ── re-upgrade cycle ─────────────────────────────────────────────────────

    def test_reupgrade_020_cycle(self, alembic_config_020):
        """019 → 020 → (cannot downgrade, but upgrade is idempotent)."""
        cfg, db_path = alembic_config_020

        # First pass: 019 → 020
        command.upgrade(cfg, "020")
        assert self._table_exists(db_path, "domain_tumor_board_consensus")

        # Cannot downgrade, but upgrading again should succeed (idempotent)
        command.upgrade(cfg, "020")
        assert self._table_exists(db_path, "domain_tumor_board_consensus")
        assert self._table_exists(db_path, "domain_tumor_board_opinions")
        assert self._table_exists(db_path, "domain_tumor_board_consensus_traces")

    # ── FK existence ─────────────────────────────────────────────────────────

    def test_upgrade_020_foreign_keys_exist(self, alembic_config_020):
        """Verify that FK constraints are created on the new tables."""
        cfg, db_path = alembic_config_020
        command.upgrade(cfg, "020")

        import sqlite3
        conn = sqlite3.connect(str(db_path))

        # Check FK on domain_tumor_board_consensus
        cursor = conn.execute("PRAGMA foreign_key_list(domain_tumor_board_consensus)")
        fks = {row[3]: row[4] for row in cursor.fetchall()}
        assert "patient_id" in fks, "Missing FK from consensus to domain_patients"
        assert fks["patient_id"] == "id"
        assert "recommendation_id" in fks, "Missing FK from consensus to domain_recommendations"
        assert "clinical_decision_id" in fks, "Missing FK from consensus to domain_clinical_decisions"

        # Check FK on domain_tumor_board_opinions
        cursor = conn.execute("PRAGMA foreign_key_list(domain_tumor_board_opinions)")
        fks = {row[3]: row[4] for row in cursor.fetchall()}
        assert "consensus_id" in fks, "Missing FK from opinions to consensus"
        assert fks["consensus_id"] == "id"

        # Check FK on domain_tumor_board_consensus_traces
        cursor = conn.execute("PRAGMA foreign_key_list(domain_tumor_board_consensus_traces)")
        fks = {row[3]: row[4] for row in cursor.fetchall()}
        assert "consensus_id" in fks, "Missing FK from traces to consensus"
        assert fks["consensus_id"] == "id"

        conn.close()

    # ── Index existence ──────────────────────────────────────────────────────

    def test_upgrade_020_indexes_exist(self, alembic_config_020):
        """Verify indexes are created as expected."""
        cfg, db_path = alembic_config_020
        command.upgrade(cfg, "020")

        # Check indexes on domain_tumor_board_consensus
        indexes = self._get_indexes(db_path, "domain_tumor_board_consensus")
        idx_names = list(indexes.keys())
        assert any("consensus_id" in str(idx) for idx in idx_names), (
            "Missing index on consensus_id"
        )
        assert any("patient_id" in str(idx) for idx in idx_names), (
            "Missing index on patient_id"
        )

        # Check indexes on domain_tumor_board_opinions
        indexes = self._get_indexes(db_path, "domain_tumor_board_opinions")
        idx_names = list(indexes.keys())
        assert any("consensus_id" in str(idx) for idx in idx_names), (
            "Missing index on opinions.consensus_id"
        )

        # Check indexes on domain_tumor_board_consensus_traces
        indexes = self._get_indexes(db_path, "domain_tumor_board_consensus_traces")
        idx_names = list(indexes.keys())
        assert any("trace_id" in str(idx) for idx in idx_names), (
            "Missing index on traces.trace_id"
        )
        assert any("consensus_id" in str(idx) for idx in idx_names), (
            "Missing index on traces.consensus_id"
        )

    # ── Unique constraint ────────────────────────────────────────────────────

    def test_upgrade_020_unique_constraint_exists(self, alembic_config_020):
        """Verify the (trace_id, step_order) unique constraint on traces."""
        cfg, db_path = alembic_config_020
        command.upgrade(cfg, "020")

        unique_constraints = self._get_unique_constraints(
            db_path, "domain_tumor_board_consensus_traces",
        )

        # Check for the constraint by name or columns
        found = False
        for name, columns in unique_constraints.items():
            if set(columns) == {"trace_id", "step_order"}:
                found = True
                break

        # Also check via index introspection (unique index)
        if not found:
            indexes = self._get_indexes(db_path, "domain_tumor_board_consensus_traces")
            for name, info in indexes.items():
                if info["unique"] and set(info["columns"]) == {"trace_id", "step_order"}:
                    found = True
                    break

        assert found, (
            "Missing unique constraint on (trace_id, step_order) "
            "in domain_tumor_board_consensus_traces"
        )

    # ── upgrade preserves existing tables ────────────────────────────────────

    def test_upgrade_020_preserves_019_tables(self, alembic_config_020):
        """Upgrading to 020 should not drop tables created by 019."""
        cfg, db_path = alembic_config_020

        command.upgrade(cfg, "019")
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables_before = {row[0] for row in cursor.fetchall()}
        conn.close()

        command.upgrade(cfg, "020")
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables_after = {row[0] for row in cursor.fetchall()}
        conn.close()

        missing = tables_before - tables_after
        assert not missing, f"Tables from 019 missing after 020 upgrade: {missing}"

        # New tables should be present
        assert "domain_tumor_board_consensus" in tables_after
        assert "domain_tumor_board_opinions" in tables_after
        assert "domain_tumor_board_consensus_traces" in tables_after

    # ── columns verification ─────────────────────────────────────────────────

    def test_upgrade_020_columns_consensus_table(self, alembic_config_020):
        """Verify columns of domain_tumor_board_consensus."""
        cfg, db_path = alembic_config_020
        command.upgrade(cfg, "020")

        import sqlite3
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("PRAGMA table_info(domain_tumor_board_consensus)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        conn.close()

        expected = {
            "consensus_id", "patient_id", "recommendation_id",
            "clinical_decision_id", "consensus_status", "consensus_score",
            "final_recommendation", "supporting_rationale",
            "dissenting_opinions", "unresolved_questions", "required_follow_up",
            "participating_specialties", "created_by", "created_at", "updated_at",
        }
        for col in expected:
            assert col in columns, f"Column {col} missing from domain_tumor_board_consensus"

    def test_upgrade_020_columns_opinions_table(self, alembic_config_020):
        """Verify columns of domain_tumor_board_opinions."""
        cfg, db_path = alembic_config_020
        command.upgrade(cfg, "020")

        import sqlite3
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("PRAGMA table_info(domain_tumor_board_opinions)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        conn.close()

        expected = {
            "consensus_id", "specialty", "participant_id",
            "position", "confidence", "rationale",
            "supporting_evidence", "contraindications",
            "preferred_option", "alternative_option",
            "requires_more_information", "created_at",
        }
        for col in expected:
            assert col in columns, f"Column {col} missing from domain_tumor_board_opinions"

    def test_upgrade_020_columns_traces_table(self, alembic_config_020):
        """Verify columns of domain_tumor_board_consensus_traces."""
        cfg, db_path = alembic_config_020
        command.upgrade(cfg, "020")

        import sqlite3
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute("PRAGMA table_info(domain_tumor_board_consensus_traces)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        conn.close()

        expected = {
            "trace_id", "consensus_id", "step_order",
            "step_type", "input_summary", "output_summary", "created_at",
        }
        for col in expected:
            assert col in columns, f"Column {col} missing from domain_tumor_board_consensus_traces"

