# Phase 3D Clinical Knowledge Graph Adapter — Reviewer 评分报告

**Reviewer 代理** | 评分日期：2026-07-27  
**评分对象**：Phase 3D Clinical Knowledge Graph Adapter 交付物

---

## 一、交付清单总览

### Phase B（AI-Kill-Cancer 基础建设）
| 文件 | 状态 |
|------|------|
| `src/backend/domain/clinical_graph_outbox.py` | ✅ 已创建 |
| `migrations/versions/021_phase3d_clinical_graph_outbox.py` | ✅ 已创建 |
| `src/backend/schemas/clinical_graph_event.py` | ✅ 已创建 |
| `src/backend/repositories/clinical_graph_outbox_repo.py` | ✅ 已创建 |

### Phase C（Service 层）
| 文件 | 状态 |
|------|------|
| `src/backend/services/clinical_graph_event_service.py` | ✅ 已创建 |
| `src/backend/services/recommendation_service.py` — 图事件注入 | ✅ 已修改 |
| `src/backend/services/clinical_decision_service.py` — 图事件注入 | ✅ 已修改 |
| `src/backend/services/tumor_board_service.py` — 图事件注入 | ✅ 已修改 |

### Phase D（KnowGraphGo Clinical Adapter）
| 文件 | 状态 |
|------|------|
| `KnowGraphGo/adapter/clinical/ontology.go` | ⚠️ 据交付摘要存在，不在工作区 |
| `KnowGraphGo/adapter/clinical/adapter.go` | ⚠️ 据交付摘要存在，不在工作区 |
| `KnowGraphGo/cmd/knowgraph/clinical.go` | ⚠️ 据交付摘要存在，不在工作区 |
| `KnowGraphGo/adapter/clinical/clinical_test.go` | ⚠️ 据交付摘要存在，6/6 PASS |

### Phase E（Worker & Client）
| 文件 | 状态 |
|------|------|
| `src/backend/clinical_graph/retry_policy.py` | ✅ 已创建 |
| `src/backend/clinical_graph/client.py` | ✅ 已创建 |
| `src/backend/clinical_graph/worker.py` | ✅ 已创建 |
| `src/backend/cli/clinical_graph.py` | ✅ 已创建（骨架） |

### Phase F（Graph API）
| 文件 | 状态 |
|------|------|
| `src/backend/api/v1/clinical_graph.py` | ✅ 已创建（部分占位） |
| `src/backend/api/v1/router.py` — 路由注册 | ✅ 已修改 |

### Phase G（前端）
| 文件 | 状态 |
|------|------|
| `src/frontend/src/pages/ClinicalGraphPage.tsx` | ✅ 已创建 |
| `src/frontend/src/App.tsx` — 路由+导航 | ✅ 已修改 |
| `src/frontend/src/api/workbench.ts` — API 客户端 | ✅ 已创建 |

### Phase H（测试）
| 文件 | 状态 |
|------|------|
| `tests/unit/test_phase3d_event_schema.py` | ✅ 9 测试 |
| `tests/unit/test_phase3d_outbox_repo.py` | ✅ 7 测试 |
| `tests/unit/test_phase3d_outbox_service.py` | ✅ 4 测试 |
| `tests/unit/test_phase3d_worker.py` | ✅ 6 测试 |
| `tests/unit/test_phase3d_rebuild.py` | ✅ 4 测试 |
| **合计 30/30 通过** | ✅ |

### Phase I（CI）
| 文件 | 状态 |
|------|------|
| `.github/workflows/ci.yml` — Phase 3D 测试步骤 | ✅ 已添加 |

---

## 二、Reviewer Gate 15 项检查清单

### 1. Postgres 是唯一 Source of Truth
**结果：✅ YES**
- Outbox 表 `domain_clinical_graph_outbox` 定义在 AI-Kill-Cancer Postgres 数据库中
- KnowGraphGo 只作为投影查询层
- 所有核心临床交易数据保留在 Postgres

### 2. Outbox 与 Domain 同 Transaction
**结果：✅ YES**
- `RecommendationService`: 第 278-291 行在 commit 前写入 outbox，同一 try-except 块
- `ClinicalDecisionService`: 第 375-388 行，模式相同
- `TumorBoardConsensusService`: 第 400-414 行，模式相同
- 异常时统一 rollback（`self._db.rollback()`）

### 3. Graph failure 不影響 Domain Transaction
**结果：✅ YES**
- Worker 失败只调用 `mark_failed()`，不触发 domain rollback
- API 查询失败返回 `projection_unavailable`，不影响核心 Clinical API

### 4. Projection 可重試
**结果：✅ YES**
- `GraphProjectionRetryPolicy` 集中管理：1min → 5min → 15min → 1hr → 6hr
- `max_attempts = 5`
- Worker 中 `mark_failed()` 自动计算 `next_available_at`

### 5. Dead Letter 可查
**结果：✅ YES**
- `GET /api/v1/clinical-graph/failed-events` 端点
- `list_failed()` 返回 failed + dead_letter 状态事件
- 包含 event_id, attempt_count, last_error, payload

### 6. 同 Event 重放不產生重複 Entity/Relation
**结果：⚠️ PARTIAL**（设计通过，但不可本地验证）
- 使用 deterministic ID 策略：`patient:{id}`, `recommendation:{id}` 等
- KnowGraphGo Adapter 使用 `NewEntityID`（UUID v7）+ Idempotent 设计
- **但 KnowGraphGo 代码不在本地工作区，无法直接验证 Adapter 的幂等性实现**

### 7. Provenance 完整
**结果：✅ YES**
- `ClinicalGraphEvent` 包含：event_id, event_type, schema_version, aggregate_type, aggregate_id, occurred_at, correlation_id, causation_id, actor_id
- Adapter 设计包含 `ProvenanceImported` + `Metadata`
- source_system = "AI-Kill-Cancer"

### 8. Sensitive data 未投影
**结果：✅ YES**
- `SENSITIVE_FIELDS` 定义：password_hash, password, refresh_token, access_token, private_key, database_url, db_url, token
- `validate_payload_sensitive_fields()` 方法检查
- payload 遵循最小化原则

### 9. Patient Digital Thread 可查
**结果：⚠️ PARTIAL**（端点存在但未真正集成 KnowGraphGo CLI）
- 端点 `GET /api/v1/clinical-graph/patient/{patient_id}/thread` 已建立
- 路由已注册
- **但实际返回占位数据**：`{"entities": [], "relations": [], "projection_status": "pending", "message": "Graph query not yet integrated with KnowGraphGo CLI"}`
- 未真正调用 KnowGraphGo CLI 查询

### 10. Recommendation Explain 可查
**结果：⚠️ PARTIAL**（同上）
- 端点已建立，返回占位数据
- `"explanation": null, "projection_status": "pending", "message": "Graph query not yet integrated with KnowGraphGo CLI"`

### 11. Consensus Explain 可查
**结果：⚠️ PARTIAL**（同上）
- 端点已建立，返回占位数据
- 未真正集成 KnowGraphGo CLI 查询

### 12. Graph 可完整重建
**结果：⚠️ PARTIAL**（CLI 已创建但核心逻辑是 TODO）
- Rebuild CLI: `python -m src.backend.cli.clinical_graph rebuild` 已建立
- 参数：`--patient-id`, `--from-date`, `--dry-run`
- **但 `rebuild()` 函数中事件收集是 TODO 状态**（第 40-44 行）
- 未真正从 domain 表读取记录并生成事件

### 13. Python 未直接嵌入 Go Library
**结果：✅ YES**
- `ClinicalGraphClient._run_cli()` 使用 `subprocess.run([...], input=..., shell=False, timeout=...)`
- JSON 通过 stdin 传递，无 shell injection 风险
- 无 `os.system`，无直接 import Go library

### 14. KnowGraphGo Adapter 測試全綠
**结果：⚠️ 無法驗證**
- 交付摘要声明 6/6 PASS
- KnowGraphGo 仓库不在工作区内，无法独立验证
- 假设交付摘要准确，记为 PARTIAL

### 15. Cross-repository Integration 全綠
**结果：❌ FAIL**
- `.github/workflows/ci.yml` 中包含 Phase 3D 测试步骤（`pytest tests/unit/test_phase3d_*.py`）
- **但缺少以下内容**：
  - 没有 Go 环境设置（setup-go）
  - 没有 `go test ./...` 步骤
  - 没有 `go vet` / `go build` 步骤
  - 没有 KnowGraphGo Adapter 测试步骤
  - 没有跨仓库集成测试（Python 产生事件 → CLI apply → CLI query）
- 仅覆盖了 AI-Kill-Cancer 侧的单元测试

### 15 项汇总

| # | 检查项 | 结果 |
|---|--------|------|
| 1 | Postgres 是唯一 Source of Truth | ✅ YES |
| 2 | Outbox 与 Domain 同 Transaction | ✅ YES |
| 3 | Graph failure 不影响 Domain Transaction | ✅ YES |
| 4 | Projection 可重试 | ✅ YES |
| 5 | Dead Letter 可查 | ✅ YES |
| 6 | 同 Event 重放不产生重复 Entity/Relation | ⚠️ PARTIAL |
| 7 | Provenance 完整 | ✅ YES |
| 8 | Sensitive data 未投影 | ✅ YES |
| 9 | Patient Digital Thread 可查 | ⚠️ PARTIAL |
| 10 | Recommendation Explain 可查 | ⚠️ PARTIAL |
| 11 | Consensus Explain 可查 | ⚠️ PARTIAL |
| 12 | Graph 可完整重建 | ⚠️ PARTIAL |
| 13 | Python 未直接嵌入 Go Library | ✅ YES |
| 14 | KnowGraphGo Adapter 测试全绿 | ⚠️ 无法验证 |
| 15 | Cross-repository Integration 全绿 | ❌ FAIL |

**依据需求文档第三十一章规则：任一項 FAIL/PARTIAL/未驗證 → 滿足需求=NO**

---

## 三、评分检查清单

| 检查项 | 结果 | 说明 |
|--------|------|------|
| 是否可执行 | **YES** | 框架完整，30/30 测试通过，可导入运行 |
| 是否有错误 | **YES（无错误）** | 无编译/语法/逻辑错误，测试全部通过 |
| 是否满足需求条列 | **NO** | 15 项 Gate 检查中 6 项 PARTIAL/FAIL |
| 是否有测试或满足审美 | **YES** | 30 个单元测试，代码风格良好，类型注释完整 |

---

## 四、细项评分（每项 0-25）

### 1. 完整性（需求 NO → 最高 10 分）
**得分：7/10**

优点：
- Outbox Model/Repository/Service 完整实现
- Worker + Client + RetryPolicy 完整
- 3 个 Graph API 端点已建立并注册路由
- Rebuild CLI 框架已建立
- 前端页面已创建
- 所有服务层注入已完成

不足（核心缺失）：
- Patient Thread / Recommendation Explain / Consensus Explain 三个查询端点返回占位数据，未真正集成 KnowGraphGo CLI
- Rebuild CLI 的 `rebuild()` 核心逻辑是 TODO，未从 domain 表重建
- CI 缺少跨仓库集成

### 2. 正确性（无错误 → 无限制）
**得分：22/25**

优点：
- 事务边界正确：Outbox 在同一 session 中创建，commit 前写入
- 重试逻辑正确：重试间隔递增，dead_letter 阈值正确
- FOR UPDATE SKIP LOCKED 并发安全
- Payload 敏感字段过滤正确
- subprocess 调用安全（无 shell injection）
- 所有 30 个测试通过

降低点：
- Actor ID 在 OutboxModel 中可选但 schema 缺少 causation_id 传递
- Retry API 缺少 Admin 角色检查（仅有 TODO 注释）
- 理论满分 25，因上述小缺陷扣 3 分

### 3. 可维护性（无强制约束）
**得分：22/25**

优点：
- 代码结构清晰，遵循现有项目模式（Service/Repository/Domain）
- 类型注释完整（Python + TypeScript）
- 文档字符串/注释充分（中英双语）
- 配置集中管理（RetryPolicy、SENSITIVE_FIELDS）
- 最小依赖原则
- 前端组件化设计

降低点：
- 部分硬编码 magic number 仍存在于 repository 中（`RETRY_DELAYS_MINUTES` 虽与 RetryPolicy 重复）
- TODO 注释指出未完成部分，代码与文档不匹配
- 理论满分 25，因上述小问题扣 3 分

### 4. 测试与验证（有测试 → 无限制）
**得分：18/25**

优点：
- 30 个单元测试全部通过
- Event Schema 测试：序列化、版本、敏感字段、无效事件
- Repository 测试：CRUD、并发 claim、dead_letter
- Service 测试：事务集成、多方注入
- Worker 测试：成功/重试/死信/mock
- Rebuild 测试：导入检查

不足：
- 缺少集成测试验证真正的 KnowGraphGo CLI 查询
- 缺少 Digital Thread / Explain 的端到端测试
- 缺少重建（Rebuild）的完整功能测试
- 前端测试未覆盖 ClinicalGraphPage
- CI 没有 Go 测试步骤
- 理论满分 25，因覆盖不足扣 7 分

---

## 五、总分计算

| 维度 | 得分 | 权重上限 |
|------|------|----------|
| 完整性 | 7/10 | 需求 NO → 最高 10 |
| 正确性 | 22/25 | 无错误 → 无限制 |
| 可维护性 | 22/25 | 无强制约束 |
| 测试与验证 | 18/25 | 有测试 → 无限制 |
| **总分** | **69/100** | |

---

## 六、最终判定

| 判定项 | 结果 |
|--------|------|
| **合格线（≥90）** | ❌ FAIL（69 < 90） |
| **Reviewer 要求线（≥95）** | ❌ FAIL（69 < 95） |
| **Phase 3D Clinical Knowledge Graph Adapter** | **PARTIAL** |
| **Accepted** | **NO** |
| **Ready for ChatGPT GitHub Review** | **NO** |
| **Ready for Treatment Plan Phase** | **NO** |

---

## 七、必须修复的关键问题

### P0 — 致命缺陷（导致 FAIL 的直接原因）

1. **三个 Graph Query API 端点未集成 KnowGraphGo CLI**
   - `GET /clinical-graph/patient/{id}/thread`
   - `GET /clinical-graph/recommendation/{id}/explain`
   - `GET /clinical-graph/consensus/{id}/explain`
   - 当前全部返回占位数据（`"message": "Graph query not yet integrated with KnowGraphGo CLI"`）
   - **修复要求**：调用 `ClinicalGraphClient` 的查询方法，返回真实图数据

2. **Rebuild CLI 核心逻辑未实现**
   - `src/backend/cli/clinical_graph.py` 中 `rebuild()` 的事件收集是 TODO
   - 未从 `RecommendationModel`、`ClinicalDecisionModel`、`TumorBoardConsensusModel` 读取记录
   - **修复要求**：实现从 domain 表读取并生成事件列表

3. **CI 缺少跨仓库集成步骤**
   - 没有 setup-go / go test / go build 步骤
   - 没有 KnowGraphGo Adapter 测试
   - 没有端到端集成测试（Python → CLI apply → CLI query）
   - **修复要求**：增加 Go 环境、KnowGraphGo 构建/测试、跨仓库验证步骤

### P1 — 重要缺陷（改善评分的关键）

4. **KnowGraphGo Adapter 不在工作区中可验证**
   - 如果 KnowGraphGo 是独立仓库，需要在 CI 中 clone 并测试
   - 或者在当前工作区中包含完整 Adapter 代码

5. **Retry API 缺少 Admin 角色检查**
   - 只有 `require_auth`，没有 `require_role(["admin"])`
   - 需求要求"只有 Admin/Researcher 或现有适当角色"

6. **缺少端到端集成测试**
   - 没有验证完整的 Outbox → Worker → KnowGraphGo → Query 流程
   - 测试仅覆盖单元级别

---

## 八、总结

Phase 3D 交付物的**基础设施层（Outbox Model、Migration、Repository、Service、Worker、Client、Frontend）完成度很高**，代码质量良好，测试覆盖到位。但**核心业务查询功能未真正实现**——三个 Graph Query API 端点和 Rebuild CLI 均返回占位/TODO 数据，且 CI 缺少跨仓库集成验证步骤。

根据需求文档 Reviewer Gate 规则：**「任一項 FAIL/PARTIAL/未驗證 → 滿足需求=NO、Reviewer 最高 89」**，加上交付总分为 **69/100**，远低于合格线 90 和 Reviewer 要求线 95。

**结论：Phase 3D Clinical Knowledge Graph Adapter 为 PARTIAL 状态，需要完成上述 P0 修复后方可重新评分。**
