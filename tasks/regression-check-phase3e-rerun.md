# 返工後需求回歸檢查 — Phase 3E（第2次）

> 檢查日期：2025-07-17
> 目的：確認 Step 4b 首次發現的 1 FAIL + 3 PARTIAL 已全部返工修復完畢

---

## FAIL-1：§十四 Alternative Plan（alternatives 不入庫）

| # | 檢查項目 | 結果 | 證據 |
|---|---------|------|------|
| 1 | `TreatmentPlanModel` 有 `alternative_options` JSON 欄位 | **PASS** ✅ | `src/backend/domain/treatment_plan.py:63` — `alternative_options = Column(JSON, nullable=True)` |
| 2 | Migration 024 檔案存在 | **PASS** ✅ | `migrations/versions/024_phase3e_treatment_plan_alternatives.py` 存在 |
| 3 | `_persist_plan()` 寫入 alternatives，`_model_to_response()` 從 DB 讀取 | **PASS** ✅ | `treatment_plan_service.py:786` — 寫入 `alternative_options=engine_output.alternatives`；`treatment_plan_service.py:1347` — 讀取 `model.alternative_options or []`；`treatment_plan_service.py:1381` — 傳入 `TreatmentPlanResponse(alternatives=alternatives)` |
| 4 | `TreatmentPlanResponse` 包含 `alternatives` 字段 | **PASS** ✅ | `treatment_plan_service.py:142` — `alternatives : list[dict]` |

**判定：4/4 PASS ✅ → 已修復**

---

## PARTIAL-2：§二十五 Frontend Detail 頁缺少 Review Date

| # | 檢查項目 | 結果 | 證據 |
|---|---------|------|------|
| 1 | `TreatmentPlanDetailPage.tsx` 有 `review_date` 顯示 | **PASS** ✅ | `src/frontend/src/pages/TreatmentPlanDetailPage.tsx:590-594` — 條件式渲染「審查日期 (Review Date)」區塊 |
| 2 | `treatmentPlan.ts` API 類型有 `review_date` 欄位 | **PASS** ✅ | `src/frontend/src/api/treatmentPlan.ts:59` — `review_date?: string \| null` |

**判定：2/2 PASS ✅ → 已修復**

---

## PARTIAL-3：§二十六 HTML Report 缺少 Review Date

| # | 檢查項目 | 結果 | 證據 |
|---|---------|------|------|
| 1 | `_render_treatment_plan()` 有 `review_date` 渲染 | **PASS** ✅ | `report_generator.py:1674` — 提取 `review_date = str(tp.get("review_date", ""))`；`report_generator.py:1787-1788` — 條件式輸出 `<dt>Review Date</dt><dd>...</dd>` |

**判定：1/1 PASS ✅ → 已修復**

---

## PARTIAL-4：§二十八 Postgres CI 缺少 downgrade + re-upgrade 測試

| # | 檢查項目 | 結果 | 證據 |
|---|---------|------|------|
| 1 | CI 有 Migration 023 Downgrade / Re-upgrade 步驟 | **PASS** ✅ | `.github/workflows/ci.yml:177-183` — `Postgres Integration Gate - Migration 023 Downgrade / Re-upgrade` 步驟，執行 `alembic downgrade 023` + `alembic upgrade 023` |

**判定：1/1 PASS ✅ → 已修復**

---

## 總評

| 項目 | 原始狀態 | 本次檢查 | 結果 |
|------|---------|---------|------|
| FAIL-1：§十四 Alternative Plan | FAIL | 4/4 PASS | **✅ 已修復** |
| PARTIAL-2：§二十五 Frontend Review Date | PARTIAL | 2/2 PASS | **✅ 已修復** |
| PARTIAL-3：§二十六 HTML Report Review Date | PARTIAL | 1/1 PASS | **✅ 已修復** |
| PARTIAL-4：§二十八 Postgres CI | PARTIAL | 1/1 PASS | **✅ 已修復** |

**PASS: 8/8（100%）**
**FAIL: 0**

> **結論：所有 4 項返工修復已全部通過回歸檢查，可進入 Step 5。**
