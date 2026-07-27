# Task Status

## 場景
hardening（架構強化）

## 場景說明
修正既有功能的架構問題、邊界案例驗證、審計追蹤補全 — Phase 3D Graph Correctness Hardening

## 角色分派
- planner: 制定強化計劃與優先級排序
- backend-logic（Python + Go）: 後端邏輯修正（validation、audit trail、ID 確定性）
- knowgraphgo-dev（Go）: KnowGraphGo Clinical ID Factory、Clinical Adapter、Clinical CLI
- frontend-logic（如需）: 前端邏輯修正（navigation、sample data 移除）
- test-writer: 撰寫回歸測試驗證修正（含跨語言 ID Parity 測試、跨倉庫 Integration Test）
- reviewer: 評分代理
- devops（CI）: CI 修正（KnowGraphGo SHA pin、跨倉庫 CI）

## 當前階段
Phase 3D Graph Correctness Hardening（Base Commit: 5882612 / 4b63405）
先前審查：PARTIAL（≈60/100），Accepted NO，Ready for Treatment Plan NO

## 範圍限制
- 只修知識圖譜的：Identity, Relations, Idempotency, Provenance, Query Consistency, Worker Correctness, Cross-repository Integration
- 不是重新設計 Outbox，不是 Treatment Plan
- 不得混入 Phase 3E / 其他功能 / AGENTS.md 大型修改
- 禁止 force push / rebase / 修改舊 Commit
- 先 KnowGraphGo 完成 → Push → 取得 SHA → AI-Kill-Cancer CI pin 該 SHA → 再完成 AI-Kill-Cancer Commit

## 驗收標準
全部通過以下才允許 Accepted=YES：
- [ ] Deterministic ID PASS
- [ ] Relation Integrity PASS
- [ ] Idempotent Replay PASS
- [ ] Digital Thread PASS
- [ ] Provenance PASS
- [ ] Python/Go ID Parity PASS
- [ ] Worker Correctness PASS
- [ ] Cross-repository CI PASS
- [ ] Reviewer >= 95

## Phase 3D：Graph Correctness Hardening — 任務清單

### KnowGraphGo（Go）
- [ ] KG-01：ClinicalIDFactory — Deterministic ID 實作（UUIDv5 + 固定 Namespace）
- [ ] KG-02：Clinical Adapter 修正 — Target Entities + Relations + Provenance
- [ ] KG-03：Idempotent Replay 測試（Go golden tests）

### AI-Kill-Cancer（Python）
- [ ] AKC-01：Outbox Schema 補強 + Migration 022（correlation_id, causation_id, occurred_at, claim_token, processing_started_at, last_failed_at）
- [ ] AKC-02：Event Payload 與真實模型同步（RecommendationService / ClinicalDecisionService / TumorBoardConsensusService）
- [ ] AKC-03：Python ClinicalGraphIDFactory + ID Parity 測試
- [ ] AKC-04：ClinicalGraphClient 非阻塞化（asyncio.create_subprocess_exec）
- [ ] AKC-05：Worker Transaction 修正 + Stale Recovery（SELECT FOR UPDATE SKIP LOCKED、claim_token、processing_started_at、last_failed_at）
- [ ] AKC-06：Failed Events 狀態一致性 + Status API 真實健康度（operational / degraded / unavailable）
- [ ] AKC-07：Explain Query 修正（不得將 Entity ID 當 Relation ID、確認真實路徑）
- [ ] AKC-08：CI 修正（KnowGraphGo SHA pin、cross-repository CI）

### 跨領域整合
- [ ] INT-01：跨語言 ID Parity 測試（Python ID == Go ID）
- [ ] INT-02：跨倉庫 Integration Test（CLI build → 臨時 SQLite → Event apply → 重放 → query → 驗證冪等 + Digital Thread）

### Meta（文件與流程）
- [ ] META-01：docs/clinical-graph-id-spec.md 規格文件
- [ ] META-02：Step 4b 需求回歸檢查
- [ ] META-03：REVIEWER 評分
- [ ] META-04：總結報告 + Git Commit & Push

## 注意事項
- 嚴格遵守 AI-Kill-Cancer 與 KnowGraphGo 各自的 AGENTS.md 與既有流程
- 一次完成，不要中途回報
- 完成兩個 Repository、測試、CI、Commit、Push 後一次回報
- 不得自行開始下一階段（Phase 3E / Treatment Plan）
