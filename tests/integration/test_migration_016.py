"""
Migration 016 — Phase 2 Clinical Workspace: upgrade / downgrade 循环测试.

验证 ``016_phase2_clinical_workspace.py`` 的 upgrade() 和 downgrade()
互为逆操作，且支持完整的 upgrade → downgrade → upgrade 循环。

通过 ``CI_SKIP_MIGRATION`` 环境变量或 ``--skip-migration`` 标记跳过
（在没有数据库的 CI 环境中使用）。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from alembic.config import Config
from alembic import command
from sqlalchemy import inspect as sa_inspect

# ── 条件跳过 ──────────────────────────────────────────────────────────────────
_SKIP = os.environ.get("CI_SKIP_MIGRATION", "").lower() in ("1", "true", "yes")
_REASON = "CI_SKIP_MIGRATION is set — no database available"


# ── 辅助函数 ──────────────────────────────────────────────────────────────────


def _make_alembic_config(db_url: str | None = None) -> Config:
    """构建指向临时 SQLite 数据库的 Alembic 配置。

    使用 ``sqlite+aiosqlite://``（内存数据库）作为默认值，
    确保测试在开发环境和 CI 中都能执行（只要 aiosqlite 已安装）。
    """
    cfg = Config()
    cfg.set_main_option("script_location", str(Path("migrations").resolve()))
    cfg.set_main_option(
        "sqlalchemy.url",
        db_url or "sqlite+aiosqlite:///./test_migration_016.db",
    )
    return cfg


def _table_exists(inspector, table: str) -> bool:
    """检查 SQLAlchemy inspect 对象中是否存在指定表。"""
    return table in inspector.get_table_names()


# ── 016 新增的表列表 ──────────────────────────────────────────────────────────

PHASE2_TABLES = [
    "clinical_decision_nodes",
    "clinical_agent_opinions",
    "clinical_consensus_results",
    "clinical_recommendations",
]


# ── 共用 fixture ──────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def alembic_cfg() -> Config:
    """模块级 fixture：创建 Alembic 配置（SQLite 文件数据库）。"""
    cfg = _make_alembic_config()
    yield cfg
    # 清理临时数据库文件
    db_path = Path("test_migration_016.db")
    if db_path.exists():
        db_path.unlink(missing_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
# 测试类
# ═══════════════════════════════════════════════════════════════════════════════


class TestMigration016Upgrade:
    """测试 upgrade 创建所有必要表。"""

    @pytest.mark.skipif(_SKIP, reason=_REASON)
    def test_upgrade_head_creates_phase2_tables(self, alembic_cfg):
        """执行 ``alembic upgrade head`` 后验证 Phase 2 表存在。"""
        # 执行全部 migration 到最新版本
        command.upgrade(alembic_cfg, "head")

        # 获取数据库连接并检查表
        from sqlalchemy.ext.asyncio import create_async_engine

        engine = create_async_engine(alembic_cfg.get_main_option("sqlalchemy.url"))

        async def _check():
            async with engine.connect() as conn:
                inspector = await conn.run_sync(sa_inspect)
                for table in PHASE2_TABLES:
                    assert _table_exists(
                        inspector, table
                    ), f"表 {table} 应在 upgrade head 后存在"

        import asyncio

        asyncio.run(_check())

    @pytest.mark.skipif(_SKIP, reason=_REASON)
    def test_upgrade_head_creates_indexes(self, alembic_cfg):
        """验证关键索引已创建。"""
        command.upgrade(alembic_cfg, "head")

        from sqlalchemy.ext.asyncio import create_async_engine

        engine = create_async_engine(alembic_cfg.get_main_option("sqlalchemy.url"))

        async def _check():
            async with engine.connect() as conn:
                inspector = await conn.run_sync(sa_inspect)
                # clinical_decision_nodes 索引
                idx_cdn = {i["name"] for i in inspector.get_indexes("clinical_decision_nodes")}
                assert any("case_id" in n for n in idx_cdn), "clinical_decision_nodes 应有 case_id 索引"
                assert any("context_hash" in n for n in idx_cdn), "clinical_decision_nodes 应有 context_hash 索引"

                # clinical_agent_opinions 索引
                idx_cao = {i["name"] for i in inspector.get_indexes("clinical_agent_opinions")}
                assert any("case_id" in n for n in idx_cao), "clinical_agent_opinions 应有 case_id 索引"
                assert any("run_id" in n for n in idx_cao), "clinical_agent_opinions 应有 run_id 索引"

        import asyncio

        asyncio.run(_check())


class TestMigration016Downgrade:
    """测试 downgrade 正确撤销 016 变更。"""

    @pytest.mark.skipif(_SKIP, reason=_REASON)
    def test_downgrade_removes_phase2_tables(self, alembic_cfg):
        """执行 upgrade head 后 downgrade -1，验证 Phase 2 表已删除。"""
        command.upgrade(alembic_cfg, "head")
        command.downgrade(alembic_cfg, "-1")

        from sqlalchemy.ext.asyncio import create_async_engine

        engine = create_async_engine(alembic_cfg.get_main_option("sqlalchemy.url"))

        async def _check():
            async with engine.connect() as conn:
                inspector = await conn.run_sync(sa_inspect)
                for table in PHASE2_TABLES:
                    assert not _table_exists(
                        inspector, table
                    ), f"表 {table} 应在 downgrade -1 后删除"

        import asyncio

        asyncio.run(_check())


class TestMigration016Cycle:
    """完整的 upgrade → downgrade → upgrade 循环测试。"""

    @pytest.mark.skipif(_SKIP, reason=_REASON)
    def test_upgrade_downgrade_upgrade_cycle(self, alembic_cfg):
        """执行 upgrade head → downgrade -1 → upgrade head，验证表状态。"""
        # ── 第 1 步：upgrade head ──
        command.upgrade(alembic_cfg, "head")

        from sqlalchemy.ext.asyncio import create_async_engine

        engine = create_async_engine(alembic_cfg.get_main_option("sqlalchemy.url"))

        async def _step1():
            async with engine.connect() as conn:
                inspector = await conn.run_sync(sa_inspect)
                for table in PHASE2_TABLES:
                    assert _table_exists(inspector, table), f"Step 1: {table} 应存在"

        import asyncio

        asyncio.run(_step1())

        # ── 第 2 步：downgrade -1 ──
        command.downgrade(alembic_cfg, "-1")

        async def _step2():
            async with engine.connect() as conn:
                inspector = await conn.run_sync(sa_inspect)
                for table in PHASE2_TABLES:
                    assert not _table_exists(
                        inspector, table
                    ), f"Step 2: {table} 应已被删除"

        asyncio.run(_step2())

        # ── 第 3 步：再次 upgrade head ──
        command.upgrade(alembic_cfg, "head")

        async def _step3():
            async with engine.connect() as conn:
                inspector = await conn.run_sync(sa_inspect)
                for table in PHASE2_TABLES:
                    assert _table_exists(
                        inspector, table
                    ), f"Step 3: {table} 应重新创建"

        asyncio.run(_step3())


# ═══════════════════════════════════════════════════════════════════════════════
# 静态审计测试（无需数据库）
# ═══════════════════════════════════════════════════════════════════════════════


class TestMigration016StaticAudit:
    """对 migration 016 源码的静态分析，不依赖数据库连接。"""

    MIGRATION_PATH = Path("migrations/versions/016_phase2_clinical_workspace.py")

    @pytest.fixture(scope="class")
    def migration_module(self):
        """动态导入 migration 016 模块。"""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "migration_016",
            str(self.MIGRATION_PATH),
        )
        assert spec is not None, f"Migration 文件未找到: {self.MIGRATION_PATH}"
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_revision_identifiers(self, migration_module):
        """验证 revision 标识符正确。"""
        assert migration_module.revision == "016"
        assert migration_module.down_revision == "015"

    def test_upgrade_function_exists(self, migration_module):
        """验证 upgrade() 函数存在。"""
        assert hasattr(migration_module, "upgrade"), "缺少 upgrade()"
        assert callable(migration_module.upgrade), "upgrade() 不是可调用对象"

    def test_downgrade_function_exists(self, migration_module):
        """验证 downgrade() 函数存在。"""
        assert hasattr(migration_module, "downgrade"), "缺少 downgrade()"
        assert callable(migration_module.downgrade), "downgrade() 不是可调用对象"

    def test_upgrade_creates_four_tables(self, migration_module):
        """验证 upgrade 通过静态分析应创建 4 个表。"""
        import ast

        source = self.MIGRATION_PATH.read_text("utf-8")
        tree = ast.parse(source)

        # 在 upgrade 函数中查找 create_table 调用
        create_tables = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "upgrade":
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        func = child.func
                        if isinstance(func, ast.Attribute) and func.attr == "create_table":
                            if child.args:
                                name_node = child.args[0]
                                if isinstance(name_node, ast.Constant):
                                    create_tables.append(name_node.value)

        assert len(create_tables) == 4, (
            f"upgrade() 应包含 4 个 create_table 调用，"
            f"实际找到 {len(create_tables)}: {create_tables}"
        )
        assert "clinical_decision_nodes" in create_tables
        assert "clinical_agent_opinions" in create_tables
        assert "clinical_consensus_results" in create_tables
        assert "clinical_recommendations" in create_tables

    def test_downgrade_drops_four_tables(self, migration_module):
        """验证 downgrade 通过静态分析应删除 4 个表（逆序）。"""
        import ast

        source = self.MIGRATION_PATH.read_text("utf-8")
        tree = ast.parse(source)

        drop_tables = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "downgrade":
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        func = child.func
                        if isinstance(func, ast.Attribute) and func.attr == "drop_table":
                            if child.args:
                                name_node = child.args[0]
                                if isinstance(name_node, ast.Constant):
                                    drop_tables.append(name_node.value)

        assert len(drop_tables) == 4, (
            f"downgrade() 应包含 4 个 drop_table 调用，"
            f"实际找到 {len(drop_tables)}: {drop_tables}"
        )
        # 验证逆序（先创建的表后删除）
        assert drop_tables == [
            "clinical_recommendations",
            "clinical_consensus_results",
            "clinical_agent_opinions",
            "clinical_decision_nodes",
        ], f"downgrade 删除顺序应为逆序: {drop_tables}"

    def test_upgrade_downgrade_symmetric(self, migration_module):
        """验证 upgrade 创建的表集合与 downgrade 删除的表集合一致。"""
        import ast

        source = self.MIGRATION_PATH.read_text("utf-8")
        tree = ast.parse(source)

        created = set()
        dropped = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        func = child.func
                        if isinstance(func, ast.Attribute):
                            if child.args and isinstance(child.args[0], ast.Constant):
                                if func.attr == "create_table":
                                    created.add(child.args[0].value)
                                elif func.attr == "drop_table":
                                    dropped.add(child.args[0].value)

        assert created == dropped, (
            f"upgrade 创建的表 ({created}) 与 "
            f"downgrade 删除的表 ({dropped}) 不一致"
        )

    def test_foreign_key_references_exist(self, migration_module):
        """验证外键引用的表在项目中存在（基本完整性检查）。"""
        import ast

        source = self.MIGRATION_PATH.read_text("utf-8")
        tree = ast.parse(source)

        referenced_tables = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr == "ForeignKey":
                    if node.args and isinstance(node.args[0], ast.Constant):
                        fk_value: str = node.args[0].value
                        # 提取被引用的表名（如 "domain_cancer_cases.id" → "domain_cancer_cases"）
                        table_name = fk_value.split(".")[0]
                        referenced_tables.add(table_name)

        # 被引用的表应在 migration 链中创建过
        # domain_cancer_cases 由 migration 001 创建
        # clinical_decision_nodes 是自引用，由本 migration 创建
        assert "domain_cancer_cases" in referenced_tables, "应引用 domain_cancer_cases"
        assert "clinical_decision_nodes" in referenced_tables, "应有自引用 FK"
