# Task Status — Phase 3C Tumor Board Consensus Engine

## 場景識別

| 項目 | 內容 |
|------|------|
| **場景分類** | feature-dev（功能開發） |
| **場景說明** | 開發全新 Tumor Board Consensus Engine 模組，包含 Models / Migration / Repositories / Service / Engine / API / Frontend / Tests，採用 Minimal Integration / Repository Pattern / Service Transaction Boundary |
| **對照 scene_rules.yaml** | feature-dev：新功能模組的完整開發流程 ✓ |
| **需求來源** | tasks/requirements.md（Phase 3C 規格） |

## 角色分派

| 角色 | 職責 |
|------|------|
| **planner** | 制定執行計劃（Step 2 PLANNER） |
| **backend-logic** | 後端業務邏輯（Engine / Service / Repositories） |
| **api-designer** | API 設計（Router / Handler / Request/Response schema） |
| **db-modeler** | 資料庫建模（Models / Migration） |
| **frontend-logic** | 前端業務邏輯（Tumor Board 頁面與互動） |
| **unit-tester** | 單元測試（Engine / Service / API unit tests） |
| **integration-tester** | 整合測試（跨模組整合測試） |
| **doc-writer** | 文件撰寫（API docs / README） |
| **reviewer** | 評分代理（目標 >= 95 分） |

## 任務清單

| ID | 描述 | 優先級 | 狀態 |
|----|------|--------|------|
| **TBC-1** | PLANNER 制定執行計劃（模組拆解、依賴拓撲、里程碑） | P0 | [ ] |
| **TBC-2** | DB Modeler — Models & Migration（TumorBoardSession / ConsensusRecord） | P0 | [ ] |
| **TBC-3** | Backend Logic — Repositories（Session / Consensus CRUD） | P0 | [ ] |
| **TBC-4** | Backend Logic — Service Layer（Transaction Boundary / Business Logic） | P0 | [ ] |
| **TBC-5** | Backend Logic — Consensus Engine（投票邏輯 / 加權計算 / 結果產生） | P0 | [ ] |
| **TBC-6** | API Designer — REST API（Router / Handler / Validation） | P0 | [ ] |
| **TBC-7** | Frontend Logic — Tumor Board 前端頁面 | P1 | [ ] |
| **TBC-8** | Unit Tests（Engine / Service / API） | P0 | [ ] |
| **TBC-9** | Integration Tests（跨模組流程測試） | P0 | [ ] |
| **TBC-10** | Doc Writer — API 文件與 README 更新 | P1 | [ ] |
| **TBC-11** | REVIEWER 評分 + 最終驗證 | P0 | [ ] |

## 約束條件

- ❌ 不得修改任何已驗收模組（Phase 1 / 2 / 3A / 3B 既有程式碼）
- ❌ 不得修改 Clinical Decision 模組
- ❌ 不得修改 Recommendation 模組
- ✅ 採用 Minimal Integration（僅新增必要模組）
- ✅ 遵循 Repository Pattern + Service Transaction Boundary
- ✅ 所有新程式碼需通過測試驗證

## 完成條件

- 所有 TBC 任務完成（TBC-1 ~ TBC-11）
- 測試全部 PASS（Unit + Integration）
- Reviewer 評分 >= 95
- Git Commit & Push 成功

---

## 歷史記錄

| 時間 | 事件 |
|------|------|
| 待填 | Step 1 場景識別完成 |
