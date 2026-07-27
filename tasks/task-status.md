# Task Status

## 場景
cross-repo-acceptance-fix

## 場景說明
跨倉庫（KnowGraphGo × AI-Kill-Cancer）修正 Phase 3D Final Acceptance 的四個驗收缺口

## 角色分派
- **planner**: 規劃執行計劃
- **general-manager**: 總經理，流程管控、子代理調度、協調兩個倉庫
- **backend-logic**: 實作 KnowGraphGo Clinical CLI `clinical id` 指令及 Adapter Canonical Payload 映射
- **unit-tester**: 撰寫 Go CLI Tests 與 Adapter Tests
- **integration-tester**: 撰寫跨倉庫 E2E 測試、ID Parity 測試、Replay 驗證、Stub Preservation 驗證
- **doc-writer**: 撰寫 `docs/clinical-graph-event-schema-v1.md` Canonical Schema 文件
- **reviewer**: 評分驗證（需 >= 95 分才可結案）

## 當前階段
Step 1 — 場景識別與角色分派

## 範圍限制
- ❌ 不得新增功能（不得新增 Treatment Plan 或其他 API）
- ❌ 不得重構 Outbox
- ❌ 不得修改已驗收的 Clinical Domain 功能（Recommendation／Decision／Consensus 核心）
- ❌ 不得開始 Treatment Plan
- ❌ 不得修改或提交 AGENTS.md
- ❌ 不得修改 Migration 017～022
- ❌ 不得降低 CI 標準

## 驗收標準
1. ✅ `clinical id` CLI 真實存在
2. ✅ Python == Go CLI ID parity
3. ✅ Canonical Event Schema 一致
4. ✅ Drug Entity / Relation 真實建立
5. ✅ Evidence Entity / Relation 真實建立
6. ✅ Consensus Opinion / Specialty 真實建立
7. ✅ Path JSON 內容正確
8. ✅ Relation Kind 正確
9. ✅ Count Query 無零值假 PASS
10. ✅ Replay Count 不增加
11. ✅ Stub 不覆蓋完整 Patient
12. ✅ Relation Provenance 可從 Store 查回
13. ✅ GitHub Actions 全綠

---

## 執行清單

### Step 1：場景識別與角色分派 ✅（已完成）
- [x] 識別場景
- [x] 分派角色
- [x] 寫入 task-status.md
