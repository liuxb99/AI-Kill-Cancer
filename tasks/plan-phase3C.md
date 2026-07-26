# Phase 3C 執行計劃 — Tumor Board Consensus Engine

---

## 1. 任務摘要

### 1.1 Phase 3C 目標

建立 **Tumor Board Consensus Engine** 模組，實現：
```
Clinical Decision
↓
Multi-specialty Opinions
↓
Consensus Calculation
↓
Tumor Board Consensus
```

這是一個完整、可獨立驗收的模組，涵蓋 Domain Models / Enums / Rules → Database Models + Migration → Engine → Repositories → Service → API → Frontend → Report Section → Tests（Engine / Model / Repo / Service / API / Integration / Frontend / Migration / CI）。

### 1.2 範圍邊界

| 範圍 | 狀態 |
|------|------|
| Tumor Board Consensus Engine | ✅ 做 |
| SpecialtyType Enum（9+ 專科） | ✅ 做 |
| ConsensusStatus Enum（6 種狀態） | ✅ 做 |
| Position Enum（support/oppose/abstain） | ✅ 做 |
| ConsensusRuleSet（Threshold 集中管理） | ✅ 做 |
| Consensus Trace（8 steps） | ✅ 做 |
| P0 Patient/Recommendation/ClinicalDecision 關聯驗證 | ✅ 做 |
| Audit Trail（created_by） | ✅ 做 |
| API POST/GET/List/Opinions/Trace | ✅ 做 |
| Frontend List/Detail/Create | ✅ 做 |
| HTML Report Section | ✅ 做 |
| Backend Tests（Engine/Model/Repo/Service/API/Integration） | ✅ 做 |
| Migration 019→020 upgrade/downgrade/re-upgrade | ✅ 做 |
| Postgres CI Gate | ✅ 做 |
| Frontend Tests | ✅ 做 |
| Treatment Plan / Medication Order / Guideline Execution | ❌ 不做 |
| Phase 3D / Phase 4 | ❌ 不做 |
| 修改已驗收 Migration 017/018/019 | ❌ 不做 |
| 修改 Phase 3A / Phase 3B 核心功能 | ❌ 不做 |
| Sample/fake/hardcoded 前端資料 | ❌ 不做 |

### 1.3 依循的模式約定

- **Domain Model**: `CompatUUID` PK, `String(64)` business ID, `JSON` for complex data, `DateTime` timestamps, `relationship` with cascade
- **Repository**: 繼承 `BaseRepository[ModelT]`，inject `AsyncSession`，**不 commit/rollback**，不吞 Exception
- **Service**: inject `db`, repos, engine；管理 transaction boundary（commit/rollback）；回傳 Pydantic DTO
- **Engine**: 純業務邏輯，無 DB 依賴；規則來自 `ConsensusRuleSet`（集中配置）
- **API**: `APIRouter` + `Depends(require_auth)` + `Depends(get_db)`；404/422/500 錯誤處理
- **Frontend**: React + fetch API client；loading/error/empty/detail 四種狀態
- **Migration**: Alembic revision 020；`create_table`/`drop_table`；FK/Index/Unique 正確
- **Report**: `ReportGenerator` 新增 `_render_tumor_board_consensus()` section

---

## 2. 任務清單（依批次分組）

### Batch A — Domain Models + Enums + Rules

| 子任務 | 說明 | 負責角色 |
|--------|------|----------|
| A1 | 新增 `SpecialtyType` Enum（9+ 專科：medical_oncology, surgical_oncology, radiation_oncology, pathology, radiology, genomics, pharmacy, nursing, palliative_care） | db-modeler |
| A2 | 新增 `ConsensusStatus` Enum（unanimous, strong_consensus, majority_consensus, split_decision, insufficient_information, deferred） | db-modeler |
| A3 | 新增 `Position` Enum（support, oppose, abstain） | db-modeler |
| A4 | 新增 `ConsensusRuleSet` 類別（集中存放 Threshold：UNANIMOUS=1.0, STRONG=0.8, MAJORITY=0.6, SPLIT_THRESHOLD=0.4；含 Weight 常數） | backend-logic |
| A5 | 新增 `TumorBoardConsensusRequest` / `TumorBoardConsensusResponse` / `SpecialistOpinionDTO` / `ConsensusSummaryDTO` Pydantic DTOs | api-designer |
| A6 | 新增 `SpecialistOpinion` Domain Input Model（specialty, participant_id, position, confidence, rationale, supporting_evidence, contraindications, preferred_option, alternative_option, requires_more_information） | backend-logic |

**預計規模**: ~200 行（Enums ~60, RuleSet ~80, DTOs ~60）

---

### Batch B — Database Models + Migration 020

| 子任務 | 說明 | 負責角色 |
|--------|------|----------|
| B1 | 新增 `TumorBoardConsensusModel`（table: `domain_tumor_board_consensus`）— id, consensus_id, patient_id, recommendation_id, clinical_decision_id, consensus_status, consensus_score, final_recommendation, supporting_rationale, dissenting_opinions, unresolved_questions, required_follow_up, participating_specialties, created_by, created_at, updated_at | db-modeler |
| B2 | 新增 `TumorBoardOpinionModel`（table: `domain_tumor_board_opinions`）— id, consensus_id (FK), specialty, participant_id, position, confidence, rationale, supporting_evidence, contraindications, preferred_option, alternative_option, requires_more_information, created_at | db-modeler |
| B3 | 新增 `TumorBoardConsensusTraceModel`（table: `domain_tumor_board_consensus_traces`）— id, trace_id, consensus_id (FK), step_order, step_type, input_summary, output_summary, created_at；`UniqueConstraint("trace_id", "step_order")` | db-modeler |
| B4 | 新增 Migration 020（`020_phase3c_tumor_board_consensus_tables.py`），revises=019 | db-modeler |
| B5 | Migration 020 建立 FK: consensus→patient/recommendation/clinical_decision（CASCADE/SET NULL），opinions→consensus（CASCADE），traces→consensus（CASCADE） | db-modeler |
| B6 | Migration 020 建立 Index: consensus on patient_id, clinical_decision_id；opinions on consensus_id；traces on trace_id, consensus_id | db-modeler |
| B7 | Migration 020 建立 Unique: `UNIQUE(trace_id, step_order)` on traces | db-modeler |
| B8 | Migration 020 upgrade/downgrade/re-upgrade 正確 | db-modeler |

**預計規模**: ~350 行（Models ~180, Migration ~170）

---

### Batch C — Consensus Engine

| 子任務 | 說明 | 負責角色 |
|--------|------|----------|
| C1 | 建立 `TumorBoardConsensusEngine` 類別 | backend-logic |
| C2 | 實作 Weight Calculation：`Opinion Weight = Specialty Weight × Confidence Weight × Evidence Weight` | backend-logic |
| C3 | 實作 Consensus Scoring：support_score / oppose_score / abstain_score / consensus_ratio / confidence_score | backend-logic |
| C4 | 實作 Status Classification：根據 ConsensusRuleSet Threshold 判定 unanimous → deferred | backend-logic |
| C5 | 實作 Dissent Extraction：找出反對/保留意見 | backend-logic |
| C6 | 實作 Final Recommendation / Supporting Rationale 組裝 | backend-logic |
| C7 | Engine 使用 ConsensusRuleSet 配置，不得硬編碼 Threshold | backend-logic |

**預計規模**: ~300 行

---

### Batch D — Repositories

| 子任務 | 說明 | 負責角色 |
|--------|------|----------|
| D1 | 新增 `TumorBoardConsensusRepository`（create, get_by_id, get_by_uuid, list_by_patient_id, list_by_clinical_decision_id, count_by_patient_id） | backend-logic |
| D2 | 新增 `TumorBoardOpinionRepository`（create, create_many, list_by_consensus_id） | backend-logic |
| D3 | 新增 `TumorBoardConsensusTraceRepository`（create, create_many, get_by_consensus_id, get_by_trace_id） | backend-logic |
| D4 | 遵守 Repository 規則：不 commit、不 rollback、不吞 Exception | backend-logic |

**預計規模**: ~250 行

---

### Batch E — Service

| 子任務 | 說明 | 負責角色 |
|--------|------|----------|
| E1 | 建立 `TumorBoardConsensusService` 類別 | backend-logic |
| E2 | P0 關聯驗證：`Recommendation.patient_id == ClinicalDecision.patient_id == Request.patient_id` | backend-logic |
| E3 | P0 關聯驗證：`ClinicalDecision.recommendation_id == Request.recommendation_id` | backend-logic |
| E4 | 任一不一致 → raise ValueError → API 422，不執行 Engine，不留殘餘資料 | backend-logic |
| E5 | Transaction boundary：Engine → 建立 Consensus Model → 建立 Opinion Models → 建立 Trace Models → commit；失敗 rollback + raise RuntimeError | backend-logic |
| E6 | Audit Trail：`created_by` 從 API user 傳入，一路寫入 Model | backend-logic |
| E7 | Consensus Trace 8 steps（load_context, validate_links, normalize_opinions, calculate_weights, calculate_consensus, resolve_dissent, finalize_consensus, prepare_persistence） | backend-logic |

**預計規模**: ~350 行

---

### Batch F — API

| 子任務 | 說明 | 負責角色 |
|--------|------|----------|
| F1 | `POST /api/v1/tumor-board-consensus` — 建立 Consensus（status 201） | api-designer |
| F2 | `GET /api/v1/tumor-board-consensus/{consensus_id}` — 查詢單筆 | api-designer |
| F3 | `GET /api/v1/tumor-board-consensus?patient_id=&skip=&limit=` — 列表（分頁） | api-designer |
| F4 | `GET /api/v1/tumor-board-consensus/{consensus_id}/opinions` — 查詢意見 | api-designer |
| F5 | `GET /api/v1/tumor-board-consensus/{consensus_id}/trace` — 查詢 Trace | api-designer |
| F6 | Router 註冊：在 `api/v1/router.py` 加入 `include_router` | api-designer |
| F7 | 錯誤處理：404（not found）、422（validation/link error）、500（generic） | api-designer |

**預計規模**: ~300 行

---

### Batch G — Frontend

| 子任務 | 說明 | 負責角色 |
|--------|------|----------|
| G1 | 新增 API Client `src/frontend/src/api/tumor_board_consensus.ts`（createConsensus, fetchConsensusById, fetchConsensusList, fetchOpinions, fetchTrace） | frontend-logic |
| G2 | 新增 `TumorBoardConsensusListPage`（/tumor-board）：輸入 patient_id 查詢、顯示 status/score/specialties/created_at、進入 Detail | frontend-logic |
| G3 | 新增 `TumorBoardConsensusPage`（/tumor-board/:id）：顯示 Consensus Status, Score, Final Recommendation, Supporting Rationale, Dissenting Opinions, Unresolved Questions, Required Follow-up, Specialist Opinions, Trace Summary | frontend-logic |
| G4 | `ClinicalDecisionPage` 新增「建立 Tumor Board Consensus」入口，填寫 Specialist Opinions → POST → navigate(`/tumor-board/{id}`) | frontend-logic |
| G5 | `App.tsx` 註冊 Router：`/tumor-board`, `/tumor-board/:id`；Navbar 加「腫瘤 board」連結 | frontend-logic |
| G6 | 禁止 sample/fake/hardcoded data | frontend-logic |

**預計規模**: ~500 行

---

### Batch H — Report Section

| 子任務 | 說明 | 負責角色 |
|--------|------|----------|
| H1 | 在 `ReportGenerator` 新增 `_render_tumor_board_consensus()` 方法 | doc-writer |
| H2 | 顯示：Consensus Status, Consensus Score, Participating Specialties, Final Recommendation, Supporting Rationale, Dissenting Opinions, Unresolved Questions, Required Follow-up | doc-writer |
| H3 | 在 `generate()` 中組裝 Section（若資料存在） | doc-writer |
| H4 | 不重寫整個 Report Generator | doc-writer |

**預計規模**: ~100 行

---

### Batch I — Tests（Engine + Model + Repository）

| 子任務 | 說明 | 負責角色 |
|--------|------|----------|
| I1 | Engine Tests（10+ cases）：unanimous, strong_consensus, majority_consensus, split_decision, insufficient_information, deferred, specialty weighting, confidence weighting, contraindication impact, dissent extraction | unit-tester |
| I2 | Model Tests：Model creation, Relations, Cascade, JSON round-trip, Unique constraints | unit-tester |
| I3 | Repository Tests：create, get, list, count, create_many, pagination, not found | unit-tester |

**預計規模**: ~800 行

---

### Batch J — Tests（Service + API + Integration）

| 子任務 | 說明 | 負責角色 |
|--------|------|----------|
| J1 | Service Tests（9+ cases）：successful consensus, patient mismatch (422), recommendation mismatch (422), clinical decision mismatch (422), created_by persistence, transaction rollback, opinion persistence failure, trace persistence failure, commit failure | integration-tester |
| J2 | API Tests：POST success, GET success, List empty, List one, Pagination, 401 (unauth), 404 (not found), 422 (validation), 500 generic | integration-tester |
| J3 | Digital Thread Test：Patient→Recommendation→ClinicalDecision→TumorBoardConsensus→Opinions→Trace 全部可從 Database 還原 | integration-tester |
| J4 | Restart Recovery Test：App1 POST Consensus → GET → Shutdown → App2 GET Consensus + Opinions + Trace | integration-tester |

**預計規模**: ~1200 行

---

### Batch K — Frontend Tests

| 子任務 | 說明 | 負責角色 |
|--------|------|----------|
| K1 | List route test | frontend-logic |
| K2 | Detail route test | frontend-logic |
| K3 | Navigation test | frontend-logic |
| K4 | Create form test | frontend-logic |
| K5 | POST API test | frontend-logic |
| K6 | Redirect test | frontend-logic |
| K7 | Empty state test | frontend-logic |
| K8 | Error state test | frontend-logic |

**預計規模**: ~400 行

---

### Batch L — Migration Tests + CI

| 子任務 | 說明 | 負責角色 |
|--------|------|----------|
| L1 | Migration 019→020 upgrade 測試 | integration-tester |
| L2 | Migration 020→019 downgrade 測試 | integration-tester |
| L3 | Migration 019→020 re-upgrade 測試 | integration-tester |
| L4 | FK / Index / Unique / Multiple Trace Steps 驗證 | integration-tester |
| L5 | Postgres CI Gate 設定（GitHub Actions PostgreSQL service） | integration-tester |
| L6 | Full regression 確認（所有既有測試仍 PASS） | integration-tester |

**預計規模**: ~300 行

---

## 3. 依賴關係

```
Batch A (Enums + Rules)
  ↓
Batch B (DB Models + Migration 020)
  ↓
Batch C (Consensus Engine)
  ↓
Batch D (Repositories) ──────── 依賴 B（Models）
  ↓
Batch E (Service) ───────────── 依賴 C（Engine）+ D（Repositories）
  ↓
Batch F (API) ───────────────── 依賴 E（Service）
  ↓
Batch G (Frontend) ──────────── 依賴 F（API）
  ↓
Batch H (Report Section) ────── 依賴 B（Models）
  ↓
Batch I (Engine/Model/Repo Tests) ── 依賴 A/B/C/D
  ↓
Batch J (Service/API/Integration Tests) ── 依賴 E/F
  ↓
Batch K (Frontend Tests) ────── 依賴 G
  ↓
Batch L (Migration Tests + CI) ── 依賴 B（Migration）
```

**實際執行推薦順序（平行化）**:

```
第一波: A + B（可並行，A 先完成供 B 參考）
第二波: C + D（可並行）
第三波: E（依賴 C+D）
第四波: F + H（可並行，F 依賴 E）
第五波: G（依賴 F）
第六波: I + L（可並行）
第七波: J（依賴 E+F+I）
第八波: K（依賴 G）
```

---

## 4. 負責角色

| 角色 | 批次 | 核心職責 |
|------|------|----------|
| **db-modeler** | A, B | Enums, Models, Migration |
| **backend-logic** | C, D, E | Engine, Repositories, Service |
| **api-designer** | F | API Router + Handlers + Error Mapping |
| **frontend-logic** | G, K | Frontend Pages + API Client + Tests |
| **doc-writer** | H | Report Section |
| **unit-tester** | I | Engine + Model + Repository Tests |
| **integration-tester** | J, L | Service + API + Digital Thread + Restart Recovery + Migration Tests + CI |
| **reviewer** | 最終驗證 | Reviewer Gate（≥95） |

---

## 5. 返工預案

| 常見失敗模式 | 修復策略 | 偵測方式 |
|-------------|----------|----------|
| Migration 020 FK 指向錯誤欄位 | 檢查 FK 的 `ref_column` 是否正確指向 PK | Migration Test（L1-L4） |
| `UNIQUE(trace_id, step_order)` 遺漏 | 確認 `__table_args__` 中有 `UniqueConstraint` | Model Test（I2）+ Migration Test |
| Repository 內含 commit/rollback | Code Review + 測試檢查 | Reviewer Gate |
| Service 未正確 rollback | 模擬 persistence failure 驗證 DB 無殘留 | Service Test（J1） |
| P0 關聯驗證遺漏 | 確認 Service 在 Engine 執行前驗證 patient/recommendation/clinicalDecision 一致性 | Service Test（J1） |
| created_by 為 NULL | 確認 API → Service → Model 傳遞鏈 | Service Test（J1）+ API Test |
| Frontend 使用 hardcoded data | Code Review | Reviewer Gate |
| Engine Threshold 散落 | 確認所有 Threshold 來自 ConsensusRuleSet | Engine Test（I1） |
| 前端 Create 流程未串接 | 確認 ClinicalDecisionPage 有「建立 Tumor Board Consensus」入口 | Frontend Test（K4-K6） |
| Postgres CI 未通過 | 修復 Migration 或 Transaction 邏輯 | CI Run |
| API 洩漏 Exception/SQL/Stack Trace | 確認 500 handler 只回傳 generic message | API Test（J2） |

---

## 6. 預計工作量（估算行數）

| Batch | 說明 | 預估行數 | 工時比例 |
|-------|------|----------|----------|
| A | Enums + Rules + DTOs | ~200 | 5% |
| B | Models + Migration | ~350 | 8% |
| C | Engine | ~300 | 7% |
| D | Repositories | ~250 | 6% |
| E | Service | ~350 | 8% |
| F | API | ~300 | 7% |
| G | Frontend | ~500 | 12% |
| H | Report Section | ~100 | 2% |
| I | Engine/Model/Repo Tests | ~800 | 19% |
| J | Service/API/Integration Tests | ~1200 | 28% |
| K | Frontend Tests | ~400 | 10% |
| L | Migration Tests + CI | ~300 | 7% |
| **總計** | | **~4,650** | **100%** |

> 註：測試（I + J + K + L）約佔總量的 ~64%，符合專案對測試覆蓋率的重視。

---

## 7. Reviewer Gate 條件

### 7.1 評分閾值
- **必須 ≥ 95 分** 才可標記 Phase 3C 完成
- < 95 分 → 標記 `PARTIAL`，`Ready for Next Phase = NO`

### 7.2 11 項必檢查清單（逐條確認）

```
[ ] 1. Recommendation、Clinical Decision、Patient 關聯一致（P0 驗證）
[ ] 2. created_by 寫入所有記錄（Audit Trail）
[ ] 3. Opinions 全部持久化（create_many）
[ ] 4. Consensus Trace 多 Step 持久化（8 steps）
[ ] 5. Transaction All-or-Nothing（失敗 rollback，無殘留）
[ ] 6. API POST/GET/List 可用（含 opinions/trace endpoints）
[ ] 7. Frontend List/Detail/Create 可用（無 hardcoded data）
[ ] 8. Digital Thread 可還原（Patient → Recommendation → ClinicalDecision → Consensus → Opinions → Trace）
[ ] 9. Restart 後可讀（跨 App 生命週期）
[ ] 10. Migration 020 upgrade/downgrade/re-upgrade 正確
[ ] 11. Postgres CI 全綠（GitHub Actions 通過）
```

任一項為 `FAIL` / `PARTIAL` / `未驗證`：
- 滿足需求 = `NO`
- Reviewer 最高 = `89`
- Ready for Next Phase = `NO`

### 7.3 Phase 3C 完成條件

```
- 所有 Batch A~L 完成
- 所有測試 PASS（Unit + Integration + Frontend + Migration）
- Postgres CI 全綠
- Reviewer ≥ 95
- Git Commit & Push 成功
```

---

## 附錄：Phase 3C 需求需求覆蓋矩陣

| 需求章節 | 涵蓋 Batch | 說明 |
|----------|-----------|------|
| 一、任務定位 | 全體 | 完整模組定位 |
| 二、執行流程 | 全體 | 依循 AGENTS.md |
| 三、開始前必讀 | 全體 | 已參考所有模式 |
| 四、核心目標 | C, E, F | 輸入/輸出規格 |
| 五、專科意見模型 | A, C | SpecialtyType + SpecialistOpinion |
| 六、Consensus 狀態 | A, C | ConsensusStatus + 計算邏輯 |
| 七、Consensus 計算規則 | C, A | Weight + Scoring + ConsensusRuleSet |
| 八、P0 資料一致性 | E, J | 關聯驗證 + Service Test |
| 九、Audit Trail | E, F, J | created_by 鏈 |
| 十、Database Models | B | 3 個 Model |
| 十一、Migration 020 | B, L | upgrade/downgrade/re-upgrade |
| 十二、Repository | D, I | 3 個 Repository |
| 十三、Service | E, J | Transaction Boundary |
| 十四、Consensus Trace | E, C | 8 steps |
| 十五、API | F, J | 5 endpoints |
| 十六、Frontend | G, K | 2 pages + 入口 |
| 十七、建立入口 | G | ClinicalDecisionPage 新增 |
| 十八、HTML Report | H | Report Section |
| 十九、測試要求 | I, J, K, L | 全部測試類型 |
| 二十、真實 Postgres Gate | L | CI 設定 |
| 二十一、禁止事項 | 全體 | Code Review 檢查 |
| 二十二、Commit Scope | 全體 | 僅 Tumor Board 範圍 |
| 二十三、Reviewer Gate | Reviewer | 11 項檢查清單 |
| 二十四、Git 要求 | 全體 | feat(phase3c): 單一 Commit |
| 二十五、完成後只回報 | 全體 | 最終回報格式 |

---

*計劃版本: 1.0*
*建立日期: 2026-07-26*
