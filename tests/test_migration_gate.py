"""
CI Migration Gate Tests
用於 CI 中驗證 migration gate 流程的各個步驟。
對應 .github/workflows/ci.yml 中 migration-gate 作業的步驟。
"""
import pytest
from sqlalchemy import text


@pytest.mark.pg
class TestMigrationGate:
    """CI Migration Gate 驗證：每個步驟獨立測試。"""

    def test_upgrade_head_success(self, alembic_runner):
        """Step 1: upgrade head 成功執行"""
        alembic_runner("upgrade", "head")

    def test_composite_unique_constraints_exist(self, pg_connection, alembic_runner):
        """Step 2: 驗證 composite unique constraints 正確建立"""
        alembic_runner("upgrade", "head")

        # 檢查 domain_treatment_plans 的 uq_plan_id_version
        rows = pg_connection.execute(text("""
            SELECT con.conname FROM pg_catalog.pg_constraint con
            JOIN pg_catalog.pg_class rel ON rel.oid = con.conrelid
            WHERE rel.relname = 'domain_treatment_plans'
              AND con.contype = 'u'
        """)).fetchall()
        unique_names = [r[0] for r in rows]
        assert 'uq_plan_id_version' in unique_names, \
            f"Missing uq_plan_id_version in {unique_names}"

        # 檢查 domain_treatment_plan_traces 的 uq_trace_step
        rows = pg_connection.execute(text("""
            SELECT con.conname FROM pg_catalog.pg_constraint con
            JOIN pg_catalog.pg_class rel ON rel.oid = con.conrelid
            WHERE rel.relname = 'domain_treatment_plan_traces'
              AND con.contype = 'u'
        """)).fetchall()
        unique_names = [r[0] for r in rows]
        assert 'uq_trace_step' in unique_names, \
            f"Missing uq_trace_step in {unique_names}"

    def test_foreign_keys_exist(self, pg_connection, alembic_runner):
        """Step 3: 驗證 foreign keys (previous_version_id, supersedes_version_id) 存在"""
        alembic_runner("upgrade", "head")

        rows = pg_connection.execute(text("""
            SELECT con.conname FROM pg_catalog.pg_constraint con
            JOIN pg_catalog.pg_class rel ON rel.oid = con.conrelid
            WHERE rel.relname = 'domain_treatment_plans'
              AND con.contype = 'f'
        """)).fetchall()
        fk_names = [r[0] for r in rows]
        assert 'fk_prev_version' in fk_names, \
            f"Missing fk_prev_version in {fk_names}"
        assert 'fk_supersedes_version' in fk_names, \
            f"Missing fk_supersedes_version in {fk_names}"

    def test_downgrade_024_success(self, pg_connection, alembic_runner):
        """Step 4: downgrade 到 024 成功"""
        alembic_runner("upgrade", "head")
        alembic_runner("downgrade", "024")

        # 驗證：025 新增的 columns 不應存在
        inspector = pytest.importorskip("sqlalchemy").inspect(pg_connection)
        plan_cols = {c["name"] for c in inspector.get_columns("domain_treatment_plans")}
        assert "previous_version_id" not in plan_cols
        assert "supersedes_version_id" not in plan_cols

    def test_reupgrade_head_success(self, pg_connection, alembic_runner):
        """Step 5: downgrade 024 → re-upgrade head 成功"""
        alembic_runner("upgrade", "head")
        alembic_runner("downgrade", "024")
        alembic_runner("upgrade", "head")

        # 驗證：025 的 columns 已恢復
        inspector = pytest.importorskip("sqlalchemy").inspect(pg_connection)
        plan_cols = {c["name"] for c in inspector.get_columns("domain_treatment_plans")}
        assert "previous_version_id" in plan_cols
        assert "supersedes_version_id" in plan_cols
