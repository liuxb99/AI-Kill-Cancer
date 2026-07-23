# Plan: Phase 2 修復返工 第 2 次 — 補全遺漏項目

## 背景

Phase 2 六大 REPAIR 修復交付後 REVIEWER 評分為 **58/100 ❌ 不合格**。

### 評分摘要

| 項目 | 得分 | 權重範圍 |
|------|------|---------|
| 完整性 | 8 | 0-10（需求 NO 上限） |
| 正確性 | 6 | 0-10（有錯誤上限） |
| 可維護性 | 20 | 0-25 |
| 測試與驗證 | 24 | 0-25 |
| **總分** | **58 ❌** | 門檻：90 |

### 關鍵問題（必須修復）

| 編號 | 問題 | 影響 |
|------|------|------|
| **FIX-A** | REPAIR-2: `collect_by_variant()` 缺少 `source_statuses`，僅 `collect()` 有 | 完整性 -2, 正確性 -4 |
| **FIX-B** | REPAIR-2: 只記錄了 `AUTHORIZATION_REQUIRED`，未記錄 `AVAILABLE`/`ERROR` | 完整性 -2 |
| **FIX-C** | REPAIR-6: `vercel.json` 缺少 `/api/*` API proxy rewrites | 完整性 -2, 正確性 -3 |
| **FIX-D** | REPAIR-4: `session.py` 未增加 rollback 處理 | 完整性 -1, 正確性 -2 |
| **FIX-E** | REPAIR-2: `SourceStatus` 模型缺少 `items_count` 字段 | 可維護性 -2 |

### 建議修復（非強制但建議）

| 編號 | 問題 | 說明 |
|------|------|------|
| FIX-F | 新增 `SourceStatus`/`SourceStatusType` 的獨立單元測試類 | 測試 -1 |
| FIX-G | `SourceStatus.timestamp` 與 `EvidenceBundle.retrieved_at` 去重 | 可維護性 -2 |
| FIX-H | 提取授權來源 warning 為共用方法 | 可維護性 -1 |

---

## 修正策略

本次返工聚焦 **5 項必須修復**（FIX-A ~ FIX-E），以達到 ≥ 90 分門檻。

---

## 修正任務

### FIX-A: collect_by_variant() 加入 source_statuses

#### 修改 `src/backend/clinical/collector.py`

**A.1 修改 `_collect_for_gene()` 回傳型別**

目前 `_collect_for_gene()` 回傳 `list[EvidenceItem]`。改為回傳 `tuple[list[EvidenceItem], dict[str, SourceStatusType]]` 以攜帶每個來源的觀察狀態。

新增內部回傳型別（或直接在方法內回傳 tuple）：

```python
async def _collect_for_gene(
    self, gene: str, context: ClinicalContext,
) -> tuple[list[EvidenceItem], dict[str, SourceStatusType]]:
    """..."""
```

在方法內部：
- 建立 `source_observed: dict[str, SourceStatusType] = {}`
- 對每個來源（merger → ClinVar → PubMed → ClinicalTrials）：
  - 成功時記錄 `source_observed[source_name] = SourceStatusType.AVAILABLE`
  - 異常時記錄 `source_observed[source_name] = SourceStatusType.ERROR`
- 在 `gene_cache.set()` 之前回傳 `(items, source_observed)`

**A.2 修改 `collect()` 聚合來源狀態**

將 `source_statuses` 的建構從只在末尾加授權來源，改為：
1. 先從每個 `_collect_for_gene()` 的回傳中收集 `source_observed`
2. 對每個觀察到的來源，用 `SourceStatusType` 建立 `SourceStatus`
3. 再加上授權來源的 `AUTHORIZATION_REQUIRED` 狀態
4. 合併去重（同一來源取最高嚴重性：ERROR > UNAVAILABLE > AUTHORIZATION_REQUIRED > AVAILABLE）

**A.3 修改 `collect_by_variant()` 加入來源狀態追蹤**

在方法內部新增 `source_statuses: list[SourceStatus] = []`：
- 對 merger 調用：成功 → AVAILABLE，異常 → ERROR
- 對 ClinVar 調用：成功 → AVAILABLE，異常 → ERROR
- 對 PubMed 調用：成功 → AVAILABLE，異常 → ERROR
- 對 ClinicalTrials 調用：成功 → AVAILABLE，異常 → ERROR
- 對授權來源：`AUTHORIZATION_REQUIRED`
- 在 `EvidenceBundle(items=items, source_statuses=source_statuses, ...)` 中傳入

注意：快取命中時也應回傳合理的 `source_statuses`（無法得知實際狀態時可設為空列表或 AVAILABLE 推斷）。

#### 特定程式碼修改對照

**A.3.1 `_collect_for_gene()` 修改前後**

修改前（第 218-300 行）：
```python
async def _collect_for_gene(
    self, gene: str, context: ClinicalContext,
) -> list[EvidenceItem]:
    ...
    return items  # 第 300 行
```

修改後：
```python
async def _collect_for_gene(
    self, gene: str, context: ClinicalContext,
) -> tuple[list[EvidenceItem], dict[str, SourceStatusType]]:
    ...
    # 追蹤每個來源的狀態
    source_observed: dict[str, SourceStatusType] = {}
    
    # ── 1. CIViC / DGIdb via EvidenceMerger ──────────
    try:
        merger_result = await self._merger.merge_gene_evidence(...)
        ...
        source_observed["civic"] = SourceStatusType.AVAILABLE
    except Exception:
        ...
        source_observed["civic"] = SourceStatusType.ERROR
    
    # ── 2. ClinVar ────────────────────────────────────
    try:
        ...
        source_observed["clinvar"] = SourceStatusType.AVAILABLE
    except Exception:
        ...
        source_observed["clinvar"] = SourceStatusType.ERROR
    
    # ── 3. PubMed ─────────────────────────────────────
    try:
        ...
        source_observed["pubmed"] = SourceStatusType.AVAILABLE
    except Exception:
        ...
        source_observed["pubmed"] = SourceStatusType.ERROR
    
    # ── 4. ClinicalTrials.gov ─────────────────────────
    try:
        ...
        source_observed["clinicaltrials"] = SourceStatusType.AVAILABLE
    except Exception:
        ...
        source_observed["clinicaltrials"] = SourceStatusType.ERROR
    
    ...
    return items, source_observed  # 改為回傳 tuple
```

**A.3.2 `collect()` 修改前後**

修改前（第 69-122 行）：
```python
async def collect(self, context: ClinicalContext) -> EvidenceBundle:
    all_items: list[EvidenceItem] = []
    seen_genes: set[str] = set()
    for variant in context.variants:
        gene = ...
        ...
        gene_items = await self._collect_for_gene(gene, context)
        all_items.extend(gene_items)
    
    # 只有授權來源的狀態
    source_statuses: list[SourceStatus] = []
    now_ts = datetime.now(timezone.utc).isoformat()
    for src in _AUTH_SOURCES:
        ...
        source_statuses.append(SourceStatus(...))
    
    bundle = EvidenceBundle(items=all_items, source_statuses=source_statuses, ...)
    return bundle
```

修改後：
```python
async def collect(self, context: ClinicalContext) -> EvidenceBundle:
    all_items: list[EvidenceItem] = []
    seen_genes: set[str] = set()
    source_observed_all: dict[str, SourceStatusType] = {}
    
    for variant in context.variants:
        gene = ...
        ...
        gene_items, source_observed = await self._collect_for_gene(gene, context)
        all_items.extend(gene_items)
        # 合併來源狀態（取最高嚴重性）
        for src, st in source_observed.items():
            if src not in source_observed_all or _status_priority(st) > _status_priority(source_observed_all[src]):
                source_observed_all[src] = st
    
    # 建構完整 source_statuses
    source_statuses: list[SourceStatus] = []
    now_ts = datetime.now(timezone.utc).isoformat()
    for src, st in source_observed_all.items():
        source_statuses.append(SourceStatus(
            source_name=src,
            status_type=st,
            timestamp=now_ts,
        ))
    # 授權來源
    for src in _AUTH_SOURCES:
        if src not in source_observed_all:
            source_statuses.append(SourceStatus(
                source_name=src,
                status_type=SourceStatusType.AUTHORIZATION_REQUIRED,
                message="requires API key / licence",
                timestamp=now_ts,
            ))
    
    bundle = EvidenceBundle(items=all_items, source_statuses=source_statuses, ...)
    return bundle
```

其中 `_status_priority()` 是一個靜態輔助方法：
```python
@staticmethod
def _status_priority(st: SourceStatusType) -> int:
    """Higher = more severe."""
    ordering = {
        SourceStatusType.ERROR: 4,
        SourceStatusType.UNAVAILABLE: 3,
        SourceStatusType.AUTHORIZATION_REQUIRED: 2,
        SourceStatusType.AVAILABLE: 1,
    }
    return ordering.get(st, 0)
```

**A.3.3 `collect_by_variant()` 修改重點**

目前第 124-214 行。修改要點：

1. 快取命中時（第 141-146 行）：改為 `EvidenceBundle(items=..., source_statuses=[], retrieved_at=...)`（空列表表示無法獲取狀態）
2. 每個 try/except 區塊加入 `source_statuses.append(...)`
3. 授權來源的 `logger.warning` 改為 `source_statuses.append(SourceStatus(...))`
4. 最終回傳的 `EvidenceBundle` 包含 `source_statuses`

---

### FIX-B: 補全 AVAILABLE/ERROR 狀態記錄

此項已包含在 FIX-A 的設計中：`_collect_for_gene()` 對每個來源記錄 `AVAILABLE`（成功）或 `ERROR`（異常），`collect_by_variant()` 同理。

確保以下來源都被覆蓋：
- `civic`（透過 merger 調用）
- `clinvar`
- `pubmed`
- `clinicaltrials`
- `nccn` / `esmo` / `oncokb`（AUTHORIZATION_REQUIRED）

---

### FIX-C: vercel.json 增加 API proxy rewrites

#### 修改 `vercel.json`

目前內容：
```json
{
  "rootDirectory": "src/frontend",
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "installCommand": "npm ci",
  "nodeVersion": "18",
  "rewrites": [
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ]
}
```

修改後：
```json
{
  "rootDirectory": "src/frontend",
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "installCommand": "npm ci",
  "nodeVersion": "18",
  "rewrites": [
    {
      "source": "/api/(.*)",
      "destination": "/api/$1"
    },
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ]
}
```

> **注意**：`/api/(.*)` → `/api/$1` 的 rewrite 會讓 Vercel 將匹配的請求傳遞給 Serverless Functions 或後端服務。如果後端是獨立部署的服務，應改為：
> ```json
> {
>   "source": "/api/(.*)",
>   "destination": "https://your-backend.vercel.app/api/$1"
> }
> ```
> 具體 destination URL 需根據實際部署環境填寫。

---

### FIX-D: session.py 增加 rollback 處理

#### 修改 `src/backend/database/session.py`

目前內容（第 7-14 行）：
```python
async def get_db():
    if async_session_factory is None:
        raise RuntimeError("Database not initialized")
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
```

修改後：
```python
async def get_db():
    if async_session_factory is None:
        raise RuntimeError("Database not initialized")
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

新增 `except` 區塊在異常發生時先 rollback 再重新拋出，確保事務不會處於不一致狀態後才關閉 session。

---

### FIX-E: SourceStatus 模型補充 items_count 字段

#### 修改 `src/backend/clinical/evidence_models.py`

目前內容（第 65-83 行）：
```python
class SourceStatus(BaseModel):
    source_name: str
    status_type: SourceStatusType
    message: Optional[str] = None
    timestamp: str = ""
```

修改後：
```python
class SourceStatus(BaseModel):
    source_name: str
    status_type: SourceStatusType
    message: Optional[str] = None
    items_count: int = 0
    timestamp: str = ""
```

並在建構 `SourceStatus` 時傳入 `items_count`（來源返回的 evidence item 數量）。

---

### FIX-F: 新增 SourceStatus 獨立單元測試（建議）

#### 在 `tests/unit/test_evidence_collector.py` 中新增

```python
class TestSourceStatus:
    """Tests for SourceStatus and SourceStatusType models."""

    def test_source_status_type_values(self):
        """SourceStatusType should have expected enum values."""
        assert SourceStatusType.AVAILABLE.value == "available"
        assert SourceStatusType.UNAVAILABLE.value == "unavailable"
        assert SourceStatusType.AUTHORIZATION_REQUIRED.value == "authorization_required"
        assert SourceStatusType.ERROR.value == "error"

    def test_source_status_create_minimal(self):
        """Create SourceStatus with only required fields."""
        status = SourceStatus(
            source_name="clinvar",
            status_type=SourceStatusType.AVAILABLE,
        )
        assert status.source_name == "clinvar"
        assert status.status_type == SourceStatusType.AVAILABLE
        assert status.message is None
        assert status.items_count == 0
        assert status.timestamp == ""

    def test_source_status_create_full(self):
        """Create SourceStatus with all fields."""
        status = SourceStatus(
            source_name="nccn",
            status_type=SourceStatusType.AUTHORIZATION_REQUIRED,
            message="requires licence",
            items_count=0,
            timestamp="2026-01-01T00:00:00",
        )
        assert status.items_count == 0
        assert status.message == "requires licence"

    def test_source_status_with_items(self):
        """SourceStatus should record items_count when data was returned."""
        status = SourceStatus(
            source_name="pubmed",
            status_type=SourceStatusType.AVAILABLE,
            items_count=5,
        )
        assert status.items_count == 5
```

---

### FIX-G: 去重 timestamp（建議）

`SourceStatus` 的 `timestamp` 字段與 `EvidenceBundle.retrieved_at` 語義重疊。建議：
- 保留 `SourceStatus.timestamp`（可為空字串），建構時不強制傳入
- 消費者應優先使用 `EvidenceBundle.retrieved_at` 作為整體時間戳

此項為可維護性優化，不影響功能正確性。可暫緩處理。

---

### FIX-H: 提取共用方法（建議）

將 `_AUTH_SOURCES` 的 `logger.warning` + `SourceStatus` 建構提取為共用方法：

```python
def _report_auth_sources(self) -> list[SourceStatus]:
    """Return SourceStatus entries for authorisation-required sources."""
    statuses = []
    now_ts = datetime.now(timezone.utc).isoformat()
    for src in _AUTH_SOURCES:
        logger.warning("Knowledge source '%s' requires authorisation...", src)
        statuses.append(SourceStatus(
            source_name=src,
            status_type=SourceStatusType.AUTHORIZATION_REQUIRED,
            message="requires API key / licence",
            timestamp=now_ts,
        ))
    return statuses
```

在 `collect()` 和 `collect_by_variant()` 中調用此方法取代重複代碼。

此項為可維護性優化，建議包含在本次返工中以提高分數。

---

## 修改檔案清單

| 文件 | 操作 | 說明 |
|------|------|------|
| `src/backend/clinical/collector.py` | **修改** | FIX-A + FIX-B: `_collect_for_gene` 改回傳 `tuple`; `collect()` 合併來源狀態; `collect_by_variant()` 加入 `source_statuses`; 提取 `_report_auth_sources()` 共用方法 |
| `src/backend/clinical/evidence_models.py` | **修改** | FIX-E: `SourceStatus` 新增 `items_count` 字段 |
| `vercel.json` | **修改** | FIX-C: 增加 `/api/(.*)` rewrite 規則 |
| `src/backend/database/session.py` | **修改** | FIX-D: `get_db()` 增加 `except` rollback 處理 |
| `tests/unit/test_evidence_collector.py` | **修改** | 更新 collector 測試以適配 `_collect_for_gene` 回傳型別變化; 新增 `TestSourceStatus` 類 |

---

## 驗收標準

1. ✅ `collect_by_variant()` 回傳的 `EvidenceBundle` 包含 `source_statuses`
2. ✅ `collect()` 和 `collect_by_variant()` 的 `source_statuses` 包含所有來源的 AVAILABLE/ERROR/AUTHORIZATION_REQUIRED 狀態
3. ✅ `SourceStatus` 包含 `items_count` 字段
4. ✅ `vercel.json` 有 `/api/(.*)` rewrite 規則
5. ✅ `get_db()` 在異常時調用 `session.rollback()`
6. ✅ 所有現有測試通過
7. ✅ 新增的 `TestSourceStatus` 測試通過
8. ✅ `pytest tests/unit/test_evidence_collector.py -v` 全部通過

---

## 預期分數提升

| 項目 | 修復前 | 修復後預期 | 說明 |
|------|--------|------------|------|
| 完整性 | 8/10 | 10/10 | 補齊所有遺漏需求 |
| 正確性 | 6/10 | 9-10/10 | 修正實作偏差 |
| 可維護性 | 20/25 | 22-24/25 | 提取共用方法、補充 items_count |
| 測試與驗證 | 24/25 | 25/25 | 新增 SourceStatus 測試 |
| **總分** | **58** | **91-94 ✅** | 達到合格門檻 ≥90 |
