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
        constraints = [
            ("uq_trace_step", "domain_treatment_plan_traces"),
        ]

        for conname, table in constraints:
            row = conn.execute(
                text(f"""SELECT 1 FROM pg_catalog.pg_constraint
                    WHERE conname = '{conname}'
                      AND conrelid = '{table}'::regclass""")
            ).fetchone()
            assert row, f"❌ Constraint {conname} not found on {table}"
            print(f"✅ Constraint {conname} exists on {table}")

    print("🎉 Migration verification PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
