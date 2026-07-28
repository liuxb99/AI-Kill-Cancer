# Architecture Review 需求回歸檢查報告

> **檢查日期**：2025-01  
> **對照文件**：`tasks/requirements.md`（原始需求） → `tasks/reviews/architecture_review.md`（交付報告）  
> **判定標準**：全部 PASS → ✅ 可進入 Step 7 REVIEWER；任一 FAIL/PARTIAL → ❌ 繼續返工  

---

## 總評判定

| 結果 | 說明 |
|:----:|------|
| **✅ 全部 PASS** | 26 項檢查項目全數通過，3 項補充（§13 Trace 對比表、§14 Tests 逐類審查表、§10.5+§10.6 Domain State/Version）完整準確 |

---

## 第一部分：13 項 Review 項目

### 1. Domain Architecture Review — Entity/Aggregate/ValueObject/State/Version + Domain 依賴

| 需求 | 報告位置 | 判定 | 依據 |
|------|---------|:----:|------|
| 逐一檢查 Entity/Aggregate/ValueObject/State/Version 是否一致設計 | §10.2 逐檔案審查表（26 個檔案完整列出） | ✅ PASS | 每檔案列出類別、分類、ID、ORM 依賴、API 混入、建議 |
| 檢查 Domain 是否有 SQL/API/Session/HTTP 依賴 | §10.3 Domain 外部依賴審計 | ✅ PASS | 逐類掃描：無 SQL/API/Session/HTTP，但全部有 ORM 依賴 |
| 全部列出 | §10.2 完整 26 檔案表格 | ✅ PASS | |
| **補充：Domain State/Version 檢查** | **§10.5 + §10.6（新增）** | **✅ PASS** | **逐檔案列出 version 欄位，含關鍵發現（僅 TreatmentPlan 有完整版本控制，其餘無樂觀鎖）** |

### 2. Repository Layer Review — commit/rollback/flush + Business Logic

| 需求 | 報告位置 | 判定 | 依據 |
|------|---------|:----:|------|
| 確認 Repository 不得有 commit/rollback/flush | §3 P0-03（`BaseRepository` 第 29/73/82 行預設 `commit()`） | ✅ PASS | 明確指出 BaseRepository 預設 commit 行為導致事務邊界下沉 |
| 確認 Repository 不得有 Business Logic | §3 P0-04（`clinical_graph_outbox_repo.py` 全檔案混入業務邏輯） | ✅ PASS | 指出 CRUD 與業務邏輯未分離 |
| 全部列出 | §12.1.1 列出所有 Repository 的自訂查詢模式 | ✅ PASS | 20+ Repository 逐一列出重複 SQL 模式 |

### 3. Service Layer Review — Transaction Boundary

| 需求 | 報告位置 | 判定 | 依據 |
|------|---------|:----:|------|
| 確認 Transaction Boundary 只有在 Service 層存在 | §3 P0-03（事務邊界下沉到 Repository）、§6 R-H3（統一事務策略） | ✅ PASS | |
| 確認 Engine/Repository 不得開 transaction | §3 P0-03（BaseRepository 預設 commit）、§3 P2-04（手動 try/commit 重複模式） | ✅ PASS | |
| 全部列出 | §3 P0-03、P2-04；§6 R-H3、R-H4 | ✅ PASS | |

### 4. Engine Layer Review — Pure Function + 禁止外部依賴

| 需求 | 報告位置 | 判定 | 依據 |
|------|---------|:----:|------|
| 確認 Engine 是否為 Pure Function | §3 P1-01（`RecommendationEngine.run()` I/O 副作用，482-715 行） | ✅ PASS | |
| 確認 Engine 不得有 DB/API/Repository/Session 依賴 | §1 評語（Engine 層協調職責清晰）、§6 R-H7（將 I/O 和狀態管理移到呼叫方） | ✅ PASS | |
| 全部列出 | §3 P1-01、§6 R-H7、§3 P2-08（ClinicalDecisionEngine 無 Trace） | ✅ PASS | |

### 5. Migration Review — Upgrade/Downgrade/Re-upgrade + SQLite/Postgres

| 需求 | 報告位置 | 判定 | 依據 |
|------|---------|:----:|------|
| 檢查所有 Migration 的 Upgrade→Downgrade→Re-upgrade 是否一致 | §3 P1-09（015/022/025 不一致、不冪等）、§6 R-L6（修正不冪等問題） | ✅ PASS | |
| 檢查 SQLite 與 Postgres 是否完全一致 | §14.6 Migration 測試表、§14.7 Postgres 測試表 | ✅ PASS | 025 PG 完整循環測試 + Schema 比較 + Trace Constraint 測試 |
| 全部列出 | §14.6 + §14.7 完整表格 | ✅ PASS | |

### 6. API Layer Review — HTTP Status/Error/Validation

| 需求 | 報告位置 | 判定 | 依據 |
|------|---------|:----:|------|
| 確認所有 GET/POST/PATCH/DELETE 的 HTTP Status/Error/Validation 是否一致 | §3 P1-07（三種 Error 格式）、P1-08（POST 返回 200 非 201） | ✅ PASS | |
| 全部列出 | §6 R-M6（統一 Error Schema）、R-L7（統一 HTTP Status）、R-L8（409 Conflict） | ✅ PASS | |

### 7. Digital Thread Review — Event→Outbox→Projection→KnowGraphGo

| 需求 | 報告位置 | 判定 | 依據 |
|------|---------|:----:|------|
| 確認 Patient/Recommendation/Decision/Consensus/TreatmentPlan 的 Event→Outbox→Projection→KnowGraphGo 是否一致 | §3 P1-06（Patient Outbox 事件完全缺失）、§7 RSK-04（Patient 永不投射到圖譜） | ✅ PASS | |
| 全部列出 | §3 P0-04、P1-06、§6 R-M9、§7 RSK-04 | ✅ PASS | |

### 8. Trace Review — trace_id/step_order/step_name/input/output/created_at

| 需求 | 報告位置 | 判定 | 依據 |
|------|---------|:----:|------|
| 確認所有 Calculation Trace 的 trace_id/step_order/step_name/input/output/created_at 是否一致 | **§13 Trace 字段一致性對比表（新增）** | ✅ PASS | 完整盤點 4 套 Trace 系統，13 個字段維度交叉比對 |
| 全部列出 | §13.2 字段級一致性對比表（4 套 × 11 維度） | ✅ PASS | 每字段逐一標註 ❌/⚠️/✅ |

### 9. Graph Adapter Review — Projection/Relation/Stub/Provenance + 無 Duplicate Mapping

| 需求 | 報告位置 | 判定 | 依據 |
|------|---------|:----:|------|
| 確認所有 Projection/Relation/Stub/Provenance 是否一致 | §5 Duplicate Code（Patient/Evidence Stub 重複）、§3 P0-06（buildProvenance 硬編碼） | ✅ PASS | |
| 確認不得有 Duplicate Mapping | §5.1-5.5 詳細列出 5 種重複模式（Patient Stub ×4、Evidence Stub ×4、ID 去重 ×3、Data Loading ×2、Provenance ×N） | ✅ PASS | |
| 全部列出 | §5 完整 5 子節逐一列出 | ✅ PASS | |

### 10. Tests Coverage Review — 8 類別

| 需求 | 報告位置 | 判定 | 依據 |
|------|---------|:----:|------|
| 確認 Coverage 是否缺少：Engine/Repository/Service/API/Restart/Migration/Postgres/Graph | **§14 Tests Coverage 8 類別逐類審查表（新增）** | ✅ PASS | |
| 全部列出 | §14.1~§14.8 逐一表格 + §14.9 總結 | ✅ PASS | 每類別含測試標的、檔案、數量、覆蓋範圍、缺失案例 |

### 11. Dead Code Analysis — Unused/TODO/FIXME/Deprecated/Duplicate/Copy Paste

| 需求 | 報告位置 | 判定 | 依據 |
|------|---------|:----:|------|
| 找出 Unused/TODO/FIXME/Deprecated/Duplicate/Copy Paste | §11 Dead Code Analysis 完整 7 子節 | ✅ PASS | |
| 全部列出 | §11.2~§11.6 逐一掃描 src/tests/migrations/KnowGraphGo | ✅ PASS | |
| 不得直接刪除 | 報告僅列出，無刪除操作 | ✅ PASS | |

### 12. Architecture Smell Analysis — God Service/Long Function/Circular Dependency/Duplicated Logic/SQL/Validation

| 需求 | 報告位置 | 判定 | 依據 |
|------|---------|:----:|------|
| 找出 God Service/Long Function/Circular Dependency/Duplicated Logic/Duplicated SQL/Duplicated Validation | §12 Architecture Smell 完整 3 子節 + §4 Code Smell 完整列表 | ✅ PASS | |
| 全部列出 | §12.1.1 重複 SQL（20+ 檔案）、§12.2 重複 Validation（Adapter/API/Agent 三層）、§4 21 項 Code Smell | ✅ PASS | |

### 13. Refactor Candidate Analysis — High/Medium/Low

| 需求 | 報告位置 | 判定 | 依據 |
|------|---------|:----:|------|
| 列出 High/Medium/Low 三個等級 | §6 Refactor List 完整三個等級 | ✅ PASS | |
| 全部列出 | R-H1~R-H7（7 項 HIGH）、R-M1~R-M10（10 項 MEDIUM）、R-L1~R-L10（10 項 LOW） | ✅ PASS | 每項含 ID、項目、受影響檔案、預估工時、說明 |

---

## 第二部分：最終輸出 9 項

| # | 輸出項目 | 報告位置 | 判定 |
|:-:|---------|---------|:----:|
| 14 | Architecture Score | §1 — 65/100（加權計算） | ✅ PASS |
| 15 | Maintainability Score | §2 — 57/100（加權計算） | ✅ PASS |
| 16 | Technical Debt | §3 — P0×6 + P1×11 + P2×12 | ✅ PASS |
| 17 | Code Smell | §4 — 21 項（Critical/Major/Minor） | ✅ PASS |
| 18 | Duplicate Code | §5 — 5 種重複模式（含行號對照） | ✅ PASS |
| 19 | Refactor List | §6 — H7 + M10 + L10 = 27 項 | ✅ PASS |
| 20 | Risk List | §7 — RSK-01~RSK-14（含嚴重程度/可能性/影響/緩解措施） | ✅ PASS |
| 21 | Phase 3F 建議 | §8 — 必須完成 3 項 + 高度建議 4 項 + 若有餘力 4 項 | ✅ PASS |
| 22 | P0/P1/P2 改善清單 | §9 — P0×6 + P1×11 + P2×12（含優先序、建議做法、預估工時） | ✅ PASS |

---

## 第三部分：禁止事項

| # | 禁止事項 | 判定 | 說明 |
|:-:|---------|:----:|------|
| 23 | 沒有新增功能 | ✅ PASS | 報告僅做 Review/Analysis/Report |
| 24 | 沒有修改功能 | ✅ PASS | 無任何程式修改 |
| 25 | 沒有修改 API 行為 | ✅ PASS | 無 API 行為變更 |
| 26 | 只有 Review / Analysis / Report | ✅ PASS | 內容符合 |

---

## 第四部分：REVIEWER 指出 3 項缺失補充確認

### ① Trace 欄位一致性對比表（新增 §13）

| 檢查項 | 結果 |
|-------|:----:|
| 是否新增獨立章節 | ✅ §13 Trace 字段一致性對比表 |
| 是否盤點所有 Trace 系統 | ✅ 4 套（CalculationTrace / TreatmentPlanTrace / DecisionNode / TumorBoardEngine trace_steps）+ ClinicalDecisionEngine 零 Trace |
| 字段級比對是否完整 | ✅ 11 個維度（trace_id 命名/類型/step_order/step_name/input/output/created_at/status/parent/持久化/序列化/基底） |
| 一致性判定是否明確 | ✅ 每欄位標示 ❌/⚠️/✅ + 說明 |
| 建議是否具體 | ✅ 4 項建議（P1×2 + P2×2） |
| **整體判定** | **✅ 完整、準確** |

### ② Tests Coverage 8 類別逐類審查表（新增 §14）

| 檢查項 | 結果 |
|-------|:----:|
| 是否新增獨立章節 | ✅ §14 Tests Coverage 8 類別逐類審查表 |
| 8 類別是否完全覆蓋 | ✅ Engine / Repository / Service / API / Restart Recovery / Migration / Postgres / Graph |
| 每類別是否逐項列出 | ✅ 每類別含測試標的、測試檔案、測試數量、覆蓋範圍、缺失案例 |
| 總結是否完整 | ✅ §14.9 總結表（等級/總 test 數/強項/缺口） |
| 分數是否一致 | ✅ 維持 8.0/10 |
| **整體判定** | **✅ 完整、準確** |

### ③ Domain State/Version 檢查（補充 §10.5 + §10.6）

| 檢查項 | 結果 |
|-------|:----:|
| 是否補充到 Domain 章節 | ✅ §10.5 Domain State/Version 字段檢查、§10.6 Domain Version 控制總結 |
| 是否逐檔案列出 version 欄位 | ✅ 18 個 Domain Model 逐一列出 version 欄位名稱/型別/樂觀鎖 |
| 關鍵發現是否明確 | ✅ 僅 TreatmentPlan 有完整版本控制，其餘無樂觀鎖 |
| 建議是否具體 | ✅ 引入 `__version__` 或 `version_id` 樂觀鎖模式 |
| **整體判定** | **✅ 完整、準確** |

---

## 最終結論

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   ✅ 全部 PASS — 26 項檢查項目全數通過                       │
│                                                             │
│   3 項補充（§13 / §14 / §10.5+§10.6）均完整、準確            │
│                                                             │
│   判定：可進入 Step 7 REVIEWER                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```
