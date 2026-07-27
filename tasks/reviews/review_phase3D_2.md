# Phase 3D Reviewer Report — 第2次返工評分

> 評審日期：2026-07-27  
> 評審者：Reviewer Agent  
> 評審範圍：Phase 3D Clinical Knowledge Graph Adapter（第2次返工後）

---

## 15 項 Reviewer Gate 檢查

| # | 檢查項目 | 狀態 | 說明 |
|---|---------|------|------|
| 1 | Postgres 是唯一 Source of Truth | ✅ PASS | Outbox 只在 Postgres，KnowGraphGo 為可重建的投影層 |
| 2 | Outbox 與 Domain 同 Transaction | ✅ PASS | Service 在 commit 前寫入 Outbox，同一 transaction |
| 3 | Graph failure 不影響 Domain Transaction | ✅ PASS | Worker 失敗只 mark_failed，不影響已提交 domain data |
| 4 | Projection 可重試 | ✅ PASS | GraphProjectionRetryPolicy：1min→5min→15min→1hr→6hr |
| 5 | Dead Letter 可查 | ✅ PASS | list_failed API 支援 failed/dead_letter 查詢 |
| 6 | 同 Event 重放不產生重複 Entity/Relation | ⚠️ PARTIAL | Python 側 event_id 唯一；Idempotent projection 依賴 KnowGraphGo adapter |
| 7 | Provenance 完整 | ✅ PASS | ClinicalGraphEvent 包含 event_id, actor_id, correlation_id 等 |
| 8 | Sensitive data 未投影 | ✅ PASS | SENSITIVE_FIELDS 檢測 + 最小 payload |
| 9 | Patient Digital Thread 可查 | ✅ PASS | GET /api/v1/clinical-graph/patient/{id}/thread |
| 10 | Recommendation Explain 可查 | ✅ PASS | GET /api/v1/clinical-graph/recommendation/{id}/explain |
| 11 | Consensus Explain 可查 | ✅ PASS | GET /api/v1/clinical-graph/consensus/{id}/explain |
| 12 | Graph 可完整重建 | ✅ PASS | CLI `clinical_graph rebuild` 已實現 |
| 13 | Python 未直接嵌入 Go Library | ✅ PASS | subprocess.run 呼叫 knowgraph CLI |
| 14 | KnowGraphGo Adapter 測試全綠 | ⚠️ 無法本地驗證 | CI 中有 KnowGraphGo 測試步驟 |
| 15 | Cross-repository Integration | ⚠️ 無法本地驗證 | CI 中有 cross-repository 步驟 |

---

## 嚴重缺陷

### 🔴 CRITICAL：`require_role` 函數不存在

- **位置**：`src/backend/api/v1/clinical_graph.py:88-90`
- **問題描述**：
  ```python
  from src.backend.auth import require_role    # ← ImportError！！！
  require_role(["admin", "researcher"])(user)  # ← 程式碼不會執行到這裡
  ```
- `src/backend/auth/__init__.py` 和 `src/backend/auth/dependencies.py` 中**均未定義 `require_role`**。
- 這導致 `POST /api/v1/clinical-graph/retry/{event_id}` endpoint 在運行時拋出 `ImportError`，無法使用。
- 違反需求第二十節（管理 API 必須受 Auth/Role 保護）。
- 第1次返工聲稱「已加上 require_role」，但實際並未完成。

### 🟡 MODERATE：缺少「View in Knowledge Graph」連結

- 需求第二十四節要求：
  > 在 Recommendation Page、Clinical Decision Page、Tumor Board Consensus Page 新增「View in Knowledge Graph」連結
- 前端程式碼中**未找到**任何「View in Knowledge Graph」或類似連結/按鈕。

---

## 測試結果

- Phase 3D 單元測試 5 個檔案（event_schema, outbox_repo, outbox_service, rebuild, worker）— 存在
- Phase 3D 整合測試 1 個檔案（query_api）— 存在
- KnowGraphGo 測試 — CI 中有但本地無法執行
- `go build ./...` — 通過（依賴 KnowGraphGo）

---

## 評分

### 檢查清單

| 項目 | 結果 | 說明 |
|------|------|------|
| 是否可執行 | **NO** | `require_role` 缺失導致 retry endpoint crash |
| 是否有錯誤 | **NO（有錯誤）** | `require_role` ImportError |
| 是否滿足需求條列 | **NO** | require_role 缺失 + 前端連結缺失 |
| 是否有測試或滿足審美 | **YES** | 有 Phase 3D 測試，CI 有整合測試 |

### 細項評分（每項 0-25）

| 項目 | 分數 | 上限說明 |
|------|------|---------|
| 完整性 | **8/10** | 需求未完全滿足，上限 10 分。多數需求已完成，但缺少 require_role 和前端連結 |
| 正確性 | **5/10** | 有錯誤，上限 10 分。require_role 缺失導致運行時錯誤 |
| 可維護性 | **18/25** | 程式碼結構合理，但 worker 直接 commit、API inline import 可改進 |
| 測試與驗證 | **18/25** | 有基本測試，但缺少 Digital Thread Integration、Restart Recovery 等關鍵測試 |

### 總分

**8 + 5 + 18 + 18 = 49 分**（< 95，不合格）

---

## 最終判定

| 項目 | 結果 |
|------|------|
| Phase 3D Clinical Knowledge Graph Adapter | **FAIL** |
| Accepted | **NO** |
| Ready for ChatGPT GitHub Review | **NO** |
| Ready for Treatment Plan Phase | **NO** |

### 必須修復才能重新評分

1. **`require_role` 缺失**：在 `src/backend/auth/dependencies.py` 中實作 `require_role` 函數，或在 `src/backend/auth/__init__.py` 中匯出已存在的函數，並確保 `POST /api/v1/clinical-graph/retry/{event_id}` 正確使用。
2. **「View in Knowledge Graph」連結**：在 Recommendation、Clinical Decision、Tumor Board Consensus 前端頁面中加入連結。

修正上述兩項後，完整性和正確性可望分別提升至 9/10 和 9/10（上限內），預估分數：
9 + 9 + 18 + 18 = 54，仍低於 95 但高於 90（若其他項目未再發現新問題）。需要更多測試和修復才能達到 ≥95。
