## Reviewer 報告 — Phase 3C

### 檢查清單
- 是否可執行：YES（所有核心檔案存在且可匯入）
- 是否有錯誤：NO（有 2 項測試失敗、2 項前後端不一致問題）
- 是否滿足需求條列：NO（11 項 Gate 中有 3 項 PARTIAL/FAIL，依規則滿足需求=NO）
- 是否有測試：YES（130+ backend tests +  frontend tests）

### 細項評分

**完整性：21/25**
需求多數達成，但存在以下缺漏：Frontend 狀態映射未對應實際 consensus status 值（unanimous/strong_consensus 等），list page 使用不存在的 `specialist_opinions` 欄位，缺少 `participating_specialties` 支援。Migration 020 的 unique constraint 未內嵌於 CREATE TABLE 中導致 SQLite 測試失敗。Trace 關聯缺少 `order_by`。

**正確性：20/25**
核心邏輯正確——Engine 計算 consensus status 符合需求（6 種狀態均支援），Service 的連結驗證（P0 資料一致性）完整實作，transaction all-or-nothing 正確。但存在以下正確性問題：(1) `traces` relationship 缺少 `order_by`，導致存取時順序不保證 (2) Frontend 狀態標籤不認識實際 consensus status 值 (3) Migration 在 SQLite 上因 `create_unique_constraint` 不支援而全部失敗。

**可維護性：22/25**
程式碼結構良好，遵循 Repository Pattern、Service Transaction Boundary、Engine 分層。ConsensusRuleSet 集中管理 threshold。使用 Enum 而非 if/elif。程式碼註解與 docstring 充足。略扣分因：Trace 關聯沒加 order_by（對 selectin lazy loading 是常見遺漏）。

**測試與驗證：15/25**
有測試但有以下問題：
- Migration 020 測試全部 11 項在 SQLite 上 FAIL（`op.create_unique_constraint` 不支援）
- `test_multiple_traces_ordered_by_step` FAIL（真實程式碼問題）
- `test_commit_failure_rollback` ERROR（測試環境 fixture 問題）
- `test_end_to_end_restart_recovery` FAIL（外部 API 不可用，非程式碼問題，但測試本身需要 mock 或 CI）
- Frontend 測試使用不符合 API 合約的 mock 資料（`status` vs `consensus_status`、`trace_summary` vs separate trace API）
- 沒有 Frontend 測試驗證 consensus 建立流程的端到端行為

### 總分：78/100（不合格）

依 Reviewer Gate 規則：滿足需求=NO → 最高 89。但即使忽略此規則，4 項總分 78 仍低於 90 合格線。

---

### 11 項 Gate 檢查結果

[✅] 1. 關聯一致：PASS
- Service._validate_links 檢查 recommendation.patient_id、clinical_decision.patient_id、clinical_decision.recommendation_id 三者一致性
- Engine 也檢查必要欄位非空

[✅] 2. created_by 寫入：PASS
- Service 接收 created_by 參數並寫入 TumorBoardConsensusModel
- 測試驗證資料庫持久化

[✅] 3. Opinions 全部持久化：PASS
- Service 使用 opinion_repo.create_many() 批次寫入所有意見
- 測試驗證 2 筆 opinions 正確持久化

[⚠️] 4. Consensus Trace 多 Step 持久化：PARTIAL
- Service 寫入 8 個 trace steps（0-7）
- Unique constraint (trace_id, step_order) 正確
- 但 traces relationship 缺少 order_by，存取 model.traces 時順序不保證
- 測試 `test_multiple_traces_ordered_by_step` 因此 FAIL（第 712 行：assert orders == sorted(orders) 失敗）

[✅] 5. Transaction All-or-Nothing：PASS
- Service commit 成功 / rollback 失敗
- commit_failure_rollback 測試因 fixture 問題 ERROR，但 rollback 邏輯本身正確（其他 rollback 測試 PASS）

[✅] 6. API POST/GET/List 可用：PASS
- POST /api/v1/tumor-board-consensus → 201 ✓
- GET /api/v1/tumor-board-consensus/{id} → 200/404 ✓
- GET /api/v1/tumor-board-consensus?patient_id= → 200 (list) ✓
- GET /api/v1/tumor-board-consensus/{id}/opinions → 200 ✓
- GET /api/v1/tumor-board-consensus/{id}/trace → 200 ✓
- Error codes: 401, 404, 422, 500 ✓

[⚠️] 7. Frontend List/Detail/Create 可用：PARTIAL
- List route `/tumor-board` ✓
- Detail route `/tumor-board/:id` ✓
- Create flow from ClinicalDecisionPage ✓
- Routes registered in App.tsx ✓
- Navigation link ✓
- ⚠️ Bug 1: List page 使用 `c.specialist_opinions` 顯示專科，但 List API response 無此欄位（應使用 `participating_specialties`）
- ⚠️ Bug 2: `statusLabel()`/`statusColor()` 只認識 finalized/approved/in_review/pending/draft/rejected，不認識實際值 unanimous/strong_consensus/majority_consensus/split_decision/insufficient_information/deferred
- ⚠️ Bug 3: Detail page 使用 `consensus.trace_summary` 但 API response 無此欄位（trace 應透過獨立 endpoint 取得）

[✅] 8. Digital Thread 可還原：PASS
- 測試驗證 Patient → Recommendation → Clinical Decision → Tumor Board Consensus 完整鏈
- 從 Consensus 可回溯至 Patient
- FK 鏈完整

[⚠️] 9. Restart 後可讀：PARTIAL
- Restart recovery test 存在且結構正確
- 但在本環境因外部 API 不可用（NCCN/ESMO/OncoKB 需授權）導致 recommendation 建立失敗
- 需在真實 CI（Postgres + all services）上驗證

[❌] 10. Migration 020 upgrade/downgrade/re-upgrade：FAIL
- Migration 檔案存在且結構正確 ✓
- 建立 3 張表（domain_tumor_board_consensus, domain_tumor_board_opinions, domain_tumor_board_consensus_traces）✓
- FK、Indexes 正確 ✓
- downgrade 標記為 irreversible ✓
- ❌ `op.create_unique_constraint()` 在 `create_table` 外部呼叫，SQLite 不支援 ALTER TABLE ADD CONSTRAINT
- 全部 11 項 Migration 020 測試在 SQLite 上 FAIL
- 在 Postgres 上應可正常運作，但測試尚未在 Postgres 驗證

[❌] 11. Postgres CI 全綠：FAIL
- CI workflow 已包含 Postgres service 和 tumor board tests 步驟
- 但未觀察到真實 CI 執行結果
- Migration test（line 93）使用 SQLite，020 測試會 FAIL
- 依需求：CI 未通過 → Reviewer 最高 89

---

### 缺漏說明

#### 1. Trace Relationship 缺少 order_by
**檔案**: `src/backend/domain/tumor_board.py` lines 51-56
```python
traces = relationship(
    "TumorBoardConsensusTraceModel",
    back_populates="consensus",
    cascade="all, delete-orphan",
    lazy="selectin",
)
```
缺少 `order_by=TumorBoardConsensusTraceModel.step_order`，導致 `consensus.traces` 存取時順序不保證。Service `_model_to_response` 中 `model.traces[0].trace_id` 可能拿到非第一步的 trace。

**修復建議**：加上 `order_by="TumorBoardConsensusTraceModel.step_order"` 或 `order_by=TumorBoardConsensusTraceModel.step_order`（依匯入方式）。

#### 2. Frontend List Page 使用了不存在的欄位
**檔案**: `src/frontend/src/pages/TumorBoardConsensusListPage.tsx` lines 245-250
```tsx
{c.specialist_opinions && c.specialist_opinions.length > 0
  ? c.specialist_opinions
      .map((s) => s.specialty)
      .filter(Boolean)
      .join(', ')
  : '—'}
```
List API (`ConsensusListResponse`) 回傳 `participating_specialties: list[str]`，而非 `specialist_opinions: list[object]`。應改為 `c.participating_specialties?.join(', ') || '—'`。

#### 3. Frontend Status 映射不匹配
**檔案**: `src/frontend/src/pages/TumorBoardConsensusListPage.tsx` lines 22-70、`TumorBoardConsensusPage.tsx` lines 26-76

`statusLabel()` 和 `statusColor()` 處理的 status 值（finalized, approved, in_review, pending, draft, rejected）與實際 API 回傳的 consensus_status 值（unanimous, strong_consensus, majority_consensus, split_decision, insufficient_information, deferred）完全不符。所有實際狀態會落入 default case，顯示原始英文字串而非中文標籤。

**修復建議**：將 switch cases 改為對應 ConsensusStatus 的六種值。

#### 4. Detail Page trace 使用方式不一致
**檔案**: `src/frontend/src/pages/TumorBoardConsensusPage.tsx` lines 136-145

Detail page 透過 `getTumorBoardConsensusTrace(id)` 獨立取得 trace，這是正確的。但 fallback 使用 `consensus.trace_id` 顯示原始字串（line 461-464），而 API response 的 `trace_id` 只是第一個 trace step 的標識符，並非 trace summary。

#### 5. Migration 020 的 unique constraint 無法在 SQLite 測試
**檔案**: `migrations/versions/020_phase3c_tumor_board_consensus.py` lines 87-91

```python
op.create_unique_constraint(
    "uq_tbc_trace_step",
    "domain_tumor_board_consensus_traces",
    ["trace_id", "step_order"],
)
```

`create_unique_constraint` 使用 ALTER TABLE ADD CONSTRAINT，SQLite 不支援。應將 constraint 內嵌於 `create_table` 的 `sa.UniqueConstraint('trace_id', 'step_order', name='uq_tbc_trace_step')` 參數中。

#### 6. 測試環境問題
- `test_commit_failure_rollback`：Async SQLite fixture 在替換 `commit` 方法後引發 greenlet 錯誤，可能因 async 上下文管理不正確
- `test_end_to_end_restart_recovery`：需要外部 API（NCCN/ESMO/OncoKB）推薦引擎才能建立 recommendation，在本環境無法通過

---

### 結論

Phase 3C Tumor Board Consensus Engine 的核心功能完整實作，包含 Domain Models、Engine、Rules、Repository、Service、API、Frontend、Report Section、Migration 及測試。架構遵循既有模式，程式碼品質良好。

但存在以下關鍵問題導致無法通過 Reviewer Gate：
1. **Frontend 狀態映射錯誤**：不認識實際 values → 需修正 statusLabel/statusColor
2. **Frontend List Page 欄位錯誤**：使用 `specialist_opinions` 而非 `participating_specialties`
3. **Traces relationship 缺少 order_by**：一項測試 FAIL
4. **Migration 020 測試全部 FAIL**：unique constraint 在 SQLite 不支援
5. **CI 未真實執行**：無法確認 Postgres 相容性

**修正優先順序**：
1. 修復 migration 020 的 unique constraint（移至 create_table 內）
2. 修正 frontend 狀態映射和 list page 欄位
3. 加上 traces relationship 的 order_by
4. 在真實 GitHub Actions CI 上驗證全部測試綠燈

**Phase 3C 狀態：PARTIAL**  
**Accepted：NO**  
**Ready for Phase 3D：NO**
