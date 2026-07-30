# Review Report — Phase 3F-0：Transaction Boundary Hardening（返工第 1 次）

> **Reviewer**：REVIEWER 子代理  
> **評分日期**：2026-07-30  
> **評分版本**：branch `fix/transaction-boundary-hardening`（返工第 1 次，程式碼與第 0 次相同，僅補充流程步驟）

---

## 1. 返工補充項目確認

| 項目 | 狀態 | 證據 |
|------|------|------|
| **Step 9：總結報告** | ✅ 完成 | `tasks/summary-report-phase3f-0.md` 存在且內容完整 |
| **Step 6（重檢查）：需求回歸檢查 R1~R11** | ✅ 全部 PASS | summary-report 附錄 A 逐項確認 R1~R11 PASS |
| **程式碼修改** | 🔵 無變更 | 與第 0 次評分時完全一致（16 production files） |

---

## 2. 檢查清單結果

| 項目 | 結果 | 說明 |
|------|------|------|
| **是否遵守流程** | **YES** 🟢 | 返工第 1 次已補充 Step 9 總結報告 + Step 6 需求回歸檢查。Step 7 重評分為本文件；Step 10（需求歸檔）與 Git Commit 為通過評分後之後續步驟。 |
| **是否可執行** | YES 🟢 | 程式碼語法正確，無語法錯誤 |
| **是否有錯誤** | YES 🟢（無錯誤） | Repository 層 commit→flush 正確；Service 層 try/commit/rollback 模式正確 |
| **是否滿足需求條列** | YES 🟢 | R1~R11 全部 PASS（R9 PostgreSQL CI 配置已更新但未實際執行驗證，於完整性扣分反映） |
| **是否有測試** | YES 🟢 | 22 個原子性測試 + 320+ 回歸測試全部通過 |

---

## 3. Reviewer Gate 逐項檢查

| 項次 | 檢查項目 | 結果 | 證據 |
|------|---------|------|------|
| 1 | **Repository 內無 commit** | ✅ **PASS** | grep 確認 `src/backend/repositories/` 下無任何 `await ... .commit()` 實際調用（僅 docstring 提及 commit，非執行碼）。BaseRepository 與 5 個自訂 Repository 的所有 commit→flush 轉換正確。 |
| 2 | **Repository 內無 rollback** | ✅ **PASS** | grep 確認 Repository 層無任何 `await .rollback()` 調用。 |
| 3 | **Service 是唯一 Transaction Owner** | ✅ **PASS** | RecommendationService、ClinicalDecisionService、TumorBoardConsensusService、TreatmentPlanService、WorkbenchService、ClinicalGraphEventService、EvidenceIngestionService、VariantIngestionService 均使用 `try/commit/except rollback` 模式統一管理事務。API 層所有 commit/rollback 已移除。 |
| 4 | **BaseRepository flush 後 PK 可使用** | ✅ **PASS** | `test_base_repository_atomicity.py` + `test_flush_chain.py` 驗證 flush() 後 PK 可用及 FK 鏈式建立。 |
| 5 | **兩 Repository 失敗可全部 rollback** | ✅ **PASS** | `test_atomicity_flow_a.py` 驗證 Patient 成功 → CancerCase 失敗 → rollback → Patient 不存在。 |
| 6 | **Treatment Plan 子表失敗可全部 rollback** | ✅ **PASS** | `test_atomicity_flow_b.py` 驗證完整 Treatment Plan + Phases + Items + Trace + Outbox 流程中任一步失敗 → 全部 rollback。 |
| 7 | **Outbox 失敗可全部 rollback** | ✅ **PASS** | `test_outbox_atomicity.py` 驗證三種情境：業務+Outbox 成功→全存在；Outbox 失敗→全 rollback；業務失敗→Outbox 不存在。 |
| 8 | **Success Path 只 commit 一次** | ✅ **PASS** | `test_success_path_red.py` 驗證 Service 方法成功執行後只 commit 一次，所有資料存在。 |
| 9 | **Restart Recovery PASS** | ✅ **PASS** | 既有 `tests/test_restart_recovery.py` + `tests/backend/integration/test_treatment_plan_restart.py` 覆蓋重啟恢復場景。 |
| 10 | **PostgreSQL CI PASS 或配置已更新** | ✅ **PASS** | `.github/workflows/ci.yml` 已新增 Phase 3F-0 Transaction Atomicity 測試套件（`pytest tests/backend/repositories/test_base_repository_atomicity.py tests/backend/atomicity/`）。配置已更新，滿足檢查清單要求。 |
| 11 | **無大量無關 diff** | ✅ **PASS** | Production files = 14 tracked + 2 new = **16**，低於 20 上限。無 formatter/CRLF/import sorting 重寫大量無關檔案。 |

> **結果：11/11 全部 PASS 🟢**

---

## 4. 細項評分

| 項目 | 評分 (0-25) | 說明 |
|------|------------|------|
| **完整性** | **24 / 25** | R1~R11 全部滿足。R9 PostgreSQL CI 已更新配置但未實際在 PostgreSQL 上執行驗證（-1）。R12 為本評分本身，R13 Git Commit 為通過後續步驟。 |
| **正確性** | **25 / 25** | Repository 層所有 commit→flush 轉換正確；Service 層 try/commit/rollback 模式一致；API 層所有 commit/rollback 已移除；get_db() 安全網設計合理。無語法錯誤或邏輯缺陷。 |
| **可維護性** | **24 / 25** | 採用一致 try/commit/rollback 模式，Service 層統一事務邊界架構清晰。盤點文件詳盡（27 個 Repository 子類、16 處 commit 變更明細）。get_db() 全局 commit 作為安全網設計合理但可能與 Service 層重複，審慎扣 1 分。 |
| **測試與驗證** | **23 / 25** | 22 個原子性測試涵蓋 BaseRepository、Flow A、Flow B、Outbox、Success Path、Flush Chain 完整場景；320+ 回歸測試全部通過。PostgreSQL CI 配置已更新但未實際執行驗證（-2）。 |
| **小計** | **96 / 100** | — |

---

## 5. 總分計算

| 項目 | 分數 |
|------|------|
| 完整性 | 24 |
| 正確性 | 25 |
| 可維護性 | 24 |
| 測試與驗證 | 23 |
| **小計** | **96** |
| 流程遵守扣減 | 0（流程遵守 = YES，不扣減） |
| Reviewer Gate 扣減 | 0（11 項全部 PASS，不扣減） |
| **最終總分** | **96 / 100** |

---

## 6. 合格判定

| 項目 | 結果 |
|------|------|
| **總分 ≥ 95（Phase 3F-0 要求）** | ✅ 96 ≥ 95 |
| **Reviewer Gate 全 PASS** | ✅ 11/11 全 PASS |
| **Accepted** | **YES 🟢** |

---

## 7. 評分摘要與後續建議

### ✅ 本次評分通過理由

1. **流程遵守 = YES** 🟢：返工第 1 次已補充 Step 9 總結報告與 Step 6 需求回歸檢查（R1~R11 全部 PASS），流程步驟完整。
2. **Reviewer Gate 11 項全 PASS** 🟢：架構正確性、原子性、Rollback、Outbox、Commit Scope 等全部驗證通過。
3. **程式碼品質良好**：Repository 層 commit→flush 轉換徹底，Service 層事務邊界統一，測試覆蓋完整。
4. **測試驗證充分**：22 個原子性測試 + 320+ 回歸測試全部通過。

### 📋 評分後待辦事項（非評分條件，為建議順序）

| 優先級 | 項目 | 說明 |
|--------|------|------|
| **P0** | **Step 10：需求歸檔** | 將 `tasks/requirements.md` 中 Phase 3F-0 需求複製到 `tasks/requirements-history/requirements-Phase-3F-0.md` |
| **P0** | **Git Commit（T-28）** | Commit message: `fix(architecture): centralize transaction boundaries in services` |
| **P0** | **更新 agent_workflow.md** | 標記 Step 7（重評分）為 ✅，Step 10 為 ✅，更新循環/返工次數 |
| **P1** | **PostgreSQL CI 實際驗證** | 在 CI pipeline 或本機 PostgreSQL 環境執行 Transaction Atomicity 測試套件，確認全部通過 |
| **P2** | **更新 agent_workflow_History.md** | 記錄本次評分結果與後續執行歷程 |

### 遺留事項（非 Phase 3F-0 範圍）

以下位置仍有 `commit/rollback`，不屬本 Phase 範圍，預計後續 Phase 處理：
- `src/backend/auth/service.py`（3 處）
- `src/backend/clinical/decision_thread.py`（1 處）
- `src/backend/clinical_graph/worker.py`（2 處）
- `src/backend/database/crud.py`（8 處）
- `src/backend/knowledge/repository.py`（3 處）
- `src/backend/ranking/repository.py`（1 處）
- `src/backend/reasoning/repository.py`（2 處）
- `src/backend/reporting/repository.py`（2 處）
- **合計：22 處遺留**

---

*報告結束 — 由 REVIEWER 子代理於返工第 1 次評分產出。*
