# Phase 3B — Clinical Decision Layer 執行計劃

## 概述

在 Phase 3A Recommendation Engine 之上建立 Clinical Decision Layer，形成完整鏈路：

**Patient → Variant → Evidence → Recommendation → Clinical Decision**

---

## 批次劃分（依賴關係）

### Batch A — Foundation（Domain Models + Enum + Migration）
| # | 任務 | 負責角色 | 產出檔案 | 依賴 |
|---|------|---------|---------|------|
| A1 | 新增 Clinical Decision 相關 Enum（DecisionTypeEnum、DecisionStatusEnum、ConfidenceLevelEnum） | PLANNER→CODER | `src/backend/domain/enums.py`（追加） | 無 |
| A2 | 建立 ClinicalDecisionModel（含決策類型、理由、證據、信心、替代方案、禁忌症等欄位） | CODER | `src/backend/domain/clinical_decision.py` | A1 |
| A3 | 建立 ClinicalDecisionTraceModel（含追溯鏈：recommendation_id → clinical_decision_id） | CODER | `src/backend/domain/clinical_decision.py` | A2 |
| A4 | 建立新 Migration 018（clinical_decisions + clinical_decision_traces 兩張表） | CODER | `migrations/versions/018_phase3b_clinical_decision_tables.py` | A2, A3 |

### Batch B — Repository Layer
| # | 任務 | 負責角色 | 產出檔案 | 依賴 |
|---|------|---------|---------|------|
| B1 | 建立 ClinicalDecisionRepository（create/get_by_id/list_by_patient_id/list_by_recommendation_id） | CODER | `src/backend/repositories/clinical_decision_repo.py` | A4 |
| B2 | 建立 ClinicalDecisionTraceRepository（create/get_by_decision_id/get_by_recommendation_id） | CODER | `src/backend/repositories/clinical_decision_repo.py`（同檔案） | A4 |

### Batch C — Clinical Decision Engine（核心邏輯）
| # | 任務 | 負責角色 | 產出檔案 | 依賴 |
|---|------|---------|---------|------|
| C1 | 建立 ClinicalDecisionEngine（輸入 Patient/Variant/Evidence/Recommendation → 輸出 ClinicalDecision） | CODER | `src/backend/clinical/clinical_decision_engine.py` | A2 |
| C2 | 建立 JSON Schema（ClinicalDecisionResult、DecisionOption、AlternativeOption 等） | CODER | `src/backend/clinical/schemas/clinical_decision.json` | A2 |
| C3 | 建立 DecisionRule 規則集（DecisionType 判定、Confidence 計算、Contraindication 檢測） | CODER | `src/backend/clinical/decision_rules.py` | C1 |

### Batch D — Clinical Decision Service
| # | 任務 | 負責角色 | 產出檔案 | 依賴 |
|---|------|---------|---------|------|
| D1 | 建立 ClinicalDecisionService（整合 Engine + Repository + Trace，管理 Transaction Boundary） | CODER | `src/backend/services/clinical_decision_service.py` | B1, B2, C1 |
| D2 | 建立 DecisionResponse/DecisionRequest Pydantic DTOs | CODER | `src/backend/services/clinical_decision_service.py`（同檔案） | A2 |

### Batch E — API Layer
| # | 任務 | 負責角色 | 產出檔案 | 依賴 |
|---|------|---------|---------|------|
| E1 | 建立 POST /api/v1/clinical-decision endpoint | CODER | `src/backend/api/v1/clinical_decision.py` | D1 |
| E2 | 建立 GET /api/v1/clinical-decision/{id} endpoint | CODER | `src/backend/api/v1/clinical_decision.py`（同檔案） | D1 |
| E3 | 註冊 router 到 v1 router | CODER | `src/backend/api/v1/router.py`（追加 import + include_router） | E1 |
| E4 | HTTP Error Security（固定 error code + generic message，不得洩漏 Exception） | CODER | `src/backend/api/v1/clinical_decision.py` | E1 |

### Batch F — Frontend
| # | 任務 | 負責角色 | 產出檔案 | 依賴 |
|---|------|---------|---------|------|
| F1 | 建立 ClinicalDecisionPage（顯示決策類型、理由、信心、替代方案、禁忌症、證據摘要） | CODER | `src/frontend/src/pages/ClinicalDecisionPage.tsx` | E1 |
| F2 | 建立 API 呼叫層（fetchClinicalDecisionById, fetchClinicalDecisionTree） | CODER | `src/frontend/src/api/clinical_decision.ts` | E1 |
| F3 | 註冊 Route `/clinical-decision/:id` 及 `/clinical-decision` 到 App.tsx | CODER | `src/frontend/src/App.tsx`（追加 Route） | F1 |
| F4 | 加入 Navigation Menu（主選單加入 Clinical Decision 項目） | CODER | `src/frontend/src/App.tsx` + Navigation Component | F1 |
| F5 | 從 RecommendationPage 可導航至 ClinicalDecisionPage（查看關聯決策） | CODER | `src/frontend/src/pages/RecommendationPage.tsx`（追加 Link） | F1 |

### Batch G — HTML Report Enhancement
| # | 任務 | 負責角色 | 產出檔案 | 依賴 |
|---|------|---------|---------|------|
| G1 | Report Generator 加入 Clinical Decision Section（Decision Type / Reason / Alternatives / Evidence Summary） | CODER | `src/backend/clinical/report_generator.py`（追加 method） | D1 |
| G2 | Report Generator 的 generate() 接受 Clinical Decision 參數並渲染 | CODER | `src/backend/clinical/report_generator.py`（修改） | G1 |

### Batch H — 測試
| # | 任務 | 負責角色 | 產出檔案 | 依賴 |
|---|------|---------|---------|------|
| H1 | Domain Model Tests（ClinicalDecisionModel JSON round-trip, Index, Trace relation） | CODER | `tests/test_clinical_decision_models.py` | A4 |
| H2 | Repository Tests（CRUD, Rollback, Not Found, list_by_patient_id, list_by_recommendation_id） | CODER | `tests/test_clinical_decision_repo.py` | B2 |
| H3 | Service Tests（Decision Creation/Update, Transaction, Failure Rollback） | CODER | `tests/test_clinical_decision_service.py` | D1 |
| H4 | API Integration Tests（POST→DB, GET→DB, 404, 422, 500） | CODER | `tests/test_api_clinical_decision.py` | E4 |
| H5 | Digital Thread Tests（Evidence → Recommendation → Clinical Decision 完整可還原） | CODER | `tests/test_clinical_decision_thread.py` | D1, A4 |
| H6 | Integration Test（Patient → Recommendation → Clinical Decision → Restart → GET） | CODER | `tests/test_clinical_decision_integration.py` | D1 |
| H7 | Migration Tests（upgrade→downgrade→upgrade again） | CODER | `tests/test_migration.py`（追加 test class） | A4 |
| H8 | Frontend Route Test（Route registered, Navigation clickable, Page renders, API path correct） | CODER | `tests/test_frontend_route.py`（或更新現有） | F4 |

---

## 執行順序（合併批次）

實際執行時建議以 Phase 為單位合併以減少返工：

```
Phase 1: Batch A → Migration (Foundation)
Phase 2: Batch B → Repository
Phase 3: Batch C → Engine (Core Logic)
Phase 4: Batch D → Service
Phase 5: Batch E → API
Phase 6: Batch F → Frontend
Phase 7: Batch G → Report Enhancement
Phase 8: Batch H → All Tests
Phase 9: Final Verification (go test ./..., Frontend build, API smoke test, coverage, git diff)
```

---

## 返工預案

| 情境 | 觸發條件 | 處理方式 |
|------|---------|---------|
| **Migration 衝突** | 018 與未來 migration 衝突 | 確認 017 是 latest，018 的 down_revision="017"。若已存在 018，改用 019 |
| **Enum 衝突** | 已有同名 Enum | 使用 Enum 命名規範：DecisionTypeEnum, DecisionStatusEnum。若已有相似 Enum 則擴展現有 |
| **Repository 模式不一致** | BaseRepository 的 create() 自行 commit（與 Phase 3A 要求矛盾） | 遵循 recommendation_repo.py 模式：僅 self.db.add()，不 commit，由 service 管理 transaction |
| **Frontend Route 衝突** | /clinical-decision 被佔用 | 使用 /clinical-decision 路徑（需求明確指定） |
| **測試 DB 連線失敗** | SQLite in-memory 無法完全模擬 Postgres JSONB | 使用現有 conftest.py 的 MockAsyncSession + 真實 SQLite in-memory 雙層測試 |
| **Phase 3A 功能被修改** | 不小心改到已驗收功能 | 嚴格遵守需求：不得修改 Phase 3A / 已驗收功能。Git diff 確認 scope |
| **API 命名衝突** | /api/v1/clinical-decision 與現有 /api/v1/clinical/ 衝突 | 確定命名：/api/v1/clinical-decision（獨立 prefix）與 /api/v1/clinical/ 不同 namespace |
| **Report Generator 修改破裂** | 加入 Clinical Decision 資訊破壞既有 Report | 使用 optional parameter，不改變既有 generate() signature 的強制參數 |
| **reviewer 評分 < 90** | AGENTS.md Step 5b 規則 | 自動啟動返工循環：PLANNER(resume) → CODER(resume) → REVIEWER 重新評分 |

---

## 關鍵設計決策

### 1. ClinicalDecisionModel 欄位設計
```python
class ClinicalDecisionModel(DBBase):
    __tablename__ = "domain_clinical_decisions"
    
    id = Column(CompatUUID, primary_key=True, default=_uuid)
    decision_id = Column(String(64), unique=True, nullable=False, index=True)
    patient_id = Column(CompatUUID, ForeignKey("domain_patients.id", ondelete="CASCADE"), nullable=False, index=True)
    recommendation_id = Column(CompatUUID, ForeignKey("domain_recommendations.id", ondelete="SET NULL"), nullable=True, index=True)
    decision_type = Column(String(64), nullable=False)  # e.g. "approved", "off_label", "clinical_trial", "contraindicated"
    reason = Column(Text, nullable=False)
    evidence_summary = Column(JSON, nullable=True)
    confidence = Column(String(32), nullable=False)  # e.g. "high", "medium", "low"
    alternatives = Column(JSON, nullable=True)  # List of alternative decisions
    contraindications = Column(JSON, nullable=True)  # List of contraindications
    status = Column(String(32), nullable=False, default="active")
    created_by = Column(CompatUUID, ForeignKey("domain_users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationship to trace
    traces = relationship("ClinicalDecisionTraceModel", back_populates="clinical_decision", cascade="all, delete-orphan", lazy="selectin")
```

### 2. ClinicalDecisionTraceModel 欄位設計
```python
class ClinicalDecisionTraceModel(DBBase):
    __tablename__ = "domain_clinical_decision_traces"
    
    id = Column(CompatUUID, primary_key=True, default=_uuid)
    trace_id = Column(String(64), unique=True, nullable=False, index=True)
    clinical_decision_id = Column(CompatUUID, ForeignKey("domain_clinical_decisions.id", ondelete="CASCADE"), nullable=True, index=True)
    recommendation_id = Column(CompatUUID, ForeignKey("domain_recommendations.id", ondelete="SET NULL"), nullable=True, index=True)
    step_order = Column(Integer, nullable=False)
    step_type = Column(String(64), nullable=False)
    input_summary = Column(JSON, nullable=True)
    output_summary = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    clinical_decision = relationship("ClinicalDecisionModel", back_populates="traces")
```

### 3. 數位線程（Digital Thread）設計
```
Patient ──→ Recommendation ──→ Clinical Decision
   │                              │
   │                              ├── Decision Type
   │                              ├── Reason
   │                              ├── Evidence Summary
   │                              ├── Confidence
   │                              ├── Alternatives
   │                              └── Contraindications
   │
   └── recommendation_id (FK: domain_recommendations.id)
   
ClinicalDecisionTrace:
  - trace_id (unique)
  - clinical_decision_id (FK)
  - recommendation_id (FK)
  - step_order
  - step_type
  - input_summary (JSON)
  - output_summary (JSON)
```

### 4. API 設計
```python
# POST /api/v1/clinical-decision
# Request:
{
    "patient_id": "uuid",
    "recommendation_id": "uuid",
    "variants": ["EGFR L858R", "KRAS G12C"],
    "context": { ... }  # optional
}
# Response:
{
    "decision_id": "uuid-string",
    "patient_id": "uuid",
    "recommendation_id": "uuid",
    "decision_type": "approved",
    "reason": "Based on NCCN Level 1 evidence...",
    "evidence_summary": { ... },
    "confidence": "high",
    "alternatives": [ ... ],
    "contraindications": [ ... ],
    "trace_id": "uuid-string",
    "created_at": "ISO-8601"
}

# GET /api/v1/clinical-decision/{decision_id}
# Response: same as POST response
```

### 5. 檔案路徑總表

| 層級 | 路徑 | 新增/修改 |
|------|------|----------|
| Enum | `src/backend/domain/enums.py` | 修改（追加） |
| Domain | `src/backend/domain/clinical_decision.py` | 新增 |
| Migration | `migrations/versions/018_phase3b_clinical_decision_tables.py` | 新增 |
| Repository | `src/backend/repositories/clinical_decision_repo.py` | 新增 |
| Engine | `src/backend/clinical/clinical_decision_engine.py` | 新增 |
| Rules | `src/backend/clinical/decision_rules.py` | 新增 |
| Schema | `src/backend/clinical/schemas/clinical_decision.json` | 新增 |
| Service | `src/backend/services/clinical_decision_service.py` | 新增 |
| API | `src/backend/api/v1/clinical_decision.py` | 新增 |
| Router | `src/backend/api/v1/router.py` | 修改（追加） |
| Frontend Page | `src/frontend/src/pages/ClinicalDecisionPage.tsx` | 新增 |
| Frontend API | `src/frontend/src/api/clinical_decision.ts` | 新增 |
| Frontend Route | `src/frontend/src/App.tsx` | 修改（追加） |
| Report | `src/backend/clinical/report_generator.py` | 修改（追加 method） |
| Tests (Models) | `tests/test_clinical_decision_models.py` | 新增 |
| Tests (Repo) | `tests/test_clinical_decision_repo.py` | 新增 |
| Tests (Service) | `tests/test_clinical_decision_service.py` | 新增 |
| Tests (API) | `tests/test_api_clinical_decision.py` | 新增 |
| Tests (Thread) | `tests/test_clinical_decision_thread.py` | 新增 |
| Tests (Integration) | `tests/test_clinical_decision_integration.py` | 新增 |
| Tests (Migration) | `tests/test_migration.py` | 修改（追加 class） |
| Tests (Frontend Route) | `tests/test_frontend_route.py`（新建或更新現有） | 新增 |

---

## 依賴圖

```
Batch A (Domain + Migration)
    │
    ├──→ Batch B (Repository)
    │         │
    │         └──→ Batch D (Service) ←── Batch C (Engine)
    │                                        │
    │                                        └── (Rules + Schema)
    │
    ├──→ Batch E (API) ←── Batch D
    │         │
    │         ├──→ Batch F (Frontend)
    │         └──→ Batch G (Report Enhancement)
    │
    └──→ Batch H (Tests) ←── All Above
```

---

## 驗收準則

1. `alembic upgrade head` 成功，018 migration 建立 `domain_clinical_decisions` 和 `domain_clinical_decision_traces` 兩張表
2. POST /api/v1/clinical-decision 回傳完整 Clinical Decision JSON
3. GET /api/v1/clinical-decision/{id} 回傳相同資料
4. Clinical Decision 的 recommendation_id 可追溯到 Phase 3A 的 Recommendation
5. Frontend Clinical Decision Page 可正常顯示並可從 Navigation Menu 進入
6. Recommendation Report HTML 包含 Clinical Decision 資訊
7. `go test ./...` 全部通過
8. Review Score ≥ 90
