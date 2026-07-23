# Phase 2 修復計劃 — 六大修復項目執行計劃

> **基線**: 當前最新 commit `60b2ec3`（已刪除 config/env.go 等無關 Go 文件）  
> **工作目錄**: `agent_workflow.md` 和 `agent_workflow_History.md` 有未暫存修改  
> **狀態**: Phase 2 核心開發已完成（評分 94/100 ✅），但存在六個需修復的品質/安全/部署問題

---

## 目錄

1. [REPAIR-1: Phase 2 Scope Cleanup](#repair-1-phase-2-scope-cleanup)
2. [REPAIR-2: Clinical Logic Audit — Evidence 狀態模型改進](#repair-2-clinical-logic-audit--evidence-狀態模型改進)
3. [REPAIR-3: Authorization Audit](#repair-3-authorization-audit)
4. [REPAIR-4: Database Persistence Verification](#repair-4-database-persistence-verification)
5. [REPAIR-5: Migration Verification](#repair-5-migration-verification)
6. [REPAIR-6: Vercel Deployment Repair](#repair-6-vercel-deployment-repair)
7. [依賴關係圖](#依賴關係圖)
8. [執行順序建議](#執行順序建議)

---

## REPAIR-1: Phase 2 Scope Cleanup

| 欄位 | 值 |
|------|------|
| **任務 ID** | REPAIR-1 |
| **名稱** | 清理 config/ 目錄殘留及 Go 相關引用 |
| **描述** | 確認 config/ 目錄下無殘留 LlamaEnv/Go 相關內容，並用 git grep 確認無殘留引用 |
| **負責角色** | backend-logic |
| **依賴** | 無 |
| **預計工時** | 1h |

### 現狀

commit `60b2ec3` 已刪除以下 Go 文件：
- `config/env.go`
- `config/loader.go`
- `config/types.go`
- `config/unsloth-env.go`

當前 `config/` 目錄下僅有：
- `auto-mode.md`（291B）
- `default-mode.md`（320B）
- `role-library.md`（859B）
- `write-spec.md`（136B）

### 執行步驟

#### Step 1.1: 確認 config/ 目錄無 Go 文件

- **命令**: 遍歷 `config/` 目錄確認無 `.go` 文件
- **驗證**: `ls config/` 應只返回上述 4 個 `.md` 文件

#### Step 1.2: git grep 確認無殘留引用

- **範圍**: 全代碼庫（含 `src/`、`tests/`、`config/`）
- **搜索模式**:
  ```
  模式 1: "\.go" | "config/env" | "config/loader" | "config/types" | "LlamaEnv"
  模式 2: "Golang" | "golang" | "config/env.go"
  ```
- **預期**: 僅 `ClinicalTrials.gov` 等無關匹配，無 Go 相關引用
- **注意**: 前述 grep 結果顯示所有 `.go` 匹配均為 `.gov`（ClinicalTrials.gov），非 Go 代碼引用

#### Step 1.3: 清理任何殘留（如有發現）

- **操作**: 若 Step 1.2 發現殘留 import/引用，移除對應行
- **注意**: 當前分析未發現殘留，此步可能為空操作

### 修改檔案清單

| 文件 | 操作 | 說明 |
|------|------|------|
| `config/` | 僅檢查 | 確認無 `.go` 文件 |
| 無 | 不修改 | 預期無需代碼修改 |

### 驗收標準

1. ✅ `config/` 目錄下無 `.go` 文件
2. ✅ `git grep "\.go"` 僅返回 `ClinicalTrials.gov` 等無關匹配
3. ✅ `git grep "config/env\|config/loader\|config/types\|LlamaEnv"` 返回空
4. ✅ `git grep "Golang\|golang"` 返回空

---

## REPAIR-2: Clinical Logic Audit — Evidence 狀態模型改進

| 欄位 | 值 |
|------|------|
| **任務 ID** | REPAIR-2 |
| **名稱** | 證據收集器授權狀態模型改進 |
| **描述** | 建立 SourceStatus 模型，讓 NCCN/ESMO/OncoKB 等授權來源的狀態明確化，而非僅在 log 中 warning |
| **負責角色** | db-modeler + backend-logic |
| **依賴** | REPAIR-1 |
| **預計工時** | 4h |

### 現狀分析

- `src/backend/clinical/collector.py` 第 30-31 行：`_AUTH_SOURCES = ("nccn", "esmo", "oncokb")`
- `collect()` 方法在遍歷完所有基因後（第 93-99 行）為每個授權來源寫 `logger.warning()`
- `collect_by_variant()` 同樣僅在末尾 warning（第 179-185 行）
- `EvidenceBundle`（`evidence_models.py`）沒有追蹤哪個來源可用/不可用/需授權

**問題**: 下游調用者無法從 `EvidenceBundle` 得知：
1. 哪些來源被查詢了
2. 哪些來源因授權限制被跳過
3. 哪些來源查詢失敗

### 設計方案

#### 新增 SourceStatus 枚舉/模型

在 `src/backend/clinical/evidence_models.py` 中新增：

```python
from enum import Enum
from typing import Optional

class SourceStatusType(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    AUTHORIZATION_REQUIRED = "authorization_required"
    ERROR = "error"

class SourceStatus(BaseModel):
    """Status of a knowledge source after a collection attempt."""
    source_name: str
    status: SourceStatusType
    message: Optional[str] = None
    items_count: int = 0
```

#### 修改 EvidenceBundle

在 `EvidenceBundle` 中新增 `source_statuses` 字段：

```python
class EvidenceBundle(BaseModel):
    items: list[EvidenceItem] = Field(default_factory=list)
    source_statuses: list[SourceStatus] = Field(default_factory=list)
    # ... 現有字段保持不變
```

#### 修改 EvidenceCollector

在 `collect()` 和 `collect_by_variant()` 中：
1. 對每個來源（CIViC、ClinVar、PubMed、ClinicalTrials.gov）記錄 `SourceStatus(status=AVAILABLE)` 或 `SourceStatus(status=ERROR)` 
2. 對授權來源（NCCN、ESMO、OncoKB）記錄 `SourceStatus(status=AUTHORIZATION_REQUIRED, message="API key / licence required")`
3. 將 `source_statuses` 列表傳入 `EvidenceBundle`

### 修改檔案清單

| 文件 | 操作 | 說明 |
|------|------|------|
| `src/backend/clinical/evidence_models.py` | 修改 | 新增 `SourceStatusType` 枚舉、`SourceStatus` 模型；修改 `EvidenceBundle` 加 `source_statuses` 字段 |
| `src/backend/clinical/collector.py` | 修改 | 在 `collect()` 和 `collect_by_variant()` 中收集來源狀態；移除單純的 `logger.warning` |
| `tests/unit/test_evidence_collector.py` | 修改 | 新增測試驗證 `source_statuses` 正確填充 |

### 驗收標準

1. ✅ `SourceStatusType` 枚舉包含 `available` / `unavailable` / `authorization_required` / `error`
2. ✅ `SourceStatus` 模型包含 `source_name`、`status`、`message`、`items_count`
3. ✅ `EvidenceBundle.source_statuses` 在 `collect()` 返回時包含所有查詢來源的狀態
4. ✅ 授權來源（NCCN/ESMO/OncoKB）狀態為 `authorization_required`
5. ✅ 查詢成功的來源狀態為 `available`
6. ✅ 查詢失敗的來源狀態為 `error`（含錯誤信息）
7. ✅ 不破壞現有測試

---

## REPAIR-3: Authorization Audit

| 欄位 | 值 |
|------|------|
| **任務 ID** | REPAIR-3 |
| **名稱** | API 端點授權審計與 authorization matrix 測試 |
| **描述** | 審核所有 v1 API 端點的授權裝飾器，建立 authorization matrix 測試確保每個端點都有正確的權限控制 |
| **負責角色** | api-designer + test-writer |
| **依賴** | REPAIR-1 |
| **預計工時** | 6h |

### 現狀分析

- `src/backend/api/v1/router.py` 包含 17 個子路由模組
- `src/backend/api/v1/clinical.py` 中：
  - 所有端點使用 `Depends(require_case_access(CaseRole.VIEWER))` ✅
  - GET `/evidence/gene/{gene_symbol}` 使用 `Depends(require_auth)` ⚠️（缺少 case-level 權限檢查）
  - GET `/thread/node/{node_id}` 使用 `Depends(require_auth)` ⚠️（但手動調用 `verify_case_access`）
- 已有測試 `tests/integration/test_authorization.py` 和 `tests/test_authorization_hardening.py`
- `tests/test_authorization_hardening.py` 中的 `TestRouteSecurityCoverage` 檢查所有 v1 路由是否有 auth

### 執行步驟

#### Step 3.1: 審核所有 v1 路由的授權裝飾器

檢查 `src/backend/api/v1/` 下所有路由文件：

| 路由文件 | 端點數 | 須檢查 |
|---------|--------|--------|
| `clinical.py` | 10 | ✅ |
| `cases.py` | 待審 | |
| `patients.py` | 待審 | |
| `analyses.py` | 待審 | |
| `evidence.py` | 待審 | |
| `ranking.py` | 待審 | |
| `knowledge.py` | 待審 | |
| `reasoning.py` | 待審 | |
| `reports.py` | 待審 | |
| `workbench.py` | 待審 | |
| `variants.py` | 待審 | |
| `specimens.py` | 待審 | |
| `sequencing.py` | 待審 | |
| `uploads.py` | 待審 | |
| `upload_vcf.py` | 待審 | |
| `case_acl.py` | 待審 | |

#### Step 3.2: 建立 authorization matrix

建立一個全面的 authorization matrix 表格，包含：

| 端點 | 方法 | 當前授權 | 最少所需角色 | 審計結果 |
|------|------|---------|-------------|---------|
| `GET /clinical/context/{case_id}` | GET | `require_case_access(VIEWER)` | VIEWER | ✅ |
| `GET /clinical/evidence/{case_id}` | GET | `require_case_access(VIEWER)` | VIEWER | ✅ |
| `GET /clinical/evidence/gene/{gene}` | GET | `require_auth` | VIEWER | ⚠️ 應改為 case-level |
| `POST /clinical/agents/{case_id}` | POST | `require_case_access(VIEWER)` | VIEWER | ✅ |
| ... | | | | |

#### Step 3.3: 補充 authorization matrix 測試

在 `tests/test_authorization_hardening.py` 中新增或加強：

```python
class TestAuthorizationMatrix:
    """Verify every endpoint has the correct authorization decorator."""
    
    # 定義完整的授權期望矩陣
    AUTH_MATRIX = {
        ("GET", "/api/v1/clinical/context/{case_id}"): "require_case_access",
        ("POST", "/api/v1/clinical/analyze/{case_id}"): "require_case_access",
        # ... 完整覆蓋所有端點
    }
    
    def test_every_endpoint_has_expected_auth(self):
        """Verify auth decorator matches expectation."""
        ...
```

#### Step 3.4: 修復任何發現的授權缺漏

若 Step 3.1 發現缺少授權的端點：
1. 添加缺失的 `require_auth` 或 `require_case_access` 裝飾器
2. 更新對應測試

### 修改檔案清單

| 文件 | 操作 | 說明 |
|------|------|------|
| `src/backend/api/v1/clinical.py` | 可能修改 | 若發現授權缺漏則修復 |
| `src/backend/api/v1/*.py` | 審計僅 | 審計所有路由文件（視發現決定是否修改） |
| `tests/test_authorization_hardening.py` | 增強 | 新增 AuthorizationMatrix 測試類 |
| `tests/integration/test_authorization.py` | 可能增強 | 補充 case-level 測試 |

### 驗收標準

1. ✅ 所有 v1 API 端點都有授權裝飾器（無遺漏）
2. ✅ Authorization matrix 測試完整覆蓋所有端點
3. ✅ `GET /evidence/gene/{gene_symbol}` 至少使用 `require_auth`（無法 case-level，因無 case_id）
4. ✅ 每種 HTTP 方法（GET/POST/PUT/DELETE）都有對應的權限檢查
5. ✅ 測試通過 `pytest tests/test_authorization_hardening.py`
6. ✅ 測試通過 `pytest tests/integration/test_authorization.py`

---

## REPAIR-4: Database Persistence Verification

| 欄位 | 值 |
|------|------|
| **任務 ID** | REPAIR-4 |
| **名稱** | 資料庫持久化驗證與 session reload 測試 |
| **描述** | 檢查 DecisionNodeModel 和 ClinicalContext 的持久化邏輯，設計 session reload 測試確保資料正確保存與讀取 |
| **負責角色** | db-modeler + test-writer |
| **依賴** | REPAIR-1 |
| **預計工時** | 6h |

### 現狀分析

#### DecisionThreadRepository（`decision_thread.py`）

- `create_node()` 第 200-203 行：
  ```python
  self.db.add(model)
  await self.db.commit()
  await self.db.refresh(model)
  ```
- 使用 `expire_on_commit=False`（`session.py` 第 20 行），這意味著 commit 後對象不會自動過期
- get_case_thread() 直接查詢，無特別 session 管理

#### ClinicalContext（`models.py`）

- 純 Pydantic 模型，不是 SQLAlchemy ORM 模型
- 不直接持久化到資料庫（由 API 端點序列化返回）
- `freeze()` 方法計算 context_hash

#### 資料庫 Session 模式（`session.py`）

- `get_db()` 使用 `async_session_factory()` context manager
- `expire_on_commit=False`
- 無顯式事務回滾處理（僅 finally 中 close）

### 執行步驟

#### Step 4.1: 審計 DB session 使用模式

檢查所有使用 `AsyncSession` 的文件：

| 文件 | 使用模式 | 潛在問題 |
|------|---------|---------|
| `src/backend/clinical/decision_thread.py` | `commit()` + `refresh()` | ⚠️ 需要確認 refresh 後字段完整 |
| `src/backend/clinical/collector.py` | 僅接收 db，不寫入 | ✅ |
| `src/backend/clinical/builder.py` | 僅查詢 | ✅ |
| `src/backend/api/v1/clinical.py` | 通過 Depends(get_db) 獲取 | ✅ |
| `src/backend/database/session.py` | async context manager | ⚠️ 無 rollback 處理 |

#### Step 4.2: 修復 session 管理器（如有需要）

若 Step 4.1 發現問題：
- 在 `get_db()` 中增加異常時的 rollback 處理
- 確保 session 始終正確關閉

#### Step 4.3: 設計 session reload 測試

在 `tests/unit/test_decision_thread.py` 中新增：

```python
class TestSessionReload:
    """Verify database session reload works correctly."""
    
    async def test_create_node_then_reload(self):
        """Create a node, then reload from a fresh session to verify persistence."""
        # 使用測試資料庫 fixture
        # 1. 在 session A 中建立 node
        # 2. commit + refresh
        # 3. 在 session B 中查詢同一 node
        # 4. 驗證所有欄位正確保存
        pass
    
    async def test_node_fields_persisted_correctly(self):
        """Verify each field type survives a round-trip."""
        # UUID, datetime, JSON, Text, String 各類型
        pass
```

**注意**: 由於當前測試使用 mock DB（`AsyncMock`），真正的 session reload 測試需要：
- 方案 A：使用測試專用 SQLite（async）資料庫
- 方案 B：保持 mock 測試，但驗證 `commit()` 和 `refresh()` 被正確調用
- 建議：方案 B 先通過（快速），方案 A 作為整合測試補充

#### Step 4.4: 驗證 ClinicalContext 非持久化但 context_hash 一致

- 確認 `ClinicalContext` 不是 ORM 模型（設計如此，無需修改）
- 驗證 `freeze()` 產生一致的 context_hash
- 確認現有測試已覆蓋 hash 一致性

### 修改檔案清單

| 文件 | 操作 | 說明 |
|------|------|------|
| `src/backend/database/session.py` | 可能修改 | 增加 rollback 處理 |
| `tests/unit/test_decision_thread.py` | 增強 | 新增 SessionReload 測試類 |
| `tests/integration/test_phase2_api.py` | 可能增強 | 補充 DB round-trip 測試 |

### 驗收標準

1. ✅ DB session 在異常時能正確 rollback 和關閉
2. ✅ DecisionNode 所有欄位類型（UUID、datetime、JSON、Text）正確持久化
3. ✅ commit → refresh → 重新查詢 週期完整驗證
4. ✅ 現有單元測試全部通過（mock DB）
5. ✅ 新增的 session reload 測試通過（mock 或真實 DB）

---

## REPAIR-5: Migration Verification

| 欄位 | 值 |
|------|------|
| **任務 ID** | REPAIR-5 |
| **名稱** | 資料庫遷移腳本驗證與 upgrade → downgrade → upgrade 測試 |
| **描述** | 讀取並驗證 migration 016 腳本，規劃升級→降級→升級循環測試確保可逆性 |
| **負責角色** | db-modeler |
| **依賴** | REPAIR-1 |
| **預計工時** | 3h |

### 現狀分析

`migrations/versions/016_phase2_clinical_workspace.py`：
- 創建 4 張表：`clinical_decision_nodes`、`clinical_agent_opinions`、`clinical_consensus_results`、`clinical_recommendations`
- 使用 `sa.String(36)` 作為 UUID 主鍵（非 `CompatUUID`，與模型層的 `CompatUUID` 不一致）
- Foreign key：`case_id` → `domain_cancer_cases.id`（CASCADE DELETE）
- Foreign key：`parent_id` → `clinical_decision_nodes.id`（SET NULL）
- downgrade() 按創建順序反向 drop 表

### 潛在問題

1. **UUID 類型不一致**：遷移腳本用 `sa.String(36)`，但 `DecisionNodeModel` 第 48 行用 `CompatUUID`。雖然 Python 層會處理轉換，但資料庫層缺少 UUID 類型約束。
2. **無索引創建**：除了 `case_id` 和 `context_hash` 索引（通過 `index=True`），無其他性能索引。
3. **無初始數據**：遷移僅創建表結構，無 seed data。

### 執行步驟

#### Step 5.1: 審計遷移腳本

逐行檢查 `016_phase2_clinical_workspace.py`：

| 檢查項 | 當前狀態 | 建議 |
|--------|---------|------|
| `sa.String(36)` vs `CompatUUID` | 不一致 | ⚠️ 可改為 `sa.String(36)` 以匹配模型層的字符串 UUID |
| Foreign key 正確性 | ✅ domain_cancer_cases.id | 正確 |
| CASCADE 策略 | ✅ DELETE / SET NULL | 正確 |
| 索引覆蓋 | ⚠️ 僅 case_id + context_hash | 可考慮新增 run_id 索引 |
| downgrade 完整 | ✅ 4 張表都 drop | 正確 |
| 類型長度 | String(36) 對於 UUID 足夠 | 正確 |

#### Step 5.2: 規劃 upgrade → downgrade → upgrade 測試

建立測試腳本 `tests/integration/test_migration_016.py`：

```python
class TestMigration016:
    """Test migration 016 upgrade → downgrade → upgrade cycle."""
    
    async def test_upgrade_downgrade_cycle(self):
        """Run upgrade() then downgrade() then upgrade() again."""
        # 使用 Alembic 配置與測試資料庫
        # 1. 確認當前版本為 015
        # 2. 執行 upgrade()
        # 3. 驗證 4 張表存在
        # 4. 執行 downgrade()
        # 5. 驗證 4 張表已刪除
        # 6. 再次執行 upgrade()
        # 7. 驗證 4 張表再次存在
        pass
    
    async def test_upgrade_creates_tables_with_expected_columns(self):
        """Verify each table has the expected columns and types."""
        pass
    
    async def test_downgrade_removes_tables(self):
        """Verify downgrade removes all 4 tables."""
        pass
```

**注意**: 此測試需要真實資料庫連接。方案：
- 方案 A（推薦）：使用 SQLite（Alembic 支援 SQLite 的 upgrade/downgrade）
- 方案 B：使用測試 PostgreSQL 實例
- 方案 C：純語法驗證（在不實際執行 migration 的情況下驗證腳本語法）

#### Step 5.3: 修復任何發現的問題

若 Step 5.1 發現問題：
1. 統一 UUID 類型（遷移腳本 + 模型層一致）
2. 補充缺失的索引
3. 確保 upgrade → downgrade 完全逆操作

### 修改檔案清單

| 文件 | 操作 | 說明 |
|------|------|------|
| `migrations/versions/016_phase2_clinical_workspace.py` | 可能修改 | 修復 UUID 類型不一致、補充索引 |
| `tests/integration/test_migration_016.py` | 新增 | migration 循環測試 |

### 驗收標準

1. ✅ upgrade() 成功創建 4 張表
2. ✅ downgrade() 成功刪除 4 張表
3. ✅ upgrade → downgrade → upgrade 循環不報錯
4. ✅ 每張表的欄位數量、名稱、類型正確
5. ✅ 外鍵約束正確（指向 `domain_cancer_cases.id`）
6. ✅ 級聯策略正確（CASCADE DELETE / SET NULL）

---

## REPAIR-6: Vercel Deployment Repair

| 欄位 | 值 |
|------|------|
| **任務 ID** | REPAIR-6 |
| **名稱** | Vercel 部署診斷與修復 |
| **描述** | 讀取 vercel.json，診斷可能的部署失敗原因，規劃修復方案 |
| **負責角色** | devops |
| **依賴** | 無（可與其他任務並行） |
| **預計工時** | 4h |

### 現狀分析

`vercel.json`：
```json
{
  "buildCommand": "cd src/frontend && npm ci && npm run build",
  "outputDirectory": "src/frontend/dist",
  "installCommand": "cd src/frontend && npm ci"
}
```

### 潛在失敗原因診斷

#### 問題 1: Root 目錄與 Frontend 子目錄結構

- Vercel 默認從根目錄構建，但專案結構是 monorepo（後端 Python + 前端 Node.js）
- `vercel.json` 指定 `cd src/frontend` 來定位前端
- **風險**: Vercel 的 `installCommand` 和 `buildCommand` 都從根目錄執行，`cd src/frontend` 可能與 Vercel 的 workspace 檢測衝突

#### 問題 2: npm ci 依賴安裝

- `npm ci` 需要 `package-lock.json` 存在且與 `package.json` 一致
- **風險**: 若 lockfile 未提交或過時，`npm ci` 會失敗
- **確認點**: `src/frontend/package-lock.json` 是否存在

#### 問題 3: 構建產物目錄

- `outputDirectory: "src/frontend/dist"` — Vercel 需要將此目錄部署為靜態站點
- **風險**: Vercel 的默認輸出目錄是相對於根目錄的，若 vite 配置將輸出寫入不同路徑則不匹配

#### 問題 4: API Routes 缺失

- Vercel 需要 `api/` 目錄或 `vercel.json` 中的 `rewrites` 配置來處理後端 API
- 當前 `vercel.json` 無 `rewrites` 或 `functions` 配置
- **風險**: 前端靜態頁面可部署，但後端 API 調用會 404

### 執行步驟

#### Step 6.1: 確認 Frontend 構建配置

檢查 `src/frontend/` 目錄結構：

```
src/frontend/
├── package.json
├── package-lock.json      (是否存在？)
├── vite.config.ts         (構建設置)
├── tsconfig.json
├── src/
│   ├── main.tsx
│   └── ...
└── dist/                  (構建產物)
```

#### Step 6.2: 診斷 npm ci 可行性

- **檢查**: `src/frontend/package-lock.json` 是否存在且有效
- **檢查**: `package.json` 中的 scripts: `build` 命令是否正確

#### Step 6.3: 檢查 Vite 輸出配置

- **檢查**: `vite.config.ts` 中的 `outDir` 是否為 `dist`
- **檢查**: 相對路徑 vs 絕對路徑問題

#### Step 6.4: 規劃 API Proxy 配置

Vercel 部署前端靜態站點時，需要配置 API 請求代理：
- 方案 A: 在 `vercel.json` 中增加 `rewrites` 將 `/api/*` 代理到後端服務
- 方案 B: 使用 Vercel Serverless Functions（需要 Node.js adapter）
- 方案 C: 分離部署（前端 Vercel + 後端獨立服務器）

```json
{
  "rewrites": [
    { "source": "/api/(.*)", "destination": "https://backend.example.com/api/$1" }
  ]
}
```

#### Step 6.5: 修復並測試

根據診斷結果：
1. 修復 `vercel.json` 配置
2. 在本地運行 `npm run build` 確認構建成功
3. 驗證構建產物結構

### 修改檔案清單

| 文件 | 操作 | 說明 |
|------|------|------|
| `vercel.json` | 修改 | 補充 rewrites、修正輸出配置 |
| `src/frontend/vite.config.ts` | 可能修改 | 修正 base path、output 配置 |
| `.env.production` | 可能新增 | 生產環境變數 |

### 驗收標準

1. ✅ `npm run build` 在 src/frontend 目錄執行成功
2. ✅ 構建產物輸出到 `src/frontend/dist/`
3. ✅ `vercel.json` 配置正確，可在 Vercel 部署
4. ✅ API 請求通過 rewrites 正確代理到後端
5. ✅ 前端頁面（HTML/JS/CSS）正常加載
6. ✅ 無 CORS 或跨域問題

---

## 依賴關係圖

```
REPAIR-1 (Scope Cleanup) ─── 無依賴，可最先執行
     │
     ├──→ REPAIR-2 (Evidence 狀態模型) ─── 需要 REPAIR-1 確保無殘留引用干擾
     │
     ├──→ REPAIR-3 (Authorization Audit) ─── 需要 REPAIR-1 確保環境乾淨
     │
     ├──→ REPAIR-4 (DB Persistence) ─── 需要 REPAIR-1
     │
     ├──→ REPAIR-5 (Migration Verification) ─── 需要 REPAIR-1
     │
REPAIR-6 (Vercel Deployment) ─── 無依賴，可與 REPAIR-1~5 並行
```

**建議執行順序**:
1. **REPAIR-1** → 最先執行（快速清理，為後續任務鋪路）
2. **REPAIR-2** → 需要 REPAIR-1 完成
3. **REPAIR-3 + REPAIR-4 + REPAIR-5** → 可在 REPAIR-1 完成後並行執行
4. **REPAIR-6** → 可與以上全部並行，無依賴

---

## 執行順序建議

| 批次 | 任務 | 負責角色 | 估計工時 | 說明 |
|------|------|---------|---------|------|
| **批次 1** | REPAIR-1 | backend-logic | 1h | 快速清理，最先執行 |
| **批次 2** | REPAIR-2 | db-modeler + backend-logic | 4h | 需 REPAIR-1 |
| **批次 3a** | REPAIR-3 | api-designer + test-writer | 6h | 與 3b/3c 並行 |
| **批次 3b** | REPAIR-4 | db-modeler + test-writer | 6h | 與 3a/3c 並行 |
| **批次 3c** | REPAIR-5 | db-modeler | 3h | 與 3a/3b 並行 |
| **批次 4** | REPAIR-6 | devops | 4h | 可全程並行 |
| **總計** | | | **~24h** | |

### 關鍵路徑
```
REPAIR-1 (1h) → REPAIR-2 (4h) = 5h (關鍵路徑)
REPAIR-3/4/5 並行 = 6h
REPAIR-6 並行 = 4h
總關鍵路徑 = 11h
```

---

## 總結

| 修復項目 | 問題嚴重性 | 影響範圍 | 工時 | 優先級 |
|---------|-----------|---------|------|--------|
| REPAIR-1: Scope Cleanup | 🟢 低 | 代碼庫整潔度 | 1h | P1 |
| REPAIR-2: Evidence 狀態模型 | 🟡 中 | 臨床決策正確性 | 4h | P1 |
| REPAIR-3: Authorization Audit | 🔴 高 | 安全性 | 6h | P0 |
| REPAIR-4: DB Persistence | 🟡 中 | 資料完整性 | 6h | P1 |
| REPAIR-5: Migration 驗證 | 🟡 中 | 資料庫可靠性 | 3h | P1 |
| REPAIR-6: Vercel 部署 | 🔴 高 | 生產部署 | 4h | P0 |

> **P0** = 必須在 next release 前修復  
> **P1** = 建議在 next release 前修復  
> **P2** = 可推遲到後續迭代
