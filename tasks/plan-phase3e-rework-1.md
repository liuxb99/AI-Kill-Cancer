# Phase 3E 返工計劃 #1（Rework #1）

> 基於 Step 4b 需求回歸檢查結果：1 項 FAIL + 3 項 PARTIAL

---

## 總覽

| 項次 | 問題編號 | 需求章節 | 問題摘要 | 嚴重程度 | 預計工時 |
|------|---------|---------|---------|---------|---------|
| 1 | FAIL-1 | §十四 Alternative Plan | alternatives 不入庫，查詢時永遠為空 | **FAIL** | 3 人時 |
| 2 | PARTIAL-2 | §二十五 Frontend Detail | Detail 頁缺少 Review Date 顯示 | PARTIAL | 0.5 人時 |
| 3 | PARTIAL-3 | §二十六 HTML Report | Report 缺少 Review Date 渲染 | PARTIAL | 0.5 人時 |
| 4 | PARTIAL-4 | §二十八 Postgres CI | 缺少 Migration 023 獨立 empty downgrade + re-upgrade 測試 | PARTIAL | 1 人時 |
| | | | **總計** | | **~5 人時** |

---

## 1. FAIL-1：§十四 Alternative Plan — alternatives 不入庫

### 角色
db-modeler → backend-logic

### 問題描述
`TreatmentPlanEngine.generate()` 已產生 `alternatives` 並在 `_model_to_response()` 的 engine_output 分支（建立時）正確返回，但：
1. `TreatmentPlanModel` 無 `alternative_options` 欄位
2. `_persist_plan()` 未將 alternatives 存入 model
3. `_model_to_response()` 的 DB 讀取分支（`engine_output is None`）永遠返回 `alternatives = []`（第 1345 行）

### 修改檔案清單

| 檔案 | 修改類型 | 說明 |
|------|---------|------|
| `src/backend/domain/treatment_plan.py` | 修改 | TreatmentPlanModel 加入 `alternative_options` 欄位 |
| `migrations/versions/024_add_alternative_options.py` | 新增 | Migration 024：ALTER TABLE 新增欄位 |
| `src/backend/services/treatment_plan_service.py` | 修改 | `_persist_plan()` 儲存 alternatives；`_model_to_response()` 從 model 讀取 |
| `tests/backend/models/test_treatment_plan_models.py` | 修改 | 新增 alternative_options JSON round-trip 測試 |
| `tests/backend/services/test_treatment_plan_service.py` | 修改 | 驗證 alternatives 被正確存入與讀回 |

### 具體修改內容

#### 1.1 TreatmentPlanModel 加入 alternative_options

**檔案**：`src/backend/domain/treatment_plan.py`

在 `review_date` 欄位（第 65 行）之後、`previous_plan_id`（第 66 行）之前插入：

```python
alternative_options = Column(JSON, nullable=True)
```

同時在 `__repr__` 無需特別處理此欄位。

#### 1.2 建立 Migration 024

**檔案**：`migrations/versions/024_add_alternative_options.py`

```python
"""Add alternative_options to domain_treatment_plans

Revision ID: 024
Revises: 023
Create Date: 2026-07-28
"""
from alembic import op
import sqlalchemy as sa

revision = "024"
down_revision = "023"


def upgrade():
    op.add_column(
        "domain_treatment_plans",
        sa.Column("alternative_options", sa.JSON(), nullable=True),
    )


def downgrade():
    # Empty-table guard: only allow downgrade when table has no data
    conn = op.get_bind()
    result = conn.execute(
        sa.text("SELECT COUNT(*) FROM domain_treatment_plans")
    ).scalar()
    if result > 0:
        raise sa.exc.OperationalError(
            "Cannot downgrade 024: domain_treatment_plans has data. "
            "Delete all treatment plan data first.",
            params={},
            orig=Exception("data exists"),
        )
    op.drop_column("domain_treatment_plans", "alternative_options")
```

#### 1.3 _persist_plan() 存入 alternative_options

**檔案**：`src/backend/services/treatment_plan_service.py`

在 `_persist_plan()` 方法中（第 768~785 行），於 `treatment_goals=request.treatment_goals,` 之後或 `start_date` 相關欄位附近，加入：

```python
alternative_options=engine_output.alternatives or None,
```

具體插入點：在第 777 行 `treatment_goals=request.treatment_goals,` 之後、第 778 行 `summary=engine_output.summary,` 之前。

#### 1.4 _model_to_response() 從 DB 讀取 alternatives

**檔案**：`src/backend/services/treatment_plan_service.py`

將第 1345 行：

```python
alternatives = []  # alternatives not stored in DB as separate model
```

改為：

```python
alternatives = model.alternative_options or []
```

#### 1.5 更新 _model_to_response() 的 engine_output 分支（選擇性）

目前 engine_output 分支（第 1294 行）已正確使用 `engine_output.alternatives`，無需修改。

#### 1.6 新增測試

**檔案**：`tests/backend/models/test_treatment_plan_models.py`

在既有 JSON round-trip 測試中（或新增獨立法方法），驗證：

```python
async def test_alternative_options_json_round_trip(self):
    """alternative_options 欄位可寫入 JSON 並正確讀回。"""
    plan = await self._create_plan()
    alt_data = [
        {"drug_name": "Sorafenib", "rank": 2, "overall_score": 0.72},
        {"drug_name": "Pazopanib", "rank": 3, "overall_score": 0.65},
    ]
    plan.alternative_options = alt_data
    await self.async_session.flush()
    self.async_session.expire(plan)
    reloaded = await self.async_session.get(TreatmentPlanModel, plan.id)
    assert reloaded.alternative_options == alt_data
```

**檔案**：`tests/backend/services/test_treatment_plan_service.py`

在 service test 中，驗證：
1. `create_plan()` 後，從 DB 重新查詢的 plan 包含 alternatives
2. 可用 `_make_service().get_plan()` 驗證回應中的 alternatives 不為空

### 驗收條件

| 檢查項 | 預期結果 |
|--------|---------|
| `TreatmentPlanModel.alternative_options` 存在 | Column(JSON, nullable=True) |
| Migration 024 upgrade 執行成功 | `alembic upgrade head` 不報錯 |
| Migration 024 downgrade（空資料）成功 | `alembic downgrade 023` 正常執行 |
| Migration 024 downgrade（有資料）失敗 | 拋出 OperationalError |
| `create_plan()` 存入 alternatives | DB 中 `alternative_options` 欄位有值 |
| `get_plan()` 從 DB 讀取 alternatives | Response.alternatives 與 Engine 輸出一致 |
| 舊 plan（無 alternative_options）查詢不報錯 | 返回空列表 `[]` |

---

## 2. PARTIAL-2：§二十五 Frontend Detail — 缺少 Review Date

### 角色
frontend-logic

### 問題描述
`TreatmentPlanDetailPage.tsx` 的資訊區顯示了 created_by、approved_by、approved_at、activated_at，但未顯示 `review_date`。

### 修改檔案清單

| 檔案 | 修改類型 | 說明 |
|------|---------|------|
| `src/frontend/src/pages/TreatmentPlanDetailPage.tsx` | 修改 | 在 Approval Info 區加入 review_date 卡片 |

### 具體修改內容

**檔案**：`src/frontend/src/pages/TreatmentPlanDetailPage.tsx`

在 Approval Info grid（第 570~596 行）中，於 `activated_at` 卡片（第 590~595 行）之後加入：

```tsx
{plan.review_date && (
  <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4">
    <label className="block text-xs font-medium text-gray-500 uppercase tracking-wider mb-1">審查日期 (Review Date)</label>
    <p className="text-sm text-gray-700">{formatDateTime(plan.review_date)}</p>
  </div>
)}
```

插入位置：第 596 行（`activated_at` 區塊的 `</div>` 結束之後）、第 598 行（Trace 區塊開始之前）。

### 驗收條件

| 檢查項 | 預期結果 |
|--------|---------|
| Detail 頁渲染 review_date | 顯示「審查日期 (Review Date)」卡片 |
| review_date 為 None 時隱藏 | 不顯示該區塊 |
| 日期格式 | 使用既有 `formatDateTime` 函數 |

---

## 3. PARTIAL-3：§二十六 HTML Report — 缺少 Review Date

### 角色
backend-logic

### 問題描述
`report_generator.py` 的 `_render_treatment_plan()` 方法未提取也未渲染 `review_date` 欄位。

### 修改檔案清單

| 檔案 | 修改類型 | 說明 |
|------|---------|------|
| `src/backend/clinical/report_generator.py` | 修改 | 在 `_render_treatment_plan()` 中提取並渲染 review_date |

### 具體修改內容

**檔案**：`src/backend/clinical/report_generator.py`

**步驟 A**：在 `_render_treatment_plan()` 方法開頭（第 1650~1674 行變數萃取區），於 `activated_at`（第 1673 行）之後加入：

```python
review_date = str(tp.get("review_date", ""))
```

**步驟 B**：在 Approval Info 區塊（第 1777~1789 行）中，於 `activated_at` 的 `<dd>` 之後加入：

```python
if review_date:
    approval_parts.append(f"<dt>Review Date</dt><dd>{html_lib.escape(review_date[:10])}</dd>")
```

具體插入點：第 1787 行 `if activated_at:` 區塊之後、第 1788 行 `if approval_parts:` 之前。

### 驗收條件

| 檢查項 | 預期結果 |
|--------|---------|
| Report 渲染 review_date | 顯示「Review Date」欄位 |
| review_date 為空時隱藏 | 不顯示該行 |
| 日期截斷 | 僅顯示日期部分（前 10 字元，即 YYYY-MM-DD） |

---

## 4. PARTIAL-4：§二十八 Postgres CI — 缺少 023 empty downgrade + re-upgrade 測試

### 角色
devops

### 問題描述
CI 中 Postgres Gate 的 Migration 測試（`.github/workflows/ci.yml` 第 171~175 行）僅執行「全降版到 016 + 全升版到 head」，未針對 Migration 023 做獨立的 empty downgrade（023→022）+ re-upgrade（022→023）測試。

### 修改檔案清單

| 檔案 | 修改類型 | 說明 |
|------|---------|------|
| `.github/workflows/ci.yml` | 修改 | 在既有 migration 測試中插入 023 獨立降版測試 |
| `tests/test_migration.py`（或新增腳本） | 選擇性修改 | 可選：新增 Python 輔助驗證 |

### 具體修改內容

**檔案**：`.github/workflows/ci.yml`

在既有的 Postgres Gate migration 測試區塊（第 151~175 行）中，**在「Full downgrade to 016 and re-upgrade」之前**插入 023 獨立降版測試：

```yaml
      - name: Postgres Gate - Migration 023 empty downgrade + re-upgrade
        if: always()
        env:
          DATABASE_URL: ${{ steps.pg_url.outputs.url }}
        run: |
          set -e
          # Ensure treatment plan tables are empty (data was deleted in previous step)
          alembic -c migrations/alembic.ini downgrade 023
          echo "✅ 023→022 downgrade succeeded (empty tables)"
          alembic -c migrations/alembic.ini upgrade 023
          echo "✅ 022→023 re-upgrade succeeded"
```

如果希望同時驗證**有資料時 downgrade 被阻擋**，可在前述 data-deletion 步驟（第 156~170 行）**之前**加入：

```yaml
      - name: Postgres Gate - Migration 023 downgrade blocked when data exists
        if: always()
        env:
          DATABASE_URL: ${{ steps.pg_url.outputs.url }}
        run: |
          set -e
          # Verify downgrade 023→022 is blocked when Treatment Plan tables have data
          alembic -c migrations/alembic.ini downgrade 023 2>&1 && { echo "ERROR: 023→022 downgrade should have been blocked when data exists"; exit 1; } || echo "OK: 023→022 downgrade blocked as expected (data exists)"
```

> **注意**：此阻擋測試需要 `ci-test-pid` 的 Treatment Plan 資料已寫入。若建立 Treatment Plan 資料超出既有測試範圍，可跳過此項（空資料降版 + re-upgrade 已足夠）。

### Migration 024 的延伸考量

本次返工新增 Migration 024，其 empty downgrade + re-upgrade 測試應**一併**加入 CI，比照 023 的模式：

```yaml
      - name: Postgres Gate - Migration 024 empty downgrade + re-upgrade
        if: always()
        env:
          DATABASE_URL: ${{ steps.pg_url.outputs.url }}
        run: |
          set -e
          alembic -c migrations/alembic.ini downgrade 024
          echo "✅ 024→023 downgrade succeeded (empty tables)"
          alembic -c migrations/alembic.ini upgrade 024
          echo "✅ 023→024 re-upgrade succeeded"
```

### 驗收條件

| 檢查項 | 預期結果 |
|--------|---------|
| 023 empty downgrade | `alembic downgrade 023` 成功（空表格降版） |
| 023 re-upgrade | `alembic upgrade 023` 成功（重新升版） |
| 024 empty downgrade（若加入） | `alembic downgrade 024` 成功 |
| 024 re-upgrade（若加入） | `alembic upgrade 024` 成功 |
| 不破壞既有 migration 測試 | 既有 downgrade 016 + upgrade head 仍通過 |

---

## 5. 執行順序與依賴

```
FAIL-1 (Model + Migration)  ← 無依賴
  ├─→ FAIL-1 (Service)       ← 依賴 Model 修改完成
  ├─→ FAIL-1 (Tests)         ← 依賴 Service 修改完成
  ├─→ PARTIAL-4 (CI)         ← 依賴 Migration 024 存在（可有條件地先完成 023 部分）
PARTIAL-2 (Frontend)         ← 無依賴（可並行）
PARTIAL-3 (Report)           ← 無依賴（可並行）
```

建議執行順序：
1. **FAIL-1**（Model → Migration → Service → Tests）
2. **PARTIAL-4**（CI，含 Migration 024 降版測試）
3. **PARTIAL-2**（Frontend，可與其他項並行）
4. **PARTIAL-3**（Report，可與其他項並行）

## 6. 不做的事

- ✅ 不修改 Engine（`treatment_plan_engine.py`）— alternatives 產出邏輯已是正確的
- ✅ 不修改 Repository 層
- ✅ 不修改 API Router
- ✅ 不修改 Graph Event / Outbox 結構
- ✅ 不修改 KnowGraphGo
- ✅ 不重構既有 Migration 023
- ✅ 不修改 `CreatePlanRequest` DTO
- ❌ 不建立獨立的 `TreatmentAlternativeModel` — 採用 JSON 欄位方案，符合 `treatment_goals` 既有 pattern

## 7. 風險與注意事項

- **向後相容**：既有 plan 的 `alternative_options` 欄位為 NULL，`_model_to_response()` 的 `model.alternative_options or []` 保證回退為空列表，不影響舊資料。
- **Migration 024 downgrade guard**：必須確保有資料時拋出異常，比照 Migration 023 的 pattern。
- **Frontend review_date**：需確認 `plan.review_date` 的型別（API 返回 ISO string 或 null），`formatDateTime` 應能正確處理。
