# Phase 3A Hardening 執行計劃

## 概覽

本計劃針對 Phase 3A Drug Recommendation Engine V1 進行加固，將記憶體 dict 改為 Postgres 資料庫、補上 Trace 持久化、接入前端 Router、清理 artefacts、修復 HTTP 500 洩漏。

**目標**：所有 P0/P1 問題修復 + 正式實作 + 完整測試，一次 Commit。

**禁止事項**：
- ❌ 不得使用 dict/global variable/singleton cache/module-level cache/process memory/temporary file/JSON file/SQLite fallback 代替 DB
- ❌ 不得使用 mock/monkeypatch 偽裝 restart
- ❌ 不得 force push / rebase master
- ❌ 不得只新增 Model 不接 API
- ❌ 不得只接 Route 不接 Navigation
- ❌ Commit 只包含指定內容，不得混入無關修改

---

## 1. 任務分解（以 Batch 分組）

### Batch A — Foundation（基礎建設）

| ID | 任務 | 負責角色 | 檔案位置 | 描述 |
|----|------|----------|----------|------|
| A1 | **RecommendationModel** | db-modeler | `src/backend/domain/recommendation.py` | 建立 RecommendationModel (SQLAlchemy ORM)，包含 id, patient_id, case_id, trace_id, engine_version, status, request_payload (JSON), result_payload (JSON), report_html (Text), created_by, created_at, updated_at。 |
| A2 | **RecommendationTraceModel + TraceStepModel** | db-modeler | `src/backend/domain/recommendation_trace.py` | 建立 RecommendationTraceModel (id, recommendation_id FK, patient_id, trace_id, status, started_at, completed_at) 及 RecommendationTraceStepModel (id, trace_id FK, step_name, step_type, input_data JSON, output_data JSON, timestamp, duration_ms)。與 RecommendationModel 建立外鍵關聯。 |
| A3 | **Alembic Migration** | db-modeler | `alembic/versions/` (新增 revision) | 新增正式 Migration，包含 recommendations / recommendation_traces / recommendation_trace_steps 三張表。upgrade 安全建立，downgrade 完整還原。 |

### Batch B — Repository & Service

| ID | 任務 | 負責角色 | 檔案位置 | 描述 |
|----|------|----------|----------|------|
| B1 | **RecommendationRepository** | backend-logic | `src/backend/clinical/recommendation_repository.py` | 建立 Repository 類別：create(), get_by_id(), get_by_trace_id(), list_by_patient_id()。不自行 commit，由 Service 管理 Transaction。使用 AsyncSession。 |
| B2 | **TraceRepository** | backend-logic | `src/backend/clinical/recommendation_repository.py`（或獨立檔案） | 建立 Trace 相關查詢：create_trace(), add_step(), get_trace_by_id(), get_trace_by_recommendation_id()。與 RecommendationRepository 共用 session。 |
| B3 | **RecommendationService** | backend-logic | `src/backend/clinical/recommendation_service.py` | 建立正式 Service：run_pipeline() → 執行 Engine Pipeline → 建立 Recommendation Record + Trace → 生成 HTML Report → 同一 Transaction 提交或 Rollback。取代 API 中直接操作 dict 的邏輯。 |

### Batch C — API Hardening

| ID | 任務 | 負責角色 | 檔案位置 | 描述 |
|----|------|----------|----------|------|
| C1 | **API 改為全 Database** | api-designer | `src/backend/api/v1/recommendation.py` | POST /api/v1/recommendation 改為呼叫 RecommendationService，結果寫入 DB。GET /api/v1/recommendation/{recommendation_id} 改為從 DB 讀取。移除 `_recommendations` dict。保留現有 Pydantic Request/Response Schema。 |
| C2 | **HTTP 500 Error Security** | backend-logic / security-fixer | `src/backend/api/v1/recommendation.py`（及 middleware） | 所有非預期 Exception 改為 logger.exception() + 固定 error code + generic message。不洩漏 Exception 內容給 Client。檢查 FastAPI exception handlers 是否有全局設定。 |
| C3 | **Router 清理** | api-designer | `src/backend/api/v1/recommendation.py` | 移除 `_recommendations: dict[str, dict] = {}` 及所有相關記憶體操作。確認無其他檔案引用該變數。 |

### Batch D — Frontend

| ID | 任務 | 負責角色 | 檔案位置 | 描述 |
|----|------|----------|----------|------|
| D1 | **App.tsx Route 註冊** | frontend-logic | `src/frontend/src/App.tsx` | 加入 `<Route path="/recommendation" element={<RecommendationPage />} />`。 |
| D2 | **Navigation/Menu 接入** | frontend-logic | `src/frontend/src/components/Navbar.tsx`（或等同） | 在導航選單中加入 Recommendation Page 的 Link。確認點擊可到達。 |
| D3 | **API Client 確認** | frontend-logic | `src/frontend/src/pages/RecommendationPage.tsx` | 確認 API path 正確（`/api/v1/recommendation`），無 hardcode fake data。 |

### Batch E — Tests

| ID | 任務 | 負責角色 | 檔案位置 | 描述 |
|----|------|----------|----------|------|
| E1 | **Model Tests** | unit-tester | `tests/backend/models/test_recommendation_model.py` | RecommendationModel JSON round-trip, Index 正確性, Trace relation。 |
| E2 | **Repository Tests** | unit-tester | `tests/backend/repositories/test_recommendation_repository.py` | create, get_by_id, get_by_trace_id, list_by_patient_id, not found, rollback。使用 Test Database。 |
| E3 | **Service Tests** | unit-tester | `tests/backend/services/test_recommendation_service.py` | 成功建立、同 transaction、Report failure、Pipeline failure rollback。 |
| E4 | **API Integration Tests** | integration-tester | `tests/backend/api/test_recommendation_api.py` | POST→DB 驗證、GET→DB 驗證、404、422、500 generic（不洩漏 Exception）。使用 TestClient。 |
| E5 | **Restart Recovery Test** | integration-tester | `tests/backend/integration/test_restart_recovery.py` | 真實新 App、新 Engine、新 Session。重啟後 Recommendation 和 Trace 仍可查詢。 |
| E6 | **Trace Persistence Test** | integration-tester | `tests/backend/integration/test_trace_persistence.py` | Evidence→Weight→Score→Rank→Explanation 完整計算鏈可從 DB 還原。 |
| E7 | **Frontend Route Test** | frontend-tester | `tests/frontend/`（依專案慣例） | Route registered、Navigation clickable、Page renders、API path correct。 |
| E8 | **Migration Tests** | integration-tester | `tests/backend/integration/test_migration.py` | upgrade→downgrade→upgrade again 安全可逆。 |

### Batch F — Cleanup

| ID | 任務 | 負責角色 | 檔案位置 | 描述 |
|----|------|----------|----------|------|
| F1 | **清理 Phase E/Vercel artefacts** | doc-writer | 專案根目錄及 tasks/ | 先確認無其他正式功能引用，再移除無關檔案。如 tasks/ 中殘留的 Phase E / Vercel 相關檔案。 |
| F2 | **確認 requirements.md 歷史正確** | doc-writer | `tasks/requirements.md` | 確認已保留舊有 Vercel/Phase E 需求、Phase 3A 原始需求、Phase 3A Hardening 章節。只 append，不覆蓋。 |

---

## 2. 依賴關係

```
A1 ──→ A3 ──→ B1 ──→ B3 ──→ C1
A2 ──→ A3 ──→ B2 ──→ B3 ──→ C1
                       B3 ──→ E3
A1, A2 ──→ E1
B1, B2 ──→ E2
C1, C2 ──→ E4
B3, C1 ──→ E5 (Restart Recovery)
A2, B2 ──→ E6 (Trace Persistence)
A3 ──→ E8 (Migration)
D1, D2, D3 ──→ E7 (Frontend Route)
C2 無依賴，可並行於 Batch C
F1 無依賴，可並行
F2 無依賴，可並行
E7 依賴 D1~D3
```

**批次執行順序建議**：
1. Batch A（Model + Migration）— 基礎建設
2. Batch B（Repository + Service）— 業務邏輯
3. Batch C（API Hardening）— API 層
4. Batch D（Frontend）— 前端（可與 Batch C 部分並行）
5. Batch E（Tests）— 完整測試驗證
6. Batch F（Cleanup）— 最後清理

**關鍵路徑**：A1 → A3 → B1 → B3 → C1 → E4 → E5（Restart Recovery 為最終驗證）

---

## 3. 負責角色對照

| 角色 | 負責 Batch |
|------|-----------|
| db-modeler | A1, A2, A3 |
| backend-logic | B1, B2, B3 (兼 C2, C3) |
| api-designer | C1, C3 |
| backend-logic / security-fixer | C2 |
| frontend-logic | D1, D2, D3 |
| unit-tester | E1, E2, E3 |
| integration-tester | E4, E5, E6, E8 |
| frontend-tester | E7 |
| doc-writer | F1, F2 |
| reviewer | 最終評分 |

---

## 4. 返工預案

### 關鍵風險點

| 風險 | 影響 | 緩解策略 | 返工觸發條件 |
|------|------|----------|------------|
| Migration downgrade 不完全 | DB 狀態混亂 | 撰寫 Migration 後立即測試 upgrade→downgrade→upgrade | E8 Migration Tests 失敗 |
| Service Transaction 邊界錯誤 | 資料不一致 | Service 使用同一 session + commit/rollback 模式 | E3 Service Tests 失敗 |
| Restart Recovery Test 使用 mock | 測試無效 | 強制使用真實新 App/Engine/Session，不可 mock | E5 失敗 |
| Frontend Route 註冊但 Navigation 未加 | 使用者找不到頁面 | 同時確認 Route + Navigation + Link | E7 Frontend Route Test 失敗 |
| HTTP 500 仍洩漏 Exception | P1 未修 | 加入 middleware 層級攔截 + logger.exception() | E4 API 500 generic 測試失敗 |
| 清理 artefacts 誤刪正式檔案 | 功能損壞 | 先確認引用關係再刪除 | 刪除後 go test ./... 失敗 |
| `_recommendations` dict 未完全移除 | P0-1 未修 | grep 確認無殘留 | C3 Router 清理未完成 |

### 返工策略

1. **單一任務失敗** → 該任務負責子代理 resume，修正後重新執行該任務及其下游相依任務
2. **批次全部失敗** → PLANNER resume 重新評估該批次設計後再執行
3. **Restart Recovery Test 失敗** → 檢查 Service 是否真的操作 DB + API 是否正確從 DB 讀取
4. **Migration Test 失敗** → 檢查 downgrade 邏輯，確保 DROP TABLE 順序正確（先刪 steps→traces→recommendations）
5. **最終 Reviewer 評分 < 90** → PLANNER resume 讀取評分報告，針對缺失項目重新規劃後執行返工循環

---

## 5. 設計規範

### Model 設計

**RecommendationModel** (`recommendations` table):
| Column | Type | Constraint | Notes |
|--------|------|-----------|-------|
| id | UUID (PK) | default uuid4 |  |
| patient_id | String(64) | NOT NULL, INDEX |  |
| case_id | String(64) | NULLABLE |  |
| trace_id | String(64) | NULLABLE, INDEX |  |
| engine_version | String(32) | NOT NULL | e.g. "1.0.0" |
| status | String(16) | NOT NULL | "pending" / "completed" / "failed" |
| request_payload | JSON | NOT NULL | 原始請求 |
| result_payload | JSON | NULLABLE | 完整結果 |
| report_html | Text | NULLABLE | HTML Report |
| created_by | String(128) | NULLABLE | user id |
| created_at | DateTime | NOT NULL | utcnow |
| updated_at | DateTime | NOT NULL, onupdate | utcnow |

**RecommendationTraceModel** (`recommendation_traces` table):
| Column | Type | Constraint | Notes |
|--------|------|-----------|-------|
| id | UUID (PK) | default uuid4 |  |
| recommendation_id | UUID (FK) | REFERENCES recommendations(id), INDEX |  |
| patient_id | String(64) | NOT NULL |  |
| trace_id | String(64) | NOT NULL, UNIQUE |  |
| status | String(16) | NOT NULL | "running" / "completed" / "failed" |
| started_at | DateTime | NOT NULL |  |
| completed_at | DateTime | NULLABLE |  |

**RecommendationTraceStepModel** (`recommendation_trace_steps` table):
| Column | Type | Constraint | Notes |
|--------|------|-----------|-------|
| id | UUID (PK) | default uuid4 |  |
| trace_id | UUID (FK) | REFERENCES recommendation_traces(id), INDEX |  |
| step_name | String(64) | NOT NULL |  |
| step_type | String(32) | NOT NULL | "input"/"evidence"/"score"/"recommendation"/"output" |
| input_data | JSON | NULLABLE |  |
| output_data | JSON | NULLABLE |  |
| timestamp | DateTime | NOT NULL |  |
| duration_ms | Float | NULLABLE |  |

### Repository 方法簽章

```python
class RecommendationRepository:
    async def create(self, db: AsyncSession, model: RecommendationModel) -> RecommendationModel: ...
    async def get_by_id(self, db: AsyncSession, id: UUID) -> RecommendationModel | None: ...
    async def get_by_trace_id(self, db: AsyncSession, trace_id: str) -> RecommendationModel | None: ...
    async def list_by_patient_id(self, db: AsyncSession, patient_id: str, limit: int = 20) -> list[RecommendationModel]: ...
```

### Service 方法簽章

```python
class RecommendationService:
    def __init__(self, db: AsyncSession, repository: RecommendationRepository, ...): ...
    async def run_recommendation(self, request: RecommendationRequest, user: UserModel) -> RecommendationResponse: ...
    async def get_recommendation(self, recommendation_id: str) -> RecommendationResponse | None: ...
```

### API 簽章（保持不變）

- POST `/api/v1/recommendation` → `RecommendationResponse`
- GET `/api/v1/recommendation/{recommendation_id}` → `RecommendationResponse`

### HTTP Error 安全格式

```json
{
    "error": "internal_error",
    "message": "An internal error occurred. Please try again later or contact support."
}
```

---

## 6. 測試策略

### 測試資料庫
- 使用獨立 Test Database（PostgreSQL），每個 Test Class 前 truncate 相關 tables
- 或使用 docker-compose 啟動測試用 Postgres 實例

### 測試類型

| 類型 | 工具 | 重點 |
|------|------|------|
| Unit Tests | pytest + pytest-asyncio | Model round-trip, Repository CRUD |
| Integration Tests | TestClient (FastAPI) + real DB | API 端到端, Restart Recovery, Trace Persistence |
| Migration Tests | Alembic 程式化操作 | upgrade→downgrade→upgrade |
| Frontend Tests | React Testing Library | Route registered, Navigation clickable, API path |

### Restart Recovery Test 設計
1. 建立真實 AsyncEngine + Session
2. POST 建立 recommendation → 取得 id
3. 關閉 engine + session
4. 建立全新 AsyncEngine + Session（模擬重啟）
5. GET 查詢同一 id → 確認可取得完整資料
6. 查詢 Trace → 確認 steps 完整

---

## 7. 最終驗證清單

- [ ] go test ./... 全部通過
- [ ] Frontend build 成功（npm run build）
- [ ] Backend build 成功
- [ ] API Smoke Test（POST → GET → 驗證資料一致）
- [ ] Migration upgrade→downgrade→upgrade 安全
- [ ] 無 dict 殘留（grep `_recommendations` 確認）
- [ ] HTTP 500 不回傳 Exception 細節
- [ ] RecommendationPage 可從 Navigation 進入
- [ ] Git diff 只包含指定檔案
- [ ] 一次 Commit 完成

---

## 8. Batch 執行順序摘要

```
Step 1: Batch A (A1 → A2 → A3)  — db-modeler
Step 2: Batch B (B1 → B2 → B3)  — backend-logic
Step 3: Batch C (C1 → C2 → C3)  — api-designer + backend-logic
Step 4: Batch D (D1 → D2 → D3)  — frontend-logic
Step 5: Batch E (E1~E8)         — unit-tester + integration-tester + frontend-tester
Step 6: Batch F (F1 → F2)       — doc-writer
Step 7: 全量驗證 + 一次 Commit
```

---

*本計劃由 PLANNER 產出，對應 Step 2。*
