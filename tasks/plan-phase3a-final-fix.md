# Phase 3A Hardening Final Fix — 執行計劃

## 前置分析摘要

根據 tasks/phase3a-final-fix-pre-read.md 的程式碼掃描，三個 P0 問題的根因如下：

| 問題 | 根因位置 | 根因說明 |
|------|---------|---------|
| **P0-1** | `services/recommendation_service.py:255-274` | persistence try/except 吞例外後仍 `return response`，API 層永遠收 200 |
| **P0-2** | `tests/test_restart_recovery.py` 全部 | 使用 SQLite 檔案 + 直接 Repository 操作 + 手動造資料，非真實 API/App/Postgres 鏈路 |
| **P0-3** | `domain/recommendation.py` + `services/recommendation_service.py` | `RecommendationTraceModel` 缺少 patient_id/status/started_at/completed_at；`RecommendationTraceStepModel` 缺少 duration_ms；`_persist_recommendation` 未寫入完整欄位 |

---

## 任務清單

### Batch A：Atomic Persistence（P0-1）
- **負責角色**：backend-logic
- **目標**：`recommendation_service.py` 中 persistence 失敗不得回傳成功，必須 rollback → raise → API 500
- **修改檔案**：`src/backend/services/recommendation_service.py`
- **依賴**：無

#### 技術方案

**修改位置**：`recommendation_service.py` 第 255-274 行（`_persist_recommendation` 與 `commit` 的 try/except 區塊）

**現狀程式碼**（簡化）：
```python
try:
    await self._persist_recommendation(...)
    await self._db.commit()
except Exception:
    await self._db.rollback()
    logger.exception("Failed to persist recommendation %s — rolled back.")
# 沒有 raise，繼續 return response  ← P0-1 根因
```

**修正後程式碼**：
```python
try:
    await self._persist_recommendation(...)
    await self._db.commit()
except Exception as exc:
    await self._db.rollback()
    logger.exception("Failed to persist recommendation %s — rolled back.")
    raise RuntimeError("Failed to persist recommendation") from exc  # ← 讓例外傳播
```

**說明**：
1. 改為 `except Exception as exc` 以保留原始例外鏈
2. 在 rollback 與 log 後 `raise RuntimeError(...)`，讓例外傳遞給 API 層
3. API 層（`recommendation.py:176-184`）的 `except Exception` handler 已正確實作 `{"error": "INTERNAL_ERROR", "message": "Recommendation processing failed."}`，HTTP 500
4. 此修正後 Client 不再取得 `recommendation_id` 當 DB 無資料
5. `recommendation`、`trace`、`trace_steps` 在同一 transaction 中，因 `_persist_recommendation` 內部使用同一個 `self._db`（AsyncSession），且 Service 層管理全部 add 後才 commit，達成 All-or-Nothing

**需注意**：
- `_persist_recommendation` 方法內部已經依序 add：RecommendationModel → RecommendationTraceModel → RecommendationTraceStepModel（每個 step），全部使用 `self._db.add()`
- Service 的 `create_recommendation` 方法從 pipeline 執行到 persist 全程使用同一 `self._db` session，transaction 邊界正確

---

### Batch B：API 500 安全映射（P0-1 配套）
- **負責角色**：api-designer
- **目標**：確認 API 層已區分 ValueError / PersistenceError(RuntimeError) / 其他 Exception，HTTP 500 不洩漏細節
- **修改檔案**：`src/backend/api/v1/recommendation.py`
- **依賴**：Batch A

#### 技術方案

**現狀分析**（pre-read 4.2 節）：
| 路由 | 例外來源 | HTTP 狀態 | Response Body | 正確？ |
|------|---------|-----------|---------------|--------|
| POST | ValueError（無 evidence/無 ranking） | 422 | `{"error": "validation_failed", "message": ...}` | ✅ 正確 |
| POST | Exception（含 RuntimeError） | 500 | `{"error": "INTERNAL_ERROR", "message": "Recommendation processing failed."}` | ✅ 正確 |
| GET | Exception | 500 | `{"error": "INTERNAL_ERROR", ...}` | ✅ 正確 |
| GET | model is None | 404 | `{"error": "not_found", "message": ...}` | ✅ 正確 |

**結論**：API 層的例外處理已正確實作。Batch A 修正後，Service 層的 persistence failure 會傳播 RuntimeError 到此 handler，自動得到 HTTP 500 + generic message。

**但仍需確認的事項**：
1. API handler 中 `except Exception` 的 catch 範圍是否會意外 catch 到 `asyncio.CancelledError` 等不該抓的例外？→ 檢查：若使用 `except Exception`（而非 `except BaseException`）則安全，asyncio.CancelledError 繼承自 BaseException 而非 Exception
2. 確認 POST handler 第 176 行附近是否為 `except Exception as e:` 而非 bare `except:` → 需檢查
3. **無需修改程式碼**，但需在 plan 中標註已驗證

**修改**：
- 若發現 `except Exception` 不完整，補上 `except (ValueError, RuntimeError, ...)` 的精確捕獲
- 但根據 pre-read 分析，API 層已正確，因此 Batch B 主要是**驗證確認**，可能無需實際修改

---

### Batch C：完整 Trace Persistence（P0-3）
- **負責角色**：backend-logic
- **目標**：正式 Recommendation Pipeline 寫入 Evidence/Weight/Score/Rank/Explanation；補齊 Model 缺少欄位；Migration 對應更新
- **修改檔案**：
  - `src/backend/domain/recommendation.py`（Model 加欄位）
  - `src/backend/services/recommendation_service.py`（`_persist_recommendation` 補寫入）
  - `migrations/versions/017_phase3a_recommendation_tables.py` 或新增 `018_phase3a_trace_fields.py`
- **依賴**：Batch A

#### 技術方案

##### C1：補齊 RecommendationTraceModel 欄位

現狀缺少的欄位（對照 plan-phase3a-hardening.md 設計規範）：

```python
# 現有欄位（domain/recommendation.py）
class RecommendationTraceModel(DBBase):
    __tablename__ = "domain_recommendation_traces"
    
    id = Column(CompatUUID, primary_key=True, default=_uuid)
    trace_id = Column(String(64), unique=True, nullable=False, index=True)
    recommendation_id = Column(CompatUUID, ForeignKey(...), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    # 缺少：patient_id, status, started_at, completed_at

# 修正後（新增欄位）
class RecommendationTraceModel(DBBase):
    __tablename__ = "domain_recommendation_traces"
    
    id = Column(CompatUUID, primary_key=True, default=_uuid)
    trace_id = Column(String(64), unique=True, nullable=False, index=True)
    recommendation_id = Column(CompatUUID, ForeignKey("domain_recommendations.id", ondelete="CASCADE"), nullable=True, index=True)
    patient_id = Column(String(64), nullable=False, index=True)           # ← 新增
    status = Column(String(16), nullable=False, default="running")         # ← 新增（running/completed/failed）
    started_at = Column(DateTime, nullable=False)                          # ← 新增
    completed_at = Column(DateTime, nullable=True)                         # ← 新增（nullable，因為 pipeline 可能失敗）
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
```

##### C2：補齊 RecommendationTraceStepModel 欄位

```python
# 現有欄位
class RecommendationTraceStepModel(DBBase):
    __tablename__ = "domain_recommendation_trace_steps"
    
    id = Column(CompatUUID, primary_key=True, default=_uuid)
    trace_id = Column(CompatUUID, ForeignKey("domain_recommendation_traces.id", ondelete="CASCADE"))
    step_order = Column(Integer)
    step_type = Column(String(64))
    input_summary = Column(JSON, nullable=True)
    output_summary = Column(JSON, nullable=True)
    evidence_references = Column(JSON, nullable=True)
    weight = Column(Float, nullable=True)
    score = Column(Float, nullable=True)
    rank = Column(Integer, nullable=True)
    status = Column(String(32))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    # 缺少：duration_ms

# 修正後（新增欄位）
class RecommendationTraceStepModel(DBBase):
    # ... 既有欄位 ...
    duration_ms = Column(Float, nullable=True)   # ← 新增（TraceStep Pydantic model 有此欄位但從未寫入 DB）
```

**注意**：`step_name` 和 `parent_trace_id` 雖然在 TraceStep Pydantic model 中，但 DB model 不一定需要對應，因為 `step_type` 已可辨識步驟類型，`parent_trace_id` 則從未在目前的 pipeline 中使用。最小方案只加 `duration_ms`。

##### C3：修改 `_persist_recommendation` 寫入完整欄位

現狀（service 中 trace 寫入邏輯）：
```python
trace_model = RecommendationTraceModel(
    trace_id=trace_id,
    recommendation_id=rec_model.id,
)
# 缺少 patient_id, status, started_at, completed_at
```

修正後：
```python
trace_model = RecommendationTraceModel(
    trace_id=trace_id,
    recommendation_id=rec_model.id,
    patient_id=str(patient_id),                    # ← 新增（從 request 或 rec_model 取得）
    status=calc_trace.status if hasattr(calc_trace, 'status') else "completed",  # ← 新增
    started_at=calc_trace.started_at if hasattr(calc_trace, 'started_at') else datetime.utcnow(),  # ← 新增
    completed_at=calc_trace.completed_at if hasattr(calc_trace, 'completed_at') else datetime.utcnow(),  # ← 新增
)
```

**獲取 patient_id 的方式**：在 `create_recommendation` 方法中，`request` 物件已有 `patient_id`，可在呼叫 `_persist_recommendation` 時傳入。

**Step 層級寫入補強**（現狀已寫入 step_type/input_summary/output_summary，需確認 evidence_references/weight/score/rank 也被寫入）：
```python
step_model = RecommendationTraceStepModel(
    trace_id=trace_model.id,
    step_order=step.step_order,                    # 需確認 TraceManager 有賦予 step_order
    step_type=step.step_type,
    input_summary=step.input_data if hasattr(step, 'input_data') else step.get('input_summary'),
    output_summary=step.output_data if hasattr(step, 'output_data') else step.get('output_summary'),
    evidence_references=step.get('evidence_references'),  # ← 確認已寫入
    weight=step.get('weight'),                      # ← 確認已寫入
    score=step.get('score'),                        # ← 確認已寫入
    rank=step.get('rank'),                          # ← 確認已寫入
    status="completed",
    duration_ms=step.duration_ms if hasattr(step, 'duration_ms') else None,  # ← 新增
)
```

**需檢查**：TraceManager 的 `add_step` 是否已將 evidence_references/weight/score/rank 存入 step 的 output_data 或獨立欄位？若 pipeline 的 Engine/EvidenceAggregator/DrugRanker 已將這些資料放入 step，則直接讀取即可；若尚未放入，需在 pipeline component 中補上。

**不建議**：將 TraceManager 改為直接寫 DB — 保持 in-memory cache 作為 pipeline 執行期間的快取，僅在 `_persist_recommendation` 時一次寫入。

##### C4：Migration 更新

兩種方案：
1. **修改現有 017 migration**（若尚未 merge 到 master）：直接補上 ALTER TABLE ADD COLUMN 語句
2. **新增 018 migration**（若 017 已存在於歷史中）：`alembic revision -m "phase3a_trace_fields"`，產生 upgrade/downgrade

**upgrade 內容（018）**：
```python
def upgrade():
    op.add_column('domain_recommendation_traces', sa.Column('patient_id', sa.String(64), nullable=False, index=True))
    op.add_column('domain_recommendation_traces', sa.Column('status', sa.String(16), nullable=False, server_default='running'))
    op.add_column('domain_recommendation_traces', sa.Column('started_at', sa.DateTime, nullable=False, server_default=sa.func.now()))
    op.add_column('domain_recommendation_traces', sa.Column('completed_at', sa.DateTime, nullable=True))
    op.add_column('domain_recommendation_trace_steps', sa.Column('duration_ms', sa.Float, nullable=True))
```

**downgrade**：反向 `op.drop_column`。

---

### Batch D：Transaction Tests（T1）
- **負責角色**：test-writer
- **目標**：5 個 Transaction Case
- **需使用 Postgres integration**（若無法使用 Postgres，則退而使用 `sqlite+aiosqlite://` 但必須測試 rollback 行為）
- **依賴**：Batch A、B、C

#### 技術方案

**測試架構**：新增 `tests/test_recommendation_transaction.py`

**測試案例**：

| Case | 情境 | 觸發方式 | 預期行為 |
|------|------|---------|---------|
| 1 | Recommendation create 失敗 | mock/setup 讓 `_persist_recommendation` 中 add recommendation 時拋例外（例如 duplicate key 或 FK violation） | rollback → 無殘留 → API 500 |
| 2 | Trace create 失敗 | 同上，但在 add trace 時拋例外 | rollback → 無殘留 → API 500 |
| 3 | Trace Step create 失敗 | 同上，但在 add step 時拋例外 | rollback → 無殘留 → API 500 |
| 4 | Commit 失敗 | mock `AsyncSession.commit` 拋例外 | rollback → API 500 |
| 5 | 成功 | 正常 pipeline | 全部 commit → GET 可讀取完整資料 |

**實現方式 Option A（使用 mock 模擬失敗）**：
- 透過 pytest fixture 注入 mock，讓特定操作拋出例外
- 驗證：使用 `AsyncSession.rollback.assert_called_once()` + verify DB 無資料

**實現方式 Option B（使用真實 DB 觸發 FK/Constraint 失敗）**：
- 例如：傳入不存在的 patient_id（但 FK 若設為可空或無 FK 則無法觸發）
- 或：讓 DB connection 中斷（network drop），但此方式不可靠

**建議**：Option A（mock）+ 一個真實 DB 驗證（Case 5：成功情境直接用 Postgres/SQLite 驗證資料可讀）

**驗證 rollback 無殘留**：
```python
# 在所有 rollback case 結尾
remaining_recs = await session.execute(select(RecommendationModel))
assert len(remaining_recs.scalars().all()) == 0
remaining_traces = await session.execute(select(RecommendationTraceModel))
assert len(remaining_traces.scalars().all()) == 0
remaining_steps = await session.execute(select(RecommendationTraceStepModel))
assert len(remaining_steps.scalars().all()) == 0
```

---

### Batch E：Restart Recovery Test（P0-2）
- **負責角色**：test-writer
- **目標**：真正 End-to-End App 1 → POST → shutdown → App 2 → GET
- **需使用 Postgres**（若環境不允許，退而使用 file-based SQLite 但必須走完整 API 鏈路）
- **依賴**：Batch A、B、C

#### 技術方案

**現狀問題**（pre-read 5.1 節）：
- 使用 SQLite 檔案 + 直接 Repository 操作
- 沒有 TestClient、沒有 create_app()、沒有 API 路徑
- 手動造資料而非經由實際 pipeline

**最小可行方案**（若 Postgres 不可用，使用 file-based SQLite 但走 API）：

```python
# tests/test_restart_recovery.py — 完整重寫

@pytest.fixture(scope="module")
def db_path():
    """使用暫存檔案，確保跨 engine 實例可讀"""
    path = os.path.join(tempfile.gettempdir(), f"test_restart_{uuid4().hex}.db")
    yield path
    if os.path.exists(path):
        os.unlink(path)

def test_end_to_end_restart_recovery(db_path):
    """Phase 1: App 1 → POST → 確認 → dispose → Phase 2: App 2 → GET 確認"""
    # === Phase 1: App 1 ===
    settings.DATABASE_URL = f"sqlite+aiosqlite:///{db_path}"
    settings.APP_MODE = "demo"  # 確保 pipeline 可執行
    app1 = create_app()
    client1 = TestClient(app1)
    
    # 透過 API POST
    create_resp = client1.post(
        "/api/v1/recommendation",
        json={...},  # 標準 request payload
        headers={"Authorization": f"Bearer {VALID_TOKEN}"},
    )
    assert create_resp.status_code == 200
    rec_id = create_resp.json()["recommendation_id"]
    trace_id = create_resp.json().get("trace_id")
    
    # 驗證 DB 中有資料（透過 API 或直接查詢）
    get_resp = client1.get(f"/api/v1/recommendation/{rec_id}", headers=...)
    assert get_resp.status_code == 200
    
    # 關閉 App 1
    app1.dependency_overrides.clear()
    del client1, app1
    
    # 強制 dispose engine（若有 engine 引用）
    
    # === Phase 2: App 2（全新實例）===
    app2 = create_app()  # 重新建立，使用相同 DATABASE_URL
    client2 = TestClient(app2)
    
    # 驗證 app1 != app2
    assert id(app1) != id(app2)
    
    # 透過 API GET 取得相同資料
    get_resp2 = client2.get(f"/api/v1/recommendation/{rec_id}", headers=...)
    assert get_resp2.status_code == 200
    data2 = get_resp2.json()
    assert data2["recommendation_id"] == rec_id
    if trace_id:
        assert data2.get("trace_id") == trace_id
    
    # 清理
    app2.dependency_overrides.clear()
```

**真正 Postgres 方案**（若可啟用 Postgres）：
```python
@pytest.fixture(scope="module")
def postgres_db():
    """使用 docker-compose 或 testcontainers 啟動 Postgres"""
    # 使用 testcontainers 套件
    postgres = DockerContainer("postgres:15-alpine")
    postgres.with_env("POSTGRES_USER", "test")
    postgres.with_env("POSTGRES_PASSWORD", "test")
    postgres.with_env("POSTGRES_DB", "test")
    postgres.with_exposed_ports(5432)
    postgres.start()
    
    db_url = f"postgresql+asyncpg://test:test@localhost:{postgres.get_exposed_port(5432)}/test"
    yield db_url
    postgres.stop()

def test_restart_recovery_postgres(postgres_db):
    settings.DATABASE_URL = postgres_db
    # ... 同上述流程 ...
    # 新增驗證 engine1 != engine2:
    # app1.state.engine 與 app2.state.engine 不同
```

**需注意**：
- 測試必須證明 `app1 ≠ app2`、`engine1 ≠ engine2`、`sessionmaker1 ≠ sessionmaker2`
- 可透過在 app.state 中儲存 engine reference 來比較
- 若使用 file-based SQLite，需確保檔案路徑跨 app 實例可存取

---

### Batch F：Trace Persistence Tests（P0-3 驗證）
- **負責角色**：test-writer
- **目標**：Service 產生的 Trace 需有 evidence_references/weight/score/rank/explanation
- **依賴**：Batch C

#### 技術方案

**現狀問題**（pre-read 5.2 節）：
- `test_trace_persistence.py` 使用手動造資料而非實際 pipeline
- 從未驗證 evidence_references/weight/score/rank/explanation 的正確性
- 使用 SQLite 而非 Postgres

**修正方案**：重寫 `tests/test_trace_persistence.py`，走實際 Service 路徑：

```python
@pytest.fixture
async def service(db_session):
    # 使用真實 DB session 而非 mock
    repo = RecommendationRepository(db_session)
    trace_repo = TraceRepository(db_session)
    # 建立真實 pipeline component（若非同步則使用 async）
    engine_run = RecommendationEngineRun()
    ranking_engine = DrugRankingEngine()
    explainable_engine = DrugExplainableEngine()
    report_generator = HTMLReportGenerator()
    trace_manager = TraceManager()
    
    service = RecommendationService(
        db=db_session,
        repo=repo,
        trace_repo=trace_repo,
        engine_run=engine_run,
        ranking_engine=ranking_engine,
        explainable_engine=explainable_engine,
        report_generator=report_generator,
        trace_manager=trace_manager,
    )
    return service

async def test_trace_evidence_references_persisted(service, sample_request):
    """驗證 pipeline 產生的 trace step 含有 evidence_references"""
    response = await service.create_recommendation(sample_request)
    trace_id = response.trace_id
    
    # 從 DB 讀取 trace steps
    steps = await service.trace_repo.get_steps_by_trace_id(trace_id)
    
    # 驗證至少有一個 step 有 evidence_references
    evidence_steps = [s for s in steps if s.evidence_references is not None]
    assert len(evidence_steps) > 0, "至少需有一個 evidence step 含 references"
    
    # 驗證 evidence_references 是有效 JSON array
    for step in evidence_steps:
        refs = step.evidence_references
        assert isinstance(refs, list), "evidence_references 須為 list"
        for ref in refs:
            assert "source" in ref, "每個 reference 需有 source"
            assert "evidence_level" in ref, "每個 reference 需有 evidence_level"

async def test_trace_weight_score_rank_persisted(service, sample_request):
    """驗證每個 trace step 的 weight/score/rank 被正確寫入"""
    response = await service.create_recommendation(sample_request)
    trace_id = response.trace_id
    
    steps = await service.trace_repo.get_steps_by_trace_id(trace_id)
    
    # 驗證至少有一個 step 有 weight/score
    scored_steps = [s for s in steps if s.weight is not None or s.score is not None]
    assert len(scored_steps) > 0, "至少需有一個 step 含 weight/score"
    
    # 驗證 recommendation step 有 rank
    rank_steps = [s for s in steps if s.rank is not None]
    assert len(rank_steps) > 0, "至少需有一個 step 含 rank"

async def test_trace_explanation_from_output_summary(service, sample_request):
    """驗證 explanation 可從 output_summary 還原"""
    response = await service.create_recommendation(sample_request)
    trace_id = response.trace_id
    
    steps = await service.trace_repo.get_steps_by_trace_id(trace_id)
    
    # 檢查 output_summary 中是否包含解釋性內容
    output_steps = [s for s in steps if s.step_type == "output" or s.step_type == "recommendation"]
    for step in output_steps:
        if step.output_summary:
            summary = step.output_summary
            # 驗證 summary 含有 explanation 或 reason 欄位
            assert any(k in summary for k in ["explanation", "reason", "rationale"]), \
                f"output_summary 需含解釋性文字，現有 keys: {list(summary.keys())}"

async def test_full_trace_chain_from_database(service, db_session, sample_request):
    """完整 chain：DB → 還原 → 驗證所有步驟順序正確"""
    response = await service.create_recommendation(sample_request)
    trace_id = response.trace_id
    rec_id = response.recommendation_id
    
    # 關閉 session → 新 session（模擬 restart）
    await db_session.close()
    new_session = AsyncSession(engine)  # 需有 engine fixture
    
    # 從 DB 讀取完整 chain
    trace_repo = TraceRepository(new_session)
    rec_repo = RecommendationRepository(new_session)
    
    rec = await rec_repo.get_by_id(rec_id)
    assert rec is not None
    assert rec.trace_id == trace_id
    
    trace = await trace_repo.get_trace_by_recommendation_id(rec_id)
    assert trace is not None
    assert trace.trace_id == trace_id
    
    steps = await trace_repo.get_steps_by_trace_id(trace_id)
    assert len(steps) > 0
    
    # 驗證 step 順序正確（input → evidence → score → recommendation → output）
    step_types = [s.step_type for s in sorted(steps, key=lambda x: x.step_order)]
    expected_order = ["input", "evidence", "score", "recommendation", "output"]
    for expected, actual in zip(expected_order, step_types):
        if actual != expected:
            break  # 允許中間有額外步驟，但順序需合理
    
    await new_session.close()
```

---

### Batch G：Migration 驗證（T2）
- **負責角色**：db-modeler
- **目標**：alembic upgrade/downgrade/re-upgrade，驗證 FK/Index/JSONB
- **依賴**：無

#### 技術方案

**現狀**：`tests/test_migration.py` 已支援 upgrade → downgrade → upgrade again 循環。

**需更新**：
1. 若新增 018 migration，將 018 納入測試
2. 新增 FK/Index/JSONB 驗證：

```python
def test_migration_trace_fields(db_path):
    """測試新增的 trace 欄位 migration"""
    config = make_config(db_path)
    
    # upgrade to latest
    upgrade(config, "head")
    
    # 驗證新欄位存在
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("PRAGMA table_info(domain_recommendation_traces)")
    columns = {row[1]: row for row in cursor.fetchall()}
    assert "patient_id" in columns, "需有 patient_id 欄位"
    assert "status" in columns, "需有 status 欄位"
    assert "started_at" in columns, "需有 started_at 欄位"
    assert "completed_at" in columns, "需有 completed_at 欄位"
    
    cursor2 = conn.execute("PRAGMA table_info(domain_recommendation_trace_steps)")
    columns2 = {row[1]: row for row in cursor2.fetchall()}
    assert "duration_ms" in columns2, "需有 duration_ms 欄位"
    
    conn.close()
    
    # downgrade
    downgrade(config, "-1")
    
    # 驗證欄位已移除
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("PRAGMA table_info(domain_recommendation_traces)")
    columns = {row[1]: row for row in cursor.fetchall()}
    assert "patient_id" not in columns
    assert "status" not in columns
    conn.close()
    
    # re-upgrade
    upgrade(config, "head")
```

**FK 驗證**：
```python
# 取得所有 FK 資訊
cursor = conn.execute("PRAGMA foreign_key_list(domain_recommendation_traces)")
fks = cursor.fetchall()
# 驗證 recommendation_id → domain_recommendations.id FK 存在
assert any(fk[3] == "domain_recommendations" and fk[4] == "id" for fk in fks)
```

**Index 驗證**：
```python
cursor = conn.execute("PRAGMA index_list(domain_recommendation_traces)")
indices = [row[1] for row in cursor.fetchall()]
assert any("patient_id" in idx for idx in indices), "patient_id 需有 index"
```

---

### Batch H：完整驗證（T3）
- **負責角色**：exec-dev
- **目標**：backend build + unit tests + API tests + service tests + transaction tests + trace tests + Postgres tests + restart tests + frontend build + git diff --check
- **依賴**：A~G

#### 驗證命令

```bash
# Backend build
cd src/backend
pip install -e .  # 或 poetry install

# Run all tests
cd tests
pytest test_recommendation_service.py -v
pytest test_api_recommendation.py -v
pytest test_recommendation_transaction.py -v
pytest test_trace_persistence.py -v
pytest test_restart_recovery.py -v
pytest test_migration.py -v

# 若 Postgres 可用
pytest test_restart_recovery.py -v -k postgres

# Frontend build
cd src/frontend
npm run build

# Git diff 檢查
git diff --check
```

---

### Batch I：Git Commit & Push（T4）
- **負責角色**：exec-dev
- **目標**：單一 commit，訊息 `fix(phase3a): enforce atomic persistence and real restart recovery`
- **依賴**：H

#### 提交範圍確認

根據 requirements.md 的「提交範圍」：
- 只允許修改：`recommendation_service.py`、`recommendation.py` (API)、必要的 domain/repository、必要的 migration、新測試檔案、`tasks/` 文檔
- 不得修改無關檔案

**變更預估清單**：
| 檔案 | 變更類型 | 原因 |
|------|---------|------|
| `src/backend/services/recommendation_service.py` | 修改 | P0-1：raise RuntimeError；P0-3：補寫入欄位 |
| `src/backend/api/v1/recommendation.py` | 可能修改（若例外處理需補強） | P0-1 配套 |
| `src/backend/domain/recommendation.py` | 修改 | P0-3：Model 加欄位 |
| `migrations/versions/018_phase3a_trace_fields.py` | 新增 | P0-3：Migration |
| `tests/test_recommendation_transaction.py` | 新增 | Transaction Tests |
| `tests/test_restart_recovery.py` | 重寫 | P0-2：Restart Recovery Test |
| `tests/test_trace_persistence.py` | 重寫 | P0-3 驗證 |
| `tests/test_migration.py` | 修改（若需納入 018） | Migration 驗證 |
| `tasks/plan-phase3a-final-fix.md` | 新增 | 本計劃文件 |
| `tasks/requirements.md` | 可能修改 | 若需恢復/追加需求歷史 |

---

## 依賴圖

```
A (P0-1: persistence atomic) → B (API 500 驗證) → C (P0-3: trace persistence)
                                                       │
A → B → C → D (Transaction Tests)                     │
A → B → C → E (Restart Recovery Test)                 │
A → B → C → F (Trace Persistence Tests)               │
G (Migration 驗證，獨立)                               │
                                                       │
D + E + F + G → H (完整驗證) → I (Git Commit & Push)
```

## 返工預案

若任一 Batch 的 REVIEWER 評分 < 90，標記具體缺失項目，重新規劃該 Batch 的修正方案。

**常見返工原因與對策**：

| 返工原因 | 對策 |
|---------|------|
| Batch A 修正後仍有 persistence failure 回 200 | 檢查是否還有其他 code path 未修正（例如 `_persist_recommendation` 內部有 try/except 吞例外） |
| Batch C 的 Trace 欄位未完整寫入 | 檢查 `_persist_recommendation` 中 trace/step 寫入邏輯，確認每個欄位都有對應賦值 |
| Batch D/E 測試無法通過 | 檢查 mock/fixture 是否正確模擬失敗情境；檢查 service 依賴注入是否完整 |
| Batch E 的 Restart Test 無法驗證 engine 不同 | 檢查 app.state 是否有存 engine reference；若無則需在 create_app 中注入 |
| Batch G Migration downgrade 失敗 | 檢查 downgrade 的 `op.drop_column` 順序與 upgrade 相反 |

## 禁止事項

- 不得修改無關檔案（參見需求中的提交範圍）
- 不得修改 AGENTS.md
- 不得建立第二套測試架構
- 不得使用 SQLite 代替 Postgres 驗收（但可作為 fallback 方案，前提是 Postgres 環境不可用）
- 不得 skip / xfail 測試
- 不得 force push / rebase master
- ❌ 不得將 TraceManager 改為 DB 直接寫入（保持 in-memory cache 模式）
- ❌ 不得改動 API schema（RecommendationRequest/Response 功能正常）
- ❌ 不得重構整個 service（只針對 persistence failure 路徑修正）
