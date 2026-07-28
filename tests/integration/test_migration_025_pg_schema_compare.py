"""
PostgreSQL Integration Test: Schema Compare
驗證 downgrade/re-upgrade 前後 schema 一致。
"""
import pytest
from sqlalchemy import inspect


def get_schema_summary(connection):
    """取得 schema 的結構摘要用於比對"""
    inspector = inspect(connection)
    tables = inspector.get_table_names()
    summary = {}
    for table in sorted(tables):
        columns = [(c["name"], c["type"].__class__.__name__, c["nullable"])
                   for c in inspector.get_columns(table)]
        pk = inspector.get_pk_constraint(table)
        fks = [(fk["constrained_columns"], fk["referred_table"])
               for fk in inspector.get_foreign_keys(table)]
        unique_constraints = [(uc["name"], uc["column_names"])
                              for uc in inspector.get_unique_constraints(table)]
        indexes = [(ix["name"], ix["column_names"], ix["unique"])
                   for ix in inspector.get_indexes(table)]
        summary[table] = {
            "columns": sorted(columns),
            "pk": pk,
            "fks": sorted(fks),
            "unique_constraints": sorted(unique_constraints),
            "indexes": sorted(indexes),
        }
    return summary


@pytest.mark.pg
@pytest.mark.integration
class TestSchemaComparePG:
    """驗證 downgrade/re-upgrade 前後 schema 完全一致。"""

    def test_downgrade_025_to_024_schema_equal(self, pg_connection, alembic_runner):
        """025 downgrade 到 024 後 schema 應與直接 024 upgrade 相等"""
        # Step 1: 先 upgrade 到 024，記錄 schema
        alembic_runner("upgrade", "024")
        schema_024 = get_schema_summary(pg_connection)

        # Step 2: upgrade 到 025
        alembic_runner("upgrade", "025")

        # Step 3: downgrade 回 024
        alembic_runner("downgrade", "024")
        schema_after_downgrade = get_schema_summary(pg_connection)

        # 比對：降級後的 schema 應與 024 完全相同
        assert schema_024 == schema_after_downgrade, \
            "Downgrade 025→024 schema mismatch"

    def test_reupgrade_024_to_025_schema_equal(self, pg_connection, alembic_runner):
        """025→024→025 後 schema 應與直接 025 相等"""
        # Step 1: 直接 upgrade 到 025，記錄 schema
        alembic_runner("upgrade", "025")
        schema_025 = get_schema_summary(pg_connection)

        # Step 2: downgrade 回 024
        alembic_runner("downgrade", "024")

        # Step 3: re-upgrade 到 025
        alembic_runner("upgrade", "025")
        schema_after_reupgrade = get_schema_summary(pg_connection)

        assert schema_025 == schema_after_reupgrade, \
            "Re-upgrade 024→025 schema mismatch"
