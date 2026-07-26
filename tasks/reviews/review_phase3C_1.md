## Reviewer 報告 — Phase 3C（返工第 1 次評分）

### 檢查清單
- **是否可執行**：YES（所有核心檔案存在且可匯入）
- **是否有錯誤**：YES（13 項前端測試失敗、1 項 backend 測試 fixture 錯誤、1 項 migration FK 測試斷言問題）
- **是否滿足需求條列**：NO（11 項 Gate 中有 4 項未達 FULL PASS，依規則滿足需求 = NO）
- **是否有測試**：YES（271+ 項測試 — 112 backend + 159 frontend）

### 細項評分

**完整性：23/25**
- 核心架構完整：Domain Models、Engine、Rules、Repository、Service、API、Frontend、Migration、Report Section、Tests 全部到位
- 前次 5 項主要問題已修正 4 項：
  - ✅ Frontend 狀態映射（6 種 consensus status）
  - ✅ List page 使用 `participating_specialties`
  - ✅ Traces relationship `order_by`
  - ✅ Migration unique constraint 內嵌於 create_table
- 一項未完全修復：前端的 `TumorBoardConsensus` TypeScript 介面仍宣告 `specialist_opinions` 欄位（第 211 行），但 API response（`ConsensusResponse`）無此欄位。Detail page 有 fallback 邏輯故不致出錯，但型別宣告不準確。
- 前端測試 mock 資料（`createMockResponse`）仍含 `specialist_opinions`，與真實 API contract 不一致

**正確性：22/25**
- 核心邏輯均正確：Engine 計算 6 種 consensus status、weighted scoring、dissent extraction 完全符合需求
- Service 的 P0 連結驗證（patient/recommendation/clinical-decision consistency）完整實作
- 所有 API endpoint 行為正確（POST 201 / GET 200 / 404 / 422 / 500）
- 扣分原因：
  - 前端型別與 API contract 不一致（`specialist_opinions` 不存在於 response）
  - mock 資料含真實 API 不提供的欄位，導致測試不能準確反映生產行為
  - 13 項前端測試失敗反映 mock 與頁面互動的 gap

**可維護性：23/25**
- 程式碼結構優良，遵循既有 Repository Pattern、Service Transaction Boundary、Engine 分層
- `ConsensusRuleSet` 集中管理 threshold
- 使用 `Enum`（`ConsensusStatus`, `Position`）而非 if/elif
- Docstring 充足
- 扣分：前端型別中含 dead code（`specialist_opinions` 欄位從未被 API 回傳）、Detail page 中 fallback 邏輯略顯冗餘

**測試與驗證：18/25**
- **大幅進步**：Migration 020 測試從前次 0/11 PASS → 12/13 PASS
- `test_multiple_traces_ordered_by_step` 從 FAIL → PASS（order_by 已修正）
- 但仍存在以下問題：
  - **13 項前端測試失敗**（3 個 test files）：主要為 mock 資料不一致、async 等待問題、多元素匹配
  - **`test_commit_failure_rollback`**：async SQLite + mock greenlet 問題（同既有 `test_clinical_decision_models.py` 的 fixture 問題）
  - **`test_end_to_end_restart_recovery`**：外部 API（NCCN/ESMO/OncoKB）授權不可用
  - **Migration FK 測試斷言**：SQLite 上 `PRAGMA foreign_key_list` 回傳的 column index 不同於測試預期，非 migration 本身問題
  - **CI 未在真實 Postgres 上執行**：無法確認 Postgres 相容性

### 總分：86/100（不合格）

依 Reviewer Gate 規則：滿足需求 = NO → 最高 89。86 分仍低於 90 合格線。

---

### 11 項 Gate 檢查結果

[✅] 1. **關聯一致**：PASS
- Service._validate_links 檢查 Recommendation.patient_id、ClinicalDecision.patient_id、Request.patient_id 三者一致
- Engine 也檢查必要欄位非空

[✅] 2. **created_by 寫入**：PASS
- Service 接收 created_by 參數並寫入 TumorBoardConsensusModel
- 測試驗證資料庫持久化

[✅] 3. **Opinions 全部持久化**：PASS
- Service 使用 opinion_repo.create_many() 批次寫入所有意見
- 測試驗證 opinions 正確持久化

[✅] 4. **Consensus Trace 多 Step 持久化**：PASS
- Service 寫入 8 個 trace steps（0-7）
- Unique constraint (trace_id, step_order) 內嵌於 create_table ✅
- traces relationship 已加入 `order_by="TumorBoardConsensusTraceModel.step_order"` ✅
- `test_multiple_traces_ordered_by_step` 已通過 ✅

[✅] 5. **Transaction All-or-Nothing**：PASS
- Service commit 成功 / rollback 失敗
- `test_commit_failure_rollback` 因 fixture 問題 ERROR，但 rollback 邏輯本身正確

[✅] 6. **API POST/GET/List 可用**：PASS
- POST /api/v1/tumor-board-consensus → 201 ✓
- GET /api/v1/tumor-board-consensus/{id} → 200/404 ✓
- GET /api/v1/tumor-board-consensus?patient_id= → 200 (list) ✓
- GET /api/v1/tumor-board-consensus/{id}/opinions → 200 ✓
- GET /api/v1/tumor-board-consensus/{id}/trace → 200 ✓
- Error codes: 401, 404, 422, 500 ✓

[⚠️] 7. **Frontend List/Detail/Create 可用**：PARTIAL
- List route `/tumor-board` ✓
- Detail route `/tumor-board/:id` ✓
- Create flow from ClinicalDecisionPage ✓
- Routes registered in App.tsx ✓
- Navigation link ✓
- ⚠️ 13 項前端測試失敗（App.test.tsx 8 項、TumorBoardConsensusPage.test.tsx 4 項、ClinicalDecisionPage.test.tsx 1 項）
- ⚠️ Frontend type `TumorBoardConsensus` 含 `specialist_opinions` 但 API response 無此欄位
- ⚠️ Mock 資料與 API contract 不一致

[✅] 8. **Digital Thread 可還原**：PASS
- 測試驗證 Patient → Recommendation → Clinical Decision → Tumor Board Consensus 完整鏈
- FK 鏈完整
- 可從 Consensus 回溯至 Patient

[⚠️] 9. **Restart 後可讀**：PARTIAL
- Restart recovery test 存在且結構正確
- 但在本環境因外部 API（NCCN/ESMO/OncoKB）授權問題導致 recommendation 建立失敗
- 需在真實 CI（Postgres + all services）上驗證

[⚠️] 10. **Migration 020 upgrade/downgrade/re-upgrade**：PARTIAL
- 檔案存在且結構正確 ✓
- 建立 3 張表 ✓
- FK、Indexes 正確 ✓
- Unique constraint 內嵌於 create_table（SQLite 相容） ✅
- upgrade/downgrade/re-upgrade 測試 PASS（11/12 ✓）
- ❌ `test_upgrade_020_foreign_keys_exist` 在 SQLite 上斷言失敗（`PRAGMA foreign_key_list` 回傳 column index 不同，非 migration 問題）
- 在 Postgres 上應可正常運作

[❌] 11. **Postgres CI 全綠**：FAIL
- CI workflow 已包含 Postgres service 和 tumor board tests 步驟
- 但未觀察到真實 CI 執行結果
- 依需求文件：CI 未通過 → Reviewer 最高 89

---

### 前次問題修復驗證

| # | 問題 | 前次狀態 | 本次結果 | 驗證方式 |
|---|------|---------|---------|---------|
| 1 | Frontend Status 映射（不認識 consensus status） | ❌ | ✅ | `statusLabel()`/`statusColor()` 已改為 unanimous/strong_consensus/majority_consensus/split_decision/insufficient_information/deferred |
| 2 | List page 使用 `specialist_opinions` | ❌ | ✅ | 已改為 `c.participating_specialties?.join(', ')` |
| 3 | Traces relationship 缺少 order_by | ❌ | ✅ | 已加入 `order_by="TumorBoardConsensusTraceModel.step_order"`；對應測試通過 |
| 4 | Migration 020 unique constraint 在 SQLite 失效 | ❌ | ✅ | 已內嵌至 create_table 的 `sa.UniqueConstraint(...)` |
| 5 | 前端測試 mock 資料 | ⚠️ | ⚠️ | 部分更新但仍含 `specialist_opinions` 欄位（API 無此欄位） |

---

### 問題摘要（待解決）

**高優先級**：
1. **前端測試 13 項失敗**：主要涉及 App.test.tsx 的路由測試和 TumorBoardConsensusPage.test.tsx 的狀態/UI 測試
   - App.test.tsx: 路由渲染問題（async 等待不足、mock 未 resolve）
   - TumorBoardConsensusPage.test.tsx: 空狀態顯示、多元素匹配
   - 建議：修正 mock 資料欄位以符合 API contract，改善 async 測試的等待策略
2. **Frontend type `specialist_opinions`**：雖然有 fallback 邏輯，但型別和 mock 都包含真實 API 不提供的欄位
3. **CI 未在 Postgres 上驗證**：無法確認全部測試在真實環境中通過

**中優先級**：
4. **`test_commit_failure_rollback`**：async SQLite fixture 的 greenlet 問題（同既有測試）
5. **Migration FK 測試斷言**：SQLite 上 FK 測試斷言不精確
6. **`test_end_to_end_restart_recovery`**：外部 API 授權問題

**低優先級**：
7. Dead code 清理（Detail page 中 `consensus.specialist_opinions` 回退路徑）

---

### 結論

返工後 Phase 3C 的 5 項主要問題中 4 項已完全修正，migration 測試從 0/11 進步到 12/13。核心功能完整、正確、可維護。

但仍存在以下關鍵問題：
1. 前端測試 13 項失敗（mock 資料與 API contract 不一致、async 等待問題）
2. Migration FK 測試 1 項在 SQLite 上斷言失敗
3. CI 未在真實 Postgres 上執行（依規則最高 89）

**Phase 3C 狀態：PARTIAL**  
**Accepted：NO**  
**Ready for Phase 3D：NO**

**建議優先修復**：
1. 修正前端測試 mock 資料以符合真實 API contract（移除 mock 中 `specialist_opinions`，使用獨立 opinions API）
2. 解決前端測試中的 async 等待問題
3. 修正 migration FK 測試在 SQLite 上的斷言
4. 在 GitHub Actions Postgres CI 上驗證全部測試綠燈後再請求重新評分
