# Task Status

## 場景
devops（CI/CD 驗收）

## 角色分派
- planner: 規劃驗收步驟
- devops: CI 驗證執行
- reviewer: 驗收確認

## 當前任務
Phase 3C 最終 CI 驗收

## 範圍限制
- 目標：找出 Commit `437581a` 對應的 GitHub Actions Run（以 `head_sha` 匹配），逐一檢查 Run 中全部 9 個步驟是否通過
- 只做 CI 驗證，不修改任何源代碼
- 不得修改：Engine、Service、Repository、Migration 020、Frontend、Tests、AGENTS.md
- 僅允許驗證操作：讀取 CI 執行狀態

## 驗收標準
- [ ] 找到對應 Commit 的 GitHub Actions Run
- [ ] Run 中所有步驟全部通過（綠色勾）
- [ ] 記錄驗收結果與截圖證據
- [ ] 更新 summary-report-phase3c-ci-final-fix.md

## Phase 3D：Clinical Knowledge Graph Adapter
状态：进行中
场景：feature-dev

### 任务清单
- [ ] P3D-001：Migration 021 — 建立 domain_clinical_graph_outbox 表
- [ ] P3D-002：ClinicalGraphOutboxModel 與 Outbox Repository
- [ ] P3D-003：ClinicalGraphEvent Schema DTO
- [ ] P3D-004：ClinicalGraphEventService（Service 層整合）
- [ ] P3D-005：KnowGraphGo Clone 與專案結構了解
- [ ] P3D-006：KnowGraphGo Clinical Domain Adapter（Ontology + Adapter）
- [ ] P3D-007：KnowGraphGo Clinical CLI（apply/rebuild/verify）
- [ ] P3D-008：AI-Kill-Cancer ClinicalGraphClient（Adapter Client）
- [ ] P3D-009：ClinicalGraphProjectionWorker
- [ ] P3D-010：Rebuild CLI（python -m src.backend.cli.clinical_graph）
- [ ] P3D-011：Graph Status API（/api/v1/clinical-graph/status 等）
- [ ] P3D-012：Graph Query API（patient thread / recommendation explain / consensus explain）
- [ ] P3D-013：Frontend ClinicalGraphPage + View in Knowledge Graph 連結
- [ ] P3D-014：Outbox Service 注入（RecommendationService / ClinicalDecisionService / TumorBoardConsensusService）
- [ ] P3D-015：測試（Event Schema / Outbox / Service Transaction / Adapter / Worker / Rebuild / Query / Digital Thread / Restart Recovery / Frontend）
- [ ] P3D-016：CI 更新（AI-Kill-Cancer + KnowGraphGo + Cross-repository Integration）
- [ ] P3D-017：Step 4b 需求回歸檢查
- [ ] P3D-018：REVIEWER 評分
- [ ] P3D-019：總結報告 + Git Commit & Push
