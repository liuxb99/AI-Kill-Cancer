# Phase 3F-0 獨立最終審查報告

> **Phase**: 3F-0 Transaction Boundary Hardening  
> **審查類型**: 最終審查（返工第 1 次評分後，因 Outbox Contract Gate FAIL 退回）  
> **評分日期**: 2026-07-30  
> **評分版本**: branch `fix/transaction-boundary-hardening`（返工第 1 次程式碼）

---

## 評分

| 項目 | 評分 | 說明 |
|------|------|------|
| 完整性 | **23 / 25** | R1~R11 基本滿足，但 FixedOutboxRepository 遮蔽 Outbox Contract 問題導致 R7 未真正通過（-1）；R9 PostgreSQL CI 未實際執行驗證（-1）。 |
| 正確性 | **24 / 25** | Repository 層 commit→flush 轉換正確；Service 層 try/commit/rollback 模式一致；API 層 commit/rollback 已移除。但 `_create_outbox_event()` 不傳入 `event_id` 依賴測試層補救，屬 Production Bug（-1）。 |
| 可維護性 | **24 / 25** | 架構設計清晰，Service 層統一事務邊界。FixedOutboxRepository 為測試專用 wrapper 增加維護成本，且遮蔽真實問題（-1）。 |
| 測試與驗證 | **22 / 25** | 原子性測試套件完整（22 個測試 + 320+ 回歸測試）。但 FixedOutboxRepository 使測試不反映真實 Production 行為（-2）；PostgreSQL CI 未實際執行驗證（-1）。 |
| **總分** | **93 / 100** | — |

---

## Gate 結果

| Gate | 結果 |
|------|------|
| Architecture Gate | PASS ✅ |
| Transaction Boundary Gate | PASS ✅ |
| PostgreSQL Atomicity Gate | PASS ✅ |
| Migration Scope Deviation | ACCEPT 🔶 |
| CI Safety Gate | PASS ✅ |

> **Outbox Contract Gate** → **FAIL** ❌（詳細分析見 §4）

---

## §4 Outbox Contract Gate 失敗分析

### §4.1 問題概述

`TestTreatmentPlanServiceSuccessPath` 測試使用 `FixedOutboxRepository` wrapper，該 wrapper 在 `event_id` 未提供時自動補上一個隨機 UUID。此 wrapper 的存在**遮蔽了 Production 層的重大缺陷**。

### §4.2 FixedOutboxRepository 詳細分析

#### Production 層缺陷

**`TreatmentPlanService._create_outbox_event()`**（位於 `src/backend/services/treatment_plan_service.py` L981~L1032）在建立 Outbox 事件時，**不傳入 `event_id`**：

```python
async def _create_outbox_event(self, event_type, plan_model, engine_output, request, actor_id=None):
    # ... 建構 payload ...
    await self._outbox_repo.create(
        # ⚠️ 未傳入 event_id！
        aggregate_type=GraphAggregateType.TREATMENT_PLAN.value,
        aggregate_id=plan_model.plan_id,
        event_type=event_type.value,
        schema_version=1,
        payload=payload,
        actor_id=actor_id,
        occurred_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
```

#### Model 定義

**`ClinicalGraphOutboxModel.event_id`**（位於 `src/backend/domain/clinical_graph_outbox.py`）定義為：

```python
event_id = Column(String(64), unique=True, nullable=False, index=True)
```

- `NOT NULL` — 資料庫層不允許空值
- `unique=True` — 必須唯一
- 無資料庫層預設值 — 必須由應用層提供

#### 測試層的遮蔽

**`FixedOutboxRepository`** 在測試中自動補上 `event_id`：

```python
class FixedOutboxRepository:
    async def create(self, **kwargs):
        if "event_id" not in kwargs:
            kwargs["event_id"] = f"event-{uuid.uuid4().hex}"
        return await self._inner.create(**kwargs)
```

此 wrapper 使得測試全部通過，但 Production service 實際上並未履行 Outbox contract 中「必須提供合法 `event_id`」的要求。

#### 影響鏈

```
Production _create_outbox_event() 不傳入 event_id
  → ClinicalGraphOutboxModel.event_id = NOT NULL (無預設值)
    → 若無 FixedOutboxRepository，測試應 FAIL
      → FixedOutboxRepository 在測試層補上 event_id → 測試 PASS
        → Production Bug 被遮蔽 ❌
```

#### 根因

1. **直接原因**: `_create_outbox_event()` 未傳入 `event_id` 參數。
2. **間接原因**: `ClinicalGraphOutboxRepository.create()` 及其 Model 對 `event_id` 的處理不明確 — Repository 層是否應自動產生 `event_id` 無統一規範。
3. **測試掩蓋**: `FixedOutboxRepository` 的存在使此問題在測試中不可見。

### §4.3 修復方向

| 面向 | 建議方案 | 優先級 |
|------|---------|--------|
| **Production 修正** | 在 `_create_outbox_event()` 中傳入 `event_id=str(_uuid.uuid4())` | P0 |
| **測試清理** | 移除 `FixedOutboxRepository` wrapper，測試使用真實 `ClinicalGraphOutboxRepository` | P0 |
| **規範明確** | 決定 `event_id` 的產生責任歸屬：Service 層產生 vs Repository 層自動產生 | P1 |

### §4.4 Gate 判定

| 項目 | 結果 |
|------|------|
| Outbox Contract Gate | **FAIL** ❌ |
| 原因 | Production `TreatmentPlanService._create_outbox_event()` 不傳入 `event_id`，`FixedOutboxRepository` 在測試層遮蔽此缺陷 |
| 影響 | Accepted = **NO** 🔴 |

---

## 逐項需求評分（R1~R13）

### R1：先建立失敗重現測試

| 狀態 | 評分說明 |
|------|---------|
| ✅ **PASS** | T-02~T-05 紅燈測試已建立：BaseRepository 原子性測試、Flow A、Flow B、Success Path 均在修正前確認紅燈（FAIL）。紅燈記錄存於各測試檔案。 |

### R2：完整盤點 BaseRepository 使用範圍

| 狀態 | 評分說明 |
|------|---------|
| ✅ **PASS** | `tasks/phase3f0-inventory.md` 完整盤點 27 個 Repository 子類，含 16 處 commit 變更明細及所有繼承 BaseRepository 的類別。清單無遺漏。 |

### R3：Transaction Contract

| 狀態 | 評分說明 |
|------|---------|
| ✅ **PASS** | Repository 層所有 commit→flush 轉換完成；Service 層使用一致 try/commit/rollback 模式；API 層所有 commit/rollback 已移除。唯 `get_db()` 安全網的全局 commit 可能與 Service 層重複，但不違反 Contract。 |

### R4：修正 BaseRepository

| 狀態 | 評分說明 |
|------|---------|
| ✅ **PASS** | `base.py` 三方法已修正：`create` → flush + refresh；`update` → flush + refresh；`delete` → delete + flush。無殘留 commit。 |

### R5：檢查所有 Repository

| 狀態 | 評分說明 |
|------|---------|
| ✅ **PASS** | 6 個受影響 Repository（case_acl、evidence_item、drug_interaction、knowledge_source、variant）的自行 commit 已全部改為 flush。grep 確認 Repository 層無 `await .commit()` 或 `await .rollback()` 實際調用。 |

### R6：修正受影響 Service

| 狀態 | 評分說明 |
|------|---------|
| ✅ **PASS** | 8 個 Service（RecommendationService、ClinicalDecisionService、TumorBoardConsensusService、TreatmentPlanService、WorkbenchService、ClinicalGraphEventService、EvidenceIngestionService、VariantIngestionService）均使用 `try / commit / except rollback / raise` 一致模式。 |

### R7：Outbox 原子性

| 狀態 | 評分說明 |
|------|---------|
| ⚠️ **PARTIAL** | ⚠️ Outbox 與業務資料同交易的功能正確（測試驗證業務+Outbox 同 commit/rollback）。**但 FixedOutboxRepository 問題導致 Outbox Contract Gate FAIL**：`_create_outbox_event()` 不傳入 `event_id`，依賴測試層補救，未真正履行 Outbox contract。 |
| 扣分 | -1（完整性） |

### R8：Flush 後可繼續使用

| 狀態 | 評分說明 |
|------|---------|
| ✅ **PASS** | `test_flush_chain.py` 驗證 Plan flush → Phase 使用 plan.id → Item 使用 phase.id → Outbox 使用 plan_id → Service commit。PK 鏈完整可用。 |

### R9：測試要求

| 狀態 | 評分說明 |
|------|---------|
| ✅ **PASS**（基本） | BaseRepository Tests、Atomicity Tests Flow A/Flow B、Success Tests、Restart Recovery 測試全部存在。但 FixedOutboxRepository 使 Success Path 測試不反映真實 Production 行為（-2 測試驗證）。PostgreSQL CI 配置已更新但未實際執行（-1 測試驗證）。 |

### R10：回歸要求

| 狀態 | 評分說明 |
|------|---------|
| ✅ **PASS** | 320+ 回歸測試（Phase 3A~3E + Migration Gate + Frontend Build）全部通過。ruff 無新錯誤。 |

### R11：Commit Scope Gate

| 狀態 | 評分說明 |
|------|---------|
| ✅ **PASS** | Production files = 14 tracked + 2 new = **16**，低於 20 上限。無 formatter/CRLF/import sorting 重寫大量無關檔案。 |

### R12：Reviewer Gate

| 狀態 | 評分說明 |
|------|---------|
| ❌ **FAIL** | Reviewer Gate 雖 11 項檢查全 PASS，但 **Outbox Contract Gate FAIL** 導致 Accepted = NO，最終總分 93（未達 95 門檻）。 |

### R13：Git

| 狀態 | 評分說明 |
|------|---------|
| ✅ **PASS**（評分時） | Commit message 已規劃 `fix(architecture): centralize transaction boundaries in services`，允許一個 CI 修復 Commit，禁止 force push。評分時尚未執行 commit（屬評分後步驟）。 |

### 需求評分總結

| 需求 | 狀態 | 備註 |
|------|------|------|
| R1 紅燈測試 | ✅ PASS | |
| R2 盤點 | ✅ PASS | |
| R3 Transaction Contract | ✅ PASS | |
| R4 BaseRepository 修正 | ✅ PASS | |
| R5 Repository 檢查 | ✅ PASS | |
| R6 Service 修正 | ✅ PASS | |
| R7 Outbox 原子性 | ⚠️ PARTIAL | FixedOutboxRepository 遮蔽 → Outbox Contract Gate FAIL |
| R8 Flush 後 PK | ✅ PASS | |
| R9 測試 | ⚠️ PARTIAL | FixedOutboxRepository 遮蔽真實問題 |
| R10 回歸 | ✅ PASS | |
| R11 Commit Scope | ✅ PASS | |
| R12 Reviewer Gate | ❌ FAIL | Outbox Contract Gate FAIL → Accepted = NO |
| R13 Git | ✅ PASS | |

---

## 最終判定

| 項目 | 結果 |
|------|------|
| **總分** | **93 / 100** |
| **Outbox Contract Gate** | **FAIL** ❌ |
| **Accepted** | **NO** 🔴 |

### 不合格原因

1. **🔴 Outbox Contract Gate FAIL**: `TreatmentPlanService._create_outbox_event()` 不傳入 `event_id`，`FixedOutboxRepository` 在測試層遮蔽此 Production Bug。Outbox 模式的正確性受損。
2. **🔴 總分 93 < 95**: Phase 3F-0 要求 ≥ 95 才能 Accepted，93 分未達門檻。

### 必須返工項目

| 優先級 | 項目 | 說明 |
|--------|------|------|
| **P0** | **修正 `_create_outbox_event()` 傳入 `event_id`** | 在 `treatment_plan_service.py` 的 `_create_outbox_event()` 中傳入 `event_id=str(_uuid.uuid4())` |
| **P0** | **移除 `FixedOutboxRepository`** | 測試改用真實 `ClinicalGraphOutboxRepository`，使測試反映真實 Production 行為 |
| **P0** | **重新驗證 Outbox Contract Gate** | 確認 `event_id` 正確傳入、所有呼叫路徑覆蓋、測試無遮蔽 |
| **P1** | **執行 PostgreSQL CI 驗證** | 在 Postgres 上執行 Transaction Atomicity 測試套件 |
| **P1** | **重新提交 REVIEWER 評分** | 目標 ≥ 95，Accepted = YES |

---

## 附錄 A：審查範圍說明

本報告為 **最終審查報告**，記錄 Phase 3F-0 返工第 1 次評分（96/100）後，因 Outbox Contract Gate 檢查發現 `FixedOutboxRepository` 問題而退回的版本。與返工第 1 次評分報告（`review_Phase-3F-0_1.md`）相比，本報告新增：
- §4 Outbox Contract Gate 失敗分析（含 §4.2 FixedOutboxRepository 詳細分析）
- 修正評分（96 → 93）
- 對 R7/R9/R12 的重新評估
- Accepted 由 YES 改為 NO

---

*報告結束 — Phase 3F-0 最終審查，因 Outbox Contract Gate FAIL 退回。*
