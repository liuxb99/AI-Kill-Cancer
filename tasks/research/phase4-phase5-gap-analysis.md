# Phase 4 & Phase 5 Gap Analysis 報告

> **生成日期**：2026-08-01  
> **分析範圍**：從 tasks/research/current-capability-inventory.md 盤點結果出發，覆蓋 23 個維度  
> **目標**：量化當前狀態與 Phase 4 / Phase 5 目標之間的差距，提供優先級與風險評估  

---

## 目錄

1. [RAG／Evidence Retrieval](#1-ragevidence-retrieval)
2. [Clinical Knowledge Graph Retrieval](#2-clinical-knowledge-graph-retrieval)
3. [NCCN/ESMO/ASCO Guideline Adapter](#3-nccnesmoasco-guideline-adapter)
4. [Literature Evidence Ranking](#4-literature-evidence-ranking)
5. [Clinical Trial Matching](#5-clinical-trial-matching)
6. [Drug Interaction](#6-drug-interaction)
7. [Contraindication Checking](#7-contraindication-checking)
8. [Explainable AI](#8-explainable-ai)
9. [Citation/Provenance](#9-citationprovenance)
10. [Evidence Freshness](#10-evidence-freshness)
11. [FHIR R4](#11-fhir-r4)
12. [HL7/DICOM/PACS](#12-hl7dicom-pacs)
13. [Multi-tenant](#13-multi-tenant)
14. [RBAC/ABAC](#14-rbacabac)
15. [Audit Log](#15-audit-log)
16. [Background Jobs / Queue](#16-background-jobs--queue)
17. [Retry/Dead-letter](#17-retrydead-letter)
18. [Monitoring/Metrics](#18-monitoringmetrics)
19. [Backup/Restore](#19-backuprestore)
20. [Security Gate](#20-security-gate)
21. [Platform Registry](#21-platform-registry--phase-5)
22. [Specialty Module](#22-specialty-module--phase-5)
23. [Oncology Decoupling](#23-oncology-decoupling--phase-5)

---

## 1. RAG／Evidence Retrieval

| 項目 | 內容 |
|---|---|
| **As-Is（現況）** | **🔴 Missing** — 完全無實作。全域 grep "vector\|embedding\|rag\|RAG\|chroma\|pinecone\|weaviate\|qdrant\|langchain" 無生產程式碼匹配。無 Vector DB、無 Embedding pipeline、無 RAG 檢索架構。 |
| **To-Be（目標）** | **Deferred（Phase 5+）** — 原定 Phase 4 建立完整 RAG pipeline，經 ChatGPT 審查後決定推遲。保留語義搜尋與知識增強生成為長期目標，待產品需求明確且有充分證據後再導入。 |
| **Gap（缺口）** | 1. 無 Vector DB 實例與連線<br>2. 無 Embedding 模型／服務<br>3. 無文檔分塊策略與實作<br>4. 無檢索（retriever）元件<br>5. 無 RAG 與 ClinicalReasoningService 的整合<br>6. 無向量索引的管理 API<br><br>**⚠️ ChatGPT 審查決定**：目前無充分證據需要引入 Vector DB / Embedding pipeline。Phase 4 保持 Technology Agnostic，避免過早綁定特定基礎設施。上述缺口暫不處理，待 Phase 5 或更晚重新評估。 |
| **Dependencies（依賴）** | 1. 外部 Vector DB 服務或決定使用嵌入式（如 Chroma embedded）<br>2. Embedding API key 或本地模型部署<br>3. Python 套件：langchain / llama-index / chromadb / qdrant-client<br><br>**（以上依賴項目前全部擱置，不導入任何 Vector DB 相關套件）** |
| **Risks（風險）** | - **技術**：Embedding 模型選擇影響檢索品質；需實驗多種 chunk 策略<br>- **資源**：若使用本地 Embedding 模型需 GPU 資源<br>- **時間**：從零建立約 4-6 週（含整合測試）<br>- **🧭 推遲風險**：Phase 4 階段無法實現語義檢索，關鍵字檢索（現有基礎）可能無法滿足高階查詢需求；此風險已被接受 |
| **Priority（優先級）** | **Deferred（Phase 5+）** — 基於 ChatGPT 審查要求，目前無充分證據需要引入 Vector DB / RAG 基礎設施。保持 Technology Agnostic。 |
| **Blocking（阻擋關係）** | ⏸️ **原阻擋關係暫停**：Evidence Retrieval 語義增強、Guideline Agent 語義匹配、ClinicalTrialAgent 語義搜尋等依賴 RAG 的能力暫不實現，改用關鍵字檢索與現有規則引擎替代方案。 |

---

## 2. Clinical Knowledge Graph Retrieval

| 項目 | 內容 |
|---|---|
| **As-Is（現況）** | **✅ Complete** — KnowGraphGo（13 Go packages, 35+ 測試）作為 Graph 引擎，Python 端透過 `ClinicalGraphClient`（`src/backend/clinical_graph/client.py`）以 subprocess 呼叫 knowgraph CLI 進行事件投影與查詢。API 端點 `src/backend/api/v1/clinical_graph.py` 提供 /status、/query、/explain 等 REST 介面。 |
| **To-Be（目標）** | **Phase 4 結束**：維持現有架構但補強：(1) Python 端應有更高階的 Query Builder，而非直接呼叫 CLI；(2) 將 KnowGraphGo 包裝為獨立 gRPC/REST 服務而非 subprocess 呼叫；(3) 支援 GraphQL 或開放查詢介面供外部消費。 |
| **Gap（缺口）** | 1. KnowGraphGo 目前以 subprocess 執行，缺乏服務化封裝（無 health check、無自動重啟、無連接池）<br>2. Python 端查詢能力有限（僅 client.py 中 query_path / query_related / explain_relation 三個方法）<br>3. 無高階查詢 DSL（如 Cypher-like query）<br>4. 缺乏 Graph 健康監控與即時同步狀態 |
| **Dependencies（依賴）** | 1. Go 編譯工具鏈<br>2. 若改為 gRPC 服務需 protobuf 定義 |
| **Risks（風險）** | - **技術**：subprocess 方式在容器化環境可能不穩定<br>- **資源**：KnowGraphGo 服務化需 DevOps 配置 |
| **Priority（優先級）** | **P2（應該）** — 現有可運作，但服務化可提升穩定性與擴充性 |
| **Blocking（阻擋關係）** | 不阻擋 Phase 4 其他項目；服務化建議延至 Phase 5 執行 |

---

## 3. NCCN/ESMO/ASCO Guideline Adapter

| 項目 | 內容 |
|---|---|
| **As-Is（現況）** | **🟠 Stub** — `src/backend/agents/guideline_agent.py`（19804 bytes）可從 EvidenceBundle 中過濾 guideline 來源的資料項（NCCN, ESMO, ASCO），但 adapter registry（`src/backend/adapters/registry.py`）中**無註冊**任何 guideline 專用 adapter。無專用 NCCN/ESMO/ASCO API 連接。現有 guideline 資料只能透過已匯入的 evidence items 被動使用。 |
| **To-Be（目標）** | **Phase 4 結束**：建立 NCCN／ESMO／ASCO 專用 Adapter，支援：(1) 即時查詢 guideline API，(2) 結構化 guideline 資料擷取與本地快取，(3) guideline 版本管理與更新通知。 |
| **Gap（缺口）** | 1. 無 GuidelineAdapter 類別實作<br>2. 無 NCCN/ESMO/ASCO API 憑證與整合<br>3. 無 guideline 結構化儲存模型（目前僅泛用 EvidenceItem）<br>4. 無 guideline 版本比較與變更追蹤<br>5. GuidelineAgent 現有實作仰賴已匯入的 evidence，無法即時查詢最新 guideline |
| **Dependencies（依賴）** | 1. NCCN 內容 API 授權（需商業許可）<br>2. ESMO / ASCO 公開指南可透過 PubMed 或官方 PDF 取得<br>3. 若無 API，需建立 guideline 結構化匯入 pipeline（PDF parsing + NLP） |
| **Risks（風險）** | - **資源**：NCCN API 需付費授權，可能昂貴<br>- **技術**：Guideline PDF 結構化難度高，NLP 解析不保證 100% 準確<br>- **時間**：真實 adapter 實作約 2-4 週／每個機構 |
| **Priority（優先級）** | **P1（必須）** — Phase 4 核心整合，無真實 guideline 連接則 GuidelineAgent 無實際效用 |
| **Blocking（阻擋關係）** | 不阻擋其他 Phase 4 項目，但 GuidelineAgent 功能受限 |

---

## 4. Literature Evidence Ranking

| 項目 | 內容 |
|---|---|
| **As-Is（現況）** | **✅ Complete** — `src/backend/clinical/drug_ranking.py`（DrugRankingEngine）提供完整 evidence-based drug ranking pipeline。`src/backend/ranking/engine.py`（DrugRankingEngine）整合 6 個 Scorer（EvidenceLevelScorer, GuidelineScorer, ClinicalTrialScorer, RegulatoryScorer, FreshnessScorer, DrugInteractionScorer）。`src/backend/ranking/scorers.py` 包含完整 scorer 實作。 |
| **To-Be（目標）** | **Phase 4 結束**：維持現有架構，建議增強：(1) 加入 LLM-based ranking 作為輔助，(2) 支援可設定權重配置（目前為硬編碼），(3) 排名結果可追溯至每條 evidence 來源。 |
| **Gap（缺口）** | 1. Ranking weights 目前為程式碼內常數，無法動態調整<br>2. 無 A/B testing 框架比較不同 ranking 策略<br>3. 無 ML-based ranking 模型 |
| **Dependencies（依賴）** | 無重大依賴 |
| **Risks（風險）** | - **技術**：權重調整需臨床專家驗證 |
| **Priority（優先級）** | **P3（可延後）** — 現有 ranking 已可運作，增強為 Phase 5 項目 |
| **Blocking（阻擋關係）** | 不阻擋任何項目 |

---

## 5. Clinical Trial Matching

| 項目 | 內容 |
|---|---|
| **As-Is（現況）** | **🟡 Partial** — `src/backend/agents/clinical_trial_agent.py`（18007 bytes）可從 EvidenceBundle 中過濾 trial 資料項，計算 match score（cancer type, stage, variant, biomarker 匹配），並評估 eligibility。但此實作**仰賴已匯入的 trial records**，無即時 ClinicalTrials.gov API 查詢能力。`src/backend/knowledge/adapters/clinicaltrials.py`（3950 bytes）有 ClinicalTrialsAdapter 但**未註冊到 adapter registry**。 |
| **To-Be（目標）** | **Phase 4 結束**：(1) 完成 ClinicalTrialsAdapter 註冊與真實 ClinicalTrials.gov API 整合，(2) 支援結構化 eligibility criteria 匹配（年齡、ECOG、既往治療等），(3) 提供 trial 地理位置篩選，(4) trial 結果快取與定期更新。 |
| **Gap（缺口）** | 1. ClinicalTrialsAdapter 未註冊到 registry，未被 ClinicalTrialAgent 使用<br>2. 無 ClinicalTrials.gov API 真實查詢（現有 adapter 可能為 scaffold）<br>3. Eligibility 匹配過於粗糙（僅年齡／ECOG 基本檢查）<br>4. 無 trial 招募狀態過濾<br>5. 無 trial 結果（outcome）整合到 ranking |
| **Dependencies（依賴）** | 1. ClinicalTrials.gov API 為公開免費，無需授權<br>2. 可能需要建立結構化 eligibility criteria parser |
| **Risks（風險）** | - **技術**：ClinicalTrials.gov API rate limit（~100 req/sec 不需 key）<br>- **時間**：真實 trial matching 約 3-4 週 |
| **Priority（優先級）** | **P1（必須）** — Phase 4 核心功能，臨床試驗匹配為精準腫瘤學關鍵能力 |
| **Blocking（阻擋關係）** | 不阻擋其他 Phase 4 項目，但 ClinicalTrialAgent 目前功能受限 |

---

## 6. Drug Interaction

| 項目 | 內容 |
|---|---|
| **As-Is（現況）** | **✅ Complete** — 完整的藥物交互系統：(1) `src/backend/evidence/domain.py:L104-170` 定義 `DrugInteractionModel`（SQLAlchemy）+ `DrugInteractionResponse`（Pydantic），(2) `src/backend/repositories/drug_interaction_repo.py` 提供完整 CRUD + upsert，(3) `src/backend/pipeline/dgidb_adapter.py` 連接 DGIdb API（REST，真實實作），(4) `src/backend/ranking/scorers.py:L325` `ClinicalTrialScorer` 包含 drug interaction 評分，(5) `src/backend/clinical/decision_rules.py:L293-383` `detect_contrandications()` 檢查 drug interaction 類型。 |
| **To-Be（目標）** | **Phase 4 結束**：維持現有功能，建議增強：(1) 加入 DrugBank 或 OpenFDA 作為輔助來源，(2) 支援多藥物組合交互檢查（>2 drugs），(3) 提供互動式 drug interaction 可視化。 |
| **Gap（缺口）** | 1. 目前僅支援 DGIdb 單一來源<br>2. 多藥物組合交互檢查未實作<br>3. 無藥物交互作用 severity 分級的可視化 |
| **Dependencies（依賴）** | 1. DrugBank 需商業授權<br>2. OpenFDA 為公開 API |
| **Risks（風險）** | - **技術**：多藥物組合交互為 NP-hard 問題，需啟發式演算法 |
| **Priority（優先級）** | **P2（應該）** — 現有功能已可運作，增強為 Phase 4 後期／Phase 5 |
| **Blocking（阻擋關係）** | 不阻擋任何項目 |

---

## 7. Contraindication Checking

| 項目 | 內容 |
|---|---|
| **As-Is（現況）** | **✅ Complete** — `src/backend/clinical/decision_rules.py` 中的 `DecisionRuleSet.detect_contraindications()` 提供完整的禁忌症檢查，涵蓋 4 種類型：(1) `variant_resistance` — 基因變異導致抗藥性，(2) `evidence_contraindication` — 證據來源明確禁忌，(3) `allergy` — 患者過敏記錄，(4) `drug_interaction` — 與現有藥物潛在交互作用。整合在 `ClinicalDecisionEngine`（`src/backend/clinical/clinical_decision_engine.py:L235-265`）與 `TreatmentPlanEngine`（`src/backend/clinical/treatment_plan_engine.py:L432-476`）中。 |
| **To-Be（目標）** | **Phase 4 結束**：維持現有架構，建議增強：(1) 加入外部禁忌症知識庫（如 ONC High Priority Drug Interactions list），(2) 支援結構化 severity 評級（目前已有基本分級），(3) 提供禁忌症 override 工作流（醫師可 override 並記錄原因）。 |
| **Gap（缺口）** | 1. 禁忌症規則目前為規則引擎實作，缺乏外部知識庫整合<br>2. 無 override 審計流程<br>3. 嚴重度分級未標準化 |
| **Dependencies（依賴）** | 無重大依賴 |
| **Risks（風險）** | - **法規**：禁忌症檢查涉及 patient safety，override 流程需符合醫療法規 |
| **Priority（優先級）** | **P3（可延後）** — 現有功能已完整，增強為 Phase 5 |
| **Blocking（阻擋關係）** | 不阻擋任何項目 |

---

## 8. Explainable AI

| 項目 | 內容 |
|---|---|
| **As-Is（現況）** | **✅ Complete** — `src/backend/clinical/explainable_recommendation.py`（23407 bytes）提供完整的 ExplainableEngine：(1) `ReasonItem` — 單一解釋片段，(2) `RecommendationReason` — 單一藥物的完整解釋，(3) `ExplainableEngine` — 從 ranking result 產出解釋結構，(4) `ExplanationFormatter` — 支援 plain text 與 HTML 輸出。整合於 RecommendationService 與 ReportGenerator。 |
| **To-Be（目標）** | **Phase 4 結束**：維持現有架構，建議增強：(1) 支援 LLM 生成自然語言解釋（現為模板驅動），(2) 加入反事實解釋（"若無此變異則藥物 X 將被推薦"），(3) 解釋可視化在前端以 DecisionThreadTab 展示。 |
| **Gap（缺口）** | 1. 解釋目前為模板結構化，缺乏 LLM 增強的自然語言潤飾<br>2. 無反事實（counterfactual）解釋能力<br>3. 前端展示可進一步豐富（圖形化解釋樹） |
| **Dependencies（依賴）** | 1. LLM API key（若引入 LLM 生成） |
| **Risks（風險）** | - **技術**：LLM 生成的解釋可能產生幻覺，需事實校驗 |
| **Priority（優先級）** | **P3（可延後）** — 現有解釋引擎已完整可用，增強為 Phase 5 |
| **Blocking（阻擋關係）** | 不阻擋任何項目 |

---

## 9. Citation/Provenance

| 項目 | 內容 |
|---|---|
| **As-Is（現況）** | **✅ Complete** — 系統各層均有 citation/provenance 追蹤：(1) Agent 層：`src/backend/agents/base.py:L116` 要求 references 含 citation，(2) Reasoning 層：`src/backend/reasoning/validator.py` `EvidenceCitationValidator` 驗證所有 citation 對應真實 evidence，(3) Reporting 層：`src/backend/reporting/builder.py:L42-48` 收集 citations 到報告，(4) Pipeline 層：`src/backend/pipeline/analysis_job.py:L199` 提供完整 provenance，(5) Adapter 層：`src/backend/adapters/base.py:L88` 提供 provenance metadata。 |
| **To-Be（目標）** | **Phase 4 結束**：維持現有架構，建議增強：(1) 支援 W3C PROV-O 標準 provenance 輸出，(2) 加入 citation 格式自動轉換（AMA, APA, Vancouver），(3) 提供 citation 驗證 API（PMID/DOI 自動解析）。 |
| **Gap（缺口）** | 1. 無標準 provenance ontology（如 W3C PROV-O）<br>2. 無多格式 citation 輸出<br>3. 無 PMID/DOI 自動驗證服務 |
| **Dependencies（依賴）** | 1. Crossref API 或 PubMed API 用於 DOI/PMID 解析 |
| **Risks（風險）** | - **時間**：低風險，增量改進 |
| **Priority（優先級）** | **P3（可延後）** — 現有 citation 功能已完整可用 |
| **Blocking（阻擋關係）** | 不阻擋任何項目 |

---

## 10. Evidence Freshness

| 項目 | 內容 |
|---|---|
| **As-Is（現況）** | **🟡 Partial** — `src/backend/ranking/scorers.py:L143-157` 包含 `FreshnessScorer`，根據證據發布年份計算新鮮度分數（>5年=0.7, <2年=1.1, 2-5年=1.0）。但**缺乏系統性的證據 freshness 管理**：(1) 無證據定期更新機制，(2) 無證據版本對比，(3) 無過期證據標記與警示，(4) 無自動重新檢索排程。 |
| **To-Be（目標）** | **Phase 4 結束**：(1) 建立證據來源定期更新 scheduler，(2) 證據版本管理（每次更新保留歷史版本），(3) 過期證據自動降級警示，(4) freshness dashboard 顯示各來源最後更新時間。 |
| **Gap（缺口）** | 1. 無定期更新排程（CIViC, DGIdb, PubMed 等來源）<br>2. 無證據版本模型（目前 evidence items 直接覆蓋）<br>3. 無過期證據標記機制<br>4. 無 freshness 監控儀表板 |
| **Dependencies（依賴）** | 1. Background Jobs / Queue（#16）作為更新排程基礎<br>2. 各來源 API 可用性 |
| **Risks（風險）** | - **技術**：定期更新需避免 API rate limit<br>- **資源**：自動更新需要 Background Jobs 基礎設施 |
| **Priority（優先級）** | **P2（應該）** — Phase 4 中期，與 #16 Background Jobs 配合 |
| **Blocking（阻擋關係）** | 阻擋於 #16 Background Jobs / Queue 完成後始可實作 |

---

## 11. FHIR R4

| 項目 | 內容 |
|---|---|
| **As-Is（現況）** | **🟠 Stub** — `src/backend/reporting/renderer.py:L74-135` 僅有 `FHIRExporter.export()` 產出簡化的 FHIR R4 Bundle（Composition + Section），`src/backend/api/v1/reports.py:L154` 提供 `GET /{report_id}/fhir` 端點。無完整 FHIR R4 資源模型（Patient, Observation, MedicationRequest, DiagnosticReport, Condition, Procedure, etc.），無 FHIR 驗證，無 FHIR Server 整合，無 SMART-on-FHIR 授權。 |
| **To-Be（目標）** | **Phase 4 結束**：建立完整 FHIR R4 相容層：(1) 實作核心 FHIR 資源（Patient, Observation, MedicationRequest, Condition, DiagnosticReport, Procedure, CarePlan），(2) FHIR 資源驗證（fhirpath/fhir-validator），(3) FHIR API 端點（read/search/create/update），(4) 內部模型 ↔ FHIR 資源的雙向映射。 |
| **Gap（缺口）** | 1. 無 FHIR R4 資源模型（從零到至少 7 個核心資源）<br>2. 無 FHIR 序列化／反序列化<br>3. 無 FHIR 驗證邏輯<br>4. 無 FHIR API 端點（目前僅匯出單一 bundle）<br>5. 無 SMART-on-FHIR 授權<br>6. 無內部 domain model ↔ FHIR 映射層 |
| **Dependencies（依賴）** | 1. FHIR Python 套件：fhir.resources / fhirpath / fhir-parser<br>2. HL7 FHIR 規範文件（R4）<br>3. 若需 FHIR Server：HAPI FHIR / Firely Server |
| **Risks（風險）** | - **技術**：FHIR 規範複雜，核心資源映射需大量 domain knowledge<br>- **時間**：完整實作約 6-8 週（含 mapping + API + testing）<br>- **法規**：FHIR 相容性需符合各國法規要求 |
| **Priority（優先級）** | **P1（必須）** — Phase 4 核心互通性功能 |
| **Blocking（阻擋關係）** | 阻擋 Phase 4：醫療系統互通性；不阻擋其他 Phase 4 項目 |

---

## 12. HL7/DICOM/PACS

| 項目 | 內容 |
|---|---|
| **As-Is（現況）** | **🔴 Missing** — 全域 grep "HL7\|hl7\|DICOM\|dicom\|PACS\|pacs" 無 production code 匹配。完全無實作。 |
| **To-Be（目標）** | **Phase 4 結束**：HL7 v2 訊息解析基礎能力（ADT、ORM、ORU 訊息類型），可接收並解析醫院 HL7 訊息。**Phase 5 結束**：DICOM 影像管理、PACS 查詢／擷取（WADO-RS）、完整的 HL7 v2 發送/接收。 |
| **Gap（缺口）** | 1. 無 HL7 v2 訊息解析器<br>2. 無 MLLP 通訊協定支援<br>3. 無 DICOM 檔案解析<br>4. 無 DICOMweb（WADO-RS/QIDO-RS/STOW-RS）支援<br>5. 無 PACS 查詢整合<br>6. 無醫療設備資料整合 |
| **Dependencies（依賴）** | 1. Python HL7 套件：hl7 / python-hl7 / pydicom<br>2. 需 HL7 v2 測試訊息樣本<br>3. PACS 整合需 DICOM conformance statement 評估 |
| **Risks（風險）** | - **技術**：HL7 v2 不同醫療機構實作差異大，需彈性解析<br>- **時間**：HL7 基礎約 3-4 週，DICOM/PACS 約 6-8 週<br>- **法規**：醫療資料傳輸需 HIPAA/GDPR 合規 |
| **Priority（優先級）** | **HL7 P1（必須）Phase 4 / DICOM P2（應該）Phase 5** |
| **Blocking（阻擋關係）** | 不阻擋 Phase 4 其他項目；HL7 基礎可單獨實作 |

---

## 13. Multi-tenant

| 項目 | 內容 |
|---|---|
| **As-Is（現況）** | **🔴 Missing** — 無 multi-tenant 架構實作。全域 grep "multi_tenant\|tenant\|organization\|org_id\|tenant_id" 無生產程式碼匹配（`multi_tenant` 為完全無匹配）。資料庫 Schema 中無 org_id／tenant_id 欄位。 |
| **To-Be（目標）** | **Phase 5 結束**：(1) 多租戶資料隔離（Schema-per-tenant 或 Row-level tenant isolation），(2) 租戶註冊與管理 API，(3) 租戶層級配置（品牌、功能開關、費率限制），(4) 跨租戶管理員功能。 |
| **Gap（缺口）** | 1. 無 tenant context 模型與中介層<br>2. 資料庫 Schema 無 tenant 隔離欄位<br>3. 所有 Repository query 無 tenant 過濾<br>4. 無租戶 onboarding 流程<br>5. Auth 系統無組織層級 |
| **Dependencies（依賴）** | 1. #14 RBAC/ABAC 需擴充組織層級<br>2. 資料庫 migration 需重新設計 |
| **Risks（風險）** | - **技術**：從單租戶到多租戶為架構級改造，可能需大量重構<br>- **時間**：完整改造約 8-12 週<br>- **資源**：Schema-per-tenant 方式會增加運維複雜度 |
| **Priority（優先級）** | **P0（阻擋）Phase 5** — Phase 5 核心平台功能 |
| **Blocking（阻擋關係）** | Phase 5 多租戶為 Platform Registry（#21）與 Specialty Module（#22）之前置條件 |

---

## 14. RBAC/ABAC

| 項目 | 內容 |
|---|---|
| **As-Is（現況）** | **🟡 Partial** — 已有完整 RBAC（6 角色：admin, oncologist, researcher, nurse, readonly, system）：`src/backend/auth/models.py` 定義 Role/Permission/ROLE_PERMISSIONS 映射。JWT 認證（`auth/service.py`）與 Case ACL（`auth/case_acl_service.py`）提供案例層級存取控制。但**缺乏真正的 ABAC（Attribute-Based Access Control）**：(1) 無屬性評估引擎，(2) 無動態政策（如「僅主治醫師可修改自己的治療計畫」），(3) 無資源層級權限（如特定欄位可見性）。 |
| **To-Be（目標）** | **Phase 4 結束**：(1) 引入 ABAC 政策引擎（如 OPA / Casbin），(2) 資源層級存取控制（欄位級可見性），(3) 動態政策定義 API。**Phase 5 結束**：組織層級 RBAC/ABAC 與 Multi-tenant 整合。 |
| **Gap（缺口）** | 1. 無 ABAC 政策引擎<br>2. 無動態政策定義與管理<br>3. 資源層級（欄位級）權限未實作<br>4. 無政策評估日誌<br>5. Role 為靜態定義，無法動態組合 |
| **Dependencies（依賴）** | 1. 外部政策引擎：OPA（Rego）或 Casbin（Python）<br>2. #13 Multi-tenant 用於組織層級 |
| **Risks（風險）** | - **技術**：ABAC 政策可能複雜，需謹慎設計政策模型<br>- **時間**：ABAC 基礎約 4-6 週 |
| **Priority（優先級）** | **ABAC P1（必須）Phase 4 / 組織層級 RBAC P2 Phase 5** |
| **Blocking（阻擋關係）** | 阻擋 Phase 4：資源層級安全控制需 ABAC 支援 |

---

## 15. Audit Log

| 項目 | 內容 |
|---|---|
| **As-Is（現況）** | **✅ Complete** — `src/backend/domain/audit_log.py` 定義 `AuditLogModel`（含 actor_id, action, resource_type, resource_id, details, ip_address, user_agent, timestamp）。`src/backend/observability/audit.py` 提供 `AuditLogger` 實作。API 層透過 `require_auth` 等 decorator 自動記錄關鍵操作。 |
| **To-Be（目標）** | **Phase 4 結束**：維持現有架構，建議增強：(1) Audit Log 查詢 UI（過濾、搜尋、匯出），(2) 不可篡改儲存（append-only table + hash chain），(3) 整合監控系統（告警異常操作）。 |
| **Gap（缺口）** | 1. 無 Audit Log 前端查詢介面<br>2. 無 hash chain 防篡改機制<br>3. 無異常操作告警<br>4. 無 log 保留政策（retention policy） |
| **Dependencies（依賴）** | 1. #18 Monitoring/Metrics 用於告警 |
| **Risks（風險）** | - **時間**：低風險，增量改進 |
| **Priority（優先級）** | **P2（應該）** — Phase 4 後期／Phase 5 |
| **Blocking（阻擋關係）** | 不阻擋任何項目 |

---

## 16. Background Jobs / Queue

| 項目 | 內容 |
|---|---|
| **As-Is（現況）** | **✅ Complete（Phase 4）** — 原有 Transactional Outbox Pattern（Clinical Graph 事件投影）持續運作。Phase 4 B4（Infrastructure & Observability）已實作 general-purpose job queue：
- **實作方式**：ARQ + Redis，非同步任務佇列
- **Job API**：`src/backend/api/v1/jobs.py` 提供 enqueue / status / cancel 端點
- **Scheduler**：`src/backend/jobs/scheduler.py` 支援 cron-like 定期任務（evidence freshness update、guideline sync）
- **Retry/Dead-letter 泛化**：`src/backend/jobs/retry_policy.py` 將 Outbox 設計模式泛化，支援可設定 max_retries、exponential backoff、dead-letter 自動標記
- **Worker**：`src/backend/jobs/worker.py` ARQ worker 啟動腳本
- **Redis 服務**：透過 `docker-compose.redis.yml` 一鍵啟動 |
| **To-Be（目標）** | **Phase 4 結束**：已達成 — (1) ARQ + Redis job queue 整合完成，(2) Job 註冊／排程／取消 API 完成，(3) 定期任務排程器完成，(4) Job 狀態監控儀表板透過 Grafana（B4）實現。 |
| **Gap（缺口）** | ✅ **已透過 Phase 4 B4（Infrastructure & Observability）實現**：
- ❌ 無 job queue 基礎設施 → ✅ ARQ + Redis 已實作
- ❌ 無定期排程器 → ✅ Scheduler 已實作
- ❌ 無 job 管理 API → ✅ Job API 已實作
- ❌ 無 job 狀態持久化與查詢 → ✅ Redis + API 查詢已實作
- ❌ 無 task 優先級支援 → ⚠️ 基本優先級支援（ARQ 原生），進階優先級佇列待 Phase 5 強化 |
| **Dependencies（依賴）** | 1. ✅ Redis 服務（已透過 docker-compose.redis.yml 納管）<br>2. ✅ Python 套件：arq / redis（已引入） |
| **Risks（風險）** | - ✅ ARQ 已選定，風險已緩解（ARQ 輕量、足以支撐 Phase 4 需求）<br>- ✅ Redis 運維成本低（Docker 一鍵啟動） |
| **Priority（優先級）** | **P1（必須） — ✅ 已實現** |
| **Blocking（阻擋關係）** | ✅ 已解除 — Background Jobs 基礎設施完成後，#10 Evidence Freshness 與 #3 Guideline Adapter 可基於此執行定期更新；#17 Retry/Dead-letter 泛化也已隨 B4 一併實現 |

---

## 17. Retry/Dead-letter

| 項目 | 內容 |
|---|---|
| **As-Is（現況）** | **✅ Complete** — ClinicalGraphOutbox 有完整的重試與死信機制：`src/backend/clinical_graph/retry_policy.py` 定義 `DEFAULT_RETRY_POLICY`（exponential backoff, max_attempts=5）。`src/backend/repositories/clinical_graph_outbox_repo.py` 支援 `mark_failed()`、自動 dead-letter（超過 max_attempts 標記為 `dead_letter`）、`release_stale()` 超時釋放。`src/backend/api/v1/clinical_graph.py` 提供 dead-letter 查詢端點。 |
| **To-Be（目標）** | **Phase 4 結束**：保留 outbox retry 機制，並擴充至 general job queue（#16）。(1) job queue 層支援 retry 策略配置，(2) 支援 dead-letter queue 管理 UI，(3) 支援手動重試 dead-letter job。 |
| **Gap（缺口）** | 1. Retry 機制僅限 ClinicalGraphOutbox，未泛化<br>2. 無 dead-letter 管理 UI<br>3. 無手動重試 API |
| **Dependencies（依賴）** | 1. #16 Background Jobs / Queue |
| **Risks（風險）** | - **時間**：低風險，可複用 outbox 設計模式 |
| **Priority（優先級）** | **P2（應該）** — Phase 4 後期，與 #16 配套 |
| **Blocking（阻擋關係）** | 阻擋於 #16 Background Jobs 完成後 |

---

## 18. Monitoring/Metrics

| 項目 | 內容 |
|---|---|
| **As-Is（現況）** | **🟡 Partial** — `src/backend/observability/` 包含 (1) `audit.py` — AuditLogger，(2) `__init__.py` 匯出 HealthChecker/HealthStatus。`src/backend/api/v1/` 有 health check 端點。但**缺乏生產級監控**：(1) 無 Prometheus metrics（request count, latency, error rate），(2) 無 OpenTelemetry tracing，(3) 無 profiling，(4) 無 log aggregation 整合。 |
| **To-Be（目標）** | **Phase 4 結束**：(1) Prometheus metrics 整合（request duration, throughput, error rates, business metrics），(2) 關鍵端點與引擎的 OpenTelemetry tracing，(3) Grafana dashboard，(4) 自訂 business metrics（recommendations generated, trials matched, etc.）。 |
| **Gap（缺口）** | 1. 無 metrics 收集（無 Prometheus client）<br>2. 無 distributed tracing（無 OpenTelemetry）<br>3. 無儀表板（無 Grafana）<br>4. 無業務層 KPI 監控<br>5. 無 log 聚合（如 ELK/Loki） |
| **Dependencies（依賴）** | 1. Prometheus + Grafana 服務<br>2. Python 套件：prometheus-client / opentelemetry-api / opentelemetry-sdk |
| **Risks（風險）** | - **技術**：Tracing 可能影響效能，需採樣策略<br>- **資源**：需維運 Prometheus + Grafana |
| **Priority（優先級）** | **P1（必須）** — Phase 4 基礎設施，生產環境必要 |
| **Blocking（阻擋關係）** | 不阻擋其他 Phase 4 功能開發，但上線前必須完成 |

---

## 19. Backup/Restore

| 項目 | 內容 |
|---|---|
| **As-Is（現況）** | **🔴 Missing** — 無備份還原機制實作。無備份腳本、無自動排程、無備份驗證。 |
| **To-Be（目標）** | **Phase 4 結束**：(1) 資料庫自動備份腳本（支援 SQLite 與 PostgreSQL），(2) 備份排程（cron job 或 job queue），(3) 備份驗證與完整性檢查，(4) 還原流程文件。**Phase 5 結束**：point-in-time recovery、跨區域備份。 |
| **Gap（缺口）** | 1. 無備份腳本<br>2. 無備份排程<br>3. 無備份儲存管理（本地／S3）<br>4. 無還原流程（手動或自動）<br>5. 無備份監控與告警 |
| **Dependencies（依賴）** | 1. #16 Background Jobs 用於排程備份<br>2. 備份儲存（S3 bucket 或本地磁碟） |
| **Risks（風險）** | - **資源**：備份儲存成本<br>- **風險**：無備份為生產環境重大風險 |
| **Priority（優先級）** | **P1（必須）** — Phase 4 上線前必須完成 |
| **Blocking（阻擋關係）** | 不阻擋功能開發，但阻擋正式上線 |

---

## 20. Security Gate

| 項目 | 內容 |
|---|---|
| **As-Is（現況）** | **🔴 Missing** — 無安全閘門機制。無 SAST/DAST 整合、無 dependency vulnerability scanning、無 secrets detection、無 container image scanning。 |
| **To-Be（目標）** | **Phase 4 結束**：(1) CI/CD pipeline 整合 SAST（如 Semgrep/Bandit），(2) Dependency scanning（pip-audit / Snyk），(3) Secrets detection（truffleHog / git-secrets），(4) 安全政策定義與強制執行。**Phase 5 結束**：DAST、container scanning、SBOM 產出。 |
| **Gap（缺口）** | 1. CI 中無安全掃描步驟<br>2. 無 dependency vulnerability 檢查<br>3. 無 secrets 洩漏檢測<br>4. 無安全政策定義<br>5. 無 SBOM（軟體物料清單） |
| **Dependencies（依賴）** | 1. CI/CD pipeline（GitHub Actions）已存在，需擴充 |
| **Risks（風險）** | - **時間**：SAST 整合約 1-2 週<br>- **風險**：無安全閘門可能導致漏洞流入生產 |
| **Priority（優先級）** | **P1（必須）** — Phase 4 上線前必須完成 |
| **Blocking（阻擋關係）** | 不阻擋功能開發，但阻擋正式上線 |

---

## 21. Platform Registry（Phase 5）

| 項目 | 內容 |
|---|---|
| **As-Is（現況）** | **🔴 Missing** — 無平台註冊表機制。無服務發現、無模組註冊、無擴充點定義。 |
| **To-Be（目標）** | **Phase 5 結束**：(1) 平台模組註冊 API（module name, version, health check, dependencies），(2) 擴充點（extension point）機制允許第三方開發外掛，(3) 平台模組依賴解析與啟動順序管理，(4) 模組市場／目錄。 |
| **Gap（缺口）** | 1. 無模組定義與註冊結構<br>2. 無擴充點 SPI<br>3. 無模組生命週期管理<br>4. 無版本相容性檢查 |
| **Dependencies（依賴）** | 1. #13 Multi-tenant 基礎<br>2. #14 RBAC/ABAC 平台層級 |
| **Risks（風險）** | - **技術**：擴充點設計為架構級決策，需謹慎<br>- **時間**：約 6-8 週 |
| **Priority（優先級）** | **P0（阻擋）Phase 5** — Phase 5 平台化核心 |
| **Blocking（阻擋關係）** | 阻擋 Phase 5：#22 Specialty Module 與 #23 Oncology Decoupling 依賴此 registry |

---

## 22. Specialty Module（Phase 5）

| 項目 | 內容 |
|---|---|
| **As-Is（現況）** | **🔴 Missing** — 無專科模組架構。所有功能為腫瘤學專用，無法擴充至其他專科。 |
| **To-Be（目標）** | **Phase 5 結束**：(1) 專科模組框架（定義 specialty module 的 scaffold/generator），(2) 領域模型可插拔（不同專科有不同模型），(3) 專科特定的 guideline adapter、scoring、ranking，(4) 支援心臟科、神經科等模組擴充。 |
| **Gap（缺口）** | 1. 無模組化架構<br>2. 領域模型緊耦合腫瘤學<br>3. 無專科特定的擴充點<br>4. 現有 oncology 邏輯未抽離為模組 |
| **Dependencies（依賴）** | 1. #21 Platform Registry<br>2. #23 Oncology Decoupling |
| **Risks（風險）** | - **技術**：專科模組框架需從平台註冊表與 decoupling 基礎上建構<br>- **時間**：約 8-12 週 |
| **Priority（優先級）** | **P0（阻擋）Phase 5** — Phase 5 核心交付 |
| **Blocking（阻擋關係）** | 阻擋於 #21 與 #23 完成後 |

---

## 23. Oncology Decoupling（Phase 5）

| 項目 | 內容 |
|---|---|
| **As-Is（現況）** | **🤔 需分析** — 目前整個系統與腫瘤學領域緊耦合：(1) `src/backend/domain/cancer_case.py` — 癌種特定模型，(2) `src/backend/domain/variant.py` — 基因變異模型（腫瘤學核心），(3) `src/backend/domain/enums.py` 中 CancerTypeEnum, VariantTypeEnum 等為腫瘤學專用，(4) Pipeline（VCF, CIViC, DGIdb）為腫瘤基因體學專用，(5) Agents（GuidelineAgent, ClinicalTrialAgent）雖可用其他專科領域但實作邏輯為腫瘤學導向。 |
| **To-Be（目標）** | **Phase 5 結束**：(1) 將核心 platform 功能與 oncology-specific 邏輯分離，(2) Oncology 模組化（作為一個 specialty module 存在），(3) Platform core 提供泛用臨床決策框架，(4) Oncology 特有的 model、engine、pipeline 封裝為可拔插模組。 |
| **Gap（缺口）** | 1. 無領域模型抽象層（domain model 直接使用 oncology 類型）<br>2. 引擎（ClinicalDecisionEngine, DrugRankingEngine）為 oncology 專用<br>3. Pipeline（VCF, CIViC, DGIdb）為腫瘤基因體學專用<br>4. Agents 雖泛用但實作傾向 oncology<br>5. Enum 類型包含大量 oncology 特定值<br>6. 資料庫 schema 含 oncology 特定欄位 |
| **Dependencies（依賴）** | 1. #21 Platform Registry<br>2. #22 Specialty Module 框架 |
| **Risks（風險）** | - **技術**：Decoupling 為大規模重構，需在不中斷現有功能下進行<br>- **時間**：約 10-16 週<br>- **資源**：需資深架構師主導 |
| **Priority（優先級）** | **P0（阻擋）Phase 5** — Phase 5 關鍵架構改造 |
| **Blocking（阻擋關係）** | 阻擋於 #21 Platform Registry 後；為 #22 Specialty Module 之前置 |

---

## 總結：優先級矩陣

### ⚠️ Phase 4 範圍變更（基於 ChatGPT 審查）

經 ChatGPT 審查 Master Plan 後，Phase 4 範圍進行以下調整：

| 變更類型 | 項目 | 原狀態 | 新狀態 | 原因 |
|---------|------|--------|--------|------|
| **Deferred** | #1 RAG／Evidence Retrieval | Phase 4 P0 必須 | **Deferred to Phase 5+** | 無充分證據需要引入 Vector DB；保持 Technology Agnostic |
| **Out of Scope** | treatment_plan_service.py 大型 Service Refactor | 未明確列出但假設為 Phase 4 | **Out of Scope** | 非產品能力；內部重構不阻擋產品化 |
| **Out of Scope** | Frontend 產品化強化（大規模 UI 重構） | 未明確列出但假設為 Phase 4 | **Out of Scope** | 非 Phase 4 核心產品能力；前端維持現有功能迭代 |
| **保持** | 其餘 Phase 4 項目 | — | 不變 | — |

> **總體原則**：Phase 4 只保留**真正阻擋產品化**的核心能力，移除所有大型 Service Refactor 與 Frontend 重構。RAG/Vector DB 相關能力降級為 Deferred，待 Phase 5 或更晚有明確需求時再導入。

### Phase 4 必須完成（P0/P1）

| 優先級 | 維度 | 估計工時 | 阻擋關係 |
|--------|------|----------|----------|
| **P0** | #16 Background Jobs / Queue | 2-3 週 | 阻擋 #10 |
| **P1** | #3 NCCN/ESMO/ASCO Guideline Adapter | 2-4 週 | 不阻擋但 GuidelineAgent 受限 |
| **P1** | #5 Clinical Trial Matching | 3-4 週 | 不阻擋但 TrialAgent 受限 |
| **P1** | #11 FHIR R4 | 6-8 週 | 阻擋互通性 |
| **P1** | #14 RBAC/ABAC | 4-6 週 | 阻擋資源層級安全 |
| **P1** | #18 Monitoring/Metrics | 3-4 週 | 上線必要條件 |
| **P1** | #19 Backup/Restore | 1-2 週 | 上線必要條件 |
| **P1** | #20 Security Gate | 1-2 週 | 上線必要條件 |

### Phase 4 應該完成（P2）

| 優先級 | 維度 | 估計工時 | 附註 |
|--------|------|----------|------|
| **P2** | #10 Evidence Freshness | 2-3 週 | 需 #16 完成 |
| **P2** | #17 Retry/Dead-letter (泛化) | 1 週 | 需 #16 完成 |
| **P2** | #6 Drug Interaction (增強) | 1-2 週 | 非必要 |
| **P2** | #15 Audit Log (增強) | 1-2 週 | 非必要 |
| **P2** | #2 Clinical Knowledge Graph (服務化) | 3-4 週 | 可延至 Phase 5 |

### Phase 4 可延後（P3）

| 優先級 | 維度 | 附註 |
|--------|------|------|
| **P3** | #4 Literature Evidence Ranking (增強) | 現有可運作 |
| **P3** | #7 Contraindication Checking (增強) | 現有可運作 |
| **P3** | #8 Explainable AI (增強) | 現有可運作 |
| **P3** | #9 Citation/Provenance (增強) | 現有可運作 |

### Deferred（Phase 5+）

| 優先級 | 維度 | 附註 |
|--------|------|------|
| **Deferred** | #1 RAG／Evidence Retrieval | 基於 ChatGPT 審查要求推遲；保持 Technology Agnostic；待產品需求明確後重新評估 |

### Phase 5 必須完成（P0）

| 優先級 | 維度 | 估計工時 | 阻擋關係 |
|--------|------|----------|----------|
| **P0** | #13 Multi-tenant | 8-12 週 | 阻擋 #21 |
| **P0** | #21 Platform Registry | 6-8 週 | 阻擋 #22, #23 |
| **P0** | #22 Specialty Module | 8-12 週 | 需 #21, #23 |
| **P0** | #23 Oncology Decoupling | 10-16 週 | 需 #21 |
| **P2** | #12 HL7/DICOM/PACS (DICOM) | 6-8 週 | 非必要但建議 |
| **P2** | #14 RBAC/ABAC (組織層級) | 3-4 週 | 需 #13 |

---

## 關鍵風險摘要

1. **FHIR R4 複雜度風險**：醫療互操作性標準實作需大量領域知識，建議優先導入核心資源集（Patient, Observation, MedicationRequest）並逐步擴充。
2. ~~**RAG 技術選擇風險**：Vector DB 與 Embedding 模型選擇影響深遠，建議 Phase 4 初期進行 PoC 比較多種方案。~~  
   **（已降級）** RAG 已被 Deferred to Phase 5+，此風險不再適用於 Phase 4。Phase 4 維持關鍵字檢索與規則引擎方案。
3. **NCCN API 授權風險**：需確認商業授權成本與可用性，備案為手動結構化 guideline PDF。
4. **Oncology Decoupling 架構風險**：Phase 5 最大風險項，建議 Phase 4 後期即開始架構設計，避免 Phase 5 前期探索。
5. **HL7 實作差異風險**：不同醫療機構 HL7 v2 實作差異大，建議以彈性 parser 為目標而非 strict validation。

---

*本報告基於 tasks/research/current-capability-inventory.md 盤點結果，並經由實際程式碼路徑驗證。*
