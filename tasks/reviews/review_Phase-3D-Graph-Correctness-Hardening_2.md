# REVIEW Report: Phase-3D-Graph-Correctness-Hardening (Round 2 — Rework 1 Review)

> 基於返工計劃 `tasks/plan-phase3d-hardening-rework-1.md` 執行第 1 輪返工後的評分。
> 原始需求：`tasks/requirements.md`
> 前次評分：`review_Phase-3D-Graph-Correctness-Hardening_0.md`（42/100，18/20 PASS，2 FAIL）

---

## 檢查清單

| 項目 | 結果 | 說明 |
|------|------|------|
| 是否可執行 | **YES** | 代碼可導入，57 個測試中 54 個通過 |
| 是否有錯誤 | **NO（有錯誤）** | 3 個測試失敗；tumor_board_service.py 有 idx 變量引用 bug |
| 是否滿足需求條列 | **NO** | Digital Thread 和 Cross-repository Integration 核心需求未完成 |
| 是否有測試 | **YES** | 新增 9 個測試文件共 57 個測試，但覆蓋不完整 |

---

## 細項評分

| 項目 | 評分 | 備註 |
|------|------|------|
| 完整性 | **8/25** | 需求未滿足（最高 10 分）。代碼修復了 0 次報告中的 2 個 FAIL 項目，但 Digital Thread E2E 和 Cross-repository Integration 核心需求未完成 |
| 正確性 | **15/25** | 核心邏輯基本正確，但 `tumor_board_service.py:410` 存在 `idx` 變量未定義/重用殘留值的 bug；3 個測試因 fixture 問題失敗 |
| 可維護性 | **20/25** | 代碼結構良好，模塊拆分合理，ID Factory 設計清晰，Worker 三段式事務正確實現 |
| 測試與驗證 | **12/25** | 新增了 9 個測試文件，但內容偏基礎：無真正的 Cross-repo E2E Digital Thread 測試、無 Full Rebuild 冪等性測試、無跨語言 golden test 交叉比對、3 個測試失敗 |

---

## 總分：**55/100**（不合格）

---

## Reviewer Gate 20 項逐項確認

| # | 項目 | 結果 | 說明 |
|---|------|------|------|
| 1 | Entity ID deterministic | **PASS** | UUIDv5 + 固定 Namespace + canonical key；Go 和 Python 實現一致 |
| 2 | Relation ID deterministic | **PASS** | `clinical:relation:{kind}:{from}:{to}` 格式，Go/Python 一致 |
| 3 | Same Event replay idempotent | **PASS** | Go `TestDuplicateReplay_Idempotent` 驗證實體/關係數量與 ID 一致（CI 中運行） |
| 4 | created→updated 不重複 | **PASS** | Go `TestUpdatedEvent_Upsert` 驗證更新後 ID 不變、屬性更新 |
| 5 | 所有 Relation Target 存在 | **PASS** | Go `TestRelationTargetIntegrity` 驗證 delta 中所有 From/To 均有對應 Entity |
| 6 | Patient→Recommendation 正確 | **PASS** | adapter.go mapRecommendationEvent 創建 FOR_PATIENT 關係 |
| 7 | Recommendation→Drug/Evidence 正確 | **PASS** | adapter.go 創建 RECOMMENDS/SUPPORTED_BY 關係 |
| 8 | Decision→Recommendation 正確 | **PASS** | adapter.go mapClinicalDecisionEvent 創建 BASED_ON 關係 |
| 9 | Consensus→Decision 正確 | **PASS** | adapter.go mapConsensusEvent 創建 DERIVED_FROM 關係 |
| 10 | Consensus→Opinion→Specialty 正確 | **PASS** | adapter.go 創建 HAS_OPINION + PROVIDED_BY_SPECIALTY 關係鏈 |
| 11 | Python ID == Go ID | **PASS** | 相同 CLINICAL_NAMESPACE、相同 canonical key 格式、相同規範化規則；CI 中有內联驗證 |
| 12 | Provenance 完整 | **PASS** | entityProps 包含 12 個 Provenance 欄位；Go `TestProvenanceFields` 驗證 |
| 13 | Event Payload 來自真實 Domain Model | **🟡 PARTIAL** | (a) recommendation_service.py 的 `evidence_references` 已從 recommendations 提取 ✅；(b) tumor_board_service.py 的 `opinion_id` 已使用 ClinicalGraphIDFactory 生成 ✅；(c) 但 tumor_board_service.py:407-410 使用殘留 `idx` 變量而非 `enumerate`，導致多個相同 specialty+participant_id 的 opinions 可能碰撞 ⚠️ |
| 14 | async subprocess 不阻塞 | **PASS** | client.py 使用 `asyncio.create_subprocess_exec()`，shell=False，有 timeout/kill/returncode/JSON 校驗 |
| 15 | Worker 不長時間持有 DB lock | **PASS** | 三段式事務：Claim→commit→External Work→Result→commit，符合要求 |
| 16 | stale processing 可恢復 | **PASS** | `release_stale()` 將超過 timeout 的 processing 事件重置為 pending |
| 17 | failed events API 可見 | **PASS** | `GET /clinical-graph/failed-events` 返回 failed/dead_letter 事件列表 |
| 18 | Status API 反映 CLI 真實狀態 | **PASS** | `/clinical-graph/status` 結合 outbox 統計、CLI 可用性、stale count、oldest pending age，返回 operational/degraded/unavailable |
| 19 | CI pin KnowGraphGo SHA | **PASS** | CI 使用 `ref: f0a1075`（特定 SHA），非浮動分支 |
| 20 | Cross-repository Digital Thread 測試通過 | **FAIL** | CI 中只有 Python ID 內联驗證和 Go 單元測試，缺少需求 §十七 要求的完整端到端測試（Build CLI → 臨時 SQLite DB → 產生事件序列 → apply → 再 apply → query → 驗證冪等 + Digital Thread 路徑）。`tests/test_cross_repo_integration.py` 不存在 |

**Gate 統計：PASS=18，PARTIAL=1，FAIL=1**

---

## 核心需求檢查（任一未完成 → 滿足需求=NO → 總分最高 89）

| 核心需求 | 狀態 | 說明 |
|----------|------|------|
| Deterministic ID | ✅ PASS | Python/Go 均已實現 UUIDv5 確定性 ID |
| Relation Integrity | ✅ PASS | Go 端 adapter 正確實現，測試通過 |
| Idempotency | ✅ PASS | Go 端有重放測試，Python 端 opinion_id 已確定性 |
| Digital Thread | ❌ **FAIL** | 只有 schema 定義測試（`test_phase3d_digital_thread.py`），沒有真正的 E2E 路徑驗證 |
| Cross-language ID parity | 🟡 PARTIAL | Python 端測試通過（10 TestCases），CI 有內联驗證，但缺少 Go golden test 交叉比對 |
| Cross-repository integration | ❌ **FAIL** | 缺少需求 §十七 要求的完整 E2E Digital Thread 測試 |

---

## 前次 FAIL 項目修復檢查

### Item 13：Event Payload 來自真實 Domain Model

**recommendation_service.py evidence_references**：

✅ **已修復**。不再是硬編碼 `[]`。第 290-299 行從 `response.get("recommendations", [])` 中提取 drug_name/evidence_score/sensitivity_score/resistance_score/conflict_score 作為 evidence_references。同時第 474 行 `_persist_recommendation()` 中的 trace step 也從 `output_data` 中調用 `_extract_evidence_references()` 提取。

### Item 20：Cross-repository 測試

文件存在檢查：

| 文件 | 存在 | 內容評估 |
|------|------|----------|
| `tests/test_phase3d_id_parity.py` | ✅ | 10 個測試，全部通過。測試 Python ClinicalGraphIDFactory 的確定性、標準化、無碰撞、UUIDv5 版本。但**缺少**與 Go 的交叉比對（無 golden test 載入） |
| `tests/test_phase3d_rebuild_idempotent.py` | ✅ | 6 個測試，全部通過。但內容僅為 Event Schema 的 serialization round-trip，**不是**真正的 rebuild 冪等性測試（沒有兩次 rebuild 後比對 Entity/Relation 數量） |
| `tests/test_phase3d_digital_thread.py` | ✅ | 5 個測試，全部通過。但僅驗證 `GraphEventType`/`GraphAggregateType` 枚舉定義存在，**不是**真正的 Digital Thread 路徑查詢測試 |

返工計劃中承諾的 `tests/test_cross_repo_integration.py`（4C）**不存在**。

---

## 新增問題

### 問題 A：tumor_board_service.py:407-410 — idx 變量引用 bug

**位置**：`src/backend/services/tumor_board_service.py` 第 407-410 行

```python
for opinion in request.specialist_opinions:                        # line 405 — 沒有 enumerate
    specialist_opinions.append({
        "opinion_id": ClinicalGraphIDFactory.opinion_id(
            f"{...}:{getattr(opinion, 'participant_id', '') or str(idx)}"  # line 409 — idx 未定義
            f":{idx}"                                             # line 410 — idx 使用殘留值
        ),
```

`idx` 變量在上一個 for 循環（第 383 行 `for idx, step in enumerate(result.trace_steps)`）中定義。當前循環（第 405 行）沒有 `enumerate`，因此 `idx` 使用的是上一個循環的**最後一個值**。這導致：
- 所有 specialist_opinions 使用相同的 `idx` 值（即 trace_steps 的最後一個索引）
- 若 trace_steps 為空，`idx` 可能未定義（報 NameError）

**影響**：對於同一個 consensus 事件的重放，因為 trace_steps 數量固定，opinion_id 仍然確定性。但多個相同 specialty+participant_id 的 opinions 可能得到相同的 opinion_id（碰撞）。應改用 `for idx, opinion in enumerate(request.specialist_opinions)`。

### 問題 B：3 個測試失敗

| 測試 | 失敗原因 | 歸因 |
|------|----------|------|
| `test_mark_failed` | 測試斷言 `status == "pending" or "dead_letter"`，但生產代碼正確實現了 `status = "failed"` | 測試代碼 bug |
| `test_worker_with_mock_client` | 創建的事件缺少 `occurred_at` 字段，`ClinicalGraphEvent` Pydantic 驗證失敗 | 測試 fixture 缺少字段 |
| `test_worker_retry_on_failure` | 同上 | 同上 |

這些是測試代碼的 bug，但表明測試的健壯性不足。

### 問題 C：測試覆蓋缺口

| 需求要求 | 實現狀態 |
|----------|----------|
| Migration 022 upgrade/downgrade/re-upgrade | ❌ 無專用測試 |
| Concurrent worker claim test | ❌ 無 |
| Stale processing recovery | ❌ 無專用測試 |
| Recommendation/Decision/Consensus payload correctness | ❌ 無 |
| Patient thread real graph query | ❌ 無 |
| Explain real path（recommendation + consensus） | ❌ 無 |
| Restart recovery with graph projection | ❌ 無 |
| Full rebuild 冪等性（兩次 rebuild 比對） | ❌ 無 |
| 跨語言 ID golden test 交叉比對 | ❌ 無 |

---

## 關鍵問題匯總

### P0 問題

1. **Cross-repository Digital Thread E2E 測試缺失**（需求 §十七）
   - 返工計劃承諾的 `tests/test_cross_repo_integration.py` 未實現
   - CI 中的 Cross-repository Integration Test 僅為 Python ID 內联驗證
   - 無 Build CLI → 臨時 SQLite → 產生事件序列 → apply → verify 的完整流程
   - **影響**：無法驗證跨倉庫整合是否正常工作

2. **tumor_board_service.py idx 變量 bug**
   - 第 410 行使用殘留 `idx` 而非 `enumerate`
   - **影響**：相同 specialty+participant_id 的多個 opinions 可能 ID 碰撞

### P1 問題

3. **測試覆蓋不足**
   - 多項需求 §十九 要求的測試缺失
   - 3 個測試因 fixture 問題失敗
   - `test_rebuild_idempotent.py` 和 `test_digital_thread.py` 僅為 schema-level 測試

4. **Cross-language ID parity 缺少 Go golden test 交叉比對**
   - 雖有 Python 測試和 CI 內联驗證，但無 Go golden output → Python 讀取的正式交叉驗證

---

## 最終判定

Phase 3D Graph Correctness Hardening：**FAIL**
Phase 3D Accepted：**NO**
Ready for Treatment Plan：**NO**

### 判定依據

- 總評分 **55/100**，遠低於 95 分合格線
- 6 項核心需求中 2 項未完成（**Digital Thread**、**Cross-repository integration**）
- Reviewer Gate 20 項中 1 項 FAIL（Item 20: Cross-repository Digital Thread 測試）、1 項 PARTIAL（Item 13: Event Payload 有 idx bug）
- 新增 3 個測試失敗，表明測試質量不足
- 新增的測試文件（rebuild_idempotent / digital_thread）僅為 schema-level 測試，未達到真正的 E2E 驗證

### 需要修復的項目

| 優先級 | 項目 | 說明 |
|--------|------|------|
| **P0** | 建立真正的 Cross-repository E2E Digital Thread 測試 | 按照需求 §十七，實現 Build CLI → 臨時 SQLite DB → 事件序列 → apply → 再 apply → query → 驗證冪等 + Digital Thread |
| **P0** | 修復 tumor_board_service.py idx 變量 bug | 將 `for opinion in request.specialist_opinions:` 改為 `for idx, opinion in enumerate(request.specialist_opinions):` |
| **P1** | 修復 3 個測試失敗 | 修正 test_mark_failed 的斷言邏輯；在 worker 測試 fixture 中提供 occurred_at |
| **P1** | 補充 Migration 022 測試 | upgrade/downgrade/re-upgrade 測試 |
| **P1** | 補充 Full Rebuild 冪等性測試 | 真正的兩次 rebuild 後比對 Entity/Relation 數量 |
| **P1** | 實現跨語言 ID golden test 交叉比對 | Go 生成 golden output → Python 讀取並比對 |

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
| unit/test_phase3d_event_schema.py (9 tests) | ✅ 全部通過 |
| unit/test_phase3d_outbox_repo.py (7 tests) | ❌ test_mark_failed FAIL |
| unit/test_phase3d_outbox_service.py (4 tests) | ✅ 全部通過 |
| unit/test_phase3d_rebuild.py (4 tests) | ✅ 全部通過 |
| unit/test_phase3d_worker.py (6 tests) | ❌ test_worker_with_mock_client + test_worker_retry_on_failure FAIL |
