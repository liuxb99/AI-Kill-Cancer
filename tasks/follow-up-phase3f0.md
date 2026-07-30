# Follow-up: Phase 3F-0 殘留議題

本文件記錄 Phase 3F-0 中發現但**不在本輪修正範圍**的問題。

---

## 1. FixedOutboxRepository 遮蔽 Outbox Contract

**檔案：** `tests/backend/atomicity/test_success_path_red.py`

**問題：**
`TestTreatmentPlanServiceSuccessPath` 測試使用 `FixedOutboxRepository` wrapper，該 wrapper 在 `event_id` 未提供時自動補上一個隨機 UUID。

```python
class FixedOutboxRepository:
    async def create(self, **kwargs):
        if "event_id" not in kwargs:
            kwargs["event_id"] = f"event-{uuid.uuid4().hex}"
        return await self._inner.create(**kwargs)
```

**影響：**
- Production `TreatmentPlanService._create_outbox_event()` 方法不傳入 `event_id`
- `ClinicalGraphOutboxModel.event_id` 是 `NOT NULL` 且無資料庫層預設值
- `FixedOutboxRepository` 在測試層補上 `event_id`，使測試通過，但遮蔽了 production service 未履行 Outbox contract 的真實問題

**建議處置：**
- 在 Production 層修正 `_create_outbox_event()`，確保其產生合法的 `event_id`
- 移除此 wrapper 後，所有相關測試應仍可通過
- 此為 Outbox 模式正確性議題，非交易邊界問題

**狀態：** 未開始（排入後續 Phase）
