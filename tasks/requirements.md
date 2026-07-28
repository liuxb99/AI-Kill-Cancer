# Phase 3E Hardening（禁止新增功能，只修 Reviewer 問題）

> **核心原則：** 本輪不是新功能開發。禁止新增任何功能。只修 ChatGPT GitHub Review 指出的問題。依 AGENTS.md 完整流程執行。完成後一次回報。

---

## 修復範圍

### 允許修改
- TreatmentPlan
- Repository
- Service
- Migration
- Tests
- CI

### 禁止修改
- API 介面
- Frontend UI
- Engine 演算法
- Graph Schema

---

## P0-1 Versioning（最高優先）

**問題：** 目前 Versioning 設計錯誤：revision → new UUID → new plan_id → version+1，導致 GET /versions 只能查到自己。

**修正要求：**

- Database PK(id) 每個版本不同
- Business plan_id 所有版本固定
- version 使用 1, 2, 3... 遞增
- Migration：移除 plan_id UNIQUE，保留 UNIQUE(plan_id, version)
- revision：沿用舊 plan_id，version+1，不得產生新的 plan_id
- 重新補齊：Version tests、Repository tests、API tests
- 驗證：GET versions 必須一次看到 v1, v2, v3

---

## P0-2 Treatment Item Persistence

**問題：** Engine 已產生 drug_id, procedure_code, frequency, duration, route, planned_dose_text，但 Service 沒寫入 DB。

**修正要求：**

- 全部補齊上述欄位的持久化
- Restart Recovery 後不得遺失
- 新增 Persistence tests、Restart tests，逐欄驗證

---

## P0-3 Monitoring Persistence

**問題：** 遺失 target_range, warning_threshold, critical_threshold, action_if_abnormal, responsible_specialty。

**修正要求：**

- 全部補齊上述欄位的持久化
- 重新補 Restart tests、Digital Thread tests，逐欄驗證

---

## P0-4 Trace

**問題：** 每一步 trace_id 都是新的。

**修正要求：**

- 改成一個 Plan 共用同一 trace_id
- 使用 step_order 區分每一步
- Database：UNIQUE(trace_id, step_order)，不得使用 UNIQUE(trace_id)
- 重新補 Trace tests、Restart tests

---

## P1-1 Phase Mapping

**問題：** 所有 Item 都放第一個 Phase。

**修正要求：**

- 必須真正依 phase_type 或 Engine Output 分配 Item 到對應 Phase
- 新增 Phase mapping tests

---

## P1-2 Revision Policy

**問題：** revision 不可任何狀態都能做。

**修正要求：**

- 建立 RevisionPolicy
- 至少限制允許的狀態：approved、active、paused
- 禁止的狀態：draft、cancelled、completed、superseded
- 非法操作返回 HTTP 409

---

## P1-3 Migration Gate

**問題：** CI downgrade 023 upgrade 023 沒有真正測到 023。

**修正要求：**

- 改成真正測：head → 022 → 023 → head
- 有資料時 023 downgrade 必須失敗
- 空資料時 023 downgrade 必須成功

---

## 測試要求

- Version chain tests
- Persistence tests
- Restart Recovery tests
- Migration tests
- Trace tests
- Phase Mapping tests
- Revision Policy tests

> **注意：** 不得只補 Assertion，必須真正驗證行為。

---

## 禁止事項

- ❌ 新增 Placeholder
- ❌ 降低測試標準
- ❌ 修改 Reviewer
- ❌ 修改需求
- ❌ 跳過 CI
- ❌ continue-on-error
- ❌ 假 PASS

---

## Git 完成條件

完成後需執行以下步驟：

1. 全部編譯通過
2. 全部測試通過
3. 完整 CI 通過
4. Git Commit
5. Git Push

**最終回報內容：**

- Commit SHA
- GitHub Actions 狀態
- 新增測試數
- 修復項目清單
- 修改檔案清單

> **重要：** 不要自己宣告 Accepted，等待 ChatGPT 使用 GitHub Connector 做正式 Review。
