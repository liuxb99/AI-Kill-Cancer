# REVIEW-PHASE3F0-R3 返工 — 總結報告

> **文件狀態**：✅ 已完成
> **產生日期**：2026-07-31
> **任務代號**：REVIEW-PHASE3F0-R3（Phase 3F-0 Transaction Boundary Hardening 返工）
> **場景**：hardening（架構強化）

---

## 1. 基本資訊

| 項目 | 內容 |
|------|------|
| **任務名稱** | REVIEW-PHASE3F0-R3 返工（處理 ChatGPT 透過 GitHub Connector 加入的 2 個 REVIEW 註解） |
| **來源** | `tasks/requirements.md` 附錄 B（B.1 P0-01 / B.2 P1-02 / B.3 完成條件） |
| **REVIEW 註解 commit** | `8b502fe`（P0-01）、`3e75eb0`（P1-02），已 git pull origin master 合併 |
| **工作分支** | `plan/phase4-phase5-master-plan` |
| **Commit SHA** | `7e76313`（R3 主修改）+ `084d45a`（測試修復） |
| **Push 狀態** | ✅ 已 Push 至 `origin/plan/phase4-phase5-master-plan`，pre-push hook（ECC）驗證通過 |
| **執行日期** | 2026-07-31 |
| **參與角色** | PLANNER, backend-logic, test-writer, fleet(6), REVIEWER, doc-writer |

---

## 2. 需求摘要

### 2.1 P0-01（阻斷性）：`get_db()` 自動 commit 造成雙 transaction owner

**問題**：`src/backend/database/session.py` 的 `get_db()` 在請求成功後自動 commit，但 Service 層也自行 commit/rollback，同一請求兩個 transaction owner。

**修改要求**：移除 get_db 自動 commit；所有直接注入 db 的寫入 endpoint 改由 Service 管理；不得以 dependency auto-commit 補救。

**驗證要求**（3 項）：Service 成功只 commit 一次；Service 後段失敗完整 rollback；endpoint 在 Service 返回後發生例外時不留下部分提交資料。

### 2.2 P1-02（重要）：`variants.py` 錯誤洩漏

**問題**：`import_variants` catch-all 直接 `detail=str(e)`，洩漏內部資訊且把 4xx 壓成 500。

**修改要求**：保留 HTTPException（4xx 透傳）；其餘只記錄 server log；對外回傳固定訊息 + error id。

**驗證要求**（2 項）：內部 DB 例外文字不出現在 response body；合法 4xx 不被轉 500。

---

## 3. 代碼變更明細

### 3.1 基礎改造（批次 0）

| 檔案 | 變更 |
|------|------|
| `src/backend/database/session.py` | `get_db()` 移除自動 commit；保留 except rollback（清理）+ finally close；REVIEW 註解改 REVIEW-RESOLVED |
| `src/backend/services/base.py`（新） | `run_in_transaction` + `BaseService` |

### 3.2 A 類 12 檔案 / 21 endpoint 改造（批次 1）

| API 檔案 | endpoint | 新增 Service |
|----------|----------|--------------|
| patients.py | 3 | PatientService |
| specimens.py | 1 | SpecimenService |
| sequencing.py | 1 | SequencingTestService |
| cases.py | 3（create 含 grant_owner 同交易） | CancerCaseService |
| case_acl.py | 2（403 保留） | CaseAccessService |
| analyses.py | 1（含 status=PENDING） | AnalysisRunService |
| uploads.py | 1 | UploadService |
| upload_vcf.py | 1（storage cleanup 保留） | VCFUploadService |
| research.py | 1 | ResearchPaperService |
| clinical.py | 4 | ClinicalPipelineService |
| reports.py | 1 | ReportService |
| ranking.py | 2 | DrugRankingService |

- 所有 A 類寫入 endpoint：`XxxService(db)` → Service 統一 commit/rollback → 4xx 透傳 → 固定訊息 + error_id

### 3.3 支援性 repo 改 flush-only

| 檔案 | 變更 |
|------|------|
| `clinical/decision_thread.py` | `create_node` 移除 commit（保留 flush + refresh） |
| `reporting/repository.py` | `create / update_status` 移除 commit |
| `ranking/repository.py` | `create` 移除 commit |
| `database/crud.py` | `create_research_paper` 移除 commit |

### 3.4 B 類 7 檔案確認

variants/evidence/clinical_graph/treatment_plans/recommendation/clinical_decision/tumor_board_consensus — 移除 auto-commit 後 Service 為唯一 owner，無需改寫入邏輯。

### 3.5 P1-02 本體

| 檔案 | 變更 |
|------|------|
| `api/v1/variants.py` | `except HTTPException: raise`；其餘 error_id + logger.exception + 固定訊息；REVIEW 註解 REVIEW-RESOLVED |

---

## 4. 測試與驗證結果

### 4.1 新增驗證測試（紅燈先行）

| 測試檔案 | 數量 | 覆蓋驗證 |
|----------|------|----------|
| test_phase3f0_r3_p0_transaction_boundary.py | 5 | commit 一次 / 後段失敗 rollback / endpoint 例外不留資料 |
| test_phase3f0_r3_p1_variants_errors.py | 2 | DB 例外不洩漏 + error_id / 4xx 不轉 500 |

### 4.2 紅燈 → 綠燈

| 階段 | 結果 |
|------|------|
| 紅燈先行 | 4 FAILED / 3 PASSED（問題存在證據） |
| 綠燈驗證 | 7 passed ✅ |

### 4.3 既有測試同步調整

- `tests/unit/test_decision_thread.py`：7 處 flush-only 適配 → 36 passed
- 修復預先存在失敗（git stash 驗證與本次修改無關）：FakeDB 補 flush + migration db 清理 → 89 passed

### 4.4 完整回歸

| 套件 | 結果 |
|------|------|
| 全量測試（sqlite） | **1685 passed / 23 skipped / 0 failed** ✅ |
| atomicity 目錄 | **18 passed** ✅ |

---

## 5. 流程記錄

```
Step 0   git pull origin master 合併 REVIEW commit；報到 ✅
Step 1   需求記錄至 requirements.md 附錄 B ✅
Step 2   場景識別 hardening ✅
Step 3   PLANNER 產出 plan-Phase-3F0-R3.md（4 批次、28 檔案）✅
Step 4   Workflow 更新 ✅
Step 5   紅燈 4 FAILED/3 PASSED → 批次 0-2 → 綠燈 7 passed → 全量 1685 passed ✅
Step 6   需求回歸檢查：B.1 6/6、B.2 4/4、B.3 2/2 全部 PASS ✅
Step 7   REVIEWER：完整性25 正確性25 可維護性23 測試驗證25 | 總分 98/100 合格 ✅
Commit   7e76313 + 084d45a → Push origin/plan/phase4-phase5-master-plan ✅
```

---

## 6. REVIEW 註解處理狀態

| 註解 | 位置 | 狀態 |
|------|------|------|
| REVIEW-PHASE3F0-R3-P0-01 | session.py L13-26 | ✅ REVIEW-RESOLVED（原文字保留 + RESOLUTION） |
| REVIEW-PHASE3F0-R3-P1-02 | variants.py L73-82 | ✅ REVIEW-RESOLVED（原文字保留 + RESOLUTION） |

---

## 7. 後續事項（已知技術債）

| # | 項目 | 狀態 |
|---|------|------|
| 1 | `reasoning/repository.py` 仍自行 commit | ⚠️ 不在本輪範圍，列為 Phase 4 前置 |
| 2 | `knowledge/repository.py` 仍自行 commit | ⚠️ 不在本輪範圍，同上 |
| 3 | ranking.py 請求內雙 transaction（各自主動 commit） | 非雙 owner 衝突，維持現狀 |
| 4 | crud.py 其餘未被 production 使用的 CRUD commit | 既有遺留 |

---

## 結論

**REVIEW-PHASE3F0-R3 返工完成**：P0-01 消除雙 transaction owner、P1-02 消除 str(e) 洩漏。7 項驗證測試紅燈先行 → 綠燈全過；全量 1685 passed / 0 failed；Step 6 全 PASS、Step 7 REVIEWER 98/100；REVIEW 註解 REVIEW-RESOLVED；已 Commit + Push。✅
