# REVIEW Report: Phase-3D-Graph-Correctness-Hardening (Round 3 — Rework 2 Review)

> 基於返回工第 2 輪後的評分。
> 原始需求：`tasks/requirements.md`
> 前次評分：`review_Phase-3D-Graph-Correctness-Hardening_2.md`（55/100）

---

## 檢查清單

| 項目 | 結果 | 說明 |
|------|------|------|
| 是否可執行 | **YES** | 代碼可導入，57 個測試中 54 個通過 |
| 是否有錯誤 | **NO（有錯誤）** | 3 個測試仍然失敗（與前次相同，未修復） |
| 是否滿足需求條列 | **NO** | Digital Thread 和 Cross-repository Integration 核心需求未完成 |
| 是否有測試 | **YES** | 新增 `integration/test_phase3d_query_api.py`（7 tests），但 3 個測試失敗未修復 |

---

## 細項評分

| 項目 | 評分 | 備註 |
|------|------|------|
| 完整性 | **14/25** | 核心 P0 修復較多：idx bug 修復 ✅、mark_failed→failed ✅、三段式事務 ✅、stale release ✅、非阻塞 client ✅、Status API 真實健康度 ✅。但 Digital Thread E2E 和 Cross-repository Integration 核心需求仍缺失 |
| 正確性 | **16/25** | 核心邏輯修正確實提升了正確性；但 3 個已知測試失敗仍未修復（測試代碼 bug），表明測試與生產代碼間的一致性不足 |
| 可維護性 | **20/25** | 代碼結構良好，模塊拆分合理，三段式事務架構清晰，ID Factory 設計一致 |
| 測試與驗證 | **12/25** | 新增 `integration/test_phase3d_query_api.py`（7 tests），但 3 個測試失敗未修復，測試覆蓋缺口（Migration 022、Concurrent claim、Stale recovery 等）仍然存在 |

---

## 總分：**62/100**（不合格）

（14 + 16 + 20 + 12 = 62）

---

## Reviewer Gate 20 項逐項確認

| # | 項目 | 結果 | 說明 |
|---|------|------|------|
| 1 | Entity ID deterministic | **PASS** | UUIDv5 + 固定 Namespace + canonical key；Go 和 Python 實現一致 |
| 2 | Relation ID deterministic | **PASS** | `clinical:relation:{kind}:{from}:{to}` 格式，Go/Python 一致 |
| 3 | Same Event replay idempotent | **PASS** | Go `TestDuplicateReplay_Idempotent` 驗證 |
| 4 | created→updated 不重複 | **PASS** | Go `TestUpdatedEvent_Upsert` 驗證 |
| 5 | 所有 Relation Target 存在 | **PASS** | Go `TestRelationTargetIntegrity` 驗證 |
| 6 | Patient→Recommendation 正確 | **PASS** | adapter.go mapRecommendationEvent 創建 FOR_PATIENT |
| 7 | Recommendation→Drug/Evidence 正確 | **PASS** | adapter.go 創建 RECOMMENDS/SUPPORTED_BY |
| 8 | Decision→Recommendation 正確 | **PASS** | adapter.go 創建 BASED_ON |
| 9 | Consensus→Decision 正確 | **PASS** | adapter.go 創建 DERIVED_FROM |
| 10 | Consensus→Opinion→Specialty 正確 | **PASS** | adapter.go 創建 HAS_OPINION + PROVIDED_BY_SPECIALTY |
| 11 | Python ID == Go ID | **🟡 PARTIAL** | Python 端 10 個測試全部通過 ✅；CI 中有 Python 內联驗證。但**缺少 Go golden test 交叉比對** — 沒有讓 Go 生成 ID 與 Python 生成的 ID 進行正式比對 |
| 12 | Provenance 完整 | **PASS** | entityProps 包含 12 個 Provenance 欄位；Go `TestProvenanceFields` 驗證 |
| 13 | Event Payload 來自真實 Domain Model | **PASS** | (a) recommendation_service.py evidence_references 已從 response 提取 ✅；(b) tumor_board_service.py opinion_id 使用 ClinicalGraphIDFactory 生成 ✅；(c) idx bug **已修復** — 第 405 行已改為 `for op_idx, opinion in enumerate(...)` ✅ |
| 14 | async subprocess 不阻塞 | **PASS** | client.py 使用 `asyncio.create_subprocess_exec()`，shell=False，有 timeout/kill/returncode/JSON 校驗 ✅ |
| 15 | Worker 不長時間持有 DB lock | **PASS** | 已實現三段式事務：Claim→commit→External Work→Result→commit ✅ |
| 16 | stale processing 可恢復 | **PASS** | `release_stale()` 將超過 timeout 的 processing 事件重置為 pending ✅ |
| 17 | failed events API 可見 | **PASS** | `GET /clinical-graph/failed-events` 返回 failed/dead_letter 事件列表 ✅ |
| 18 | Status API 反映 CLI 真實狀態 | **PASS** | `/clinical-graph/status` 結合 outbox 統計、CLI 可用性、stale count、oldest pending age ✅ |
| 19 | CI pin KnowGraphGo SHA | **PASS** | CI 使用 `ref: f0a1075`（特定 SHA），非浮動分支 ✅ |
| 20 | Cross-repository Digital Thread 測試通過 | **FAIL** | CI 中的 Cross-repository Integration Test 僅為 Python 內联 ID 驗證 + Go 單元測試。**缺少需求 §十七 要求的完整 E2E 測試**（Build CLI → 臨時 SQLite DB → 產生事件序列 → apply → 再 apply → query → 驗證冪等 + Digital Thread 路徑）。`tests/test_cross_repo_integration.py` 不存在。❌ |

**Gate 統計：PASS=18，PARTIAL=1，FAIL=1**

與前次相比：Item 13 從 PARTIAL 提升為 PASS（idx bug 已修復）。其餘不變。

---

## 核心需求檢查（任一未完成 → 滿足需求=NO → 總分最高 89）

| 核心需求 | 狀態 | 說明 |
|----------|------|------|
| Deterministic ID | ✅ PASS | Python/Go 均已實現 UUIDv5 確定性 ID |
| Relation Integrity | ✅ PASS | Go 端 adapter 正確實現，測試通過 |
| Idempotency | ✅ PASS | Go 端有重放測試，Python 端 opinion_id 已確定性 |
| Digital Thread | ❌ **FAIL** | 仍只有 schema 定義測試（`test_phase3d_digital_thread.py`），沒有真正的 E2E 路徑驗證 |
| Cross-language ID parity | 🟡 PARTIAL | Python 端測試通過（10 TestCases），CI 有內联驗證，但缺少 Go golden test 交叉比對 |
| Cross-repository integration | ❌ **FAIL** | 缺少需求 §十七 要求的完整 E2E Digital Thread 測試 |

---

## 前次 FAIL 項目修復檢查

### Item 13：Event Payload 來自真實 Domain Model（前次 PARTIAL → 本次 PASS）

**idx 變量 bug**：

✅ **已修復**。第 405 行已改為：
```python
for op_idx, opinion in enumerate(request.specialist_opinions):
```
使用 `op_idx` 替代原有的殘留 `idx` 變量。每個 opinion 的 ID 現在基於 `specialty:participant_id:op_idx` 生成，唯一且確定性。

**recommendation_service.py evidence_references**：

✅ 仍然正確。從 `response.get("recommendations", [])` 中提取。

### Item 20：Cross-repository Digital Thread 測試（前次 FAIL → 本次 FAIL）

❌ **未修復**。`tests/test_cross_repo_integration.py` 仍然不存在。

CI 中的 Cross-repository Integration Test（第 81-122 行）僅為 Python 端 ID 內联驗證（自驗，沒有與 Go 比對）。Cross-repository Digital Thread Test（第 124-139 行）僅運行了 Go 單元測試 `TestDuplicateReplay_Idempotent` 和 `TestRelationTargetIntegrity`，沒有實現需求 §十七 要求的完整端到端測試流程。

---

## 新增/已修復的關鍵改進（相對於前次）

本次返工在工作目錄（未提交）中包含了大量重要修復：

| 改進項 | 狀態 | 說明 |
|--------|------|------|
| mark_failed 設為 "failed" | ✅ | 從 `new_status = "pending"` 改為 `new_status = "failed"`，符合需求 §十四 |
| claim_pending 含 failed 狀態 | ✅ | `status.in_(["pending", "failed"])`，符合需求 §十四 |
| 三段式事務 | ✅ | Worker 實現 Claim→commit→External Work→Result→commit，不長時間持有 DB lock |
| stale processing 恢復 | ✅ | `release_stale()` 方法，將卡在 processing 超過 timeout 的事件重置為 pending |
| 非阻塞 async subprocess | ✅ | 使用 `asyncio.create_subprocess_exec()` 替代 `subprocess.run()`，含 timeout/kill |
| Status API 真實健康度 | ✅ | 結合 outbox 統計、CLI 可用性、stale count、oldest pending age，返回 operational/degraded/unavailable |
| Outbox Model 補充字段 | ✅ | 新增 correlation_id, causation_id, claim_token, occurred_at, processing_started_at, last_failed_at |
| CI pin KnowGraphGo SHA | ✅ | 從 `ref: master` 改為 `ref: f0a1075` |
| Explain Query 修正 | ✅ | `_build_explain_text()` 根據 entities/relations 建構可讀解釋，不把 Entity ID 當 Relation ID |

---

## 仍然存在的問題

### 問題 A：3 個測試仍然失敗（與前次相同，未修復）

| 測試 | 失敗原因 | 性質 |
|------|----------|------|
| `test_mark_failed` | 斷言 `evt.status == "pending" or evt.status == "dead_letter"`，但生產代碼 `mark_failed` 設置的是 `"failed"` | **測試代碼 bug** — 應改為 `assert evt.status in ("failed", "dead_letter")` |
| `test_worker_with_mock_client` | Worker 創建 `ClinicalGraphEvent` 時需要 `occurred_at` 字段，但測試 fixture 創建的事件沒有設置 `occurred_at` | **測試 fixture 缺少字段** — 應在 `repo.create()` 時提供 `occurred_at` |
| `test_worker_retry_on_failure` | 同上（`occurred_at` 缺失導致 Pydantic 驗證失敗，錯誤信息覆蓋了預期的 "test error"） | **測試 fixture 缺少字段** — 同上 |

**影響**：這 3 個測試在第一次評審（Round 0）時就已存在，經過 2 次返工仍未修復。這表明測試維護未被納入返工範圍。

### 問題 B：Cross-repository Digital Thread E2E 測試缺失（需求 §十七）

**核心缺失**：
- CI 中無 Build CLI → 臨時 SQLite Graph DB → 產生事件序列 → CLI apply → 再 apply → CLI query → 驗證冪等 + Digital Thread 的完整流程
- `tests/test_cross_repo_integration.py` 不存在
- 無法驗證跨倉庫整合是否正常工作

### 問題 C：測試覆蓋缺口仍然存在

| 需求 §十九 要求的測試 | 實現狀態 |
|----------------------|----------|
| Migration 022 upgrade/downgrade/re-upgrade | ❌ 無專用測試 |
| Concurrent worker claim test | ❌ 無 |
| Stale processing recovery | ❌ 無專用測試 |
| Recommendation/Decision/Consensus payload correctness | ❌ 無 |
| Patient thread real graph query | ❌ 無 |
| Explain real path（recommendation + consensus） | ❌ 無 |
| Restart recovery with graph projection | ❌ 無 |
| Full rebuild 冪等性（兩次 rebuild 比對） | ❌ 無（現有測試僅為 schema round-trip） |
| 跨語言 ID golden test 交叉比對 | ❌ 無 |

---

## 最終判定

Phase 3D Graph Correctness Hardening：**FAIL**
Phase 3D Accepted：**NO**
Ready for Treatment Plan：**NO**

### 判定依據

- 總評分 **62/100**，遠低於 95 分合格線
- 6 項核心需求中 2 項未完成（**Digital Thread**、**Cross-repository integration**），1 項 PARTIAL（**Cross-language ID parity**）
- Reviewer Gate 20 項中 1 項 FAIL（Item 20: Cross-repository Digital Thread 測試）、1 項 PARTIAL（Item 11: 缺少 Go golden test 交叉比對）
- 3 個測試仍然失敗，且經過 2 次返工均未修復
- 雖然本次返工修復了大量 P0 級別的生產代碼問題（idx bug、mark_failed 狀態、三段式事務、非阻塞 client、Status API 等），但核心測試驗證需求未滿足

### 必須修復的項目（優先級排序）

| 優先級 | 項目 | 說明 |
|--------|------|------|
| **P0** | 建立真正的 Cross-repository E2E Digital Thread 測試 | 按照需求 §十七，實現 Build CLI → 臨時 SQLite DB → 事件序列 → apply → 再 apply → query → 驗證冪等 + Digital Thread |
| **P0** | 修復 3 個測試失敗 | test_mark_failed（斷言改為 `in ("failed", "dead_letter")`）、test_worker_with_mock_client 和 test_worker_retry_on_failure（fixture 補充 occurred_at） |
| **P1** | 實現 Cross-language ID golden test 交叉比對 | Go 生成 golden output → Python 讀取並比對 |
| **P1** | 補充真正的 Full Rebuild 冪等性測試 | 兩次 rebuild 後比對 Entity/Relation 數量 |
| **P1** | 補充真正的 Digital Thread 路徑查詢測試 | 驗證 Patient→Recommendation→Decision→Consensus 的完整路徑 |

---

## 附：測試執行結果

```
57 個測試中：54 passed, 3 failed
```

| 測試套件 | 結果 |
|----------|------|
| test_phase3d_id_parity.py (10 tests) | ✅ 全部通過 |
| test_phase3d_digital_thread.py (5 tests) | ✅ 全部通過 |
| test_phase3d_rebuild_idempotent.py (6 tests) | ✅ 全部通過 |
| test_phase3d_async_client.py (6 tests) | ✅ 全部通過 |
| integration/test_phase3d_query_api.py (7 tests) | ✅ 全部通過 |
| unit/test_phase3d_event_schema.py (9 tests) | ✅ 全部通過 |
| unit/test_phase3d_outbox_repo.py (7 tests) | ❌ test_mark_failed FAIL |
| unit/test_phase3d_outbox_service.py (4 tests) | ✅ 全部通過 |
| unit/test_phase3d_rebuild.py (4 tests) | ✅ 全部通過 |
| unit/test_phase3d_worker.py (6 tests) | ❌ test_worker_with_mock_client + test_worker_retry_on_failure FAIL |

---

## 與前次評分對比

| 維度 | Round 2 (前次) | Round 3 (本次) | 變化 |
|------|---------------|---------------|------|
| 完整性 | 8/25 | 14/25 | ↑ +6（idx bug 修復、多項 P0 修復） |
| 正確性 | 15/25 | 16/25 | ↑ +1（核心邏輯修正確實） |
| 可維護性 | 20/25 | 20/25 | → 不變 |
| 測試與驗證 | 12/25 | 12/25 | → 不變（3 個測試仍失敗，覆蓋缺口仍在） |
| **總分** | **55/100** | **62/100** | **↑ +7** |
| Reviewer Gate PASS | 18/20 | 18/20 | → 不變（Item 13 PARTIAL→PASS，但 Item 11 仍為 PARTIAL） |
| 核心需求完成度 | 3/6 ✅ | 3/6 ✅ (+1 🟡) | → Idem（Item 11 從 PARTIAL 偏 PASS 方向，但仍缺少 golden test 交叉比對） |

本次返工在生產代碼層面修復了大量 P0 問題，但測試層面的問題（3 個測試失敗、核心測試缺失）完全未被觸及。這是阻礙通過評審的主要原因。
