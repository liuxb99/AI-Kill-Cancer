# Phase 3F-0 Inventory — BaseRepository 使用範圍完整盤點

> 盤點日期：2026-07-30
> 盤點範圍：src/backend/repositories/、src/backend/services/、src/backend/api/v1/

---

## 一、所有繼承 BaseRepository 的類別（共 27 個）

| # | 檔案路徑 | 類別名稱 | 覆寫 create/update/delete | 呼叫 super() |
|---|---------|---------|--------------------------|-------------|
| 1 | `repositories/analysis_run_repo.py` | AnalysisRunRepository | 未覆寫 | 使用繼承的 create/update/delete |
| 2 | `repositories/cancer_case_repo.py` | CancerCaseRepository | 未覆寫 | 同上 |
| 3 | `repositories/case_acl_repo.py` | CaseACLRepository | 未覆寫，有自訂方法含 commit | 同上 |
| 4 | `repositories/clinical_decision_repo.py` | ClinicalDecisionRepository | **覆寫 create()** | ❌ 自訂 add 無 commit |
| 5 | `repositories/clinical_decision_repo.py` | ClinicalDecisionTraceRepository | **覆寫 create()** | ❌ 自訂 add 無 commit |
| 6 | `repositories/drug_interaction_repo.py` | DrugInteractionRepository | 未覆寫，有自訂 upsert() 含 commit | 使用繼承的 |
| 7 | `repositories/drug_repo.py` | DrugRepository | 未覆寫 | 使用繼承的 |
| 8 | `repositories/evidence_item_repo.py` | EvidenceItemRepository | 未覆寫，有自訂 upsert() 含 commit | 使用繼承的 |
| 9 | `repositories/evidence_repo.py` | EvidenceRepository | 未覆寫 | 使用繼承的 |
| 10 | `repositories/knowledge_source_repo.py` | KnowledgeSourceRepository | 未覆寫，有自訂方法含 commit | 使用繼承的 |
| 11 | `repositories/patient_repo.py` | PatientRepository | 未覆寫 | 使用繼承的 |
| 12 | `repositories/recommendation_repo.py` | RecommendationRepository | **覆寫 create()** | ❌ 自訂 add 無 commit |
| 13 | `repositories/recommendation_repo.py` | TraceRepository | 未覆寫 | 使用繼承的 |
| 14 | `repositories/report_repo.py` | ReportRepository | 未覆寫 | 使用繼承的 |
| 15 | `repositories/sequencing_test_repo.py` | SequencingTestRepository | 未覆寫 | 使用繼承的 |
| 16 | `repositories/specimen_repo.py` | SpecimenRepository | 未覆寫 | 使用繼承的 |
| 17 | `repositories/treatment_plan_repo.py` | TreatmentPlanRepository | **覆寫 create()** | ❌ add+flush 無 commit |
| 18 | `repositories/treatment_plan_repo.py` | TreatmentPhaseRepository | **覆寫 create/create_many/delete** | ❌ flush |
| 19 | `repositories/treatment_plan_repo.py` | TreatmentItemRepository | **覆寫 create/create_many/delete** | ❌ flush |
| 20 | `repositories/treatment_plan_repo.py` | TreatmentMonitoringRepository | **覆寫 create/create_many/delete** | ❌ flush |
| 21 | `repositories/treatment_plan_repo.py` | TreatmentSafetyRuleRepository | **覆寫 create/create_many/delete** | ❌ flush |
| 22 | `repositories/treatment_plan_repo.py` | TreatmentPlanTraceRepository | **覆寫 create/create_many/delete** | ❌ flush |
| 23 | `repositories/tumor_board_repo.py` | TumorBoardConsensusRepository | **覆寫 create()** | ❌ add+flush 無 commit |
| 24 | `repositories/tumor_board_repo.py` | TumorBoardOpinionRepository | **覆寫 create/create_many** | ❌ 部分 flush |
| 25 | `repositories/tumor_board_repo.py` | TumorBoardConsensusTraceRepository | **覆寫 create/create_many** | ❌ 部分 flush |
| 26 | `repositories/uploaded_file_repo.py` | UploadedFileRepository | 未覆寫 | 使用繼承的 |
| 27 | `repositories/user_repo.py` | UserRepository | 未覆寫 | 使用繼承的 |
| 28 | `repositories/variant_repo.py` | VariantRepository | 未覆寫，有自訂 bulk_create() 含 commit | 使用繼承的 |

## 二、不繼承 BaseRepository 的倉儲

| 檔案路徑 | 類別名稱 | 說明 |
|---------|---------|------|
| `repositories/clinical_graph_outbox_repo.py` | ClinicalGraphOutboxRepository | 完全自幹，使用 flush() 而非 commit() ✅ |

## 三、擁有自訂 commit/rollback 的 Repository（需修改）

| 類別 | 方法 | 行號 | commit 寫法 | 修改方式 |
|------|------|------|------------|---------|
| **BaseRepository** | `create()` | base.py | `await self.db.commit()` | 改 flush |
| **BaseRepository** | `update()` | base.py | `await self.db.commit()` | 改 flush |
| **BaseRepository** | `delete()` | base.py | `await self.db.commit()` | 改 flush |
| **CaseACLRepository** | `delete_case_permission()` | L35 | `await self.db.commit()` | 改 flush |
| **CaseACLRepository** | `grant_permission()` | L45, L55 | `await self.db.commit()`（2 處） | 改 flush |
| **DrugInteractionRepository** | `upsert()` | L53, L73 | `await self.db.commit()`（2 處） | 改 flush |
| **EvidenceItemRepository** | `upsert()` | L80, L100, L134 | `await self.db.commit()`（3 處） | 改 flush |
| **EvidenceItemRepository** | `withdraw_by_source_record()` | L195 | `await self.db.commit()` | 改 flush |
| **KnowledgeSourceRepository** | `upsert()` | L34, L40 | `await self.db.commit()`（2 處） | 改 flush |
| **KnowledgeSourceRepository** | `record_health_check()` | L66 | `await self.db.commit()` | 改 flush |
| **VariantRepository** | `bulk_create()` | L26 | `await self.db.commit()` | 改 flush |

## 四、Service 層交易管理現狀

| Service | 有無 commit/rollback | 狀態 |
|---------|---------------------|------|
| RecommendationService | ✅ L317 commit, L319 rollback | ✅ 正確 |
| ClinicalDecisionService | ✅ L394 commit, L396 rollback | ✅ 正確 |
| TumorBoardConsensusService | ✅ L435 commit, L437 rollback | ✅ 正確 |
| TreatmentPlanService | ✅ 多處 commit/rollback | ✅ 正確 |
| ClinicalGraphEventService | ❌ 無交易管理 | ⚠️ 需確認 |

## 五、API 層直接 commit/rollback 的位置（需修改）

| API 檔案 | Endpoint | 行號 | 操作 |
|---------|---------|------|------|
| `api/v1/clinical_graph.py` | POST /events/{event_id}/retry | L169 | `await db.commit()` |
| `api/v1/workbench.py` | POST /tumor-board/{case_id}/review | L112-114 | commit + rollback |
| `api/v1/workbench.py` | POST /tumor-board/{case_id}/vote | L306-308 | commit + rollback |
| `api/v1/workbench.py` | POST /tumor-board/{case_id}/comment | L375-377 | commit + rollback |
| `api/v1/workbench.py` | POST /case/{case_id}/notes | L482-484 | commit + rollback |
| `api/v1/workbench.py` | PATCH /case/{case_id}/notes/{note_id} | L543 | commit |
| `api/v1/workbench.py` | DELETE /case/{case_id}/notes/{note_id} | L596 | commit |

## 六、修改範圍摘要

| 類別 | 數量 | 說明 |
|------|------|------|
| BaseRepository (base.py) | 3 處 commit 改 flush | create/update/delete |
| Repository 自行 commit | 11 處 commit 改 flush | 5 個 repo（CaseACL, DrugInteraction, EvidenceItem, KnowledgeSource, Variant） |
| API commit/rollback | 7 處移至 Service | workbench.py 6 處, clinical_graph.py 1 處 |
| Service 新增/擴充 | 視情況 | WorkbenchService、Ingestion Services |
| **Production files 修改** | **~8-12 個** | 低於 20 上限 ✅ |
