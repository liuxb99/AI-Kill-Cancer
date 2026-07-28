"""
PostgreSQL Integration Test: Full Migration Cycle
完整 upgrade → downgrade → re-upgrade → insert → query 流程。
"""
import pytest
from sqlalchemy import text


@pytest.mark.pg
@pytest.mark.integration
class TestFullCyclePG:
    """PostgreSQL 完整 migration 生命週期測試。"""

    def test_full_cycle_upgrade_downgrade_reupgrade(self, pg_connection, alembic_runner):
        """upgrade head → downgrade 024 → upgrade head → insert → query"""
        # Step 1: upgrade head
        alembic_runner("upgrade", "head")

        # Step 2: 插入測試資料驗證 025 schema 可用
        trace_id = "full-cycle-trace"
        pg_connection.execute(text("""
            INSERT INTO domain_treatment_plan_traces
            (trace_id, step_order, plan_id, node_type, "data")
            VALUES (:trace_id, :step, :plan_id, :node_type, :data)
        """), {
            "trace_id": trace_id,
            "step": 1,
            "plan_id": "plan-1",
            "node_type": "standard",
            "data": '{"step": 1}'
        })
        pg_connection.commit()

        # Step 3: downgrade 到 024
        alembic_runner("downgrade", "024")

        # Step 4: re-upgrade 到 head
        alembic_runner("upgrade", "head")

        # Step 5: 插入不同 step 資料
        for step in [2, 3]:
            pg_connection.execute(text("""
                INSERT INTO domain_treatment_plan_traces
                (trace_id, step_order, plan_id, node_type, "data")
                VALUES (:trace_id, :step, :plan_id, :node_type, :data)
            """), {
                "trace_id": trace_id,
                "step": step,
                "plan_id": f"plan-{step}",
                "node_type": "standard",
                "data": '{"step": %d}' % step
            })
        pg_connection.commit()

        # Step 6: query 驗證全部三筆存在
        rows = pg_connection.execute(
            text("SELECT trace_id, step_order FROM domain_treatment_plan_traces WHERE trace_id = :tid ORDER BY step_order"),
            {"tid": trace_id}
        ).fetchall()
        assert len(rows) == 3, f"Expected 3 rows, got {len(rows)}"
        assert [r[1] for r in rows] == [1, 2, 3]
