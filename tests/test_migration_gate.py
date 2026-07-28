"""
CI Migration Gate Verification Tests
唯讀測試 — 驗證 migration 025 的 constraint 已正確建立。
CI 中的 upgrade/downgrade 步驟已在測試前完成。
"""
import pytest
from sqlalchemy import text, inspect


@pytest.mark.pg
class TestMigrationGate:
    """驗證 migration 025 的 schema 狀態。"""

    def test_composite_unique_constraints_exist(self, pg_connection):
        """驗證 uq_trace_step (UNIQUE trace_id, step_order) 存在"""
        rows = pg_connection.execute(text("""
            SELECT con.conname FROM pg_catalog.pg_constraint con
            JOIN pg_catalog.pg_class rel ON rel.oid = con.conrelid
            WHERE rel.relname = 'domain_treatment_plan_traces'
              AND con.contype = 'u'
        """)).fetchall()
        names = [r[0] for r in rows]
        assert 'uq_trace_step' in names, f"Missing uq_trace_step in {names}"

    def test_trace_id_unique_removed(self, pg_connection):
        """驗證舊的 UNIQUE(trace_id) 約束已被移除（已取代為複合唯一）"""
        rows = pg_connection.execute(text("""
            SELECT con.conname FROM pg_catalog.pg_constraint con
            JOIN pg_catalog.pg_class rel ON rel.oid = con.conrelid
            WHERE rel.relname = 'domain_treatment_plan_traces'
              AND con.contype = 'u'
        """)).fetchall()
        names = [r[0] for r in rows]
        # 不應再有單獨的 trace_id UNIQUE
        for name in names:
            assert name != 'domain_treatment_plan_traces_trace_id_key'

    def test_foreign_keys_exist(self, pg_connection):
        """驗證 foreign keys 存在於 domain_treatment_plans"""
        rows = pg_connection.execute(text("""
            SELECT con.conname FROM pg_catalog.pg_constraint con
            JOIN pg_catalog.pg_class rel ON rel.oid = con.conrelid
            WHERE rel.relname = 'domain_treatment_plans'
              AND con.contype = 'f'
        """)).fetchall()
        fk_names = [r[0] for r in rows]
        assert 'fk_prev_version' in fk_names
        assert 'fk_supersedes_version' in fk_names

    def test_plan_id_version_unique(self, pg_connection):
        """驗證 uq_plan_id_version (UNIQUE plan_id, version) 存在"""
        rows = pg_connection.execute(text("""
            SELECT con.conname FROM pg_catalog.pg_constraint con
            JOIN pg_catalog.pg_class rel ON rel.oid = con.conrelid
            WHERE rel.relname = 'domain_treatment_plans'
              AND con.contype = 'u'
        """)).fetchall()
        names = [r[0] for r in rows]
        assert 'uq_plan_id_version' in names, f"Missing uq_plan_id_version in {names}"
