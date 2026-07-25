# Phase 3B Final Acceptance Fix — 執行計劃

## 概述

本計劃針對 Phase 3B ChatGPT GitHub Review 86/100 的兩個 P0 缺陷進行修復，**不新增任何其他功能**。

| P0 | 缺陷 | 狀態 | 處理方式 |
|----|------|------|----------|
| P0-1 | Migration 018 的 `trace_id unique` 與 ORM `UniqueConstraint("trace_id", "step_order")` 不一致 | 未修 | 新增 Migration 019 |
| P0-2 | 前端呼叫 `GET /api/v1/clinical-decision?patient_id=...`，後端無 Collection API | 未修 | 新增 Repository + Service + Router |

### 當前程式碼差異摘要

- **Migration 018**：`trace_id` 定義為 `unique=True, nullable=False, index=True`，無 compound unique
- **ORM `ClinicalDecisionTraceModel`**：`trace_id` 為 `unique=False`，但有 `UniqueConstraint("trace_id", "step_order", name="uq_trace_step")`
- **Repository**：已有 `list_by_patient_id`，**缺少** `count_by_patient_id`
- **Service**：已有 `list_decisions_by_patient`，**缺少** `count_decisions_by_patient`
- **Router**：只有 `POST ""` 和 `GET "/{decision_id}"`，**缺少** `GET ""` (Collection)
- **Frontend `clinical_decision.ts`**：已定義 `fetchClinicalDecisionsByPatientId` 呼叫 `/clinical-decision?patient_id=...` 及 `ClinicalDecisionListResponse`，**但後端不存在**
- **Frontend `ClinicalDecisionListPage.tsx`**：已實作完整列表 UI，**但無法正常運作**

---

## Batch A：Migration 019（TASK-FIX-01 + TASK-FIX-06）

| 項目 | 內容 |
|------|------|
| **負責角色** | backend-logic / db-modeler |
| **依賴** | 無 |
| **檔案** | `migrations/versions/019_phase3b_trace_compound_unique.py` |

### 操作步驟

#### Step A1 — 建立 Migration 019

```python
"""phase3b_trace_compound_unique

Revision ID: 019
Revises: 018
Create Date: 2026-07-26

Align migration with ORM: drop trace_id unique, create compound unique(trace_id, step_order).
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "019"
down_revision: Union[str, None] = "018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Drop trace_id unique constraint
    op.drop_constraint("uq_domain_clinical_decision_traces_trace_id", "domain_clinical_decision_traces", type_="unique")
    # 2. Create normal index on trace_id (keep existing index util)
    #    若原 unique 已含 index，則需重建普通 index
    op.create_index("ix_domain_clinical_decision_traces_trace_id", "domain_clinical_decision_traces", ["trace_id"])
    # 3. Create UNIQUE(trace_id, step_order)
    op.create_unique_constraint("uq_trace_step", "domain_clinical_decision_traces", ["trace_id", "step_order"])

def downgrade() -> None:
    # 1. Drop compound unique
    op.drop_constraint("uq_trace_step", "domain_clinical_decision_traces", type_="unique")
    # 2. Drop normal index
    op.drop_index("ix_domain_clinical_decision_traces_trace_id", table_name="domain_clinical_decision_traces")
    # 3. Restore trace_id unique
    op.create_unique_constraint("uq_domain_clinical_decision_traces_trace_id", "domain_clinical_decision_traces", ["trace_id"])
```

> **注意**：實際 constraint 名稱需確認 Migration 018 在 PostgreSQL 中自動產生的名稱。若 018 使用 `sa.UniqueConstraint` 則名稱不同。建議先執行 `alembic upgrade 018` 後在 psql 中確認。若名稱不符，以實際 PostgreSQL 產生的名稱為準。

#### Step A2 — Migration Tests

新增 migration tests（`tests/migrations/test_019_migration.py` 或合併至既有 migration test suite）：

- **Case 1**：`alembic upgrade 018` → `alembic upgrade 019` → Insert 5 trace steps → **PASS**
- **Case 2**：`alembic downgrade 018` → **PASS**
- **Case 3**：`alembic upgrade 019` → **PASS**

驗證點：
- 018→019 後可插入多筆相同 `trace_id` 但不同 `step_order` 的步驟
- downgrade 後恢復唯一 `trace_id`
- re-upgrade 後 compound unique 再次生效

---

## Batch B：Collection API（TASK-FIX-02 + TASK-FIX-03 + TASK-FIX-04 + TASK-FIX-05）

| 項目 | 內容 |
|------|------|
| **負責角色** | api-designer / backend-logic / test-writer |
| **依賴** | Batch A（無直接依賴，可並行） |

### 操作步驟

#### Step B1 — Repository 新增 `count_by_patient_id`

**檔案**：`src/backend/repositories/clinical_decision_repo.py`

在 `ClinicalDecisionRepository` 類別中新增方法：

```python
async def count_by_patient_id(
    self,
    patient_id: uuid.UUID,
) -> int:
    """Count clinical decisions for a patient.

    Parameters
    ----------
    patient_id : uuid.UUID
        The patient's UUID.

    Returns
    -------
    int
        Total number of clinical decisions for this patient.
    """
    from sqlalchemy import func
    stmt = (
        select(func.count())
        .select_from(ClinicalDecisionModel)
        .where(ClinicalDecisionModel.patient_id == patient_id)
    )
    result = await self.db.execute(stmt)
    return result.scalar_one()
```

#### Step B2 — Service 新增 `count_decisions_by_patient`

**檔案**：`src/backend/services/clinical_decision_service.py`

在 `ClinicalDecisionService` 類別中新增方法：

```python
async def count_decisions_by_patient(
    self,
    patient_id: UUID,
) -> int:
    """Count total clinical decisions for a patient.

    Parameters
    ----------
    patient_id : UUID
        The patient's UUID.

    Returns
    -------
    int
        Total decision count.
    """
    return await self._decision_repo.count_by_patient_id(patient_id)
```

確認 `list_decisions_by_patient` 已存在（第 431-457 行），無需修改。

#### Step B3 — Router 新增 GET Collection Route

**檔案**：`src/backend/api/v1/clinical_decision.py`

新增：

```python
@router.get("", response_model=dict)
async def list_clinical_decisions(
    patient_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    user: UserModel = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List clinical decisions for a patient with pagination."""
    service = ClinicalDecisionService(db=db)
    try:
        patient_uuid = UUID(patient_id)
        decisions = await service.list_decisions_by_patient(
            patient_id=patient_uuid,
            skip=skip,
            limit=limit,
        )
        total = await service.count_decisions_by_patient(patient_id=patient_uuid)
        return {"decisions": [d.model_dump() for d in decisions], "total": total}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception:
        logger.exception("Unexpected error in list_clinical_decisions")
        raise HTTPException(status_code=500, detail="Internal server error")
```

> **重要**：`GET ""`（collection route）必須放在 `GET "/{decision_id}"` **之前**，避免 FastAPI route matching 將 `?patient_id=...` 參數錯誤匹配到 `/{decision_id}`。

#### Step B4 — API Tests

新增測試檔案 `tests/api/test_clinical_decision_list_api.py`，至少包含：

| Test Case | 描述 |
|-----------|------|
| List Empty | 查詢無決策的患者 → `{"decisions": [], "total": 0}` |
| List One | 建立一筆決策後查詢 → 回傳 1 筆 |
| Pagination | 建立多筆，驗證 skip/limit 正確分頁 |
| Wrong Patient | 無效 UUID → 422 |
| Unauthorized | 無 token → 401 |

---

## Batch C：Frontend Integration Test（TASK-FIX-07）

| 項目 | 內容 |
|------|------|
| **負責角色** | test-writer / frontend-logic |
| **依賴** | Batch B（API 必須已存在） |

在 `tests/frontend/` 或現有 frontend test suite 中新增 integration test：

- **真正呼叫 List API**（不 mock）
- 測試流程：
  1. 通過後端 API 建立一個 patient + 一個 clinical decision
  2. 呼叫 `GET /api/v1/clinical-decision?patient_id=...`
  3. 驗證回傳 decisions 陣列包含剛建立的決策
  4. 驗證 total 正確
- 不可使用 mock 來繞過不存在 endpoint

---

## Batch D：回歸驗證 + Git Push（TASK-FIX-08）

| 項目 | 內容 |
|------|------|
| **負責角色** | exec-dev |
| **依賴** | Batch A + B + C |

### 完整回歸測試

```bash
# Backend tests
go test ./tests/...  # 若有 Go tests
# 或 Python tests
pytest tests/ --cov=src/backend --cov-report=term

# Migration tests
pytest tests/migrations/ -v

# API tests
pytest tests/api/ -v

# Frontend tests
cd src/frontend && npm test -- --run
```

### Git Commit

```
fix(phase3b): add migration019 and clinical decision collection api
```

Commit 內容需包含：
- `migrations/versions/019_phase3b_trace_compound_unique.py`（新增）
- `src/backend/repositories/clinical_decision_repo.py`（修改）
- `src/backend/services/clinical_decision_service.py`（修改）
- `src/backend/api/v1/clinical_decision.py`（修改）
- 相關測試檔案（新增/修改）

### Git Push

```
git push origin master
```

---

## 返工預案

| 條件 | 動作 |
|------|------|
| Reviewer < 95 | PLANNER resume 重新規劃 |
| API Tests 失敗 | 檢查 route ordering、response schema 是否與 frontend `ClinicalDecisionListResponse` 一致 |
| Migration Tests 失敗 | 確認 constraint 名稱、檢查 downgrade 順序 |
| Frontend Integration Test 失敗 | 確認 API endpoint 已正確部署、response 格式匹配 |
| 最多返工循環 | 5 次後停止並回報 |

---

## 時間線

| Batch | 預估步驟數 | 備註 |
|-------|-----------|------|
| Batch A | 2（Migration + Tests） | 可獨立執行 |
| Batch B | 4（Repo + Service + Router + API Tests） | 可與 Batch A 並行 |
| Batch C | 1（Frontend Integration Test） | 依賴 Batch B |
| Batch D | 1（Regression + Commit + Push） | 依賴全部完成 |

---

## 風險與注意事項

1. **Route Ordering**：`GET ""` 必須在 `GET "/{decision_id}"` 之前註冊，否則 FastAPI 會將 query parameter 請求錯誤匹配到 path parameter
2. **Constraint Name Discovery**：PostgreSQL 自動產生的 unique constraint 名稱與 Alembic 預設可能不同，Migration 中需使用實際名稱
3. **Response Schema Alignment**：後端回傳的 `decisions` 陣列中的每個物件必須完全符合 `ClinicalDecisionResponse` schema（與 frontend 的 `ClinicalDecisionResponse` interface 一致）
4. **無副作用**：不得修改任何與 Phase 3A、Recommendation、CI、Vercel、AGENTS.md 相關的檔案
