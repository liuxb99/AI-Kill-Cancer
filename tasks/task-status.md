# Task Status

## 任務 ID
Phase-3E-Hardening

## 場景
hardening（架構強化）

## 場景描述
修正既有功能的架構問題、邊界案例驗證、審計追蹤補全

## 角色分派
| 角色 | 職責 |
|------|------|
| planner | 制定強化計劃與優先級排序 |
| backend-logic | 後端邏輯修正（versioning、persistence、trace、phase mapping、revision policy） |
| test-writer | 撰寫回歸測試驗證修正（version chain、persistence、restart recovery、migration、trace、phase mapping、revision policy） |
| reviewer | 評分代理 |

## 優先級
- P0-1 Versioning（最高優先）
- P0-2 Treatment Item Persistence
- P0-3 Monitoring Persistence
- P0-4 Trace
- P1-1 Phase Mapping
- P1-2 Revision Policy
- P1-3 Migration Gate
