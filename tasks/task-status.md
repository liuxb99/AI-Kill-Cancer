# Task Status

## 場景
Phase 3A Final Acceptance Gate — PostgreSQL CI Gate + Real Pipeline Trace

## 任務
| ID | 描述 | 優先級 | 狀態 |
|----|------|--------|------|
| GATE-1 | GitHub Actions Postgres Integration Gate（修改 ci.yml） | P0 | [ ] |
| GATE-2 | Postgres Restart Recovery（修改 test_restart_recovery.py） | P0 | [ ] |
| GATE-3 | Real Pipeline Trace（修改 test_trace_persistence.py + source） | P0 | [ ] |
| GATE-4 | Real Trace Acceptance Test（新增 test_real_pipeline_trace_persistence.py） | P0 | [ ] |
| GATE-5 | Trace 欄位映射 Helper（修改 trace 寫入邏輯） | P0 | [ ] |
| GATE-6 | 完整驗證 + Git Commit & Push | P0 | [ ] |

## 禁止修改
- AGENTS.md
- Phase 3B 功能
- Vercel 部署
- 前端 UI
- 認證系統
- 無關格式化 / dependency upgrade

---

## Phase 3B — Clinical Decision Layer

**場景**：feature-dev（功能開發）

**啟動時間**：2026-07-25 19:02

**狀態**：進行中

**角色分派**：
| 角色 | 職責 |
|------|------|
| planner | 制定執行計劃 |
| backend-logic | 後端業務邏輯（Engine、Service） |
| api-designer | API 設計 |
| db-modeler | 資料庫建模（Model、Migration） |
| frontend-logic | 前端頁面與路由 |
| test-writer | 測試撰寫 |
| doc-writer | 文件與報告 |
| reviewer | 評分代理 |

**任務清單（待 planner 產出）**：
待 Step 2 PLANNER 完成後更新

---

## Phase 3B Hardening — 架構問題修正

**場景**：hardening（架構強化）

**啟動時間**：2026-07-26

**狀態**：待啟動

**角色分派**：
| 角色 | 職責 |
|------|------|
| planner | 制定強化計劃與優先級排序 |
| backend-logic | 後端邏輯修正（validation、audit trail、DTO） |
| frontend-logic | 前端邏輯修正（navigation、sample data 移除） |
| test-writer | 撰寫回歸測試驗證修正 |
| reviewer | 評分代理 |

**修正項目**：
| 優先級 | ID | 描述 | 狀態 |
|--------|----|------|------|
| P0 | HARDEN-1 | Recommendation 必須屬於同一位 Patient（加 validation） | [ ] |
| P0 | HARDEN-2 | created_by 必須完整傳遞（Audit Trail） | [ ] |
| P0 | HARDEN-3 | context.patient 不得覆蓋 Database Patient | [ ] |
| P0 | HARDEN-4 | Frontend Navigation 移除假資料 sample | [ ] |
| P1 | HARDEN-5 | Clinical Decision Trace 拆成 4~5 個 Step | [ ] |
| P1 | HARDEN-6 | DTO Mutable Default 修正 | [ ] |

**禁止修改**：
- AGENTS.md
- Phase 3A 已完成功能
- Vercel 部署
- 認證系統
