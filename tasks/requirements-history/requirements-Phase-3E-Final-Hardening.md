# Phase 3E Final Hardening（Migration 025 + CI Acceptance）

## 核心原則
- 不得修改業務功能
- 不得修改 Engine
- 不得修改 API 行為
- 不得修改 Frontend

## P0-1 PostgreSQL Trace Constraint
Migration 025 必須：
1. 查詢 PostgreSQL 目前真正存在的 UNIQUE Constraint
2. 刪除 `domain_treatment_plan_traces_trace_id_key` 或任何 UNIQUE(trace_id)
3. 再建立 UNIQUE(trace_id, step_order)
4. 不得只 DROP INDEX（Constraint 與 Index 必須區分）
5. 必須支援同 trace_id 多 step 全部成功
6. 新增 PostgreSQL Integration Test

## P0-2 Migration 025 Downgrade
downgrade 完成後必須恢復為 Migration 024 Schema：
1. plan_id UNIQUE
2. trace_id UNIQUE
3. previous_version_id 移除
4. supersedes_version_id 移除
5. 新增 024→025→024→025 Schema Compare Test

## P0-3 CI Migration Gate
CI 必須完整執行：
1. Postgres → upgrade → migration verify → migration tests → downgrade → re-upgrade → verify → PASS
2. 不得 continue-on-error、skip、allow-failure

## P0-4 Downgrade Environment
1. Migration Gate 使用全新 PostgreSQL Database，不得使用已有測試資料
2. 流程：create db → upgrade → migration verify → downgrade → upgrade → verify
3. Migration Gate 與 Integration Test 必須隔離

## P1 PostgreSQL Migration Robustness
所有 DROP CONSTRAINT / DROP INDEX / ADD CONSTRAINT / CREATE INDEX 均需：
- IF EXISTS / IF NOT EXISTS
- 或動態查詢 pg_constraint
- SQLite 仍保持相容

## P1 Tests
1. Trace Constraint 測試：同 trace_id 三筆不同 step 全部 PASS
2. Downgrade 驗證：025→024 Schema Equal → 025 Schema Equal
3. PostgreSQL 真實：upgrade → downgrade → upgrade → insert → query 全部 PASS
4. GitHub Actions Backend 全部 SUCCESS，不得 Failure / Skipped / Neutral

## 完成交付清單
1. Commit SHA
2. Files Changed
3. Migration 025 修改內容
4. 新增 PostgreSQL Tests
5. 新增 CI Tests
6. Run ID
7. Backend 結果 (SUCCESS)
8. Frontend 結果 (SUCCESS)
9. Migration Verification (PASS)
10. Migration Tests (PASS)
11. Downgrade (PASS)
12. Re-upgrade (PASS)
13. Schema Compare (PASS)
14. git status
15. Reviewer Score (>=95)

## 驗收標準
- Backend SUCCESS
- Frontend SUCCESS
- Migration Verification PASS
- Migration Tests PASS
- Upgrade PASS
- Downgrade PASS
- Re-upgrade PASS
- Schema Compare PASS
- Reviewer >=95
- 否則不得宣告 Accepted 或 Ready for Next Phase
