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

---
## 任務：Phase 3E Versioning Final Fix

### 場景
hardening（架構強化）— 修正 ChatGPT GitHub Review 發現的 Phase 3E 架構問題

### 角色分派
| 角色 | 職責 |
|------|------|
| PLANNER | 制定修正計劃與優先級排序 |
| backend-logic | Migration 025、Repository Version Chain、Version Link、Phase Mapping 後端修正 |
| test-writer | Migration Test、Version Chain Test、Version Link Test、Phase Mapping Test、Restart Recovery、Digital Thread |
| REVIEWER | 評分代理 |

### P0 任務清單
| ID | 描述 | 負責角色 |
|----|------|---------|
| P0-1 | Migration Compatibility：新增 Migration 025，修正 UNIQUE 約束 | backend-logic |
| P0-2 | Repository Version Chain：拆分 get_by_plan_id、新增版本感知查詢 | backend-logic |
| P0-3 | Version Link：previous_plan_id → previous_version_id，建立 self reference | backend-logic |
| P0-4 | Phase Mapping：Engine 輸出 phase_type，Service 依 phase_type 分配 Phase | backend-logic |
| T-ALL | 全部測試：Migration、Version Chain、Version Link、Phase Mapping、Restart Recovery、Digital Thread | test-writer |
