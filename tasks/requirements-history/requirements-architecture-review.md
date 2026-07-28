# Architecture Review (Phase 1 ~ Phase 3E)

## 任務類型
全面 Code Review + Architecture Review

## 禁止事項
- 禁止新增功能
- 禁止修改功能
- 禁止修改 API 行為
- 禁止修改程式
- 禁止重構
- 禁止 Commit 大量修改
- 只能：Review / Analysis / Report

## Review Scope
完整 Review 以下所有階段的全部程式：
Phase1 → Phase2 → Phase3A → Phase3B → Phase3C → Phase3D → Phase3E

## Review 項目

### 1. Domain
逐一檢查 Entity / Aggregate / ValueObject / State / Version 是否都有一致設計。
檢查 Domain 是否仍有 SQL / API / Session / HTTP 依賴。
全部列出。

### 2. Repository
確認 Repository 不得有 commit / rollback / flush。
確認 Repository 不得有 Business Logic。
全部列出。

### 3. Service
確認 Transaction Boundary 只有在 Service 層存在。
確認 Engine / Repository 不得開 transaction。
全部列出。

### 4. Engine
確認 Engine 是否為 Pure Function。
確認 Engine 不得有 DB / API / Repository / Session 依賴。
全部列出。

### 5. Migration
檢查所有 Migration 的 Upgrade → Downgrade → Re-upgrade 是否一致。
檢查 SQLite 與 Postgres 是否完全一致。
全部列出。

### 6. API
確認所有 GET / POST / PATCH / DELETE 的 HTTP Status / Error / Validation 是否一致。
全部列出。

### 7. Digital Thread
確認 Patient / Recommendation / Decision / Consensus / TreatmentPlan 的 Event → Outbox → Projection → KnowGraphGo 是否一致。
全部列出。

### 8. Trace
確認所有 Calculation Trace 的 trace_id / step_order / step_name / input / output / created_at 是否一致。
全部列出。

### 9. Graph Adapter
確認所有 Projection / Relation / Stub / Provenance 是否一致。
確認不得有 Duplicate Mapping。
全部列出。

### 10. Tests
確認 Coverage 是否缺少：
Engine / Repository / Service / API / Restart / Migration / Postgres / Graph。
全部列出。

### 11. Dead Code
找出 Unused / TODO / FIXME / Deprecated / Duplicate / Copy Paste。
全部列出。不得直接刪除。

### 12. Architecture Smell
找出 God Service / Long Function / Circular Dependency / Duplicated Logic / Duplicated SQL / Duplicated Validation。
全部列出。

### 13. Refactor Candidate
列出 High / Medium / Low 三個等級。
全部列出。

## 最終輸出（交付報告）
提供以下完整報告至 tasks/reviews/architecture_review.md：
1. Architecture Score
2. Maintainability Score
3. Technical Debt
4. Code Smell
5. Duplicate Code
6. Refactor List
7. Risk List
8. Phase 3F 建議
9. P0 / P1 / P2 改善清單
