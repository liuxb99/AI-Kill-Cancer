# Architecture Review 補充計劃 — 返工第 4 次（R3）

## 目標
將架構審查報告從「涵蓋核心發現」（90/100）提升至「逐項全部列出，無一遺漏」（95+），滿足原始需求中每項 Review 項目都要求「全部列出」的規定。

## 現狀摘要

| 項目 | 現有狀態 | 待補充 |
|------|---------|--------|
| #1 Domain | ✅ 已逐檔案列出（26 個檔案） | 無 |
| #2 Repository | ⚠️ 僅指出 BaseRepository 預設 commit + Outbox 業務邏輯 | **需逐檔案檢查 commit/rollback/flush** |
| #3 Service | ⚠️ 僅指出事務邊界下沉問題 | **需逐 Service 列出 Transaction Boundary** |
| #4 Engine | ⚠️ 僅指出 RecommendationEngine.run() I/O 副作用 | **需逐 Engine 提供 Pure Function 判定** |
| #5 Migration | ⚠️ 僅指出 015/022/025 問題 | **需逐 Migration 列出 Upgrade/Downgrade/Re-upgrade 一致性** |
| #6 API | ⚠️ 僅指出 Error Response 格式與 HTTP Status 不一致 | **需逐 API 端點列出 HTTP Status/Error/Validation 狀態** |
| #7 Digital Thread | ⚠️ 僅指出 Patient Outbox 缺失 + Worker 缺少 Heartbeat | **需逐 Entity 列出事件鏈狀態** |
| #8 Trace | ✅ 已逐欄位列出 Schema 不一致 | 無 |
| #9 Graph Adapter | ✅ 已列出 Mapping 狀態 | 無 |
| #10 Tests | ✅ 已逐類別列出覆蓋 | 無 |
| #11 Dead Code | ✅ 已全專案掃描列出 | 無 |
| #12 Smell | ✅ 已逐項列出 | 無 |
| #13 Refactor | ✅ 已逐項列出 | 無 |

## 六項需補充的逐項清單

### 1. Repository — 逐檔案 commit/rollback/flush 清單（優先最高）

**範圍**：`src/backend/repositories/` 下所有 21 個檔案（含 base.py）

**檢查方式**：
```python
# 對每個 Repository 檔案 grep 以下關鍵字：
grep -n "commit\|rollback\|flush" src/backend/repositories/*.py
```

**輸出格式**（表格）：

| Repository 檔案 | 有 commit()？ | 有 rollback()？ | 有 flush()？ | 違規說明 |
|----------------|:-----------:|:--------------:|:-----------:|---------|
| `base.py` | ✅（預設） | ❌ | ✅（部分） | P0-03：BaseRepository.create/update/delete 預設 commit() |
| `patient_repo.py` | ❌ | ❌ | ❌ | 合規 |
| `variant_repo.py` | ❌ | ❌ | ❌ | 合規 |
| ... | ... | ... | ... | ... |
| `clinical_graph_outbox_repo.py` | ❌ | ❌ | ❌ | P0-04：雖無 commit，但混入業務邏輯 |

**驗收標準**：21 個 Repository 檔案每行皆有狀態記錄，違規者標註對應 P0/P1 編號。

---

### 2. Service — 逐 Service Transaction Boundary 清單

**範圍**：`src/backend/services/` 下所有 5 個 Service 檔案

**檢查方式**：檢查每個 Service 方法中 `AsyncSession` 的 `begin()` / `commit()` / `rollback()` 使用位置，確認交易只在 Service 層開啟，未下沉至 Engine/Repository。

**輸出格式**：

| Service 檔案 | 方法清單 | 交易邊界位置 | 合規？ | 說明 |
|-------------|---------|------------|:-----:|------|
| `recommendation_service.py` | create_recommendation, get_recommendation, ... | Service 層內部 | ❌ | 部分交易被 BaseRepository 預設 commit() 截斷 |
| `treatment_plan_service.py` | create_plan, _create_revision, ... | Service 層 | ⚠️ | 多處手動 try/commit，缺少 `@transactional` 裝飾器 |
| ... | ... | ... | ... | ... |

**驗收標準**：每個 Service 的每個公開方法都有交易邊界位置記錄。

---

### 3. Engine — 逐 Engine Pure Function 判定清單

**範圍**：`src/backend/clinical/*engine*.py` 共 4 個 Engine

**檢查方式**：對每個 Engine 檢查：
- 是否有 DB/API/Repository/Session 依賴
- 是否有 I/O 副作用（檔案寫入、網路呼叫）
- 是否 Stateless（無可變成員變數修改）

**輸出格式**：

| Engine 檔案 | 有 DB 依賴？ | 有 I/O 副作用？ | 有 State？ | Pure Function 判定 | 違規說明 |
|------------|:-----------:|:--------------:|:---------:|:-----------------:|---------|
| `recommendation_engine.py` | ❌ | ✅ Collector+TraceManager | ❌ | ❌ **Impure** | P1-01：`run()` 含 I/O 副作用 |
| `clinical_decision_engine.py` | ❌ | ❌ | ❌ | ✅ **Pure** | 但缺少 Trace（P2-08） |
| `treatment_plan_engine.py` | ❌ | ❌ | ❌ | ✅ **Pure** | 合規 |
| `tumor_board_engine.py` | ❌ | ❌ | ❌ | ✅ **Pure** | 合規 |

**驗收標準**：4 個 Engine 皆有明確的 Pure Function 判定，附判定依據。

---

### 4. Migration — 逐 Migration Upgrade/Downgrade/Re-upgrade 一致性清單

**範圍**：`migrations/versions/` 下 001~025 共 25 個 Migration 檔案

**檢查方式**：對每個 Migration 檢查：
- Upgrade 是否有對應的 Downgrade 方法
- Downgrade 是否完整反轉 Upgrade（冪等性）
- 若涉及 SQLite/PostgreSQL 差異，是否一致

**輸出格式**：

| Migration | Upgrade ✅ | Downgrade ✅ | Re-upgrade ✅ | SQLite/PG 一致？ | 違規說明 |
|:---------:|:---------:|:-----------:|:------------:|:---------------:|---------|
| 001 | ✅ | ✅ | ✅ | ✅ | — |
| 015 | ✅ | ⚠️ | ⚠️ | ✅ | P1-09：Downgrade 不冪等 |
| 017 | ✅ | ✅ | ✅ | ✅ | P2-09：trace_id UNIQUE 約束問題（非一致性命題） |
| 022 | ✅ | ⚠️ | ⚠️ | ✅ | P1-09：Downgrade 不冪等 |
| 025 | ✅ | ⚠️ | ⚠️ | ✅ | P1-09：Downgrade 不冪等 |

**驗收標準**：25 個 Migration 皆有 Upgrade/Downgrade 存在性檢查，違規者標註問題。

---

### 5. API — 逐端點 HTTP Status/Error/Validation 清單

**範圍**：`src/backend/api/v1/` 下所有端點檔案（~25 個檔案）

**檢查方式**：對每個 API 端點檢查：
- HTTP Status Code 是否語義正確（POST→201, GET→200, DELETE→204, 等）
- Error Response 格式是否統一
- Validation 是否在 API 層（而非 Service 層）

**輸出格式**：

| 端點路由 | HTTP Method | HTTP Status | Error 格式 | Validation 位置 | 合規？ | 說明 |
|---------|:----------:|:-----------:|:---------:|:--------------:|:-----:|------|
| `/recommendations` | POST | 200 ❌（應 201） | JSON: `{"detail":...}` | API 層 | ❌ | P1-08：POST 返回 200 |
| `/recommendations/{id}` | GET | 200 | JSON: `{"detail":...}` | API 層 | ✅ | — |
| `/patients` | POST | 201 | JSON: `{"detail":...}` | API 層 | ✅ | — |
| 更多... | ... | ... | ... | ... | ... | ... |

**驗收標準**：每個 API 端點皆有 HTTP Status/Error/Validation 三項記錄。

---

### 6. Digital Thread — 逐 Entity 事件鏈狀態清單

**範圍**：Patient / Recommendation / ClinicalDecision / Consensus / TreatmentPlan 五個 Entity

**檢查方式**：對每個 Entity 追蹤事件鏈完整性：Event → Outbox → Projection → KnowGraphGo

**輸出格式**：

| Entity | Event 建立 | Outbox 寫入 | Worker 消費 | KnowGraphGo 投射 | 狀態 |
|-------|:----------:|:----------:|:----------:|:---------------:|:----:|
| Patient | ❌ | ❌ | ❌ | ❌ | **缺失**（P1-06） |
| Recommendation | ✅ | ✅ | ✅ | ✅ | 完整 |
| ClinicalDecision | ✅ | ✅ | ✅ | ✅ | 完整 |
| Consensus | ✅ | ✅ | ✅ | ✅ | 完整 |
| TreatmentPlan | ✅ | ✅ | ✅ | ✅ | 完整 |

**驗收標準**：5 個 Entity 事件鏈皆有各階段狀態記錄。

---

## 補充方式

### 方法
1. **不修改現有 Sections**：現有報告結構保持不變，不刪改已存在的內容
2. **在現有報告末尾新增附錄**：在現有架構報告 `tasks/reviews/architecture_review.md` 末尾新增「附錄 C：逐項補充清單」
3. **附錄 C 包含上述 6 張表格**，每張表格前附簡要說明

### 執行順序（按收益遞減）
1. **Repository 逐檔案清單** — 評分報告明確指出為最大缺口
2. **API 逐端點清單** — 涉及面廣，25 個檔案的覆蓋提升明顯
3. **Migration 逐版本清單** — 25 個 Migration 檢查完整
4. **Service 逐方法清單** — 5 個 Service 交易邊界
5. **Engine 逐 Engine 判定** — 4 個 Engine，簡單明確
6. **Digital Thread 逐 Entity 清單** — 5 個 Entity 事件鏈

### 驗證指令
```bash
# Repository commit/rollback/flush 檢查
grep -n "\.commit\|\.rollback\|\.flush" src/backend/repositories/*.py

# Service transaction boundary 檢查
grep -n "begin\|commit\|rollback\|@transactional" src/backend/services/*.py

# Engine Pure Function 檢查
grep -n "from.*\.database\|from.*\.api\|from.*\.repositories\|Session\|session\|file\.write\|open(" src/backend/clinical/*engine*.py

# Migration 一致性檢查
ls migrations/versions/*.py | wc -l
for f in migrations/versions/*.py; do
  echo "=== $(basename $f) ==="
  grep -n "def upgrade\|def downgrade" "$f"
done

# API 端點 HTTP Status 檢查
grep -n "status_code\|@router\.get\|@router\.post\|@router\.patch\|@router\.delete" src/backend/api/v1/*.py

# Digital Thread 事件鏈檢查
grep -n "OutboxEvent\|outbox_event\|ClinicalGraphOutbox" src/backend/domain/*.py src/backend/services/*.py
```

---

## 驗收標準（95+ 必要條件）

| # | 標準 | 檢測方式 |
|---|------|---------|
| 1 | 21 個 Repository 檔案皆有 commit/rollback/flush 狀態行 | 對照附錄 C 表格與實際 grep 結果 |
| 2 | 5 個 Service 的公開方法皆有交易邊界位置記錄 | 對照附錄 C 表格 |
| 3 | 4 個 Engine 皆有 Pure Function 判定與依據 | 對照附錄 C 表格 |
| 4 | 25 個 Migration 皆有 Upgrade/Downgrade 存在性檢查 | 對照附錄 C 表格 |
| 5 | 所有 API 端點（約 25 個檔案）皆有 HTTP Status/Error/Validation 記錄 | 對照附錄 C 表格 |
| 6 | 5 個 Entity 事件鏈皆有完整狀態記錄 | 對照附錄 C 表格 |
| 7 | 不刪改原報告任何內容 | `diff` 僅顯示新增附錄 |
| 8 | 附錄 C 位置在報告末尾，有明確標題 | 文件結構檢查 |

---

*本計劃由 PLANNER(resume) 產出，用於 Architecture Review 報告返工第 4 次。*
