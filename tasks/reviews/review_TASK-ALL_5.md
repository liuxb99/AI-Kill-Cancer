# 評分報告 for TASK-ALL（第 5 次循環 — 最終）

**評分時間**: 2026-05-26T11:00:00+08:00  
**評分者**: reviewer-agent-005

---

## 評分檢查清單（必須 YES/NO）

| 項目 | 判定 | 說明 |
|------|------|------|
| 是否可執行 | **NO** | `src/backend/api/research.py:9` 從 `main.py` 匯入 `get_db`，導致**循環匯入**。`main.py` 匯入 `research.py`，`research.py` 又回頭匯入 `main.py`，應用程式完全無法啟動 |
| 是否有錯誤 | **NO**（有錯誤） | 除循環匯入外，另有至少 6 項測試錯誤與 14 項資料庫測試錯誤 |
| 是否滿足需求條列 | NO | 應用無法啟動，基本功能無法驗證 |
| 是否有測試或满足审美 | YES | 測試架構完整（72 個 collected），但多項測試未能通過 |

---

## 第 4 次評分修正驗證

第 4 次報告指出 5 項具體 assertion 問題：

| 問題 | 修正狀態 | 驗證結果 |
|------|----------|----------|
| 1. test_research_trends: `"years"` → `"publications"` | ✅ 已修正 | 原始碼中斷言已改為 `publications` + `funding` |
| 2. test_prediction_results: 頂層 precision/recall → 巢狀 | ✅ 已修正 | 斷言改為檢查 `accuracy` 陣列內 `precision`/`recall`/`f1` |
| 3. test_dashboard_kpis: 頂層欄位 → kpis 陣列 | ✅ 已修正 | 斷言改為檢查 `data["kpis"]` 內 `label`/`value`/`unit` |
| 4. test_submit_paper: DB 依賴 | ✅ 已處理 | 標記 `@pytest.mark.skip`（需 PostgreSQL） |
| 5. test_list_papers: DB 依賴 | ✅ 已處理 | 標記 `@pytest.mark.skip`（需 PostgreSQL） |

上述 5 項 assertion 問題**已正確修正**。但測試仍無法執行，因為存在更根本的**循環匯入錯誤**。

---

## 實際測試結果（2026-05-26 實測）

```
tests/test_api.py:    ERROR（循環匯入，無法收集任何測試）
tests/test_models.py: 49 passed, 9 failed
tests/test_database.py: 0 passed, 14 errors
```

### test_api.py（全部無法收集）
**根本原因**：循環匯入（fatal error）
- `src/backend/main.py:11` → `from src.backend.api.research import router`
- `src/backend/api/research.py:9` → `from src.backend.main import get_db`
- 結果：`ImportError: cannot import name 'get_db' from partially initialized module`

這是**致命錯誤**，FastAPI 應用完全無法啟動，`TestClient` 無法建立，所有 19 個 API 測試全部無法執行。

### test_models.py — 9 項失敗
1. `TestTrainer::test_train_epoch` — `batch["input"]` key 不存在（DataLoader 回傳 tuple 而非 dict）
2. `TestTrainer::test_validate` — 同上
3. `TestMoleculeVAE::test_vae_loss` — 形狀不匹配 `(2x32) vs (64x16)`，encoder 輸出維度與 mu/logvar head 不一致
4. `TestDrugDiscoveryPipeline::test_screen_empty_library` — `DTIPredictor()` 無 config 參數導致 `NoneType`
5. `TestMoleculeUtils::test_tanimoto_identical/zero/no_union`（3 項）— float32 陣列不支援 bitwise `&` 運算
6. `TestTreatmentRecommender::test_recommend` — batch_size=1 時 BatchNorm 拋出 ValueError
7. `TestTreatmentRecommender::test_recommend_unknown_cancer` — 同上

### test_database.py — 14 項錯誤（全部）
- 模型使用 PostgreSQL 專用 `ARRAY(String)` 類型 (models.py:44,85,120,125,127)
- 測試 fixture 使用 `sqlite:///:memory:`，SQLite 無法渲染 ARRAY 類型
- 加上 `UUID` 類型也來自 `sqlalchemy.dialects.postgresql`
- 資料庫模型與測試環境**完全不匹配**

---

## 評分明細

| 項目 | 分數 | 原因 |
|------|------|------|
| 完整性（25） | **0/25** | **直接歸零**（檢查清單「是否可執行」= NO，不可執行表示需求無法驗證） |
| 正確性（25） | **0/25** | **直接歸零**（同上） |
| 可維護性（25） | **0/25** | **直接歸零**（同上） |
| 測試與驗證（25） | **0/25** | **直接歸零**（同上） |

---

## 總分

**0 + 0 + 0 + 0 = 0/100**

**結果：不合格（低於 90 分）**

---

## 缺失項目與改進建議（最終清單）

### 🔴 致命（必須優先修復）
1. **循環匯入（app 無法啟動）**  
   `research.py` 應避免從 `main.py` 匯入 `get_db`。建議方案：
   - 將 `get_db` 移到獨立模組（如 `src/backend/database/__init__.py`）
   - 或在 `research.py` 中使用延遲匯入（lazy import）
   - 或將 `get_db` 改為 `Depends` 的 callable 定義在共用位置

### 🟡 嚴重
2. **資料庫模型與測試環境不兼容**  
   `ARRAY(String)` + `UUID` 僅支援 PostgreSQL，測試用 SQLite 無法建立 table。  
   建議：改用 `JSON` 取代 `ARRAY(String)`，或使用 `sqlalchemy_utils` 的相容類型

3. **9 項模型測試失敗**  
   - `tanimoto_similarity`：改為使用 `np.logical_and` / `np.logical_or`
   - `Trainer`：修正 `_train_epoch` 和 `_validate` 中對 batch 的索引方式
   - `DrugDiscoveryPipeline.__init__`：修正無參數建構時的 config 處理
   - `TreatmentRecommender`：訓練模式 + batch_size=1 時 BatchNorm 問題需處理

### 🟢 次要
4. 少數 passing 測試（49 項）架構良好，可保留

---

## 最終判定

**第 5 次評分（最終）：0/100 — 不合格**

由於循環匯入導致應用無法啟動，專案存在致命瑕疵。依多智能體協同規範第 12.2.7 節：

**返工次數已達 5 次上限，任務狀態設為「阻塞」，需人工介入。**

請開發團隊優先解決循環匯入問題後，重新啟動評分流程。
