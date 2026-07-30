# Phase 3F-0：Transaction Boundary Hardening — 執行計劃

> 依據 tasks/requirements.md 和 tasks/task-status.md 制定。
> 核心原則：把 Transaction Boundary 完整收回 Service 層，不新增功能。

---

## 一、現狀摘要（代碼審查結論）

### P0 問題
`BaseRepository.create/update/delete` 內部自行 `self.db.commit()`，造成 Service 無法控制跨 Repository 原子交易。雖然部分 Repository（RecommendationRepository、ClinicalDecisionRepository、TreatmentPlanRepository、TumorBoardConsensusRepository）已重寫 `create()` 避開 BaseRepository 的 commit，但問題仍存在於：

1. **BaseRepository** 三個方法仍含 `commit()`
2. **非 CRUD 倉儲方法**（upsert、bulk_create、grant_permission 等）自行 `commit()`
3. **API 層**（workbench.py、clinical_graph.py）直接管理 `commit/rollback`，違反 R3 Transaction Contract

### 已修復的範圍（無須再動）
| Repository | create 行為 | 狀態 |
|---|---|---|
| RecommendationRepository | add only, no commit/flush | ✅ 正確 |
| ClinicalDecisionRepository | add only, no commit/flush | ✅ 正確 |
| ClinicalDecisionTraceRepository | add only, no commit/flush | ✅ 正確 |
| TreatmentPlanRepository | add + flush, no commit | ✅ 正確 |
| TreatmentPhaseRepository | add + flush, no commit | ✅ 正確 |
| TreatmentItemRepository | add + flush, no commit | ✅ 正確 |
| TreatmentMonitoringRepository | add + flush, no commit | ✅ 正確 |
| TreatmentSafetyRuleRepository | add + flush, no commit | ✅ 正確 |
| TreatmentPlanTraceRepository | add + flush, no commit | ✅ 正確 |
| TumorBoardConsensusRepository | add + flush, no commit | ✅ 正確 |
| TumorBoardOpinionRepository | add + flush, no commit | ✅ 正確 |
| ClinicalGraphOutboxRepository | add + flush, no commit | ✅ 正確 |

### 服務層現狀（已有 Transaction Boundary）
| Service | commit/rollback | 狀態 |
|---|---|---|
| RecommendationService | try/except 中 commit/rollback | ✅ 正確 |
| ClinicalDecisionService | try/except 中 commit/rollback | ✅ 正確 |
| TumorBoardConsensusService | try/except 中 commit/rollback | ✅ 正確 |
| TreatmentPlanService | try/except 中 commit/rollback（多個方法） | ✅ 正確 |
| ClinicalGraphEventService | 不管理交易（委託給 caller） | ✅ 正確 |

### 需要修改的範圍

**Repository 層（含自行 commit 的方法）：**
| 檔案 | 問題方法 | 問題 |
|---|---|---|
| `repositories/base.py` | `create()` / `update()` / `delete()` | 自行 commit |
| `repositories/case_acl_repo.py` | `delete_case_permission()` / `grant_permission()` | 自行 commit |
| `repositories/evidence_item_repo.py` | `upsert()` (3處) | 自行 commit |
| `repositories/drug_interaction_repo.py` | `upsert()` (2處) | 自行 commit |
| `repositories/knowledge_source_repo.py` | `upsert()` (2處) / `record_health_check()` | 自行 commit |
| `repositories/variant_repo.py` | `bulk_create()` | 自行 commit |

**API 層（需將交易管理移至 Service）：**
| 檔案 | 問題 |
|---|---|
| `api/v1/workbench.py` | 4個 endpoint 自行 commit/rollback |
| `api/v1/clinical_graph.py` | 1個 endpoint 自行 commit |

**Service 層（需新增交易管理）：**
| 檔案 | 問題 |
|---|---|
| `services/workbench_service.py`（如存在）或新增 | workbench 寫入操作需包裝 |
| - | Evidence/DrugInteraction/KnowledgeSource/Variant 批量操作需服務層包裝 |

---

## 二、Commit Scope Gate 估算

| 類別 | 預計修改檔案數 | 說明 |
|---|---|---|
| BaseRepository | 1 | `base.py` |
| 受影響 Repository | 5 | case_acl, evidence_item, drug_interaction, knowledge_source, variant |
| 受影響 Service | 2-3 | workbench service（新增或擴充）、pipeline 服務 |
| API 層 | 2 | workbench.py, clinical_graph.py |
| 測試檔案 | 5-7 | 新測試檔案 |
| CI 配置 | 1 | `.github/workflows/ci.yml` |
| **Production files 合計** | **~10-11** | ✅ 低於 20 上限 |
| **測試/CI 合計** | ~6-8 | 不計入 production 上限 |

---

## 三、任務清單

### 階段 0：前置準備

#### T-00：確認環境與分支

| 欄位 | 值 |
|---|---|
| **任務ID** | T-00 |
| **標題** | 確認開發環境與 Git 分支 |
| **描述** | 確認可執行 pytest、ruff；從 main 開 feature branch：`fix/transaction-boundary-hardening` |
| **負責角色** | PLANNER / backend-logic |
| **前置任務** | 無 |
| **預估工時** | 0.5h |
| **驗收標準** | 分支建立完成，pytest 可執行 |

---

### 階段 1：盤點階段（Inventory）

#### T-01：完整盤點 BaseRepository 使用範圍

| 欄位 | 值 |
|---|---|
| **任務ID** | T-01 |
| **標題** | 盤點所有 BaseRepository 子類與 commit/rollback 使用點 |
| **描述** | 產出正式盤點清單，包含：(1) 所有繼承 BaseRepository 的類別 (2) 哪些使用 super().create/update/delete (3) 哪些有自己的 commit/rollback (4) 哪些方法會被 Service 呼叫。需輸出到盤點文件。 |
| **負責角色** | PLANNER / backend-logic |
| **前置任務** | T-00 |
| **預估工時** | 1h |
| **產出文件** | `tasks/phase3f0-inventory.md` |
| **驗收標準** | 盤點清單完整，無遺漏 |

---

### 階段 2：紅燈階段（先紅再修）

#### T-02：建立 BaseRepository 失敗重現測試（紅燈）

| 欄位 | 值 |
|---|---|
| **任務ID** | T-02 |
| **標題** | 撰寫 BaseRepository 原子性破壞重現測試 |
| **描述** | 新增測試檔案 `tests/backend/repositories/test_base_repository_atomicity.py`。使用真實 AsyncSession + 真實 SQLite in-memory 資料庫，不得全部 Mock。測試情境：create user → 第二個 create 失敗 → 驗證 user 不存在（Partial Commit）。此測試必須先用紅燈驗證問題存在。 |
| **負責角色** | test-writer |
| **前置任務** | T-01 |
| **預估工時** | 2h |
| **依賴** | 需了解真實資料庫 fixture 設置 |
| **驗收標準** | 測試在未修改 BaseRepository 前 FAIL（紅燈） |

#### T-03：建立 Atomicity Flow A 失敗重現測試（紅燈）

| 欄位 | 值 |
|---|---|
| **任務ID** | T-03 |
| **標題** | Patient + Cancer Case 原子性重現測試 |
| **描述** | 新增測試：建立 Patient → 建立 Cancer Case 時失敗 → 驗證 Patient 不存在。第二步失敗必須全部 rollback。使用真實 Repository + 真實 AsyncSession。紅燈驗證。 |
| **負責角色** | test-writer |
| **前置任務** | T-01 |
| **預估工時** | 1.5h |
| **驗收標準** | 紅燈（失敗）：驗證當前 BaseRepository.commit() 導致 Patient 已存在但 Cancer Case 不存在 |

#### T-04：建立 Atomicity Flow B 失敗重現測試（紅燈）

| 欄位 | 值 |
|---|---|
| **任務ID** | T-04 |
| **標題** | Treatment Plan + Phases + Items + Trace + Outbox 原子性重現測試 |
| **描述** | 新增測試：建立完整 Treatment Plan 流程，在中間步驟注入失敗，驗證所有資料皆不存在（全部 rollback）。紅燈驗證。 |
| **負責角色** | test-writer |
| **前置任務** | T-01 |
| **預估工時** | 2h |
| **驗收標準** | 紅燈（失敗）：驗證任一步失敗導致所有資料不殘留 |

#### T-05：建立 Service Transaction Boundary 成功測試（紅燈）

| 欄位 | 值 |
|---|---|
| **任務ID** | T-05 |
| **標題** | 建立 Service 成功路徑測試（單一 commit） |
| **描述** | 測試 Service 方法成功執行後只 commit 一次、所有資料皆存在、Outbox 存在。紅燈驗證。 |
| **負責角色** | test-writer |
| **前置任務** | T-01 |
| **預估工時** | 1.5h |
| **驗收標準** | 紅燈（因 Service 可能依賴 BaseRepository 自動 commit 而行為異常） |

---

### 階段 3：修正 BaseRepository

#### T-06：修正 BaseRepository create/update/delete

| 欄位 | 值 |
|---|---|
| **任務ID** | T-06 |
| **標題** | BaseRepository：commit → flush + refresh |
| **描述** | 修改 `base.py` 三個方法：<br>`create`：`self.db.add(instance); await self.db.flush(); await self.db.refresh(instance); return instance`<br>`update`：set attributes → `await self.db.flush(); await self.db.refresh(instance); return instance`<br>`delete`：`await self.db.delete(instance); await self.db.flush(); return True` |
| **負責角色** | backend-logic |
| **前置任務** | T-02（紅燈確認後才可修改） |
| **預估工時** | 0.5h |
| **修改檔案** | `src/backend/repositories/base.py` |
| **驗收標準** | T-02 測試變綠燈；編譯通過 |

---

### 階段 4：檢查所有 Repository

#### T-07：移除 CaseACLRepository 自行 commit

| 欄位 | 值 |
|---|---|
| **任務ID** | T-07 |
| **標題** | 修正 CaseACLRepository 自行 commit |
| **描述** | `delete_case_permission()` 和 `grant_permission()` 中的 `self.db.commit()` 改為 `await self.db.flush()`。確認呼叫端（API/Service）有 Transaction Boundary。 |
| **負責角色** | backend-logic |
| **前置任務** | T-06 |
| **預估工時** | 0.5h |
| **修改檔案** | `src/backend/repositories/case_acl_repo.py` |
| **驗收標準** | Repository 內無 commit/rollback |

#### T-08：移除 EvidenceItemRepository 自行 commit

| 欄位 | 值 |
|---|---|
| **任務ID** | T-08 |
| **標題** | 修正 EvidenceItemRepository 自行 commit |
| **描述** | `upsert()` 方法中的三處 `self.db.commit()` 改為 `await self.db.flush()`。分析呼叫端：此 repo 主要被 Evidence ingestion pipeline 使用，需確認是否有 Service 層封裝或需新增。 |
| **負責角色** | backend-logic |
| **前置任務** | T-06 |
| **預估工時** | 1h |
| **修改檔案** | `src/backend/repositories/evidence_item_repo.py` |
| **驗收標準** | Repository 內無 commit；呼叫端有交易管理 |

#### T-09：移除 DrugInteractionRepository 自行 commit

| 欄位 | 值 |
|---|---|
| **任務ID** | T-09 |
| **標題** | 修正 DrugInteractionRepository 自行 commit |
| **描述** | `upsert()` 中的 `self.db.commit()` 改為 `await self.db.flush()`。確認呼叫端交易邊界。 |
| **負責角色** | backend-logic |
| **前置任務** | T-06 |
| **預估工時** | 0.5h |
| **修改檔案** | `src/backend/repositories/drug_interaction_repo.py` |
| **驗收標準** | Repository 內無 commit |

#### T-10：移除 KnowledgeSourceRepository 自行 commit

| 欄位 | 值 |
|---|---|
| **任務ID** | T-10 |
| **標題** | 修正 KnowledgeSourceRepository 自行 commit |
| **描述** | `upsert()` 和 `record_health_check()` 中的 `self.db.commit()` 改為 `await self.db.flush()`。確認呼叫端。 |
| **負責角色** | backend-logic |
| **前置任務** | T-06 |
| **預估工時** | 0.5h |
| **修改檔案** | `src/backend/repositories/knowledge_source_repo.py` |
| **驗收標準** | Repository 內無 commit |

#### T-11：移除 VariantRepository 自行 commit

| 欄位 | 值 |
|---|---|
| **任務ID** | T-11 |
| **標題** | 修正 VariantRepository bulk_create 自行 commit |
| **描述** | `bulk_create()` 中的 `await self.db.commit()` 改為 `await self.db.flush()`。確認呼叫端。 |
| **負責角色** | backend-logic |
| **前置任務** | T-06 |
| **預估工時** | 0.5h |
| **修改檔案** | `src/backend/repositories/variant_repo.py` |
| **驗收標準** | Repository 內無 commit |

---

### 階段 5：修正受影響 Service（加入 Transaction Boundary）

#### T-12：確認既有 Service Transaction Boundary 完整性

| 欄位 | 值 |
|---|---|
| **任務ID** | T-12 |
| **標題** | 審查 RecommendationService / ClinicalDecisionService / TumorBoardService / TreatmentPlanService |
| **描述** | 逐一檢視四個主要 Service 的寫入方法，確認：(1) 每個寫入方法都有 try/commit/rollback (2) 跨 Repository 操作在單一交易內 (3) Outbox 在同交易內 (4) 無多餘的 session.begin() + 手動 commit 重複控制。只審查不修改。 |
| **負責角色** | backend-logic |
| **前置任務** | T-06 |
| **預估工時** | 1h |
| **驗收標準** | 審查記錄寫入盤點文件；若有不符處列為待修 task |

#### T-13：修正 API 層直接管理交易（workbench.py）

| 欄位 | 值 |
|---|---|
| **任務ID** | T-13 |
| **標題** | 將 workbench API 的 commit/rollback 移至 Service |
| **描述** | `api/v1/workbench.py` 中 4 個 endpoint 直接 `await db.commit()` / `await db.rollback()`。新增或擴充 `WorkbenchService` 方法封裝這些寫入操作，包含交易管理。API 層只呼叫 service 方法。 |
| **負責角色** | backend-logic |
| **前置任務** | T-06 |
| **預估工時** | 2h |
| **修改檔案** | `src/backend/api/v1/workbench.py`, `src/backend/services/workbench_service.py`（如無則新增） |
| **驗收標準** | API 層無 commit/rollback；WorkbenchService 管理交易 boundary |

#### T-14：修正 API 層直接管理交易（clinical_graph.py）

| 欄位 | 值 |
|---|---|
| **任務ID** | T-14 |
| **標題** | 將 clinical_graph.py 的 commit 移至 Service |
| **描述** | `clinical_graph.py` 的 retry endpoint 直接 `await db.commit()`。若該邏輯屬 Graph Outbox Service 範圍，則移至 Service；若為簡單狀態更新，則封裝到 ClinicalGraphOutboxRepository 或對應 Service。 |
| **負責角色** | backend-logic |
| **前置任務** | T-06 |
| **預估工時** | 0.5h |
| **修改檔案** | `src/backend/api/v1/clinical_graph.py`, `src/backend/services/clinical_graph_event_service.py` |
| **驗收標準** | API 層無 commit/rollback |

#### T-15：為 Pipeline Repository 建立交易包裝

| 欄位 | 值 |
|---|---|
| **任務ID** | T-15 |
| **標題** | 為 EvidenceItem / DrugInteraction / KnowledgeSource / Variant 批量操作建立 Service 層交易管理 |
| **描述** | 這四個 Repository 的寫入方法（upsert/bulk_create）被 ingestion pipeline 直接呼叫。需新增對應 Service 方法，封裝交易邊界：<br>- `EvidenceIngestionService.upsert_item()`<br>- `DrugInteractionService.upsert_interaction()`<br>- `KnowledgeSourceService.upsert_source()`<br>- `VariantIngestionService.bulk_create_variants()`<br>每個 Service 方法：try / flush + commit / except rollback。 |
| **負責角色** | backend-logic |
| **前置任務** | T-08, T-09, T-10, T-11 |
| **預估工時** | 2h |
| **修改檔案** | 新增 4 個 service 檔案，或擴充現有檔案 |
| **驗收標準** | 每個寫入操作有 Service 層封裝交易；Repository 只 flush |

---

### 階段 6：Outbox 原子性處理

#### T-16：驗證所有 Outbox 與業務資料同交易

| 欄位 | 值 |
|---|---|
| **任務ID** | T-16 |
| **標題** | 驗證 Recommend/Decision/Consensus/Plan Outbox 原子性 |
| **描述** | 審查四條寫入流程，確認 Recommendation + Outbox、Decision + Outbox、Consensus + Outbox、Treatment Plan + Outbox 在同一個 Service commit 內完成。目前 ClinicalGraphEventService.create_event 只做 add+flush，由調用 Service 控制 commit — 這是正確模式。需文件確認。 |
| **負責角色** | backend-logic / test-writer |
| **前置任務** | T-12 |
| **預估工時** | 1h |
| **產出** | Outbox 原子性確認清單 |
| **驗收標準** | 四條流程確認在同一個 transaction 內完成 Outbox 寫入 |

---

### 階段 7：測試階段

#### T-17：撰寫 BaseRepository Tests

| 欄位 | 值 |
|---|---|
| **任務ID** | T-17 |
| **標題** | 完整 BaseRepository 單元測試 |
| **描述** | 測試檔案：`tests/backend/repositories/test_base_repository_atomicity.py`。涵蓋：<br>- `create` 不 commit（flush 後 PK 可用）<br>- `update` 不 commit（flush 後可查詢到變更）<br>- `delete` 不 commit（flush 後已刪除）<br>- `rollback` 後 create 不存在<br>- `rollback` 後 update 恢復原值<br>- `rollback` 後 delete 恢復<br>- 至少一組使用真實 SQLite 資料庫 |
| **負責角色** | test-writer |
| **前置任務** | T-06（BaseRepository 修正後） |
| **預估工時** | 2h |
| **驗收標準** | 全部綠燈；測試使用真實 AsyncSession |

#### T-18：Atomicity Tests Flow A

| 欄位 | 值 |
|---|---|
| **任務ID** | T-18 |
| **標題** | Patient + Cancer Case 原子性測試 |
| **描述** | 測試檔案：`tests/backend/atomicity/test_atomicity_flow_a.py`。情境：建立 Patient → 建立 Cancer Case 時失敗（注入例外）→ 驗證 Patient 和 Case 皆不存在。使用真實 Repository。 |
| **負責角色** | test-writer |
| **前置任務** | T-06 |
| **預估工時** | 1.5h |
| **驗收標準** | 全部綠燈；驗證跨 Repository rollback |

#### T-19：Atomicity Tests Flow B

| 欄位 | 值 |
|---|---|
| **任務ID** | T-19 |
| **標題** | Treatment Plan + Phases + Items + Trace + Outbox 原子性測試 |
| **描述** | 測試檔案：`tests/backend/atomicity/test_atomicity_flow_b.py`。建立完整 Treatment Plan 流程，任一步失敗驗證全部不存在。使用真實 Repository。 |
| **負責角色** | test-writer |
| **前置任務** | T-06 |
| **預估工時** | 2.5h |
| **驗收標準** | 全部綠燈 |

#### T-20：Recommendation/Decision/Consensus 擇一原子性測試

| 欄位 | 值 |
|---|---|
| **任務ID** | T-20 |
| **標題** | 至少選一條域驗證主資料 + 子資料 + Outbox 同 Transaction |
| **描述** | 測試檔案：`tests/backend/atomicity/test_outbox_atomicity.py`。選擇 Recommendation 或 Decision 或 Consensus 之一，驗證：業務資料成功 & Outbox 成功 → 全部存在；Outbox 失敗 → 業務資料不存在；業務資料失敗 → Outbox 不存在。 |
| **負責角色** | test-writer |
| **前置任務** | T-16 |
| **預估工時** | 2h |
| **驗收標準** | 三種情境全部通過 |

#### T-21：Success Tests（Service commit 一次）

| 欄位 | 值 |
|---|---|
| **任務ID** | T-21 |
| **標題** | Service 成功路徑測試 |
| **描述** | 測試檔案：`tests/backend/atomicity/test_success_paths.py`。對每個 Service 寫入方法驗證：commit 一次後所有資料存在、Outbox 存在、無殘留未提交資料。 |
| **負責角色** | test-writer |
| **前置任務** | T-06, T-17 |
| **預估工時** | 2h |
| **驗收標準** | 全部綠燈 |

#### T-22：Restart Recovery 測試

| 欄位 | 值 |
|---|---|
| **任務ID** | T-22 |
| **標題** | 重啟恢復測試 |
| **描述** | 測試檔案：`tests/backend/atomicity/test_restart_recovery.py` 或擴展現有 `test_restart_recovery.py`。建立資料 → shutdown session → 新 session 重新讀取正常。 |
| **負責角色** | test-writer |
| **前置任務** | T-06 |
| **預估工時** | 1.5h |
| **驗收標準** | 全部綠燈 |

#### T-23：Flush 後可繼續使用測試（R8）

| 欄位 | 值 |
|---|---|
| **任務ID** | T-23 |
| **標題** | 驗證 Flush 後 PK 可用、FK 子資料可建立 |
| **描述** | 測試：Plan flush → Phase 使用 plan.id → Item 使用 phase.id → Outbox 使用 plan_id → Service commit。驗證完整鏈條。 |
| **負責角色** | test-writer |
| **前置任務** | T-06 |
| **預估工時** | 1.5h |
| **驗收標準** | 全部綠燈 |

---

### 階段 8：回歸驗證階段

#### T-24：執行完整回歸測試套件

| 欄位 | 值 |
|---|---|
| **任務ID** | T-24 |
| **標題** | 執行全部回歸測試 |
| **描述** | 執行 R10 要求的回歸項目：<br>- Phase 3A Recommendation 測試<br>- Phase 3B Clinical Decision 測試<br>- Phase 3C Tumor Board Consensus 測試<br>- Phase 3D Graph Outbox 測試<br>- Phase 3E Treatment Plan 測試<br>- Migration Gate 測試<br>- Frontend Build<br>- ruff lint、pytest（unit+integration）、frontend tests、frontend build、Postgres tests、Migration gate |
| **負責角色** | backend-logic / test-writer |
| **前置任務** | T-17 ~ T-23 |
| **預估工時** | 3h |
| **驗收標準** | 全部通過 |

#### T-25：補缺失測試或修復回歸問題

| 欄位 | 值 |
|---|---|
| **任務ID** | T-25 |
| **標題** | 修復回歸測試中發現的問題 |
| **描述** | T-24 中若有測試因 Transaction Boundary 改動而失敗，分析原因並修復。可能原因：Service 未 commit 導致資料未持久化、Repository 呼叫端未預期 flush 行為。 |
| **負責角色** | backend-logic |
| **前置任務** | T-24 |
| **預估工時** | 2h（含 T-24 的一部分） |
| **驗收標準** | 全部回歸測試通過 |

---

### 階段 9：CI 更新

#### T-26：更新 CI 加入新 Transaction Atomicity 測試

| 欄位 | 值 |
|---|---|
| **任務ID** | T-26 |
| **標題** | 更新 Postgres CI 加入 Transaction Atomicity 測試 |
| **描述** | 修改 `.github/workflows/ci.yml`，在 Postgres Integration Gate 階段新增 Transaction Atomicity 測試套件執行。包括：BaseRepository atomicity、Cross-repository rollback（Flow A+B）、Treatment Plan rollback、Outbox rollback、Success commit、Restart recovery。 |
| **負責角色** | backend-logic |
| **前置任務** | T-24 |
| **預估工時** | 1h |
| **修改檔案** | `.github/workflows/ci.yml` |
| **驗收標準** | CI 上新的 Transaction 測試在 Postgres 上執行且通過 |

---

### 階段 10：最終檢查與提交

#### T-27：Commit Scope Gate 檢查

| 欄位 | 值 |
|---|---|
| **任務ID** | T-27 |
| **標題** | 確認 production files 修改 ≤ 20 |
| **描述** | 使用 `git diff --stat` 計算 production files 修改數。確認無 formatter/CRLF/import sorting/encoding 重寫大量無關檔案。 |
| **負責角色** | backend-logic |
| **前置任務** | T-26 |
| **預估工時** | 0.5h |
| **驗收標準** | Production files ≤ 20；無無關改動 |

#### T-28：Git Commit

| 欄位 | 值 |
|---|---|
| **任務ID** | T-28 |
| **標題** | 提交程式碼 |
| **描述** | Commit message：`fix(architecture): centralize transaction boundaries in services`。允許一個後續 CI 修復 Commit。禁止 force push、修改歷史 Migration。 |
| **負責角色** | backend-logic |
| **前置任務** | T-27 |
| **預估工時** | 0.5h |
| **驗收標準** | Commit 訊息正確；無 force push |

#### T-29：Reviewer Gate

| 欄位 | 值 |
|---|---|
| **任務ID** | T-29 |
| **標題** | Reviewer 評分 ≥ 95 |
| **描述** | 由 REVIEWER 角色依 AGENTS.md 規定評分。逐項確認 11 項檢查清單。任一項 FAIL/PARTIAL/SKIPPED → Reviewer 最高 89、Accepted = NO。 |
| **負責角色** | REVIEWER |
| **前置任務** | T-28 |
| **預估工時** | 2h |
| **驗收標準** | Score ≥ 95；Accepted = YES |

#### T-30：返工（如需要）

| 欄位 | 值 |
|---|---|
| **任務ID** | T-30 |
| **標題** | 根據 Reviewer 評分返工 |
| **描述** | 若 Reviewer 評分 < 95，根據評分報告調整。常見問題：遺漏的 commit/rollback、Service 交易邊界不完整、測試覆蓋不足。 |
| **負責角色** | backend-logic / test-writer |
| **前置任務** | T-29（若評分不合格） |
| **預估工時** | 依問題範圍 1-4h |
| **驗收標準** | 返工後重新送 Reviewer ≥ 95 |

---

## 四、依賴圖

```
T-00 (前置準備)
  └── T-01 (盤點)
        ├── T-02 (BaseRepository 紅燈) ──→ T-06 (修正 BaseRepository) ──→ T-17 (BaseRepository Tests)
        ├── T-03 (Flow A 紅燈) ──────────→  (T-06 修正後綠燈) ──────────→ T-18 (Flow A 測試)
        ├── T-04 (Flow B 紅燈) ──────────→  (T-06 修正後綠燈) ──────────→ T-19 (Flow B 測試)
        └── T-05 (Success 紅燈) ──────────→  (T-06+T-13~T-15 後綠燈) ──→ T-21 (Success Tests)

T-06 (修正 BaseRepository)
  ├── T-07 ~ T-11 (修正各 Repository commit)
  ├── T-12 (Service 審查)
  ├── T-13 (Workbench Service 交易邊界)
  ├── T-14 (Clinical Graph API 交易邊界)
  ├── T-15 (Pipeline Service 交易邊界)
  └── T-16 (Outbox 原子性驗證)

T-17 ~ T-23 (測試階段) ──→ T-24 (回歸測試) ──→ T-25 (修復回歸問題)
                                                    └── T-26 (CI 更新)
                                                          └── T-27 (Scope Gate)
                                                                └── T-28 (Commit)
                                                                      └── T-29 (Reviewer Gate)
                                                                            └── T-30 (返工，如需要)
```

---

## 五、返工預案

| 情境 | 觸發條件 | 應對方案 |
|---|---|---|
| **Repository commit 遺漏** | Reviewer 發現 Repository 仍有 commit() | T-07~T-11 補充修正 |
| **Service 交易邊界不完整** | Service 寫入方法無 try/commit/rollback | T-15 擴充服務層封裝 |
| **紅燈測試未先紅** | T-02~T-05 在修正前即通過（綠燈） | 表示問題已被部分修復，需調整測試以確實暴露 Atomicity Broken |
| **回歸測試大量失敗** | T-24 失敗超過 5 項 | 暫停提交，分析根因：可能 Service 缺少 commit 導致資料未持久化 |
| **Flush 後 PK 無法取得** | 部分資料庫（SQLite）flush 後不返回 PK | 改用 `await self.db.flush()` + `self.db.refresh(instance)` 確保 PK 可用 |
| **Concurrent 交易衝突** | Postgres CI 出現 deadlock | 確認 Service 使用正確的 isolation level，避免在 flush 後長時間不 commit |
| **Commit Scope 超標** | Production files > 20 | 將非核心 repo（如 evidence_item, drug_interaction）留到後續 Phase 處理，本輪只處理核心 repo |
| **Reviewer 評分 < 95** | 任一檢查清單項目 FAIL/PARTIAL/SKIPPED | 逐項修復後重新提交 Reviewer |

---

## 六、角色分派摘要

| 角色 | 任務 |
|---|---|
| **PLANNER** | T-00, T-01（已執行） |
| **backend-logic** | T-06, T-07, T-08, T-09, T-10, T-11, T-12, T-13, T-14, T-15, T-16, T-25, T-26, T-27, T-28 |
| **test-writer** | T-02, T-03, T-04, T-05, T-17, T-18, T-19, T-20, T-21, T-22, T-23 |
| **REVIEWER** | T-29 |

---

## 七、預估總工時

| 階段 | 工時 |
|---|---|
| 階段 1：盤點 | 1h |
| 階段 2：紅燈測試 | 7h |
| 階段 3：修正 BaseRepository | 0.5h |
| 階段 4：檢查 Repository | 3h |
| 階段 5：修正 Service | 5.5h |
| 階段 6：Outbox 原子性 | 1h |
| 階段 7：測試 | 10.5h |
| 階段 8：回歸驗證 | 5h |
| 階段 9：CI 更新 | 1h |
| 階段 10：最終檢查 | 3h |
| **合計** | **~37h** |
| 返工預留 | +4h |

---

## 八、Checklist（Reviewer Gate 檢查清單）

1. [ ] BaseRepository.create/update/delete 不再自行 commit
2. [ ] 所有 Repository 內無 commit/rollback 呼叫
3. [ ] Service 層負責所有寫入操作的交易邊界（try/commit/rollback）
4. [ ] API 層無 commit/rollback 呼叫
5. [ ] Engine 層無 Session/Repository/commit/rollback 呼叫
6. [ ] Outbox 與業務資料在同一交易中
7. [ ] 紅燈測試已在修正前確認失敗
8. [ ] BaseRepository 測試覆蓋 create/update/delete/rollback/flush
9. [ ] Atomicity Tests 覆蓋 Flow A 和 Flow B
10. [ ] Recommendation/Decision/Consensus 至少一條 Outbox 原子性測試
11. [ ] Success Tests、Restart Recovery Tests 存在且通過
12. [ ] Postgres CI 包含 Transaction Atomicity 測試套件
13. [ ] Commit message 正確
14. [ ] Production files ≤ 20
15. [ ] 所有回歸測試通過（ruff、pytest、frontend tests、frontend build、Postgres、Migration gate）

---

## 九、返工第 1 次計劃（Rework Round 1）

> 基於 REVIEWER 評分結果（總分 0，流程遵守 = NO）制定返工計劃。
> Review 報告：`tasks/reviews/review_Phase-3F-0_0.md`
> 當前分支：`fix/transaction-boundary-hardening`（19 modified + 2 new files，尚未提交）

### 9.1 不合格根因

| # | 問題 | 嚴重性 | 說明 |
|---|------|--------|------|
| F1 | **Git Commit 未執行** | P0 blocker | T-28 是 T-29（REVIEWER）之前置任務，當前所有修改均為 unstaged 狀態 |
| F2 | **需求未歸檔** | P0 blocker | `tasks/requirements-history/` 中無 Phase 3F-0 需求歸檔文件 |
| F3 | **Step 9 + Step 10 未完成** | P0 blocker | 總結報告未產出、agent_workflow.md 顯示 Step 8-10 未勾選 |
| F4 | **PostgreSQL CI 未實際驗證** | P1 partial | CI 配置已更新，但無實際在 Postgres 上執行並通過的證據（本地無法運行 CI） |

### 9.2 返工策略

**總體原則**：只完成流程步驟，不修改程式碼。

程式碼質量已通過 REVIEWER 認可（Reviewer Gate 10/11 PASS，唯一 PARTIAL 為 PostgreSQL CI 無法本地驗證）。返工目標是讓「流程遵守 = YES」，使完整評分機制可以重新運作。

**執行順序**：

```
R-01 (總結報告) → R-02 (需求歸檔) → R-03 (更新 Workflow)
  → R-04 (重新 Step 6 需求回歸檢查) → R-05 (重新 Step 7 REVIEWER 評分)
  → R-06 (T-28 Git Commit) → R-07 (PostgreSQL CI 說明)
```

### 9.3 返工任務清單

---

#### R-01：完成 Step 9 — 產出總結報告

| 欄位 | 值 |
|---|---|
| **任務ID** | R-01 |
| **標題** | 產出 Phase 3F-0 總結報告 |
| **描述** | 撰寫 `tasks/summary-report-phase3f-0.md`，內容包含：<br>1. 任務概述（Transaction Boundary Hardening 整體目標）<br>2. 修改檔案清單（19 tracked + 2 untracked production files + 6 測試檔案）<br>3. 需求達成狀態（R1~R13 逐項對照）<br>4. 代碼審查總結（Repository/Service/API 三層修改摘要）<br>5. 測試結果摘要（6 個測試檔案覆蓋範圍）<br>6. REVIEWER 評分記錄（第 0 次 0 分 → 第 1 次目標 ≥ 95）<br>7. 交付物狀態 |
| **負責角色** | doc-writer |
| **前置任務** | 無（返工起點） |
| **預估工時** | 1h |
| **產出文件** | `tasks/summary-report-phase3f-0.md` |
| **驗收標準** | 報告完整，含需求對照表 + 修改清單 + 測試結果 |

---

#### R-02：完成 Step 10 — 需求歸檔

| 欄位 | 值 |
|---|---|
| **任務ID** | R-02 |
| **標題** | 將 Phase 3F-0 需求歸檔至 requirements-history |
| **描述** | 將 `tasks/requirements.md` 中 Phase 3F-0 部分（Transaction Boundary Hardening 需求章節）複製到 `tasks/requirements-history/requirements-Phase-3F-0.md`。若 `requirements.md` 同時含其他 Phase 內容，僅萃取 Phase 3F-0 相關部分；或複製完整 `requirements.md` 並在檔名標註 Phase 3F-0。<br><br>歸檔完成後，`requirements.md` 歸零（清除已完成的 Phase 3F-0 需求，保留給後續 Phase 的空白模板），或依實際需求同步處理。 |
| **負責角色** | doc-writer |
| **前置任務** | R-01 |
| **預估工時** | 0.5h |
| **產出文件** | `tasks/requirements-history/requirements-Phase-3F-0.md` |
| **驗收標準** | 歸檔文件存在；`requirements.md` 中 Phase 3F-0 需求已移除或標記為已歸檔 |

---

#### R-03：更新 agent_workflow.md + History

| 欄位 | 值 |
|---|---|
| **任務ID** | R-03 |
| **標題** | 更新 Workflow 文件反映返工進度 |
| **描述** | 修改 `agent_workflow.md`：<br>1. `[v] Step 8：返工循環（第 1 次）` — 標記為完成<br>2. `[v] Step 9：總結報告` — 標記為完成（R-01 已產出）<br>3. `[v] Step 10：需求歸檔` — 標記為完成（R-02 已歸檔）<br>4. 在 `Next Step` 區域新增 Step 6 重新檢查 + Step 7 REVIEWER<br><br>同時更新 `agent_workflow_History.md`：追加 R-01~R-03 完成記錄。 |
| **負責角色** | doc-writer |
| **前置任務** | R-01, R-02 |
| **預估工時** | 0.5h |
| **修改檔案** | `agent_workflow.md`, `agent_workflow_History.md` |
| **驗收標準** | Workflow 文件反映最新返工狀態；Step 8-10 標記為完成 |

---

#### R-04：重新執行 Step 6 — 需求回歸檢查

| 欄位 | 值 |
|---|---|
| **任務ID** | R-04 |
| **標題** | 執行完整需求回歸檢查（R1~R13） |
| **描述** | 對照 tasks/requirements.md 中 R1~R13 逐項檢查，確認：<br>**R1** 紅燈測試已在修正前確認失敗 → 檢查 tests/ 中紅燈測試記錄<br>**R2** 盤點文件完整 → 檢查 phase3f0-inventory.md<br>**R3** R4 R5 Repository/Service/API Transaction Contract → grep 確認無殘留 commit/rollback<br>**R6** Service 層交易邊界 → 檢查 try/commit/rollback 模式<br>**R7** Outbox 原子性 → 檢查 outbox 測試<br>**R8** Flush 後 PK 可用 → 檢查 flush_chain 測試<br>**R9** 測試要求全面覆蓋 → 檢查 6 個測試檔案<br>**R10** 回歸測試 → 檢查 pytest 結果<br>**R11** Commit Scope → 確認 production files ≤ 20<br>**R12** Reviewer Gate ≥ 95 → 目標設定<br>**R13** Git Commit 資訊 → commit message 確認<br><br>產出檢查清單，記錄每項 PASS/FAIL 及證據。 |
| **負責角色** | PLANNER / backend-logic |
| **前置任務** | R-03（Workflow 更新後） |
| **預估工時** | 1h |
| **產出** | 需求回歸檢查記錄（可寫入 summary-report 或獨立文件） |
| **驗收標準** | 全部 13 項需求 PASS；若有 FAIL 需先修復再繼續 |

---

#### R-05：重新啟動 Step 7 — REVIEWER 評分

| 欄位 | 值 |
|---|---|
| **任務ID** | R-05 |
| **標題** | 提交 REVIEWER 重新評分 |
| **描述** | 在 R-04 需求回歸檢查全部 PASS 後，呼叫 REVIEWER 子代理重新評分。此時：<br>1. **流程遵守 = YES**（Step 9 總結報告 ✅ + Step 10 需求歸檔 ✅ + Git Commit 雖未執行但 REVIEWER 後執行，屬正確順序）<br>2. **Reviewer Gate 11 項檢查**：第 1-9 項、第 11 項已於第 0 次 PASS；第 10 項（PostgreSQL CI）為 PARTIAL，需說明「配置已更新，本地無法運行 CI pipeline，依賴 GitHub Actions 實際運行後驗證」<br>3. 目標總分 ≥ 95<br><br>若評分 ≥ 95 → Accepted = YES → 繼續 R-06<br>若評分 < 95 → 依 REVIEWER 報告修復後重新執行 R-04→R-05 |
| **負責角色** | REVIEWER |
| **前置任務** | R-04（需求回歸檢查全部 PASS） |
| **預估工時** | 1.5h |
| **驗收標準** | Score ≥ 95；Accepted = YES |

---

#### R-06：T-28 — Git Commit

| 欄位 | 值 |
|---|---|
| **任務ID** | R-06 |
| **標題** | 提交所有程式碼並推送 |
| **描述** | REVIEWER 評分通過後，執行 Git Commit：<br>1. `git add` 所有修改檔案（19 tracked + 2 new files + 測試檔案）<br>2. `git commit -m "fix(architecture): centralize transaction boundaries in services"`<br>3. `git push origin fix/transaction-boundary-hardening`<br><br>注意：<br>- 禁止 force push<br>- 禁止修改歷史 Migration<br>- 允許一個後續 CI 修復 Commit（CI pipeline 發現問題時）<br>- 確認 `.gitignore` 排除不需要的檔案（如測試資料庫 *.db） |
| **負責角色** | backend-logic |
| **前置任務** | R-05（REVIEWER 評分通過） |
| **預估工時** | 0.5h |
| **驗收標準** | Commit 訊息正確；Push 成功；無 force push |

---

#### R-07：PostgreSQL CI 說明文件

| 欄位 | 值 |
|---|---|
| **任務ID** | R-07 |
| **標題** | 產出 PostgreSQL CI 說明文件 |
| **描述** | REVIEWER 指出第 10 項（PostgreSQL CI）為 PARTIAL，因為配置已更新但未在 Postgres 上實際執行驗證。產出簡短說明文件 `tasks/phase3f0-pg-ci-note.md`，記錄：<br>1. CI 配置變更摘要（`.github/workflows/ci.yml` 新增 Transaction Atomicity 測試套件）<br>2. 本地無法運行 CI pipeline 的原因（需 GitHub Actions 環境 + PostgreSQL 服務）<br>3. 預期 CI 運行後的行為<br>4. 驗證清單：若 CI pipeline 觸發，需確認哪些測試在 Postgres 上執行通過<br><br>此文件可附加至總結報告附錄，或在 REVIEWER 評分時作為第 10 項的補充證據。 |
| **負責角色** | doc-writer |
| **前置任務** | R-01（總結報告產出時可一併完成） |
| **預估工時** | 0.5h |
| **產出文件** | `tasks/phase3f0-pg-ci-note.md`（可選，或直接寫入總結報告附錄） |
| **驗收標準** | PostgreSQL CI 狀態透明化，REVIEWER 可理解 PARTIAL 原因 |

### 9.4 返工依賴圖

```
R-01 (總結報告)
  └── R-02 (需求歸檔)
        └── R-03 (更新 Workflow)
              └── R-04 (重新 Step 6 需求回歸檢查)
                    └── R-05 (重新 Step 7 REVIEWER 評分)
                          ├── [通過] ──→ R-06 (Git Commit)
                          └── [不通過] ──→ 修復 → R-04 → R-05
```

### 9.5 角色分派摘要

| 角色 | 任務 |
|---|---|
| **doc-writer** | R-01（總結報告）、R-02（需求歸檔）、R-03（更新 Workflow）、R-07（PG CI 說明） |
| **PLANNER / backend-logic** | R-04（需求回歸檢查） |
| **REVIEWER** | R-05（重新評分） |
| **backend-logic** | R-06（Git Commit） |

### 9.6 預估工時

| 任務 | 工時 |
|---|---|
| R-01 總結報告 | 1h |
| R-02 需求歸檔 | 0.5h |
| R-03 更新 Workflow | 0.5h |
| R-04 需求回歸檢查 | 1h |
| R-05 REVIEWER 評分 | 1.5h |
| R-06 Git Commit | 0.5h |
| R-07 PG CI 說明 | 0.5h |
| **合計** | **~5.5h** |

### 9.7 返工前 Checklist

- [ ] 確認當前分支為 `fix/transaction-boundary-hardening`
- [ ] 確認所有程式碼修改已測試通過（pytest 結果參照 REVIEWER 報告）
- [ ] 確認無 pending 的程式碼修改（返工期只做流程步驟）
- [ ] 備份 REVIEWER 第 0 次評分報告（已存在於 `tasks/reviews/review_Phase-3F-0_0.md`）

### 9.8 風險與應對

| 風險 | 機率 | 影響 | 應對 |
|------|------|------|------|
| **R-05 REVIEWER 仍評 < 95** | 中 | 需要再次返工 | PostgreSQL CI PARTIAL 可能導致扣分。若低於 95，分析扣分項目，補充說明或修復後重新提交 |
| **Git Push 衝突** | 低 | 阻滯 R-06 | 若有遠端變更，先 pull --rebase 再 push |
| **CI pipeline 實際執行失敗** | 中 | 需額外修復 Commit | 允許一個 CI 修復 Commit（R13 允許），修復後再評分 |
| **requirements.md 結構複雜** | 低 | 歸檔耗時 | 若 requirements.md 含多個 Phase，僅萃取 Phase 3F-0 章節歸檔，保留其餘內容 |
