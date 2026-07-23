# Phase 2 修復與驗收需求

## 來源
2026-07-23 指令：Phase 2 未驗收，需執行以下六大修復項目。

## 六大強制要求

### 1. Phase 2 Scope Cleanup
- 確認無關 Go 檔案（llama-server/Unsloth config）已徹底清除
- 確認無殘留引用

### 2. Clinical Logic Audit
- 審核 EvidenceCollector 中 NCCN/ESMO/OncoKB 狀態：從純 log warning 改為明確的 `unavailable` / `authorization_required` 狀態模型
- 審核 Consensus confidence 計算邏輯
- 審核 Recommendation 引擎

### 3. Authorization Audit
- 審核 API 端點授權機制
- 建立 authorization matrix 測試

### 4. Database Persistence Verification
- 驗證 ClinicalContext / DecisionNode / EvidenceBundle 的持久化正確性
- 測試 session reload 後 Digital Thread 是否正常

### 5. Migration Verification
- 執行 migration upgrade → downgrade → upgrade 完整循環
- 驗證 016_phase2_clinical_workspace.py 正確性

### 6. Vercel Deployment Repair
- 診斷 Vercel 部署失敗根因
- 修復配置或程式碼問題

## 完成條件
- 所有修復有真實程式碼 diff（非僅文檔變更）
- 測試全部通過
- 成功 push 到 origin/master
- Vercel 部署成功
- REVIEWER 評分 ≥ 90
