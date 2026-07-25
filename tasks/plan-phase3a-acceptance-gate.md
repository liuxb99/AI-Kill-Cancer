# Phase 3A Final Acceptance Gate — 執行計劃

## 概覽

**目標**：關閉 Phase 3A 剩餘的兩個驗收缺口，使 CI 真正以 Postgres 運行整合測試，且 Trace 產生鏈使用真實 Pipeline 而非 Mock TraceManager。

**範圍**：僅處理以下兩個缺口：
1. GitHub Actions 真實 Postgres Integration Gate
2. 真實 Pipeline Trace 產生鏈

**原則**：Minimal Change / Final Acceptance Gate / One Focused Commit。

**現狀摘要**：
- `ci.yml` 已有 postgres:16-alpine service container，但 pytest 只跑 `tests/unit/ tests/integration/` 且 DATABASE_URL 雖指向 Postgres 但測試本身使用 SQLite（因為測試 fixture 覆寫了 config）
- `test_restart_recovery.py` 使用 file-based SQLite，無 Postgres 版本
- `test_trace_persistence.py` 使用 `MagicMock(spec=TraceManager)` 假造完整 trace steps，非真實 Pipeline

---

## 任務清單

### GATE-1：GitHub Actions Postgres Integration Gate
- **負責角色**：devops
- **目標**：使 `ci.yml` 真正以 Postgres 運行所有相關測試
- **修改檔案**：`.github/workflows/ci.yml`
- **技術方案**：

  1. **新增 Postgres 專用 pytest step**（不覆寫既有 step，避免 break 現有 tests/unit & tests/integration 的 SQLite 測試）：
     ```yaml
     - name: Postgres integration tests
       env:
         DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/cancer_db
         SKIP_MIGRATIONS: "0"
       run: |
         # 先跑 migration 確保 schema 存在
         alembic -c migrations/alembic.ini upgrade head
         # 跑所有需要 Postgres 的測試
         pytest -v --tb=short --cov=src/backend --cov-append \
           tests/test_restart_recovery.py \
           tests/test_trace_persistence.py
     ```

  2. **將 migration step 改為對 Postgres 執行**（現有 migration step 用 SQLite）：
     - 現有 `Test migration` step 的 `DATABASE_URL` 為 `sqlite+aiosqlite:///test_migration_ci.db`
     - 新增一個 `Postgres migration` step 使用 Postgres DATABASE_URL
     - 或直接將現有 migration step 改為 Postgres（但保留 SQLite 版本作為備用）

  3. **合併 coverage**：使用 `--cov-append` 讓 Postgres 測試的 coverage 追加到上一 step 的結果

  4. **注意點**：
     - Postgres service container 已配置 health check（pg_isready）
     - 測試檔案中的 fixture 需辨識 DATABASE_URL 環境變數，當為 Postgres 時使用 Postgres 而非 SQLite
     - `test_restart_recovery.py` 的 `db_url` fixture 需改為可感知 Postgres
     - `test_trace_persistence.py` 的 `db_setup` fixture 需改為可感知 Postgres

- **依賴**：無

---

### GATE-2：Postgres Restart Recovery
- **負責角色**：backend
- **目標**：使 `test_restart_recovery.py` 支援 Postgres 運行模式
- **修改檔案**：`tests/test_restart_recovery.py`
- **技術方案**：

  1. **新增 `db_url` fixture 的 Postgres 感知邏輯**：
     ```python
     @pytest.fixture
     def db_url(request) -> str:
         """根據 DATABASE_URL 環境變數選擇 SQLite 或 Postgres."""
         import src.backend.config as _config
         original_url = _config.settings.DATABASE_URL
         pg_url = os.getenv("DATABASE_URL", "")
         if pg_url and pg_url.startswith("postgresql"):
             # 使用 CI 提供的 Postgres URL（不可建立/刪除隨機資料庫）
             # 改為在固定 Postgres DB 中執行，測試完清理資料
             _config.settings.DATABASE_URL = pg_url
             yield pg_url
             _config.settings.DATABASE_URL = original_url
         else:
             # 維持原有 SQLite file-based 行為
             file_path = os.path.join(
                 os.path.dirname(__file__),
                 f"test_restart_{uuid.uuid4().hex}.db",
             )
             _config.settings.DATABASE_URL = f"sqlite+aiosqlite:///{file_path}"
             yield file_path
             _config.settings.DATABASE_URL = original_url
             if os.path.exists(file_path):
                 os.unlink(file_path)
     ```

  2. **在 Postgres 模式下**：
     - 由於 Postgres 不支援同一個 engine 連接兩個資料庫進行跨程序重啟測試，改用 **同一 engine 內跨 session 驗證**（類似 `test_trace_persistence.py` 中的 `test_cross_session_read_within_same_engine`）
     - 測試邏輯：
       1. App 1：建立資料（patient + recommendation）
       2. 關閉 session、dispose engine
       3. 建立新 engine 連接到同一 Postgres DB
       4. App 2：讀取相同 recommendation 確認資料完整性
     - 需確保 Postgres 模式下清理測試產生的資料（teardown 刪除建立的 records）

  3. **新增 `@pytest.mark.postgres` 標記**（可選），便於 CI 選擇性執行

  4. **不移除既有 SQLite 測試**—保留兩者並存

- **依賴**：無

---

### GATE-3：Real Pipeline Trace
- **負責角色**：backend
- **目標**：移除 `test_trace_persistence.py` 中的 Mock TraceManager，改用真實 Pipeline 產生 Trace
- **修改檔案**：`tests/test_trace_persistence.py`、`src/backend/services/recommendation_service.py`
- **技術方案**：

  #### 背景分析
  現有測試流程：
  1. `_make_mock_trace_manager(steps)` → 建立 `MagicMock(spec=TraceManager)`
  2. patch `TraceManager` → 回傳 mock
  3. patch `RecommendationEngine`、`DrugRankingEngine`、`ExplainableEngine`、`ReportGenerator`
  4. 執行 `Service.create_recommendation()` → mock TraceManager 回傳預先定義的 steps
  5. 驗證 DB 中的 trace steps 包含所需欄位

  問題：mock TraceManager 直接回傳預先拼好的 steps，完全跳過 Pipeline 的 trace 記錄邏輯。

  #### 修改方案

  **（A）Service 層新增 TraceManager injection 支援**（最小修改）：

  在 `RecommendationService.__init__` 或 `create_recommendation` 新增可選參數，允許注入外部 TraceManager：

  ```python
  class RecommendationService:
      def __init__(self, db: AsyncSession, trace_manager: TraceManager | None = None) -> None:
          self._db = db
          self._trace_manager = trace_manager  # 若未提供則在 create_recommendation 內部建立
          ...
      
      async def create_recommendation(self, request_data, user_id) -> dict:
          ...
          # 改為使用注入的或內部建立的
          trace_manager = self._trace_manager or TraceManager()
          trace = trace_manager.start_trace(patient_id=patient_id)
          ...
  ```

  或者更輕量的方式：在 `create_recommendation` 方法簽名新增 `trace_manager: TraceManager | None = None` 參數。

  **（B）測試改用真實 TraceManager + 真實 Pipeline（僅 mock EvidenceCollector）**：

  核心思路：**只 mock 最底層（EvidenceCollector），讓上層 Pipeline 全部真實執行**，這樣 Trace 由真實 Pipeline 產生。

  ```python
  @pytest_asyncio.fixture
  async def db_setup():
      """建立真實 SQLite 或 Postgres 資料庫與所有表."""
      ...
      # 同時建立 Evidence 種子資料讓 Collector 可以找到
      yield session, engine, str(patient_id), str(user_id)

  async def test_trace_evidence_references_persisted(self, db_setup):
      session, engine, patient_id, user_id = db_setup
      
      # 僅 mock EvidenceCollector.collect() 回傳預先建好的 EvidenceBundle
      # 讓 RecommendationEngine.run() 真實執行 aggregate → rank → rules
      # 從而產生真實的 Trace Steps
      mock_bundle = _make_evidence_bundle()
      
      with patch.object(EvidenceCollector, "collect", new_callable=AsyncMock) as mock_collect:
          mock_collect.return_value = mock_bundle
          
          service = RecommendationService(db=session)
          response = await service.create_recommendation(
              request_data=_get_request_data(patient_id),
              user_id=user_id,
          )
          
          # trace_id 應為真實產生的 UUID，而非 "mock-trace-batch-f"
          trace_id = response["trace_id"]
          assert trace_id is not None
          assert trace_id != "mock-trace-batch-f"
          
          # 從 DB 查詢 trace steps
          trace_repo = TraceRepository(session)
          trace = await trace_repo.get_trace_by_trace_id(trace_id)
          db_steps = await trace_repo.get_steps_by_trace_id(str(trace.id))
          
          # 驗證真實 Pipeline 產生的 trace 包含所需欄位
          evidence_steps = [s for s in db_steps if s.evidence_references is not None]
          assert len(evidence_steps) > 0
          ...
  ```

  **（C）如果 EvidenceCollector 依賴外部 API 導致測試不穩定**，則採用替代方案：
  
  在 `db_setup` 中直接寫入 Evidence 資料到 `evidence` 相關 table（若專案有本地 evidence 表），或者使用 **fake EvidenceCollector** 繼承自真實類別並覆寫 `collect`。

  **（D）廢除的 helper**：
  - 移除 `_make_mock_trace_manager()` — 不再使用 MagicMock TraceManager
  - 移除 `_sample_trace_steps()` — 不再使用預先定義的假 steps
  - 保留 `_make_pipeline_result()`、`_make_ranking_results()`、`_make_explanations()` — 但這些將改為真實 Pipeline 產生的資料，或作為 EvidenceBundle 的來源

  **（E）Trace 欄位映射驗證**：

  現有 Service 層 `_persist_recommendation` 已正確從 `step.output_data` 提取：
  ```python
  evidence_references=output_data.get("evidence_references"),
  weight=input_data.get("weight") or output_data.get("weight"),
  score=output_data.get("score"),
  rank=output_data.get("rank"),
  ```

  但真實 Pipeline 產生的 `output_data` 結構可能與 `_sample_trace_steps()` 不同。需要確認：
  - `collect_evidence` step 的 output_data 包含 `evidence_references`？目前 engine 的 `_record_trace_step` 僅輸出 `evidence_count` 和 `sources`，**不包含 `evidence_references`**
  - `rank_drugs` step 的 output_data 包含 `score` 和 `rank`？目前僅輸出 `ranking` list

  **因此需要補強 `recommendation_engine.py` 中的 `_record_trace_step` 呼叫**，在 output_data 中加入 `evidence_references`、`weight`、`score`、`rank` 等欄位，或者修改 `_persist_recommendation` 的提取邏輯以 match 真實 pipeline 的 output_data 結構。

- **依賴**：GATE-5（若需補強 _extract 映射）

---

### GATE-4：Real Trace Acceptance Test
- **負責角色**：backend
- **目標**：新增一個 acceptance test，端到端驗證真實 Pipeline 產生的 Trace 包含所有必要欄位
- **新增檔案**：`tests/test_acceptance_real_trace.py`
- **技術方案**：

  1. **測試場景**：
     - 建立完整的真實 Pipeline（僅 mock 外部 API 呼叫）
     - 執行 Service.create_recommendation()
     - 從 DB 讀取 trace steps
     - 驗證每個 step 的欄位完整性

  2. **核心驗證點**（對應 P0-3 需求）：
     - `evidence_references`：至少一個 step 有此欄位且非空
     - `weight`：至少一個 step 有此欄位且非空
     - `score`：至少一個 step 有此欄位且非空
     - `rank`：至少一個 step 有此欄位且非空
     - `explanation`：可從 `output_summary` 還原

  3. **測試方法**：
     ```python
     @pytest.mark.asyncio
     async def test_real_pipeline_trace_contains_all_required_fields(db_setup):
         """真實 Pipeline 產生的 trace 包含所有必要欄位."""
         session, engine, patient_id, user_id = db_setup
         
         with patch.object(EvidenceCollector, "collect", new_callable=AsyncMock) as mock_collect:
             mock_collect.return_value = _make_evidence_bundle()
             
             service = RecommendationService(db=session)
             response = await service.create_recommendation(
                 request_data=_get_request_data(patient_id),
                 user_id=user_id,
             )
             
             # 從 DB 讀取 trace
             trace_repo = TraceRepository(session)
             trace = await trace_repo.get_trace_by_trace_id(response["trace_id"])
             steps = await trace_repo.get_steps_by_trace_id(str(trace.id))
             
             # 驗證各欄位
             assert any(s.evidence_references for s in steps), "evidence_references 缺失"
             assert any(s.weight is not None for s in steps), "weight 缺失"
             assert any(s.score is not None for s in steps), "score 缺失"
             assert any(s.rank is not None for s in steps), "rank 缺失"
             assert any(
                 s.output_summary and ("explanations" in s.output_summary or "reason" in s.output_summary)
                 for s in steps
             ), "explanation 缺失"
     ```

  4. **`_make_evidence_bundle()` helper**：
     - 建立一個包含 `EvidenceItem` 的 `EvidenceBundle`
     - 包含至少一個 drug（如 "Osimertinib"）的證據
     - 包含 `evidence_references` 格式的資料（source, level, pmid）

  5. **同時支援 SQLite 和 Postgres 模式**（透過 DATABASE_URL 環境變數切換）

- **依賴**：GATE-3（確認真實 Pipeline 的 output_data 結構）

---

### GATE-5：Trace 欄位映射 Helper
- **負責角色**：backend
- **目標**：補強 Service 層的 `_extract`（或 `_persist_recommendation`）邏輯，確保真實 Pipeline 產生的 trace step 欄位能被正確映射到 `RecommendationTraceStepModel`
- **修改檔案**：`src/backend/services/recommendation_service.py`、`src/backend/clinical/recommendation_engine.py`
- **技術方案**：

  #### 問題分析
  現有 `_persist_recommendation` 從 `step.output_data` 提取欄位的方式：
  ```python
  evidence_references=output_data.get("evidence_references"),
  weight=input_data.get("weight") or output_data.get("weight"),
  score=output_data.get("score"),
  rank=output_data.get("rank"),
  ```

  但 `recommendation_engine.py` 中的 `_record_trace_step` 呼叫**並未在 output_data 中包含這些欄位**。真實 Pipeline 產生的 output_data 結構：
  - `collect_evidence` output：`{"evidence_count": N, "sources": [...]}` — **無 evidence_references**
  - `aggregate_evidence` output：`{"drug_count": N, "drugs": [...], "total_weight_by_drug": {...}}` — **無 evidence_references**
  - `rank_drugs` output：`{"ranking": [...]}` — **無 score 或 rank 在最外層**
  - `apply_rules` output：`{"rules_evaluated": N, "rules_fired": N, "fired_rule_ids": [...]}`
  - `assemble_output` output：`{"pipeline_status": "completed"}`

  因此，當 `_persist_recommendation` 嘗試從 output_data 提取 `evidence_references`、`score`、`rank` 時，會得到 `None`。

  #### 修改方案

  **（A）在 `recommendation_engine.py` 中補強 `_record_trace_step` 的 output_data**：

  在 `collect_evidence` 的 output_data 中加入 `evidence_references`：
  ```python
  _record_trace_step(
      self._trace_manager,
      trace_id,
      "collect_evidence",
      "input",
      output_data={
          "evidence_count": len(evidence_bundle.items),
          "sources": [...],
          "evidence_references": [
              {"source": item.source, "level": item.evidence_level, "pmid": item.source_record_id}
              for item in evidence_bundle.items[:10]  # 只取前 N 筆避免過大
          ],
      },
  )
  ```

  在 `rank_drugs` 的 output_data 中加入 `score` 和 `rank`：
  ```python
  _record_trace_step(
      self._trace_manager,
      trace_id,
      "rank_drugs",
      "score",
      output_data={
          "ranking": [...],
          "score": max(r.get("total_weight", 0) for r in ranked) if ranked else 0,
          "rank": 1,
      },
  )
  ```

  **（B）或在 `_persist_recommendation` 中改用更聰明的提取邏輯（從 input_data 和 output_data 中遞迴尋找）**：

  ```python
  @staticmethod
  def _extract_field(data: dict, *keys: str) -> Any:
      """從巢狀 dict 中遞迴提取第一個匹配的欄位值."""
      for key in keys:
          if key in data:
              return data[key]
          for v in data.values():
              if isinstance(v, dict):
                  result = _extract_field(v, key)
                  if result is not None:
                      return result
              elif isinstance(v, list) and v and isinstance(v[0], dict):
                  for item in v:
                      if key in item:
                          return item[key]
      return None
  ```

  **（C）建議方案**：**同時採用（A）和（B）**：
  - （A）確保 Engine 層在 output_data 中包含必要欄位（source of truth）
  - （B）作為 Service 層的防禦性提取（fallback）

  #### 具體修改
  
  **`src/backend/clinical/recommendation_engine.py`**：
  1. `collect_evidence`：在 output_data 中加入 `evidence_references`（從 evidence_bundle.items 提取）
  2. `aggregate_evidence`：在 output_data 中加入 `weight`（取最高 total_weight）
  3. `rank_drugs`：在 output_data 中加入 `score` 和 `rank`
  4. `apply_rules`：在 output_data 中加入 `score`（基於 rules_fired / rules_evaluated 比率）
  5. `assemble_output`：無需額外欄位

  **`src/backend/services/recommendation_service.py`**：
  1. 新增 `_extract_field` 靜態方法作為防禦性提取
  2. 在 `_persist_recommendation` 中使用 `_extract_field` 作為 fallback

- **依賴**：無（可獨立實作）

---

### GATE-6：完整驗證 + Git Commit & Push
- **負責角色**：devops / backend
- **目標**：確保所有修改通過本地驗證並提交
- **技術方案**：

  1. **本地執行驗證**：
     ```bash
     # 1. lint
     ruff check src/ tests/
     
     # 2. 現有測試（確保未 break）
     pytest -v --tb=short tests/unit/ tests/integration/
     
     # 3. Postgres 測試（若本地有 Postgres）
     set DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/cancer_db
     alembic -c migrations/alembic.ini upgrade head
     pytest -v --tb=short tests/test_restart_recovery.py tests/test_trace_persistence.py tests/test_acceptance_real_trace.py
     ```

  2. **Git Commit**：
     ```bash
     git add -A
     git commit -m "Phase 3A Final Acceptance Gate

     - ci.yml: add Postgres integration test step with real pg service
     - test_restart_recovery.py: support Postgres mode via DATABASE_URL
     - test_trace_persistence.py: replace Mock TraceManager with real pipeline
     - Add test_acceptance_real_trace.py for end-to-end trace verification
     - recommendation_engine.py: enrich trace step output_data with required fields
     - recommendation_service.py: add _extract_field helper for robust mapping

     Closes Phase 3A acceptance gaps.
     "
     ```

  3. **Push & 驗證 CI**：
     - Push 到 master/main 觸發 CI
     - 確認 Postgres integration tests step 為綠色
     - 確認所有測試以 Postgres 運行，無 skip/xfail

- **依賴**：GATE-1 到 GATE-5 全部完成

---

## 依賴關係

```mermaid
graph TD
    G5[GATE-5: Trace 欄位映射 Helper] --> G3[GATE-3: Real Pipeline Trace]
    G5 --> G4[GATE-4: Real Trace Acceptance Test]
    G3 --> G4
    G1[GATE-1: CI Postgres Gate] --> G2[GATE-2: Postgres Restart Recovery]
    G1 --> G3
    G1 --> G4
    G2 --> G6[GATE-6: 驗證 + Commit]
    G4 --> G6
```

- GATE-1（CI）是 GATE-2/3/4 的先決條件（CI 環境需要 Postgres service）
- GATE-5（欄位映射）建議在 GATE-3 之前或同時完成，因為 GATE-3 依賴正確的欄位映射
- GATE-2、GATE-3、GATE-4 可並行開發
- GATE-6 是最後整合步驟

---

## 返工預案

| 風險 | 影響 | 緩解措施 |
|------|------|----------|
| EvidenceCollector 依賴外部 API，mock 後 pipeline 行為與真實不同 | GATE-3/4 驗證不完整 | 使用 fake EvidenceCollector 繼承真實類別，僅覆寫 collect 方法 |
| Postgres service container 在 CI 中啟動但測試連線失敗 | GATE-1 失敗 | 加入 pg_isready retry loop；檢查 DATABASE_URL 格式 |
| 真實 Pipeline 產生的 trace steps 數量/結構與驗證期望不符 | GATE-3/4 assertion failed | 先調整 GATE-5 確保欄位映射正確；調整測試 assertion 以 match 實際 pipeline 輸出 |
| Test fixture 中 SQLite 與 Postgres 行為差異（如 autoincrement、UUID 型別） | 測試在 Postgres 下失敗 | 使用 `CompatUUID` 已在 model 層處理；注意 Postgres 的 UUID 型別比 SQLite 嚴格 |
| 跨 session 重啟測試在 Postgres 模式下無法完全模擬「重啟」（因為同一個 connection pool） | GATE-2 驗證不完整 | 改為建立兩個完全獨立的 engine instance（不同 connect args）來模擬重啟；或接受跨 session 驗證作為替代 |

---

## 總結

本計劃透過 6 個 Gate 關閉 Phase 3A 的兩個驗收缺口：

1. **CI 層面**：在 ci.yml 新增 Postgres 專用 pytest step，讓所有相關測試以真實 Postgres 運行
2. **測試層面**：改造 `test_restart_recovery.py` 支援 Postgres；改造 `test_trace_persistence.py` 使用真實 Pipeline Trace；新增 `test_acceptance_real_trace.py` 端到端驗證
3. **程式碼層面**：補強 Engine 層 trace step output_data 的欄位完整性；新增 Service 層的防禦性欄位提取邏輯

最終產出為一個 Focused Commit，包含所有修改，CI 完全通過。
