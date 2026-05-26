# 評分報告 for TASK-ALL（第 2 次循環）

**評分時間**: 2026-05-26T14:20:00+08:00
**評分者**: reviewer-agent

---

## 評分檢查清單（必須 YES/NO）

| 項目 | 判定 |
|------|------|
| 是否可執行 | YES |
| 是否有錯誤 | YES |
| 是否滿足需求條列 | NO |
| 是否有測試或满足审美 | YES |

---

## 第 1 次評分 8 項缺失修正審查

| # | 缺失項目 | 預期修正 | 現狀 | 結果 |
|---|---------|---------|------|------|
| 1 | docker/init.sql 缺失 | 建立 init.sql | `docker/init.sql` 已存在，含 patients / diagnoses / treatments 三表與 UUID 主鍵 | ✅ 已修正 |
| 2 | 前端 ResearchPortal 使用 mock 數據 | 改用真實 API 呼叫 | ResearchPortal.tsx 使用 `fetch(${API_BASE}/api/v1/...)` 呼叫後端端點 | ✅ 已修正 |
| 3 | agent_event_log.md 時間戳衝突 | 追加勘誤記錄 | 已追加 ERRATUM 記錄（14:10）說明重複記錄的修正 | ✅ 已修正 |
| 4 | main.py 未建立真實資料庫連線 | 加入 async engine + lifespan | main.py 已整合 `create_async_engine`、`async_session_factory`、`lifespan`，含 `Base.metadata.create_all` | ✅ 已修正 |
| 5 | src/tools/ 模組為空 | 實作工具函式 | `src/tools/utils.py` 含 `generate_id`、`load_json`、`save_json` | ✅ 已修正 |
| 6 | deploy.yml 使用 sshpass | 改用 SSH key | deploy.yml 使用 `DEPLOY_KEY` secret + `ssh-keyscan` + `ssh -i`，無 sshpass | ✅ 已修正 |
| 7 | 缺少 migration 機制 | 加入 Alembic 配置 | `migrations/` 含 `alembic.ini`、`env.py`（支援 async）、`script.py.mako` | ✅ 已修正 |
| 8 | 圖表數據硬編碼 | 部分改為 API 串接 | **CancerStats.tsx、ResearchTrends.tsx、PredictionResults.tsx、Dashboard.tsx KPI 仍全為硬編碼靜態資料** | ❌ 未修正 |

### 修正總結
- **8 項中 7 項已修正**（87.5%）
- **1 項未達標**：所有圖表元件（CancerStats、ResearchTrends、PredictionResults）及儀表板 KPI 卡片仍使用硬編碼數據，未串接任何 API 端點

---

## 其他觀察到的問題

1. **research.py 使用記憶體儲存**：`_papers`、`_sandbox_runs`、`_uploads` 為 in-memory list（附註 `# use real DB in production`），重啟後資料遺失，且與已建立的資料庫模型不對接
2. **routes.py /predict 仍為 mock 邏輯**：附註 `# Mock prediction logic`，未使用 `src/models/` 下的實際模型
3. **圖表元件無錯誤處理**：若改為 API 呼叫後，缺少 loading state 與錯誤邊界處理

---

## 評分明細

### 完整性（10/25）

**受檢查清單限制（「是否滿足需求條列」為 NO），最高 10 分。**

7/8 項修正已完成，但第 8 項（圖表數據串接 API）完全未處理。圖表是儀表板的核心功能，此缺失直接影響使用者體驗與系統可信度。

### 正確性（22/25）

代碼結構正確，無語法錯誤。資料庫模型設計合理（Patient → Diagnosis → Treatment → Drug），Pydantic schema 驗證完整，API 路由組織清晰。扣分原因：research.py 同時存在 Pydantic 模型與 in-memory dict 兩種資料表示，一致性不足。

### 可維護性（20/25）

專案目錄結構清晰，模組分工明確。主要扣分項目：
- `src/tools/utils.py` 功能過少（僅 3 個函式），未充分發揮工具模組價值
- chart 元件與業務邏輯耦合（硬編碼數據直接寫在元件內）
- research.py 的 mock runner 散落在同一檔案中，未抽離

### 測試與驗證（20/25）

具備：
- `tests/test_api.py`：覆蓋 health、predict、recommend、research 端點，含邊界測試
- `tests/conftest.py`：提供 fixture 與 mock session
- `tests/test_database.py`、`test_models.py` 存在

扣分原因：
- 缺少圖表元件的測試（雖然圖表為展示層，但可考慮 snapshot 測試）
- 無集成測試驗證 frontend ↔ backend 連通性

---

## 總分

| 項目 | 分數 |
|------|------|
| 完整性 | 10/25 |
| 正確性 | 22/25 |
| 可維護性 | 20/25 |
| 測試與驗證 | 20/25 |
| **總分** | **72/100** |

## 結果

**不合格（低於 90 分）**

---

## 缺失項目與改進建議

### 必須修正（影響評分為 NO 的項目）
1. **圖表數據改為 API 串接**：為 CancerStats、ResearchTrends、PredictionResults 建立後端 API 端點，前端 chart 元件改為非同步 fetch，並加入 loading / error state

### 建議改善
2. **research.py 串接資料庫**：將 in-memory stores 改為使用 SQLAlchemy session 與已定義的 ORM 模型
3. **routes.py 整合 ML 模型**：將 `/predict` mock 邏輯替換為 `src/models/` 下的實際推論調用
4. **補上圖表 error boundary**：所有資料展示元件加入 `Suspense` 或條件渲染的錯誤處理
