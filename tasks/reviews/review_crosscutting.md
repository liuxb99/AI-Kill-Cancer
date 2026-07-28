# 横切关注点审查报告

> 审查日期: 2026-07-20
> 审查范围: Migration(001-025), API(v1), Digital Thread, Trace

---

## 5. Migration Review

**分數：6/10**

### 发现的问题

#### 5.1 SQLite 与 PostgreSQL 不一致

1. **migrations/versions/001** — 使用了 `sa.sqlalchemy.dialects.postgresql` 导入但未使用；`_create_enum_if_not_exists` 函数定义了但从未被调用。这导致 migration 001 假设存在 `postgresql` 方言的 import，但从未实际使用它。
   - 文件: `migrations/versions/001_initial_precision_oncology_foundation.py:22,31-40`

2. **migrations/versions/015** — Upgrade 中正确处理了 SQLite 的特殊性（使用 recreate table 方式实现 NOT NULL），但 **downgrade() 中使用 `batch_alter_table` 的 `alter_column(nullable=True)`**，这在 SQLite 下可能不会正确还原为非空的约束——因为 SQLite 的 batch mode 虽然会重建表，但 `alter_column` 的 `nullable=True` 实际上什么也不做，导致原本 NOT NULL 的列仍然 NOT NULL。这违反了 Upgrade/Downgrade 的幂等性。
   - 文件: `migrations/versions/015_make_clinical_reports_case_id_non_nullable.py:65-72`

3. **migrations/versions/022** — SQLite 的 downgrade 使用表重建策略，但在重建后重新创建了所有索引。然而：
   - 它没有还原 `correlation_id` 上的索引 `ix_outbox_correlation_id`
   - `CREATE INDEX` 语句可能因索引已存在而失败（虽然 upgrade 用了 try-except，downgrade 没有）
   - 文件: `migrations/versions/022_phase3d_graph_correctness_outbox.py:78-142`

4. **migrations/versions/025** — Upgrade 中 SQLite 分支删除了 `uq_treatment_plan_version` 约束并创建了 `uq_plan_id_version`，但在 downgrade 中：
   - SQLite 分支使用 `batch_op.alter_column("plan_id", existing_type=sa.String(64), nullable=False)` 来恢复索引，但 `nullable=False` 参数实际上没有改变列的可空性
   - PostgreSQL 分支直接使用 `ALTER TABLE ... DROP CONSTRAINT IF EXISTS`，而 SQLite 分支使用了不同的机制
   - 文件: `migrations/versions/025_phase3e_version_composite_unique.py:139-198`

#### 5.2 Upgrade ↔ Downgrade ↔ Re-upgrade 不一致

5. **migrations/versions/019** — Downgrade 使用了 `IrreversibleMigrationError` 来防止有数据时降级，这是好实践。但 upgrade 中的 `op.drop_index()` 调用假设索引名称 `ix_domain_clinical_decision_traces_trace_id` 一定存在——如果从 018 直接升级到 019 没问题，但如果降级后再升级，索引名称可能因数据库而异（SQLAlchemy 自动生成的索引名可能不同）。
   - 文件: `migrations/versions/019_phase3b_trace_compound_unique.py:41-100`

6. **migrations/versions/004** — 添加了 `analysis_eligible` 列，其 `server_default="pending_validation"`。但在 downgrade 中只是 `drop_column`，没有还原数据的逻辑。如果表中有数据，downgrade 会丢失这些列的数据。
   - 文件: `migrations/versions/004_phase2a_final_security.py:23-38`

#### 5.3 SQLite 下 batch operations 的潜在问题

7. **migrations/versions/003** — 使用了 `with op.batch_alter_table("domain_uploaded_files") as batch_op:` 来修改 `sequencing_test_id` 的 nullable 属性。在 SQLite 下，batch mode 会重建整个表，这：
   - 需要表上不能有外键引用约束冲突（如果有其他表引用了此表，重建可能失败）
   - 不保证并发安全
   - 文件: `migrations/versions/003_phase2a_hardening.py:48-49`

8. **migrations/versions/022** — `_has_column` 函数使用 `PRAGMA table_info()` 检查列是否存在。这在 SQLite 下工作正常，但在不同 SQLite 版本中的行为可能存在细微差异。特别是 `row[1]` 的索引取决于 PRAGMA 输出的列顺序，虽然这在实践中稳定，但不如使用命名列那么健壮。
   - 文件: `migrations/versions/022_phase3d_graph_correctness_outbox.py:27-44`

#### 5.4 其他潜在问题

9. **migrations/versions/008** — `domain_drug_rankings` 表缺少 `sa.ForeignKey` 引用，虽然某些列（`variant_id`, `case_id`）看起来应该是外键。在 SQLite 下这没问题，但在 PostgreSQL 下这些列不会被强制执行引用完整性。
   - 文件: `migrations/versions/008_drug_ranking.py:23-39`

10. **migrations/versions/013** — 在 upgrade 中使用了 `Inspector.has_table()` 和列检查来实现幂等性，但在 downgrade() 中直接 `op.drop_table()`，如果表已经不存在会导致错误。
    - 文件: `migrations/versions/013_production_hardening.py:66`

11. **migrations/versions/021** — Downgrade 在检查 `domain_clinical_graph_outbox` 表中是否有数据时，在检查前没有确认表是否存在。如果表不存在（例如从 020 直接降级），`SELECT COUNT(*)` 会失败。
    - 文件: `migrations/versions/021_phase3d_clinical_graph_outbox.py:51-53`

### 良好实践

- Migration 019、020、021、023 使用了 `IrreversibleMigrationError` 来防止有数据时降级破坏数据。
- Migration 015 正确实现了 SQLite 的表重建模式来处理 NOT NULL 约束。
- Migration 022 的 `_has_column` 函数跨数据库检查列是否存在，实现了幂等性。
- Migration 025 的 PostgreSQL 分支使用了 `DO $$ ... END $$` 匿名代码块来实现条件约束创建/删除。

### 建议

1. **统一 SQLite/PostgreSQL 模式**：为所有 migration 添加明确的 SQLite 分支，而不是依赖 `batch_alter_table` 作为通用解决方案。
2. **添加幂等性检查**：在所有 `drop_index`、`drop_column`、`drop_table` 前添加存在性检查。
3. **验证 downgrade 后的 schema**：在 CI 中添加 `alembic downgrade -1 && alembic upgrade +1` 测试，确保升级→降级→再升级的幂等性。
4. **修复 Migration 015 的 downgrade**：确保 downgrade 后 `case_id` 列确实可空。

---

## 6. API Layer Review

**分數：7/10**

### 发现的问题

#### 6.1 HTTP Status Code 不一致

1. **POST 返回 200 而非 201**：
   - `/api/v1/recommendation` — `@router.post("", response_model=RecommendationResponse)` 没有指定 `status_code=201`。
   - 文件: `src/backend/api/v1/recommendation.py:125`

2. **PATCH 使用 PUT**：
   - `/api/v1/cases/{case_id}` 使用 `@router.put(...)` 但语义上是部分更新（使用 `body.model_dump(exclude_none=True)`），应该用 PATCH。
   - 文件: `src/backend/api/v1/cases.py:131`

3. **DELETE 返回 200 而非 204**：
   - `analyses.py` 中没有 DELETE 端点。
   - 但 `patients.py:93` 和 `cases.py:150` 正确使用了 `status_code=204`。
   - ✅ 这是正确的。

4. **GET 端点缺少 404 处理**：
   - `/api/v1/clinical/evidence/gene/{gene_symbol}` — 没有对不存在的 gene 进行 404 检查，而是返回一个空的 EvidenceBundle。
   - 文件: `src/backend/api/v1/clinical.py:158-171`

5. **POST 端点缺少 409 冲突处理**：
   - 大多数 POST 端点对唯一约束冲突没有专门的 409 处理，统一返回 500。
   - 例如 `patients.py:38` 的 `create_patient` 如果 `external_id` 重复会返回 500 而不是 409。
   - 文件: `src/backend/api/v1/patients.py:33-38`

#### 6.2 Error Response 格式不一致

6. **三种不同的 error 格式并存**：
   - **格式 A**: `{"error": "not_found", "message": "..."}` — 用于 clinical.py 和推荐相关的端点
   - **格式 B**: 纯文本 `"detail": "Patient not found"` — 用于 patients.py、cases.py
   - **格式 C**: 带状态码的 JSON `{"error": "invalid_uuid", "message": "..."}` — 用于 evidence.py
   
   文件对比:
   - `clinical.py:106` → 格式 A 
   - `patients.py:54` → 格式 B
   - `evidence.py:87` → 格式 C

7. **Validation 错误格式不统一**：
   - `clinical_decision.py:54` 使用 `raise HTTPException(status_code=422, detail=str(e))` — 纯文本
   - `recommendation.py:169` 使用 `raise HTTPException(status_code=422, detail={"error": "validation_failed", "message": str(exc)})` — 结构化 JSON
   - `treatment_plans.py:89` 使用 `raise HTTPException(status_code=422, detail=str(e))` — 纯文本

#### 6.3 Validation 位置不一致

8. **部分 Validation 在 API 层，部分在 Service 层**：
   - `patients.py:48-50` — UUID 验证在 API 层
   - `cases.py:72-74` — UUID 验证在 API 层
   - `clinical_decision.py:45-46` — Validation 委托给 Service 层（ValueError 捕获）
   - `recommendation.py:162-164` — Validation 委托给 Service 层

   这种不一致导致 API 层有时返回 400（格式错误），有时返回 422（业务验证失败），有时返回 500（未捕获的异常）。

#### 6.4 缺少标准错误 Schema

9. 没有统一的错误响应模型。虽然一些端点使用了 `{"error": "...", "message": "..."}` 格式，但这不是全局强制执行的。建议定义一个标准的 `ErrorResponse` Pydantic 模型并在所有端点中使用。

#### 6.5 其他问题

10. **cases.py:150-163** — DELETE 端点中的 UUID 验证使用 `status_code=404` 而不是 `400`，这和 patients.py 的行为不一致。
    - 文件: `src/backend/api/v1/cases.py:141,160`

11. **upload_vcf.py** 和 **uploads.py** — 文件上传端点的错误处理使用内联 try-except，但格式与其他端点不同（使用不同的 detail 结构）。

12. **缺少请求体的 Pydantic Validation**：
    - `recommendation.py:33-61` — `RecommendationRequest` 有 `min_length` 约束，但部分端点（如 `workbench.py`）的请求体没有明确的字段约束。

### 良好实践

- 大部分 GET 端点正确返回 200/404 语义。
- DELETE 端点正确使用 204/404 语义（除了上传相关端点）。
- `clinical.py` 中的 `_build_context_and_evidence` 辅助函数统一了重复的逻辑。
- `treatment_plans.py` 中的 `_handle_service_error` 辅助函数统一了异常到 HTTP 错误的映射。

### 建议

1. **定义统一的 Error Schema**：创建全局 `ErrorResponse` 模型，格式为 `{"error": "...", "message": "...", "details": {...} | None}`。
2. **统一 HTTP Status Code**：确保所有 POST 返回 201，PATCH 返回 200，DELETE 返回 204。
3. **统一 Validation 策略**：决定 API 层只做格式验证（UUID 格式、必填字段），Service 层做业务验证。
4. **为所有 POST 添加 409 处理**：捕获唯一约束冲突并返回 409。
5. **CI 集成**：添加 OpenAPI schema 检查，确保所有端点的 response_model 和 status_code 与规范一致。

---

## 7. Digital Thread Review

**分數：7.5/10**

### 发现的问题

#### 7.1 事件链完整性

1. **Patient 的事件链不完整**：
   - Event schema 定义了 `patient.created` 和 `patient.updated`（`clinical_graph_event.py:24-25`）
   - KnowGraphGo 端处理了这两个事件（`adapter.go:67-68`）
   - 但 Python 后端没有找到任何创建 patient outbox 事件的代码！
   - `grep` 检查确认：没有服务调用 `clinical_graph_event_service.create_event` 来发出 patient 事件
   - 这意味着 Patient 实体的变化永远不会被投影到知识图谱

2. **Recommendation 的事件链**：
   - `recommendation_service.py:277-309` — 在 `create_recommendation` 中写入了 `recommendation.created` outbox 事件 ✅
   - 但 `recommendation.updated` 事件从未被发出（没有更新 recommendation 的端点）
   - ✅ 这可能是设计如此

3. **Clinical Decision 的事件链**：
   - `clinical_decision_service.py:374-387` — 在 `create_decision` 中写入了 `clinical_decision.created` outbox 事件 ✅
   - 但 `clinical_decision.updated` 事件从未被发出
   - ✅ 合理，因为决策一般不更新

4. **Tumor Board Consensus 的事件链**：
   - `tumor_board_service.py:400-428` — 在 `create_consensus` 中写入了 `tumor_board_consensus.created` outbox 事件 ✅
   - 但 `tumor_board_consensus.updated` 事件从未被发出
   - ✅ 合理

5. **Treatment Plan 的事件链**：
   - `treatment_plan_service.py:355-356` — 在 `create_plan` 中写入了 `treatment_plan.created` outbox 事件 ✅
   - `treatment_plan_service.py:572` — `submit_plan` 中写入了 `treatment_plan.updated` ✅
   - `treatment_plan_service.py:769,776` — 状态变更事件（approved/activated/paused/completed/superseded）✅
   - **这是最完整的事件链** ✅

#### 7.2 Outbox 模式的一致性

6. **出箱模式有两种实现方式**：
   - **方式 A（`clinical_graph_event_service.py`）**：使用 `ClinicalGraphEventService.create_event()`，推荐使用这种方式
   - **方式 B（`treatment_plan_service.py`）**：直接使用 `ClinicalGraphOutboxRepository` 的 `create()` 方法，绕过了 `ClinicalGraphEventService`
   - 文件: `src/backend/services/clinical_graph_event_service.py:34-56` vs `src/backend/services/treatment_plan_service.py:981-1023`
   
   这导致：
   - 方式 B 不进行敏感字段验证（`validate_payload_sensitive_fields`）
   - 方式 B 需要手动构造 event DTO
   - 方式 B 不会自动设置 `clinical_graph_outbox` 表中的 `occurred_at` 字段

7. **服务注入方式不一致**：
   - `recommendation_service.py:79-84` — 可选的 `graph_event_service` 构造函数参数
   - `clinical_decision_service.py:156-163` — 可选的 `graph_event_service` 构造函数参数
   - `tumor_board_service.py:243-251` — 可选的 `graph_event_service` 构造函数参数
   - `treatment_plan_service.py:235-249` — 直接创建 `ClinicalGraphOutboxRepository` 实例
   
   `treatment_plan_service` 没有使用 `ClinicalGraphEventService`，而是直接操作 repository。

#### 7.3 KnowGraphGo 端 Projection Handler 的完整性

8. **KnowGraphGo 端的事件处理覆盖**（`adapter/clinical/adapter.go`）：
   - `patient.created` / `patient.updated` → `mapPatientEvent` ✅
   - `recommendation.created` / `recommendation.updated` → `mapRecommendationEvent` ✅
   - `clinical_decision.created` / `clinical_decision.updated` → `mapClinicalDecisionEvent` ✅
   - `tumor_board_consensus.created` / `tumor_board_consensus.updated` → `mapConsensusEvent` ✅
   - `treatment_plan.created` / `treatment_plan.updated` → `mapTreatmentPlanEvent` ✅
   - `treatment_plan.approved` / `.activated` / `.paused` / `.completed` / `.superseded` → 各有独立 handler ✅
   
   **KnowGraphGo 端的事件处理是完整的！** 所有在 `GraphEventType` 中定义的事件类型都有对应的 Go handler。

9. **但是**：KnowGraphGo 端处理了 `patient.updated` 事件，但 Python 后端从未发送 `patient.updated` 事件（`patients.py:71-90` 的 PATCH 端点没有写 outbox）。

#### 7.4 ID 工厂一致性

10. **Python vs Go ID 工厂一致性**：
    - `src/backend/clinical_graph/id_factory.py` — Python 端的 UUIDv5 实现
    - `KnowGraphGo/adapter/clinical/id_factory.go` — Go 端的 UUIDv5 实现
    - 两者的 `CLINICAL_NAMESPACE` 相同：`a7b4e5c2-8d9f-4a3b-8c1d-6e9f2a7b3c5d`
    - 两者的规范化规则相同（trim + lowercase）
    - 两者的 canonical key 格式相同
    - ✅ **ID 工厂跨语言一致**

#### 7.5 Worker 实现

11. **`ClinicalGraphProjectionWorker`** 使用了三段式事务（claim → external work → result），这是正确的 Outbox 模式实现 ✅
12. **`release_stale`** 方法处理了卡在 `processing` 状态的陈旧事件 ✅
13. **重试策略**通过 `DEFAULT_RETRY_POLICY` 实现，包括指数退避和死信阈值 ✅

#### 7.6 缺失的事件类型

14. **Event schema 中缺少 `patient.deleted`**: 
    - `GraphEventType` 中没有定义 `patient.deleted`
    - 患者删除后，知识图谱中的患者实体不会被删除或标记为非活跃
    - 文件: `src/backend/schemas/clinical_graph_event.py:23-39`

15. **Event schema 中没有 `treatment_plan.deleted`**:
    - 当 treatment plan 被删除时，知识图谱中对应的实体不会被清理

### 良好实践

- KnowGraphGo 端的 adapter 实现了完整的 entity-relation 映射，包括所有 5 个业务领域和处理 15+ 种事件类型。
- 三段式事务（claim → work → result）正确实现了 Outbox 模式。
- Python 和 Go 之间的 ID 工厂使用相同的 UUIDv5 命名空间和规范化规则，保证了确定性 ID 的跨语言一致性。

### 建议

1. **添加 Patient outbox 事件**：在 `PatientRepository.update()` 和创建患者的端点中添加 outbox 事件写入。
2. **统一 Outbox 写入方式**：让 `treatment_plan_service` 也使用 `ClinicalGraphEventService` 而不是直接操作 repository。
3. **添加删除事件**：为 `patient.deleted` 和 `treatment_plan.deleted` 添加事件类型和处理逻辑。
4. **添加 CI 检查**：确保每个 `GraphEventType` 都有对应的 Go handler，反之亦然。

---

## 8. Trace Review

**分數：5.5/10**

### 发现的问题

#### 8.1 Trace Schema 不统一

1. **存在三个独立的 Trace 系统**：

   | 系统 | 文件 | 存储方式 | 字段 |
   |------|------|----------|------|
   | **CalculationTrace** | `calculation_trace.py` | 内存 (dict) | `trace_id`, `patient_id`, `steps[]` (step_name, step_type, input_data, output_data, timestamp, duration_ms) |
   | **TreatmentPlanTrace** | `treatment_plan_trace.py` | 内存 + DB (ORM) | `step_order`, `step_type`, `input_summary`, `output_summary`, `rule_ids`, `evidence_ids` |
   | **DecisionThread** | `decision_thread.py` | DB (ORM) | `node_type`, `input_snapshot`, `evidence_snapshot`, `agent_id`, `reasoning`, `confidence`, `context_hash` |
   
   这三个系统各自为政：
   - 字段命名不一致：`input_data` vs `input_summary` vs `input_snapshot`
   - 字段类型不一致：`output_data: dict` vs `output_summary: dict` vs `input_snapshot: dict`
   - 时间戳字段不一致：`timestamp: datetime` vs 无时间戳 vs `timestamp: DateTime`
   - 没有统一的 Trace ID 体系

2. **DB 层面的 Trace 表结构也不一致**：
   - `domain_recommendation_traces` + `domain_recommendation_trace_steps` (migration 017)
   - `domain_clinical_decision_traces` (migration 018)
   - `domain_tumor_board_consensus_traces` (migration 020)
   - `domain_treatment_plan_traces` (migration 023)
   
   这些表的字段命名、约束和关系都不同——没有统一的 trace_step 表设计。

#### 8.2 CalculationTrace 未被任何引擎使用

3. **`CalculationTrace` / `TraceManager` 的使用范围**：
   - 仅在 `recommendation_engine.py` 中被使用 ✅
   - `clinical_decision_engine.py` — **完全不使用** CalculationTrace ❌
   - `tumor_board_engine.py` — 使用自建的 `trace_steps: List[Dict]` 而不是 CalculationTrace ❌
   - `treatment_plan_engine.py` — 使用 `TreatmentPlanTraceBuilder` 而不是 CalculationTrace ❌

4. **`clinical_decision_engine.py`**（`src/backend/clinical/clinical_decision_engine.py`）：
   - 完全没有 trace 相关代码
   - `grep` 确认文件中没有 "trace" 或 "Trace" 的匹配
   - 这是一个缺少 Trace 的 Engine

5. **`tumor_board_engine.py`**（`src/backend/clinical/tumor_board_engine.py`）：
   - 使用了自建的 `trace_steps: List[Dict]` 列表
   - 每个步骤函数都接受并填充 `trace_steps` 参数
   - 但它不使用 `CalculationTrace` 或 `TraceManager`
   - Trace 格式是简单的 `List[Dict]`，没有类型约束

#### 8.3 CalculationTrace 是纯内存的

6. **`TraceManager` 将所有 trace 存储在内存中**（`_traces: dict[str, CalculationTrace]`）
   - 服务器重启后所有 trace 丢失
   - 不支持跨请求的 trace 查询（除了通过 API 返回的 trace_id）
   - 文件: `src/backend/clinical/calculation_trace.py:201`

7. 虽然有 DB 层面的 trace 表（如 `domain_recommendation_traces`），但 `CalculationTrace` 和这些表之间没有映射关系。`recommendation_service.py:158` 创建的 `TraceManager` 实例完全是内存中的，不持久化到数据库。

#### 8.4 TreatmentPlanTrace 不与 CalculationTrace 一致

8. **`TreatmentPlanTraceBuilder`**（`treatment_plan_trace.py`）和 **`TraceManager`**（`calculation_trace.py`）是两套独立的实现：
   - `TreatmentPlanTraceBuilder.add_step()` 返回 `TreatmentPlanTraceStep` 对象
   - `TraceManager.add_step()` 接受 `TraceStep` 对象（来自 `calculation_trace.py`）
   - 两者都表示"一系列步骤"，但互不兼容
   - 即使它们都持久化到 DB，格式也不一致

#### 8.5 Migration 中的 Trace 表定义

9. **Migration 017** 创建的 `domain_recommendation_traces` 和 `domain_recommendation_trace_steps` 表：
   - `trace_id` 在 `domain_recommendation_traces` 中是 UNIQUE，但实际应该允许多个 step 共享同一个 trace_id（类似 migration 019 修复的问题）
   - 文件: `migrations/versions/017_phase3a_recommendation_tables.py:48`

10. **Migration 018** 创建的 `domain_clinical_decision_traces` 表：
    - `trace_id` 是 UNIQUE，但同一条目包含 `step_order` 字段（暗示每行是一个 step）
    - 这被 Migration 019 修复了——但 017 的类似问题没有被修复
    - 文件: `migrations/versions/018_phase3b_clinical_decision_tables.py:46-56`

#### 8.6 Trace 字段不完整

11. **`TraceStep`**（`calculation_trace.py:30-87`）包含：
    - `step_name`, `step_type`, `input_data`, `output_data`, `timestamp`, `duration_ms`, `parent_trace_id`
    - 但没有 `step_order` 字段（步骤顺序依赖列表索引）
    - 没有 `evidence_ids` 或 `rule_ids`（这些在 `TreatmentPlanTraceStep` 中有）

12. **`TreatmentPlanTraceStep`**（`treatment_plan_trace.py:48-84`）包含：
    - `step_order`, `step_type`, `input_summary`, `output_summary`, `rule_ids`, `evidence_ids`
    - 但没有 `step_name`（使用 `step_type` 代替）
    - 没有 `timestamp` 或 `duration_ms`
    - 没有 `parent_trace_id`

#### 8.7 DecisionThread 中的 Trace 不完整

13. **`DecisionNode`**（`decision_thread.py:77-142`）包含 `input_snapshot` 和 `evidence_snapshot`，但：
    - 没有 `output_snapshot`（只记录了输入和证据，不记录步骤的输出）
    - 对于 agent_opinion 节点，`reasoning` 字段被用于存储 agent 的 summary，但这不是结构化的
    - 文件: `src/backend/clinical/decision_thread.py:77-101`

### 良好实践

- `recommendation_engine.py` 正确使用了 `TraceManager` 来记录完整的 pipeline 步骤。
- `treatment_plan_engine.py` 在每个步骤中都记录了 `rule_ids` 和 `evidence_ids`，提供了完整的可审计性。
- `tumor_board_engine.py` 的自建 trace 系统至少记录了每个步骤的输入输出。
- 几乎所有 engine 都有某种形式的 trace 记录——只是不统一。

### 建议

1. **统一 Trace Schema**：定义一个通用的 `TraceStep` 模型，包含 `step_order`, `step_type`, `step_name`, `input_data`, `output_data`, `timestamp`, `duration_ms`, `evidence_ids`, `rule_ids`, `parent_trace_id` 字段，在所有 engine 中统一使用。
2. **统一 Trace Manager**：将 `TraceManager` 从纯内存改为支持 DB 持久化（可选），或废弃它，让所有 engine 都使用 DB-backed trace。
3. **修复 Migration 017 的 trace_id UNIQUE 问题**：类似 migration 019，为 recommendation_traces 添加复合 UNIQUE(trace_id, step_order) 约束。
4. **为 clinical_decision_engine.py 添加 Trace**：目前该 engine 完全没有 trace 记录。
5. **统一 DecisionThread 和 CalculationTrace**：两者都用于跟踪 pipeline 步骤，但使用不同的数据模型。考虑将 DecisionNode 与 TraceStep 统一。

---

## 总结

| 审查项目 | 分数 | 关键发现 |
|----------|------|----------|
| Migration Review | 6/10 | SQLite/PostgreSQL 不一致、downgrade 不幂等、部分 migration 缺少数据保护 |
| API Layer Review | 7/10 | Status Code 不一致、Error Response 格式不统一、Validation 位置不统一 |
| Digital Thread Review | 7.5/10 | Patient 事件缺失、Outbox 写入方式不统一、其余事件链完整 |
| Trace Review | 5.5/10 | 三套独立 Trace 系统、字段命名不一致、缺少 DB 持久化、clinical_decision_engine 无 Trace |

**整体横切关注点评分：6.5/10**

主要改进方向：
1. 统一 Trace 架构
2. 统一 SQLite/PostgreSQL migration 策略
3. 统一 API Error Response 格式
4. 完善 Patient 事件链
