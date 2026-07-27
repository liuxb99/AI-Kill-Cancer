# Phase 3C Hardening

Repository: https://github.com/liuxb99/AI-Kill-Cancer
Branch: master
Base Commit: 3441f47

## 目前狀態
- Phase 3C：PARTIAL
- ChatGPT GitHub Review：80/100
- Accepted：NO
- Ready for Phase 3D：NO

## 範圍限制
- 只允許修正：P0-1 Migration 020 Downgrade、P0-2 Restart Recovery、P0-3 Frontend Tests、P0-4 Postgres CI、P0-5 AGENTS.md Scope
- 不得新增功能、頁面、API、Engine
- 不得修改 Recommendation / ClinicalDecision / Phase3A / Phase3B
- 不得開始：Treatment Plan、Phase 3D、Phase 4

## P0-1 Migration 020 Downgrade
目前狀態：downgrade() 永遠 raise IrreversibleMigrationError，不符合 020→019→020 驗證需求。

必須改成：
- 空資料庫：020→019 正常 drop（consensus, opinions, traces 三表）
- 有正式資料：先檢查 domain_tumor_board_consensus、domain_tumor_board_opinions、domain_tumor_board_consensus_traces 三表 COUNT(*)
  - 任何 >0 則 raise IrreversibleMigrationError（不可刪資料、不可 merge、不可 truncate）
  - Error 保持 "Cannot downgrade..."
- Migration Tests：
  - Empty DB → 020→019 PASS
  - Data Exists → 020→019 Blocked PASS
  - 019→020 PASS

## P0-2 Restart Recovery
目前狀態：PARTIAL，不是 PASS。

必須真正完整鏈路：
App1 → POST → Shutdown → App2 → GET Consensus → GET Opinions → GET Trace 全部 PASS

不得用 SQLite create_all 冒充 Restart
必須完整：API → Service → Repository → Database → Restart → 讀回

## P0-3 Frontend Tests
目前狀態：168/172
修到：172/172
不得 skip、xfail、刪測試

## P0-4 Postgres CI
本輪必須在 GitHub Actions 上真正執行 Postgres CI
涵蓋：Migration 020、Engine、Service、API、Digital Thread、Restart Recovery 全部 Postgres PASS
回報：Run ID、全部 Job Success
沒有 GitHub Actions 則 Reviewer 不得 >89

## P0-5 AGENTS.md Restore
上一輪修改了 AGENTS.md，本輪必須回復。
不得保留與 Phase3C 無關的流程修改。
Commit 只能包含 Tumor Board Hardening。

## P1-1 Consensus Status Default
目前 Migration 中 consensus_status 的 default 從 unanimous
改成 pending 或 insufficient_information
避免 Service 漏寫時產生假共識

## 禁止事項
- 不得新增功能、頁面、API、Engine
- 不得修改 Recommendation / ClinicalDecision / Phase3A / Phase3B

## Commit
一個 commit：fix(phase3c): harden migration restart and ci
不得混入其他內容

## 完成條件
Migration PASS + Restart PASS + Frontend PASS + CI PASS + Reviewer >=95
才允許 Phase 3C Accepted: YES、Ready for Phase 3D: YES
