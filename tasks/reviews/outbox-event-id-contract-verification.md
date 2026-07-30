# Phase 3F-0 Outbox event_id Contract 完整核查报告

> **產出日期**: 2026-07-30  
> **範圍**: ClinicalGraphOutboxModel.event_id 欄位的完整 Contract 鏈 — 從 Service 生產到 Repository 儲存、Model 定義、Migration 聲明、消費者依賴  
> **審查基準**: 原始 Phase 3F-0 Transaction Boundary Hardening 提交（返工前狀態）vs 返工第 2 次修正後狀態

---

## 1. 完整呼叫鏈

```
TreatmentPlanService.create_plan()
  └─ _create_outbox_event()                           # [L981-1032]
       └─ self._outbox_repo.create(**kwargs)           # [L1023-1032]
            └─ ClinicalGraphOutboxRepository.create()
                 ├─ 只自動產生 "id"（若未傳入）
                 └─ 不對 "event_id" 做任何自動補償
                      └─ ClinicalGraphOutboxModel(**kwargs)
                           ├─ event_id = Column(String(64), unique=True, nullable=False, index=True)
                           └─ 無 default（Model 層）
                                └─ Migration 021 / 022
                                     └─ event_id 無 server_default（DB 層）
```

### 返工前（原始 Phase 3F-0 提交）

```
_create_outbox_event() 在 L1024 未傳入 event_id
  → Repository.create() 不自動填入 event_id
    → Model() 無 default → event_id = None
      → NOT NULL 約束違反 → INSERT 拋出 IntegrityError
        → Service 層 catch Exception → rollback → 資料丟失 + 使用者收到 500
```

### 返工第 2 次修正後

```
_create_outbox_event() 在 L1024 傳入 event_id=str(_uuid.uuid4())
  → Repository.create() 正常接收 event_id
    → Model 層取得有效 UUID 字串
      → DB INSERT 成功
```

---

## 2. 關鍵問題答案

| # | 問題 | 答案 | 證據位置 |
|---|------|------|---------|
| 1 | **`_create_outbox_event()` 是否傳入 `event_id`** | **返工前：❌ 否**；返工後：✅ 是 | `treatment_plan_service.py` L1024 原始缺少 `event_id=` 參數 → 修正後加入 `event_id=str(_uuid.uuid4())` |
| 2 | **Repository 是否自動產生 `event_id`** | ❌ 否 | `ClinicalGraphOutboxRepository.create()`（`clinical_graph_outbox_repo.py` L26-33）僅對 `"id"` 做 `kwargs.setdefault`，`event_id` 無任何自動補償邏輯 |
| 3 | **Model 是否有 Python-level `default`** | ❌ 否 | `ClinicalGraphOutboxModel`（`clinical_graph_outbox.py` L15）`event_id = Column(String(64), unique=True, nullable=False, index=True)` — 無 `default=` 參數 |
| 4 | **Migration 是否有 `server_default`** | ❌ 否 | Migration 021（`021_phase3d_clinical_graph_outbox.py` L29）`sa.Column("event_id", sa.String(64), unique=True, nullable=False, index=True)` — 無 `server_default=`；對比：`status`、`attempt_count`、`available_at` 等均有 `server_default` |
| 5 | **`event_id` 是否為 `NOT NULL`** | ✅ 是 | Model 層 `nullable=False` + Migration 層 `nullable=False` |
| 6 | **測試 wrapper 是否遮蔽問題** | **返工前：✅ 是**（FixedOutboxRepository）；返工後：❌ 已移除 | `FixedOutboxRepository` 在返工前測試中自動填入 `event_id`，遮蔽了 Service 層未傳入的缺陷；返工第 2 次已移除該 wrapper |
| 7 | **其他 Service 是否正確傳入 `event_id`** | ✅ 是（對照組正常） | `ClinicalGraphEventService.create_event()`（`clinical_graph_event_service.py` L40）正確傳入 `event_id=str(uuid.uuid4())` |
| 8 | **KnowGraphGo 是否依賴 `event_id`** | ✅ 是，強依賴 | `KnowGraphGo/adapter/clinical/adapter.go` L49 定義 `EventID string \`json:"event_id"\``，L120/142/164 將 `event_id` 寫入 Graph Metadata；若 `event_id` 為 `NULL` 則 Graph 節點/邊缺少唯一標識符 |

---

## 3. 問題根因分析

### 3.1 缺陷鏈

```
Service 層遺漏參數
    ↓
Repository 層無防禦性補償
    ↓
Model 層無 default
    ↓
DB 層無 server_default
    ↓
NOT NULL 約束 → IntegrityError → Rollback → 500
```

這是一條**四層防護全失效**的 Contract 斷裂鏈。任意一層有防護都能避免 Production 故障。

### 3.2 為何其他 Service 沒有此問題

| Service | 傳入 event_id | 原始碼位置 |
|---------|--------------|-----------|
| `ClinicalGraphEventService.create_event()` | ✅ `event_id=str(uuid.uuid4())` | `clinical_graph_event_service.py` L40 |
| `TreatmentPlanService._create_outbox_event()`（返工前） | ❌ 遺漏 | `treatment_plan_service.py` L1024（原始） |
| `TreatmentPlanService._create_outbox_event()`（返工後） | ✅ `event_id=str(_uuid.uuid4())` | `treatment_plan_service.py` L1024（修正後） |

`ClinicalGraphEventService` 由 Phase 3D 開發，當時對 Outbox Contract 理解正確。`TreatmentPlanService._create_outbox_event()` 由 Phase 3E 開發，遺漏了 `event_id` 參數。

### 3.3 測試遮蔽（Test Masking）

返工前的測試使用 `FixedOutboxRepository`（一個測試專用子類），該子類在 `create()` 方法中自動填入 `event_id`：

```python
class FixedOutboxRepository(ClinicalGraphOutboxRepository):
    async def create(self, **kwargs) -> ClinicalGraphOutboxModel:
        if "event_id" not in kwargs:
            kwargs["event_id"] = str(uuid.uuid4())  # 自動補償！
        return await super().create(**kwargs)
```

這導致：
- **單元測試全部通過**（遮蔽了 Service 層遺漏）
- **整合測試也通過**（使用同一 wrapper）
- **Production 直接崩潰**（無 wrapper 保護）

### 3.4 KnowGraphGo 消費者影響

KnowGraphGo 的 `adapter.go` 將 `event_id` 作為 Graph Edge Metadata 的核心欄位寫入：

```go
// adapter.go L49
EventID string `json:"event_id"`

// L120 - Patient Node
"event_id": event.EventID,

// L142 - Recommendation Node  
"event_id": event.EventID,

// L164 - Relation Edge
"event_id": event.EventID,
```

若 `event_id` 為 `NULL`，Graph 中將出現缺少唯一識別符的節點/邊，導致：
- Neo4j 中無法正確去重（dedup）
- 下游查詢無法關聯回原始 Outbox 事件
- Debug 和稽核軌跡中斷

---

## 4. 嚴重度評估

| 維度 | 評級 | 說明 |
|------|------|------|
| **影響範圍** | **全域** | 所有 `TreatmentPlanService.create_plan()` 呼叫全部失敗 |
| **觸發條件** | **100%** | 每次建立 Treatment Plan 均觸發 |
| **可觀測性** | **中等** | 500 Internal Server Error 可觀測，但 root cause `event_id` 缺失不易從錯誤訊息直接定位 |
| **資料損失** | **是（事務性）** | Service 層 `except Exception` → `rollback()` → 整筆 Treatment Plan 及其關聯資料全部丟失 |
| **用戶體驗** | **嚴重** | 使用者無法建立 Treatment Plan，操作完全中斷 |

### CVE 風格評分

```
CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:N/I:N/A:H (7.5 High)
- Availability: High（每次操作均導致 500，完全不可用）
- Scope: Changed（資料庫 IntegrityError 傳播至應用層導致 Service rollback）
```

### 原始判定

**P0 — Production Runtime Failure** ⛔

---

## 5. 檢測時機分析

| 檢測層級 | 是否可捕獲此缺陷 | 實際捕獲情況 |
|---------|----------------|------------|
| **IDE / Language Server** | ❌ | Python 動態語言，無編譯期檢查 |
| **型別檢查器（mypy/pyright）** | ❌ | `**kwargs` 動態參數繞過型別檢查 |
| **Linter（ruff/flake8）** | ❌ | 非語法/風格問題 |
| **單元測試** | ❌ | `FixedOutboxRepository` 遮蔽問題 |
| **整合測試** | ❌ | 同上，使用相同 wrapper |
| **手動程式碼審查** | ✅ | 原始 Phase 3F-0 Reviewer Gate 未發現（第 0 次 review 未報告此問題） |
| **返工審查（Phase 3F-0 R2）** | ✅ | Outbox Contract Gate 明確指出此缺陷並要求修正 |

### 教訓

4 層防護全失效 + 測試遮蔽 = 1 個 Production P0。任一層有防護即可避免。

---

## 6. 返工修正驗證

### 6.1 修正內容

**檔案**: `src/backend/services/treatment_plan_service.py` L1024

```python
# 返工前（L1024，原始）
await self._outbox_repo.create(
    # 缺少 event_id！
    aggregate_type=...,
    ...
)

# 返工後（L1024，修正）
await self._outbox_repo.create(
    event_id=str(_uuid.uuid4()),  # ✅ 已補上
    aggregate_type=...,
    ...
)
```

### 6.2 修正驗證清單

| 檢查項 | 結果 | 確認方式 |
|--------|------|---------|
| `event_id` 格式與既有 `ClinicalGraphEventService` 一致 | ✅ `str(uuid.uuid4())` vs `str(_uuid.uuid4())` 等價 | 代碼比對 |
| 4 個呼叫位置全部覆蓋 | ✅ 全部經由 `_create_outbox_event()` 單一方法 | L356、L572、L769、L776 |
| `FixedOutboxRepository` 已移除 | ✅ grep 無結果 | 全域搜尋 |
| Migration 層無需變更 | ✅ Model 定義不變，僅需傳入正確值 | Migration 021/022 |
| KnowGraphGo 相容 | ✅ `event_id` 為有效 UUID 字串，格式正確 | adapter.go 結構定義 |
| 273/273 測試通過 | ✅ | Phase 3F-0 R2 測試執行結果 |

### 6.3 Contract 強固建議（後續 Phase）

| 建議 | 優先級 | 說明 |
|------|--------|------|
| **Repository 層防禦性補償** | P1 | `ClinicalGraphOutboxRepository.create()` 增加 `if "event_id" not in kwargs: kwargs["event_id"] = str(uuid.uuid4())` 作為安全網 |
| **Model 層 default** | P2 | `event_id = Column(String(64), ..., default=lambda: str(uuid.uuid4()))` — ORM-level fallback |
| **測試不使用 wrapper 遮蔽 Contract** | P0（已強制） | 已移除 `FixedOutboxRepository`；新增規則：測試 Repository 不得自動補償 Business-logic 欄位 |
| **Cross-Service 參數對齊審查** | P2 | 確保所有呼叫 `ClinicalGraphOutboxRepository.create()` 的位置傳入完整參數集 |

---

## 7. 最終判定

| 階段 | Outbox Contract Gate | 說明 |
|------|---------------------|------|
| **Phase 3F-0 原始提交** | **FAIL** 🔴 | `_create_outbox_event()` 未傳入 `event_id`，導致 100% Production Runtime Failure |
| **Phase 3F-0 返工第 1 次** | **FAIL** 🔴 | 程式碼未變更，問題依然存在 |
| **Phase 3F-0 返工第 2 次** | **PASS** ✅ | L1024 已補上 `event_id=str(_uuid.uuid4())`，273/273 測試通過，KnowGraphGo 相容 |

> **總結論**: Outbox `event_id` Contract 在原始 Phase 3F-0 提交中斷裂（四層防護全失效 + 測試遮蔽），導致 P0 Production Runtime Failure。返工第 2 次修正已從根因補救：Service 層正確傳入 `event_id`，並移除測試遮蔽 wrapper。**Contract Gate 由 FAIL 轉為 PASS**。

---

*報告結束 — 基於 `src/backend/services/treatment_plan_service.py`、`src/backend/repositories/clinical_graph_outbox_repo.py`、`src/backend/domain/clinical_graph_outbox.py`、`migrations/versions/021_phase3d_clinical_graph_outbox.py`、`KnowGraphGo/adapter/clinical/adapter.go` 的完整來源分析。*
