"""
PostgreSQL Integration Test: Trace Constraint
驗證同 trace_id 多個 step_order 可以共存。
"""
import pytest
from sqlalchemy import text


@pytest.mark.pg
@pytest.mark.integration
class TestTraceConstraintPG:
    """PostgreSQL 上驗證 UNIQUE(trace_id, step_order) 約束正確運作。"""

    def test_same_trace_id_multiple_steps(self, pg_connection, alembic_runner):
        """同 trace_id 可插入 step=1,2,3 全部成功"""
        # 先確保 schema 為最新
        alembic_runner("upgrade", "head")

        trace_id = "test-trace-multi-step"
        for step in [1, 2, 3]:
            pg_connection.execute(text("""
                INSERT INTO domain_treatment_plan_traces
                (trace_id, step_order, plan_id, node_type, "data")
                VALUES (:trace_id, :step, :plan_id, :node_type, :data)
            """), {
                "trace_id": trace_id,
                "step": step,
                "plan_id": f"plan-{step}",
                "node_type": "standard",
                "data": '{"key": "value"}'
            })
        pg_connection.commit()

        # 驗證三筆資料
        rows = pg_connection.execute(
            text("SELECT trace_id, step_order FROM domain_treatment_plan_traces WHERE trace_id = :tid ORDER BY step_order"),
            {"tid": trace_id}
        ).fetchall()
        assert len(rows) == 3
        assert [r[1] for r in rows] == [1, 2, 3]
