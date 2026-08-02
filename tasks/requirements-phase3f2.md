# Requirements — Phase 3F-2：Outbox event_id Defense-in-Depth

## 目標

強化 `ClinicalGraphOutboxRepository.create()` 的 event_id 契約，避免任何新 Service 或未來呼叫方遺漏 event_id 時造成 NOT NULL、事件重播、去重與稽核鏈中斷。

## 必須完成

1. Repository 在未提供 event_id 時自動產生 UUID 字串。
2. 明確拒絕空字串、純空白與非字串 event_id。
3. 保留呼叫方傳入的合法 event_id，不得覆寫。
4. 新增單元測試覆蓋 fallback、保留值、非法輸入與 flush 行為。
5. Ruff 與專項測試通過後合併 master。
