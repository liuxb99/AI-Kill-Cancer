# Phase 3F-0：Transaction Boundary Hardening

## 架構 P0 問題
BaseRepository.create/update/delete 內部自行 commit()，造成 Service 無法控制跨 Repository 原子交易。

## 唯一目標
把 Transaction Boundary 完整收回 Service 層。

## 禁止事項
- 新增業務功能
- 開始 Phase 3F 其他功能
- Domain／ORM 分離
- Trace 統一
- Graph Adapter 重構
- API Contract 修改
- Frontend 修改
- Migration 大改
- AGENTS.md 修改

## 允許修改範圍
- BaseRepository
- 受影響 Repository
- 受影響 Service
- Transaction Tests
- Postgres CI
- 必要流程文件

## 需求條列

### R1：先建立失敗重現測試
- 不得先修改 BaseRepository
- 新增真實測試重現 Partial Commit（Atomicity Broken）
- 使用真實 AsyncSession、真實 Repository，不得全部 Mock
- 測試必須先紅（fail），再修程式

### R2：完整盤點 BaseRepository 使用範圍
- 搜尋 BaseRepository、super().create/update/delete、.create(/update(/delete(
- 範圍：src/backend/repositories/、src/backend/services/
- 產出使用清單（Repository、使用哪個方法、呼叫 Service、是否依賴自動 commit、修改後需要在哪裡補 Service commit）

### R3：Transaction Contract
- Repository：只能 add/execute/flush/refresh/delete/query，不得 commit/rollback/自行開 transaction/吞 exception
- Service：負責 Transaction Boundary、commit、rollback、跨 Repository 原子性、Outbox 同 Transaction
- Engine：不得 Session/Repository/commit/rollback
- API：不得 commit/rollback

### R4：修正 BaseRepository
- create：flush + refresh（取代 commit + refresh）
- update：flush + refresh（取代 commit + refresh）
- delete：delete + flush（取代 delete + commit）
- Repository 內不得有 commit/rollback

### R5：檢查所有 Repository
- 完整搜尋 await self.db.commit() / await db.commit() / await session.commit() / rollback()
- Repository commit → 移除或改 flush
- Repository rollback → 移除
- 每一處確認呼叫端 Service 有正式 Transaction Boundary

### R6：修正受影響 Service
- 所有寫入 Service 必須明確負責交易
- 優先檢查：RecommendationService、ClinicalDecisionService、TumorBoardConsensusService、TreatmentPlanService、ClinicalGraph Outbox 寫入流程、Patient/Case 建立流程
- 採用一致模式（try/commit/rollback 或 async with db.begin()）
- 不得在同一流程中 session.begin() + 手動 commit 重複控制交易

### R7：Outbox 原子性
- Recommendation + Recommendation Outbox 同 Transaction
- Clinical Decision + Decision Outbox 同 Transaction
- Consensus + Consensus Outbox 同 Transaction
- Treatment Plan + Treatment Plan Outbox 同 Transaction
- 驗證：業務資料成功 Outbox 失敗 → 全部 rollback；Outbox 成功業務資料失敗 → 全部 rollback
- 不得出現：業務資料存在 Outbox 不存在，或 Outbox 存在業務資料不存在

### R8：Flush 後可繼續使用
- flush 後取得 PK
- 後續 Repository 使用該 PK
- 建立 FK 子資料
- 建立 Outbox
- 最後由 Service commit
- 補測試驗證：Plan flush → Phase 使用 plan.id → Item 使用 phase.id → Outbox 使用 plan_id → Service commit

### R9：測試要求
- BaseRepository Tests：create/update/delete 不 commit、flush 後 PK 可用、rollback 後 create 不存在/update 恢復/delete 恢復；至少一組使用真實資料庫
- Atomicity Tests Flow A（Patient + Cancer Case，第二步失敗全部 rollback）
- Atomicity Tests Flow B（Treatment Plan + Phases + Items + Trace + Outbox，任一步失敗全部不存在）
- Recommendation/Decision/Consensus 至少選一條驗證主資料 + 子資料 + Outbox 同 Transaction
- Success Tests：Service commit 一次，所有資料存在，Outbox 存在
- Restart Recovery：建立資料 → shutdown → 重新讀取正常
- PostgreSQL CI：真實執行 BaseRepository atomicity、Cross-repository rollback、Treatment Plan rollback、Outbox rollback、Success commit、Restart recovery

### R10：回歸要求
- Phase 3A Recommendation
- Phase 3B Clinical Decision
- Phase 3C Tumor Board Consensus
- Phase 3D Graph Outbox
- Phase 3E Treatment Plan
- Migration Gate
- Frontend Build
- 全部通過：ruff、pytest、frontend tests、frontend build、Postgres tests、Migration gate

### R11：Commit Scope Gate
- 修改上限 20 個 production files
- 不得因 formatter/CRLF/import sorting/encoding 重寫大量無關檔案

### R12：Reviewer Gate
- 逐項確認 11 項檢查清單
- 任一項 FAIL/PARTIAL/SKIPPED → Reviewer 最高 89、Accepted = NO
- Reviewer 必須 >= 95

### R13：Git
- Commit message: fix(architecture): centralize transaction boundaries in services
- 允許一個後續 CI 修復 Commit
- 禁止 force push、修改歷史 Migration、開始其他架構重構

## 完成報告要求
見 Phase 3F-0 文檔第十五節。
