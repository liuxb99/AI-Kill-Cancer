# Phase 2 總結報告 — Multi-Agent Clinical Decision Workspace

> **專案**: AI-Kill-Cancer Clinical Workbench  
> **階段**: Phase 2 — Multi-Agent Clinical Decision Workspace  
> **Baseline commit**: `322a59a3a066bcf802512cf375c3e1dc330df794`  
> **分支**: `master`  
> **狀態**: ✅ 已完成（含 1 次返工修正）

---

## 目錄

1. [架構總覽](#1-架構總覽)
2. [工作流程](#2-工作流程)
3. [完成統計](#3-完成統計)
4. [核心模組](#4-核心模組)
5. [新增 API 端點](#5-新增-api-端點)
6. [資料庫遷移](#6-資料庫遷移)
7. [新增檔案清單](#7-新增檔案清單)
8. [品質評分](#8-品質評分)
9. [待改進事項](#9-待改進事項)
10. [附錄：術語對照](#10-附錄術語對照)

---

## 1. 架構總覽

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Phase 2 核心工作流                                       │
│                                                                             │
│  Case ─→ ClinicalContextBuilder ─→ EvidenceCollector ─→ Multi-Agent         │
│                                │                    │     Discussion          │
│                                │                    │         │              │
│                                ▼                    ▼         ▼              │
│                          ClinicalContext      EvidenceBundle  6 Agents       │
│                                │                    │         │              │
│                                └────────┬───────────┘         │              │
│                                         │                     │              │
│                                         ▼                     │              │
│                                   ConsensusEngine ◄───────────┘              │
│                                         │                                    │
│                                         ▼                                    │
│                               RecommendationGenerator                        │
│                                         │                                    │
│                                         ▼                                    │
│                                   Digital Thread                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

Phase 2 將 Phase 1 Clinical Workbench 的孤立模組轉變為協作式臨床決策工作空間，實現從**病案匯入 → 臨床上下文建構 → 證據收集 → 多代理討論 → 共識匯總 → 治療推薦 → 決策線程追溯**的完整管線。

---

## 2. 工作流程

| 步驟 | 組件 | 說明 |
|------|------|------|
| ① | `CaseContextBuilder` | 從資料庫組裝完整 `ClinicalContext`（診斷、分期、病理、變異、治療史、用藥、ECOG 等） |
| ② | `EvidenceCollector` | 從 CIViC、ClinVar、PubMed、ClinicalTrials.gov 等來源收集證據，產出 `EvidenceBundle` |
| ③ | 6 個 Agent 討論 | 平行執行各專科 Agent，各自產出 `AgentOpinion` |
| ④ | `ConsensusEngine` | 聚合 Agent 意見，Jaccard 相似度檢測衝突，產出結構化 `ConsensusResult` |
| ⑤ | `RecommendationGenerator` | 基於共識結果生成一線/二線/臨床試驗推薦，輸出 JSON + Markdown |
| ⑥ | `DecisionThreadRepository` | 將每個步驟記錄為 `DecisionNode`，形成可追溯的決策樹 |

---

## 3. 完成統計

### 3.1 階段任務統計

| 階段 | 名稱 | 任務數 | 狀態 |
|------|------|--------|------|
| Phase 2a | 核心後端基礎 | 6 | ✅ 完成 |
| Phase 2b | 多代理系統 | 6 | ✅ 完成 |
| Phase 2c | Digital Thread | 3 | ✅ 完成 |
| Phase 2d | 前端分頁 | 7 | ✅ 完成 |
| Phase 2e | 測試與整合 | 5 | ✅ 完成（含修正） |
| **總計** | | **29** | **✅ 完成** |

### 3.2 檔案統計

| 類別 | 檔案數 | 說明 |
|------|--------|------|
| 後端 Python 模組 | ~18 | clinical/、agents/、api/v1/clinical.py |
| 前端 TypeScript/TSX | ~14 | 6 個 Tab 元件 + 對應測試 + API 客戶端 |
| 遷移腳本 | 1 | `016_phase2_clinical_workspace.py` |
| 後端單元測試 | 6 | `test_clinical_context.py`、`test_evidence_collector.py` 等 |
| 後端整合測試 | 2 | `test_phase2_api.py`、`test_phase2_workflow.py` |
| 前端元件測試 | 7 | 6 個 Tab 測試 + `Workbench.test.tsx` |
| **總計** | **~48** | 新增/修改檔案 |

### 3.3 估計工時

| 階段 | 估計工時 | 說明 |
|------|---------|------|
| Phase 2a | ~36h | ClinicalContextBuilder、EvidenceCollector、API |
| Phase 2b | ~48h | 6 個 Agent、ConsensusEngine、RecommendationGenerator |
| Phase 2c | ~18h | 決策節點模型、儲存庫、API |
| Phase 2d | ~32h | 6 個新 Tab 元件、路由、API 客戶端 |
| Phase 2e | ~24h | 單元/整合/E2E 測試 |
| 返工修正 | ~6h | 前端匯出/導入一致性修正 |
| **總計** | **~164h** | |

---

## 4. 核心模組

### 4.1 Clinical Context Builder

| 項目 | 說明 |
|------|------|
| **類別** | `CaseContextBuilder`（`src/backend/clinical/builder.py`） |
| **輸入** | `case_id` → 資料庫讀取 patient、case、variants 等資料 |
| **輸出** | `ClinicalContext`（Pydantic frozen dataclass） |
| **關鍵欄位** | `case_id`, `patient_id`, `age`, `gender`, `diagnosis`, `stage`, `histology`, `cancer_type`, `oncotree_code`, `biomarkers`, `variants`, `treatment_history`, `current_medications`, `allergies`, `ecog_score` |
| **特點** | 所有下游模組消費此上下文，避免重複查詢資料庫；提供 `freeze()` 產生 `context_hash` |

### 4.2 Evidence Collector

| 項目 | 說明 |
|------|------|
| **類別** | `EvidenceCollector`（`src/backend/clinical/collector.py`） |
| **證據來源** | CIViC、ClinVar、PubMed、ClinicalTrials.gov |
| **輸出** | `EvidenceBundle`（含 evidence level、citation、confidence、conflicts） |
| **特點** | 支援按基因查詢、支援非同步並行收集 |

### 4.3 Multi-Agent System

| Agent | 檔案 | 職責 |
|-------|------|------|
| **BaseAgent** | `src/backend/agents/base.py` | 抽象基底類別，定義 `analyze()` 介面 |
| **DiagnosisAgent** | `src/backend/agents/diagnosis_agent.py` | 診斷分析（癌症類型、分期、亞型） |
| **VariantAgent** | `src/backend/agents/variant_agent.py` | 基因變異解讀與 pathogenicity 評估 |
| **DrugAgent** | `src/backend/agents/drug_agent.py` | 藥物匹配與敏感性分析 |
| **ResistanceAgent** | `src/backend/agents/resistance_agent.py` | 抗藥性分析 |
| **GuidelineAgent** | `src/backend/agents/guideline_agent.py` | 臨床指南比對（NCCN/ESMO） |
| **ClinicalTrialAgent** | `src/backend/agents/clinical_trial_agent.py` | 臨床試驗匹配 |
| **AgentOrchestrator** | `src/backend/agents/orchestrator.py` | 協調多 Agent 平行執行 |

### 4.4 Consensus Engine

| 項目 | 說明 |
|------|------|
| **類別** | `ConsensusEngine`（`src/backend/agents/consensus.py`） |
| **方法** | 純規則引擎，Jaccard 相似度衝突檢測 |
| **輸出** | `ConsensusResult`（含 agreement level、conflicts、recommended/alternative options） |
| **agreement 級別** | `high`, `moderate`, `low`, `none` |

### 4.5 Recommendation Generator

| 項目 | 說明 |
|------|------|
| **類別** | `RecommendationGenerator`（`src/backend/clinical/recommendation.py`） |
| **輸出** | 結構化治療推薦（JSON + Markdown 格式） |
| **內容** | First-line、Second-line、Clinical Trial、Benefit/Risk、Monitoring Plan |

### 4.6 Digital Thread

| 項目 | 說明 |
|------|------|
| **核心類別** | `DecisionNode`、`DecisionThreadRepository`、`DecisionThreadInjector` |
| **儲存** | `clinical_decision_nodes` 資料表（關聯式 + JSON snapshot） |
| **節點類型** | `context_built`, `evidence_collected`, `agent_opinion`, `consensus_reached`, `recommendation_generated` |
| **功能** | 完整決策鏈追溯、決策樹查看、單節點查詢 |

### 4.7 Frontend Tabs

| Tab 元件 | 檔案 | 功能 |
|----------|------|------|
| **ContextTab** | `src/frontend/src/components/tabs/ContextTab.tsx` | 顯示 ClinicalContext |
| **EvidenceTab** | `src/frontend/src/components/tabs/EvidenceTab.tsx` | 顯示 EvidenceBundle |
| **AgentsTab** | `src/frontend/src/components/tabs/AgentsTab.tsx` | 顯示 Agent 討論結果 |
| **ConsensusTab** | `src/frontend/src/components/tabs/ConsensusTab.tsx` | 顯示 ConsensusResult |
| **RecommendationTab** | `src/frontend/src/components/tabs/RecommendationTab.tsx` | 顯示治療推薦 |
| **DecisionThreadTab** | `src/frontend/src/components/tabs/DecisionThreadTab.tsx` | 顯示決策線程樹 |

> 所有 Tab 元件統一使用**具名匯出**（`export function X`），並在 `Workbench.tsx` 中以**具名導入**（`import { X } from ...`）引用，確保匯出/導入一致性。

---

## 5. 新增 API 端點

所有端點位於 `src/backend/api/v1/clinical.py`，路由前綴 `/api/v1/clinical`：

| 方法 | 路徑 | 功能 | 回應模型 |
|------|------|------|----------|
| `GET` | `/context/{case_id}` | 獲取 ClinicalContext | `ClinicalContext` |
| `GET` | `/evidence/{case_id}` | 獲取 EvidenceBundle | `EvidenceBundle` |
| `GET` | `/evidence/gene/{gene}` | 按基因查證據 | `EvidenceBundle` |
| `POST` | `/agents/{case_id}` | 運行 Agent 討論 | `list[AgentOpinion]` |
| `POST` | `/consensus/{case_id}` | 運行共識引擎 | `ConsensusResult` |
| `POST` | `/recommend/{case_id}` | 生成治療推薦 | `dict` |
| `POST` | `/analyze/{case_id}` | 完整分析流程 | `dict` |
| `GET` | `/thread/{case_id}` | 獲取決策線程 | `list[DecisionNode]` |
| `GET` | `/thread/{case_id}/tree` | 獲取決策樹 | `list[DecisionNode]` |
| `GET` | `/thread/node/{node_id}` | 獲取單個決策節點 | `DecisionNode` |

### 安全控制

所有端點使用 `Depends(require_case_access(CaseRole.VIEWER))` 進行權限控制，確保只有授權使用者可存取病案資料。

---

## 6. 資料庫遷移

### Migration 016 — Phase 2 Clinical Workspace

| 檔案 | `migrations/versions/016_phase2_clinical_workspace.py` |
|------|--------------------------------------------------------|
| **父遷移** | `015` |
| **新增資料表** | 4 張 |

#### 新增資料表結構

| 資料表 | 主要欄位 | 用途 |
|--------|----------|------|
| `clinical_decision_nodes` | `id`, `case_id`, `parent_id`, `node_type`, `input_snapshot`, `evidence_snapshot`, `agent_id`, `agent_type`, `reasoning`, `confidence`, `decision_label`, `timestamp`, `context_hash` | 決策節點儲存 |
| `clinical_agent_opinions` | `id`, `case_id`, `run_id`, `agent_type`, `agent_version`, `summary`, `pros`, `cons`, `confidence`, `references`, `created_at` | Agent 意見儲存 |
| `clinical_consensus_results` | `id`, `case_id`, `run_id`, `agreement`, `confidence`, `conflicts`, `recommended_option`, `alternative_options`, `unresolved_questions`, `created_at` | 共識結果儲存 |
| `clinical_recommendations` | `id`, `case_id`, `run_id`, `recommendation_type`, `content_json`, `content_markdown`, `rationale`, `confidence`, `created_at` | 治療推薦儲存 |

---

## 7. 新增檔案清單

### 7.1 後端核心

| 檔案 | 說明 |
|------|------|
| `src/backend/clinical/models.py` | ClinicalContext Pydantic 模型 |
| `src/backend/clinical/builder.py` | CaseContextBuilder |
| `src/backend/clinical/collector.py` | EvidenceCollector |
| `src/backend/clinical/evidence_models.py` | 證據相關模型 |
| `src/backend/clinical/recommendation.py` | RecommendationGenerator |
| `src/backend/clinical/decision_thread.py` | DecisionNode + DecisionThreadRepository |
| `src/backend/agents/base.py` | BaseAgent 抽象基底 |
| `src/backend/agents/models.py` | AgentOpinion 模型 |
| `src/backend/agents/orchestrator.py` | AgentOrchestrator |
| `src/backend/agents/diagnosis_agent.py` | DiagnosisAgent |
| `src/backend/agents/variant_agent.py` | VariantAgent |
| `src/backend/agents/drug_agent.py` | DrugAgent |
| `src/backend/agents/resistance_agent.py` | ResistanceAgent |
| `src/backend/agents/guideline_agent.py` | GuidelineAgent |
| `src/backend/agents/clinical_trial_agent.py` | ClinicalTrialAgent |
| `src/backend/agents/consensus.py` | ConsensusEngine + ConsensusResult |
| `src/backend/api/v1/clinical.py` | Phase 2 API 端點 |

### 7.2 前端

| 檔案 | 說明 |
|------|------|
| `src/frontend/src/components/tabs/ContextTab.tsx` | 上下文 Tab |
| `src/frontend/src/components/tabs/EvidenceTab.tsx` | 證據 Tab |
| `src/frontend/src/components/tabs/AgentsTab.tsx` | Agent 討論 Tab |
| `src/frontend/src/components/tabs/ConsensusTab.tsx` | 共識 Tab |
| `src/frontend/src/components/tabs/RecommendationTab.tsx` | 推薦 Tab |
| `src/frontend/src/components/tabs/DecisionThreadTab.tsx` | 決策線程 Tab |
| `src/frontend/src/api/workbench.ts` | API 客戶端（含 Phase 2 端點） |

### 7.3 測試

| 檔案 | 類別 | 說明 |
|------|------|------|
| `tests/unit/test_clinical_context.py` | 單元測試 | ClinicalContext 模型 + CaseContextBuilder（14 個測試） |
| `tests/unit/test_evidence_collector.py` | 單元測試 | EvidenceCollector（mock 外部 API） |
| `tests/unit/test_agents.py` | 單元測試 | BaseAgent + 多個 Agent |
| `tests/unit/test_consensus.py` | 單元測試 | ConsensusEngine（含邊界情況） |
| `tests/unit/test_recommendation.py` | 單元測試 | RecommendationGenerator |
| `tests/unit/test_decision_thread.py` | 單元測試 | DecisionNode + DecisionThreadRepository |
| `tests/integration/test_phase2_api.py` | 整合測試 | 所有 API 端點 |
| `tests/integration/test_phase2_workflow.py` | 整合測試 | 完整管線端到端測試 |
| `src/frontend/src/test/tabs/AgentsTab.test.tsx` | 前端測試 | AgentsTab loading/error/success/empty |
| `src/frontend/src/test/tabs/ConsensusTab.test.tsx` | 前端測試 | ConsensusTab 各狀態 |
| `src/frontend/src/test/tabs/ContextTab.test.tsx` | 前端測試 | ContextTab 各狀態 |
| `src/frontend/src/test/tabs/DecisionThreadTab.test.tsx` | 前端測試 | DecisionThreadTab 各狀態 |
| `src/frontend/src/test/tabs/EvidenceTab.test.tsx` | 前端測試 | EvidenceTab 各狀態 |
| `src/frontend/src/test/tabs/RecommendationTab.test.tsx` | 前端測試 | RecommendationTab 各狀態 |
| `src/frontend/src/test/Workbench.test.tsx` | 前端測試 | Workbench 整合測試 |

### 7.4 遷移

| 檔案 | 說明 |
|------|------|
| `migrations/versions/016_phase2_clinical_workspace.py` | 新增 4 張 Phase 2 資料表 |

---

## 8. 品質評分

### 8.1 首次評分（循環 1）

| 項目 | 分數 | 備註 |
|------|------|------|
| 完整性 | 22/25 | |
| 正確性 | **18/25** | ← 主要問題：前端匯出/導入不一致 |
| 可維護性 | 22/25 | |
| 測試驗證 | 23/25 | |
| **總分** | **85 ❌** | 門檻：90，不合格 |

**關鍵問題**：Workbench.tsx 使用具名導入（`import { ContextTab }`），但 6 個 Tab 元件使用預設匯出（`export default function`），導致匯出/導入不一致。

### 8.2 返工修正後評分（循環 2）

| 項目 | 分數 | 說明 |
|------|------|------|
| 完整性 | 24/25 | 模型、Builder、Collector、6 個 Agent、Engine、Generator、Digital Thread、前端 Tab 完整 |
| 正確性 | 24/25 | 前端匯出/導入已修復；模型/API/非同步/錯誤處理皆正確 |
| 可維護性 | 23/25 | 清晰的模組劃分、完整 docstrings、type hints |
| 測試與驗證 | 23/25 | 14 個測試檔案（6 單元 + 2 整合 + 6 前端 + 1 整合） |
| **總分** | **94 ✅** | 門檻：90，合格 |

**提升**：85 → 94（+9 分），主要改善來自前端匯出/導入不一致的完整修復。

### 8.3 修復範圍

| 修復項目 | 檔案數 | 狀態 |
|----------|--------|------|
| 6 個 Tab 元件改為具名匯出（`export function`） | 6 | ✅ 已修復 |
| 6 個測試檔案改為具名導入（`import { X }`） | 6 | ✅ 已修復 |
| Workbench.tsx import 一致性驗證 | 1 | ✅ 驗證通過 |

---

## 9. 待改進事項

### 🟡 中度問題

1. **ecog_score / allergies 欄位映射不完整**
   - `ClinicalContext` 模型中已定義`ecog_score` 和 `allergies` 欄位，但 `CaseContextBuilder._assemble()` 方法尚未從資料庫讀取這些資料。
   - **建議**：在後續迭代中補齊 Builder 的資料庫查詢邏輯。

2. **Workbench.tsx 檔案過於臃腫**
   - 單一檔案超過 1000 行（實際約 44KB），建議將大型子面板拆分到獨立檔案。
   - **建議**：Phase 3 中重構為更小的模組化元件。

### 🟢 輕微問題

3. **EvidenceCollector 授權來源無替代方案**
   - NCCN、ESMO、OncoKB 等授權來源目前僅返回空結果，無公開 API 替代方案。
   - **建議**：可考慮整合更多開放資料庫（如 Open Targets、PharmGKB）。

4. **部分 Agent 推理邏輯可進一步強化**
   - 目前 Agent 分析基於規則引擎，可考慮引入 LLM 增強（如 GPT-4 / Claude）以提供更深度的推理。
   - **建議**：Phase 3 中可選配 LLM 驅動的 Agent 模式。

5. **前端部分 TypeScript 型別使用 `any`**
   - 部分 API 回應未定義完整介面，使用 `any` 作為型別。
   - **建議**：逐步補齊完整的 TypeScript 介面定義。

6. **缺少授權來源降級處理的測試**
   - 未測試外部 API 全部失效時的降級行為。
   - **建議**：在測試套件中增加降級情景覆蓋。

---

## 10. 附錄：術語對照

| 英文 | 中文 |
|------|------|
| Clinical Context Builder | 臨床上下文建構器 |
| Evidence Collector | 證據收集器 |
| Multi-Agent Discussion | 多代理討論 |
| Consensus Engine | 共識引擎 |
| Recommendation Generator | 治療推薦生成器 |
| Digital Thread | 決策線程（數位線程） |
| ClinicalContext | 臨床上下文 |
| EvidenceBundle | 證據包 |
| AgentOpinion | 代理意見 |
| ConsensusResult | 共識結果 |
| DecisionNode | 決策節點 |
| ECOG Score | ECOG 體能狀態評分 |
| Jaccard Similarity | Jaccard 相似度 |
| ORM / Pydantic | 資料模型框架 |
| Alembic Migration | 資料庫遷移 |

---

> **報告生成日期**: 2026-07-21  
> **下一階段**: Phase 3 — 待規劃（建議方向：LLM 增強推理、UI/UX 優化、更多證據來源整合、Workbench 模組化重構）
