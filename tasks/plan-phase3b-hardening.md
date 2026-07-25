# Phase 3B Hardening — 執行計劃

## 概述

**目標**：修正 ChatGPT GitHub Review 找出的 6 項架構問題（84/100 → ≥95/100），完成 Phase 3B 強化後進入 Phase 3C。

**基線**：Phase 3B Clinical Decision Layer（Commit 2896cb0，Review 94/100 → ChatGPT Review 84/100）

**Reviewer 門檻**：≥ 95 分，低於 95 分須返工。

**禁止修改**：Phase 3A、Migration 001-017、CI、Recommendation Engine、AGENTS、Vercel、Phase 3C/Tumor Board/Consensus Engine。

---

## 一、修改點分析摘要

| # | 優先級 | 問題 | 當前狀態 | 修改檔案 |
|---|--------|------|---------|---------|
| HARDEN-1 | P0 | Recommendation.patient_id 未驗證與 Patient 一致 | Service 載入 recommendation 後未比對 patient_id | `clinical_decision_service.py` |
| HARDEN-2 | P0 | created_by = NULL | API 有 user 但未傳至 Model | `clinical_decision_service.py`, `clinical_decision.py` (API) |
| HARDEN-3 | P0 | context.patient 覆蓋 Database Patient | Service 優先使用 context.patient 而非 DB | `clinical_decision_service.py` |
| HARDEN-4 | P0 | 前端 Navigation 使用假路徑 /sample | Navbar 寫死 `/clinical-decision/sample` | `App.tsx`, `ClinicalDecisionPage.test.tsx`, 新增 `ClinicalDecisionListPage.tsx` |
| HARDEN-5 | P1 | Trace 只有 Step0 | 單一步驟塞滿所有資訊 | `clinical_decision_service.py` |
| HARDEN-6 | P1 | DTO Mutable Default | `=[]` 存在 3 處 | `clinical_decision_service.py` |

---

## 二、任務清單

### Batch 1：P0 修正（高優先級，序列執行）

| ID | 任務 | 負責角色 | 產出檔案 | 預估工時 | 依賴 |
|----|------|---------|---------|---------|------|
| **H1.1** | **P0-1：添加 recommendation.patient_id 驗證** | backend-logic | `src/backend/services/clinical_decision_service.py`（修改） | 0.5h | 無 |
| | 在 `_load_recommendation_data()` 後檢查 `recommendation["patient_id"]` 與傳入的 `patient_uuid` 是否一致 | | | | |
| | 不一致時 raise `ValueError("Recommendation does not belong to this patient")` | | | | |
| | API 層會將 ValueError 映射為 422，Transaction 自動 rollback | | | | |
| **H1.2** | **P0-1 測試：Patient A + Recommendation B → 422 → DB 無資料** | test-writer | `tests/test_clinical_decision_service.py`（追加） | 0.5h | H1.1 |
| | 新增 `test_create_decision_patient_recommendation_mismatch` | | | | |
| | 驗證：assert raises(ValueError) + repo.list_by_patient_id assert 無資料 | | | | |
| **H2.1** | **P0-2：created_by 傳遞鏈** | backend-logic | `src/backend/services/clinical_decision_service.py`, `src/backend/api/v1/clinical_decision.py` | 0.5h | 無 |
| | Service `create_decision()` 新增參數 `created_by: str \| UUID` | | | | |
| | `ClinicalDecisionModel` 建立時傳入 `created_by=UUID(created_by)` | | | | |
| | API 端：`service.create_decision(..., created_by=str(user.id))` | | | | |
| **H2.2** | **P0-2 測試：created_by 驗證** | test-writer | `tests/test_clinical_decision_service.py`（追加） | 0.5h | H2.1 |
| | 新增 `test_create_decision_created_by_set` | | | | |
| | 驗證 persisted model 的 `created_by` == 傳入的 user UUID | | | | |
| | API 層可加 `test_create_decision_created_by_matches_user` | | | | |
| **H3.1** | **P0-3：強制 Database Patient 優先** | backend-logic | `src/backend/services/clinical_decision_service.py`（修改） | 0.5h | 無 |
| | 修改 `create_decision()`：永遠先從 DB 載入 Patient | | | | |
| | 若 context 含 `patient`，只取其 supplementary 欄位（如 allergies、medications），不覆蓋 id/sex/birth_year | | | | |
| | 若 DB 載入失敗（patient not found），raise ValueError | | | | |
| **H3.2** | **P0-3 測試：context 不覆蓋 DB** | test-writer | `tests/test_clinical_decision_service.py`（追加） | 0.5h | H3.1 |
| | 新增 `test_context_patient_does_not_override_db` | | | | |
| | context.patient 含不同 sex/age，驗證最終採用 DB 值 | | | | |
| **H4.1** | **P0-4：Navbar 移除 /sample** | frontend-logic | `src/frontend/src/App.tsx`（修改） | 0.5h | 無 |
| | 將 `{ label: '臨床決策', path: '/clinical-decision/sample' }` 改為 `{ label: '臨床決策', path: '/clinical-decision' }` | | | | |
| **H4.2** | **P0-4：新增 Clinical Decision List Page** | frontend-logic | `src/frontend/src/pages/ClinicalDecisionListPage.tsx`（新增） | 1.5h | H4.1 |
| | 方案 A：建立簡易列表頁，顯示病患的 Clinical Decision 列表 | | | | |
| | 提供輸入 patient_id 表單或從 API 取得清單 | | | | |
| | 點擊項目導航至 `/clinical-decision/{id}` | | | | |
| **H4.3** | **P0-4：註冊 `/clinical-decision` Route** | frontend-logic | `src/frontend/src/App.tsx`（修改） | 0.5h | H4.2 |
| | 新增 `<Route path="/clinical-decision" element={<ClinicalDecisionListPage />} />` | | | | |
| **H4.4** | **P0-4 前端測試更新** | test-writer | `src/frontend/src/test/ClinicalDecisionPage.test.tsx`（修改） | 0.5h | H4.1 |
| | 將 `/clinical-decision/sample` 期望改為 `/clinical-decision` | | | | |
| | 新增 List Page Route 測試 | | | | |

### Batch 2：P1 修正（中優先級，可與 Batch 1 部分並行）

| ID | 任務 | 負責角色 | 產出檔案 | 預估工時 | 依賴 |
|----|------|---------|---------|---------|------|
| **H5.1** | **P1-1：Trace 拆成 5 步驟** | backend-logic | `src/backend/services/clinical_decision_service.py`（修改） | 1h | 無 |
| | 將目前單一步驟 `clinical_decision_evaluate` 拆為： | | | | |
| | Step 1: `load_recommendation` — input: recommendation_id, output: recommendation data summary | | | | |
| | Step 2: `validate_patient` — input: patient_id, recommendation.patient_id, output: validation result | | | | |
| | Step 3: `evaluate` — input: variants, evidence; output: engine raw result (同目前) | | | | |
| | Step 4: `decision` — input: engine result; output: decision_type, confidence, alternatives, contraindications | | | | |
| | Step 5: `persist` — input: decision_id, trace_id; output: status | | | | |
| **H5.2** | **P1-1 測試：驗證 5 步驟存在** | test-writer | `tests/test_clinical_decision_service.py`（追加） | 0.5h | H5.1 |
| | 新增 `test_trace_has_all_steps` | | | | |
| | 使用 `db_session.execute()` 查詢 trace steps，驗證 step_order 0-4 都存在 | | | | |
| | 每個 step_type 符合預期 | | | | |
| **H6.1** | **P1-2：DTO Mutable Default 修正** | backend-logic | `src/backend/services/clinical_decision_service.py`（修改） | 0.5h | 無 |
| | `ClinicalDecisionRequest.variants: list[dict] = []` → `variants: list[dict] = Field(default_factory=list)` | | | | |
| | `ClinicalDecisionResponse.alternatives: list[dict] = []` → `alternatives: list[dict] = Field(default_factory=list)` | | | | |
| | `ClinicalDecisionResponse.contraindications: list[dict] = []` → `contraindications: list[dict] = Field(default_factory=list)` | | | | |

### Batch 3：最終驗證（序列，依賴所有修正完成）

| ID | 任務 | 負責角色 | 產出檔案 | 預估工時 | 依賴 |
|----|------|---------|---------|---------|------|
| **H7.1** | **Backend 整合測試** | test-writer | `tests/test_api_clinical_decision.py`（修改追加） | 1h | H1.1, H2.1, H3.1, H5.1, H6.1 |
| | 更新 API mock 層級討論（review 指出 mock 層級偏高） | | | | |
| | 新增 `test_create_decision_patient_recommendation_mismatch_api`（實穿測試） | | | | |
| **H7.2** | **全面回歸測試** | reviewer | `go test ./...` + `pytest` + `npm test` | 1h | H1.1-H6.1 |
| | `go test ./...` 全部通過 | | | | |
| | `pytest --cov` 確認覆蓋率 | | | | |
| | `npm test` 前端測試通過 | | | | |
| **H7.3** | **Git Commit & Push** | doc-writer | Git 提交 | 0.5h | H7.2 |
| | Commit message: `Phase 3B Hardening: P0/P1 fixes — patient validation, created_by audit, DB patient priority, frontend nav, trace steps, DTO defaults` | | | | |
| | 確認 Commit Scope 不含禁止修改的檔案 | | | | |
| **H7.4** | **Reviewer 評分** | reviewer | `tasks/reviews/review_Phase-3B-Hardening_0.md` | 0.5h | H7.3 |
| | Reviewer 評分 ≥ 95 → PASS | | | | |
| | 若 < 95 → 返工循環 | | | | |

---

## 三、任務依賴關係

```
H1.1 ─── H1.2
  │
H2.1 ─── H2.2
  │
H3.1 ─── H3.2
  │
H4.1 ─── H4.2 ─── H4.3 ─── H4.4
  │
H5.1 ─── H5.2
  │
H6.1（無依賴）
  │
  └─── 全部 ─── H7.1 ─── H7.2 ─── H7.3 ─── H7.4
```

**備註**：
- H1.1、H2.1、H3.1、H4.1、H5.1、H6.1 彼此**無依賴關係**，可並行修改（不同檔案/不同區塊）
- 測試任務（H1.2、H2.2、H3.2、H4.4、H5.2）依賴對應的實作任務
- H7.x 系列依賴所有實作與測試完成

---

## 四、批次分組

### 可並行組（Batch A）
| 任務 | 檔案 | 修改內容 |
|------|------|---------|
| H1.1 | `clinical_decision_service.py` | 添加 patient_id 驗證（約 5 行） |
| H2.1 | `clinical_decision_service.py` + `clinical_decision.py` | created_by 傳遞鏈（約 10 行） |
| H3.1 | `clinical_decision_service.py` | 強制 DB Patient 優先（約 15 行） |
| H4.1 | `App.tsx` | 修改 Nav link（1 行） |
| H5.1 | `clinical_decision_service.py` | Trace 拆步驟（約 40 行） |
| H6.1 | `clinical_decision_service.py` | DTO Mutable Default 修正（3 行） |

**注意**：H1.1、H2.1、H3.1、H5.1、H6.1 都修改同一檔案 `clinical_decision_service.py`，雖邏輯上無依賴，但實務上應**由同一 backend-logic 角色一次性完成**以避免 merge conflict。

### 可並行組（Batch B）
| 任務 | 檔案 |
|------|------|
| H1.2 | `tests/test_clinical_decision_service.py` |
| H2.2 | `tests/test_clinical_decision_service.py` |
| H3.2 | `tests/test_clinical_decision_service.py` |
| H4.4 | `ClinicalDecisionPage.test.tsx` |
| H5.2 | `tests/test_clinical_decision_service.py` |

**注意**：H1.2、H2.2、H3.2、H5.2 皆修改同一測試檔案，建議由同一 test-writer 一次性完成。

### 需序列組
```
H4.1 → H4.2 → H4.3 → H4.4（前端鏈路）
H1.1 → H1.2（實作後測試）
H2.1 → H2.2
H3.1 → H3.2
H5.1 → H5.2
All → H7.1 → H7.2 → H7.3 → H7.4
```

---

## 五、詳細修改說明

### H1.1：P0-1 patient_id 驗證

**修改位置**：`src/backend/services/clinical_decision_service.py` 中 `create_decision()` 方法

**當前代碼**（約 line 218）：
```python
recommendation = await self._load_recommendation_data(rec_id_str)
if recommendation is None:
    raise ValueError(
        f"Recommendation with id '{rec_id_str}' not found",
    )
```

**修改後**：
```python
recommendation = await self._load_recommendation_data(rec_id_str)
if recommendation is None:
    raise ValueError(
        f"Recommendation with id '{rec_id_str}' not found",
    )

# P0-1: Validate recommendation belongs to the same patient
rec_patient_id = recommendation.get("patient_id")
if rec_patient_id and str(rec_patient_id) != str(patient_uuid):
    raise ValueError(
        f"Recommendation '{rec_id_str}' belongs to patient "
        f"'{rec_patient_id}', not patient '{patient_uuid}'",
    )
```

### H2.1：P0-2 created_by 傳遞

**修改位置 A**：`src/backend/api/v1/clinical_decision.py` Line 43

**當前**：
```python
result = await service.create_decision(
    patient_id=request.patient_id,
    recommendation_id=request.recommendation_id,
    variants=request.variants,
    context=request.context,
)
```

**修改後**：
```python
result = await service.create_decision(
    patient_id=request.patient_id,
    recommendation_id=request.recommendation_id,
    variants=request.variants,
    context=request.context,
    created_by=str(user.id),
)
```

**修改位置 B**：`clinical_decision_service.py` `create_decision()` 簽名

**當前**：
```python
async def create_decision(
    self,
    patient_id: str | UUID,
    recommendation_id: str | UUID,
    variants: list[dict],
    context: dict | None = None,
) -> ClinicalDecisionResponse:
```

**修改後**：
```python
async def create_decision(
    self,
    patient_id: str | UUID,
    recommendation_id: str | UUID,
    variants: list[dict],
    context: dict | None = None,
    created_by: str | UUID | None = None,
) -> ClinicalDecisionResponse:
```

**修改位置 C**：`ClinicalDecisionModel` 建立處（約 line 253）

**當前**：
```python
decision_model = ClinicalDecisionModel(
    decision_id=decision_id,
    patient_id=patient_uuid,
    ...
    # created_by 未被設定
)
```

**修改後**：
```python
decision_model = ClinicalDecisionModel(
    decision_id=decision_id,
    patient_id=patient_uuid,
    ...
    created_by=uuid.UUID(created_by) if created_by else None,
)
```

### H3.1：P0-3 context.patient 不覆蓋 DB

**修改位置**：`create_decision()` 方法開頭（約 line 214-216）

**當前邏輯**：
```python
patient_data: dict[str, Any] | None = ctx.get("patient")
if patient_data is None:
    patient_data = await self._load_patient_data(patient_uuid)
```
→ 先看 context，再看 DB

**修改後邏輯**：
```python
# Always load patient from Database — the single source of truth
patient_data = await self._load_patient_data(patient_uuid)

# context.patient is supplemental only — merge non-overlapping fields
ctx_patient = ctx.get("patient")
if ctx_patient and isinstance(ctx_patient, dict):
    for key, value in ctx_patient.items():
        # Do NOT override core identity fields from DB
        if key not in ("id", "patient_id", "external_id", "display_name",
                       "birth_year", "age_range", "sex", "consent_status",
                       "created_at"):
            patient_data[key] = value
```

### H4.1 + H4.2 + H4.3：P0-4 Frontend Navigation

**H4.1：App.tsx Navbar** — 修改 1 行：
```javascript
// 改前
{ label: '臨床決策', path: '/clinical-decision/sample' },
// 改後
{ label: '臨床決策', path: '/clinical-decision' },
```

**H4.2：新增 ClinicalDecisionListPage.tsx** — 簡潔列表頁
- 提供輸入 patient_id 的表單
- 呼叫 GET `/api/v1/clinical-decision?patient_id={id}`（或 POST 後跳轉）
- 顯示決策列表（簡易表格）
- 點擊跳轉至 `/clinical-decision/{decision_id}`

**H4.3：App.tsx Routes** — 追加：
```javascript
import ClinicalDecisionListPage from './pages/ClinicalDecisionListPage'
// ...
<Route path="/clinical-decision" element={<ClinicalDecisionListPage />} />
```

### H5.1：P1-1 Trace 拆 5 步驟

**修改位置**：`create_decision()` 方法中 Trace 建立邏輯（約 line 268-282）

**當前**（單一步驟）：
```python
trace_model = ClinicalDecisionTraceModel(
    trace_id=trace_id,
    recommendation_id=...,
    step_order=0,
    step_type="clinical_decision_evaluate",
    input_summary={...},
    output_summary=result.to_dict(),
    created_at=created_at,
)
```

**修改後**（5 步驟）：

```python
trace_steps = [
    ClinicalDecisionTraceModel(
        trace_id=trace_id,
        recommendation_id=recommendation_uuid,
        step_order=0,
        step_type="load_recommendation",
        input_summary={"recommendation_id": rec_id_str},
        output_summary={
            "status": "loaded",
            "engine_version": recommendation.get("engine_version"),
            "drug_count": len(recommendation.get("recommendations", [])),
        },
        created_at=created_at,
    ),
    ClinicalDecisionTraceModel(
        trace_id=trace_id,
        recommendation_id=recommendation_uuid,
        step_order=1,
        step_type="validate_patient",
        input_summary={
            "patient_id": str(patient_uuid),
            "recommendation_patient_id": recommendation.get("patient_id"),
        },
        output_summary={"valid": True, "match": True},
        created_at=created_at,
    ),
    ClinicalDecisionTraceModel(
        trace_id=trace_id,
        recommendation_id=recommendation_uuid,
        step_order=2,
        step_type="evaluate",
        input_summary={
            "variants": list(variants),
            "evidence_count": len(evidence),
        },
        output_summary=result.to_dict(),  # engine result
        created_at=created_at,
    ),
    ClinicalDecisionTraceModel(
        trace_id=trace_id,
        recommendation_id=recommendation_uuid,
        step_order=3,
        step_type="decision",
        input_summary={
            "decision_type": result.decision_type,
            "confidence": result.confidence,
        },
        output_summary={
            "decision_type": result.decision_type,
            "confidence": result.confidence,
            "alternatives_count": len(result.alternatives),
            "contraindications_count": len(result.contraindications),
        },
        created_at=created_at,
    ),
    ClinicalDecisionTraceModel(
        trace_id=trace_id,
        recommendation_id=recommendation_uuid,
        step_order=4,
        step_type="persist",
        input_summary={
            "decision_id": decision_id,
            "trace_id": trace_id,
        },
        output_summary={"status": "persisted"},
        created_at=created_at,
    ),
]
```

然後迴圈進行 `self._trace_repo.create(step)`。

**注意**：需要先 flush decision_model 取得 id，然後建立所有 trace steps，再 commit。每個 trace step 的 `clinical_decision_id` 需在 decision flush 後設定。

### H6.1：P1-2 DTO Mutable Default

**修改位置**：`ClinicalDecisionRequest` 和 `ClinicalDecisionResponse` 類別

**修改前**：
```python
class ClinicalDecisionRequest(BaseModel):
    patient_id: str
    recommendation_id: str
    variants: list[dict] = []

class ClinicalDecisionResponse(BaseModel):
    evidence_summary: dict | None = None
    alternatives: list[dict] = []
    contraindications: list[dict] = []
```

**修改後**：
```python
from pydantic import Field

class ClinicalDecisionRequest(BaseModel):
    patient_id: str
    recommendation_id: str
    variants: list[dict] = Field(default_factory=list)

class ClinicalDecisionResponse(BaseModel):
    evidence_summary: dict | None = None
    alternatives: list[dict] = Field(default_factory=list)
    contraindications: list[dict] = Field(default_factory=list)
```

---

## 六、返工預案

| 情境 | 觸發條件 | 處理方式 |
|------|---------|---------|
| **P0-1 驗證發現 recommendation.patient_id 回傳 None** | Phase 3A RecommendationModel.patient_id 可為 None | 若 recommendation.patient_id 為 None 時跳過驗證（log warning），或視為不匹配 |
| **created_by 型別衝突** | SQLAlchemy Column(CompatUUID) 與 Pydantic UUID 不一致 | 使用 `uuid.UUID(str(created_by))` 進行標準化 |
| **context.patient merge 邏輯漏掉欄位** | DB Patient 有新的 domain 欄位 | 使用白名單（id, sex, birth_year 等）而非黑名單 |
| **Frontend List Page API 不存在** | 尚無 `GET /api/v1/clinical-decision?patient_id=` | 先使用簡易輸入表單 + POST 跳轉方案，不依賴 list API |
| **Trace 拆步驟後 test 失敗** | 測試檢查 `step_type == "clinical_decision_evaluate"` | 更新測試期望值為 5 個新 step_type |
| **多任務修改同一檔案衝突** | H1.1 + H2.1 + H3.1 + H5.1 + H6.1 都改 `clinical_decision_service.py` | 由同一 backend-logic 角色一次性完成所有變更 |
| **Reviewer 評分 < 95** | AGENTS.md Step 5b 規則 | 自動啟動返工循環：PLANNER(resume) → CODER(resume) → REVIEWER 重新評分 |
| **npm test 因 route 變更失敗** | 測試檢查舊路徑 `/clinical-decision/sample` | 同步更新測試期望值 |

---

## 七、測試策略摘要

### 新增測試一覽

| 測試 ID | 對應任務 | 測試類別 | 驗證重點 |
|---------|---------|---------|---------|
| T1 | H1.2 | Service Unit | `create_decision()` with mismatched patient/recommendation → ValueError |
| T2 | H1.2 | Service Unit | rollback: DB 無殘留 ClinicalDecision / Trace |
| T3 | H2.2 | Service Unit | created_by 等於傳入的 user UUID |
| T4 | H2.2 | API Integration | POST → created_by matches authenticated user |
| T5 | H3.2 | Service Unit | context.patient 有不同 sex → DB sex 保持不變 |
| T6 | H4.4 | Frontend Route | App.tsx 包含 `/clinical-decision`（非 `/clinical-decision/sample`） |
| T7 | H4.4 | Frontend Route | ClinicalDecisionListPage Route 已註冊 |
| T8 | H5.2 | Service Unit | Trace 包含 5 個 steps（step_order 0-4） |
| T9 | H5.2 | Service Unit | 每個 step_type 符合預期名稱 |
| T10 | H7.1 | API Integration | API 端到端測試 patient/recommendation mismatch → 422 |

### 測試分類

| 層級 | 測試框架 | 執行方式 |
|------|---------|---------|
| Backend Unit | pytest | `pytest tests/test_clinical_decision_service.py -v` |
| Backend API | pytest + TestClient | `pytest tests/test_api_clinical_decision.py -v` |
| Frontend | vitest | `npm test -- --run` |
| 整合 | pytest | `pytest tests/test_clinical_decision_integration.py -v` |

### 驗收檢查清單

- [ ] `pytest tests/test_clinical_decision_service.py -v` — 全部通過
- [ ] `pytest tests/test_api_clinical_decision.py -v` — 全部通過
- [ ] `npm test -- --run` — 全部通過
- [ ] `go test ./...`（如有 Go 組件）— 全部通過
- [ ] `git diff --stat` 確認僅修改允許的檔案
- [ ] Reviewer 評分 ≥ 95

---

## 八、執行順序（建議）

```
Phase 1: 所有 P0 實作（H1.1, H2.1, H3.1, H4.1）— 由 backend-logic + frontend-logic 並行
Phase 2: 所有 P0 測試（H1.2, H2.2, H3.2, H4.4）— 由 test-writer 執行
Phase 3: 前端列表頁（H4.2, H4.3）— 由 frontend-logic 執行
Phase 4: P1 實作（H5.1, H6.1）— 由 backend-logic 執行
Phase 5: P1 測試（H5.2）— 由 test-writer 執行
Phase 6: 整合測試更新（H7.1）— 由 test-writer 執行
Phase 7: 全面回歸測試（H7.2）
Phase 8: Git Commit & Push（H7.3）
Phase 9: Reviewer 評分（H7.4）
```

---

## 九、Commit Scope 確認

### 允許修改的檔案

| 檔案 | 修改內容 |
|------|---------|
| `src/backend/services/clinical_decision_service.py` | P0-1, P0-2, P0-3, P1-1, P1-2 |
| `src/backend/api/v1/clinical_decision.py` | P0-2（傳遞 created_by） |
| `src/frontend/src/App.tsx` | P0-4（修改 Nav path + 新增 Route） |
| `src/frontend/src/pages/ClinicalDecisionListPage.tsx` | **新增** |
| `src/frontend/src/test/ClinicalDecisionPage.test.tsx` | P0-4（更新期望值） |
| `tests/test_clinical_decision_service.py` | 新增測試 |
| `tests/test_api_clinical_decision.py` | 新增測試 |
| `tasks/plan-phase3b-hardening.md` | **本計劃檔案** |
| `tasks/summary-report-phase3b-hardening.md` | 總結報告（新增） |
| `tasks/requirements.md` | 追加 Phase 3B Hardening 完成記錄 |

### 禁止修改的檔案

- `migrations/versions/001-017`（任何既有 migration）
- `src/backend/domain/recommendation.py`（Phase 3A 領域模型）
- `src/backend/repositories/recommendation_repo.py`（Phase 3A Repository）
- `src/backend/services/recommendation_service.py`（Phase 3A Service）
- `src/backend/api/v1/recommendation.py`（Phase 3A API）
- `src/backend/clinical/clinical_decision_engine.py`（Phase 3B Engine — 非修改範圍）
- `src/backend/domain/clinical_decision.py`（Phase 3B Domain Model — 非修改範圍，如需修改只允許 created_by 欄位未使用問題，但 P0-2 只需在 Service 層傳值即可）
- `src/backend/repositories/clinical_decision_repo.py`（非修改範圍）
- `AGENTS.md`、CI/CD、Vercel 配置
- `.claude-agents/` 中的角色定義

---

## 十、風險評估

| 風險 | 影響 | 機率 | 緩解措施 |
|------|------|------|---------|
| H1.1/H2.1/H3.1/H5.1/H6.1 同時編輯同一檔案導致衝突 | 高 | 中 | 由同一 backend-logic 角色一次性完成 |
| Frontend List Page 需要新增 API endpoint | 中 | 低 | 先用 POST+redirect 方案，不依賴 list API |
| Phase 3C 功能被誤改 | 高 | 低 | 嚴格遵守禁止事項，commit 前 git diff 檢查 |
| Trace 拆步驟後導致 DB 相容性問題 | 中 | 低 | 不修改 migration schema，只改變資料寫入方式 |
| Reviewer 評分 < 95 | 高 | 中 | 提前準備返工循環 |

---

## 十一、完成條件

1. 所有 6 項 HARDEN 任務（H1-H6）實作完成
2. 至少 10 項新增測試全部通過
3. `pytest` + `npm test` 全部綠色
4. Git diff 僅包含允許範圍
5. Reviewer 評分 ≥ 95
6. Phase 3B Hardening 總結報告產出

---

*計劃版本：v1.0*
*作者：PLANNER*
*日期：2026-07-26*
