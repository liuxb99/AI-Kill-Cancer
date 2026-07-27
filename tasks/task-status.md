# Task Status

## 場景
- 場景類型：acceptance-fix（自定義場景）
- 任務ID：Phase-3D-Final-Acceptance-Fix-R2
- 創建時間：2026-07-27 22:05

### 選擇理由

本任務跨越 CI/CD 配置修復、E2E 測試強化、Go 後端開發三個領域，標準場景（devops、hardening）均無法涵蓋全部所需角色，故採用自定義場景 `acceptance-fix`。

| 需求 | 性質 | 所需角色 |
|------|------|---------|
| P0-1 Postgres Integration Gate | CI 配置修復 + DB migration 相容性修復 | devops, backend-logic |
| P0-2 Stub Preservation | E2E 測試強化（四次驗證五欄位） | test-writer |
| P0-3 Relation Provenance | 新增 Relation Query + 八欄位驗證 | knowgraphgo-dev, test-writer |
| P0-4 KnowGraphGo Checkout | CI 固定 SHA | devops |

### 比對記錄

| 場景 | 匹配度 | 說明 |
|------|--------|------|
| feature-dev | ❌ 低 | 需要 api-designer/frontend-logic 等角色，本任務不需要 |
| bug-fix | ❌ 低 | 缺少 devops、test-writer 角色 |
| devops | ⚠️ 中 | 有 devops 角色但缺少 test-writer，無法處理 P0-2/P0-3 |
| hardening | ⚠️ 中 | 有 test-writer 但缺少 devops 和 knowgraphgo-dev |
| **acceptance-fix（自定義）** | ✅ 高 | 可靈活涵蓋所有必要角色 |

## 角色分派
| 角色 | 負責人 | 任務 |
|------|--------|------|
| PLANNER | planner | 制定執行計劃 |
| devops | devops | 修復 CI 配置（P0-1、P0-4） |
| backend-logic | backend-logic | 修復 Postgres/Databse migration 相容性（P0-1.2） |
| test-writer | test-writer | 強化 E2E 測試（P0-2、P0-3 測試部分） |
| knowgraphgo-dev | knowgraphgo-dev | Go 端新增 Relation Query（P0-3） |
| REVIEWER | reviewer | 評分驗證 |

## 任務清單
| ID | 優先級 | 描述 | 負責角色 | 狀態 |
|----|--------|------|----------|------|
| P0-1 | P0 | Postgres Integration Gate — 移除 continue-on-error 並修復 Migration/Postgres 相容性 | devops + backend-logic | pending |
| P0-2 | P0 | Stub Preservation — E2E 測試強化，四次驗證五個欄位一致 | test-writer | pending |
| P0-3 | P0 | Relation Provenance — 新增真正 Relation Query，驗證八個欄位 | knowgraphgo-dev + test-writer | pending |
| P0-4 | P0 | KnowGraphGo Checkout — CI 固定 SHA 6d2b20a6，不得 checkout main | devops | pending |
