# REVIEW Report: Phase-3D-Graph-Correctness-Hardening (Round 0)

## 检查清单
- 是否可执行：YES
- 是否有错误：NO（有错误）
- 是否满足需求条列：NO
- 是否有测试：YES

## 细项评分
- 完整性：7/10（需求NO，最高10分）
- 正确性：6/10（有错误，最高10分）
- 可维护性：17/25
- 测试与验证：12/25

## 总分：42/100（不合格）

## Reviewer Gate 20 项逐项确认

| # | 项目 | 结果 | 说明 |
|---|------|------|------|
| 1 | Entity ID deterministic | PASS | UUIDv5 + 固定 Namespace + canonical key；Go 和 Python 实现一致 |
| 2 | Relation ID deterministic | PASS | `clinical:relation:{kind}:{from}:{to}` 格式，Go/Python 一致 |
| 3 | Same Event replay idempotent | PASS | Go `TestDuplicateReplay_Idempotent` 验证实体/关系数量与 ID 一致 |
| 4 | created→updated 不重复 | PASS | Go `TestUpdatedEvent_Upsert` 验证更新后 ID 不变、属性更新 |
| 5 | 所有 Relation Target 存在 | PASS | Go `TestRelationTargetIntegrity` 验证 delta 中所有 From/To 均有对应 Entity |
| 6 | Patient→Recommendation 正确 | PASS | adapter.go mapRecommendationEvent 创建 FOR_PATIENT 关系，To 指向 Patient |
| 7 | Recommendation→Drug/Evidence 正确 | PASS | adapter.go 创建 RECOMMENDS/SUPPORTED_BY 关系，Drug/Evidence 实体均在 delta 中 |
| 8 | Decision→Recommendation 正确 | PASS | adapter.go mapClinicalDecisionEvent 创建 BASED_ON 关系 |
| 9 | Consensus→Decision 正确 | PASS | adapter.go mapConsensusEvent 创建 DERIVED_FROM 关系 |
| 10 | Consensus→Opinion→Specialty 正确 | PASS | adapter.go 创建 HAS_OPINION + PROVIDED_BY_SPECIALTY 关系链 |
| 11 | Python ID == Go ID | PASS | 相同 CLINICAL_NAMESPACE、相同 canonical key 格式、相同规范化规则；CI 中内联验证 |
| 12 | Provenance 完整 | PASS | entityProps 包含 source_system/source_table/source_id/event_id/event_type/schema_version/actor_id/correlation_id/causation_id/occurred_at/aggregate_type/aggregate_id；Go `TestProvenanceFields` 验证 |
| 13 | Event Payload 来自真实 Domain Model | **FAIL** | (a) tumor_board_service.py 第406行 `opinion_id` 使用 `str(_uuid.uuid4())` 随机生成，非确定值，违反确定性原则；(b) recommendation_service.py 的 `evidence_references` 硬编码为 `[]`，未从 pipeline 提取实际证据引用 |
| 14 | async subprocess 不阻塞 | PASS | client.py 使用 `asyncio.create_subprocess_exec()`，shell=False，有 timeout/kill/returncode/JSON 校验 |
| 15 | Worker 不长时间持有 DB lock | PASS | 三段式事务：Claim→commit→External Work→Result→commit，符合要求 |
| 16 | stale processing 可恢复 | PASS | `release_stale()` 将超过 timeout 的 processing 事件重置为 pending |
| 17 | failed events API 可见 | PASS | `GET /clinical-graph/failed-events` 返回 failed/dead_letter 事件列表 |
| 18 | Status API 反映 CLI 真实状态 | PASS | `/clinical-graph/status` 结合 outbox 统计、CLI 可用性、stale count、oldest pending age，返回 operational/degraded/unavailable |
| 19 | CI pin KnowGraphGo SHA | PASS | CI 使用 `ref: f0a1075`（特定 SHA），非浮动分支 |
| 20 | Cross-repository Digital Thread 测试通过 | **FAIL** | CI 运行独立 Go 测试和 Python 测试，但缺少需求要求的完整端到端测试：Build CLI → 临时 SQLite → 产生 Event → apply → 再 apply → query → 验证幂等 + Digital Thread 路径 |

**Gate 统计：PASS=18，FAIL=2**

## 关键问题汇总

### P0 问题

1. **Consensus Event opinion_id 随机生成**（tumor_board_service.py:406）
   - `"opinion_id": str(_uuid.uuid4())` 使用随机 UUID 而非确定值
   - `SpecialistOpinionDTO` 缺少 opinion_id 字段
   - 导致相同 consensus 重建时产生不同 graph entity ID
   - **影响**：破坏 Consensus 事件幂等性，违反确定性 ID 原则

2. **Patient Thread status 检查不完整**（clinical_graph.py:190-197）
   - `get_patient_thread` 仅检查 `result.get("success")` 就标记 `projection_status = "connected"`
   - 违反需求 "不得只因 CLI 回传 success 就标记 projection_status = connected，必须确认 entities 或 path 非空"

3. **Recommendation event evidence_references 为空**（recommendation_service.py:296）
   - `"evidence_references": []` 硬编码为空列表，未从 pipeline 提取实际证据引用

### 测试覆盖缺口

1. **缺少完整的跨仓库 Digital Thread E2E 测试**（需求第17项）
2. **缺少 async client 子进程测试**（success/non-zero exit/timeout/invalid JSON/CLI not found/large stdout）
3. **缺少 full rebuild 幂等性测试**（两次 rebuild 后 Entity/Relation 数量一致）
4. **缺少独立的跨语言 ID parity 测试文件**（仅有 CI 内联 Python 验证，无 Go/Python 交叉断言）

## 最终判定

Phase 3D Graph Correctness Hardening：**FAIL**
Phase 3D Accepted：**NO**
Ready for Treatment Plan：**NO**

### 判定依据

- 总评分 **42/100**，远低于 95 分合格线
- 6 项核心要求中（Deterministic ID / Relation Integrity / Idempotency / Digital Thread / Cross-language ID parity / Cross-repository integration），**Idempotency** 因 opinion_id 随机生成未完全满足
- Reviewer Gate 20 项中 2 项 FAIL（Item 13: Event Payload 来自 Domain Model；Item 20: Cross-repository Digital Thread 测试）
- 需求第四项明确要求"若 payload 缺少 opinion_id / specialty / evidence_ids，须在 AI-Kill-Cancer Event Payload 中补足"，当前实现未满足

### 修复建议

1. **修复 opinion_id 随机生成**：在 `SpecialistOpinionDTO` 中添加 opinion_id 字段，或基于 specialist+specialty+position 生成确定性 opinion_id
2. **修复 Patient Thread status 检查**：添加 `if entities:` 条件判断后再标记 connected
3. **补全 evidence_references**：从 pipeline 提取实际证据引用并写入 outbox payload
4. **补充测试**：async client 子进程测试、full rebuild 幂等性测试、跨仓库 E2E Digital Thread 测试、跨语言 ID parity 断言测试
