# Phase 3D Graph Correctness Hardening — 第 5 次 Review 報告

## 基本資訊

- **任務**: Phase 3D Graph Correctness Hardening
- **返工次數**: 第 5 次（最終評分）
- **評審日期**: 2026-07-28
- **評審人**: AI Reviewer Sub-agent
- **KnowGraphGo SHA**: `a7a5b2e`（fix(clinical): add panic for empty ID validation）
- **CI KnowGraphGo ref**: `a7a5b2e`（固定 SHA ✅）

---

## 檢查清單

| 項目 | 結果 | 說明 |
|------|------|------|
| 是否可執行 | **YES** | Go build/vet 通過，Python import 無錯誤 |
| 是否有錯誤 | **NO（有錯誤）** | Go 17 項測試全部 PASS，Python 54 項 PASS + 3 項 FAILED（均為測試代碼問題，非生產代碼） |
| 是否滿足需求條列 | **NO** | 見 Reviewer Gate 20 項詳細分析 |
| 是否有測試 | **YES** | KnowGraphGo 17 項測試 + AI-Kill-Cancer 10 個測試文件共 57 項測試 |

---

## 測試實際運行結果

### KnowGraphGo (Go) 測試 — 全部 17 項 PASS ✅

```
=== RUN   TestClinicalIDFactory_Deterministic              --- PASS
=== RUN   TestClinicalIDFactory_RelationID                 --- PASS
=== RUN   TestMapPatientEvent                              --- PASS
=== RUN   TestMapRecommendationEvent                       --- PASS
=== RUN   TestMapDecisionEvent                             --- PASS
=== RUN   TestMapConsensusEvent                            --- PASS
=== RUN   TestRelationTargetIntegrity                      --- PASS (3 subtests)
=== RUN   TestDuplicateReplay_Idempotent                   --- PASS
=== RUN   TestUpdatedEvent_Upsert                          --- PASS
=== RUN   TestProvenanceFields                             --- PASS (4 subtests)
=== RUN   TestSensitivePayloadRejection                    --- PASS
=== RUN   TestNewClinicalAdapter                           --- PASS
=== RUN   TestNewOntology                                  --- PASS
=== RUN   TestPatientEvent                                 --- PASS
=== RUN   TestUnknownEvent                                 --- PASS
=== RUN   TestImportInterface                              --- PASS
=== RUN   TestRebuild                                      --- PASS
```

### AI-Kill-Cancer (Python) 測試 — 54 項 PASS + 3 項 FAILED ⚠️

```
tests/test_phase3d_async_client.py .............. 6 PASSED
tests/test_phase3d_digital_thread.py ............ 5 PASSED
tests/test_phase3d_id_parity.py ............... 10 PASSED
tests/test_phase3d_rebuild_idempotent.py ....... 6 PASSED
tests/unit/test_phase3d_event_schema.py ........ 9 PASSED
tests/unit/test_phase3d_outbox_repo.py ......... 6 PASSED + 1 FAILED
tests/unit/test_phase3d_outbox_service.py ...... 4 PASSED
tests/unit/test_phase3d_rebuild.py ............. 4 PASSED
tests/unit/test_phase3d_worker.py .............. 3 PASSED + 2 FAILED
```

**3 項失敗分析（均為測試代碼問題）：**

1. `test_mark_failed` — 測試斷言 `status == "pending" or status == "dead_letter"`，但新實作正確將 status 設為 `"failed"`。測試未同步更新到新的 status 模型。

2. `test_worker_with_mock_client` — 測試創建事件時未設置 `occurred_at`，導致 worker 構建 `ClinicalGraphEvent` 時 pydantic 驗證失敗。

3. `test_worker_retry_on_failure` — 同上，測試創建事件時缺少 `occurred_at`。

> **結論**: 生產代碼無錯誤，3 項測試需要更新以適配新的必填字段 `occurred_at` 和新的 status 枚舉值 `failed`。

### 靜態分析

```
go vet ./adapter/clinical/...   → 通過（無警告）
go build ./cmd/knowgraph/       → 通過
```

---

## Reviewer Gate 20 項逐項確認

| # | 檢查項 | 狀態 | 證據 |
|---|--------|------|------|
| 1 | Entity ID deterministic | ✅ PASS | UUIDv5 + ClinicalNamespace (`a7b4e5c2-...`) + canonical key，Go/Python 一致 |
| 2 | Relation ID deterministic | ✅ PASS | `clinical:relation:{kind}:{from}:{to}` 格式，Go/Python 一致 |
| 3 | Same Event replay idempotent | ✅ PASS | `TestDuplicateReplay_Idempotent` PASS |
| 4 | created→updated 不重複 | ✅ PASS | `TestUpdatedEvent_Upsert` PASS |
| 5 | 所有 Relation Target 存在 | ✅ PASS | `TestRelationTargetIntegrity` 3 子測試全部 PASS |
| 6 | Patient→Recommendation 正確 | ✅ PASS | FOR_PATIENT Relation 存在並指向 Patient Entity |
| 7 | Recommendation→Drug/Evidence 正確 | ✅ PASS | RECOMMENDS + SUPPORTED_BY Relation 存在 |
| 8 | Decision→Recommendation 正確 | ✅ PASS | BASED_ON Relation 存在 |
| 9 | Consensus→Decision 正確 | ✅ PASS | DERIVED_FROM Relation 存在 |
| 10 | Consensus→Opinion→Specialty 正確 | ✅ PASS | HAS_OPINION + PROVIDED_BY_SPECIALTY Relation 存在 |
| 11 | Python ID==Go ID | ⚠️ PARTIAL | 算法一致（同 namespace + canonical key + normalize），**但無直接 Go golden test 輸出與 Python 輸出的交叉驗證測試** |
| 12 | Provenance 完整 | ⚠️ PARTIAL | Entity Properties 包含完整 11 個 provenance 字段（source_system, source_id, source_table, aggregate_type, aggregate_id, event_id, event_type, schema_version, occurred_at, actor_id, correlation_id, causation_id）。**Relation 僅設置 ProvenanceImported 枚舉值，未在 Relation 層級保存詳細 Properties** |
| 13 | Event Payload 來自真實 Domain Model | ✅ PASS | RecommendationService / TumorBoardService 均已從真實 pipeline 結果構建 payload |
| 14 | async subprocess 不阻塞 | ✅ PASS | `asyncio.create_subprocess_exec()` 實現，6 項子進程測試全部 PASS |
| 15 | Worker 不長時間持有 DB lock | ✅ PASS | 三段式事務（claim→commit→work→result→commit） |
| 16 | stale processing 可恢復 | ✅ PASS | 支援 stale recovery：processing 超過 timeout 重新變為 pending |
| 17 | failed events API 可見 | ✅ PASS | 5 種狀態（pending/processing/failed/completed/dead_letter），GET failed 端點存在 |
| 18 | Status API 反映 CLI 真實狀態 | ✅ PASS | 結合 Outbox pending/failed/dead_letter 計數、CLI 可用性、clinical verify、projection 時間等 7 項指標 |
| 19 | CI pin KnowGraphGo SHA | ✅ PASS | `ref: a7a5b2e`（固定 SHA，非浮動分支） |
| 20 | Cross-repository Digital Thread | ⚠️ PARTIAL | CI 中運行 Go adapter 測試 + Python ID 驗證，**但缺少需求 §十七要求的完整端到端流程**：Build CLI → 臨時 SQLite → 產生 Event 序列 → apply → 再次 apply → query → 驗證冪等 + Digital Thread 路徑 |

> **判定**: 6 項核心需求（Deterministic ID / Relation Integrity / Idempotency / Digital Thread / Cross-language ID parity / Cross-repository integration）中，**3 項完全滿足，3 項部分滿足**。依 requirements.md 規則，滿足需求條列 = NO，最高 89 分。

---

## 細項評分

### 完整性（19/25）

| 需求分類 | 完成度 | 說明 |
|----------|--------|------|
| Deterministic ID（三、十） | ✅ 完成 | Go + Python 雙實現，同 namespace + canonical key + normalize |
| Target Entity 建立（四） | ✅ 完成 | 4 種 Event（Patient/Recommendation/ClinicalDecision/Consensus）均正確建立完整 Entities + Relations |
| GraphDelta 完整性（五） | ✅ 完成 | 測試驗證所有 Relation.From/To 均在 delta 中 |
| Idempotent Replay（六） | ✅ 完成 | replay + upsert 測試通過 |
| Provenance（七） | ⚠️ 部分 | Entity 包含完整 provenance（11 字段）；Relation 僅設置 `ProvenanceImported`，未在 Relation Properties 中保存詳細來源信息 |
| Outbox Schema（八、十三） | ✅ 完成 | Migration 022 存在，6 個新欄位（correlation_id, causation_id, occurred_at, claim_token, processing_started_at, last_failed_at） |
| Event Payload（九） | ✅ 完成 | RecommendationService 從 pipeline 結果提取 evidence_references；TumorBoardService 構建 specialist_opinions |
| Python Query ID（十） | ✅ 完成 | `ClinicalGraphIDFactory` 完整實現 9 種 Entity + RelationID |
| Explain Query（十一） | ✅ 完成 | Recommendation / Consensus explain API 存在 |
| Async Client（十二） | ✅ 完成 | `asyncio.create_subprocess_exec()`，6 項子進程測試全部 PASS |
| Worker Transaction（十三） | ✅ 完成 | 三段式事務（Claim → Commit → External Work → Result → Commit） |
| Failed Events（十四） | ✅ 完成 | 5 種狀態（pending/processing/failed/completed/dead_letter），claim_pending 包含 failed |
| Status API（十五） | ✅ 完成 | 7 項健康指標整合，狀態分為 operational/degraded/unavailable |
| CI 修正（十六） | ✅ 完成 | 固定 SHA `a7a5b2e`，非浮動分支 |
| 跨倉庫測試（十七） | ⚠️ 部分 | CI 中有 Python ID 校驗 + Go 單元測試，但缺少完整 E2E 流程 |
| 空 ID 拒絕（三） | ✅ 完成 | Go `panic()` ✅（`newEntityID` 空值 panic），Python `raise ValueError` ✅ |

### 正確性（22/25）

- ID 算法完全正確（UUIDv5 + 相同 namespace `a7b4e5c2-...` + 相同 canonical key 格式）
- 映射邏輯覆蓋所有 4 種 Event 類型及其 update 類型
- Go 17 項測試全部 PASS ✅
- Python 54 項測試 PASS ✅
- 無語法錯誤、無 lint 警告
- **扣 3 分**：3 項 Python 測試因測試代碼未適配最新變更而失敗（生產代碼正確，但測試代碼落後）

### 可維護性（22/25）

- 代碼結構清晰，Go 和 Python 實現對稱
- 文檔齊全（`docs/clinical-graph-id-spec.md` 存在）
- 命名規範，注釋充分
- KnowGraphGo SHA 已 pin
- **扣 3 分**：Relation Provenance 不完整可能導致未來混淆；測試代碼未同步更新

### 測試與驗證（17/25）

- KnowGraphGo: 17 項測試 ✅
- AI-Kill-Cancer: 10 個測試文件，54 項 PASS + **3 項 FAILED** ⚠️
- CI 中自動化執行 ✅
- **缺少**：直接 Go vs Python ID 交叉驗證（golden test 比較）
- **缺少**：端到端 Cross-repository Digital Thread 測試
- **扣分**：3 項測試失敗降低可靠性

---

## 總分

| 維度 | 分數（0-25） |
|------|-------------|
| 完整性（Completeness） | 19 |
| 正確性（Correctness） | 22 |
| 可維護性（Maintainability） | 22 |
| 測試與驗證（Testing & Verification） | 17 |
| **總分** | **80 / 100** |

**判定：不合格（< 90）** ❌

---

## 關鍵不足摘要

### 相比第 4 次 Review 的變化

| 問題 | 第 4 次狀態 | 第 5 次狀態 | 變化 |
|------|-----------|-----------|------|
| Go 空 ID 拒絕 | ❌ 未實現 | ✅ panic() 已實現 | **✅ 已修復** |
| Relation Provenance | ⚠️ 部分 | ⚠️ 部分（未變） | **❌ 未修復** |
| 跨語言 ID 交叉驗證 | ⚠️ 部分 | ⚠️ 部分（未變） | **❌ 未修復** |
| 端到端 Digital Thread 測試 | ⚠️ 部分 | ⚠️ 部分（未變） | **❌ 未修復** |
| 測試穩定性 | ✅ 全部 PASS | ⚠️ 3 項 FAILED | **⬇️ 倒退** |

### 當前 4 項關鍵不足

1. **Relation Provenance 不完整**（requirements.md 第七節）
   - Entity 的 Properties 包含完整 11 個 provenance 字段
   - Relation 僅設置 `Provenance: ProvenanceImported`，未在 Properties 中保存詳細信息
   - `graph.Relation` 結構體支持 Properties 字段，但 adapter.go 未使用

2. **缺少直接跨語言 ID 比較測試**（requirements.md 第十節）
   - CI 中僅驗證 Python 端 ID 有效性及算法一致性
   - 無 Go 生成 golden output → Python 讀取比對的正式交叉驗證
   - 無法直接證明 Python ID == Go ID

3. **缺少端到端 Digital Thread Integration Test**（requirements.md 第十七節）
   - CI 中只運行了 adapter 單元測試 + Python ID 校驗
   - 未實現需求要求的完整流程：Build CLI → 臨時 SQLite Graph DB → 產生 Event → CLI apply → 再次 apply → CLI query → 驗證冪等 + Digital Thread 路徑

4. **3 項 Python 測試失敗**
   - `test_mark_failed`：測試斷言未更新到新的 status 模型（`"failed"` 替代 `"pending"/"dead_letter"`）
   - `test_worker_with_mock_client` / `test_worker_retry_on_failure`：測試創建事件時缺少必填字段 `occurred_at`

---

## 建議（按優先級）

1. **P0**: 修復 3 項失敗測試（更新 test_mark_failed 斷言，為 worker 測試中的事件添加 occurred_at）
2. **P1**: 在 KnowGraphGo 建立 golden test 產生 golden_output.json → Python 側讀取比對
3. **P1**: 在 CI 中增加完整的 E2E Digital Thread 測試（build CLI → init DB → apply → query → verify）
4. **P2**: 考慮在 Relation 的 Properties 中也保存詳細 provenance 信息

---

## 最終判定

| 項目 | 結果 |
|------|------|
| Phase 3D Graph Correctness Hardening | **FAIL** |
| Phase 3D Accepted | **NO** |
| Ready for Treatment Plan | **NO** |
| Reviewer Score | **80/100** ⛔ |

**原因**：6 項核心需求中 3 項（Digital Thread / Cross-language ID parity / Cross-repository integration）未完全滿足，依 requirements.md 規則 Reviewer 最高 89 分。當前總分 80/100 < 90，判定不合格。此外 3 項 Python 測試失敗導致測試穩定性倒退。
