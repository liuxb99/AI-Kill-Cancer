# 分层架构审查报告

> **审查范围**：Domain 层、Repository 层、Service 层、Engine 层  
> **审查时间**：2025-01  
> **项目版本**：v1.0.1  

---

## 目录

1. [Domain 层审查](#1-domain-层审查)
2. [Repository 层审查](#2-repository-层审查)
3. [Service 层审查](#3-service-层审查)
4. [Engine 层审查](#4-engine-层审查)
5. [全局性问题总结](#5-全局性问题总结)

---

## 1. Domain 层审查

### 1.1 Entity 标识完整性
**分數：9/10**

所有 `*Model` 类（ORM 模型）均使用 `CompatUUID` 类型的主键 `id` 字段，共 37 个 Model 类全部符合要求。

**良好实践：**
- 所有 Model 使用 UUID 主键，全局唯一标识
- 使用 `CompatUUID` 兼容不同类型数据库

### 1.2 ValueObject 不可变性
**分數：7/10**

**发现的问题：**
- Domain 层不包含独立的 `@dataclass(frozen=True)` ValueObject 类。所有 Pydantic schema（`*Create`、`*Response`、`*Update`）虽然通过 `BaseModel` 实现了不可变性，但它们是作为**数据传输对象**而非领域值对象设计的。
- 没有明确的 ValueObject 模式：`EvidenceSearchResult`（evidence.py:108）、`GraphNode`（visualization_graph.py:74）等虽为 Pydantic 模型，但缺乏明确的值对象边界定义。
- `CancerCaseModel` 中的 `radioiodine_status` 和 `recurrence_status`（cancer_case.py:34-35）类型为 `String(64)`，未使用 enum 约束，可能导致非法状态值。

**良好实践：**
- Pydantic `BaseModel` 的子类默认 `frozen=False` 但通过 `ConfigDict` 可控制，部分类配置为不可变。

**建议：**
- 定义显式的 `@dataclass(frozen=True)` 值对象，如 `class GeneIdentifier:`、`class VariantCoordinate:`
- 将 `radioiodine_status` 和 `recurrence_status` 改为 enum 约束

### 1.3 Aggregate 边界
**分數：6/10**

**发现的问题：**
1. Aggregate 边界不清晰。所有 Model 都在同一个 `domain/` 包中扁平存放，没有使用嵌套包或显式的 Aggregate 根标记。
2. 存在跨 Aggregate 的直接外键引用（如 `TreatmentPlanModel` 同时引用 `PatientModel`、`RecommendationModel`、`ClinicalDecisionModel`、`TumorBoardConsensusModel`），这可能导致 Aggregate 边界被突破。
3. 没有明确的 Aggregate Root 标记模式（如专门的基类或装饰器）。

**良好实践：**
- `TreatmentPlanModel` 使用 `plan_id + version` 复合唯一约束（treatment_plan.py:28-29），体现了版本化的 Aggregate 设计思路。

**建议：**
- 使用 `typing.Annotated` 或自定义基类标记 Aggregate Root
- 考虑将强关联的 Model 分组到子包（如 `domain.patient.*`、`domain.clinical.*`）

### 1.4 State 转换
**分數：6/10**

**发现的问题：**
1. 状态定义分散：`plan_status`（treatment_plan.py:58）使用 `String(32)` 而非 enum，运行时无类型安全。
2. `ClinicalDecisionModel.status`（clinical_decision.py:37）使用 `String(32)`，默认 `"active"`，但 `DecisionStatusEnum` 已定义为 `ACTIVE / SUPERSEDED / WITHDRAWN / ARCHIVED`——ORM 模型未复用该 enum。
3. `RecommendationModel.status`（recommendation.py:33）使用 `String(32)`，默认 `"pending"`；同样未复用 `RecommendationStatusEnum`。
4. 大多数 `status` 字段使用 `String(32)` 而非 `SAEnum`，损失了数据库层的类型约束。

**良好实践：**
- `AnalysisRunModel.status`（analysis_run.py:30）正确使用 `SAEnum(AnalysisStatusEnum)`
- `PatientModel.consent_status`（patient.py:40）正确使用 `SAEnum(ConsentStatusEnum)`
- `UploadedFileModel.upload_status`（uploaded_file.py:49-50）正确使用 `SAEnum`
- `VariantModel`（variant.py:54,58）正确使用 `SAEnum`
- `TreatmentPlanStateMachine`（clinical/treatment_plan_state_machine.py）提供了完善的状态机定义和转换规则

**建议：**
- 统一使用 `SAEnum` 替代 `String(32)` 存储状态
- 确保 ORM 模型中的状态字段与枚举定义一致

### 1.5 Version 控制（乐观锁）
**分數：4/10**

**发现的问题：**
1. **缺乏乐观锁机制**：没有一个 Model 实现 `__version__` 或 `version_id` 字段用于乐观锁并发控制。
2. `TreatmentPlanModel.version`（treatment_plan.py:33）是业务版本号（用于版本化治疗计划），并非乐观锁版本。
3. 没有 `ROWVERSION` / `_version` / `version_id` 字段用于检测并发写入冲突。

**建议：**
- 为所有 Aggregate Root Model 添加 `version_id = Column(Integer, default=1)` 乐观锁字段
- 在 Repository 层的 `update` 方法中增加 `WHERE version_id = :expected_version` 条件

### 1.6 Domain 纯净性 —— 严重问题
**分數：2/10**

**这是 Domain 层最严重的问题。**

**发现的问题：**

**所有 26 个 Domain 文件均违反纯净性原则**，具体如下：

| 文件 | 违规行 | 问题描述 |
|------|--------|----------|
| 全部 21 个 `*Model` 文件 | 各文件 `from sqlalchemy import ...` | **导入 SQLAlchemy ORM 列类型**，将 ORM 依赖引入 Domain 层 |
| 全部 21 个 `*Model` 文件 | 各文件 `from src.backend.database.models import Base as DBBase` | **导入数据库基础设施模块**，Domain 层直接依赖 `database.models` |
| 全部 21 个 `*Model` 文件 | 各文件 `from src.backend.database.models import CompatUUID` | 同上 |
| 全部 21 个 `*Model` 文件 | `class *Model(DBBase)` | **ORM 模型继承自数据库基类**，Domain 类耦合了 ORM 生命周期 |
| 全部 21 个 `*Model` 文件 | `id = Column(CompatUUID, primary_key=True)` | **使用 ORM 的 Column 定义字段**，而非纯 Python 类型 |
| `user.py` | `LoginRequest`, `LogoutRequest`, `RefreshRequest`, `TokenResponse` | **API 认证相关 DTO** 放在 Domain 层，属于表现层关注点 |
| `visualization_graph.py` | 全部 | **API 响应模型**（`GraphAnalysisResponse`）放在 Domain 层 |

**典型违规模式示例（analysis_run.py）**：
```python
# line 11 — ORM 导入
from sqlalchemy import JSON, BigInteger, Column, DateTime, ForeignKey, String
# line 15-16 — 数据库基础设施导入
from src.backend.database.models import Base as DBBase
from src.backend.database.models import CompatUUID
# line 24 — 继承 ORM 基类
class AnalysisRunModel(DBBase):
    ...
    id = Column(CompatUUID, primary_key=True, default=_uuid)
```

**根本原因分析：**
项目采用了"胖 Domain 文件"策略——每个 `domain/*.py` 文件同时包含：
1. SQLAlchemy ORM 模型（继承 `DBBase`）
2. Pydantic 请求/响应 Schema（继承 `BaseModel`）

这在严格 DDD 实践中是不推荐的。Domain 层应该只包含纯 Python 领域对象，ORM 映射应放在 Infrastructure 层（如 `database/models.py`），API Schema 应放在独立的 `schemas/` 层。

**建议：**
- **分离 ORM 模型和领域模型**：将 `*Model` 类移到 `src/backend/database/models.py` 或 `src/backend/infrastructure/orm/` 中
- **创建纯领域模型**：在 `domain/` 中保留纯 Python 类（`@dataclass`），不含任何 ORM 依赖
- **移动 API Schema**：将 `LoginRequest`、`TokenResponse`、`GraphAnalysisResponse` 等移到 `src/backend/api/schemas/`
- **使用 Repository 做映射**：Repository 负责在 ORM 模型和领域模型之间转换

---

## 2. Repository 层审查

### 2.1 事务控制
**分數：4/10**

**发现的问题：**

**BaseRepository 默认提交事务**（`base.py`）：
| 文件 | 行号 | 调用 |
|------|------|------|
| `base.py` | 29 | `await self.db.commit()`（create） |
| `base.py` | 73 | `await self.db.commit()`（update） |
| `base.py` | 82 | `await self.db.commit()`（delete） |

这导致**任何继承 BaseRepository 且未覆盖这些方法的子类都会主动提交事务**，将事务边界从 Service 层拉到了 Repository 层。

**实际调用 commit() 的子类**：
| 文件 | 行号 | 说明 |
|------|------|------|
| `case_acl_repo.py` | 35,45,55 | `delete_case_permission` 和 `grant_permission` 中直接 commit |
| `drug_interaction_repo.py` | 53,73 | `upsert` 方法中 commit |
| `evidence_item_repo.py` | 80,100,134,195 | `upsert` 和 `withdraw_by_source_record` 中 commit |
| `knowledge_source_repo.py` | 34,40,66 | `upsert` 和 `record_health_check` 中 commit |
| `variant_repo.py` | 26 | `bulk_create` 中 commit |

**使用 flush() 而非 commit() 的较新 Repository**：
| 文件 | 行号 | 说明 |
|------|------|------|
| `treatment_plan_repo.py` | 73,290,314,323,354,379,388,419,444,453,484,509,518,549,574,583,614 | 全部使用 flush() |
| `tumor_board_repo.py` | 66,256,345 | 全部使用 flush() |
| `clinical_graph_outbox_repo.py` | 32 | 使用 flush() |
| `clinical_decision_repo.py` | 覆盖 create() 仅 add+flush | 文档声明"由 Service 层管理事务边界" |
| `recommendation_repo.py` | 覆盖 create() 仅 add+flush | 同上 |

**结论**：事务策略不一致。较新的 Repository（`clinical_decision`、`recommendation`、`treatment_plan`、`tumor_board`）正确地将提交权交给 Service 层，但较老的 Repository 和 BaseRepository 默认行为违反了"Repository 不应管理事务"的原则。

**建议：**
- `BaseRepository.create()`、`update()`、`delete()` 改为使用 `flush()` 而非 `commit()`
- 审计所有调用了 `commit()` 的子类，将事务提交责任上移到 Service 层
- 考虑引入 `@transactional` 装饰器统一管理事务边界

### 2.2 业务逻辑混入
**分數：5/10**

**严重违规：`clinical_graph_outbox_repo.py`**

该文件自行实现（未继承 BaseRepository），混入了大量业务逻辑：

| 行号 | 违规内容 |
|------|----------|
| 50-51 | `status.in_(["pending", "failed"])` — 业务状态判断 |
| 60-63 | 设置 `status = "processing"`、`claim_token`、`processing_started_at` — 业务状态转换 |
| 61 | `row.status = "processing"` — 领域状态变更 |
| 76-99 | `mark_failed` 中调用 `DEFAULT_RETRY_POLICY.is_dead_letter()`（行83）判断是否转死信 |
| 82-86 | 根据尝试次数决策 `new_status` 为 `dead_letter` 还是 `failed` |
| 115-135 | `release_stale` 中计算 `deadline = now - timedelta(minutes=timeout_minutes)` 并遍历修改状态 |
| 150-165 | `get_status_counts` 执行聚合分组 |

**依赖违规**：
| 文件 | 行号 | 违规内容 |
|------|------|----------|
| `clinical_graph_outbox_repo.py` | 11 | `from src.backend.clinical_graph.retry_policy import DEFAULT_RETRY_POLICY` — **依赖非 Domain 模块** |

**建议：**
- 将 `ClinicalGraphOutboxRepository` 拆分为两个部分：
  - 基础 CRUD Repository（仅 `create`、`find_by_status`、`update_status` 等方法）
  - Outbox Processor Service（处理重试策略、死信判断、状态机逻辑）

### 2.3 CRUD 职责
**分數：7/10**

**命名/职责偏离的方法**：

| 文件 | 方法 | 问题 |
|------|------|------|
| `clinical_graph_outbox_repo.py` | `claim_pending`, `mark_completed`, `mark_failed`, `mark_dead_letter`, `release_stale`, `get_status_counts` | 语义是服务层操作 |
| `evidence_item_repo.py` | `withdraw_by_source_record` | 批量更新操作，非标准 CRUD |
| `knowledge_source_repo.py` | `record_health_check` | 专有业务操作 |
| `case_acl_repo.py` | `grant_permission` | 语义是授权操作 |

**良好实践：**
- `BaseRepository` 提供标准的 `create/get/list/count/update/delete` 方法
- 多数子类方法命名符合 `find_by_*`、`list_by_*`、`get_by_*`、`count_by_*` 模式

### 2.4 类型注解完整性
**分數：5/10**

| 文件组 | 状态 | 说明 |
|--------|------|------|
| `clinical_decision_repo.py`, `recommendation_repo.py`, `treatment_plan_repo.py`, `tumor_board_repo.py`, `clinical_graph_outbox_repo.py` | ✅ 完整 | 参数和返回类型均有注解 |
| 其余 17 个 Repository 文件 | ❌ 不完整 | `__init__(self, db)` 缺少 `db: AsyncSession` 类型注解；多个方法缺返回类型 |

---

## 3. Service 层审查

### 3.1 Transaction Boundary
**分數：8/10**

**良好实践：**
- 所有 Service 正确控制事务边界，统一的 `try/commit/rollback` 模式：
  - `clinical_decision_service.py:394-396`
  - `recommendation_service.py:317-319`
  - `treatment_plan_service.py:364-369`
  - `tumor_board_service.py:435-437`
- 所有 Service 文档明确声明"Transaction management is handled by this service"
- `ClinicalGraphEventService` 明确定义"不管理事务边界"

**发现的问题：**
| 问题 | 文件:行号 | 说明 |
|------|-----------|------|
| 🟡 BaseRepository 默认 commit() | `base.py:29,73,82` | 任何忘记重写 `create()` 的子类会导致事务提前提交 |
| 🟡 手动 try/commit 模式重复 | 4个 Service 文件 | 每个写方法都要手写 try/commit/rollback，缺少统一的 `@transactional` 装饰器 |

**建议：**
- 引入 `@transactional` 装饰器或上下文管理器减少重复代码
- 参考 Spring 的 `@Transactional` 模式

### 3.2 Engine/Repository 事务问题
**分數：9/10**

**良好实践：**
- 所有 Repository 子类（在 Service 控制下）仅 `add` + `flush()`，不 `commit()`
- 所有 Engine 不涉及数据库操作
- `ClinicalGraphEventService` 不自开事务

### 3.3 协调职责
**分數：10/10**

所有 Service 均正确承担了编排职责：

| Service | 协调的组件数 | 协调的组件 |
|---------|-------------|-----------|
| `ClinicalDecisionService` | 4+ | ClinicalDecisionEngine + 2 Repositories + ClinicalGraphEventService |
| `RecommendationService` | 7+ | EvidenceCollector + DrugRankingEngine + ExplainableEngine + RecommendationEngine + 2 Repositories + ClinicalGraphEventService |
| `TreatmentPlanService` | 8+ | TreatmentPlanEngine + TreatmentPlanStateMachine + 6 Repositories + ClinicalGraphOutboxRepository |
| `TumorBoardService` | 6+ | ConsensusEngine + 3 Repositories + ClinicalGraphEventService |

### 3.4 业务逻辑
**分數：8/10**

Service 层包含业务逻辑是合理的。所有 Service 均包含验证、条件判断、循环和数据转换。

**发现的问题：**
- `recommendation_service.py:128-131` — `_parse_variant()` 手动解析 "EGFR L858R" 格式的变体字符串，这个解析逻辑应该放在 Domain 层作为 ValueObject 的方法
- `recommendation_service.py:248` — `from src.backend.api.v1.recommendation import RecommendationResponse`（**架构违规**）

### 3.5 依赖 —— 架构违规
**分數：4/10**

**严重问题：Service 层反向依赖 API 层**

| 文件 | 行号 | 违规内容 |
|------|------|----------|
| `recommendation_service.py` | 248 | `from src.backend.api.v1.recommendation import RecommendationResponse` |

这是**架构方向错误**：`api/v1/` → `services/` → `repositories/` → `domain/` 是预期依赖方向。Service 层反向依赖 API 层会：
1. 导致循环依赖风险
2. 使 Service 层与 API 协议耦合
3. 降低 Service 层的可测试性和可复用性

**建议：**
- 将 `RecommendationResponse` 提取到共享的 `schemas/` 包中
- 或直接在 Service 层定义返回类型，由 API 层做转换

---

## 4. Engine 层审查

### 4.1 Pure Function 性质
**分數：6/10**

| Engine | 分數 | 说明 |
|--------|------|------|
| `ClinicalDecisionEngine` | 7/10 | 弱纯函数（仅 logging），调用私有 API |
| `RecommendationEngine` | **3/10** | **严重违反**：通过注入的 Collector 产生 I/O，通过 TraceManager 产生状态变更 |
| `TreatmentPlanEngine` | 9/10 | 接近纯函数，所有状态局部化 |
| `TumorBoardEngine` | 9/10 | 非常接近纯函数，仅 uuid.uuid4() 非确定性 |

**发现的问题：**

**🔴 `RecommendationEngine.run()` 严重违反 Pure Function 原则**（`recommendation_engine.py`）：

| 行号 | 问题 |
|------|------|
| 511 | `await self._collector.collect(patient_context)` — 通过注入的 EvidenceCollector 产生 I/O 副作用（可能包含 DB 查询和 API 调用） |
| 482-486 | `self._trace_manager.start_trace(...)` — 修改 TraceManager 内部状态 |
| 500-527, 537-580, 591-623, 640-674, 696-710 | 多处 `self._trace_manager.add_step(...)` — 持续修改 TraceManager 状态 |
| 715 | `self._trace_manager.complete_trace(...)` — 修改 TraceManager 状态 |
| 650 | `rule.evaluate(context)` — Rule action 可能修改 `context` 字典 |
| 504, 528, 582, 625, 714 | 多处 `except Exception` 仅记录日志后静默继续，可能隐藏 pipeline 错误 |
| 489-496 | `context` 字典持有 `patient_context` 外部引用，存在被 rule action 意外修改的风险 |

**ClinicalDecisionEngine 调用私有 API**（`clinical_decision_engine.py:209`）：
- `self._rule_set._get_top_drug_name()` — 调用私有方法，紧耦合

### 4.2 外部依赖
**分數：7/10**

| Engine | DB/HTTP/Web 依赖 | 说明 |
|--------|-----------------|------|
| `ClinicalDecisionEngine` | ✅ 无 | 仅依赖 `DecisionRuleSet` |
| `RecommendationEngine` | ⚠️ 间接依赖 | 注入的 `self._collector` 可能为 `EvidenceCollector`（含 DB/API 调用） |
| `TreatmentPlanEngine` | ✅ 无 | 仅依赖 `TreatmentPlanRuleSet` 和 `TreatmentPlanTraceBuilder` |
| `TumorBoardEngine` | ✅ 无 | 仅依赖 `ConsensusRuleSet` 和 `ConsensusStatus` |

### 4.3 Domain 依赖
**分數：8/10**

| Engine | 是否仅依赖 Domain | 说明 |
|--------|------------------|------|
| `ClinicalDecisionEngine` | ✅ 是 | 仅依赖 `DecisionRuleSet`（domain rules） |
| `RecommendationEngine` | ⚠️ 否 | 依赖 `TraceManager`（来自 `calculation_trace`，使用了 `pydantic.BaseModel`，属于基础设施层） |
| `TreatmentPlanEngine` | ✅ 是 | 仅依赖 `TreatmentPlanRuleSet` 和 `TreatmentPlanTraceBuilder`（纯数据） |
| `TumorBoardEngine` | ✅ 是 | 仅依赖 `ConsensusRuleSet` 和 `ConsensusStatus`（domain enum） |

### 4.4 代码质量
**分數：8/10**

所有 Engine 文件均有：
- ✅ 完整的类型注解
- ✅ 充分的文档字符串
- ✅ 清晰的输入输出类型

**发现的问题：**
- `recommendation_engine.py:177-178` — Docstring 与参数类型不一致
- `treatment_plan_engine.py` — 静态方法与实例方法使用不一致
- `tumor_board_engine.py` — 未 import `logging`，缺失证据缺失时的调试记录

---

## 5. 全局性问题总结

### 优先级矩阵

| 优先级 | 问题 | 影响层 | 影响范围 |
|--------|------|--------|----------|
| **🔴 P0** | Domain 层混入 SQLAlchemy ORM 依赖 | Domain | 全部 26 个文件 |
| **🔴 P0** | Service 层反向依赖 API 层 | Service | `recommendation_service.py:248` |
| **🔴 P0** | BaseRepository 默认 commit() 导致事务边界下移 | Repository | `base.py:29,73,82` 影响所有子类 |
| **🔴 P0** | `clinical_graph_outbox_repo.py` 混入大量业务逻辑 | Repository | `clinical_graph_outbox_repo.py` 全文件 |
| **🟡 P1** | `RecommendationEngine.run()` 严重违反 Pure Function | Engine | `recommendation_engine.py:482-715` |
| **🟡 P1** | ORM 状态字段使用 String 而非 SAEnum | Domain | 多个 Model 文件 |
| **🟡 P1** | 缺少乐观锁版本控制 | Domain | 全部 Model |
| **🟡 P1** | Repository 类型注解不完整 | Repository | 17/22 个文件 |
| **🟢 P2** | Aggregate 边界不清晰 | Domain | 全局 |
| **🟢 P2** | 缺少显式 ValueObject 模式 | Domain | 全局 |
| **🟢 P2** | Engine 调用私有 API | Engine | `clinical_decision_engine.py:209` |
| **🟢 P2** | 手动 try/commit 重复模式 | Service | 全部 4 个 Service |

### 总体评分

| 层 | 分數 | 关键短板 |
|----|------|---------|
| **Domain** | **4/10** | ORM 依赖混入（P0），缺乏纯净性 |
| **Repository** | **5/10** | 事务策略不一致，业务逻辑混入 |
| **Service** | **7/10** | 反向依赖 API 层 |
| **Engine** | **7/10** | RecommendationEngine 不纯 |
| **整體** | **5.75/10** | 需要结构性重构 |

### 推荐行动项

1. **P0 — 拆分 Domain/ORM**：将现有 `*Model` 类移到 `database/models.py`，在 `domain/` 中创建纯 Python 领域模型
2. **P0 — 修复 Service-API 反向依赖**：提取共享 Schema
3. **P0 — 统一事务策略**：`BaseRepository` 改为 flush()，审计所有 commit() 调用
4. **P0 — 重构 Outbox Repository**：分离 CRUD 和业务逻辑
5. **P1 — 修复 Recommendation Engine**：将 I/O 和状态管理移到调用方
6. **P1 — 统一状态字段使用 SAEnum**：替换所有 `String(32)` 状态字段
7. **P1 — 添加乐观锁**：为 Aggregate Root 添加 version_id
8. **P2 — 补充 Repository 类型注解**：统一使用 `AsyncSession`

---

*报告结束*
