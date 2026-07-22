# AI Kill Cancer - 綜合需求文件

## 專案目標
利用人工智慧（AI）全方位對抗癌症，涵蓋工具開發、網站建設、研究分析、開發整合等面向。

## 需求範疇
1. **工具開發**：開發 AI 輔助癌症診斷、預測、治療推薦等工具
2. **網站建設**：建立資訊平台、可視化儀表板、研究入口網站
3. **研究分析**：文獻分析、基因數據處理、藥物發現 AI 模型
4. **開發整合**：將現有開源專案整合、API 開發、資料管線

## 場景分類
- 資料科學 / 研究分析
- 前端網站開發
- 後端 API 與工具開發
- 文檔與知識管理

---

# Phase 2 — Multi-Agent Clinical Decision Workspace

## 目標
將現有 Clinical Workbench 轉變為真正的臨床決策工作空間，使 Case Summary、Timeline、Notes、Attachments、Clinical Reasoning、Tumor Board、Variant Compare 等模組協作而非孤立。

## 工作流程
```
Case → Clinical Context Builder → Evidence Collector → Multi-Agent Discussion → Consensus Engine → Treatment Recommendation → Digital Thread
```

## 需求詳細

### 1. Clinical Context Builder (CaseContextBuilder)
- 輸入：diagnosis, stage, pathology, biomarkers, variants, treatment history, medications, allergies, ECOG, age, gender
- 輸出：ClinicalContext
- 所有下游模組必須消費 ClinicalContext，而非重複查詢資料庫

### 2. Evidence Collector (EvidenceCollector)
- 收集證據來源：NCCN, ESMO, FDA, ClinVar, CIViC, OncoKB, PMIDs, internal evidence
- 輸出：EvidenceBundle（含 evidence level, citation, confidence, conflicts）

### 3. Multi-Agent Discussion
- 六個獨立 Agent：DiagnosisAgent, VariantAgent, DrugAgent, ResistanceAgent, GuidelineAgent, ClinicalTrialAgent
- 每個 Agent 接收 ClinicalContext + EvidenceBundle
- 回傳 AgentOpinion（含 summary, pros, cons, confidence, references）
- Agents 不可直接修改彼此

### 4. Consensus Engine (ConsensusEngine)
- 輸入：AgentOpinion[]
- 輸出：ConsensusResult（含 agreement, conflicts, confidence, recommended option, alternative options, unresolved questions）

### 5. Recommendation Generator
- 結構化治療方案：First-line, Second-line, Clinical Trial, Supporting Evidence, Expected Benefit, Potential Risk, Monitoring Plan
- 回傳 structured JSON + markdown

### 6. Digital Thread
- 每個重要決策產生 DecisionNode（含 input, evidence, agent, reason, timestamp, parent decision）
- 完整可追溯性

### 7. 前端新分頁
- Context, Evidence, Agents, Consensus, Recommendation, Decision Thread
- 各自獨立載入
- 避免巨型 React 元件，拆分為可複用元件

### 8. 測試
- Unit Tests, Integration Tests, Frontend Tests, End-to-End Tests
- 涵蓋 Context Builder, Evidence Collector, Agent outputs, Consensus, Recommendation generation, Digital Thread

### 9. 工程規範
- 保持現有架構，不重寫 Phase 1
- 不引入佔位實作、不引入 fallback fake data、無 mock business logic
- 每個 public API 必須是 production quality
- 通過 ruff check, pytest, npm test, npm run build