# Phase 3A Final Fix — 現狀摘要

## 1. 需求現狀（tasks/requirements.md）

Phase 3A Hardening 章節列出 10 項正式實作要求及 8 項測試要求：

### 正式實作要求（10 項）

| # | 要求 | 狀態 | 備註 |
|---|------|------|------|
| 1 | RecommendationModel（SQLAlchemy ORM） | ✅ 完成 | `domain/recommendation.py` 中定義，含 id, patient_id, trace_id, engine_version, status, request_payload, result_payload, report_html, created_by, created_at, updated_at |
| 2 | Calculation Trace Persistence（RecommendationTraceModel + TraceStepModel） | ⚠️ PARTIAL | Model 已建立但缺少 plan 中要求的欄位（`RecommendationTraceModel` 缺少 patient_id, status, started_at, completed_at；`TraceStepModel` 缺少 duration_ms） |
| 3 | Migration（Alembic） | ✅ 完成 | `migrations/versions/017_phase3a_recommendation_tables.py` 可 upgrade/downgrade |
| 4 | RecommendationRepository | ✅ 完成 | `repositories/recommendation_repo.py` 含 create, get_by_id, get_by_trace_id, list_by_patient_id |
| 5 | RecommendationService | ⚠️ PARTIAL | 有完整 pipeline 但 persistence failure 仍回傳成功（P0-1 根因） |
| 6 | API（POST/GET 全 DB 操作） | ⚠️ PARTIAL | API 路由已改為呼叫 Service 但底層 Service 在 persist 失敗時仍回 200 |
| 7 | Restart Recovery Test | ❌ FAIL | 測試使用 SQLite 檔案 + 直接 Repository 呼叫，非真實 API/App/Postgres 鏈路（P0-3 根因） |
| 8 | Frontend Router | ✅ 完成 | `App.tsx` 含 `/recommendation` route |
| 9 | Frontend API Integration | ✅ 完成 | `RecommendationPage.tsx` 呼叫正式 API |
| 10 | HTTP Error Security | ✅ 完成 | `logger.exception()` + 固定 error code + generic message |

### 測試要求（8 項，對應 Batch E1–E8）

| # | 測試 | 狀態 | 備註 |
|---|------|------|------|
| E1 | Backend Model Tests | ✅ 內含在 service test | 無獨立 model test 檔案 |
| E2 | Repository Tests | ✅ 內含在 service test | 無獨立 repository test 檔案 |
| E3 | Service Tests | ✅ `test_recommendation_service.py` | 但大量使用 mock，非完整端到端 |
| E4 | API Integration Tests | ⚠️ PARTIAL | `test_api_recommendation.py` 使用 TestClient + in-memory SQLite，但 demo mode 下證據收集常失敗 |
| E5 | Restart Recovery Test | ❌ FAIL | 使用 SQLite + 直接 Repository 操作，非真正 App Restart |
| E6 | Trace Persistence Test | ⚠️ PARTIAL | 使用 SQLite + 自行填資料，未經實際 pipeline |
| E7 | Frontend Route Test | ✅ | `test/RecommendationPage.test.tsx` |
| E8 | Migration Tests | ✅ | `test_migration.py` 含 017 測試 |

---

## 2. 計劃現狀（tasks/plan-phase3a-hardening.md）

任務清單與完成狀態（對照 Batch）：

| Batch | 任務 | 狀態 | 實際檔案 |
|-------|------|------|---------|
| A1 | RecommendationModel | ✅ | `domain/recommendation.py` |
| A2 | RecommendationTraceModel + TraceStepModel | ⚠️ 欄位短少 | `domain/recommendation.py` |
| A3 | Alembic Migration | ✅ | `migrations/versions/017_phase3a_recommendation_tables.py` |
| B1 | RecommendationRepository | ✅ | `repositories/recommendation_repo.py` |
| B2 | TraceRepository | ✅ | 同上檔案 |
| B3 | RecommendationService | ⚠️ P0-1 bug | `services/recommendation_service.py` |
| C1 | API 改為全 Database | ⚠️ 不完全 | `api/v1/recommendation.py` — Service 層 persist failure 不阻斷 |
| C2 | HTTP 500 Error Security | ✅ | 路由層已實作 |
| C3 | Router 清理 | ✅ | 無 `_recommendations` dict 殘留 |
| D1 | App.tsx Route | ✅ | |
| D2 | Navigation/Menu | ✅ | |
| D3 | API Client | ✅ | |
| E1–E8 | Tests | 見上表 | |
| F1 | 清理 artefacts | ⚠️ 零位元檔案殘留 | |
| F2 | requirements.md 歷史 | ✅ | |

---

## 3. REVIEWER 報告摘要（review_Phase-3A-Hardening_0.md）

### 評分明細

| 項目 | 分數 | 最高 |
|------|------|------|
| 完整性 | 22 | 25 |
| 正確性 | 24 | 25 |
| 可維護性 | 22 | 25 |
| 測試與驗證 | 23 | 25 |
| **總分** | **91** | **100** — 合格 ✅ |

### 檢查清單

- 是否可執行：YES
- 是否有錯誤：YES（無錯誤）
- 是否滿足需求條列：YES
- 是否有測試：YES

### 缺失項目（REVIEWER 指出，但分數未反映的深層問題）

REVIEWER 報告有 **誤判** 情形：

1. **Database Persistence：✅** → 但實際上 persistence failure 不回報錯誤（P0-1）。
2. **Restart Recovery：✅** → 但測試使用 SQLite 檔案 + 直接 Repository，非完整 API/App/Postgres 鏈路（P0-3）。
3. **Trace Persistence：✅** → 但 `TraceManager` 仍在記憶體中運作，TraceStep 的 `duration_ms` 等欄位未持久化。

REVIEWER 的評分基於**檔案存在**而非**品質驗證**，導致三個 P0 問題被忽略。

---

## 4. 程式碼現狀

### 4.1 recommendation_service.py

#### Persistence 錯誤處理邏輯（P0-1 根因）

```python
# 第 254-274 行
try:
    await self._persist_recommendation(...)
    await self._db.commit()
except Exception:
    await self._db.rollback()
    logger.exception("Failed to persist recommendation %s — rolled back.")
    # Return the in-memory result even if persistence fails
    # (the pipeline result is still valid for the caller)

return response  # ← 即使 DB 寫入失敗，仍回傳 200
```

**問題**：persist/commit 失敗時，Service 仍回傳 `response`（in-memory 結果），API 層收到後回傳 200 OK。Client 以為資料已保存，但 DB 中沒有任何記錄。

#### Try/Except 區塊定位

| 區塊 | 行號 | 例外類型 | 行為 |
|------|------|---------|------|
| Pipeline execution | 159-164 | Exception → RuntimeError | 正確拋出 |
| Pipeline error status | 167-171 | 條件判斷 → RuntimeError | 正確拋出 |
| Empty aggregated | 174-178 | 條件判斷 → ValueError | 正確拋出 |
| No rankings | 182-184 | 條件判斷 → ValueError | 正確拋出 |
| HTML report | 251 | Exception → log only | ✅ 非致命正確 |
| **Persistence + commit** | **255-274** | **Exception → rollback + 仍回傳 response** | **❌ P0-1** |

### 4.2 recommendation.py (API)

#### 例外處理與 HTTP 映射

| 路由 | 行號 | 例外來源 | HTTP 狀態 | Response Body |
|------|------|---------|-----------|---------------|
| POST | 161-165 | ValueError（無 evidence/無 ranking） | 422 | `{"error": "validation_failed", "message": ...}` |
| POST | 176-184 | Exception（含 RuntimeError） | 500 | `{"error": "INTERNAL_ERROR", "message": "Recommendation processing failed."}` |
| GET | 214-224 | Exception | 500 | `{"error": "INTERNAL_ERROR", ...}` |
| GET | 226-237 | model is None | 404 | `{"error": "not_found", "message": ...}` |

**問題**：API 層的例外處理**正確**，但 Service 層在 persistence failure 時**沒有拋出例外**，所以 API 層永遠不會觸發 500。這導致 Client 永遠收到 200。

### 4.3 recommendation_repo.py

#### Repository 方法列表

**RecommendationRepository**:
- `create(recommendation: RecommendationModel) → RecommendationModel` — `db.add()`
- `get_by_id(recommendation_id: str) → Optional[RecommendationModel]`
- `get_by_trace_id(trace_id: str) → Optional[RecommendationModel]`
- `list_by_patient_id(patient_id: str, limit: int = 20) → list[RecommendationModel]`

**TraceRepository**:
- `create_trace(trace: RecommendationTraceModel) → RecommendationTraceModel`
- `get_trace_by_recommendation_id(recommendation_id: str) → Optional[RecommendationTraceModel]`
- `get_trace_by_trace_id(trace_id: str) → Optional[RecommendationTraceModel]`
- `create_step(step: RecommendationTraceStepModel) → RecommendationTraceStepModel`
- `get_steps_by_trace_id(trace_id: str) → list[RecommendationTraceStepModel]`

**注意**：`BaseRepository`（`repositories/base.py`）有自己的 `create()` 方法（含 `commit` + `refresh`），但 `RecommendationRepository.create()` 覆寫為不 commit（僅 `db.add()`），符合 Service 層管理 transaction 的設計。

### 4.4 domain/recommendation.py

#### Domain Model 結構

**RecommendationModel**（`domain_recommendations` 表）：
- `id` (CompatUUID PK)
- `recommendation_id` (String 64, unique, index)
- `patient_id` (CompatUUID FK→domain_patients.id)
- `case_id` (CompatUUID FK→domain_cancer_cases.id, nullable)
- `trace_id` (String 64, nullable, index)
- `engine_version` (String 32)
- `status` (String 32)
- `request_payload` (JSON, nullable)
- `result_payload` (JSON, nullable)
- `report_html` (Text, nullable)
- `created_by` (CompatUUID FK→domain_users.id, nullable)
- `created_at` (DateTime)
- `updated_at` (DateTime)
- `traces` → relationship(RecommendationTraceModel, cascade delete)

**RecommendationTraceModel**（`domain_recommendation_traces` 表）：
- `id` (CompatUUID PK)
- `trace_id` (String 64, unique, index)
- `recommendation_id` (CompatUUID FK→domain_recommendations.id, nullable)
- `created_at` (DateTime)
- `recommendation` → relationship(RecommendationModel)
- `steps` → relationship(RecommendationTraceStepModel, cascade delete)

**⚠️ 缺少欄位**（對照 plan-phase3a-hardening.md 設計規範）：
- `patient_id` (String 64, NOT NULL) — 缺少
- `status` (String 16, "running"/"completed"/"failed") — 缺少
- `started_at` (DateTime, NOT NULL) — 缺少
- `completed_at` (DateTime, nullable) — 缺少

**RecommendationTraceStepModel**（`domain_recommendation_trace_steps` 表）：
- `id` (CompatUUID PK)
- `trace_id` (CompatUUID FK→domain_recommendation_traces.id)
- `step_order` (Integer)
- `step_type` (String 64)
- `input_summary` (JSON, nullable)
- `output_summary` (JSON, nullable)
- `evidence_references` (JSON, nullable)
- `weight` (Float, nullable)
- `score` (Float, nullable)
- `rank` (Integer, nullable)
- `status` (String 32)
- `created_at` (DateTime)
- `trace` → relationship(RecommendationTraceModel)

**⚠️ 缺少欄位**（對照 plan 設計規範 + TraceStep Pydantic model）：
- `step_name` (String 64) — 缺少（plan 有但 model 沒有，不過 service 也從不設定此欄位）
- `duration_ms` (Float, nullable) — 缺少（TraceStep 有此欄位但 model 無對應欄位）
- `timestamp` (DateTime) — 有 `created_at` 但 TraceStep 使用 `timestamp`

### 4.5 calculation_trace.py

#### TraceManager / TraceStep 寫入邏輯

**TraceStep**（Pydantic BaseModel，僅在記憶體中）：
```python
class TraceStep(BaseModel):
    step_name: str
    step_type: str          # "input" | "evidence" | "score" | "recommendation" | "output"
    input_data: dict        # 寫入 DB 時對應 input_summary
    output_data: dict       # 寫入 DB 時對應 output_summary
    timestamp: datetime     # 預設 datetime.now(UTC)
    duration_ms: float|None # 預設 None → 但 model 無此欄位
    parent_trace_id: str|None
```

**TraceManager**：完全在記憶體中運作（`self._traces: dict[str, CalculationTrace] = {}`）。

**Service 中的 Trace 持久化流程**：
1. `TraceManager.start_trace()` → 記憶體中建立 CalculationTrace
2. Pipeline 執行時，各 component 透過 `trace_manager.add_step()` 記錄步驟
3. `_persist_recommendation()` 從 `trace_manager.get_trace(trace_id)` 取出
4. 建立 `RecommendationTraceModel`（只有 trace_id + recommendation_id）
5. 對每個 step 建立 `RecommendationTraceStepModel`（只存部分欄位）

**目前寫入的欄位**（在 `_persist_recommendation` 中）：
| TraceStep 欄位 | DB 欄位 | 有寫入？ |
|---------------|---------|---------|
| step_name | ❌ 無對應 | ❌ |
| step_type | step_type | ✅ |
| input_data | input_summary | ✅ |
| output_data | output_summary | ✅ |
| timestamp | ❌ 無對應（created_at 是 auto） | ❌ |
| duration_ms | ❌ 無對應 | ❌ |
| parent_trace_id | ❌ 無對應 | ❌ |

**缺少的 Trace 層級欄位**：
| 計劃要求 | 實際 DB 欄位 | 有寫入？ |
|---------|-------------|---------|
| patient_id | ❌ 無此欄位 | ❌ |
| status（running/completed/failed） | ❌ 無此欄位 | ❌ |
| started_at | ❌ 無此欄位 | ❌ |
| completed_at | ❌ 無此欄位 | ❌ |

---

## 5. 測試現狀

### 5.1 test_restart_recovery.py

**測試方式**：
- 使用 **SQLite 檔案資料庫**（`sqlite+aiosqlite:///test_e5_restart_recovery.db`）
- 使用獨立 Engine + Session，不經過 FastAPI app
- 使用 **直接 Repository 操作** 手動建立資料（`_persist_chain_sync` helper）
- 測試資料是**自行構造**的，非經由實際 recommendation pipeline 產出
- 沒有 TestClient、沒有 API 呼叫、沒有認證流程
- 三個測試：data_intact, trace_references, multiple_records

**不足之處**（P0-3 根因）：
1. ❌ **非真正 App Restart**：沒有建立新的 `create_app()`，沒有通過 API
2. ❌ **非 Postgres**：使用 SQLite 而非 Postgres，無法驗證 FK 約束、transaction 隔離等
3. ❌ **非完整鏈路**：沒有經過 RecommendationService → Pipeline → Repository 路徑
4. ❌ **手動造資料**：直接建立 Model 實例而不經過 pipeline，無法驗證 trace step 的正確性

### 5.2 test_trace_persistence.py

**測試方式**：
- 使用 **SQLite 檔案資料庫**（`test_e6_trace_persistence.db`）
- `_build_full_chain()` 手動建立完整的 Recommendation + Trace + 5 個 Steps
- 測試 chain restoration、step order、numeric round-trip、JSON fields
- 最後一個測試 `test_full_chain_from_database` 模擬 restart（關閉 session + 開新 engine）

**不足之處**：
1. ❌ **非實際 pipeline 產出**：Step 資料是手動造的，不是來自 TraceManager
2. ❌ **非 Postgres**：使用 SQLite
3. ⚠️ Step 的 `step_name`、`duration_ms`、`parent_trace_id` 等重要 TraceStep 欄位從未被驗證，因為 DB model 根本沒有這些欄位

### 5.3 test_recommendation_service.py

**測試覆蓋範圍**：
- ✅ `test_successful_creation` — 驗證 response 結構 + 確認 DB 有紀錄
- ✅ `test_trace_with_steps_persisted` — 驗證 trace + steps 確實寫入
- ✅ `test_same_transaction_persistence` — 三者在同一 transaction
- ✅ `test_report_generation_failure_non_fatal` — report 失敗不影響
- ✅ `test_pipeline_failure_rollback` — pipeline 拋例外時 rollback
- ✅ `test_pipeline_error_status_rollback` — error status 時 rollback
- ✅ `test_empty_aggregated_data_rollback` — 無 evidence 時 rollback
- ✅ `test_repository_failure_rollback` — commit 失敗時回傳結果但 DB 乾淨
- ✅ `test_get_recommendation_found` — GET 正常
- ✅ `test_get_recommendation_not_found` — GET 回 None

**問題**：
1. ⚠️ `test_repository_failure_rollback` 測試了 persistence failure 情境且**接受目前的錯誤行為**（回傳結果不報錯），這實際上是在測試 BUG 而非正確行為
2. ⚠️ 大量使用 mock（mock_engine_run, mock_ranking_engine, mock_explainable_engine, mock_trace_manager, mock_report_generator），非真正 integration test
3. ⚠️ 使用 in-memory SQLite 而非 Postgres

### 5.4 test_api_recommendation.py

**測試覆蓋範圍**：
- ✅ `test_create_recommendation_success` — 驗證 POST 回 200 或 422
- ✅ `test_create_recommendation_minimal` — 最少欄位
- ✅ `test_create_recommendation_missing_patient_id` — 422
- ✅ `test_create_recommendation_missing_variants` — 422
- ✅ `test_create_recommendation_empty_variants` — 422
- ✅ `test_create_recommendation_invalid_top_n` — 422
- ✅ `test_create_recommendation_unauthorized` — 401
- ✅ `test_get_recommendation_not_found` — 404
- ✅ `test_get_recommendation_unauthorized` — 401
- ✅ `test_get_recommendation_after_create` — 但依賴 POST 成功（常 skip）
- ✅ `test_get_reads_from_database` — 驗證 GET 與 POST 資料一致
- ✅ `test_500_does_not_leak_exception` — 500 不洩漏細節
- ✅ `test_500_on_get_does_not_leak_exception` — GET 500 安全

**問題**：
1. ⚠️ demo mode 下證據收集常失敗，POST 回 422 而非 200，導致 GET 測試常被 skip
2. ⚠️ 使用 in-memory SQLite + demo mode，非真實 Postgres
3. ⚠️ 沒有測試 persistence failure 情境下的行為（Service 吞 exception 回 200 的 bug）

---

## 6. 既有測試基礎設施

### Postgres fixture

**目前不存在**。專案中沒有任何 Postgres 測試 fixture。

- `conftest.py`（`tests/` 根目錄）：只有 PyTorch/ML 相關 fixtures + 一個 `MockAsyncSession`（fake 物件，非真實 DB）
- 所有 recommendation 測試使用 `sqlite+aiosqlite://`（in-memory）或 `sqlite+aiosqlite:///file.db`

### App factory / create_app

位於 `src/backend/main.py:48-90`：
```python
def create_app() -> FastAPI:
    app = FastAPI(title=..., lifespan=lifespan)
    app.add_middleware(CORSMiddleware, ...)
    app.include_router(router)      # /
    app.include_router(research_router)
    app.include_router(v1_router)   # /api/v1
    app.include_router(auth_router) # /auth
    # 前端靜態檔案
    return app
```

API 測試使用 `TestClient(create_app())` 並在呼叫前修改 `settings.DATABASE_URL` 和 `settings.APP_MODE`。

### Dependency override pattern

**目前不存在**。程式碼中沒有使用 FastAPI `app.dependency_overrides` 的範例。

### AsyncSession fixture

**無統一 fixture**。每個測試檔案自行建立：

```python
# 測試檔案內自建
@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()
```

### Migration test 模式

位於 `tests/test_migration.py`：
- 使用 `alembic.config.Config` 直接操作
- 使用 SQLite 檔案（`test_migration.db`）
- 檢查 table 存在性用 `sqlite3` 模組的 `PRAGMA table_info`
- 支援 upgrade → downgrade → upgrade again 循環

### Transaction rollback test 模式

**目前不存在**。測試中沒有顯式的 transaction rollback 測試（即開始 transaction → 操作 → rollback → 驗證無資料殘留）。`test_recommendation_service.py` 中的 rollback 測試是透過讓 `mock_engine_run.run.side_effect` 拋例外或回傳 error status 來觸發 Service 層的 rollback。

---

## 7. 總結：三個根因問題的技術方案

### P0-1：Persistence failure 仍回傳成功

**根因**：`recommendation_service.py` 第 255-274 行，persist/commit 失敗時 catch exception、rollback、然後**繼續回傳 in-memory response**。

**最小修正方案**：

1. 移除 persistence try/except 的「吞 exception」行為，改為**讓例外傳播出去**：

```python
# 修正前
try:
    await self._persist_recommendation(...)
    await self._db.commit()
except Exception:
    await self._db.rollback()
    logger.exception(...)
# 沒有 raise，繼續 return response

# 修正後
try:
    await self._persist_recommendation(...)
    await self._db.commit()
except Exception:
    await self._db.rollback()
    logger.exception(...)
    raise RuntimeError("Failed to persist recommendation") from exc  # ← 新增
```

2. API 層的 `except Exception`（第 176 行）會接到此 RuntimeError，回傳 500 + generic message。

3. **無需改變** API 層的 HTTP 500 handler — 已正確實作 `INTERNAL_ERROR` response。

4. **需更新測試**：`test_repository_failure_rollback` 目前測試**舊行為**（failure 仍回傳結果），需改為驗證 RuntimeError 被拋出。

### P0-3：Restart Test 不是完整 API/App/Postgres 鏈路

**根因**：`test_restart_recovery.py` 使用 SQLite + 直接 Repository 操作 + 手動造資料。

**最小修正方案**：

建立一個新的 Restart Recovery Test，使用真實鏈路：

1. **使用 TestClient + create_app()**：透過 API 建立 recommendation
2. **使用 Postgres**（可透過 `testcontainers` 或 docker-compose 啟動測試用 Postgres）
3. **關閉 Engine → 建立新 Engine → 透過 API GET 確認資料存在**

若環境不允許 Postgres，退而求其次：
1. 仍使用 TestClient + create_app()
2. 使用 in-memory SQLite（至少驗證 API 鏈路）
3. 重點是**走完整 API 路徑**而非直接 Repository 操作

```python
# 最小可行方案（使用現有 in-memory SQLite 但走 API）
def test_restart_recovery_via_api(client, auth_headers):
    # Phase 1: POST 建立 recommendation
    create_resp = client.post("/api/v1/recommendation", json={...}, headers=...)
    assert create_resp.status_code == 200
    rec_id = create_resp.json()["recommendation_id"]
    
    # Phase 2: 重新建立 app（模擬 restart）
    # 注意：in-memory SQLite restart 後資料會消失
    # 所以這個測試只能使用檔案型 SQLite
```

**真正的 Postgres restart test** 需要：
- 獨立的 Postgres 實例（docker-compose）
- 跨連線的資料持久化驗證
- 測試 fixture 管理 engine/session lifecycle

### P0-2：Calculation Trace 實際未完整保存

**根因**三層面：

**A. TraceManager 仍在記憶體中**（`_traces: dict[str, CalculationTrace] = {}`）

**B. RecommendationTraceModel 缺少必要欄位**（對照 plan 設計規範缺少 patient_id, status, started_at, completed_at）

**C. TraceStep 的部分欄位未寫入 DB**（duration_ms、timestamp、step_name 未對應到 model）

**最小修正方案**：

1. **修正 Model 欄位**（`domain/recommendation.py`）：

```python
class RecommendationTraceModel(DBBase):
    __tablename__ = "domain_recommendation_traces"
    
    id = Column(CompatUUID, primary_key=True, default=_uuid)
    trace_id = Column(String(64), unique=True, nullable=False, index=True)
    recommendation_id = Column(CompatUUID, ForeignKey(...), nullable=True, index=True)
    patient_id = Column(String(64), nullable=False, index=True)       # ← 新增
    status = Column(String(16), nullable=False, default="running")     # ← 新增
    started_at = Column(DateTime, nullable=False)                      # ← 新增
    completed_at = Column(DateTime, nullable=True)                     # ← 新增
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
```

2. **修正 TraceStepModel 欄位**：加 `duration_ms`（Float, nullable）— 但 min 方案可先跳過，因為這屬於擴充而非 P0

3. **修正 Service 的 `_persist_recommendation`**：寫入完整欄位

```python
trace_model = RecommendationTraceModel(
    trace_id=trace_id,
    recommendation_id=rec_model.id,
    patient_id=patient_id,                           # ← 新增
    status=calc_trace.status,                        # ← 新增
    started_at=calc_trace.started_at,                # ← 新增
    completed_at=calc_trace.completed_at,            # ← 新增
)
```

4. **Migration 需更新**：`017_phase3a_recommendation_tables.py` 需對應新增欄位（或新增 018 migration）

5. **TraceManager 維持不變**（仍可保留 in-memory 作為 pipeline 執行期間的快取），只需確保 `_persist_recommendation` 完整寫入所有資料。

### 影響評估與優先順序

| 優先 | 問題 | 修改範圍 | 風險 |
|------|------|---------|------|
| 🔴 P0-1 | Persistence failure 回 200 | service 1 行 + test 1 個 | 低，單純讓例外傳遞 |
| 🔴 P0-2 | Trace 不完整 | model 加欄位 + migration + service | 中，需修改 migration |
| 🔴 P0-3 | Restart test 不真實 | 整個測試重寫 | 高，取決於 Postgres 是否能啟用 |

### 不建議的修改

- ❌ 不要將 TraceManager 改為 DB 直接寫入 — 保持 in-memory 作為 pipeline 快取，僅最終 persist 即可
- ❌ 不要改動 API schema（RecommendationRequest/Response）— 功能正常
- ❌ 不要重構整個 service — 只針對 persistence failure 路徑修正

---

*本報告由 Subagent 產出，基於真實程式碼分析，為 Phase 3A Final Fix 提供現狀基準。*
