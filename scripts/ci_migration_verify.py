"""
CI Migration Verification Script.

替代 alembic check，只驗證：
1. migration head 已到達（current revision == head）
2. 關鍵 constraint 存在於資料庫中
"""
import os
import re
import sys

from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, text


def main():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL not set")
        sys.exit(1)

    # Convert async URL to sync
    sync_url = re.sub(r"\+asyncpg|\+aiosqlite|\+aiomysql|\+aioodbc|\+asyncmy", "", db_url)
    if sync_url.startswith("postgresql://") and "+psycopg2" not in sync_url:
        sync_url = sync_url.replace("postgresql://", "postgresql+psycopg2://", 1)

    engine = create_engine(sync_url, pool_pre_ping=True)

    with engine.connect() as conn:
        # 1. Check migration head
        context = MigrationContext.configure(conn)
        current_rev = context.get_current_revision()

        config = Config("migrations/alembic.ini")
        script = ScriptDirectory.from_config(config)
        head_rev = script.get_current_head()

        assert current_rev == head_rev, (
            f"Migration mismatch: head={head_rev}, current={current_rev}"
        )
        print(f"✅ Migration head reached: {current_rev}")

        # 2. Check key constraints exist
        # uq_trace_step 是 019 建立的 UNIQUE INDEX（不是 constraint）
        # 改為檢查 pg_indexes
        indexes = [
            ("uq_trace_step", "domain_treatment_plan_traces"),
        ]
        for idxname, table in indexes:
            row = conn.execute(
                text(f"""SELECT 1 FROM pg_catalog.pg_indexes
                    WHERE indexname = '{idxname}'
                      AND tablename = '{table}'""")
            ).fetchone()
            assert row, f"❌ Index {idxname} not found on {table}"
            print(f"✅ Index {idxname} exists on {table}")

        # 同時驗證 UNIQUE(trace_id) constraint 已被移除
        row = conn.execute(text("""
            SELECT 1 FROM pg_catalog.pg_constraint con
            JOIN pg_catalog.pg_class rel ON rel.oid = con.conrelid
            WHERE rel.relname = 'domain_treatment_plan_traces'
              AND con.contype = 'u'
              AND con.conkey = (
                  SELECT array_agg(a.attnum ORDER BY a.attnum)
                  FROM pg_catalog.pg_attribute a
                  WHERE a.attrelid = rel.oid AND a.attname = 'trace_id'
              )
        """)).fetchone()
        assert row is None, "❌ UNIQUE(trace_id) constraint should have been removed"
        print("✅ No UNIQUE(trace_id) constraint remains on domain_treatment_plan_traces")

    print("🎉 Migration verification PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
