# Architecture Review 返工第 1 次補充計劃

> **基於**：需求回歸檢查 `tasks/reviews/regression_check_architecture.md`  
> **目標報告**：`tasks/reviews/architecture_review.md`  
> **來源審查**：`tasks/reviews/review_layers.md`、`tasks/reviews/review_crosscutting.md`、`tasks/reviews/review_quality.md`  
> **狀態**：3 項 PARTIAL 需補充

---

## 任務 1：Domain Architecture Review 逐檔案審查表

### 缺失原因
原報告 §1（Architecture Score）和 §3（Technical Debt）以全域問題概括了 ORM 耦合、Aggregate 邊界、ValueObject 缺失、樂觀鎖缺失等問題，但未按需求「逐一列出」每個 Domain 檔案的 Entity/Aggregate/ValueObject/State/Version 一致性審查結果。

### 補充方式（3 步）

#### 1a. 建立逐檔案審查表
掃描 `src/backend/domain/` 下 26 個檔案（不含 `__init__.py` 和 `enums.py`），對每個檔案記錄以下維度：

| 維度 | 檢查項目 | 判定標準 |
|------|---------|---------|
| **Entity** | 是否有 `id = Column(CompatUUID, …)` 主鍵 | ✅ / ❌ |
| **Aggregate** | 是否可視爲 Aggregate Root（有獨立生命週期、被 Repository 管理） | ✅ Aggregate Root / ❌ 非 Root |
| **ValueObject** | 是否包含 `@dataclass(frozen=True)` 或 Pydantic `BaseModel` 值物件 | ✅ 有 / ⚠️ 僅 Schema / ❌ 無 |
| **State** | 狀態欄位使用 `SAEnum` 還是 `String(32)` | ✅ SAEnum / ⚠️ 混合 / ❌ 全部 String |
| **Version** | 是否有 `version_id` 樂觀鎖欄位 | ✅ 有 / ❌ 無 |
| **Pureness (ORM)** | 是否繼承 `DBBase`、使用 `Column`/`String` 等 ORM 類型 | ✅ 純淨 / ❌ 混入 ORM |
| **Pureness (API)** | 是否包含 API Schema（`*Request`/`*Response`） | ✅ 純淨 / ❌ 混入 Schema |

**操作指令**：使用 `grep` 和 `read_file` 遍歷 26 個 domain 檔案，按上表逐檔案填寫審查結果，輸出爲 Markdown 表格。

#### 1b. 歸納統計
在逐檔案表格後，新增統計摘要：
- Aggregate Root 數量 / 非 Root 數量
- 使用 SAEnum 的檔案數 vs. 使用 String(32) 的檔案數
- 有 ValueObject 模式的檔案數
- 有 version_id 的檔案數（預期：0）
- 純淨（無 ORM 無 Schema）的檔案數（預期：0）

#### 1c. 更新 §3 Technical Debt
確認逐檔案審查結果與現有 P0-01、P2-01、P2-02、P1-03 的問題描述一致，必要時補充檔案路徑明細。

### 預計修改的報告章節
- **新增**：§1 之下新增「1.x Domain 逐檔案審查表」小節（或新增 §10 附錄 C）
- **修正**：§3 中 P0-01、P2-01、P2-02、P1-03 的「檔案路徑」欄可引用逐檔案表

---

## 任務 2：Dead Code Analysis 補全

### 缺失原因
原報告 §2（Maintainability Score）評語中僅提及「無 TODO/FIXME 殘留」，§5（Duplicate Code）已涵蓋 Copy-Paste，但缺少以下類別的明確列舉：
- Unused imports / functions / variables
- TODO / FIXME / HACK / XXX 註解（即使數量為零也應明確列出）
- Deprecated 標記

### 補充方式（2 步）

#### 2a. 執行全專案掃描
對以下範圍執行搜尋，並記錄結果：

| 類別 | 搜尋方法 | 預期結果 |
|------|---------|---------|
| **TODO / FIXME / HACK / XXX** | `grep -rn "TODO\|FIXME\|HACK\|XXX" src/backend/ KnowGraphGo/`（排除測試檔案） | review_quality.md §11.1 已確認「無」，需再次確認 |
| **Deprecated** | `grep -rn "deprecated\|Deprecated\|@deprecated" src/backend/ KnowGraphGo/` | review_quality.md §11.2 已確認「無」 |
| **Unused imports** | 對 Python：`flake8 --select=F401` 或 `pylint --disable=all --enable=W0611`；對 Go：`go vet` / `staticcheck` | review_quality.md §11.3 指出 adapter.go 的 `"context"` import 可能未使用 |
| **Unused functions/variables** | 對 Python：`vulture` 或 `pylint --disable=all --enable=W0612,W0613`；對 Go：`go vet -unused` | 記錄所有發現 |

**注意**：即使結果為「未發現」，也必須在報告中以表格明確記錄，而非僅在評語中提及。

#### 2b. 在報告中新增獨立 Dead Code 小節
在 §5（Duplicate Code）之後或 §4（Code Smell）之中新增「Dead Code Analysis」小節，格式如下：

```markdown
### Dead Code Analysis

| 類別 | 搜尋範圍 | 結果 | 詳細說明 |
|------|---------|:----:|---------|
| TODO / FIXME / HACK / XXX | 全專案生產代碼 | ✅ 未發現 | … |
| Deprecated 標記 | 全專案生產代碼 | ✅ 未發現 | … |
| Unused imports | Python + Go | ⚠️ 發現 1 處 | … |
| Unused functions/variables | Python + Go | ✅ 未發現 | … |
| Duplicate / Copy-Paste | （由現有 §5 涵蓋） | 詳見 §5 | … |
```

### 預計修改的報告章節
- **新增**：§5（Duplicate Code）之後新增「5.x Dead Code Analysis」小節，或合併入 §4 Code Smell
- **修正**：§2 評語中「無 TODO/FIXME 殘留」改爲引用新增的 Dead Code 表格

---

## 任務 3：Architecture Smell Analysis 補全 Duplicated SQL 和 Duplicated Validation

### 缺失原因
原報告 §4（Code Smell）涵蓋了 God Class、Long Function、跨層依賴反向、Copy-Paste 等 21 項，但缺少需求要求的：
- **Duplicated SQL**：重複的 SQL 查詢字串
- **Duplicated Validation**：重複的驗證邏輯

### 補充方式（2 步）

#### 3a. 執行 Duplicated SQL 檢查
搜尋以下模式：
- **原始 SQL 字串**：`grep -rn '"SELECT\|"INSERT\|"UPDATE\|"DELETE' src/backend/` — 檢查是否有重複的 SQL 字串
- **SQLAlchemy Query 重複**：檢查 Repository 層中相同模式（如 `select().where().order_by()`）是否在多處重複
- **Go 原始 SQL**：`grep -rn 'SELECT\|INSERT\|UPDATE\|DELETE' KnowGraphGo/store/sqlite/`

**預期結果**：review_quality.md §12.5 已指出「未發現明顯的 SQL 重複——儲存庫層使用 SQLAlchemy ORM，無原始 SQL 字串重複」，但需要在架構報告中明確記錄。

#### 3b. 執行 Duplicated Validation 檢查
檢查以下層級的驗證邏輯是否重複：
- **API 層 Pydantic 驗證** vs **Service 層業務驗證** — 檢查是否存在相同的欄位驗證規則在兩層重複定義
- **跨 Service 的相同驗證邏輯**（如 `_validate_upstream_link_consistency` 是否在多處出現）
- **Go Adapter 的 Event 驗證** — 不同 Mapper 中是否有相同的 Payload 驗證

**預期結果**：review_quality.md §12.6 已指出「API 層使用 Pydantic 驗證，Service 層有獨立的業務驗證，責任劃分清晰」，但需在架構報告中明確記錄。

#### 3c. 在 §4 Code Smell 中新增兩行
在現有 §4 Code Smell 表中追加兩行：

| 類別 | 異味描述 | 嚴重程度 | 檔案路徑 | 行號參考 |
|------|---------|---------|---------|---------|
| **Duplicated SQL** | 全專案使用 SQLAlchemy ORM / Go SQLite store，未發現重複原始 SQL 字串 | 🟢 None | 全域 | - |
| **Duplicated Validation** | API 層 Pydantic 驗證與 Service 層業務驗證分工清晰，未發現明顯重複 | 🟢 None | 全域 | - |

### 預計修改的報告章節
- **修正**：§4 Code Smell 表格追加 Duplicated SQL 和 Duplicated Validation 兩行
- **修正**：§附錄 A 中 Architecture Smell 分數保持不變（補充兩項「未發現」不影響分數）

---

## 執行順序

| 順序 | 任務 | 依賴 | 預估工時 |
|------|------|------|---------|
| **1** | 任務 1a：掃描 26 個 domain 檔案，填寫逐檔案審查表 | 無 | 1h |
| **2** | 任務 2a：執行全專案 Dead Code 掃描 | 無 | 0.5h |
| **3** | 任務 3a/3b：執行 Duplicated SQL 和 Duplicated Validation 檢查 | 無 | 0.5h |
| **4** | 任務 1b/1c：歸納統計、更新 §3 | 任務 1 | 0.5h |
| **5** | 任務 2b：在報告中新增 Dead Code 小節 | 任務 2 | 0.5h |
| **6** | 任務 3c：在 §4 新增兩行 | 任務 3 | 0.3h |
| | **合計** | | **~3.3h** |

---

## 驗收標準

補充完成後，回歸檢查 `tasks/reviews/regression_check_architecture.md` 中以下 3 項應從 **PARTIAL** 變爲 **PASS**：

| # | 項目 | PASS 條件 |
|---|------|----------|
| 1 | **Domain Architecture Review** | architecture_review.md 中存在逐檔案審查表，列出全部 26 個 domain 檔案的 Entity/Aggregate/ValueObject/State/Version/Pureness 結果 |
| 2 | **Dead Code Analysis** | architecture_review.md 中存在明確的 Dead Code 小節，以表格列出 TODO/FIXME/HACK/XXX、Deprecated、Unused 的搜尋結果（即使數量為零） |
| 3 | **Architecture Smell Analysis** | architecture_review.md §4 Code Smell 中包含 Duplicated SQL 和 Duplicated Validation 的檢查結果 |

### 自動化驗證
補充完成後，重新執行以下命令確認無新增問題：
```bash
# 確認 domain 逐檔案表覆蓋 26 個檔案
grep -c "| `src/backend/domain/" tasks/reviews/architecture_review.md

# 確認 Dead Code 表格包含 TODO/FIXME/Deprecated/Unused
grep -c "TODO\|FIXME\|Deprecated\|Unused" tasks/reviews/architecture_review.md

# 確認 Code Smell 表格包含 Duplicated SQL 和 Duplicated Validation
grep -c "Duplicated SQL\|Duplicated Validation" tasks/reviews/architecture_review.md
```
