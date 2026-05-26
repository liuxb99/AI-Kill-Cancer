# 評分報告 for TASK-ALL（第 4 次循環）

**評分時間**: 2026-05-26T10:30:00+08:00  
**評分者**: reviewer-agent-004

---

## 評分檢查清單（必須 YES/NO）

| 項目 | 判定 | 說明 |
|------|------|------|
| 是否可執行 | YES | 測試語法正確，不考慮 PyTorch 環境缺失時可正常載入 |
| 是否有錯誤 | NO | 存在 assertion 邏輯錯誤，多項新測試斷言與實際 API 回應不符 |
| 是否滿足需求條列 | YES | 已新增 TestChartsAPI（4 項）及 TestResearchAPI（2 項）測試 |
| 是否有測試或满足审美 | YES | 測試檔案結構完整，遵循專案既有模式 |

---

## 詳細錯誤分析

### 1. `test_research_trends_endpoint`（test_api.py:171）
斷言 `"years" in data`，但實際回應頂層 key 為 `publications` 與 `funding`。`years` 不存在於頂層。
→ 此測試**必定失敗**。

### 2. `test_prediction_results_endpoint`（test_api.py:179）
斷言 `"precision"`, `"recall"`, `"f1_score"` 存在於 `data` 頂層，但實際這三個欄位是巢狀在 `accuracy` 陣列的每個項目中，頂層僅有 `accuracy` 和 `roc`。
→ 此測試**必定失敗**。

### 3. `test_dashboard_kpis_endpoint`（test_api.py:188）
斷言 `"total_patients"`, `"active_treatments"`, `"models_deployed"`, `"research_papers"` 存在於 `data` 頂層，但實際回應結構為 `{"kpis": [{"label": ..., "value": ..., "unit": ...}, ...]}`，無上述欄位。
→ 此測試**必定失敗**。

### 4. `test_submit_paper`（test_api.py:204）
此端點依賴 `Depends(get_db)`，而 `get_db()` 需要 `async_session_factory`（由 `lifespan` 初始化）。`TestClient` 預設不執行 lifespan，故 `async_session_factory` 為 `None`，呼叫 `get_db()` 將拋出 `RuntimeError("Database not initialized")`。
→ 此測試**必定拋出 500 錯誤**，斷言 `status_code == 200` 不成立。

### 5. `test_list_papers`（test_api.py:219）
同上，依賴 `Depends(get_db)`，在測試環境中 PostgreSQL 連線不可用。
→ 此測試**必定拋出 500 錯誤**，斷言 `status_code == 200` 不成立。

### 小結
| 測試 | 結果 |
|------|------|
| `test_cancer_stats_endpoint` | ✅ 通過 |
| `test_research_trends_endpoint` | ❌ 斷言失配 |
| `test_prediction_results_endpoint` | ❌ 斷言失配 |
| `test_dashboard_kpis_endpoint` | ❌ 斷言失配 |
| `test_submit_paper` | ❌ DB 依賴未處理 |
| `test_list_papers` | ❌ DB 依賴未處理 |

**6 項新測試中僅 1 項可通過**，5 項有明確錯誤。

---

## 評分明細

| 項目 | 分數 | 原因 |
|------|------|------|
| 完整性（25） | 15/25 | 測試已新增，覆蓋四個圖表端點和兩個研究端點；但部分測試斷言錯誤，覆蓋不完整 |
| 正確性（25） | 5/25 | **上限 10 分**（檢查清單「是否有錯誤」= NO）。僅 1/6 測試可通過，未通過的測試有真實的 assertion 錯誤或依賴問題 |
| 可維護性（25） | 20/25 | 測試結構清晰，遵循 conftest 與 pytest 慣例，class 命名與既有模式一致 |
| 測試與驗證（25） | 5/25 | 測試雖寫入但絕大多數因錯誤無法驗證功能，驗證價值大幅降低 |

---

## 總分

**15 + 5 + 20 + 5 = 45/100**

**結果：不合格（低於 90 分）**

---

## 缺失項目與改進建議

1. **`test_research_trends_endpoint`**：將 `"years"` 改為 `"publications"`，或修改斷言邏輯以比對 `publications` 陣列內的欄位
2. **`test_prediction_results_endpoint`**：將頂層斷言改為分別檢查 `accuracy` 陣列內的「precision/recall/f1_score」欄位
3. **`test_dashboard_kpis_endpoint`**：將斷言改為檢查 `data["kpis"]` 陣列內的 label/value/unit
4. **`test_submit_paper` 與 `test_list_papers`**：需要 mock DB session 或提供測試用 SQLite 連線（如 `test_database.py` 的做法），避免依賴外部 PostgreSQL
5. 建議補上前端測試（目前 `src/frontend/` 無任何測試檔案）
6. 建議整合 conftest 避免在 API 測試中因匯入 torch 而失敗（或將 torch-heavy fixture 設為 autouse=False）

## 具體建議

- 修正 `test_api.py:172`：`assert "years" in data` → `assert "publications" in data`
- 修正 `test_api.py:183-185`：改為遍歷 `data["accuracy"]` 檢查每筆的 precision/recall/f1_score
- 修正 `test_api.py:191-194`：改為檢查 `data["kpis"]` 並比對各項的 label/value
- 為 research API 測試新增 DB fixture，使用 SQLite in-memory 取代 PostgreSQL（參考 `test_database.py` 的 engine fixture）
