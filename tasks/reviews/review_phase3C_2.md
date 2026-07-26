## Reviewer 報告 — Phase 3C（最終評分）

### 檢查清單
- **是否可執行**：YES（所有核心檔案存在且可匯入）
- **是否有錯誤**：YES（6 項測試未通過／錯誤 — 1 項 backend greenlet、1 項 restart recovery 外部 API、4 項前端 mock/timing）
- **是否滿足需求條列**：NO（11 項 Gate 中有 3 項未達 FULL PASS，依 §23 規則滿足需求=NO）
- **是否有測試**：YES（~313 項測試通過 — 145 backend + 168 frontend）

### 細項評分

**完整性：24/25**
- 核心架構完整到位：Domain Models、Engine、Rules、Repository、Service、API、Frontend、Migration 020、Report Section、Tests 全部存在
- 第 1 次 Review 的 5 項主要問題已全部修正：
  - ✅ Frontend 狀態映射（6 種 ConsensusStatus）
  - ✅ List page 使用 `participating_specialties`
  - ✅ Traces relationship `order_by`（測試通過 ✅）
  - ✅ Migration 020 unique constraint 內嵌於 `create_table`（測試 13/13 ✅）
  - ✅ 前端測試 mock 資料部分更新
- 微小缺漏：Frontend TypeScript 介面 `TumorBoardConsensus` 仍宣告 `specialist_opinions` 欄位，但 API response（`ConsensusResponse`）無此欄位。Detail page 有 fallback 邏輯故不影響功能，但型別不精確。

**正確性：23/25**
- 核心邏輯完全正確：Engine 計算 6 種 ConsensusStatus、weighted scoring、dissent extraction、threshold 管理完全符合需求 §6-§7
- P0 資料一致性驗證（patient/recommendation/clinical-decision 三角連結）完整實作 §8
- Transaction all-or-nothing 正確實作 §13
- 所有 API endpoint 行為正確（POST 201 / GET 200 / 404 / 422 / 500）
- 扣分原因：
  - 前端型別與 API contract 不一致（`specialist_opinions` 不存在於 response 但 frontend interface 宣稱存在）
  - 4 項前端測試失敗反映 mock 與頁面互動的 gap（非 production bug 但代表測試不精確）

**可維護性：24/25**
- 程式碼結構優良：Repository Pattern、Service Transaction Boundary、Engine 分層清晰
- `ConsensusRuleSet` 集中管理 threshold（符合 §7 要求）
- 使用 `Enum`（`ConsensusStatus`, `Position`）而非 if/elif 鏈
- Docstring 充足，遵循既有模式
- 扣分：前端型別中含略微誤導的 `specialist_opinions` 欄位（雖然有 fallback 無實際影響）

**測試與驗證：20/25**
- **大幅進步**：Migration 020 測試從第 0 次 0/11 → 第 1 次 12/13 → 本次 **13/13 ✅**
- **全部測試統計**：
  - Backend Engine 測試：39/39 ✅
  - Backend Model/Repo/Service/API 測試：88/89 ⚠️（1 fixture ERROR = async SQLite greenlet，同既有 `test_clinical_decision_models.py` 之間歇性問題）
  - Digital Thread 測試：5/5 ✅
  - Migration 020 測試：13/13 ✅
  - Frontend 測試：168/172 ⚠️（4 項為 mock 資料 selector/等待問題）
  - Restart Recovery 測試：0/1 ❌（外部 NCCN/ESMO/OncoKB API 授權不可用）
- 測試覆蓋率充足，但部分測試因環境限制無法通過：
  1. `test_commit_failure_rollback` — async SQLite + greenlet 問題（既有 fixtures 問題）
  2. `test_end_to_end_restart_recovery` — 需外部 API 授權
  3. 4 項前端測試 — mock 資料與 UI 互動的 selector/等待問題
  4. CI（GitHub Actions Postgres Gate）未在本環境執行

### 總分：91/100

依 §23 Reviewer Gate 規則：
- 11 項 Gate 中有部分項目為 PARTIAL/FAIL → **滿足需求 = NO**
- 依 §20：CI 未通過 → **Reviewer 最高 89**
- **最終評分：89/100**

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
- traces relationship 已加入 `order_by` ✅
- `test_multiple_traces_ordered_by_step` 已通過 ✅

[✅] 5. **Transaction All-or-Nothing**：PASS
- Service commit 成功 / rollback 失敗
- `test_commit_failure_rollback` 因 fixture 問題 ERROR（async SQLite greenlet），但 rollback 邏輯本身正確（其他 rollback 測試 PASS）

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
- ⚠️ 4 項前端測試失敗（mock 資料 selector/等待問題，非 production bug）
- ⚠️ Frontend type `TumorBoardConsensus` 含 `specialist_opinions` 但 API response 無此欄位（有 fallback 邏輯）

[✅] 8. **Digital Thread 可還原**：PASS
- 測試驗證 Patient → Recommendation → Clinical Decision → Tumor Board Consensus 完整鏈
- FK 鏈完整
- 可從 Consensus 回溯至 Patient

[⚠️] 9. **Restart 後可讀**：PARTIAL
- Restart recovery test 存在且結構正確
- 在本環境因外部 API（NCCN/ESMO/OncoKB）授權問題導致 recommendation 建立失敗（422）
- 需在真實 CI（Postgres + all services）上驗證

[✅] 10. **Migration 020 upgrade/downgrade/re-upgrade**：PASS
- 檔案存在且結構正確 ✓
- 建立 3 張表 ✓
- FK、Indexes 正確 ✓
- Unique constraint 內嵌於 create_table（SQLite 相容） ✅
- upgrade/downgrade/re-upgrade 測試全數 PASS（13/13 ✅）
- 第 0 次 review 時 0/11、第 1 次 review 時 12/13 → 本次 13/13 ✅

[❌] 11. **Postgres CI 全綠**：FAIL
- CI workflow 已包含 Postgres service 和 tumor board tests 步驟
- 但未觀察到真實 GitHub Actions CI 執行結果
- 依 §20：CI 未通過 → Reviewer 最高 89

---

### 問題修復追蹤（橫跨 3 次 Review）

| # | 問題 | Review 0 | Review 1 | Review 2 (本次) |
|---|------|---------|---------|----------------|
| 1 | Frontend Status 映射（不認識 consensus status） | ❌ | ✅ | ✅ |
| 2 | List page 使用 `specialist_opinions` | ❌ | ✅ | ✅ |
| 3 | Traces relationship 缺少 order_by | ❌ | ✅ | ✅ |
| 4 | Migration 020 unique constraint 在 SQLite 失效 | ❌ | ✅ | ✅ |
| 5 | 前端測試 mock 資料 | ⚠️ | ⚠️ | ⚠️（部分改善但仍有 4 項失敗） |
| 6 | Migration FK 測試斷言 | ❌ | ⚠️ | ✅（13/13 ✅） |
| 7 | Frontend type `specialist_opinions` 不精確 | — | ⚠️ | ⚠️（仍有但無功能影響） |

### 當前問題摘要

**高優先級**（影響評分但無法在此環境解決）：
1. **CI 未在 Postgres 上執行**（§20 硬性要求 → 最高 89）
2. **Restart Recovery 測試因外部 API 授權不可用而失敗**

**中優先級**：
3. **前端 4 項測試失敗**（mock selector 精確度 + 等待時機）
4. **Frontend type `specialist_opinions`**：型別與 API contract 不完全一致

**低優先級**（既有問題，非 Phase 3C 引入）：
5. **`test_commit_failure_rollback`**：async SQLite greenlet 問題（同 `test_clinical_decision_models.py`）

---

### 結論

經過 2 輪返工修復，Phase 3C Tumor Board Consensus Engine 的核心功能已完整、正確、可維護。全部 5 項主要問題已修正，Migration 020 測試從 0/11 → 13/13 ✅，所有 API/Service/Engine 功能正常。

但因以下硬性條件無法在本環境滿足：
1. §23 規則：Gate 項目有 PARTIAL/FAIL → 滿足需求 = NO → 最高 89
2. §20 規則：CI（GitHub Actions Postgres Gate）未執行 → 最高 89
3. 即使忽略上述規則，部分測試仍因環境限制（外部 API 授權、async SQLite greenlet、frontend mock timing）無法全綠

**Phase 3C 狀態：PARTIAL**  
**Accepted：NO**（需在真實 GitHub Actions CI 上驗證全部測試綠燈並達成 ≥95 分）  
**Ready for Phase 3D：NO**

**最終評分：89/100**

**為達成 Accepted 需補足的條件**：
1. 推送至 GitHub 並在 GitHub Actions Postgres CI 上驗證全部測試 ✅
2. 確認 4 項前端測試在真實 CI 環境中是否通過（本環境的 timing issue 可能在 CI 中消失）
3. 若 CI 全部綠燈且無新增問題，可重啟 Reviewer 評分 ≥95 後標記 Accepted

---

*報告產生時間：2026-07-26*
*評分規則：§20（CI 未通過最高 89）+ §23（滿足需求=NO 最高 89）*
