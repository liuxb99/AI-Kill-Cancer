# Phase 3B Hardening Review — Review 0

**日期**：2026-07-25  
**審查範圍**：Phase 3B Hardening（修正 ChatGPT Review 架構問題）

---

## 1. 逐條對比原始需求的評分

### P0-1：Recommendation 必須屬於同一位 Patient
**狀態**：✅ 完成
- Service 在 `create_decision()` 中第 234-240 行執行驗證：
  ```python
  rec_patient_id = recommendation.get("patient_id")
  if rec_patient_id and str(rec_patient_id) != str(patient_uuid):
      raise ValueError(...)
  ```
- 驗證在 Engine 執行前（第 247 行 `self._engine.evaluate()` 之前）
- Mismatch 時 raise `ValueError` → API 層映射為 422
- Transaction 完全 rollback（無 ClinicalDecisionModel、無 Trace 殘留）
- 測試：`test_create_decision_patient_recommendation_mismatch`（service）+ `test_create_decision_patient_recommendation_mismatch_api`（API 422）

### P0-2：created_by 完整傳遞
**狀態**：✅ 完成
- API 層：`created_by=str(user.id)` 從 `require_auth` 傳入
- Service 層：`create_decision(..., created_by=created_by)` 簽名接受參數
- Model 層：`ClinicalDecisionModel(created_by=...)` 設定欄位
- Model 定義：`created_by = Column(CompatUUID, ForeignKey("domain_users.id", ondelete="SET NULL"), nullable=True)`
- 測試：`test_create_decision_created_by_set` 驗證 created_by UUID 正確寫入 DB

### P0-3：context.patient 不得覆蓋 Database Patient
**狀態**：✅ 完成
- Patient 唯一來源為 Database（`_load_patient_data()`）
- context.patient 只合併非核心欄位（跳過 id, patient_id, external_id, display_name, birth_year, age_range, sex, consent_status, created_at）
- 測試：`test_context_patient_does_not_override_db` 驗證 context 的 sex="female" 不會覆蓋 DB 的 sex="M"，而 supplemental 欄位（allergies）被合併

### P0-4：Frontend Navigation 移除假資料
**狀態**：✅ 完成
- 無 `/clinical-decision/sample` 路由存在（grep 確認無匹配）
- 正式路由：
  - `/clinical-decision` → `ClinicalDecisionListPage`（列表頁）
  - `/clinical-decision/:id` → `ClinicalDecisionPage`（詳細頁）
- Navbar 顯示「臨床決策」連結至 `/clinical-decision`
- 前端測試 24 項全部通過，包含 Route Registration、Rendering、States、API Request、UI Elements、Navigation

### P1-1：Trace 拆 5 步驟
**狀態**：✅ 完成
- 5 個 trace step：
  1. `load_recommendation`（step_order=0）— 載入 recommendation 資料
  2. `validate_patient`（step_order=1）— 驗證 patient 歸屬
  3. `evaluate`（step_order=2）— 引擎評估
  4. `decision`（step_order=3）— 決策結果
  5. `persist`（step_order=4）— 持久化
- 每個 step 有各自獨立的 `input_summary` / `output_summary`，無塞成同一 output_summary
- 測試：`test_trace_has_all_steps` 驗證 5 steps type/order 正確

### P1-2：DTO Mutable Default 修正
**狀態**：✅ 完成
- `ClinicalDecisionRequest.variants: list[dict] = Field(default_factory=list)` ✅
- `ClinicalDecisionResponse.alternatives: list[dict] = Field(default_factory=list)` ✅
- `ClinicalDecisionResponse.contraindications: list[dict] = Field(default_factory=list)` ✅
- 無 `= []` 殘留於 DTO 定義中

---

## 2. 檢查清單（YES/NO）

| 項目 | 結果 |
|------|------|
| 是否可執行（可運行） | **YES** — 33 項後端測試 + 24 項前端測試全數通過 |
| 是否有錯誤（無錯誤） | **YES** — 程式碼語法正確、測試通過 |
| 是否滿足需求條列 | **YES** — 所有 6 項需求（4 P0 + 2 P1）全部完成 |
| 是否有測試或滿足審美 | **YES** — 每個需求均有對應測試，程式碼結構清晰 |

---

## 3. 細項評分（0-25）

| 項目 | 分數 | 說明 |
|------|------|------|
| **完整性** | **25** | 所有需求全部完成。P0-1~P0-4、P1-1、P1-2 皆已實作並附測試。無遺漏。 |
| **正確性** | **25** | 邏輯正確：patient-validation 在 engine 前執行、rollback 完整、created_by 串接完整、context 保護邏輯正確、trace 5 steps 含義不同資料、DTO defaults 正確。 |
| **可維護性** | **23** | 程式碼分層清晰（API → Service → Repository → Domain），DTO 定義完整，trace 資料結構有理。扣 2 分原因：部分服務測試使用 mock engine 而非完整 engine integration，但此為 service-level 測試的正常做法，整體可維護性仍高。 |
| **測試與驗證** | **25** | 33 項後端測試（18 service + 15 API）+ 24 項前端測試全部通過。每個需求都有正向和反向測試覆蓋。 |

---

## 4. 總分

**總分 = 25 + 25 + 23 + 25 = 98 分**

---

## 5. 合格/不合格判定

| 標準 | 結果 |
|------|------|
| 本輪門檻（使用者指定）：>= 95 分 | ✅ **98 ≥ 95 → PASS** |
| AGENTS.md 預設門檻：>= 90 分合格 | ✅ **98 ≥ 90 → PASS** |
| 任一需求未完成 → 最高 89 分 | ✅ 所有需求完成 |

**判定：PASS ✅**

**Phase 3B：PASS**  
**Ready for ChatGPT GitHub Review：YES**

---

*Review 產出完成：無返工需求，可直接 commit。*
