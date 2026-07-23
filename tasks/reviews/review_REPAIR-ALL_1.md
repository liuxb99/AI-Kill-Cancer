# Phase 2 修復交付評分報告

**評審人**: REVIEWER 子代理  
**評審日期**: 2026-07-23  
**評審範圍**: REPAIR-1 ~ REPAIR-6 六大修復交付  
**評審檔案**: 依據 tasks/review_REPAIR-ALL_1.md 要求產出  

---

## 檢查清單

| 檢查項 | 結果 | 說明 |
|--------|------|------|
| **是否可執行** | **YES** | 六大修復均已完成檔案修改/新增，測試全部通過 |
| **是否有錯誤** | **NO（有錯誤）** | 見下方細項分析，存在多處實作與計劃的偏差 |
| **是否滿足需求條列** | **NO** | REPAIR-2 未完整實作計劃要求（collect_by_variant 缺少 source_statuses、未記錄所有來源狀態）；REPAIR-6 缺少 API proxy rewrites |
| **是否有測試或滿足審美** | **YES** | 測試覆蓋充分，代碼風格與專案一致 |

---

## 細項評分

### 1. 完整性（需求 NO → 最高 10 分）

**得分: 8 / 10**

扣分原因：

| REPAIR | 問題描述 | 扣分 |
|--------|---------|------|
| REPAIR-2 | **collect_by_variant() 未實作 source_statuses**：計劃明確要求「在 collect() 和 collect_by_variant() 中」記錄來源狀態，但實際僅在 collect() 中實作；collect_by_variant() 仍只做 logger.warning | -2 |
| REPAIR-6 | **缺少 API proxy rewrites**：計劃要求「API 請求通過 rewrites 正確代理到後端」，但實際 vercel.json 的 rewrites 僅為 SPA catch-all（`/(.*) → /index.html`），無 `/api/*` 代理 | -2 |
| REPAIR-4 | **session.py 未增加 rollback 處理**：計劃 Step 4.2 要求「在 get_db() 中增加異常時的 rollback 處理」，實際未修改 session.py | -1 |
| REPAIR-2 | **未記錄 AVAILABLE/ERROR 狀態**：計劃要求對每個來源記錄狀態，但實際只記錄了 AUTHORIZATION_REQUIRED 的三個授權來源 | -2 |

> 基礎 15 分扣至 8 分（因需求 NO 強制上限 10 分）

### 2. 正確性（有錯誤 NO → 最高 10 分）

**得分: 6 / 10**

扣分原因：

| 錯誤類型 | 問題 | 扣分 |
|---------|------|------|
| **實作偏差** | REPAIR-2: collect_by_variant 沒有 source_statuses，導致部分收集路徑無法向下游傳遞來源狀態 | -4 |
| **實作偏差** | REPAIR-6: rewrites 只做 SPA fallback，無 API 代理，後端 API 在 Vercel 上會 404 | -3 |
| **缺少修復** | REPAIR-4: 未修復 session.py 的 rollback 處理（計劃指出「無顯式事務回滾處理」） | -2 |

> 基礎 15 分扣至 6 分（因有錯誤強制上限 10 分）

> 無編譯錯誤或運行時崩潰，所有測試通過。扣分聚焦於實作與計劃的偏差影響了功能正確性。

### 3. 可維護性

**得分: 20 / 25**

優點：
- 代碼結構清晰，型別提示完整（type hints, docstrings）
- SourceStatus 和 SourceStatusType 的設計良好，枚舉值命名規範
- 測試程式碼整潔，使用 pytest fixtures 模式
- 遷移測試的靜態審計（AST 分析）設計巧妙

扣分原因：

| 問題 | 描述 | 扣分 |
|------|------|------|
| 未使用的 timestamp 字段 | SourceStatus 的 `timestamp` 字段在建構時傳入，但 EvidenceBundle 已有 `retrieved_at`，二者存在重疊 | -2 |
| collect_by_variant 不一致 | collect() 與 collect_by_variant() 對授權來源的處理方式不同（一個有 source_statuses，一個沒有），增加維護負擔 | -2 |
| 授權來源警告重複 | collector.py 中 `_AUTH_SOURCES` 的 logger.warning 在 collect() 和 collect_by_variant() 中重複出現，未提取為共用方法 | -1 |

### 4. 測試與驗證

**得分: 24 / 25**

優點：
- 測試總數豐富（unit 209 + auth 53 + migration 7 + persistence 6 + evidence 53 = 328）
- 所有測試通過 ✅
- TestDecisionNodePersistence 使用真實 SQLite 進行 session reload 測試，驗證力強
- TestMigration016StaticAudit 的 AST 分析靜態審計是亮點
- TestClinicalEndpointAuthorization 完整覆蓋 6 類端點 × 4 種情況 = 24 個授權場景
- TestRouteSecurityCoverage 動態掃描所有 v1 路由

扣分原因：

| 問題 | 描述 | 扣分 |
|------|------|------|
| 無 SourceStatus 模型的獨立測試 | 沒有 TestSourceStatus 或 TestSourceStatusType 類；僅透過 collector 的整合測試間接驗證 | -1 |

---

## 總分

| 項目 | 得分 | 權重範圍 |
|------|------|---------|
| 完整性 | 8 | 0-10（需求 NO 上限） |
| 正確性 | 6 | 0-10（有錯誤上限） |
| 可維護性 | 20 | 0-25 |
| 測試與驗證 | 24 | 0-25 |
| **總分** | **58** | **0-100** |

**結論: 不合格（< 90）** ❌

---

## 關鍵問題摘要

### 必須修復才能合格

1. **REPAIR-2: collect_by_variant() missing source_statuses**  
   `collect_by_variant()` 應與 `collect()` 一致地建立 SourceStatus 列表。

2. **REPAIR-2: 只記錄 AUTHORIZATION_REQUIRED，未記錄 AVAILABLE/ERROR**  
   計劃要求對所有來源記錄狀態。至少應記錄 AVAILABLE 或 ERROR。

3. **REPAIR-6: vercel.json 缺少 API proxy rewrites**  
   SPA rewrites 無法代理後端 API 請求，需要在 rewrites 中增加 `/api/(.*)` → 後端 URL 的規則。

### 建議修復（非強制）

4. **REPAIR-2: SourceStatus 模型補充 items_count 字段**（與計劃一致）
5. **REPAIR-4: session.py 增加 rollback 處理**（計劃要求的修復但未執行）
6. **REPAIR-2: 新增 SourceStatus/SourceStatusType 的單元測試類**
7. **SourceStatus 的 timestamp 與 EvidenceBundle.retrieved_at 去重**

---

## 各項 REPAIR 詳細評估

### REPAIR-1: Phase 2 Scope Cleanup — ✅ 通過
- config/ 目錄無 .go 檔案（僅 4 個 .md 檔案）
- git grep 確認無 Go 相關殘留引用
- 無需代碼修改，純檢查 ✅

### REPAIR-2: Evidence 狀態模型改進 — ⚠️ 部分通過
- SourceStatusType 枚舉 ✅
- SourceStatus 模型 ✅（但缺少 items_count）
- EvidenceBundle.source_statuses 字段 ✅
- collect() 中為 NCCN/ESMO/OncoKB 建立狀態 ✅
- **collect_by_variant() 中未建立狀態 ❌**
- **未記錄 AVAILABLE/ERROR 狀態 ❌**
- **缺少 items_count 字段 ❌**

### REPAIR-3: Authorization Audit — ✅ 通過
- 所有 v1 端點已有授權裝飾器（審計結果）
- TestClinicalEndpointAuthorization 覆蓋 24 場景 ✅
- TestRoleBoundary + TestTokenValidation ✅
- TestCaseACLModel + TestGlobalRBAC ✅
- TestRouteSecurityCoverage 動態掃描 ✅
- **未按計劃實作靜態 TestAuthorizationMatrix（但動態掃描可替代）** ⚠️

### REPAIR-4: Database Persistence Verification — ✅ 通過（但缺少 session.py 修復）
- TestDecisionNodePersistence 6 測試 ✅
- 真實 SQLite session reload 測試 ✅
- commit/refresh 流程正確 ✅
- **session.py 未增加 rollback 處理 ❌**

### REPAIR-5: Migration Verification — ✅ 通過
- upgrade/downgrade 靜態審計 7 測試 ✅
- upgrade → downgrade → upgrade 循環測試 ✅
- 4 表創建/刪除對稱 ✅
- AST 靜態分析驗證表創建/刪除 ✅

### REPAIR-6: Vercel Deployment Repair — ⚠️ 部分通過
- rootDirectory/buildCommand/outputDirectory/nodeVersion 修正 ✅
- SPA rewrites 新增 ✅
- **缺少 API proxy rewrites (/api/*) ❌**
- 計劃明確要求「API 請求通過 rewrites 正確代理到後端」但未實作
