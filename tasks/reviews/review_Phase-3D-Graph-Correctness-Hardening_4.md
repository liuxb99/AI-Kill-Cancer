# Phase 3D Graph Correctness Hardening — 返工第 4 次 Review 報告

## 基本資訊

- **任務**: Phase 3D Graph Correctness Hardening
- **返工次數**: 第 4 次
- **評審日期**: 2026-07-28
- **評審人**: AI Reviewer Sub-agent

---

## 檢查清單

| 項目 | 結果 | 說明 |
|------|------|------|
| 是否可執行 | **YES** | Go build/vet 通過，Python import 無錯誤 |
| 是否有錯誤 | **YES（無錯誤）** | Go 17 項測試全部 PASS，Python 27 項測試全部 PASS |
| 是否滿足需求條列 | **NO** | 見下方詳細分析 |
| 是否有測試 | **YES** | KnowGraphGo 17 項測試 + AI-Kill-Cancer 4 個測試文件共 27 項測試 |

---

## 測試實際運行結果

### KnowGraphGo (Go) 測試

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

**結果: 全部 17 項測試 PASS** ✅

### AI-Kill-Cancer (Python) 測試

```
tests/test_phase3d_id_parity.py ........... 10 PASSED
tests/test_phase3d_rebuild_idempotent.py .... 6 PASSED
tests/test_phase3d_digital_thread.py ....... 5 PASSED
tests/test_phase3d_async_client.py ......... 6 PASSED
```

**結果: 全部 27 項測試 PASS** ✅

### 靜態分析

```
go vet ./adapter/clinical/...   → 通過（無警告）
go build ./cmd/knowgraph/       → 通過
```

---

## Reviewer Gate 20 項逐項確認

| # | 檢查項 | 狀態 | 證據 |
|---|--------|------|------|
| 1 | Entity ID deterministic | ✅ | UUIDv5 + ClinicalNamespace + canonical key，測試通過 |
| 2 | Relation ID deterministic | ✅ | RelationID(kind, from, to) 使用相同機制，測試通過 |
| 3 | Same Event replay idempotent | ✅ | TestDuplicateReplay_Idempotent PASS |
| 4 | created→updated 不重複 | ✅ | TestUpdatedEvent_Upsert PASS |
| 5 | 所有 Relation Target 存在 | ✅ | TestRelationTargetIntegrity PASS（3 個子測試） |
| 6 | Patient→Recommendation 正確 | ✅ | FOR_PATIENT Relation 存在 |
| 7 | Recommendation→Drug/Evidence 正確 | ✅ | RECOMMENDS + SUPPORTED_BY Relation 存在 |
| 8 | Decision→Recommendation 正確 | ✅ | BASED_ON Relation 存在 |
| 9 | Consensus→Decision 正確 | ✅ | DERIVED_FROM Relation 存在 |
| 10 | Consensus→Opinion→Specialty 正確 | ✅ | HAS_OPINION + PROVIDED_BY_SPECIALTY Relation 存在 |
| 11 | Python ID==Go ID | ⚠️**部分** | 算法一致（同 namespace + canonical key），但**無直接交叉驗證測試** |
| 12 | Provenance 完整 | ⚠️**部分** | Entity 完整（entityProps 含全部字段），但 **Relation 僅 ProvenanceImported 枚舉值，缺少 Properties 詳細信息** |
| 13 | Event Payload 來自真實 Domain Model | ✅ | RecommendationService / ClinicalDecisionService / TumorBoardService 均已檢查 |
| 14 | async subprocess 不阻塞 | ✅ | asyncio.create_subprocess_exec()，6 項測試全部 PASS |
| 15 | Worker 不長時間持有 DB lock | ✅ | 三段式事務（claim→commit→work→result→commit） |
| 16 | stale processing 可恢復 | ✅ | release_stale() 方法實現 |
| 17 | failed events API 可見 | ✅ | GET /failed-events 端點 |
| 18 | Status API 反映 CLI 真實狀態 | ✅ | CLI 可用性 + verify + 各項健康指標 |
| 19 | CI pin KnowGraphGo SHA | ✅ | ref: f0a1075（固定 SHA，非浮動分支） |
| 20 | Cross-repository Digital Thread | ⚠️**部分** | CI 中運行 adapter 測試 + Python ID parity，**但無完整的 CLI build→apply→query 端到端流程** |

> **判定**: 6 項關鍵需求中 3 項不完全滿足，依 requirements.md 規則最高 89 分。

---

## 細項評分

### 完整性（20/25）

| 需求分類 | 完成度 | 說明 |
|----------|--------|------|
| Deterministic ID（三、十） | ✅ 完成 | Go + Python dual implementation |
| Target Entity 建立（四） | ✅ 完成 | 4 種 Event 的完整 mapping |
| GraphDelta 完整性（五） | ✅ 完成 | 測試驗證所有 Relation target 在 delta 中 |
| Idempotent Replay（六） | ✅ 完成 | replay + upsert 測試通過 |
| Provenance（七） | ⚠️ 部分 | Entity 完整，但 Relation 缺少 Properties provenance |
| Outbox Schema（八、十三） | ✅ 完成 | Migration 022 存在，6 個新欄位 |
| Event Payload（九） | ✅ 完成 | 三個 Service 均已匹配 Domain Model |
| Python Query ID（十） | ✅ 完成 | docs/clinical-graph-id-spec.md 存在 |
| Explain Query（十一） | ✅ 完成 | Recommendation / Consensus explain API |
| Async Client（十二） | ✅ 完成 | 6 項非阻塞測試全部 PASS |
| Worker Transaction（十三） | ✅ 完成 | 三段式事務 |
| Failed Events（十四） | ✅ 完成 | 5 種狀態 + claim_pending 包含 failed |
| Status API（十五） | ✅ 完成 | 7 項健康指標 |
| CI 修正（十六） | ✅ 完成 | 固定 SHA f0a1075 |
| 跨倉庫測試（十七） | ⚠️ 部分 | 無端到端 Digital Thread CLI 測試 |
| 空 ID 拒絕（三） | ⚠️ 部分 | Python 實現 ✅，Go 未實現 ❌ |

### 正確性（23/25）

- ID 算法完全正確（UUIDv5 + 相同 namespace + 相同 canonical key 格式）
- 映射邏輯覆蓋所有 4 種 Event 類型及其 update 類型
- 所有測試通過
- 無語法錯誤、無 lint 警告
- 扣分項：Go 端無空 ID 驗證可能導致靜默錯誤

### 可維護性（22/25）

- 代碼結構清晰，Go 和 Python 實現對稱
- 文檔齊全（docs/clinical-graph-id-spec.md 存在）
- 命名規範，注釋充分
- 扣分項：Go ClinicalIDFactory 缺少錯誤處理；Relation Provenance 不完整可能導致未來混淆

### 測試與驗證（20/25）

- KnowGraphGo: 17 項測試，覆蓋 ID 確定性、mapping、integrity、idempotency、provenance、rebuild
- AI-Kill-Cancer: 4 個測試文件共 27 項測試
- CI 中自動化執行
- **缺少**：直接 Go vs Python ID 交叉驗證測試
- **缺少**：端到端 Digital Thread 測試（build CLI → init DB → apply events → query → verify）

---

## 總分

| 維度 | 分數（0-25） |
|------|-------------|
| 完整性（Completeness） | 20 |
| 正確性（Correctness） | 23 |
| 可維護性（Maintainability） | 22 |
| 測試與驗證（Testing & Verification） | 20 |
| **總分** | **85 / 100** |

**判定：不合格（< 90）** ❌

---

## 關鍵不足摘要

1. **Relation Provenance 不完整**（requirements.md 第七節）
   - Entity 的 Properties 包含 source_system, event_id, event_type 等完整 provenance
   - Relation 僅設置 `Provenance: ProvenanceImported`，未設置 Properties
   - `graph.Relation` 結構體支持 Properties 字段，但 adapter.go 未使用

2. **Go 端缺少空 ID 拒絕**（requirements.md 第三節）
   - Python `_make_id()` 在 key 為空時 raise ValueError
   - Go `newEntityID()` 直接生成 UUID，無錯誤檢查

3. **缺少直接跨語言 ID 比較測試**（requirements.md 第十節）
   - CI 中僅驗證 Python 端 ID 有效性
   - 未直接比較 Go 生成的 ID 與 Python 生成的 ID 是否一致

4. **缺少端到端 Digital Thread Integration Test**（requirements.md 第十七節）
   - CI 中只運行了 adapter 單元測試
   - 未實現「Build CLI → 建立臨時 SQLite Graph DB → 產生 Event → CLI apply → verify」的完整流程

---

## 建議

1. **Relation Provenance**: 在 adapter.go 的 Relation 構建中加入 Properties，使用 entityProps 或類似函數填充 provenance 信息
2. **空 ID 驗證**: Go ClinicalIDFactory.newEntityID 中加入空 ID 檢查並返回 error
3. **跨語言 ID 測試**: 在 CI 中增加 Go 程式輸出 ID，與 Python 比對的測試
4. **端到端測試**: 在 CI 中增加完整的 CLI build → apply → query → verify 流程

---

## 最終判定

| 項目 | 結果 |
|------|------|
| Phase 3D Graph Correctness Hardening | **PARTIAL** |
| Phase 3D Accepted | **NO** |
| Ready for Treatment Plan | **NO** |
| Reviewer Score | **85/100** |
