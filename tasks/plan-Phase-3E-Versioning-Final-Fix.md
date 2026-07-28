# Plan: Phase-3E-Versioning-Final-Fix

## 1. 任务总览

| 属性 | 值 |
|------|-----|
| 任务 ID | Phase-3E-Versioning-Final-Fix |
| 场景 | hardening（架构强化） |
| 优先级 | P0（Critical） |
| 目标 | 修正 ChatGPT GitHub Review 发现的 4 个 P0 版本化架构问题，所有测试通过 |

### 核心原则

- **不得修改已发布的 Migration 023**：恢复 023 到最初的发布版本（`feat(phase3e)` commit），将硬化修改移至 025
- **不得新增功能、不得修改需求、不得进入 Phase 3F**
- **不得修改 AGENTS.md、不得修改既有 API 行为（除 Version API 的拆解）**
- **所有变更必须在 Python Tests、Go Tests、Migration Tests、Version Tests、Restart Recovery、Digital Thread 全部 PASS 且 GitHub Actions 全绿后才能合并**

---

## 2. 批次与依赖关系

```
Batch A: Restore 023 + Create 025 Migration
   │
   ▼
Batch B: P0-2 Repository Version Chain
   │
   ▼
Batch C: P0-3 Version Link (previous/supersedes → FK to id)
   │
   ▼
Batch D: P0-4 Phase Mapping (Engine item → phase_type)
   │
   ▼
Batch E: 完整验证（Migration + Unit + Integration + Thread + Restart）
```

---

## 3. 每个批次的详细任务

### Batch A: Migration 修复 (P0-1)

**目标**：恢复 023 为已发布版本，新增 025 实现正确的复合唯一约束

#### A-1: 恢复 Migration 023 为发布版本

| 属性 | 值 |
|------|-----|
| 修改文件 | `migrations/versions/023_phase3e_treatment_plan_tables.py` |
| 责任人 | PLANNER → BUILDER |
| 操作 | 回滚硬化提交对 023 的修改，恢复到 `feat(phase3e)` 的原始状态 |

具体变更（共 4 处）：
1. `plan_id` 列恢复 `unique=True`（移除 `nullable=False` 不影响，保持 `nullable=False, index=True` + 加回 `unique=True`）
2. `UniqueConstraint("plan_id", "version", name="uq_plan_id_version")` → 移除（整行删除）
3. `trace_id` 列恢复 `unique=True`
4. `UniqueConstraint("trace_id", "step_order", name="uq_trace_step")` → 移除（整行删除）

> **恢复后的 023 upgrade() 应匹配 `git show HEAD~1:migrations/versions/023_phase3e_treatment_plan_tables.py` 的内容**

#### A-2: 新增 Migration 025

| 属性 | 值 |
|------|-----|
| 新建文件 | `migrations/versions/025_phase3e_version_composite_unique.py` |
| 责任人 | PLANNER → BUILDER |
| revises | `024` |

Migration 025 upgrade() 操作：
1. 删除 `domain_treatment_plans` 表上 `plan_id` 的单列唯一约束（名为自动生成的，通过 `batch_alter_table` 或 `op.drop_constraint`）
2. 添加 `UniqueConstraint("plan_id", "version", name="uq_plan_id_version")`
3. 删除 `domain_treatment_plan_traces` 表上 `trace_id` 的单列唯一约束
4. 添加 `UniqueConstraint("trace_id", "step_order", name="uq_trace_step")`
5. （预留）添加 `previous_version_id` 和 `supersedes_version_id` 列（Batch C 使用）
6. 保留所有既有数据

关键的 SQLite 兼容性注意：
- SQLite 不支持 `DROP CONSTRAINT`，必须使用 `batch_alter_table` 或 `create_table` + 数据迁移
- 使用 Alembic `batch_alter_table` 上下文管理器处理

#### A-3: 更新 Domain Model 匹配新约束

| 属性 | 值 |
|------|-----|
| 修改文件 | `src/backend/domain/treatment_plan.py` |
| 责任人 | PLANNER → BUILDER |

`TreatmentPlanModel`：
- `__table_args__` 保留 `UniqueConstraint("plan_id", "version", name="uq_plan_id_version")`（已在当前代码中存在，确认一致）

`TreatmentPlanTraceModel`：
- `__table_args__` 保留 `UniqueConstraint("trace_id", "step_order", name="uq_trace_step")`（已在当前代码中存在）

> **注意**：模型已经定义了复合唯一约束，所以模型层面不需要更改。关键是把迁移脚本恢复后再用 025 建立相同的约束。

#### A-4: Migration 测试

| 属性 | 值 |
|------|-----|
| 测试文件 | `tests/test_migration.py` |
| 责任人 | REVIEWER |

添加或更新测试用例：
1. `test_upgrade_023_creates_tables_with_single_unique` — 验证 023 的 plan_id 有 unique=True，trace_id 有 unique=True
2. `test_upgrade_025_adds_composite_unique` — 验证升级到 025 后复合唯一约束存在
3. `test_downgrade_025_restores_single_unique` — 验证降级 025 后恢复单列唯一
4. `test_upgrade_023_to_025_preserves_data` — 升级路径下数据完整
5. `test_old_db_upgrade_025_plan_v1_v2_success` — 旧 DB(023/024) → upgrade 025 → plan v1+v2 成功
6. `test_old_db_upgrade_025_trace_step1_step2_step3_success` — 旧 DB → upgrade 025 → trace step1+2+3 成功

---

### Batch B: Repository Version Chain (P0-2)

**目标**：解决 `get_by_plan_id()` 不合法的问题，拆分为三个明确的方法

#### B-1: 修改 Repository 层

| 属性 | 值 |
|------|-----|
| 修改文件 | `src/backend/repositories/treatment_plan_repo.py` |
| 责任人 | PLANNER → BUILDER |

变更：
1. **保留 `get_by_id()`** 不变（按 PK 查询）
2. **修改 `get_by_plan_id()`**：
   - 当前使用 `scalar_one_or_none()` — 在版本化后 plan_id 可对应多行，此查询不合规
   - 改为 `get_current_by_plan_id()`：`WHERE plan_id = ? AND is_current = true ORDER BY version DESC LIMIT 1`
   - 返回 `Optional[TreatmentPlanModel]`
3. **新增 `get_plan_version(plan_id, version)`**：
   - `WHERE plan_id = ? AND version = ?`
   - 返回 `Optional[TreatmentPlanModel]`
4. **保留 `list_versions()`** 不变（已经存在且正确：`WHERE plan_id = ? ORDER BY version DESC`）
5. **保留 `get_current_by_patient_id()`** 不变
6. **保留 `mark_superseded()`** 不变

```python
# 新的方法签名
async def get_current_by_plan_id(self, plan_id: str) -> Optional[TreatmentPlanModel]:
    """Get the current (latest) version of a plan by business ID."""
    stmt = (
        select(TreatmentPlanModel)
        .where(
            TreatmentPlanModel.plan_id == plan_id,
            TreatmentPlanModel.is_current == True,
        )
        .order_by(TreatmentPlanModel.version.desc())
        .limit(1)
    )
    result = await self.db.execute(stmt)
    return result.scalar_one_or_none()

async def get_plan_version(self, plan_id: str, version: int) -> Optional[TreatmentPlanModel]:
    """Get a specific version of a plan."""
    stmt = select(TreatmentPlanModel).where(
        TreatmentPlanModel.plan_id == plan_id,
        TreatmentPlanModel.version == version,
    )
    result = await self.db.execute(stmt)
    return result.scalar_one_or_none()
```

#### B-2: 修改 Service 层

| 属性 | 值 |
|------|-----|
| 修改文件 | `src/backend/services/treatment_plan_service.py` |
| 责任人 | PLANNER → BUILDER |

所有使用 `get_by_plan_id()` 的地方替换为 `get_current_by_plan_id()`：

| 方法 | 当前使用 | 改为 |
|------|---------|------|
| `get_plan()` | `get_by_plan_id()` → `get_current_by_plan_id()` | 返回当前版本 |
| `_transition_status()` | `get_by_plan_id()` → `get_current_by_plan_id()` | 对当前版本做状态转换 |
| `get_trace()` | `get_by_plan_id()` → `get_current_by_plan_id()` | 获取当前版本的 trace |
| `revise_plan()` | `get_by_plan_id()` → `get_current_by_plan_id()` | 对当前版本做 revision |

同时新增 API 方法：
- `get_plan_version(plan_id, version)` — 调用 `get_plan_version()`
- 保持 `get_versions()` 不变

> **注意**：`get_plan()` 根据需求应该返回**当前版本**（Current Version），而不是"通过 plan_id 找唯一记录"。API 行为不变（GET /{plan_id} 返回当前版本）。

#### B-3: 修改 API 层（可选）

| 属性 | 值 |
|------|-----|
| 修改文件 | `src/backend/api/v1/treatment_plans.py` |
| 责任人 | PLANNER → BUILDER |

如果需要暴露按版本查询的端点，增加：
```
GET /api/v1/treatment-plans/{plan_id}?version=2  → get_plan_version()
```
但根据"不得修改既有 API 行为"原则，可保持现有 `GET /{plan_id}` 返回当前版本（current version）。版本列表通过 `GET /{plan_id}/versions` 获取。

#### B-4: Service 测试更新

| 属性 | 值 |
|------|-----|
| 测试文件 | `tests/backend/services/test_treatment_plan_service.py` |
| 责任人 | TESTER |

更新测试用例：
1. `test_get_plan_returns_current_version` — 验证 get_plan 返回 is_current=true 的版本
2. `test_get_plan_returns_none_when_no_current_version` — 无当前版本返回 None
3. `test_revise_plan_uses_current_version` — revise 操作基于当前版本
4. `test_status_transition_uses_current_version` — 状态转换基于当前版本
5. `test_version_chain_get_v1_revise_v2_get_v2_revise_v3_get_v3` — v1→revise→v2→GET v2→revise→v3→GET v3
6. `test_list_versions_returns_all` — 验证所有版本返回

#### B-5: Repository 测试更新

| 属性 | 值 |
|------|-----|
| 测试文件 | `tests/backend/repositories/test_treatment_plan_repos.py` |
| 责任人 | TESTER |

1. `test_get_current_by_plan_id_returns_current` — 有多个版本时返回 is_current=true 的最新版本
2. `test_get_current_by_plan_id_returns_none` — 无匹配返回 None
3. `test_get_plan_version` — 按 plan_id+version 精准查询
4. `test_get_plan_version_not_found` — 不存在的 version 返回 None

---

### Batch C: Version Link (P0-3)

**目标**：将 `previous_plan_id` / `supersedes_plan_id` 从存 plan_id（业务ID）改为存 version_id（PK，UUID），建立真正的 self reference

#### C-1: 修改 Migration 025（追加列）

| 属性 | 值 |
|------|-----|
| 修改文件 | `migrations/versions/025_phase3e_version_composite_unique.py` |
| 责任人 | PLANNER → BUILDER |

追加操作到 025 upgrade()：
1. 新增列 `previous_version_id`（`String(36)`, nullable=True, index=True）— 引用 `domain_treatment_plans.id`
2. 新增列 `supersedes_version_id`（`String(36)`, nullable=True, index=True）
3. 添加 ForeignKey 约束到 `domain_treatment_plans.id`
4. 数据迁移：从旧的 `previous_plan_id` + `is_current` 逻辑（或 `supersedes_plan_id`）反向解析出对应的 version_id 并填充
5. 旧的 `previous_plan_id` 和 `supersedes_plan_id` 列保留（不删除，保持向后兼容）

> **数据迁移逻辑**：
> - `previous_version_id`：根据 `previous_plan_id`（存储的是 plan_id 业务标识），在同 plan_id 中找 version-1 的记录，取其 id
> - `supersedes_version_id`：根据 `supersedes_plan_id`（存储的是 plan_id 业务标识，是哪个 plan 替代了当前），找当前 plan_id 中被替代的记录的 id

#### C-2: 修改 Domain Model

| 属性 | 值 |
|------|-----|
| 修改文件 | `src/backend/domain/treatment_plan.py` |
| 责任人 | PLANNER → BUILDER |

```python
class TreatmentPlanModel(DBBase):
    __tablename__ = "domain_treatment_plans"
    __table_args__ = (
        UniqueConstraint("plan_id", "version", name="uq_plan_id_version"),
    )

    # 现有字段保持不变...

    # P0-3: 新增版本链接字段（FK self reference）
    previous_version_id = Column(
        CompatUUID,
        ForeignKey("domain_treatment_plans.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    supersedes_version_id = Column(
        CompatUUID,
        ForeignKey("domain_treatment_plans.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Self-referencing relationship
    previous_version = relationship("TreatmentPlanModel", remote_side="TreatmentPlanModel.id",
                                     foreign_keys=[previous_version_id],
                                     lazy="selectin")
    supersedes_version = relationship("TreatmentPlanModel", remote_side="TreatmentPlanModel.id",
                                       foreign_keys=[supersedes_version_id],
                                       lazy="selectin")

    # 保留旧字段作为 transitional（但不再使用）
    previous_plan_id = Column(String(64), nullable=True, index=True)  # deprecated
    supersedes_plan_id = Column(String(64), nullable=True, index=True)  # deprecated
```

#### C-3: 修改 Repository

| 属性 | 值 |
|------|-----|
| 修改文件 | `src/backend/repositories/treatment_plan_repo.py` |
| 责任人 | PLANNER → BUILDER |

修改 `mark_superseded()`：
- 写入 `previous_version_id`（当前 version 的 id → 新版本的 id 关系）
- 保持对旧字段的写入（向后兼容）

```python
async def mark_superseded(
    self,
    plan_id: str,
    superseded_by_version_id: uuid.UUID,  # 新版本的 PK
    revision_reason: str = "",
) -> None:
    """Mark the current version of a plan as superseded."""
    current = await self.get_current_by_plan_id(plan_id)
    if current is None:
        return
    
    stmt = (
        update(TreatmentPlanModel)
        .where(
            TreatmentPlanModel.id == current.id,
        )
        .values(
            is_current=False,
            supersedes_version_id=superseded_by_version_id,
            supersedes_plan_id=plan_id,  # 保持向后兼容
            revision_reason=revision_reason or None,
        )
    )
    await self.db.execute(stmt)
    await self.db.flush()
```

#### C-4: 修改 Service

| 属性 | 值 |
|------|-----|
| 修改文件 | `src/backend/services/treatment_plan_service.py` |
| 责任人 | PLANNER → BUILDER |

在 `revise_plan()` 中：
- 创建新版本后，调用 `mark_superseded()` 传入新版本的 `model.id`
- 新版本的 `previous_version_id` 设置为旧版本的 `id`

在 `_persist_plan()` 中：
- 接受 `previous_version_id` 参数代替 `previous_plan_id`
- 写入新版本的 `previous_version_id`

在 `_model_to_response()` 中：
- `previous_plan_id` 返回 `str(previous_version_id)` 或 `None`
- `supersedes_plan_id` 返回 `str(supersedes_version_id)` 或 `None`
- 保持 API 响应字段名不变（向后兼容）

#### C-5: Model 测试更新

| 属性 | 值 |
|------|-----|
| 测试文件 | `tests/backend/models/test_treatment_plan_models.py` |
| 责任人 | TESTER |

1. `test_version_link_v1_v2_v3` — 创建 v1→revise v2→revise v3，验证 version chain 完整：
   - v2.previous_version_id == v1.id
   - v1.supersedes_version_id == v2.id
   - v3.previous_version_id == v2.id
   - v2.supersedes_version_id == v3.id
2. `test_version_link_self_reference_fk` — FK 约束正确

---

### Batch D: Phase Mapping (P0-4)

**目标**：Engine 输出的 Treatment Item 必须包含 `phase_type`，Service 根据 phase_type 精确匹配 Phase，禁止 fallback

#### D-1: 修改 Engine

| 属性 | 值 |
|------|-----|
| 修改文件 | `src/backend/clinical/treatment_plan_engine.py` |
| 责任人 | PLANNER → BUILDER |

在 `_step_build_treatment_items()` 中：
- 为每个 item 添加 `phase_type` 字段
- 根据 recommendation/decision 的上下文推断 item 应归属的 phase_type
- `_extract_top_drug()` 返回的 dict 添加 `"phase_type": "primary_treatment"`
- `_extract_ranked_drugs()` 的 items 添加 `"phase_type": "primary_treatment"`
- 从 clinical_decision alternatives 来的 items 添加 `"phase_type": "primary_treatment"`

> **推断逻辑**：
> - 如果有 phases 列表且 phase_type 包含 `primary_treatment`，medication 类型的 item 归属 `primary_treatment`
> - 如果 phase_type 包含 `supportive_care`，supportive 类型的 item 归属 `supportive_care`
> - 如果 phase_type 包含 `monitoring`，monitoring 类型的 item 归属对应 phase
> - 默认：第一个 phase 的 phase_type

#### D-2: 修改 Service（Phase 映射逻辑）

| 属性 | 值 |
|------|-----|
| 修改文件 | `src/backend/services/treatment_plan_service.py` |
| 责任人 | PLANNER → BUILDER |

在 `_persist_plan()` 中修改 Items 的 Phase 分配逻辑（当前行 836-874）：

```python
# ── Treatment Items ─────────────────────────────────────────────
item_models: list[TreatmentItemModel] = []
for idx, item_data in enumerate(engine_output.items):
    phase_id = None
    item_phase_type = item_data.get("phase_type")
    
    if item_phase_type and item_phase_type in phase_dicts:
        phase_id = phase_dicts[item_phase_type].id
    else:
        # P0-4: 没有 phase_type 或找不到对应 phase → 直接 Validation Error
        raise ValueError(
            f"Treatment item '{item_data.get('name', 'unknown')}' "
            f"has phase_type='{item_phase_type}' which does not match "
            f"any defined phase. Available phases: {list(phase_dicts.keys())}"
        )
    
    # ... 创建 item_model
```

关键变更：
- **移除 fallback 到第一个 phase 的逻辑**
- phase_type 不匹配时直接抛 `ValueError`（API 层捕获返回 422）
- 确保 `phase_dicts` 在遍历 items 前已完全构建

#### D-3: Engine Output 要求 phase_type

| 属性 | 值 |
|------|-----|
| 修改文件 | `src/backend/clinical/treatment_plan_engine.py` |
| 责任人 | PLANNER → BUILDER |

在 `EngineOutput` 的 docstring 中明确：每个 item dict **必须**包含 `phase_type` 字段。

#### D-4: Engine 测试更新

| 属性 | 值 |
|------|-----|
| 测试文件 | `tests/backend/clinical/test_treatment_plan_engine.py` |
| 责任人 | TESTER |

1. `test_items_have_phase_type` — 所有 item 输出包含 phase_type 字段
2. `test_medication_item_phase_type_primary_treatment` — Medication → primary_treatment
3. `test_monitoring_item_phase_type_monitoring` — Monitoring → monitoring
4. `test_supportive_care_item_phase_type_supportive_care` — Supportive Care → supportive_care

#### D-5: Service 测试更新

| 属性 | 值 |
|------|-----|
| 测试文件 | `tests/backend/services/test_treatment_plan_service.py` |
| 责任人 | TESTER |

1. `test_persist_item_phase_mapping_success` — phase_type 正确匹配
2. `test_persist_item_phase_mapping_not_found_raises_validation_error` — phase_type 不匹配时抛 ValueError
3. `test_no_fallback_to_first_phase` — 验证没有 fallback 逻辑

#### D-6: API 测试更新

| 属性 | 值 |
|------|-----|
| 测试文件 | `tests/backend/api/test_treatment_plan_api.py` |
| 责任人 | TESTER |

1. `test_create_plan_item_phase_mapping` — 创建 plan 时 items 分配到正确 phase
2. `test_create_plan_item_phase_type_error_422` — phase_type 错误时返回 422

---

### Batch E: 完整验证

#### E-1: Migration 全链路测试

| 文件 | 测试内容 |
|------|---------|
| `tests/test_migration.py` | 023→024→025 升级/降级路径，数据保留 |

执行命令：
```bash
cd /workspace && python -m pytest tests/test_migration.py -v --timeout=60 2>&1 | tail -30
```

#### E-2: Unit Tests

| 文件 | 测试内容 |
|------|---------|
| `tests/backend/models/test_treatment_plan_models.py` | Version Link, Composite Unique |
| `tests/backend/repositories/test_treatment_plan_repos.py` | 新的 repository 方法 |
| `tests/backend/services/test_treatment_plan_service.py` | Current Version, Phase Mapping |
| `tests/backend/clinical/test_treatment_plan_engine.py` | phase_type 输出 |

执行命令：
```bash
cd /workspace && python -m pytest tests/backend/models/test_treatment_plan_models.py tests/backend/repositories/test_treatment_plan_repos.py tests/backend/services/test_treatment_plan_service.py tests/backend/clinical/test_treatment_plan_engine.py -v --timeout=120 2>&1 | tail -50
```

#### E-3: API Tests

| 文件 | 测试内容 |
|------|---------|
| `tests/backend/api/test_treatment_plan_api.py` | Version API, Phase Mapping API |

执行命令：
```bash
cd /workspace && python -m pytest tests/backend/api/test_treatment_plan_api.py -v --timeout=120 2>&1 | tail -50
```

#### E-4: Digital Thread Integration

| 文件 | 测试内容 |
|------|---------|
| `tests/backend/integration/test_treatment_plan_digital_thread.py` | 完整链路追溯 |

执行命令：
```bash
cd /workspace && python -m pytest tests/backend/integration/test_treatment_plan_digital_thread.py -v --timeout=120 2>&1 | tail -30
```

#### E-5: Restart Recovery

| 文件 | 测试内容 |
|------|---------|
| `tests/backend/integration/test_treatment_plan_restart.py` | 重启恢复后版本正确 |

执行命令：
```bash
cd /workspace && python -m pytest tests/backend/integration/test_treatment_plan_restart.py -v --timeout=120 2>&1 | tail -30
```

#### E-6: 综合回归

```bash
cd /workspace && python -m pytest tests/ -v --timeout=300 -x 2>&1 | tail -100
```

#### E-7: GitHub Actions 验证

确保 `.github/workflows/` 中的所有 CI 流水线通过。

---

## 4. 返工预案

如果 REVIEWER 评分 < 90，按以下策略修复：

| 失分原因 | 修复策略 |
|----------|---------|
| Migration 025 不兼容 SQLite | 使用 `batch_alter_table` + `recreate_table` 模式，参考 Alembic 官方 SQLite 迁移指南 |
| 数据迁移丢失 | 在 025 upgrade() 中添加数据完整性检查（COUNT 验证），downgrade() 也要有数据保护 |
| `get_current_by_plan_id()` 性能差 | 添加复合索引 `(plan_id, is_current, version)` |
| Phase Mapping 逻辑导致已有测试失败 | 检查所有 mock/fixture 的 engine_output 是否包含 `phase_type`；更新 fixture 数据 |
| Version Link FK 循环引用 | 使用 `remote_side` 和 `foreign_keys` 正确配置 self-referential relationship |
| 测试覆盖不足 | 补充边缘案例：空版本列表、无当前版本、并发 revise、降级路径 |

### 常见失败模式

1. **Migration 冲突**：如果 024 的 down_revision 指向 023 但 023 被恢复，确保 revision chain 不断裂
2. **SQLite 不支持 DROP CONSTRAINT**：必须使用 batch 模式重建表
3. **Self-referential FK**：SQLite 和 PostgreSQL 对 self-referential FK 的支持不同，测试需覆盖
4. **Mock 未更新**：所有 mock `EngineOutput.items` 需要添加 `phase_type` 字段

---

## 5. 验收标准

| # | 标准 | 验证方式 |
|---|------|---------|
| 1 | 023 恢复为发布版本，无硬化修改 | `git diff HEAD~1 -- migrations/versions/023_phase3e_treatment_plan_tables.py` 验证无差异 |
| 2 | 025 新增复合唯一约束 | 升级后 DB 有 `uq_plan_id_version` 和 `uq_trace_step` |
| 3 | 旧 DB(023/024) → upgrade 025 成功 | Migration Test PASS |
| 4 | plan v1 + v2 可共存 | Repository Test: plan_id 相同但 version 不同的两条记录可同时插入 |
| 5 | trace step1 + step2 + step3 可共存 | Repository Test: trace_id 相同但 step_order 不同的多条记录可同时插入 |
| 6 | `get_by_plan_id()` 不再使用 scalar_one_or_none() | 代码审查确认 |
| 7 | GET/Approve/Activate/Pause/Complete/Cancel 使用 Current Version | Service Test PASS |
| 8 | v1→revise→v2→GET v2→revise→v3→GET v3→Versions list | Version Test PASS |
| 9 | previous_version_id 指向 TreatmentPlanModel.id | Self-reference FK 正确 |
| 10 | supersedes_version_id 指向 TreatmentPlanModel.id | Self-reference FK 正确 |
| 11 | v1→v2→v3 version chain 完整 | Model Test: chain 验证 |
| 12 | Engine 输出的 item 包含 phase_type | Engine Test PASS |
| 13 | phase_type 不匹配时返回 Validation Error (422) | Service/API Test PASS |
| 14 | 无 fallback 到第一个 phase | 代码审查 + Test PASS |
| 15 | Python Tests PASS | `pytest tests/` |
| 16 | Migration Tests PASS | `pytest tests/test_migration.py` |
| 17 | Digital Thread PASS | `pytest tests/backend/integration/test_treatment_plan_digital_thread.py` |
| 18 | Restart Recovery PASS | `pytest tests/backend/integration/test_treatment_plan_restart.py` |
| 19 | GitHub Actions 全绿 | CI 状态检查 |
| 20 | 无新增功能/需求/Phase 3F | 代码审查确认 scope 未膨胀 |

---

## 6. 返工 R1 — Step 6 回歸檢查修復（Migration 025 專門測試類）

### 背景

Step 6 回歸檢查發現 2 項 PARTIAL 缺失：

| 項目 | 缺失內容 |
|------|---------|
| 項目 6 | 缺少「Old DB → upgrade 025 → plan v1+v2 成功」的專門 Migration Test |
| 項目 7 | 缺少「Old DB → upgrade 025 → trace step1+2+3 成功」的專門 Migration Test |

当前所有 P0 開發已完成（1,657 tests PASS，lint 通過），僅需在 `tests/test_migration.py` 中補上 `TestMigration025Upgrade` 測試類。

### R1-1: 新增 TestMigration025Upgrade 測試類

| 屬性 | 值 |
|------|-----|
| 新建測試類 | `tests/test_migration.py` → `TestMigration025Upgrade` |
| 位置 | 在 `TestMigration023` 類結尾之後（第 1329 行後）追加 |
| 責任人 | BUILDER |

測試類架構（參考 `TestMigration020` 的 helper 模式）：

```python
# ═══════════════════════════════════════════════════════════════════════════════
# Phase 3E — R1: Migration 025 → Composite Unique & Version Link
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def alembic_config_025(tmp_path):
    """Isolated Alembic config for 024→025 migration tests."""
    db_path = tmp_path / "test_migration_025.db"
    cfg = Config()
    cfg.set_main_option("script_location", "migrations")
    cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_path}")
    return cfg, db_path


class TestMigration025Upgrade:
    """Tests for Phase 3E migration 025 (composite unique + version link)."""

    @staticmethod
    def _table_exists(db_path, table_name):
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
    def _get_unique_constraints(db_path, table_name):
        import sqlite3, re
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
        for match in re.finditer(
            r"CONSTRAINT\s+(\w+)\s+UNIQUE\s*\(([^)]+)\)",
            create_sql, re.IGNORECASE,
        ):
            name = match.group(1)
            columns = [c.strip().strip('"') for c in match.group(2).split(",")]
            constraints[name] = columns
        return constraints

    @staticmethod
    def _get_indexes(db_path, table_name):
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
                if row[1] == idx_name:
                    unique = bool(row[2])
                    break
            result[idx_name] = {"unique": unique, "columns": columns}
        conn.close()
        return result
```

### R1-2: 測試方法 1 — `test_upgrade_025_creates_composite_unique`

**目的**：驗證 025 升級後複合唯一約束存在

```python
    def test_upgrade_025_creates_composite_unique(self, alembic_config_025):
        """Verify 025 upgrade creates composite unique constraints."""
        cfg, db_path = alembic_config_025

        # Step 1: upgrade to 024 (023 + 024)
        command.upgrade(cfg, "024")
        assert self._table_exists(db_path, "domain_treatment_plans")
        assert self._table_exists(db_path, "domain_treatment_plan_traces")

        # Step 2: upgrade to 025
        command.upgrade(cfg, "025")

        # Verify domain_treatment_plans has uq_plan_id_version
        plans_unique = self._get_unique_constraints(db_path, "domain_treatment_plans")
        found_plan = False
        for name, columns in plans_unique.items():
            if set(columns) == {"plan_id", "version"}:
                found_plan = True
                break
        assert found_plan, (
            "Missing composite unique constraint (plan_id, version) "
            "on domain_treatment_plans after 025 upgrade"
        )

        # Verify domain_treatment_plan_traces has uq_trace_step
        traces_unique = self._get_unique_constraints(db_path, "domain_treatment_plan_traces")
        found_trace = False
        for name, columns in traces_unique.items():
            if set(columns) == {"trace_id", "step_order"}:
                found_trace = True
                break
        assert found_trace, (
            "Missing composite unique constraint (trace_id, step_order) "
            "on domain_treatment_plan_traces after 025 upgrade"
        )
```

### R1-3: 測試方法 2 — `test_upgrade_025_preserves_data`

**目的**：驗證 023→024→025 升級路徑數據保留

```python
    def test_upgrade_025_preserves_data(self, alembic_config_025):
        """Verify data survives upgrade from 023 through 024 to 025."""
        import sqlite3
        cfg, db_path = alembic_config_025

        # Step 1: upgrade to 023, insert sample data
        command.upgrade(cfg, "023")
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "INSERT INTO domain_treatment_plans "
            "(id, plan_id, patient_id, version, is_current, status) "
            "VALUES ('p1', 'plan-a', 'pat-1', 1, 1, 'active')"
        )
        conn.execute(
            "INSERT INTO domain_treatment_plan_traces "
            "(id, trace_id, plan_id, step_order, step_type, output_summary) "
            "VALUES ('t1', 'trace-a', 'plan-a', 1, 'decision', 'step1')"
        )
        conn.commit()
        conn.close()

        # Step 2: upgrade to 024
        command.upgrade(cfg, "024")

        # Step 3: upgrade to 025
        command.upgrade(cfg, "025")

        # Verify data preserved
        conn = sqlite3.connect(str(db_path))
        row = conn.execute(
            "SELECT plan_id, patient_id, version, status FROM domain_treatment_plans WHERE id='p1'"
        ).fetchone()
        assert row is not None, "Plan 'p1' missing after 025 upgrade"
        assert row[0] == "plan-a"
        assert row[1] == "pat-1"
        assert row[2] == 1

        row = conn.execute(
            "SELECT trace_id, step_order, output_summary FROM domain_treatment_plan_traces WHERE id='t1'"
        ).fetchone()
        assert row is not None, "Trace 't1' missing after 025 upgrade"
        assert row[0] == "trace-a"
        assert row[1] == 1
        conn.close()
```

### R1-4: 測試方法 3 — `test_upgrade_025_plan_v1_v2_success`

**目的**：驗證 Old DB(023/024) → upgrade 025 → plan v1+v2 可共存（項目 6）

```python
    def test_upgrade_025_plan_v1_v2_success(self, alembic_config_025):
        """Old DB(023/024) → upgrade 025 → plan v1 and v2 can coexist."""
        import sqlite3, uuid
        cfg, db_path = alembic_config_025

        # Step 1: upgrade to 024 (simulating old DB at 023/024)
        command.upgrade(cfg, "024")

        # Step 2: upgrade to 025 (adds composite unique)
        command.upgrade(cfg, "025")

        # Step 3: insert plan v1 and v2 with same plan_id, different version
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "INSERT INTO domain_treatment_plans "
            "(id, plan_id, patient_id, version, is_current, status) "
            "VALUES (?, 'plan-v', 'pat-v', 1, 1, 'active')",
            (str(uuid.uuid4()),),
        )
        conn.execute(
            "INSERT INTO domain_treatment_plans "
            "(id, plan_id, patient_id, version, is_current, status) "
            "VALUES (?, 'plan-v', 'pat-v', 2, 0, 'superseded')",
            (str(uuid.uuid4()),),
        )
        conn.commit()

        # Verify both versions exist
        rows = conn.execute(
            "SELECT plan_id, version FROM domain_treatment_plans WHERE plan_id='plan-v' ORDER BY version"
        ).fetchall()
        conn.close()
        assert len(rows) == 2, f"Expected 2 versions, got {len(rows)}"
        assert rows[0] == ("plan-v", 1)
        assert rows[1] == ("plan-v", 2)
```

### R1-5: 測試方法 4 — `test_upgrade_025_trace_step1_step2_step3_success`

**目的**：驗證 Old DB → upgrade 025 → trace step1+2+3 可共存（項目 7）

```python
    def test_upgrade_025_trace_step1_step2_step3_success(self, alembic_config_025):
        """Old DB → upgrade 025 → trace step1/2/3 can coexist."""
        import sqlite3, uuid
        cfg, db_path = alembic_config_025

        # Step 1: upgrade to 024 (old DB state)
        command.upgrade(cfg, "024")

        # Step 2: upgrade to 025
        command.upgrade(cfg, "025")

        # Step 3: insert trace with step_order 1, 2, 3 (same trace_id)
        conn = sqlite3.connect(str(db_path))
        # First need a plan for FK
        plan_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO domain_treatment_plans "
            "(id, plan_id, patient_id, version, is_current, status) "
            "VALUES (?, 'trace-plan', 'pat-t', 1, 1, 'active')",
            (plan_id,),
        )
        trace_id = "trace-multi-step"
        for step in range(1, 4):
            conn.execute(
                "INSERT INTO domain_treatment_plan_traces "
                "(id, trace_id, plan_id, step_order, step_type, output_summary) "
                "VALUES (?, ?, 'trace-plan', ?, 'reasoning', ?)",
                (str(uuid.uuid4()), trace_id, step, f"step{step}_output"),
            )
        conn.commit()

        # Verify all 3 steps exist
        rows = conn.execute(
            "SELECT trace_id, step_order, output_summary "
            "FROM domain_treatment_plan_traces "
            "WHERE trace_id=? ORDER BY step_order",
            (trace_id,),
        ).fetchall()
        conn.close()
        assert len(rows) == 3, f"Expected 3 steps, got {len(rows)}"
        assert rows[0] == (trace_id, 1, "step1_output")
        assert rows[1] == (trace_id, 2, "step2_output")
        assert rows[2] == (trace_id, 3, "step3_output")
```

### R1-6: 測試方法 5 — `test_downgrade_025_restores_single_unique`

**目的**：驗證降級 025 後恢復單列唯一約束

```python
    def test_downgrade_025_restores_single_unique(self, alembic_config_025):
        """After downgrade from 025 to 024, plan_id and trace_id have single-column unique."""
        import sqlite3
        cfg, db_path = alembic_config_025

        # Step 1: upgrade all the way to 025
        command.upgrade(cfg, "025")

        # Step 2: downgrade to 024
        command.downgrade(cfg, "024")

        # Verify plan_id has unique constraint (single column)
        # In SQLite after batch downgrade, unique is expressed as a unique index
        indexes = self._get_indexes(db_path, "domain_treatment_plans")
        plan_unique_found = False
        for name, info in indexes.items():
            if info["unique"] and info["columns"] == ["plan_id"]:
                plan_unique_found = True
                break
        assert plan_unique_found, (
            "plan_id should have a single-column unique index after 025 downgrade"
        )

        # Verify trace_id has unique constraint (single column)
        indexes = self._get_indexes(db_path, "domain_treatment_plan_traces")
        trace_unique_found = False
        for name, info in indexes.items():
            if info["unique"] and info["columns"] == ["trace_id"]:
                trace_unique_found = True
                break
        assert trace_unique_found, (
            "trace_id should have a single-column unique index after 025 downgrade"
        )
```

### 验收标准

| # | 标准 | 验证方式 |
|---|------|---------|
| 1 | `test_upgrade_025_creates_composite_unique` PASS | `pytest tests/test_migration.py::TestMigration025Upgrade::test_upgrade_025_creates_composite_unique -v` |
| 2 | `test_upgrade_025_preserves_data` PASS | 同上 |
| 3 | `test_upgrade_025_plan_v1_v2_success` PASS | 同上 |
| 4 | `test_upgrade_025_trace_step1_step2_step3_success` PASS | 同上 |
| 5 | `test_downgrade_025_restores_single_unique` PASS | 同上 |
| 6 | 全部 Migration Tests PASS | `python -m pytest tests/test_migration.py -v --timeout=120` |
| 7 | 全量回归 1,657+ tests PASS | `python -m pytest tests/ -v --timeout=300` |

---

## 附录：文件修改清单总表

| 文件 | 批次 | 操作 | 说明 |
|------|------|------|------|
| `migrations/versions/023_phase3e_treatment_plan_tables.py` | A-1 | 修改（恢复） | 回滚到发布版本 |
| `migrations/versions/025_phase3e_version_composite_unique.py` | A-2, C-1 | 新建 | 复合唯一约束 + Version Link 列 |
| `src/backend/domain/treatment_plan.py` | A-3, C-2 | 修改 | 复合唯一 + Version Link 字段 |
| `src/backend/repositories/treatment_plan_repo.py` | B-1, C-3 | 修改 | 拆分为三个方法 + Version Link 写入 |
| `src/backend/services/treatment_plan_service.py` | B-2, C-4, D-2 | 修改 | Current Version + Version Link + Phase Mapping |
| `src/backend/clinical/treatment_plan_engine.py` | D-1, D-3 | 修改 | Item 输出 phase_type |
| `src/backend/api/v1/treatment_plans.py` | B-3 | 可选修改 | 版本查询 |
| `tests/test_migration.py` | A-4 | 修改 | 新增 025 迁移测试 |
| `tests/backend/models/test_treatment_plan_models.py` | C-5 | 修改 | Version Link 测试 |
| `tests/backend/repositories/test_treatment_plan_repos.py` | B-5 | 修改 | 新 repository 方法测试 |
| `tests/backend/services/test_treatment_plan_service.py` | B-4, D-5 | 修改 | Current Version + Phase Mapping |
| `tests/backend/clinical/test_treatment_plan_engine.py` | D-4 | 修改 | phase_type 输出测试 |
| `tests/backend/api/test_treatment_plan_api.py` | D-6 | 修改 | Phase Mapping API 测试 |
| `tests/backend/integration/test_treatment_plan_digital_thread.py` | E-4 | 可能修改 | 适配 Version Link |
