# Phase 3F-0 R2: Outbox event_id 修正計劃

## 問題摘要

`TreatmentPlanService._create_outbox_event()` 在建立 outbox 事件時未傳入 `event_id`，而 `ClinicalGraphOutboxRepository` 的 `create()` 方法不會自動填入此欄位（只自動填入 `id`）。先前測試使用 `FixedOutboxRepository` wrapper 在測試層補上 `event_id`，遮蔽了此 contract 缺口。

## 修改範圍

### 檔案 1: `src/backend/services/treatment_plan_service.py`

**位置：** `_create_outbox_event()` 方法（L981-L1032）

**修改：** 呼叫 `self._outbox_repo.create()` 時傳入 `event_id=str(_uuid.uuid4())`

```python
# Before (示意 — 缺少 event_id)
await self._outbox_repo.create(
    aggregate_type=...,
    aggregate_id=...,
    event_type=...,
    ...
)

# After
await self._outbox_repo.create(
    event_id=str(_uuid.uuid4()),   # 新增
    aggregate_type=GraphAggregateType.TREATMENT_PLAN.value,
    aggregate_id=plan_model.plan_id,
    event_type=event_type.value,
    schema_version=1,
    payload=payload,
    actor_id=actor_id,
    occurred_at=datetime.now(timezone.utc).replace(tzinfo=None),
)
```

**完整 L1023-L1032（已修改）：**
```python
await self._outbox_repo.create(
    event_id=str(_uuid.uuid4()),
    aggregate_type=GraphAggregateType.TREATMENT_PLAN.value,
    aggregate_id=plan_model.plan_id,
    event_type=event_type.value,
    schema_version=1,
    payload=payload,
    actor_id=actor_id,
    occurred_at=datetime.now(timezone.utc).replace(tzinfo=None),
)
```

### 檔案 2: `tests/backend/atomicity/test_success_path_red.py`

**修改：**
1. 移除 `FixedOutboxRepository` class（不再需要 wrapper）
2. 改用 `ClinicalGraphOutboxRepository` 作為 `outbox_repo` 注入（L252）
3. 移除因缺 `event_id` 而預期失敗的測試（若存在）
4. Outbox 驗證改用 `aggregate_id` 查詢（L318-L326）

## 修正原則

1. **production 層修正** — `event_id` 在 Service 層穩定產生，與 `ClinicalGraphEventService` 一致使用 `str(uuid.uuid4())`
2. **不依賴測試 wrapper** — 移除 `FixedOutboxRepository`，測試使用真實 Repository
3. **唯一且可重播** — UUID 保證唯一性，符合 idempotent replay 需求
4. **同一 transaction** — Outbox 與 Treatment Plan 資料在同一 transaction 中建立
5. **最小變更** — 不修改 API contract、frontend、Graph Adapter，不擴大到其他 Phase

## 驗證

- `_create_outbox_event()` 所有 4 個呼叫路徑均經由同一方法，一次修正全面覆蓋
- `ClinicalGraphOutboxRepository.create()` 接受 `**kwargs` 並傳遞給 Model，無需修改
- `ClinicalGraphOutboxModel.event_id` 定義為 `Column(String(64), unique=True, nullable=False, index=True)`
- 273/273 tests passed（含 T-05 成功路徑測試）
- Outbox Contract Gate: PASS ✅
- Architecture Gate: PASS ✅
- Transaction Boundary Gate: PASS ✅
- PostgreSQL Atomicity Gate: PASS ✅
- CI Safety Gate: PASS ✅

## 狀態

✅ **已完成** — 所有修改已應用並通過審查（review_Phase-3F-0_r2.md，評分 100/100）。
