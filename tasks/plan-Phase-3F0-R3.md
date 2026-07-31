# REVIEW-PHASE3F0-R3 返工計劃

> 依據 `tasks/requirements.md` 附錄 B（REVIEW-PHASE3F0-R3 返工需求）制定。
> 範圍：只制定計劃，不修改 production code。
> 狀態：PLAN ONLY（待審核後執行）。

---

## 0. 目標與範圍

| 項目 | 內容 |
|------|------|
| P0-01 | 移除 `get_db()` 自動 commit；A 類直接寫 db 的 endpoint 改由 Service 管理 transaction；B 類確認 Service 為唯一 owner |
| P1-02 | `variants.py` catch-all except 不再洩漏 `str(e)`；保留 4xx；其餘 log + 固定訊息 + error id |
| 產出 | 新增驗證測試 5 項（P0-01 ×3、P1-02 ×2），紅燈先行 |
| 約束 | 不得在 API 層直接 commit/rollback；Repository 保持 flush-only；不得用 dependency auto-commit 補救；保留原 REVIEW 註解並改為 REVIEW-RESOLVED |

> **數量說明**：需求 B.1 標題稱 A 類「共 13 處」，但表格實際列出 **12 個檔案、21 個寫入 endpoint**（patients 3、specimens 1、sequencing 1、cases 3、case_acl 2、analyses 1、uploads 1、upload_vcf 1、research 1、clinical 4、reports 1、ranking 2）。本計劃以表格為準，全數納入。

---

## 1. 現況盤點（Evidence-Based）

### 1.1 `get_db()` 現況（`src/backend/database/session.py` L7-27）

```python
async def get_db():
    ...
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()   # ← 自動 commit（問題根源）
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

### 1.2 寫入層 commit/rollback 盤點（全 src/backend）

| 層級 | 現況 | 是否合規 |
|------|------|----------|
| `repositories/base.py`（Patient/Case/Specimen/Sequencing/Upload/Variant/AnalysisRun…） | `create/update/delete` 僅 `flush()` | ✅ flush-only |
| `repositories/clinical_decision_repo.py`、`recommendation_repo.py`、`treatment_plan_repo.py`、`tumor_board_repo.py` | 僅 flush（註解明示 service 負責 commit） | ✅ flush-only |
| `repositories/case_acl_repo.py` | `grant_permission/delete_case_permission` 僅 flush | ✅ flush-only |
| **`clinical/decision_thread.py` L202** `DecisionThreadRepository.create_node()` | `await self.db.commit()` | ❌ repo 持有 commit |
| **`reporting/repository.py` L52/L67** `ReportRepository.create/update_status` | `await self.db.commit()` | ❌ repo 持有 commit |
| **`ranking/repository.py` L58** `RankingRunRepository.create` | `await self.db.commit()` | ❌ repo 持有 commit |
| **`reasoning/repository.py` L62/L79** `ReasoningRunRepository.create/update` | `await self.db.commit()` | ❌ repo 持有 commit（不在 R3 範圍，列風險） |
| **`knowledge/repository.py` L82/L93/L124** `KnowledgeRepository.upsert_entity/create_relation` | `await self.db.commit()` | ❌ repo 持有 commit（不在 R3 範圍，列風險） |
| **`database/crud.py` L38/L77/L87/L117/L157/L198/L240** | 各 CRUD 函數內部 commit | ❌ DB 工具層持有 commit（僅 `create_research_paper` 被 production 使用） |
| `services/evidence_ingestion_service.py`、`variant_ingestion_service.py` | try/commit / except rollback | ✅ Service-owned |
| `services/recommendation_service.py` L317、`clinical_decision_service.py` L394、`treatment_plan_service.py` L364/L579/L784、`tumor_board_service.py` L435 | try/commit / except rollback | ✅ Service-owned |
| `services/clinical_graph_event_service.py` L84 | try/commit / except rollback | ✅ Service-owned |
| `auth/service.py` L150/L233/L277 | commit（auth 層） | ✅ 可視為 service |
| `workbench/service.py` L454/L500/L547/L586/L635/L682 | commit（service 層） | ✅ Service-owned |
| `workbench/repository.py`、`reasoning/repository.py` 等其餘 | 詳見 1.4 | 見風險 |

### 1.3 A 類 12 檔案 / 21 endpoint 現況（移除 auto-commit 後全部失效）

| 檔案 | endpoint | 現行寫入路徑 | commit owner 現況 |
|------|----------|--------------|-------------------|
| `api/v1/patients.py` | create/update/delete_patient | `PatientRepository`（flush-only） | 依賴 get_db auto-commit ❌ |
| `api/v1/specimens.py` | create_specimen | `SpecimenRepository`（flush-only） | 依賴 get_db auto-commit ❌ |
| `api/v1/sequencing.py` | create_sequencing_test | `SequencingTestRepository`（flush-only） | 依賴 get_db auto-commit ❌ |
| `api/v1/cases.py` | create_case（repo.create + `CaseACLService.grant_owner` 兩步 flush） | `CancerCaseRepository` + `CaseACLRepository`（皆 flush-only） | 依賴 get_db auto-commit ❌ |
| `api/v1/cases.py` | update_case / delete_case | `CancerCaseRepository`（flush-only） | 依賴 get_db auto-commit ❌ |
| `api/v1/case_acl.py` | grant_case_access / revoke_case_access | `CaseACLService.grant_access/revoke_access`（flush-only） | 依賴 get_db auto-commit ❌ |
| `api/v1/analyses.py` | create_analysis | `AnalysisRunRepository`（flush-only） | 依賴 get_db auto-commit ❌ |
| `api/v1/uploads.py` | create_upload | `UploadedFileRepository`（flush-only） | 依賴 get_db auto-commit ❌ |
| `api/v1/upload_vcf.py` | upload_vcf | `UploadedFileRepository`（flush-only）+ 檔案系統副作用 | 依賴 get_db auto-commit ❌ |
| `api/research.py` | submit_paper | `database/crud.create_research_paper`（**內部 commit**） | repo/工具層 owner ❌ |
| `api/v1/clinical.py` | run_agents / run_consensus / recommend_treatment / analyze_case | `DecisionThreadRepository.create_node`（**內部 commit**）+ Orchestrator | repo 層 owner ❌ |
| `api/v1/reports.py` | create_case_report | `reporting/repository.ReportRepository.create`（**內部 commit**） | repo 層 owner ❌ |
| `api/v1/ranking.py` | rank_variant / rank_case | `EvidenceIngestionService`（commit）+ `ranking/repository.RankingRunRepository.create`（**內部 commit**） | 雙 Service/repo owner ❌ |

### 1.4 B 類 7 檔案（移除 auto-commit 後 Service 即唯一 owner，僅需確認+測試）

| 檔案 | endpoint | Service | Service 已 commit/rollback？ |
|------|----------|---------|------------------------------|
| `api/v1/variants.py` | import_variants | `VariantIngestionService` | ✅ L33/L36 |
| `api/v1/evidence.py` | refresh_evidence | `EvidenceIngestionService` | ✅ L49/L78/L95 |
| `api/v1/clinical_graph.py` | retry_event | `ClinicalGraphEventService` | ✅ L84 |
| `api/v1/treatment_plans.py` | 10 個 POST | `TreatmentPlanService` | ✅ L364/L579/L784 |
| `api/v1/recommendation.py` | create_recommendation | `RecommendationService` | ✅ L317 |
| `api/v1/clinical_decision.py` | create_clinical_decision | `ClinicalDecisionService` | ✅ L394 |
| `api/v1/tumor_board_consensus.py` | create_tumor_board_consensus | `TumorBoardConsensusService` | ✅ L435 |

> B 類不需要改寫入邏輯；但需為其增加「Service 成功只 commit 一次」等驗證測試，並將註解改為 REVIEW-RESOLVED。

### 1.5 `str(e)` 洩漏盤點（P1-02 模式）

除 `variants.py` L76 外，A 類多個檔案同樣有 `except Exception → raise HTTPException(500, detail=str(e))`：
`patients.py` L38、`specimens.py` L54、`sequencing.py` L62、`cases.py` L62、`analyses.py` L49、`uploads.py` L72、`research.py` L104/L136、`reports.py`（間接經 repo 拋出）、`clinical_decision.py`（部分）。本計劃建議在 A 類改造時一併採用 P1-02 安全錯誤模式（見 §4），避免二次返工。

---

## 2. 決策 1：`get_db()` 改造方案

**結論：移除 auto-commit；保留 except 內 rollback（作為清理用途）；保留 finally close。**

```python
async def get_db():
    if async_session_factory is None:
        raise RuntimeError("Database not initialized")
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            # 清理未提交的變更（Service 已 rollback 時為 no-op）；
            # 此 rollback 不影響任何已成功 commit 的 transaction。
            await session.rollback()
            raise
        finally:
            await session.close()
```

理由：
1. **移除 `await session.commit()`**：消除「dependency 層自動 commit」這第二個 transaction owner。成功路徑的 commit 完全交給 Service。
2. **保留 `except: rollback()`**：當 endpoint/Service 拋出異常且尚有未 commit 的 flush 變更時，rollback 清掉 session 的髒狀態，避免 PendingRollbackError 殘留與 session 被後續重用。對已 commit 的事務是 no-op，無副作用。
3. **保留 `finally: close()`**：資源釋放。
4. 保留原 REVIEW 註解內容，狀態改 `REVIEW-RESOLVED`，附 RESOLUTION 說明（見 §7）。

> ⚠️ 依賴提醒：FastAPI 中 dependency（如 `require_case_access`、`verify_case_access`）拋出的 HTTPException 也會觸發 get_db 的 except→rollback。這些是讀操作無髒資料，rollback 為 no-op，行為安全。

---

## 3. 決策 2：A 類改造模式

### 3.1 統一模式：Service 層共用 transaction helper

**結論：方案 C（通用 transaction helper）+ 方案 A（每域薄 Service）混合。** 兩者都位於 `src/backend/services/`（Service 層），不是 API dependency，符合需求約束。

新增 `src/backend/services/base.py`：

```python
"""Service 層共用工具 — 統一 transaction 管理。"""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def run_in_transaction(
    db: AsyncSession,
    operation: Callable[[], Awaitable[Any]],
) -> Any:
    """在單一 transaction 中執行操作：成功 commit 一次；異常 rollback 後 re-raise。

    這是 Service 層的交易包裝，API 層不直接 commit/rollback。
    """
    try:
        result = await operation()
        await db.commit()
        return result
    except Exception:
        await db.rollback()
        raise


class BaseService:
    """薄 Service 基底：持有 session，提供 _run() 交易包裝。"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _run(self, operation: Callable[[], Awaitable[Any]]) -> Any:
        return await run_in_transaction(self.db, operation)
```

- 新增的薄 Service 一律繼承 `BaseService`，寫方法用 `self._run(lambda: self.repo.create(**data))` 或直接 try/except commit/rollback（兩者皆可，建議統一 `_run`）。
- 對「repo 已自行 commit」的檔案（research/reports/ranking/clinical），必須先把該 repo 改為 flush-only，再包 Service（見 3.3）。

### 3.2 每檔案改造方案

| # | 檔案 | 改造方案 | 新增 Service（`src/backend/services/`） | 寫方法 |
|---|------|----------|------------------------------------------|--------|
| A1 | `api/v1/patients.py` | 方案 A（新薄 Service） | `patient_service.py` `PatientService(BaseService)` | `create/update/delete`（包 repo + commit/rollback） |
| A2 | `api/v1/specimens.py` | 方案 A | `specimen_service.py` `SpecimenService` | `create` |
| A3 | `api/v1/sequencing.py` | 方案 A | `sequencing_test_service.py` `SequencingTestService` | `create` |
| A4 | `api/v1/cases.py` | 方案 A | `cancer_case_service.py` `CancerCaseService` | `create`（repo.create + `CaseACLService.grant_owner` 同交易）、`update`、`delete` |
| A5 | `api/v1/case_acl.py` | 方案 A（包既有 auth `CaseACLService`） | `case_access_service.py` `CaseAccessService` | `grant`、`revoke`（調 `CaseACLService` 後 commit；`PermissionDeniedError` 也 rollback 後 re-raise，由 endpoint 轉 403） |
| A6 | `api/v1/analyses.py` | 方案 A | `analysis_run_service.py` `AnalysisRunService` | `create`（含 `status=PENDING` 設定） |
| A7 | `api/v1/uploads.py` | 方案 A | `upload_service.py` `UploadService` | `create` |
| A8 | `api/v1/upload_vcf.py` | 方案 A（僅包 DB 寫入；檔案系統保持 endpoint） | `vcf_upload_service.py` `VCFUploadService` | `create_upload_metadata(**data)`（repo.create + commit/rollback；失敗時 endpoint 清理 storage_path，沿用現有邏輯） |
| A9 | `api/research.py` | 方案 A + crud 改 flush-only | `research_paper_service.py` `ResearchPaperService` | `submit(**data)`（調 `create_research_paper` 或直接建 `ResearchPaper`，commit/rollback） |
| A10 | `api/v1/clinical.py` | 方案 A + decision_thread 改 flush-only | `clinical_pipeline_service.py` `ClinicalPipelineService` | `run_agents` / `run_consensus` / `recommend_treatment` / `analyze_case`（現有流程整批包入，成功 commit 一次、失敗 rollback） |
| A11 | `api/v1/reports.py` | 方案 A + reporting repo 改 flush-only | `report_service.py` `ReportService` | `create(...)`（調 `ReportRepository.create` 後 commit/rollback） |
| A12 | `api/v1/ranking.py` | 方案 A + ranking repo 改 flush-only | `drug_ranking_service.py` `DrugRankingService` | `persist_run(result_dict)`（調 `RankingRunRepository.create` 後 commit/rollback） |

每檔案的 endpoint 改造模式（一致）：

```python
# 改造後 endpoint 樣板
@router.post("", response_model=..., status_code=201)
async def create_xxx(body: XxxCreate, user=Depends(require_auth),
                     service: XxxService = Depends(get_xxx_service)):
    try:
        result = await service.create(**body.model_dump(exclude_none=True))
        return XxxResponse.model_validate(result)
    except HTTPException:
        raise  # 4xx 直接透傳
    except Exception:
        logger.exception("Failed to create xxx")
        raise HTTPException(status_code=500, detail={"error": "internal_error", "message": "Internal server error"})
```

- 在 `api/v1/deps.py` 新增 `get_xxx_service(db: AsyncSession = Depends(get_db))` 依賴（**注意：此依賴只負責注入 Service 實例，不含任何 commit/rollback**），或在 endpoint 內直接 `XxxService(db)`（與現有 B 類 endpoint 風格一致，如 `variants.py` 的 `VariantIngestionService(db)`）。**推薦後者**，與 B 類保持一致、減少 deps 膨脹。
- 寫入 endpoint 統一加 `request: Request` 參數以支援 error_id（見 §4）。

### 3.3 支援性 repository 改 flush-only（必要前置）

| 檔案 | 變更 | 受影響調用者 |
|------|------|--------------|
| `clinical/decision_thread.py` L202 `create_node` | 移除 `await self.db.commit()`，保留 flush + refresh | `api/v1/clinical.py`（經 A10 的 `ClinicalPipelineService` 包 commit）；`tests/unit/test_decision_thread.py`（測試需同步調整，見 §6.4） |
| `reporting/repository.py` L52/L67 | `create`/`update_status` 移除 commit | `api/v1/reports.py`（經 A11）；grep 確認 `update_status` 無其他 production 調用者 |
| `ranking/repository.py` L58 | `create` 移除 commit | `api/v1/ranking.py`（經 A12）；`tests/test_drug_ranking.py`（檢查並調整） |
| `database/crud.py` `create_research_paper` L240 | 移除 commit（改 flush-only） | `api/research.py`（經 A9）；`tests/test_database.py`（檢查並調整） |

> `reasoning/repository.py`、`knowledge/repository.py` 的 repo 層 commit **不在 R3 範圍**（其 endpoint 可自行 commit 而不受移除 auto-commit 影響），列入風險 §8。

### 3.4 B 類確認事項（不改造寫入邏輯）

- 逐一確認 B 類 Service 的 commit/rollback 完整（已由 §1.4 佐證）。
- 抽查 `clinical_decision_service` / `tumor_board_service` / `recommendation_service` / `treatment_plan_service` 內部**不直接使用** `DecisionThreadRepository`（grep 確認 production 僅 `clinical.py` 使用），避免 B 類內藏 repo 層 commit owner。
- B 類 endpoint 的 catch-all 錯誤處理若洩漏 `str(e)`，建議比照 §4 修正（列入 T2.2）。

---

## 4. 決策 3：P1-02 錯誤處理模式（含 A 類推廣）

### 4.1 `variants.py` import_variants（P1-02 本體）

```python
@router.post("/import", response_model=list[VariantResponse], status_code=201)
async def import_variants(
    body: VariantImportBatch,
    user: UserModel = Depends(require_auth),
    repo: VariantRepository = Depends(get_variant_repo),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    # ... 既有 4xx 校驗（_resolve_sequencing_test_case_id 抛 HTTPException 等）不變
    try:
        items_data = [item.model_dump(exclude_none=True) for item in body.items]
        service = VariantIngestionService(db)
        variants = await service.bulk_create_variants(items_data)
        return [VariantResponse.model_validate(v) for v in variants]
    except HTTPException:
        raise  # 合法 4xx/業務錯誤透傳，不轉 500
    except Exception:
        error_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())
        logger.exception("Failed to import variants [error_id=%s]", error_id)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "error_id": error_id,
                    "message": "Internal server error"},
        )
```

- `RequestIDMiddleware` 已在 response header 寫入 `X-Request-ID`；endpoint 從 `request.state` 或 `request.headers["X-Request-ID"]` 取同一個 id 放入 body，達成可追蹤。
- `logger.exception` 記錄完整 server log（含原始例外），對外只回傳固定訊息。

### 4.2 A 類推廣（建議隨 A 類改造一併採用）

所有 A 類寫入 endpoint 的 catch-all 改為同一模式：`except HTTPException: raise`；`except Exception: logger.exception + HTTPException(500, fixed_detail_with_error_id)`。避免第二次返工（Reviewer 已明確在意此問題）。

---

## 5. 任務清單（含依賴）

> 依賴：批次 0 →（批次 1 平行/串行）→ 批次 2 → 批次 3 → 批次 4。
> 批次 1 內各檔案互不依賴，可由不同子代理平行處理；但每個檔案需先完成該檔案的 Service 才改 endpoint（同檔案內串行）。

### 批次 0：基礎改造（前置）

| 任務 | 檔案 | 修改內容 | 依賴 |
|------|------|----------|------|
| T0.1 | `src/backend/database/session.py` | 移除 `await session.commit()`；保留 except rollback + finally close；REVIEW 註解改 REVIEW-RESOLVED 附 RESOLUTION | 無 |
| T0.2 | `src/backend/services/base.py`（新檔） | 新增 `run_in_transaction` + `BaseService` | 無 |

### 批次 1：A 類改造（每檔案：新 Service + endpoint 改用 + 錯誤處理安全化）

| 任務 | 檔案 | 修改內容 | 依賴 |
|------|------|----------|------|
| T1.1 | `services/patient_service.py`（新）+ `api/v1/patients.py` | 新 `PatientService`（create/update/delete，commit/rollback）；endpoint 改用；錯誤訊息安全化 | T0.2 |
| T1.2 | `services/specimen_service.py`（新）+ `api/v1/specimens.py` | 新 `SpecimenService.create`；endpoint 改用；安全化 | T0.2 |
| T1.3 | `services/sequencing_test_service.py`（新）+ `api/v1/sequencing.py` | 新 `SequencingTestService.create`；endpoint 改用；安全化 | T0.2 |
| T1.4 | `services/cancer_case_service.py`（新）+ `api/v1/cases.py` | 新 `CancerCaseService`（create 含 grant_owner 同交易 / update / delete）；endpoint 改用；安全化 | T0.2 |
| T1.5 | `services/case_access_service.py`（新）+ `api/v1/case_acl.py` | 新 `CaseAccessService`（grant/revoke 包 `CaseACLService` + commit/rollback）；endpoint 改用；403 邏輯保留 | T0.2 |
| T1.6 | `services/analysis_run_service.py`（新）+ `api/v1/analyses.py` | 新 `AnalysisRunService.create`（含 status=PENDING）；endpoint 改用；安全化 | T0.2 |
| T1.7 | `services/upload_service.py`（新）+ `api/v1/uploads.py` | 新 `UploadService.create`；endpoint 改用；安全化 | T0.2 |
| T1.8 | `services/vcf_upload_service.py`（新）+ `api/v1/upload_vcf.py` | 新 `VCFUploadService.create_upload_metadata`（僅 DB 寫入）；endpoint 在檔案驗證後調用；storage cleanup 邏輯保留 | T0.2 |
| T1.9 | `services/research_paper_service.py`（新）+ `api/research.py` + `database/crud.py` | 新 `ResearchPaperService.submit`；crud `create_research_paper` 改 flush-only；endpoint 改用；安全化 | T0.2 |
| T1.10 | `services/clinical_pipeline_service.py`（新）+ `api/v1/clinical.py` + `clinical/decision_thread.py` | 新 `ClinicalPipelineService`（4 個流程方法，各包一次 commit/rollback）；`DecisionThreadRepository.create_node` 改 flush-only；endpoint 改薄（讀取、驗證、調 Service） | T0.2 |
| T1.11 | `services/report_service.py`（新）+ `api/v1/reports.py` + `reporting/repository.py` | 新 `ReportService.create`；`ReportRepository.create/update_status` 改 flush-only；endpoint 改用 | T0.2 |
| T1.12 | `services/drug_ranking_service.py`（新）+ `api/v1/ranking.py` + `ranking/repository.py` | 新 `DrugRankingService.persist_run`；`RankingRunRepository.create` 改 flush-only；endpoint 改用 | T0.2 |

### 批次 2：P1-02

| 任務 | 檔案 | 修改內容 | 依賴 |
|------|------|----------|------|
| T2.1 | `api/v1/variants.py` | 依 §4.1 改造 except 區塊；REVIEW 註解改 REVIEW-RESOLVED 附 RESOLUTION | 無 |
| T2.2 | A 類/B 類其他洩漏 `str(e)` 的 catch-all | 依 §4.2 安全化（可隨批次 1 各任務完成；此為合併清單） | 批次 1 |
| T2.3 | `api/v1/evidence.py` 等 B 類（如發現洩漏） | 依 §4 模式修正（範圍內僅 variants.py 必須，其餘視審查決定） | 無 |

### 批次 3：測試（紅燈先行）

| 任務 | 檔案 | 修改內容 | 依賴 |
|------|------|----------|------|
| T3.1 | `tests/backend/atomicity/test_phase3f0_r3_p0_transaction_boundary.py`（新） | P0-01 驗證 3 項測試（設計見 §6.1） | 無（先寫，紅燈） |
| T3.2 | `tests/backend/api/test_phase3f0_r3_p1_variants_errors.py`（新） | P1-02 驗證 2 項測試（設計見 §6.2） | 無（先寫，紅燈） |
| T3.3 | `tests/unit/test_decision_thread.py`、`tests/test_database.py`、`tests/test_drug_ranking.py`、`tests/test_clinical_reports.py`、`tests/test_clinical_decision_thread.py` | 調整受 repo 改 flush-only 影響的既有測試（手動 commit 後驗證） | 批次 1 |

### 批次 4：驗證與收尾

| 任務 | 內容 | 依賴 |
|------|------|------|
| T4.1 | 紅燈驗證：先跑 T3.1/T3.2 → 確認 FAIL（現行 get_db auto-commit / str(e) 洩漏） | T3.1/T3.2 |
| T4.2 | 綠燈驗證：完成批次 0-2 後再跑 T3.1/T3.2 → 全綠 | 批次 0-2 |
| T4.3 | 完整測試套件回歸：`pytest`（sqlite）、`pytest -m pg`（PostgreSQL，若有 DATABASE_URL） | 全部 |
| T4.4 | REVIEW 註解改 REVIEW-RESOLVED（T0.1、T2.1 + A 類已處理處），附 RESOLUTION | 批次 0-2 |
| T4.5 | Step 6 需求回歸 + Step 7 REVIEWER 評分（由 parent/executor 執行） | T4.1-T4.3 |
| T4.6 | Commit / Push | T4.5 |

---

## 6. 測試計劃

### 6.1 P0-01 驗證 3 項測試（`tests/backend/atomicity/test_phase3f0_r3_p0_transaction_boundary.py`）

> 使用現有測試基建：`sqlite+aiosqlite`、`Base.metadata.create_all`、`async_sessionmaker`（參考 `tests/backend/atomicity/test_atomicity_flow_a.py`）；需要 API 的用 `create_app()` + `TestClient` + `settings.DATABASE_URL`（參考 `tests/test_api_v1.py`）。

**T1（驗證 1）Service 成功只 commit 一次**
- 真實 sqlite session；對 session 掛 wrapper/spy 記錄 `commit()`/`rollback()` 調用次數（或用 `event.listen(session.sync_session, "after_commit")` 計數）。
- 情境 A（B 類）：`VariantIngestionService(db).bulk_create_variants([...])` 成功後：
  - 斷言 `db.commit()` 恰 1 次；`db.rollback()` 0 次；fresh session 中資料存在。
- 情境 B（A 類新 Service）：`PatientService(db).create(sex="M", consent_status="granted")` 成功後：
  - 斷言 commit 恰 1 次；資料存在。
- 情境 C（get_db 不再 commit）：直接驅動 `get_db()` 生成器（先 `init_db("sqlite+aiosqlite://")`），`yield` 後正常返回，斷言 session 未被 commit（用 spy session）。

**T2（驗證 2）Service 後段失敗完整 rollback**
- 真實 sqlite session；用 `CancerCaseService.create`（兩步：repo.create case + acl grant_owner）：
  - mock/patch `CaseACLService.grant_owner` 抛 `Exception`（模擬後段失敗）。
  - 斷言異常被 re-raise、`db.rollback()` 被調用、fresh session 中 case 不存在（count == 0）。
- 另測 `VariantIngestionService`：mock `repo.bulk_create` 抛 IntegrityError，斷言無部分資料。

**T3（驗證 3）endpoint 在 Service 返回後發生例外時，不會留下部分提交資料**
- 情境 A（get_db 層）：驅動 `get_db()` 生成器，`yield session` 後 `await agen.athrow(RuntimeError)`，斷言 `session.rollback()` 被調用、`commit()` 未被調用。
- 情境 B（endpoint 層，驗證無隱式 auto-commit）：`create_app()` + `app.dependency_overrides` 覆寫目標 endpoint 的 Service，讓其「repo.create 成功但返回後抛 HTTPException(500)」；透過 TestClient 調用，斷言 response 500、fresh DB session 查無該資料（證明沒有被 get_db 隱式提交）。
  - 具體可選 `POST /api/v1/patients`（覆寫 `PatientService.create`）。

### 6.2 P1-02 驗證 2 項測試（`tests/backend/api/test_phase3f0_r3_p1_variants_errors.py`）

> `create_app()` + `TestClient` + sqlite，註冊/登入取 token（參考 `tests/test_api_v1.py` / `tests/integration/test_case_acl_http.py`）。

**T4（驗證 1）內部 DB 例外文字不會出現在 response body**
- 覆寫 `VariantIngestionService`（或 mock repo），讓 `bulk_create_variants` 抛 `IntegrityError`（例外文字含敏感片段，如 `UNIQUE constraint failed: variants.hgvs_notation`）。
- 斷言：
  - response.status_code == 500；
  - response body **不包含** 敏感片段（`"UNIQUE constraint"`、`"variants"` 表名、驅動字樣等）；
  - response body 含 `error_id` 且與 `X-Request-ID` header 一致（或非空）；
  - `X-Request-ID` header 存在。

**T5（驗證 2）合法 4xx 業務錯誤不會被轉換為 500**
- 走既有 4xx 校驗路徑：`POST /api/v1/variants/import` 帶無效 `sequencing_test_id`（`_resolve_sequencing_test_case_id` 抛 400）。
- 斷言 response.status_code == 400（不是 500），錯誤訊息保留。

### 6.3 紅燈先行流程（強制）

1. 先寫 T3.1 / T3.2 全部測試，**在批次 0-2 未動工前執行** → 預期：
   - T1 情境 C FAIL（get_db 仍 auto-commit）；
   - T3 FAIL（資料被隱式提交 / get_db 有 commit）；
   - T4 FAIL（response body 含 `str(e)`）。
   - T2 目前可能 PASS（repo 已 flush-only），但作為回歸保護。
2. 記錄紅燈輸出作為「問題存在」證據。
3. 完成批次 0-2 後再執行 → 全綠。
4. 若個別紅燈測試涉及未納入範圍的端點，需在計劃執行中檢討範圍並回報 parent。

### 6.4 既有測試同步調整

- `tests/unit/test_decision_thread.py`：`create_node` 改 flush-only 後，依賴「create_node 後資料已持久化」的測試需在驗證前手動 `session.commit()`。
- `tests/test_database.py`：`crud.create_research_paper` 改 flush-only 後，相關測試需手動 commit 或改用新 `ResearchPaperService`。
- `tests/test_drug_ranking.py`、`tests/test_clinical_reports.py`：repo 改 flush-only 後，以 repo 直調的測試需手動 commit（或改走新 Service）。

---

## 7. REVIEW 註解處理

- 保留原 REVIEW 註解區塊文字不刪除；狀態字樣由 `/ OPEN` 改為 `/ REVIEW-RESOLVED`，並在原註解下方附加：

```
# RESOLUTION (REVIEW-PHASE3F0-R3-P0-01): get_db() 已移除自動 commit；
# 所有 A 類寫入 endpoint 已改由 Service 層統一 commit/rollback（見 tasks/plan-Phase-3F0-R3.md）；
# B 類 Service 確認為唯一 transaction owner；3 項驗證測試通過（test_phase3f0_r3_p0_transaction_boundary.py）。
```

（P1-02 依樣辦理。）

---

## 8. 風險與注意事項

| # | 風險 | 影響 | 緩解 |
|---|------|------|------|
| R1 | **隱藏依賴 auto-commit 的寫入端點**：除 A/B 類外，需全量複查 `Depends(get_db)` 的 POST/PUT/PATCH/DELETE endpoint（`workbench.py`、`auth/api.py` 已確認走 service；`knowledge.py`、`reasoning.py` 走自行 commit 的 repo） | 移除 auto-commit 後寫入丟失 | 執行前用 grep 全量清單逐檔確認；將非 service 的直接寫入納入改造或至少標註 |
| R2 | **repo 層 commit 改 flush-only 的連鎖影響**：`decision_thread`、`reporting`、`ranking`、`crud` | 其他調用者（含測試）依賴原 commit 行為而壞 | 全量 grep 調用者；同步調整測試（T3.3）；跑完整套件 |
| R3 | **臨床 pipeline 原子性行為改變**：`clinical.py` 4 個 POST 從「每節點獨立 commit」變「整批 commit」，失敗全回滾 | 現有測試若斷言部分節點已保存會 FAIL | 更新測試；在 RESOLUTION 註明行為變更為 Phase 3F-0 預期 |
| R4 | **ranking.py 請求內雙 transaction**：`EvidenceIngestionService` commit + `DrugRankingService` commit | 非雙 owner 衝突，但非單一原子 | 維持現狀（各自原子、互不衝突）；列入 RESOLUTION 說明；如需全原子則需改 `EvidenceIngestionService` 支援 deferred commit（範圍外） |
| R5 | **`reasoning/repository.py`、`knowledge/repository.py` 的 repo 層 commit**：不在 R3 範圍 | 違反 Phase 3F-0 flush-only 原則（既有 TechDebt） | 不阻擋 R3；列為後續批次（Phase 4 前置） |
| R6 | **A 類多檔案同時改動**：12 個檔案 + 11 個新 Service + 3 個 repo + 2 個測試檔案，檔案數約 28 | 回歸面大 | 每檔案獨立批次驗證；批次 1 內任務可平行但需各自跑該域測試 |
| R7 | **測試環境差異**：sqlite vs PostgreSQL 的 rollback/commit 語義差異 | 部分行為僅在 PG 顯現 | 若有 DATABASE_URL 則跑 `-m pg`；無則 sqlite 全量 + 手動說明 |
| R8 | **`get_db` 被其他非 HTTP 消費者使用**（scripts/cli/背景任務） | 移除 auto-commit 影響非 API 寫入 | 全量 grep `get_db`（已確認僅 api/auth/deps 使用）；非 API 寫入若依賴 get_db 需改用 Service |

---

## 9. 完成條件（對照需求 B.3）

- [ ] P0-01：`get_db()` 移除 auto commit；A 類 12 檔案 / 21 endpoint 全部改由 Service 管理 transaction；B 類確認 Service 唯一 owner
- [ ] P1-02：`variants.py` 錯誤處理改造（保留 4xx、固定訊息 + error_id、完整 log）
- [ ] 5 項驗證測試新增（P0-01 ×3、P1-02 ×2），紅燈確認 FAIL → 綠燈全部通過
- [ ] REVIEW 註解改為 REVIEW-RESOLVED（保留原文，附 RESOLUTION）
- [ ] 完整測試套件（sqlite 全量 + PG 若有）無回歸
- [ ] Step 6 需求回歸 + Step 7 REVIEWER 評分 ≥90
- [ ] Commit / Push
