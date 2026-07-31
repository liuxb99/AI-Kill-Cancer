# Phase 4 & Phase 5 Master Plan 规划需求

> 本文件定義 Phase 4 與 Phase 5 的 Master Plan 規劃任務範圍、產出交付物、品質標準與禁止事項。

---

## 1. 任務名稱

**Phase 4 & Phase 5 Master Plan 規劃**

---

## 2. 當前狀態

| 項目 | 狀態 |
|------|------|
| Phase 1～3E | ✅ 已完成 |
| Phase 3F-0 Transaction Boundary Hardening | ✅ 正式 Accepted |
| master 分支合併 | ✅ 已完成 |
| 原 Phase 4 / 5 / 6 / 7 四個獨立大階段 | 🔄 合併為兩大階段（詳下） |

---

## 3. 新階段總覽

### Phase 4：Clinical AI Productization

> 合併原本 Clinical Intelligence + Hospital Integration + Production Platform

**目標**：按大型端到端 Vertical Slice 推進，每個 Slice 包含：
- Clinical AI
- Evidence
- Knowledge Graph
- Hospital Integration
- Security / Audit
- Persistence
- Observability
- CI
- Frontend
- Deployment readiness

### Phase 5：Medical AI Platform

> 將 AI-Kill-Cancer 從 Oncology application 提升為可支援多疾病、多專科的 Medical AI Platform

**目標**：
- Oncology 耦合盤點與解耦
- Registry / Plugin 化架構
- Specialty Module Contract 定義
- 多疾病、多專科支援能力

---

## 4. 本輪任務範圍

**只產出規劃與架構文件，不修改 production code。**

必須產出以下文件（共 7 項）：

### 4.1 專案現況盤點

**文件**：`tasks/research/current-capability-inventory.md`

盤點項目（每項標示狀態）：

| 盤點維度 | 狀態標籤選項 |
|----------|-------------|
| Domain / Service / Repository / API / Engine / Frontend | Complete / Partial / Stub / Missing / TechDebt |
| Migration / CI / Auth / Audit / KG / DT / Outbox / Background / Deployment / FHIR / RAG | Complete / Partial / Stub / Missing / TechDebt |

### 4.2 Gap Analysis

**文件**：`tasks/research/phase4-phase5-gap-analysis.md`

內容須包含：
- 現況（As-Is）
- 目標（To-Be）
- 缺口（Gap）
- 依賴（Dependencies）
- 風險（Risks）
- 優先級（Priority）
- 阻擋關係（Blocking Relationships）

### 4.3 Phase 4 Master Plan

**文件**：`tasks/plan-phase4-clinical-ai-productization.md`

內容須包含：
- 最終能力描述
- 架構設計
- Data Flow
- Component Diagram
- Security / FHIR / KG / Deployment Boundary
- Batch 拆分（每個 Batch 10～25 files）
- 驗收標準（Acceptance Criteria）

### 4.4 Phase 5 Master Plan

**文件**：`tasks/plan-phase5-medical-ai-platform.md`

內容須包含：
- Oncology 耦合盤點
- Registry / Plugin 化設計
- Specialty Module Contract
- Batch 拆分

### 4.5 Dependency Map

**文件**：`tasks/phase4-phase5-dependency-map.md`

內容須標示：
- 可並行（Parallel）任務
- 串行（Sequential）任務
- 外部依賴（External Dependencies）

### 4.6 Development Roadmap

**文件**：`tasks/roadmap-phase4-phase5.md`

以 **Batch** 和 **Gate** 表示開發路線圖。

### 4.7 Architecture Decision Records（ADR）

**原則**：只建立確實必要的 ADR，不要為了數量大量產生空文件。

---

## 5. 加速原則

1. **不再把任務切成過小步驟**
2. **每次完成一個大型 Vertical Batch**
3. **子代理可並行處理互不衝突的模組**
4. **中途不要頻繁詢問使用者**
5. **完成後統一執行以下檢查與提交流程**：
   - Lint
   - Unit tests
   - PostgreSQL tests
   - Integration tests
   - Frontend 驗證
   - Migration gate
   - Security gate
   - Reviewer 審查
   - Commit + Push
6. **每批 production scope 原則為 10～25 files**

---

## 6. Reviewer 評分標準

| 評分維度 | 權重 |
|----------|------|
| 完整性（Completeness） | 25 |
| 正確性（Correctness） | 25 |
| 可執行性（Executability） | 25 |
| 架構與風險控制（Architecture & Risk Control） | 25 |
| **總分** | **100** |

- **總分低於 90 必須返工**

### 額外 Gate

| Gate 名稱 | 說明 |
|-----------|------|
| Current State Evidence Gate | 必須基於真實專案現況，不可虛構 |
| Vertical Slice Quality Gate | 每個 Vertical Slice 須完整涵蓋所有層面 |
| Dependency Gate | 依賴關係須明確且無循環依賴 |
| Scope Control Gate | 不得超出規劃範圍 |
| Phase 4 Feasibility Gate | Phase 4 規劃必須在技術與資源上可行 |
| Phase 5 Platformization Gate | Phase 5 須真正達成平台化，非僅 rename |

---

## 7. 禁止事項

| # | 禁止事項 |
|---|---------|
| 1 | ❌ 禁止開始寫 production code |
| 2 | ❌ 禁止建立大量空殼 API 或 placeholder frontend |
| 3 | ❌ 禁止一開始就做 Kubernetes 或拆 microservices |
| 4 | ❌ 禁止無證據引入 Kafka / Redis / Vector DB |
| 5 | ❌ 禁止虛構已有能力 |
| 6 | ❌ 禁止使用 mock 結果宣稱 integration ready |

---

## 8. 交付檢查清單

- [ ] `tasks/research/current-capability-inventory.md`
- [ ] `tasks/research/phase4-phase5-gap-analysis.md`
- [ ] `tasks/plan-phase4-clinical-ai-productization.md`
- [ ] `tasks/plan-phase5-medical-ai-platform.md`
- [ ] `tasks/phase4-phase5-dependency-map.md`
- [ ] `tasks/roadmap-phase4-phase5.md`
- [ ] Architecture Decision Records（必要才建立）

---

# 附錄 A：ChatGPT 正式審查結果（Accepted = NO）

> 審查時間：2026-07-31  
> 審查者：ChatGPT（GitHub Connector）  
> 判定：**Accepted = NO**  
> 原因：Batch 拆分策略違反本專案加速原則（Vertical Slice）

## A.1 必須修正：Phase 4 Batch 拆分策略

**現狀**（6 個技術模組拆分）：

```
B1 FHIR R4
B2 External Adapters
B3 RAG & Semantic
B4 Production Observability
B5 Docker + CI/CD
B6 Frontend Productization
```

**改為**（3 個 Vertical Slice Batch，每個 Batch 都包含完整技術棧）：

每個 Batch 必須包含：API + Domain + Service + Repository + Frontend + Audit + Knowledge Graph + Digital Thread + CI + PostgreSQL + Migration + Documentation

範例：

| Batch | 能力流 |
|-------|--------|
| B1 | Patient Import → Evidence → Recommendation → Treatment Plan → FHIR Export → Audit → Frontend |
| B2 | Clinical Trial → Evidence Ranking → Recommendation → Treatment Update → CarePlan → Frontend |
| B3 | Drug Safety → Interaction → Contraindication → Treatment Revision → Monitoring → FHIR Export |

## A.2 必須修正：Transaction Boundary

- ❌ 禁止：`Repository transaction owner`
- ✅ 改為：**Service owns transaction**
- Repository：flush only, No commit, No rollback
- 須與 Phase 3F-0 完全一致

## A.3 必須修正：Adapter 分類

❌ 不得全部 fire-and-forget

重新分類：
- **同步**：Evidence Retrieval, Clinical Decision
- **非同步**：Guideline Sync, Background Refresh, Cache Refresh

## A.4 禁止新增基礎元件

除非 Gap Analysis + ADR + Current Capability 三者共同證明真正需要，否則：
- 禁止 Redis
- 禁止 Kafka
- 禁止 Vector DB（Qdrant / Chroma）
- 保持 Technology Agnostic

## A.5 Scope 控制

Phase 4 只留下：
- 真正阻擋產品化的能力
- ❌ 不要把大型 Service Refactor、Frontend 重構混入（那些不是產品能力）

## A.6 Phase 5 平台化

最多 2～3 個 Batch，不得十幾個。

## A.7 Reviewer 範圍

重新 Step 6 + Step 7，只重評：
- Batch Design
- Scope
- Architecture

不用重跑全部。

## A.8 完成後

- ❌ 不要 commit
- ⏸️ 等待 ChatGPT 第二次審查

---

# 附錄 B：REVIEW-PHASE3F0-R3 返工需求（正式）

> 來源：ChatGPT 透過 GitHub Connector 在原始碼中加入的 REVIEW 註解（commit 8b502fe、3e75eb0，已 pull 至 master）
> 協作流程：`docs/chatgpt-deepseek-inline-review-workflow.md`
> 執行規則：逐條完成實際代碼修正，不得只修改註解狀態；保留原 REVIEW 註解，完成後改為 REVIEW-RESOLVED 並附 RESOLUTION 說明。

---

## B.1 REVIEW-PHASE3F0-R3-P0-01 / OPEN（阻斷性）

**位置**：`src/backend/database/session.py`（get_db 內，L13-21）

### 問題
- 目前 `get_db()` 會在請求成功後自動 commit（`await session.commit()`，L22）
- 但 `EvidenceIngestionService`、`VariantIngestionService` 等 Service 也自行 commit/rollback
- 造成同一請求存在**兩個 transaction owner**，與 Phase 3F-0 選定的「Service 層明確管理交易」模式衝突

### 修改要求
統一 transaction ownership。採 Service-owned transaction 模式：
1. **移除 get_db() 的自動 commit**
2. **盤點所有直接注入 db 的寫入 endpoint**，確保它們改由 Service 管理 transaction
3. **不得**以 dependency auto-commit 補救缺少 Service transaction 的 API

### 驗證要求（新增測試）
1. Service 成功只 commit 一次
2. Service 後段失敗完整 rollback
3. endpoint 在 Service 返回後發生例外時，不會留下部分提交資料

### 已盤點的直接寫入 db endpoint（A 類：無 Service 層，全靠 get_db auto-commit，共 13 處）
| 檔案 | endpoint | 方法 |
|------|----------|------|
| `src/backend/api/v1/patients.py` | create_patient / update_patient / delete_patient | POST/PATCH/DELETE |
| `src/backend/api/v1/specimens.py` | create_specimen | POST |
| `src/backend/api/v1/sequencing.py` | create_sequencing_test | POST |
| `src/backend/api/v1/cases.py` | create_case / update_case / delete_case | POST/PUT/DELETE |
| `src/backend/api/v1/case_acl.py` | grant_case_access / revoke_case_access | POST/DELETE |
| `src/backend/api/v1/analyses.py` | create_analysis | POST |
| `src/backend/api/v1/uploads.py` | create_upload | POST |
| `src/backend/api/v1/upload_vcf.py` | upload_vcf | POST |
| `src/backend/api/research.py` | submit_paper | POST |
| `src/backend/api/v1/clinical.py` | run_agents / run_consensus / recommend_treatment / analyze_case | POST |
| `src/backend/api/v1/reports.py` | create_case_report | POST |
| `src/backend/api/v1/ranking.py` | rank_variant / rank_case | POST |

### 已盤點的 Service+get_db 雙 owner endpoint（B 類：Service 自行 commit，與 get_db 衝突）
| 檔案 | endpoint | Service |
|------|----------|---------|
| `src/backend/api/v1/variants.py` | import_variants | VariantIngestionService |
| `src/backend/api/v1/evidence.py` | refresh_evidence | EvidenceIngestionService |
| `src/backend/api/v1/clinical_graph.py` | retry_event | ClinicalGraphEventService |
| `src/backend/api/v1/treatment_plans.py` | 10 個 POST | TreatmentPlanService |
| `src/backend/api/v1/recommendation.py` | create_recommendation | RecommendationService |
| `src/backend/api/v1/clinical_decision.py` | create_clinical_decision | ClinicalDecisionService |
| `src/backend/api/v1/tumor_board_consensus.py` | create_tumor_board_consensus | TumorBoardConsensusService |

> B 類在移除 get_db auto-commit 後即自然解決（Service 成為唯一 owner），僅需確認其 Service 已正確管理 commit/rollback。

---

## B.2 REVIEW-PHASE3F0-R3-P1-02 / OPEN（重要）

**位置**：`src/backend/api/v1/variants.py`（import_variants 的 except 區塊，L69-75）

### 問題
- 直接把 `str(e)` 回傳給 API 用戶（`raise HTTPException(status_code=500, detail=str(e))`）
- 可能洩漏 SQL、資料表、constraint、驅動或內部路徑資訊
- 所有業務錯誤均被壓成無差別 500

### 修改要求
1. 保留並重新拋出既有 `HTTPException`（合法 4xx 業務錯誤不得被轉換為 500）
2. 其餘例外只記錄完整 server log
3. 對外回傳**固定、安全的錯誤訊息**與**可追蹤 request/error id**，不得暴露原始例外

### 驗證要求（新增測試）
1. 內部 DB 例外文字不會出現在 response body
2. 合法的 4xx 業務錯誤不會被轉換為 500

---

## B.3 完成條件

- [ ] P0-01 代碼修正完成（get_db 移除 auto commit + A 類 endpoint 改由 Service 管理）
- [ ] P1-02 代碼修正完成（錯誤處理改造）
- [ ] 兩項驗證測試全部新增並通過
- [ ] REVIEW 註解改為 REVIEW-RESOLVED（保留原註解，附 RESOLUTION）
- [ ] 完整返工循環（Step 6 需求回歸 + Step 7 REVIEWER 評分）通過
- [ ] 全部測試通過後 Commit / Push
