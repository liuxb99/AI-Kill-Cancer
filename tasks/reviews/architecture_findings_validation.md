# Architecture Findings Validation Gate

> **驗證日期**：2025-07-15  
> **基準版本**：v1.0.1（architecture_review.md 審查版本）  
> **當前版本**：`87cac71`（AI-Kill-Cancer HEAD）/ `189d415`（KnowGraphGo HEAD）  
> **驗證範圍**：P0/P1/P2 技術債、Code Smell、Refactor List、Risk List、附錄 C 關鍵發現
> **Severity Rule**：P0 須同時滿足 5 條件（資料錯誤、transaction 不一致、graph corruption、production crash、測試/程式證據）  

---

## 驗證方法說明

每條 Finding 使用以下方法驗證：
1. **grep 搜索**：確認檔案/符號是否存在
2. **檔案讀取**：檢查特定行號內容
3. **git log 確認**：查看是否有相關 Commit 修改過對應檔案

---

## 一、P0 問題驗證（1 項）

*注意：經 Severity Calibration Round 2 重新判定後，僅 P0-03（BaseRepository commit）保留 P0，其餘 5 項因不滿足 P0 5 條件而降級至 P1/P2。*

### Finding: P0-01 — Domain 層混入 SQLAlchemy ORM 依賴
**原始引用：** 「全部 26 個 Domain 檔案均繼承 `DBBase` 並使用 `Column`、`String` 等 ORM 類型」  
**原始證據：** `src/backend/domain/*.py` — 全部檔案  
**當前程式碼驗證：** 使用 `grep` 掃描 `src/backend/domain/` 目錄下所有檔案，確認每個 `.py` 檔案（含 `Model` 類別）仍然導入 `from src.backend.database.models import Base as DBBase`，並使用 `Column`、`String`、`ForeignKey` 等 SQLAlchemy ORM 類型。Domain 目錄仍有 26 個 `.py` 檔案（含 `__init__.py`），其中 24 個包含 ORM 依賴。  
**當前證據：** `src/backend/domain/*.py:15` 行（各檔案 `from src.backend.database.models import Base as DBBase`）  
**Status：** CONFIRMED
**Severity：** P1
**當前 symbol：** 各 Domain Model 類別（如 PatientModel、ClinicalDecisionModel 等）
**當前檔案：** `src/backend/domain/*.py:15`（各檔案 `from src.backend.database.models import Base as DBBase`）
**風險證據：** Domain 層混入 SQLAlchemy ORM 屬於架構偏好（DDD purity）問題，並非 production blocker。ORMLite 在測試環境中仍可正常使用，ORM 遷移影響 Domain 模型是已知架構技術債但未造成實際 production 事故。根據 Severity Calibration Round 2 規則：P0 須同時滿足資料錯誤、transaction 不一致、graph corruption、production crash、測試/程式證據 5 條件，Domain ORM 耦合不滿足其中任何 production 級條件，故降級爲 P1。
**Severity 判定說明：** 此爲 DDD 純淨度（purity）架構偏好，非 production blocker。不滿足 P0 條件①（無資料錯誤）、②（無 transaction 不一致）、③（無 graph corruption）、④（無 production crash），僅滿足⑤（程式證據）。降級至 P1 反映其爲重要但非緊急的架構重構項目。
**建議：** 保持 — 需要重大重構（40h+），建議在下一階段優先執行

### Finding: P0-02 — Service 層反向依賴 API 層
**原始引用：** 「Service 層反向依賴 API 層——違反分層依賴方向」  
**原始證據：** `src/backend/services/recommendation_service.py:248`  
**當前程式碼驗證：** 第 248 行依然存在 `from src.backend.api.v1.recommendation import RecommendationResponse`（lazy import 在函數內部），且 `grep` 全 `services/` 目錄顯示僅此一處反向依賴。  
**當前證據：** `src/backend/services/recommendation_service.py:248:services:create_recommendation`  
**Status：** CONFIRMED
**Severity：** P1
**當前 symbol：** `create_recommendation`（`recommendation_service.py` 內的函數）
**當前檔案：** `src/backend/services/recommendation_service.py:248`
**風險證據：** 違反 Clean Architecture 依賴方向規則（Service 層不應依賴 API 層），造成循環依賴風險，且使 Service 層無法在脫離 API 層的環境中獨立測試。
**Severity 判定說明：** 違反 Clean Architecture 依賴方向，但爲 single lazy import（僅一處），不造成資料錯誤、transaction 不一致、graph corruption 或 production crash。不滿足 P0 條件①-④，僅滿足⑤。降級至 P1。
**建議：** 保持 — 簡單但重要的依賴方向修正，需 2h

### Finding: P0-03 — BaseRepository 預設 commit() 導致事務邊界下移
**原始引用：** 「`BaseRepository` 預設 `commit()` 行爲導致事務邊界從 Service 層下沉至 Repository 層，形成資料不一致風險」  
**原始證據：** `src/backend/repositories/base.py:29,73,82`  
**當前程式碼驗證：** `base.py` 的 `create()`（L29）、`update()`（L73）、`delete()`（L82）方法均仍直接呼叫 `await self.db.commit()`，沒有改爲 `flush()`。  
**當前證據：** `src/backend/repositories/base.py:29,73,82:BaseRepository:create/update/delete`  
**Status：** CONFIRMED
**Severity：** P0
**當前 symbol：** `BaseRepository.create` / `update` / `delete`
**當前檔案：** `src/backend/repositories/base.py:29,73,82`
**風險證據：** `commit()` 在 Repository 層直接提交事務，導致：1）Service 層無法實現跨多個 Repository 操作的原子性；2）部分更新失敗無法回滾；3）事務邊界從 Service 層下沉至 Repository 層，違反 DDD 事務邊界應由 Aggregate Root 控制的原則。
**最小重現案例（Atomicity）：**
```python
# Service 中的典型場景 — repoA.create() commit 後 repoB.create() 失敗，repoA 的變更無法回滾
async def create_patient_with_case(patient_data, case_data):
    repoA = PatientRepository(db)
    repoB = CancerCaseRepository(db)
    patient = await repoA.create(**patient_data)  # ← 已 commit，無法回滾
    case = await repoB.create(**case_data)         # ← 若此步失敗，patient 已持久化
    return patient, case
```
上述場景直接在 `repositories/base.py:29` 的 `create()` 中 `commit()` 導致：第一步成功後資料已寫入資料庫，第二步失敗時 Service 層無法透過 rollback 撤銷第一步的變更，造成資料不一致。此爲 production 級資料錯誤風險。滿足 P0 條件①（資料錯誤）、②（transaction 不一致）、⑤（程式證據）。
**建議：** 保持 — 消除資料不一致風險的核心修復，需將 commit() 改爲 flush()

### Finding: P0-04 — Outbox Repository 混入部分業務邏輯
**原始引用：** 「CRUD 與業務邏輯未分離」  
**原始證據：** `src/backend/repositories/clinical_graph_outbox_repo.py` — 全檔案  
**當前程式碼驗證：** 該檔案包含以下方法，逐方法分析業務邏輯 vs persistence：

| 方法 | 業務邏輯？ | 說明 |
|------|:---------:|------|
| `create()` | 否 | 純 persistence（新增記錄） |
| `get_by_event_id()` | 否 | 純 persistence（查詢） |
| `claim_pending()` | 否 | 狀態查詢 + 標記 processing，無 business rule |
| `mark_completed()` | 否 | 純 persistence（狀態更新） |
| `mark_failed()` | **是** | 使用 `DEFAULT_RETRY_POLICY.is_dead_letter()` 決定 dead_letter/failed 狀態，使用 `_next_available_at()` 計算 retry delay |
| `mark_dead_letter()` | 部分 | 直接標記死信，無 retry 計算 |
| `release_stale()` | 否 | 時間條件查詢 + 狀態重置 |
| `get_failed_events()`, `list_failed()`, `get_status_counts()` | 否 | 純 persistence（查詢） |

其中僅 `mark_failed()` 包含真正的業務邏輯（Retry Policy 判斷、Dead Letter 判定、Retry Delay 計算），其餘方法均爲純 persistence 操作。

**當前證據：** `src/backend/repositories/clinical_graph_outbox_repo.py:全檔案:ClinicalGraphOutboxRepository`  
**Status：** PARTIALLY CONFIRMED — 確實混入少量業務邏輯（mark_failed 中的 retry/dead_letter 判斷），但大部分方法仍爲 persistence
**Severity：** P1
**當前 symbol：** `ClinicalGraphOutboxRepository`
**當前檔案：** `src/backend/repositories/clinical_graph_outbox_repo.py:全檔案`
**風險證據：** Repository 層混入少量業務邏輯（重試計算、Dead Letter 判定）違反 Repository 模式的單一職責。但此爲架構組織問題，不直接造成資料錯誤、transaction 不一致、graph corruption 或 production crash。不滿足 P0 條件①-④。
**Severity 判定說明：** 逐方法分析後確認大部分爲 persistence，僅 `mark_failed()` 包含 retry policy / dead letter / retry delay 等 business logic。根據 Severity Calibration Round 2 指示，判定爲 PARTIALLY CONFIRMED，降級至 P1。
**建議：** 保持 — 建議抽取 RetryPolicy 至 service 層

### Finding: P0-05 — Python ID Factory 缺少 5 個治療計劃相關方法
**原始引用：** 「Python ID Factory 缺少 5 個治療計劃相關方法——跨語言 ID 不一致」  
**原始證據：** `src/backend/clinical_graph/id_factory.py` — 全檔案  
**當前程式碼驗證：** 實地讀取 `src/backend/clinical_graph/id_factory.py` 確認：Python `ClinicalGraphIDFactory` 只有 patient_id/recommendation_id/clinical_decision_id/consensus_id/opinion_id/specialty_id/drug_id/evidence_id/variant_id/relation_id 共 10 個方法（L23-77），**缺少** treatment_plan_id、treatment_phase_id、treatment_item_id、monitoring_id、safety_rule_id 這 5 個方法。對比 Go `ClinicalIDFactory`（`KnowGraphGo/adapter/clinical/id_factory.go:76-98`）已有完整的 TreatmentPlanID、TreatmentPhaseID、TreatmentItemID、MonitoringID、SafetyRuleID。  
**Cross-Language Runtime 使用確認：** `grep` 全量掃描 `src/backend/` 下 `ClinicalGraphIDFactory.` 的調用，僅發現 `clinical_graph.py:189`（patient_id）、`clinical_graph.py:235`（recommendation_id）、`clinical_graph.py:286`（consensus_id）、`tumor_board_service.py:407`（opinion_id）。**Python 端無任何 runtime 調用 `treatment_plan_id`、`treatment_phase_id`、`treatment_item_id`、`monitoring_id`、`safety_rule_id`**。因此跨語言 ID 不一致問題在當前 code path 中不會實際觸發。  
**當前 symbol：** `ClinicalGraphIDFactory`（Python）/ `ClinicalIDFactory`（Go）  
**當前檔案：** `src/backend/clinical_graph/id_factory.py:23-77`（Python）/ `KnowGraphGo/adapter/clinical/id_factory.go:76-98`（Go）  
**Status：** CONFIRMED  
**Severity：** P1  
**風險證據：** Python ↔ Go ID Factory 方法不一致，存在跨語言 ID 生成規則不同的潛在風險。但經 grep 確認 Python 端**當前無任何 runtime 調用**缺少的 5 個方法，因此跨語言 ID 不匹配不會在當前 production code path 中造成實際的知識圖譜查詢失敗。未來若 Python 端需生成 treatment_plan/treatment_phase/treatment_item/monitoring/safety_rule 等 entity ID 時，需要補上對應方法。
**Severity 判定說明：** 缺少方法但無 runtime 使用，不造成資料錯誤、transaction 不一致、graph corruption 或 production crash。不滿足 P0 條件①-④，僅滿足⑤。降級至 P1。
**建議：** 保持 — 需 2h 補上 5 個方法  

### Finding: P0-06 — buildProvenance 硬編碼爲 ProvenanceImported
**原始引用：** 「所有事件被標記爲「匯入」」  
**原始證據：** `KnowGraphGo/adapter/clinical/adapter.go:110-112`  
**當前程式碼驗證：** 實地讀取 `KnowGraphGo/adapter/clinical/adapter.go` 確認：
- `buildProvenance()`（L110-112）**依然返回 `graph.ProvenanceImported`**，完全未根據 EventType 區分 provenance 來源。
- `relationProps()`（L117-133）和 `entityProps()`（L135-160）**已包含完整 8 個 Provenance 欄位**（event_id、event_type、aggregate_type、aggregate_id、correlation_id、causation_id、occurred_at、source_system），其中 **`event_type` 已可區分** created/updated/approved/activated/completed 等事件類型。

**Provenance 語意分析：**
查閱 `KnowGraphGo/graph/provenance.go` 定義：
- `ProvenanceImported` = "表示從外部系統匯入的資料"
- 所有臨床資料確實來自 Python Backend（外部系統），因此 `ProvenanceImported` **語意正確**。
- `event_type` 欄位（如 `"treatment_plan.created"`、`"treatment_plan.approved"`）已保存在 entity/relation Props 中，可作為事件來源的細粒度區分。

因此核心問題「無法區分事件來源」已透過 `event_type` 欄位得到補償，`buildProvenance` 返回 `ProvenanceImported` 本身語意正確（標示資料來源於外部匯入）。

**當前 symbol：** `buildProvenance` / `relationProps` / `entityProps`  
**當前檔案：** `KnowGraphGo/adapter/clinical/adapter.go:110-112`（buildProvenance）/ L117-133（relationProps）/ L135-160（entityProps）  
**Status：** PARTIALLY CONFIRMED — buildProvenance 仍硬編碼，但 entityProps/relationProps 中的 event_type 已能區分事件來源，ProvenanceImported 語意正確
**Severity：** P2
**風險證據：** buildProvenance 固定返回 `ProvenanceImported`，但 entityProps/relationProps 已保存 `event_type` 以區分 created/updated/approved/activated/completed 等事件類型。且 `ProvenanceImported` 對於臨床匯入資料語意正確。剩餘風險極低：僅在直接查詢 Entity/Relation 的 Provenance 欄位（而非 Properties）時無法區分事件來源。不滿足 P0 條件①-④。
**Severity 判定說明：** buildProvenance 硬編碼但語意正確，且 event_type 已保存在 properties 中提供細粒度區分。剩餘風險極低，降級至 P2。
**建議：** 保持 — 若需精確 Provenance 可考慮根據 EventType 返回不同值（如 created→ProvenanceParsed、imported→ProvenanceImported），但當前架構下收益有限  

---

## 二、P1 問題驗證（15 項）

*含從原 P0 降級 4 項：P0-01（Domain ORM）、P0-02（反向依賴）、P0-04（Outbox Repository）、P0-05（ID Factory）。*

### Finding: P1-01 — RecommendationEngine.run() 違反 Pure Function 原則
**原始引用：** 「產生 I/O 副作用」  
**原始證據：** `src/backend/clinical/recommendation_engine.py:482-715`  
**當前程式碼驗證：** `run()` 方法仍在 L440，且透過 `self._trace_manager` 寫入 trace、呼叫 Collector（含 DB/API 呼叫）。行號變化（原 482→現 440）是因代碼重構調整，但 I/O 副作用依然存在。  
**當前證據：** `src/backend/clinical/recommendation_engine.py:440-715:RecommendationEngine:run`  
**Status：** CONFIRMED  
**Severity：** P1  
**當前 symbol：** `RecommendationEngine.run`  
**當前檔案：** `src/backend/clinical/recommendation_engine.py:440-715`  
**風險證據：** `run()` 方法同時負責推理（Pure Function 應有的行爲）和 I/O 操作（trace 寫入、Collector DB/API 呼叫），違反命令查詢分離原則。導致：1）無法對推理邏輯進行純單元測試；2）I/O 失敗時推理結果遺失；3）難以並行化或分散式擴展。  
**建議：** 保持

### Finding: P1-02 — ORM 狀態欄位使用 String(32) 而非 SAEnum
**原始引用：** 「失去資料庫層類型約束」  
**原始證據：** 多個 Model 檔案，分散  
**當前程式碼驗證：** `grep` 掃描 domain/ 目錄確認多個 Model 仍使用 `Column(String(32))` 作爲狀態欄位，如 `clinical_decision.py:37`（`status = Column(String(32), default="active")`）、`clinical_graph_outbox.py:23`（`status = Column(String(32), default="pending")`）、`treatment_plan.py` 等多處。  
**當前證據：** `src/backend/domain/clinical_decision.py:37:ClinicalDecisionModel` 等  
**Status：** CONFIRMED  
**Severity：** P1  
**建議：** 保持 — 但注意到 `ConsentStatusEnum` 已被補入 `__init__.py.__all__`（L184），部分 Enum 已修復  

### Finding: P1-03 — 缺少樂觀鎖版本控制
**原始引用：** 「無 `version_id` 欄位」  
**原始證據：** 全部 Model，全域  
**當前程式碼驗證：** `grep` 搜索 `version_id|__version__|row_version` 在全 Domain 目錄下無結果。僅 `TreatmentPlanModel` 有版本控制（`version`, `previous_version_id`, `supersedes_version_id`），但無標準樂觀鎖模式。  
**當前證據：** `src/backend/domain/*.py:全域:所有 Model`  
**Status：** CONFIRMED  
**Severity：** P1  
**建議：** 保持  

### Finding: P1-04 — Repository 型別註解不完整
**原始引用：** 「17/22 個檔案缺少 `AsyncSession` 型別」
**原始證據：** 17 個 Repository 檔案的 `__init__`
**當前程式碼驗證：** 逐檔檢查 `repositories/` 目錄內所有 `.py` 檔案的 `__init__` 參數型別註解。使用 `grep` 搜索 `def __init__` 後逐行確認：

**有 AsyncSession 型別註解的檔案（6 檔案，約 15 個 class）：**
- `base.py:22` — `def __init__(self, model_class: type[ModelT], db: AsyncSession)`
- `clinical_decision_repo.py:40,204` — 2 個 class ✅
- `clinical_graph_outbox_repo.py:23` — ✅
- `recommendation_repo.py:41,146` — 2 個 class ✅
- `treatment_plan_repo.py:49,305,370,435,500,565` — 6 個 class ✅
- `tumor_board_repo.py:42,209,298` — 3 個 class ✅

**缺少 AsyncSession 型別註解的檔案（15 個）：**
`analysis_run_repo.py:7`、`cancer_case_repo.py:9`、`case_acl_repo.py:10`、`drug_interaction_repo.py:31`、`drug_repo.py:9`、`evidence_item_repo.py:39`、`evidence_repo.py:9`、`knowledge_source_repo.py:20`、`patient_repo.py:7`、`report_repo.py:7`、`sequencing_test_repo.py:7`、`specimen_repo.py:7`、`uploaded_file_repo.py:9`、`user_repo.py:10`、`variant_repo.py:9`

**統計：** 21 個 repository 檔案（不含 `__init__.py`）中，6 個有型別註解（涵蓋約 15 個 class）、15 個完全無型別註解。原始報告稱 17/22 缺少，現爲 15/21 缺少（略有改善，因 `treatment_plan_repo.py` 和 `tumor_board_repo.py` 新增的多個 class 皆有型別註解）。
**當前證據：** `src/backend/repositories/*.py:__init__:各 Repository`
**Status：** PARTIALLY CONFIRMED — 15/21 個 Repository 檔案仍缺少 AsyncSession 型別註解（較原始 17/22 略有改善）
**Severity：** P1
**建議：** 保持

### Finding: P1-05 — 三套獨立 Trace 系統
**原始引用：** 「Schema 不一致，無法統一查詢」  
**原始證據：** `calculation_trace.py`、`treatment_plan_trace.py`、`decision_thread.py`  
**當前程式碼驗證：** 三個檔案均存在，且各自獨立：`calculation_trace.py`（純記憶體 dict）、`treatment_plan_trace.py`（Builder 模式）、`decision_thread.py`（SQLAlchemy ORM）。此外 `tumor_board_engine.py` 還有第四套 `trace_steps` 機制，`ClinicalDecisionEngine` 仍完全無 Trace。  
**當前證據：** `src/backend/clinical/calculation_trace.py`, `src/backend/clinical/treatment_plan_trace.py`, `src/backend/clinical/decision_thread.py`  
**Status：** CONFIRMED  
**Severity：** P1  
**建議：** 保持 — 實際上已有四套（含 TumorBoardEngine.trace_steps）  

### Finding: P1-06 — Patient Outbox 事件完全缺失
**原始引用：** 「Patient 變更不會投射到知識圖譜」  
**原始證據：** 無對應服務調用  
**當前程式碼驗證：** `grep` 搜索 `patient.*outbox|Patient.*event|patient.*event` 在 `services/` 目錄無結果。未找到 `patient_service.py` 檔案（grep 文件名無匹配）。Patient 建立/更新仍不觸發 Outbox 事件。  
**當前證據：** `src/backend/services/`（無 patient_service.py 或任何 Patient Outbox 事件發送）  
**Status：** CONFIRMED  
**Severity：** P1  
**建議：** 保持  

### Finding: P1-07 — API Error Response 格式不統一
**原始引用：** 「三種格式並存」  
**原始證據：** `clinical.py`、`patients.py`、`evidence.py`  
**當前程式碼驗證：** 抽樣檢查 `api/v1/` 目錄各檔案，三種 Error 格式（A: `detail=str(e)` 純字串、B: `detail={"error","message"}` dict、C: `detail={"error"}` 僅 error key）仍並存，無統一 Exception Handler。  
**當前證據：** `src/backend/api/v1/*.py:分散:各 API Endpoint`  
**Status：** CONFIRMED  
**Severity：** P1  
**建議：** 保持  

### Finding: P1-08 — HTTP Status Code 不一致
**原始引用：** 「POST 返回 200 而非 201，部分語義錯誤」  
**原始證據：** `recommendation.py:125`、`cases.py:131`  
**當前程式碼驗證：** `recommendation.py:125` 路由爲 `@router.post("", response_model=RecommendationResponse)` 未設定 `status_code`，預設返回 200 而非 201。確認無 `status_code=201` 設定。  
**當前證據：** `src/backend/api/v1/recommendation.py:125:create_recommendation`  
**Status：** CONFIRMED  
**Severity：** P1  
**建議：** 保持  

### Finding: P1-09 — Migration SQLite/PostgreSQL 不一致
**原始引用：** 「部分 Downgrade 不冪等」
**原始證據：** `migrations/versions/015`、`022`、`025`
**當前程式碼驗證：** 逐檔讀取 migration 015/017/022/025 的 upgrade/downgrade 邏輯：

**015 (`015_make_clinical_reports_case_id_non_nullable.py`)：**
- upgrade：先 UPDATE 修補 NULL 值，再根據 dialect 選擇 `alter_column`（PostgreSQL）或重建表（SQLite）— 有 SQLite 相容性處理 ✅
- downgrade：使用 `batch_alter_table` 將 case_id 改回 nullable — 跨 dialect 相容 ✅

**017 (`017_phase3a_recommendation_tables.py`)：**
- upgrade：三個 `create_table` — 無 IF NOT EXISTS 檢查 ❌
- downgrade：三個 `drop_table` — 無 IF EXISTS 檢查 ❌（若重複執行會報錯）

**022 (`022_phase3d_graph_correctness_outbox.py`)：**
- upgrade：使用 `_has_column()` 檢查避免重複新增欄位 ✅；索引建立有 try/except 保護 ✅
- downgrade（SQLite）：完整重建表邏輯，先刪備份表確保冪等，再 rename/create/insert/drop ✅
- downgrade（PostgreSQL）：直接 `drop_column` — 若欄位已不存在會出錯 ❌

**025 (`025_phase3e_version_composite_unique.py`)：**
- upgrade：SQLite 用 `batch_alter_table` ✅；PostgreSQL 使用 `DROP CONSTRAINT IF EXISTS` + `CREATE UNIQUE CONSTRAINT` 含 `IF NOT EXISTS` 檢查 ✅
- downgrade：SQLite 用 batch 模式完整逆操作 ✅；PostgreSQL 用 `DROP CONSTRAINT IF EXISTS` + 條件式建立 ✅

**結論：** 015 和 025 的 downgrade 設計完善（跨 dialect 相容）；022 的 PostgreSQL downgrade 缺少欄位存在檢查；017 完全沒有 IF EXISTS 保護。整體較原始審查時已大幅改善。
**當前證據：** `migrations/versions/015*`, `017*`, `022*`, `025*`（已逐條確認）
**Status：** PARTIALLY CONFIRMED — 015、025 已獲完善修復，022 部分修復，017 仍無 IF EXISTS
**Severity：** P1
**若已修正：** 
- Migration 015 SQLite 相容性：`a9caf0d8dc0ac1bb42a2ed70fec4bc917b4a6b7d`
- Migration 013 冪等性修復：`264dedb338f84c56ca5b299707e6c2ee79982626`
- Migration 025 複合 UNIQUE 約束（Phase 3E）：`23d4d1f328453a6c040b5f920057d3ba3a56701e`、`54d8bd444121fc887c672d06dea66f7ea0c10760`、`146aa10da5c37c3e208fe1899f02fc2385d859f5`
**建議：** 降級 — 多數 Migration 問題已被後續 Commit 修復

### Finding: P1-10 — Adapter 缺少 Variant/Guideline/Drug 事件處理
**原始引用：** 「變異/指導用藥/藥物事件未處理」  
**原始證據：** `KnowGraphGo/adapter/clinical/adapter.go:66-89`  
**當前程式碼驗證：** `adapter.go:66-89` 的 `ApplyEvent()` switch 僅處理 patient、recommendation、clinical_decision、tumor_board_consensus、treatment_plan 系列事件，無 variant、guideline、drug 事件處理。`grep` 搜索 `mapVariant|mapGuideline|mapDrug` 無結果。  
**當前證據：** `KnowGraphGo/adapter/clinical/adapter.go:66-89:ClinicalAdapter:ApplyEvent`  
**Status：** CONFIRMED  
**Severity：** P1  
**建議：** 保持  

### Finding: P1-11 — Worker 缺少 Heartbeat 機制
**原始引用：** 「Phase 2 崩潰導致事件卡死」  
**原始證據：** `src/backend/clinical_graph/worker.py:60-84`  
**當前程式碼驗證：** `grep` 搜索 `heartbeat|Heartbeat` 在 `worker.py` 無結果。Worker 仍缺少心跳機制。  
**當前證據：** `src/backend/clinical_graph/worker.py:60-84:OutboxWorker`  
**Status：** CONFIRMED  
**Severity：** P1  
**建議：** 保持  

---

## 三、P2 問題驗證（12 項）

*含從原 P0 降級 1 項：P0-06（buildProvenance）。*

### Finding: P2-01 — Aggregate 邊界不清晰
**原始引用：** 「無顯式 Aggregate Root 標記」  
**原始證據：** 全域 Domain  
**當前程式碼驗證：** Domain 目中無任何 `@aggregate_root` 裝飾器或 `AggregateRoot` 基底類別標記。  
**Status：** CONFIRMED  
**Severity：** P2  

### Finding: P2-02 — 缺少顯式 ValueObject 模式
**原始引用：** 「無 `@dataclass(frozen=True)` 值物件」  
**原始證據：** 全域 Domain  
**當前程式碼驗證：** `grep` 搜索 `@dataclass(frozen=True)` 在 `domain/` 無結果。雖有 `enums.py` 作爲值物件，但無 frozen dataclass 模式。  
**Status：** CONFIRMED  
**Severity：** P2  

### Finding: P2-03 — Engine 呼叫私有 API
**原始引用：** 「耦合 RuleSet 內部實作」  
**原始證據：** `clinical_decision_engine.py:209`  
**當前程式碼驗證：** L209 依然存在 `top_drug_name = self._rule_set._get_top_drug_name(rec_dict)` — 呼叫了 `_get_top_drug_name` 私有方法。行號與原始報告一致。  
**當前證據：** `src/backend/clinical/clinical_decision_engine.py:209:ClinicalDecisionEngine`  
**Status：** CONFIRMED  
**Severity：** P2  

### Finding: P2-04 — 手動 try/commit 重複模式
**原始引用：** 「缺少 `@transactional` 裝飾器」  
**原始證據：** 全部 4 個 Service  
**當前程式碼驗證：** `grep` 搜索 `@transactional` 在 `src/` 下無結果。所有 Service 仍使用手動 try/commit/rollback 模式。  
**Status：** CONFIRMED  
**Severity：** P2  

### Finding: P2-05 — God Class：TreatmentPlanService（57KB）
**原始引用：** 「違反單一職責」  
**原始證據：** `treatment_plan_service.py`  
**當前程式碼驗證：** 檔案大小約 57KB（ls 間接確認爲 `57242` bytes），仍然是大型 God Class。  
**Status：** CONFIRMED  
**Severity：** P2  

### Finding: P2-06 — God Class：ClinicalAdapter（40KB）
**原始引用：** 「6 個大型 Mapper 函數」  
**原始證據：** `KnowGraphGo/adapter/clinical/adapter.go`  
**當前程式碼驗證：** 檔案大小約 40KB（約 1214 行），仍包含 6 個大型 Mapper 函數（mapRecommendationEvent、mapClinicalDecisionEvent、mapConsensusEvent、mapTreatmentPlanEvent 等），無明顯拆分。  
**Status：** CONFIRMED  
**Severity：** P2  

### Finding: P2-07 — God File：report_generator.py（64KB）
**原始引用：** 「單一檔案處理多種報表類型」  
**原始證據：** `report_generator.py`  
**當前程式碼驗證：** 檔案大小約 64KB，仍爲單一大型檔案。從導入行可看出它同時處理 HTML 生成、樣式定義、多種報表類型。  
**Status：** CONFIRMED  
**Severity：** P2  

### Finding: P2-08 — ClinicalDecisionEngine 完全無 Trace 記錄
**原始引用：** 「臨床決策引擎無任何追蹤」  
**原始證據：** `clinical_decision_engine.py`  
**當前程式碼驗證：** `grep` 搜索 `trace|Trace|TraceManager` 在 `clinical_decision_engine.py` 中無任何結果。完全無 Trace 記錄。  
**當前證據：** `src/backend/clinical/clinical_decision_engine.py:全檔案:ClinicalDecisionEngine`  
**Status：** CONFIRMED  
**Severity：** P2  

### Finding: P2-09 — Migration 017 trace_id UNIQUE 約束問題
**原始引用：** 「類似 019 未修復」
**原始證據：** `migrations/versions/017`
**當前程式碼驗證：** 讀取 `migrations/versions/017_phase3a_recommendation_tables.py` 後確認：
- `domain_recommendations.trace_id`（L33）：`sa.Column("trace_id", sa.String(64), nullable=True, index=True)` — 無 UNIQUE 約束，正常
- `domain_recommendation_traces.trace_id`（L48）：`sa.Column("trace_id", sa.String(64), unique=True, nullable=False, index=True)` — **有 UNIQUE=True 約束**
- `domain_recommendation_trace_steps.trace_id`（L57）：FK 指向 `domain_recommendation_traces.id` 而非 trace_id
- downgrade（L71-74）：三個 `op.drop_table()` 操作，無 IF EXISTS 判斷
**Status：** CONFIRMED — trace_id 在 domain_recommendation_traces 表設有 UNIQUE 約束，若業務允許同一 trace_id 跨多筆記錄則有問題；downgrade 無 IF EXISTS 檢查，非冪等
**Severity：** P2

### Finding: P2-10 — 缺少 KnowGraphGo CLI 端到端整合測試
**原始引用：** 「缺少 KnowGraphGo CLI 端到端整合測試」  
**原始證據：** 無測試檔案  
**當前程式碼驗證：** git log 顯示 Phase 3D 添加了 e2e 測試（`fix(e2e): adapt path validation`、`fix(e2e): use lowercase JSON keys` 等），說明已新增 CLI 端到端測試。  
**Status：** OUTDATED — Phase 3D 已補上 KnowGraphGo CLI 端到端測試  
**Severity：** P2  
**若已修正：** 
- Phase 3D 核心 commit：`5882612a42df044a7acdabb85a15ebd2a24acc8f`（feat: add clinical knowledge graph projection）
- e2e 修復 commits：`6fd6e5a6`（--json flag）、`754055e8`（path validation）、`74d5c76b`（lowercase JSON keys）、`b1aae8e2`（stub preservation）、`b0315180`（verify stub preservation）、`c2d1b688`（verify stub preservation immediately）
**建議：** 關閉  

### Finding: P2-11 — 缺少 TreatmentPlanStateMachine 獨立單元測試
**原始引用：** 「4KB 狀態機缺乏獨立單元測試」  
**原始證據：** 無測試檔案  
**當前程式碼驗證：** `grep` 搜索 `class TestTreatmentPlanStateMachine` 在 `tests/backend/clinical/test_treatment_plan_engine.py:86` 找到結果。`TestTreatmentPlanStateMachine` 已存在，包含有效/無效轉換測試、終止狀態 getAllowedTransitions 測試等完整測試案例。  
**當前證據：** `tests/backend/clinical/test_treatment_plan_engine.py:86:TestTreatmentPlanStateMachine`  
**Status：** OUTDATED — 測試已存在於 `tests/backend/clinical/test_treatment_plan_engine.py`（`TestTreatmentPlanStateMachine`），包含完整狀態轉換測試  
**Severity：** P2  
**若已修正：** `7844095e889e756bef668df72c23c432b3f5d906`（feat(phase3e): add treatment plan engine）  
**建議：** 關閉  

---

## 四、Code Smell 驗證（關鍵項）

### Finding: God Class — TreatmentPlanService（57KB）
**原始引用：** 「單一檔案 57KB，同時負責 Orchestration、Persistence、Event Creation、Version Management」
**grep 驗證：** `ls src/backend/services/treatment_plan_service.py` → 57242 bytes（~57KB）
**Status：** CONFIRMED — 檔案仍爲 ~57KB

### Finding: God Class — ClinicalAdapter（40KB）
**原始引用：** 「包含 6 個大型 Mapper 函數」
**grep 驗證：** `ls KnowGraphGo/adapter/clinical/adapter.go` → 39905 bytes（~40KB）。`grep '^func.*map' adapter.go` 列出 14 個 mapper 函數，其中 `mapTreatmentPlanEvent`（L783-1103，約 320 行）、`mapRecommendationEvent`（L233-392，約 160 行）、`mapClinicalDecisionEvent`（L394-538，約 144 行）爲大型函數。
**Status：** CONFIRMED — 未拆分

### Finding: God File — report_generator.py（64KB）
**原始引用：** 「單一檔案處理多種報表類型」
**grep 驗證：** `ls src/backend/clinical/report_generator.py` → 64451 bytes（~64KB）。檔案同時包含 CSS 樣式定義（~200 行）、HTML 生成（多個 `_render_*` 方法）、資料處理邏輯。
**Status：** CONFIRMED — 仍爲大型檔案

### Finding: God Class — RecommendationEngine + DrugRanker + EvidenceAggregator
**原始引用：** 「三個 God Class 擠在同一檔案（~780 行）」
**grep 驗證：** `ls src/backend/clinical/recommendation_engine.py` → 31224 bytes（~31KB，約 820 行）。包含 `RecommendationRule`（L42）、`EvidenceAggregator`（L133）、`DrugRanker`（L417）、`RecommendationEngine`（L440）四個 class。
**Status：** CONFIRMED — 仍在同一檔案（~820 行）

### Finding: God Class — tumor_board_service.py（34KB）
**原始引用：** 「TumorBoardConsensusService 34KB」
**grep 驗證：** `ls src/backend/services/tumor_board_service.py` → 34102 bytes（~34KB）
**Status：** CONFIRMED — 檔案約 34KB

### Finding: Long Functions — adapter.go 中的大函數
**原始引用：** 「mapTreatmentPlanEvent（L783-1103）、mapRecommendationEvent（L233-392）等」
**grep 驗證：** `grep '^func.*map' KnowGraphGo/adapter/clinical/adapter.go` 確認 14 個 mapper：
- `mapPatientEvent` L171（~62 行）
- `mapRecommendationEvent` L233（~161 行）
- `mapClinicalDecisionEvent` L394（~145 行）
- `mapConsensusEvent` L539（~244 行）
- `mapTreatmentPlanEvent` L783（~322 行）
- `mapTreatmentPlanApproved`/`Activated`/`Paused`/`Completed`/`Superseded` L1131-1147（各約 4 行，委託給 `mapTreatmentPlanStatusEvent` L1105）
- `mapTreatmentPlanStatusEvent` L1105（~26 行）
**Status：** CONFIRMED — `mapTreatmentPlanEvent`（L783-1103，~322 行）和 `mapRecommendationEvent`（L233-392，~160 行）仍爲大型函數

### Finding: Domain 依賴基礎設施（🔴 Critical）
**Status：** CONFIRMED — 同 P0-01  

### Finding: 跨層依賴反向（🔴 Critical）
**Status：** CONFIRMED — 同 P0-02  

### Finding: Schema 碎片化（🟡 Major）
**Status：** CONFIRMED — 同 P1-05  

### Finding: Magic String（🟡 Major）
**Status：** CONFIRMED — 同 P1-02  

### Finding: Copy-Paste Patient Stub（🟡 Major）
**Status：** CONFIRMED — `grep` 搜索 `stubPatient|stubEvidence` 無結果，未提取輔助方法  

### Finding: Copy-Paste Evidence ID 去重（🟢 Minor）
**原始引用：** 「重複的 evidence ID 去重邏輯未提取爲共用函數」
**grep 驗證：** `grep -r "evidence_id.*dedup\|dedup.*evidence\|_dedup_evidence\|remove_duplicate" src/` 無結果。未提取輔助函數。
**Status：** CONFIRMED — 未提取輔助函數  

### Finding: 不一致的錯誤處理（🟡 Major）
**Status：** CONFIRMED — 同 P1-07  

### Finding: Hard Code buildProvenance（🟡 Major）
**Status：** CONFIRMED — 同 P0-06  

### Finding: Private API 呼叫（🟢 Minor）
**Status：** CONFIRMED — 同 P2-03  

### Finding: 無 Trace 的 Engine（🟡 Major）
**Status：** CONFIRMED — 同 P2-08  

### Finding: 狀態機未測試（🟢 Minor）
**Status：** OUTDATED — 同 P2-11  

### Finding: 循環依賴（🟡 Major）
**Status：** CONFIRMED — `recommendation.py` ↔ `recommendation_service.py` 雙向循環仍存在, `recommendation_service.py:248` 仍 lazy import  

### Finding: 循環依賴（類型級）（🟢 Minor）
**Status：** CONFIRMED — `report_generator.py:19-23` 仍在 `TYPE_CHECKING` 下導入 API Schema  

---

## 五、Refactor List 驗證

### HIGH（7 項）

| ID | 原始描述 | 當前驗證 | Status |
|----|---------|---------|--------|
| R-H1 | 分離 Domain/ORM 模型（40h+） | 未開始，全部 Domain 檔案仍混合 ORM | CONFIRMED |
| R-H2 | 修復 Service→API 反向依賴（2h） | `recommendation_service.py:248` 仍存在 | CONFIRMED |
| R-H3 | 統一事務策略（8h） | `base.py` 仍直接 commit() | CONFIRMED |
| R-H4 | 重構 Outbox Repository（8h） | 仍混入業務邏輯 | CONFIRMED |
| R-H5 | 補上 ID Factory 5 個方法（2h） | 仍未實現 | CONFIRMED |
| R-H6 | 改進 buildProvenance（3h） | 仍返回 ProvenanceImported | CONFIRMED |
| R-H7 | 修復 RecommendationEngine.run()（12h） | run() 仍有 I/O 副作用 | CONFIRMED |

### MEDIUM（10 項）

| ID | 原始描述 | 當前驗證 | Status |
|----|---------|---------|--------|
| R-M1 | 拆分 TreatmentPlanService（16h） | 未拆分 | CONFIRMED |
| R-M2 | 拆分 ClinicalAdapter（8h） | 未拆分 | CONFIRMED |
| R-M3 | 拆分 mapTreatmentPlanEvent（4h） | 未拆分 | CONFIRMED |
| R-M4 | 統一 Trace Schema（12h） | 三套獨立系統不變 | CONFIRMED |
| R-M5 | Worker Heartbeat（3h） | 未實現 | CONFIRMED |
| R-M6 | 統一 API Error Response（6h） | 三種格式不變 | CONFIRMED |
| R-M7 | 統一狀態欄位用 SAEnum（6h） | 多處仍用 String | CONFIRMED |
| R-M8 | 添加樂觀鎖（6h） | 未實現 | CONFIRMED |
| R-M9 | 補上 Patient Outbox 事件（4h） | 未實現 | CONFIRMED |
| R-M10 | Variant/Drug Event 處理（4h） | 未實現 | CONFIRMED |

### LOW（10 項）

| ID | 原始描述 | 當前驗證 | Status |
|----|---------|---------|--------|
| R-L1 | 提取 Patient Stub Factory（2h） | 未提取 | CONFIRMED |
| R-L2 | 提取 Evidence ID 去重（1h） | 未提取 | CONFIRMED |
| R-L3 | ClinicalDecisionEngine 添加 Trace（4h） | 無 Trace | CONFIRMED |
| R-L4 | 補充 Repository 型別註解（3h） | 逐檔掃描 21 個 repository 檔案，15 個仍缺少 AsyncSession 型別註解（詳見 P1-04） | PARTIALLY CONFIRMED |
| R-L5 | 引入 @transactional 裝飾器（4h） | 未引入 | CONFIRMED |
| R-L6 | 修正 Migration 不冪等（6h） | 逐檔掃描 015/017/022/025：015、025 已完善修復，022 部分修復，017 仍無 IF EXISTS（詳見 P1-09）。修復 commits：015（`a9caf0d8`）、013（`264dedb3`）、025（`23d4d1f3`、`54d8bd44`、`146aa10d`） | PARTIALLY CONFIRMED |
| R-L7 | 統一 HTTP Status Code（2h） | POST 仍返回 200 | CONFIRMED |
| R-L8 | 添加 409 Conflict 處理（3h） | `grep` 搜索 `status_code=409|HTTP_409_CONFLICT` 在 `src/backend/api/v1/` 下找到 3 處：`clinical_graph.py:162`（`status_code=409`）、`treatment_plans.py:88`（`raise HTTPException(status_code=status.HTTP_409_CONFLICT, ...)`）、`upload_vcf.py:392`（`raise HTTPException(status_code=409, ...)`）。409 Conflict 處理已存在。代表性 commit：`5882612`（phase3d 添加 clinical_graph.py 409 處理）。 | OUTDATED — 409 Conflict 處理已實作（3 處），原始問題已解決 |
| R-L9 | 統一代碼標記/註釋語言（2h） | `grep` 搜索 Unicode CJK 範圍 `[\x{4e00}-\x{9fff}]` 在 `src/` 下返回大量結果，包括中文 docstring（`clinical_graph.py`、`treatment_plans.py`、`clinical_decision.py` 等）、中文註解（`clinical_graph/` 目錄、`etl.py` 的 logger 訊息等）、以及中文介面文字（`routes.py` 的 DashboardKPI 標籤和癌症名稱）。中英文混合註釋普遍存在。 | CONFIRMED |
| R-L10 | 補上 Missing Unit Tests（8h） | 掃描 `tests/` 目錄（共 90+ 個測試檔案）確認：`TreatmentPlanStateMachine` 已有獨立測試（`tests/backend/clinical/test_treatment_plan_engine.py:TestTreatmentPlanStateMachine`）✅；`RecommendationEngine`/`DrugRanker`/`EvidenceAggregator` 有測試（`tests/test_recommendation_engine.py`）✅；`ClinicalDecisionEngine` 在整合測試中覆蓋 ✅；`TumorBoardConsensusService`/`TumorBoardEngine` 有測試 ✅；`OutboxWorker` 有單元測試（`tests/unit/test_phase3d_worker.py`）✅。但 `ClinicalAdapter` (Go) 仍無獨立單元測試 ❌，`PatientOutbox` 因無對應 service 亦無測試 ❌。 | PARTIALLY CONFIRMED — 多數核心元件已有測試，但 Go Adapter 和 Patient Outbox 仍缺 |

---

## 六、Risk List 驗證（14 項）

| ID | 風險描述 | 嚴重程度 | 當前驗證 | Status |
|----|---------|:-------:|---------|--------|
| RSK-01 | Domain ORM 耦合導致架構僵化 | 🔴 Critical | Domain 層仍全部耦合 ORM | CONFIRMED |
| RSK-02 | BaseRepository 預設 commit() 導致部分更新 | 🔴 Critical | 仍直接 commit() | CONFIRMED |
| RSK-03 | 跨語言 ID 不一致導致圖譜資料損毀 | 🔴 Critical | ID Factory 仍缺 5 個方法 | CONFIRMED |
| RSK-04 | Patient 資料永遠不投射到知識圖譜 | 🔴 Critical | Patient Outbox 事件仍缺失 | CONFIRMED |
| RSK-05 | Trace 系統碎片化導致除錯困難 | 🟡 High | 三套系統仍各自爲政 | CONFIRMED |
| RSK-06 | Worker Phase 2 崩潰導致事件永久卡死 | 🟡 High | 無 Heartbeat | CONFIRMED |
| RSK-07 | API Error Response 不一致導致前端整合困難 | 🟡 High | 三種格式並存 | CONFIRMED |
| RSK-08 | Migration 不冪等導致生產環境升降級失敗 | 🟡 High | 部分已修復：015 SQLite compat（`a9caf0d8`）、013 idempotent（`264dedb3`）、025 複合 UNIQUE（`23d4d1f3` 等） | PARTIALLY CONFIRMED |
| RSK-09 | God Class 難以維護和測試 | 🟡 High | TreatmentPlanService 仍爲 57KB | CONFIRMED |
| RSK-10 | 缺少樂觀鎖導致併發寫入遺失更新 | 🟡 High | 無樂觀鎖實作 | CONFIRMED |
| RSK-11 | Recommendation Engine Exception 靜默吞沒 | 🟡 High | 使用 `grep` 全量掃描 `src/backend/clinical/` 下所有 `except` 子句（共 30+ 處），逐行確認：
- `collector.py` 中所有 `except Exception:` 都有 `logger.warning(..., exc_info=True)`（L171-230, L304-357）
- `recommendation_engine.py` 中所有 `except Exception:` 都有 `logger.exception(...)`（L104-123, L486-487, L528-529, L582-583, L624-625, L717-718, L784-790, L810-815）
- `builder.py` 中 `except (ValueError, AttributeError)` 有 `logger.warning`（L71-72），`except Exception` 有 `logger.warning`（L92-93, L132-133）
- `decision_thread.py` 中 `except (ValueError, TypeError)` 有明確 fallback 賦值（L181-182），`except (ValueError, AttributeError)` 有 `return None`（L253-254）
- `recommendation.py:839` `except ValueError` 有 `return len(precedence)` fallback
- `report_generator.py:1116` `except (ValueError, TypeError)` 有 `formatted_time = created` fallback
- `clinical/` 目錄下無任何 `except: pass` 或空 except 區塊
**結論：所有 exception 都有 logging 或 fallback 處理，未發現靜默吞沒模式。** | FALSE POSITIVE — 所有 except 皆有 logging 或明確 fallback，原始 finding 爲誤報 |
| RSK-12 | KnowGraphGo 缺少端到端整合測試 | 🟡 High | Phase 3D 已添加 e2e 測試（`5882612a`、`754055e8`、`b1aae8e2` 等） | OUTDATED |
| RSK-13 | 臨床決策 Engine 無 Trace | 🟡 Medium | 仍無 Trace（P2-08） | CONFIRMED |
| RSK-14 | Aggregate 邊界模糊導致跨 Aggregate 直接參考 | 🟡 Medium | 無 Aggregate Root 標記 | CONFIRMED |

---

## 七、附錄 C 關鍵發現驗證

### C.1 Repository 逐檔案清單
**原始引用：** 22 個 Repository 的 commit/rollback/flush/business logic 狀態  
**當前驗證：** 檔案數量仍爲 22 個（含 `__init__.py`），`base.py` 仍直接 commit()，`treatment_plan_repo.py` 和 `tumor_board_repo.py` 使用 flush()。  
**Status：** CONFIRMED — 狀態未變  
**更新：** 新增 `report_repo.py`（257 bytes, 空類別）等已在列表中。

### C.2 Service Transaction Boundary
**原始引用：** 所有 Service 採用手動 try/commit/rollback 模式  
**當前驗證：** `grep @transactional` 無結果，仍爲手動模式。  
**Status：** CONFIRMED  

### C.3 Engine Pure Function 判定
**原始引用：** `recommendation_engine.run()` 不純，其他 Engine 純函數  
**當前驗證：** `run()` 仍接收 `self._trace_manager`，行號 L440（原 L482）。其他 Engine 判定不變。  
**Status：** CONFIRMED  

### C.4 Migration 一致性
**原始引用：** 015 不可逆，017/019 trace_id UNIQUE 問題
**當前驗證：** 逐檔讀取 migration 015/017/022/025 後：
- 015：已有 SQLite 相容性修復，downgrade 使用 batch_alter_table ✅
- 017：upgrade 無 IF NOT EXISTS，downgrade 無 IF EXISTS ❌
- 022：upgrade 有 `_has_column()` 檢查 ✅，但 PostgreSQL downgrade 的 `drop_column` 無 IF EXISTS ❌
- 025：upgrade/downgrade 皆有完善的 dialect 判斷和 IF EXISTS/IF NOT EXISTS 保護 ✅
**Status：** PARTIALLY CONFIRMED — 部分 Migration（015、025）已獲完善修復
**修復 Commits：** 015（`a9caf0d8`）、013（`264dedb3`）、025（`23d4d1f3`、`54d8bd44`、`146aa10d`）

### C.5 API HTTP Status/Error
**原始引用：** recommendation.py POST 返回 200，三種 Error 格式  
**當前驗證：** `@router.post("", response_model=RecommendationResponse)` 無 `status_code` 參數，預設 200。Error 格式三種仍並存。  
**Status：** CONFIRMED  

### C.6 Digital Thread 事件鏈
**原始引用：** Patient 事件完全缺失，Variant/Drug 無事件類型  
**當前驗證：** `grep` 在 `services/` 中無 Patient outbox 事件，`adapter.go` 無 Variant/Drug handler。  
**Status：** CONFIRMED  

---

## 八、發現新增或變更的事項

### 新增發現：repository/ 目錄新增檔案
原始報告列出約 21 個 repository 檔案（含 base.py 和 __init__.py），當前目錄有 22 個 `.py` 檔案（其中 `analysis_run_repo.py`、`report_repo.py` 等空類別檔案）與原始架構報告一致。

### 部分修復項目
1. **Migration 015 SQLite 相容性** — commit `a9caf0d8dc0ac1bb42a2ed70fec4bc917b4a6b7d` 修復了 ALTER COLUMN 在 SQLite 的相容性問題
2. **Migration 013 冪等性修復** — commit `264dedb338f84c56ca5b299707e6c2ee79982626` 添加了 idempotent 檢查
3. **KnowGraphGo CLI e2e 測試** — Phase 3D commit 系列添加了端到端測試
4. **`ConsentStatusEnum` 補入 `__init__.__all__`** — 已修復（原始報告的 9 個遺漏 Enum 中至少 1 個已補上）
5. **Migration 025 複合 UNIQUE 約束** — 025 upgrade/downgrade 皆有完善的 dialect 判斷和 IF EXISTS 保護
6. **TreatmentPlanStateMachine 獨立單元測試** — 已新增於 `tests/backend/clinical/test_treatment_plan_engine.py`
7. **OutboxWorker 單元測試** — 已新增於 `tests/unit/test_phase3d_worker.py`

### 本次掃描補充事項
1. **RSK-11 降級爲 FALSE POSITIVE** — 全面掃描 `src/backend/clinical/` 下 30+ 個 `except` 子句，全部皆有 logging 或明確 fallback，無靜默吞沒模式
2. **R-L8 409 Conflict 處理已存在** — `clinical_graph.py:162`、`treatment_plans.py:88`、`upload_vcf.py:392` 共 3 處 409 處理
3. **R-L9 中英文混合註釋確認** — `src/` 下多個檔案存在中文 docstring、註解、logger 訊息混合使用
4. **Repository 型別註解統計更新** — 15/21 檔案仍缺少 AsyncSession 型別（原始 17/22，略有改善）
5. **Migration 022/025 冪等性評估** — 022 upgrade 有 `_has_column()` 檢查，025 有完整 dialect 判斷和 IF EXISTS 保護

---

## 九、最終統計表（去重後）

| 類別 | 總數 | CONFIRMED | PARTIALLY CONFIRMED | OUTDATED | FALSE POSITIVE |
|------|:---:|:---------:|:-------------------:|:--------:|:------------:|
| **P0 問題** | 1 | 1 | 0 | 0 | 0 |
| **P1 問題** | 15 | 12 | 3 | 0 | 0 |
| **P2 問題** | 12 | 9 | 1 | 2 | 0 |
| **Code Smell** | 7 | 7 | 0 | 0 | 0 |
| **Refactor HIGH** | 0† | 0 | 0 | 0 | 0 |
| **Refactor MEDIUM** | 0† | 0 | 0 | 0 | 0 |
| **Refactor LOW** | 3 | 1 | 1 | 1 | 0 |
| **Risk List** | 1 | 0 | 0 | 0 | 1† |
| **附錄 C** | 1 | 1 | 0 | 0 | 0 |
| **合計** | **40** | **31** | **5** | **3** | **1** |

> † Refactor HIGH 和 MEDIUM 的全部條目已分別計入 P0/P1/P2 問題（作爲問題分類的主要歸屬），故去重後爲 0。
> †† RSK-11 已確認爲 FALSE POSITIVE（誤報），統計表如實反映。

### 佔比分析
- **CONFIRMED（仍成立）**：31 / 40 = **77.5%**
- **PARTIALLY CONFIRMED（部分改善）**：5 / 40 = **12.5%**
- **OUTDATED（已被修復）**：3 / 40 = **7.5%**
- **FALSE POSITIVE（誤報）**：1 / 40 = **2.5%**

### 關鍵結論

1. **多數 Findings（77.5%）仍完全成立**：代碼庫在架構審查後雖有多個 Phase（3C、3D、3E）的功能性提交，但架構層面的核心問題幾乎未被觸及。

2. **P0 問題從 6 項降至 1 項**：經 Severity Calibration Round 2 重新判定後，僅 P0-03（BaseRepository commit 導致事務邊界下沉）保留 P0。其餘 5 項因不滿足 P0 5 條件（資料錯誤、transaction 不一致、graph corruption、production crash、測試/程式證據）而降級：
   - **P0-01**（Domain ORM 耦合）→ P1：架構偏好（DDD purity），非 production blocker
   - **P0-02**（Service→API 反向依賴）→ P1：single lazy import，不造成 production 問題
   - **P0-04**（Outbox Repository 業務邏輯）→ P1 PARTIALLY CONFIRMED：僅 mark_failed 含業務邏輯
   - **P0-05**（Python ID Factory 缺方法）→ P1：Python 端無 runtime 調用
   - **P0-06**（buildProvenance 硬編碼）→ P2 PARTIALLY CONFIRMED：ProvenanceImported 語意正確且 event_type 已補償

3. **PARTIALLY CONFIRMED 增加至 5 項（12.5%）**：反映部分 Finding 已被後續提交部分改善。

4. **少數修復來自 Infrastructure / CI**：Migration SQLite 相容性（015/025）和 KnowGraphGo CLI e2e 測試在 Phase 3D 獲得修復，說明修復集中於基礎設施層而非架構層。

5. **架構重構仍需規劃**：架構評分 65/100 的改善需要對 R-H1（Domain/ORM 分離，40h+）等重大重構進行專項投入，建議在下一階段優先執行。

6. **RSK-11 確認爲 FALSE POSITIVE**：原始審查認爲 Recommendation Engine Exception 靜默吞沒，但實際代碼中 30+ 個 except 子句全部有 logging 或明確 fallback，未發現靜默吞沒模式。此爲本次驗證中唯一誤報項。

---

*驗證完成 — 基於當前代碼庫（git HEAD）與 architecture_review.md（v1.0.1）的逐條對比分析。*
