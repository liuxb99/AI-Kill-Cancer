# Phase 3A — Drug Recommendation Engine V1 執行計劃

> 本計劃涵蓋 P3A-01 至 P3A-10 共 10 項任務的詳細規格、執行順序、依賴關係、角色分配、返工預案及工時預估。

---

## 1. 執行順序與依賴圖

```
P3A-02 (Evidence Weight/Tier/Confidence 模型)
    │
    ▼
P3A-01 (Recommendation Engine 核心)
    │
    ├──► P3A-03 (Drug Ranking 系統)
    │         │
    │         ▼
    ├──► P3A-04 (Explainable AI)
    │         │
    │         ▼
    ├──► P3A-05 (Calculation Trace)
    │
    ▼
P3A-06 (JSON Schema)
    │
    ▼
P3A-07 (API 端點)
    │
    ├──► P3A-08 (HTML Report)
    │
    ├──► P3A-09 (Frontend Page)
    │
    ▼
P3A-10 (測試)
```

### 依賴矩陣

| 任務 | 前置依賴 | 說明 |
|------|----------|------|
| P3A-02 | 無 | 模型層，可最先啟動 |
| P3A-01 | P3A-02 | Engine 需要 EvidenceWeight/Tier 模型 |
| P3A-03 | P3A-01, P3A-02 | Ranking 需要 Engine 的 Aggregator + 權重模型 |
| P3A-04 | P3A-01, P3A-03 | Explainable AI 需要 Ranking 結果 |
| P3A-05 | P3A-01, P3A-03, P3A-04 | Trace 需要 Engine + Ranking + Explainable |
| P3A-06 | P3A-01, P3A-03, P3A-04 | Schema 需對齊所有輸出模型 |
| P3A-07 | P3A-01~P3A-06 | API 需要所有後端邏輯完成 |
| P3A-08 | P3A-07 | Report 需要 API 回傳數據 |
| P3A-09 | P3A-07 | Frontend 需要 API 端點 |
| P3A-10 | P3A-01~P3A-09 | 全部完成後測試 |

### 建議執行批次

| 批次 | 任務 | 理由 |
|------|------|------|
| Batch 1 | P3A-02 | 無依賴，先建模型 |
| Batch 2 | P3A-01, P3A-03 | 核心 Engine + Ranking 可並行開發（共用模型） |
| Batch 3 | P3A-04, P3A-05 | Explainable + Trace 可並行 |
| Batch 4 | P3A-06 | Schema 收斂所有輸出 |
| Batch 5 | P3A-07 | API 整合 |
| Batch 6 | P3A-08, P3A-09 | Report + Frontend 可並行 |
| Batch 7 | P3A-10 | 最終測試 |

---

## 2. 任務詳細規格

### P3A-02: Evidence Weight / Tier / Confidence / Evidence Level 模型

**核心職責：**  
建立可擴充的證據權重系統，支援 FDA、NCCN、OncoKB、CIViC、DGIdb、OpenCRAVAT 等來源。每個來源可定義自己的權重映射、Tier 系統和 Confidence 標準。

**輸入檔案：**
- `src/backend/clinical/evidence_models.py`（現有 EvidenceItem/EvidenceBundle）
- `src/backend/ranking/scorers.py`（現有 SOURCE_QUALITY / EVIDENCE_LEVEL_WEIGHT 等字典）
- `src/backend/evidence/domain.py`（現有 EvidenceItemModel）

**輸出檔案（新建/修改）：**
- `src/backend/clinical/evidence_weight.py`（新建）
  - `EvidenceWeightConfig`：每個來源的權重設定（Pydantic model）
  - `SourceTier`：來源 Tier 定義（FDA Tier 1-3、NCCN Category 1-3 等）
  - `ConfidenceLevel`：信心水準列舉（high/medium/low/very_low）
  - `EvidenceLevelMapper`：將各來源原生 Level 映射到統一 Level（A-E / Level_1-5）
  - `WEIGHT_REGISTRY`：全域權重註冊表，支援 `register_source()` 擴充
- `src/backend/clinical/evidence_models.py`（修改）
  - 引入新的 `EvidenceWeight` 類型
  - 為 `EvidenceItem` 增加 `weight` / `tier` / `confidence` 計算屬性

**注意事項：**
- 不可寫死來源列表；使用 registry 模式，新來源只需註冊即可
- 向後相容：不破壞現有 `EvidenceItem` / `EvidenceBundle` 結構
- 權重映射需支援 override，允許使用者自訂

---

### P3A-01: Recommendation Engine 核心（Engine / Rule / Aggregator / Ranker）

**核心職責：**  
建立規則化的 Recommendation Engine，包含：
- `RecommendationEngine`：總協調器，負責管線調度
- `RecommendationRule`：單一推薦規則（可組合）
- `EvidenceAggregator`：聚合多方證據，產出 AggregatedEvidenceScore
- `DrugRanker`：根據聚合分數排序藥物

**輸入檔案：**
- `src/backend/clinical/recommendation.py`（現有 RecommendationGenerator）
- `src/backend/ranking/engine.py`（現有 DrugRankingEngine）
- `src/backend/ranking/models.py`（現有 DrugRankingResult / DrugRankItem）
- `src/backend/ranking/scorers.py`（現有 Scorers）
- 新建立的 `evidence_weight.py`

**輸出檔案（新建/修改）：**
- `src/backend/clinical/engine.py`（新建）
  - `RecommendationEngine`：主引擎
    - `async generate(case_id, context, evidence) → RecommendationResult`
    - 支援注入自訂 Rule 列表
  - `RecommendationRule(BaseModel)`：規則基礎類別
    - `name: str`、`priority: int`、`condition: Callable`、`action: Callable`
    - `async evaluate(context, evidence, scores) → RuleResult`
  - `EvidenceAggregator`：證據聚合器
    - `aggregate(evidence_items, weights) → AggregatedScore`
    - 支援 per-source 權重、per-level 權重
    - 輸出 `source_breakdown` 供 Explainable AI 使用
  - `DrugRanker`：藥物排序器
    - `rank(drug_scores, top_n=10) → list[RankedDrug]`
    - 考慮 Overall Score、Evidence Score、Sensitivity、Resistance、Conflict Score
    - 支援 tie-breaking 策略

- `src/backend/clinical/models.py`（修改）
  - 新增 `RecommendationResult`、`RankedDrug`、`AggregatedScore` 等模型

**注意事項：**
- 所有邏輯規則化，禁止 if-else 寫死
- 繼承現有 `DrugRankingEngine` 的設計但不直接依賴它——新的 `DrugRanker` 可包裹舊引擎
- Engine 需支援 `DecisionThreadInjector` 整合

---

### P3A-03: Drug Ranking 系統

**核心職責：**  
基於聚合後的證據分數，計算每種藥物的最終排名，包含 Overall Score、Evidence Score、Sensitivity、Resistance、Conflict Score 五個維度。

**輸入檔案：**
- `src/backend/ranking/engine.py`
- `src/backend/ranking/scorers.py`
- `src/backend/ranking/penalties.py`
- P3A-01 的 `EvidenceAggregator` 輸出
- P3A-02 的 `EvidenceWeightConfig`

**輸出檔案（新建/修改）：**
- `src/backend/ranking/engine.py`（修改）
  - 擴充 `DrugRankingEngine` 或建立新的 `ClinicalDrugRanker`
  - 新增 `OverallScoreCalculator`：加權組合各維度分數
  - 新增 `ConflictScoreCalculator`：計算證據之間的衝突程度
- `src/backend/ranking/models.py`（修改）
  - 新增 `OverallScore`、`ConflictScore` 欄位
  - 版本升級至 `1.0.0`
- `src/backend/ranking/scorers.py`（修改）
  - 增強 `EvidenceScorer` 支援新權重系統
  - 新增 `ConflictScorer`

**注意事項：**
- 保留舊版 `DrugRankingEngine` 的向後相容性
- Top N 排序需可配置（預設 10）
- 排序結果須包含完整 Score Breakdown 供 Explainable AI 使用

---

### P3A-04: Explainable AI

**核心職責：**  
每個 Recommendation 必須產生可追溯的 Reason、Evidence、Source、Score Detail，解釋：
- 為什麼第一名是第一名
- 為什麼第二名是第二名
- 為什麼被扣分
- 哪些證據支持哪些結論

**輸入檔案：**
- P3A-01 的 RecommendationEngine 輸出
- P3A-03 的 DrugRanking 輸出
- `EvidenceBundle`（原始證據）

**輸出檔案（新建/修改）：**
- `src/backend/clinical/explanation.py`（新建）
  - `RecommendationExplainer`：生成可解釋性內容
    - `explain_ranking(ranked_drugs, evidence) → list[DrugExplanation]`
    - `explain_score_difference(drug_a, drug_b) → str`
    - `explain_penalty(drug) → list[PenaltyExplanation]`
  - `DrugExplanation(BaseModel)`：
    - `drug_name`、`rank`、`total_score`
    - `key_evidence`：支援該藥物的關鍵證據列表
    - `supporting_sources`：來源列表（FDA/NCCN/OncoKB 等）
    - `score_breakdown_human`：人類可讀的分數明細
    - `penalty_reasons`：扣分原因
    - `conflict_summary`：衝突摘要
  - `PenaltyExplanation(BaseModel)`：
    - `type`（conflict/uncertainty/resistance）
    - `description`
    - `impact`（扣分數值）
    - `source_evidence_ids`

- `src/backend/clinical/models.py`（修改）
  - 新增 `RecommendationReason`、`ScoreDetail` 等模型

**注意事項：**
- 全部可追溯（Traceable）：每個結論都指向具體證據 ID
- 使用自然語言生成 Reason，但禁止 LLM（規則化模板）
- 中英文雙語支援（優先中文）

---

### P3A-05: Calculation Trace

**核心職責：**  
沿用既有 `DecisionThread` 架構，為推薦引擎建立完整計算軌跡：
Input → Evidence → Score → Recommendation → Output

**輸入檔案：**
- `src/backend/clinical/decision_thread.py`（現有 DecisionThreadInjector）
- P3A-01 的 RecommendationEngine
- P3A-04 的 RecommendationExplainer

**輸出檔案（修改）：**
- `src/backend/clinical/decision_thread.py`（修改）
  - 新增節點類型：`"evidence_scored"`、`"drug_ranked"`、`"recommendation_explained"`
  - 擴充 `DecisionThreadInjector`：
    - `record_evidence_scored(scored_evidence) → str`
    - `record_drug_ranked(ranked_drugs) → str`
    - `record_recommendation_explained(explanation) → str`
  - 每個節點包含 input_snapshot / output_snapshot / reasoning

**注意事項：**
- 不破壞既有 DecisionNode 模型
- 新節點類型需加入 `NodeType` Literal

---

### P3A-06: JSON Schema

**核心職責：**  
建立 Versioned JSON Schema，包含：
- `RecommendationResult`
- `DrugScore`
- `EvidenceScore`
- `RecommendationReason`

**輸入檔案：**
- P3A-01 的 `RecommendationResult`、`RankedDrug`
- P3A-03 的 `ScoreBreakdown`
- P3A-04 的 `DrugExplanation`、`RecommendationReason`

**輸出檔案（新建/修改）：**
- `src/backend/clinical/schemas.py`（新建）
  - 每個 Schema 都是 Pydantic model，附帶 `schema_version` 欄位
  - `RecommendationResultV1`：
    - `schema_version: Literal["1.0.0"]`
    - `recommendation_id`、`case_id`、`created_at`
    - `patient_snapshot`、`variants`、`top_drugs: list[DrugScoreV1]`
    - `evidence_summary: list[EvidenceScoreV1]`
    - `reasons: list[RecommendationReasonV1]`
    - `calculation_trace: list[TraceStep]`
  - `DrugScoreV1`：
    - `drug_name`、`rank`、`overall_score`
    - `evidence_score`、`sensitivity_score`、`resistance_score`
    - `conflict_score`、`guideline_support`、`regulatory_approval`
    - `confidence`、`limitations`
  - `EvidenceScoreV1`：
    - `evidence_id`、`source`、`evidence_level`
    - `weight`、`tier`、`confidence`
    - `supporting_drugs: list[str]`
  - `RecommendationReasonV1`：
    - `rank`、`drug_name`、`reason`、`key_evidence_ids`
    - `score_detail`、`penalty_detail`

- `src/backend/clinical/__init__.py`（修改）
  - 匯出所有 Schema

**注意事項：**
- 所有 Schema 必須有 `schema_version` 欄位
- 使用 `Literal` 類型確保版本字串精確
- 向後相容：新版本 Schema 應可從舊版本轉換

---

### P3A-07: API 端點

**核心職責：**  
提供兩個端點：
- `POST /api/v1/recommendation` — 觸發推薦引擎，傳入 case_id 或 variant 列表
- `GET /api/v1/recommendation/{id}` — 取得推薦結果

**輸入檔案：**
- P3A-06 的 JSON Schema
- 現有 API 模式：`api/v1/clinical.py`、`api/v1/ranking.py`
- 現有依賴注入：`auth/dependencies.py`、`database/session.py`

**輸出檔案（新建/修改）：**
- `src/backend/api/v1/recommendation.py`（新建）
  - `POST /recommendation`
    - Request body: `case_id`（必要）、`variant_ids`（可選）、`top_n`（可選，預設 10）、`include_trace`（可選，預設 false）
    - Response: `RecommendationResultV1`
    - 流程：查 case → 建立 context → 收集 evidence → 聚合權重 → 排名 → 解釋 → 產生 schema → 儲存至 DB → 返回
  - `GET /recommendation/{id}`
    - Response: `RecommendationResultV1`（從 DB 讀取）
  - `GET /recommendation`（可選）
    - 列出該使用者可存取的推薦記錄

- `src/backend/api/v1/router.py`（修改）
  - 加入 `recommendation_router`

- `src/backend/repositories/recommendation_repo.py`（新建）
  - `RecommendationRepository`：CRUD 操作
  - SQLAlchemy model：`RecommendationModel`

- 資料庫 migration（新增 migration 檔案）
  - 新建 `recommendation_results` 表

**注意事項：**
- 遵循現有 API 權限模式（require_auth + case ACL）
- 使用 `DecisionThreadInjector` 記錄 API 呼叫軌跡
- `POST` 應為同步操作（非背景任務），除非 Case 非常複雜

---

### P3A-08: HTML Drug Recommendation Report

**核心職責：**  
生成包含以下內容的 HTML 報告：
- Patient 資訊
- Variants 列表
- Evidence 摘要
- Top Drugs（含分數、理由、證據來源）
- Reason / Warnings
- Trace（完整計算軌跡）

**輸入檔案：**
- P3A-06 的 `RecommendationResultV1` Schema
- 現有報告模式：`reporting/builder.py`、`reporting/renderer.py`、`reporting/templates.py`

**輸出檔案（新建/修改）：**
- `src/backend/clinical/report_html.py`（新建）
  - `RecommendationHtmlReport`：從 `RecommendationResultV1` 生成 HTML
  - 使用 Jinja2 模板（或 f-string 生成乾淨 HTML）
  - 包含內聯 CSS（無外部依賴）
  - 結構：
    - 標頭：Case ID、Patient 摘要、產生時間
    - Variant 表格
    - Evidence 摘要（按來源分組）
    - Top N Drugs 排名（每個 Drug 展開 Score Breakdown、支持證據、扣分原因）
    - Warning/Conflict 區域
    - Calculation Trace（時間線）
    - 頁尾：免責聲明、版本資訊
  - 支援 `render_to_file(path)` 和 `render_to_string()`

- `src/backend/api/v1/recommendation.py`（修改）
  - 增加 `GET /recommendation/{id}/html` 端點，返回 `HTMLResponse`

**注意事項：**
- 使用現有 `ReportRenderer` 的模式
- 報告全部 Clientside 可列印
- 中文優先，英文備用

---

### P3A-09: Frontend Recommendation Page

**核心職責：**  
在現有前端新增 Recommendation Page，不重新設計整體 UI。

**輸入檔案：**
- 現有 Frontend 結構：`App.tsx`、`pages/`、`components/tabs/`
- P3A-07 的 API 端點
- P3A-08 的 HTML Report URL

**輸出檔案（新建/修改）：**
- `src/frontend/src/pages/Recommendation.tsx`（新建）
  - 推薦引擎首頁
  - 輸入 Case ID（或從 URL params 讀取）
  - 顯示載入/錯誤/空狀態
  - 主要卡片佈局：
    - Case 摘要卡
    - Top Drugs 排名列表（每個 Drug 可展開）
    - Evidence 摘要區塊
    - Reason / Warnings 區域
    - 檢視 HTML Report 按鈕（新分頁開啟 `/api/v1/recommendation/{id}/html`）
    - Calculation Trace 時間線
  - 使用 Tailwind CSS，遵循現有 Design System

- `src/frontend/src/api/recommendation.ts`（新建）
  - API client functions：`createRecommendation(caseId)`, `getRecommendation(id)`, `getRecommendationHtml(id)`
  - TypeScript interfaces 對應 `RecommendationResultV1`

- `src/frontend/src/App.tsx`（修改）
  - 加入路由：`/recommendation`（頁面）和 `/recommendation/:id`（查詢結果）

**注意事項：**
- 不重新設計，使用現有元件庫（Section、LoadingSkeleton、ErrorState、EmptyState）
- 支援從 Workbench 頁面導航過來
- 中文化 UI

---

### P3A-10: 測試

**核心職責：**  
至少包含：
- Unit Tests（每個核心類別）
- Integration Tests（Engine + Ranking + Explainable 整合）
- API Tests（POST/GET 端點）
- Golden Tests（HTML Report 比對）

**測試檔案（新建）：**
- `src/tests/clinical/test_evidence_weight.py`
  - 測試權重註冊、來源映射、Level 映射
- `src/tests/clinical/test_recommendation_engine.py`
  - 測試 Engine 初始化、Rule 評估、Aggregator 聚合、Ranker 排序
- `src/tests/clinical/test_explanation.py`
  - 測試 Explainable AI 輸出完整性
- `src/tests/clinical/test_calculation_trace.py`
  - 測試 DecisionThreadInjector 新節點類型
- `src/tests/api/test_recommendation_api.py`
  - 測試 POST/GET 端點、權限檢查、錯誤處理
- `src/tests/clinical/test_report_html.py`
  - 測試 HTML Report 生成、Golden File 比對

**注意事項：**
- 使用 pytest + pytest-asyncio
- API 測試使用 TestClient（FastAPI）
- Golden Tests 首次執行產生 baseline，後續 diff 比對
- 測試資料使用 Factory（避免依賴真實 DB）

---

## 3. 負責角色分配

| 任務 ID | 負責角色 | 子代理分工說明 |
|---------|----------|---------------|
| P3A-02 | **db-modeler** | 設計 EvidenceWeight/Tier/Confidence 模型，registry 模式 |
| P3A-01 | **backend-logic** | 實作 Engine/Rule/Aggregator/Ranker 核心邏輯 |
| P3A-03 | **backend-logic** | 擴充 Ranking 系統，新增 Conflict/Overall Score |
| P3A-04 | **backend-logic** | 實作 Explainable AI，規則化 Reason 生成 |
| P3A-05 | **backend-logic** | 擴充 DecisionThreadInjector，新增追蹤節點 |
| P3A-06 | **backend-logic** | 建立 Versioned JSON Schema |
| P3A-07 | **api-designer** | 實作 API 端點 + Repository + Migration |
| P3A-08 | **backend-logic** | 實作 HTML Report 生成 |
| P3A-09 | **frontend-logic** | 實作 Frontend Recommendation Page |
| P3A-10 | **unit-tester + integration-tester** | 撰寫所有測試 |

### 協作原則

1. **跨角色依賴**：`api-designer` 需等待 `backend-logic` 完成 Schema 後才能實作 API
2. **並行最大化**：Batch 2 內 P3A-01 與 P3A-03 可並行；Batch 3 內 P3A-04 與 P3A-05 可並行；Batch 6 內 P3A-08 與 P3A-09 可並行
3. **接口契約優先**：角色間以 Schema/Interface 為契約，先約定再實作

---

## 4. 返工預案

若 REVIEWER 評分低於 90，按以下方向重新規劃：

### 4.1 常見低分原因與對策

| 低分原因 | 對策 |
|----------|------|
| **缺少核心功能**（如 Explainable AI 不完整） | 優先補完 P3A-04，確保每個 Drug 都有 Reason/Evidence/Source/Score Detail |
| **權重系統不可擴充**（寫死了來源列表） | 重構 P3A-02 為純 Registry 模式，新增註冊 API |
| **Ranking 缺少維度**（缺少 Conflict Score） | 補實 P3A-03 的 ConflictScorer 和 OverallScoreCalculator |
| **Trace 不完整**（DecisionThread 缺少新節點） | 補實 P3A-05 的三個新節點類型 |
| **Schema 版本化不嚴謹** | P3A-06 強制 `schema_version` 欄位，使用 Literal |
| **API 缺少錯誤處理或權限檢查** | P3A-07 補上全面的 HTTPException 和 case ACL |
| **HTML Report 缺少 Patient/Variant/Trace 資訊** | P3A-08 補上所有必填區塊 |
| **Frontend 缺少載入/錯誤/空狀態** | P3A-09 補上所有 UI 狀態 |
| **測試覆蓋率不足** | P3A-10 補上 Unit/Integration/API/Golden Tests，目標 Line Coverage > 80% |

### 4.2 返工執行流程

1. REVIEWER 給出具體評分與缺失清單
2. 根據缺失定位到對應任務 ID
3. 該任務的負責角色重新執行
4. 所有依賴該任務的後續任務需重新驗證
5. 所有測試重新執行
6. REVIEWER 二次評分

### 4.3 緊急降級方案

若時間不足，可降級以下功能（但仍需通過 Reviewer 門檻）：
- **P3A-09 Frontend**：可先只做基本頁面（輸入 Case ID + 顯示結果），省略進階 UI
- **P3A-08 HTML Report**：可先做純文字 Markdown 報告替代
- **P3A-05 Trace**：可先只記錄關鍵節點（evidence_scored + drug_ranked），省略 recommendation_explained

---

## 5. 預估工時

### 估算方法

每個任務的「執行步驟數」指子代理需要進行的 tool call 回合數（讀檔案、編輯檔案、執行程式碼、驗證結果等）。

| 任務 ID | 預估步驟數 | 說明 |
|---------|-----------|------|
| P3A-02 | 25-35 步 | 包含模型設計、Registry 實作、單元測試 |
| P3A-01 | 40-55 步 | 核心 Engine 最複雜，含 Rule/Aggregator/Ranker |
| P3A-03 | 20-30 步 | 擴充 Ranking 系統，新增 Scorer |
| P3A-04 | 25-35 步 | Explainable AI 含模板化 Reason 生成 |
| P3A-05 | 10-15 步 | 擴充 DecisionThread，較簡單 |
| P3A-06 | 10-15 步 | 定義 Schema，版本化管理 |
| P3A-07 | 20-30 步 | API + Repository + Migration + 權限 |
| P3A-08 | 15-25 步 | HTML Report 含模板與 CSS |
| P3A-09 | 20-30 步 | Frontend 頁面 + API Client + 路由 |
| P3A-10 | 25-40 步 | 完整測試套件 |
| **總計** | **210-310 步** | 全 10 項任務 |

### 批次工時分佈

```
Batch 1: P3A-02       25-35 步
Batch 2: P3A-01+P3A-03  60-85 步（可並行）
Batch 3: P3A-04+P3A-05  35-50 步（可並行）
Batch 4: P3A-06       10-15 步
Batch 5: P3A-07       20-30 步
Batch 6: P3A-08+P3A-09  35-55 步（可並行）
Batch 7: P3A-10       25-40 步
```

---

## 附錄：檔案變更總表

| 操作 | 路徑 |
|------|------|
| **新建** | `src/backend/clinical/evidence_weight.py` |
| **新建** | `src/backend/clinical/engine.py` |
| **新建** | `src/backend/clinical/explanation.py` |
| **新建** | `src/backend/clinical/schemas.py` |
| **新建** | `src/backend/clinical/report_html.py` |
| **新建** | `src/backend/api/v1/recommendation.py` |
| **新建** | `src/backend/repositories/recommendation_repo.py` |
| **新建** | `src/frontend/src/pages/Recommendation.tsx` |
| **新建** | `src/frontend/src/api/recommendation.ts` |
| **新建** | `src/tests/clinical/test_evidence_weight.py` |
| **新建** | `src/tests/clinical/test_recommendation_engine.py` |
| **新建** | `src/tests/clinical/test_explanation.py` |
| **新建** | `src/tests/clinical/test_calculation_trace.py` |
| **新建** | `src/tests/clinical/test_report_html.py` |
| **新建** | `src/tests/api/test_recommendation_api.py` |
| **修改** | `src/backend/clinical/evidence_models.py` |
| **修改** | `src/backend/clinical/models.py` |
| **修改** | `src/backend/clinical/decision_thread.py` |
| **修改** | `src/backend/clinical/__init__.py` |
| **修改** | `src/backend/ranking/engine.py` |
| **修改** | `src/backend/ranking/models.py` |
| **修改** | `src/backend/ranking/scorers.py` |
| **修改** | `src/backend/api/v1/router.py` |
| **修改** | `src/frontend/src/App.tsx` |
| **新增** | database migration（新增 recommendation_results 表） |

---

*本計劃由 PLANNER 根據 tasks/requirements.md 及現有專案結構自動生成。*
