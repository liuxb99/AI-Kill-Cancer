# Architecture Review (Phase 1~3E) — 總結報告

## 任務概述

- **任務類型**：全面 Code Review + Architecture Review
- **Review 範圍**：Phase1 → Phase2 → Phase3A → Phase3B → Phase3C → Phase3D → Phase3E
- **交付產出**：`tasks/reviews/architecture_review.md`
- **底層子報告**：
  - `tasks/reviews/review_layers.md`（分層架構審查）
  - `tasks/reviews/review_crosscutting.md`（橫切關注點審查）
  - `tasks/reviews/review_quality.md`（程式碼品質審查）
- **禁止事項**：未新增／修改任何功能、API 行為或程式碼，僅執行 Review／Analysis／Report

---

## 評分歷程

| 階段 | 分數 | 判定 |
|------|:----:|:----:|
| 初始 REVIEWER | 82 / 100 | ❌ 不合格 |
| 返工第 2 次 REVIEWER | 91 / 100 | ✅ **合格** |

> 初次評分因 Trace 審查未「全部列出」、Tests Coverage 缺少逐類審查表、Domain State/Version 分析深度不足而扣分；第二次返工補上 §13 Trace 對比表、§14 Tests 逐類審查表、§10.5+§10.6 Domain State/Version 審查後，提升 9 分達到合格門檻。

---

## 核心發現摘要

### Architecture Score（整體架構分數）：**65 / 100**

| 審查維度 | 原始分數 (/10) | 權重 | 加權得分 |
|---------|:-------------:|:----:|:--------:|
| 分層架構（Domain / Repository / Service / Engine） | 5.75 | 40% | 2.30 |
| 橫切關注點（Migration / API / Digital Thread / Trace） | 6.50 | 30% | 1.95 |
| 程式碼品質（Graph Adapter / Tests / Dead Code / Smell） | 7.50 | 30% | 2.25 |
| **總和** | | | **6.50** |

**評語**：專案在模組劃分與 DDD 分層意圖上方向正確，但 Domain 層純淨性崩潰、事務邊界不一致、Trace 系統碎片化等結構性問題嚴重拖累分數。

### Maintainability Score（可維護性分數）：**57 / 100**

| 評估因子 | 分數 (/10) | 權重 | 加權得分 |
|---------|:----------:|:----:|:--------:|
| God Class / 超大函數 | 4.0 | 30% | 1.20 |
| 重複程式碼（Copy-Paste） | 6.5 | 20% | 1.30 |
| 依賴混亂 / 架構違規 | 5.0 | 25% | 1.25 |
| 命名與註解一致性 | 7.5 | 15% | 1.13 |
| 測試覆蓋對可維護性的支撐 | 8.0 | 10% | 0.80 |
| **總和** | | | **5.68** |

### Technical Debt（技術債摘要）

| 等級 | 數量 | 說明 |
|:----:|:----:|------|
| P0（立即修復，Blocking） | 6 項 | 架構性崩潰問題，需立即處理 |
| P1（短期改善） | 11 項 | 短期內應優先解決 |
| P2（長期追蹤） | 12 項 | 適合納入 Phase 3F 迭代改善 |

### 最重要的 P0 問題（Top 6）

| ID | 問題描述 | 影響層 | 關鍵位置 |
|----|---------|-------|---------|
| **P0-01** | **Domain 層混入 SQLAlchemy ORM 依賴**——全部 26 個 Domain 檔案繼承 `DBBase` 並使用 ORM 類型 | Domain | `src/backend/domain/*.py`（全部檔案） |
| **P0-02** | **Service 層反向依賴 API 層**——違反分層依賴方向 | Service | `src/backend/services/recommendation_service.py:248` |
| **P0-03** | **BaseRepository 預設 commit() 導致事務邊界下移**——影響所有繼承子類 | Repository | `src/backend/repositories/base.py:29,73,82` |
| **P0-04** | **Outbox Repository 混入大量業務邏輯**——CRUD 與業務邏輯未分離 | Repository | `src/backend/repositories/clinical_graph_outbox_repo.py`（全檔案） |
| **P0-05** | **Python ID Factory 缺少 5 個治療計劃相關方法**——跨語言 ID 不一致 | Graph | `src/backend/clinical_graph/id_factory.py` |
| **P0-06** | **buildProvenance 硬編碼爲 ProvenanceImported**——所有事件被標記爲「匯入」 | Graph | `KnowGraphGo/adapter/clinical/adapter.go:110-112` |

### Risk List 中的 Critical 風險

| ID | 風險描述 | 嚴重程度 | 發生概率 | 影響 |
|:--:|---------|:--------:|:--------:|:----:|
| **RSK-01** | Domain/ORM 緊耦合阻礙測試與遷移，重構工時 40h+ | 🔴 Critical | 90% | 9/10 |
| **RSK-02** | 事務邊界下沉導致資料不一致（read uncommitted / partial write） | 🔴 Critical | 70% | 8/10 |
| **RSK-03** | Trace 系統碎片化導致臨床路徑無法完整回溯 | 🟡 High | 80% | 6/10 |
| **RSK-04** | Patient 事件永不投射到知識圖譜，KnowGraphGo 永遠缺少 Patient 節點 | 🟡 High | 60% | 8/10 |
| **RSK-05** | API Error Response 格式不統一增加前端對接成本 | 🟢 Medium | 100% | 4/10 |

---

## 返工記錄

### 第 1 次 REVIEWER（82/100 → ❌ 不合格）

**主要缺失**：
1. **Trace 審查未「全部列出」**——僅提及三套 Trace 系統不一致，未提供欄位級別對比清單。
2. **Tests Coverage 審查未「全部列出」**——僅給出 8/10 分數，未逐一列出 8 個類別的覆蓋狀態。
3. **Domain State/Version 分析深度不足**——對 State 和 Version 的一致性檢查不充分。
4. **缺乏自動化工具佐證**——未使用 `coverage`、`pylint`、`mypy` 等工具的量化報告。

### 返工第 2 次 REVIEWER（91/100 → ✅ 合格）

**本次返工補充的三項內容**：

| 補充項目 | 報告章節 | 內容概述 |
|---------|---------|---------|
| **① Trace 欄位一致性對比表** | §13 | 完整盤點 4 套 Trace 系統（CalculationTrace / TreatmentPlanTrace / DecisionNode / TumorBoardEngine），11 個欄位維度交叉比對，每欄位標示 ❌/⚠️/✅，給出 4 項具體統一建議 |
| **② Tests Coverage 8 類別逐類審查表** | §14 | 逐類審查 Engine / Repository / Service / API / Restart / Migration / Postgres / Graph，每類別含測試標的、檔案、數量、覆蓋範圍、缺失案例，總結表統整各類別覆蓋等級 |
| **③ Domain State/Version 審查** | §10.5 + §10.6 | 逐一檢視 18 個狀態欄位的類型與 State Transition 定義，以及 8 個 Model 的版本控制實作，關鍵發現：僅 TreatmentPlan 有完整版本控制，其餘無樂觀鎖 |

---

## 需求回歸檢查結果

| 檢查範圍 | 項目數 | 判定 |
|---------|:------:|:----:|
| 13 項 Review 項目（Domain / Repository / Service / Engine / Migration / API / Digital Thread / Trace / Graph Adapter / Tests / Dead Code / Architecture Smell / Refactor Candidate） | 13/13 | ✅ 全部 PASS |
| 9 項最終輸出（Architecture Score / Maintainability Score / Technical Debt / Code Smell / Duplicate Code / Refactor List / Risk List / Phase 3F 建議 / P0/P1/P2 改善清單） | 9/9 | ✅ 全部 PASS |
| 禁止事項（未新增功能、未修改功能、未修改 API、僅 Review/Analysis/Report） | 4/4 | ✅ 全部 PASS |
| **總計** | **26/26** | **✅ 全部 PASS** |

---

## Phase 3F 建議

### 🔴 必須完成（3 項）

| 優先序 | 項目 | 對應問題 | 預估工時 |
|:----:|------|---------|:--------:|
| 1 | **Domain/ORM 分離**——將 `*Model` 類移到 `database/models.py`，建立純 Python 領域模型 | P0-01 | 40h+（需技術 Spike 後重新估算） |
| 2 | **統一事務策略**——`BaseRepository` 改爲 `flush()`，審計所有 `commit()` 子類 | P0-03 | 8h |
| 3 | **重構 Outbox Repository**——拆分 CRUD Repository 和 Outbox Processor Service | P0-04 | 8h |

### 🟡 高度建議（4 項）

| 優先序 | 項目 | 對應問題 | 預估工時 |
|:----:|------|---------|:--------:|
| 4 | 修復 `RecommendationEngine.run()` 純函數違規 | P1-01 | 16h |
| 5 | 統一 API Error Response 格式與 HTTP Status Code | P1-07, P1-08 | 8h |
| 6 | 補齊 Patient Outbox 事件（Patient → KnowGraphGo） | P1-06 | 8h |
| 7 | 統一三套 Trace 系統 Schema | P1-05 | 16h |

### 🟢 若有餘力（4 項）

| 優先序 | 項目 | 對應問題 | 預估工時 |
|:----:|------|---------|:--------:|
| 8 | 重構 God Class：`TreatmentPlanService`（57KB）、`ClinicalAdapter`（40KB）、`report_generator.py`（64KB） | P2-05~P2-07 | 各 8~16h |
| 9 | 補齊 KnowGraphGo Adapter 缺少的 Variant/Guideline/Drug 事件處理 | P1-10 | 8h |
| 10 | 引入 `@transactional` 裝飾器消除手動 try/commit 重複模式 | P2-04 | 4h |
| 11 | 補上 `ClinicalDecisionEngine` 測試覆蓋（目前爲 0） | Tests 缺口 | 8h |

> **重構總預估工時**：HIGH 7 項 75h+、MEDIUM 10 項 69h、LOW 10 項 35h+，**合計約 179h**。

---

## 結論

| 檢查項 | 結果 |
|-------|:----:|
| **REVIEWER 最終評分** | **91 / 100 — ✅ 合格**（較初次提升 9 分） |
| **需求回歸檢查（26 項）** | **✅ 全部 PASS** |
| **3 項補充內容**（Trace 對比表 / Tests 逐類審查 / Domain State/Version） | ✅ 完整、準確 |
| **Phase 3F 建議** | 3 項必須完成 + 4 項高度建議 + 4 項若有餘力 |

本次 Architecture Review (Phase 1~3E) 任務已完成。交付報告 `architecture_review.md` 涵蓋了全部 13 項 Review 項目與 9 項最終輸出，經過一次返工後通過 REVIEWER 評分與需求回歸檢查。報告指出了專案最緊迫的架構問題（Domain/ORM 緊耦合、事務邊界下沉、Trace 碎片化），並提供了包含優先級、預估工時與具體做法的重構路徑，可作為 Phase 3F 迭代改善的執行依據。
