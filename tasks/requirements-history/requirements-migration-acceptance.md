# AI-Kill-Cancer — Phase 3B Final Migration Acceptance

Repository：https://github.com/liuxb99/AI-Kill-Cancer

Branch：master

Base Commit：0c67398

目前狀態：
- ChatGPT GitHub Review：91~93 / 100
- Accepted：NO
- Ready for Phase 3C：NO

## 本輪範圍
只允許修正 Migration 019 Acceptance。不得新增任何新功能。不得修改 Clinical Decision。不得修改 Recommendation。不得開始 Phase 3C。

## 工作方式
完全依 AGENTS.md 流程：Step 0B → Scene → Planner → Workflow → Batch → Step4b → Reviewer → Git Push。一次完成。

## P0：Migration 019 Downgrade 安全

目前 upgrade 可以在空資料庫成功，但 downgrade 只在空資料庫成功。
真正 Production 有 trace-A（step0~step4）時，恢復 UNIQUE(trace_id) 一定失敗。

### 必須決定正式策略（擇一）

#### 策略A（建議）
Migration downgrade 時，若同一 trace_id 存在多個 step，則停止 downgrade，回傳錯誤訊息：
"Cannot downgrade Migration 019. Database already contains multi-step Clinical Decision Trace. Downgrade would destroy persisted data."
不得自動刪資料、不得偷偷 merge、不得只保留 step0。

#### 策略B
若專案要求一定可以 downgrade，必須完整設計 Data Migration → Merge → Restore → Constraint，不得遺失 Clinical Trace。

## Migration Tests

新增 3 個 Case：

**Case1**：018 → 019 → Empty Database → 018 → PASS
**Case2**：018 → 019 → Insert 5 Trace Steps → Downgrade → 明確失敗 → Error Message 正確
**Case3**：018 → 019 → Re-upgrade → PASS

不得只測空資料庫。

## API Hardening

順便補上 skip >= 0、limit 1~100 的 Query(...) 驗證。不要做其他修改。

## Reviewer
評分 >= 95 才可停止。

## Commit
一個 Commit：fix(migration): make downgrade safe for multi-step traces
不得混入其他內容。

## 完成後只回報
Commit SHA / Migration Strategy / Downgrade Behavior / Migration Tests / Backend PASS / CI PASS / Reviewer Score

最後輸出：
Phase 3B：PASS / PARTIAL
Accepted：YES / NO
Ready for ChatGPT GitHub Review：YES / NO
Ready for Phase 3C：YES / NO

只有 Migration Acceptance PASS 且 Reviewer >=95，才允許 Accepted：YES、Ready for Phase 3C：YES
