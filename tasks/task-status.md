# Task Status — Phase 3F-0：Transaction Boundary Hardening

## 場景
hardening（架構強化）

## 場景描述
修正既有功能的架構問題、邊界案例驗證、審計追蹤補全。

## 分派角色
| 角色 | 職責 |
|------|------|
| PLANNER | 制定強化計劃與優先級排序 |
| backend-logic | 修正 BaseRepository、Repository、Service |
| test-writer | 撰寫 Transaction Tests（Atomicity + Rollback + Success） |
| doc-writer | 撰寫必要流程文件 |
| REVIEWER | 評分代理 |

## 角色分工說明
- **PLANNER**：產出 tasks/plan-Phase-3F-0.md，含任務清單、依賴、負責角色、返工預案
- **backend-logic**：修改 BaseRepository（commit→flush）、檢查所有 Repository 移除非必要 commit/rollback、修正受影響 Service 加入 Transaction Boundary
- **test-writer**：撰寫 BaseRepository 測試、Atomicity Tests（Flow A+B）、Recommendation/Decision/Consensus 擇一測試、Success Tests、Restart Recovery 測試
- **doc-writer**：撰寫必要流程文件
- **REVIEWER**：依 AGENTS.md 規定評分，>=95 合格

## 排除角色
- frontend-logic（本輪禁止 Frontend 修改）
- api-designer（本輪禁止 API Contract 修改）
- db-modeler（本輪禁止 Migration 大改）
