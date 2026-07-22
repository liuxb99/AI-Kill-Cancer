# 場景識別記錄

## 場景名稱
Phase 2 — Multi-Agent Clinical Decision Workspace

## 場景分類
後端開發 / 前端開發 / 測試 / 文檔

## 需求來源
tasks/requirements.md（Phase 2 多代理臨床決策工作空間）

## 分派角色

| 角色 | 職責 |
|------|------|
| PLANNER | 制定詳細實施計劃 |
| backend-logic | 實作後端模組（Context Builder, Evidence Collector, Agents, Consensus Engine, Recommendation Generator, Digital Thread） |
| frontend-logic | 實作前端新分頁 |
| ui-designer | 前端 UI 設計與元件拆分 |
| api-designer | API 設計 |
| db-modeler | 資料庫模型設計 |
| unit-tester | 單元測試 |
| integration-tester | 整合測試 |
| REVIEWER | 評分 |

## 依賴關係
- 後端模組完成後才能進行前端整合測試
- Digital Thread 需在所有決策節點完成後實作
