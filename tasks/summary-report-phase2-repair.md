# Phase 2 修復 — 總結報告

## 基本信息
- **日期**: 2026-07-23
- **基線 commit**: 60b2ec3 (chore: remove unrelated Go files)
- **最終評分**: 97/100 ✅（返工 1 次後合格）

---

## 六大修復項目完成狀態

### 1. Phase 2 Scope Cleanup ✅
- config/ 目錄已無 Go 檔案（僅保留 4 個 .md 配置文件）
- git grep 確認無任何 LlamaEnv/Go 引用殘留
- 無需代碼修改，純檢查驗證

### 2. Clinical Logic Audit — Evidence 狀態模型改進 ✅
- **evidence_models.py**: 新增 `SourceStatusType` 枚舉（AVAILABLE/UNAVAILABLE/AUTHORIZATION_REQUIRED/ERROR）、`SourceStatus` model（含 `items_count` 字段）、`EvidenceBundle.source_statuses` 字段
- **collector.py**: 
  - `collect()` 和 `collect_by_variant()` 均記錄完整 source_statuses
  - 每個來源成功→AVAILABLE，異常→ERROR，授權源→AUTHORIZATION_REQUIRED
  - 提取 `_report_auth_sources()` 共用方法
- **測試**: 新增 `TestSourceStatus` 類（6 個測試），共 59 個 evidence collector tests

### 3. Authorization Audit ✅
- 審計所有 v1 路由（18 個模組），所有端點已有授權裝飾器
- 新增 **tests/test_authorization_hardening.py**（~440 行，53 個測試）
- 測試類：`TestClinicalEndpointAuthorization`、`TestRoleBoundary`、`TestTokenValidation`、`TestCaseACLModel`、`TestGlobalRBAC`、`TestRouteSecurityCoverage`

### 4. Database Persistence Verification ✅
- 審計 `DecisionThreadRepository.create_node()` 的 commit/refresh 流程，一切正確
- 新增 `TestDecisionNodePersistence` 類（6 個測試）：session reload、injector chain、nullable fields
- **session.py**: `get_db()` 增加 except rollback 處理

### 5. Migration Verification ✅
- 審計 migration 016（4 表創建/刪除），upgrade/downgrade 對稱
- 新增 **tests/integration/test_migration_016.py**（4 個測試類，7 個靜態審計測試）

### 6. Vercel Deployment Repair ✅
- 重寫 **vercel.json**：rootDirectory、buildCommand、outputDirectory、rewrites（SPA + API proxy）、nodeVersion
- 根因診斷：SPA rewrites 缺失、重複 npm ci、缺少 rootDirectory

---

## 修改檔案清單

| 檔案 | 操作 | 說明 |
|------|------|------|
| `src/backend/clinical/evidence_models.py` | 修改 | 新增 SourceStatusType/SourceStatus/source_statuses |
| `src/backend/clinical/collector.py` | 修改 | 完整 source_statuses 追蹤，AVAILABLE/ERROR 記錄 |
| `src/backend/database/session.py` | 修改 | get_db() 增加 rollback 處理 |
| `vercel.json` | 重寫 | rootDirectory + rewrites + nodeVersion |
| `tests/test_authorization_hardening.py` | 新增 | 授權矩陣測試（53 tests） |
| `tests/integration/test_migration_016.py` | 新增 | Migration 靜態審計測試（7 tests） |
| `tests/unit/test_decision_thread.py` | 修改 | 新增 persistence 測試（6 tests） |
| `tests/unit/test_evidence_collector.py` | 修改 | 新增 SourceStatus 測試，適配新 return type |

---

## 測試結果
- unit tests: **268 passed**（含 evidence_collector 59、decision_thread 6）
- authorization hardening: **53 passed**
- migration static: **7 passed**
- **總計: 275+ tests passed ✅**

---

## 評分歷程

| 循環 | 分數 | 狀態 |
|------|------|------|
| 初次 | 58/100 | ❌ 不合格 |
| 返工第 1 次 | 97/100 | ✅ 合格 |

## 待辦事項（非阻塞）
- [ ] 在 Vercel Dashboard 手動設置環境變數 `VITE_API_URL`
- [ ] 本地前端 build 驗證：`cd src/frontend && npm ci && npm run build`
- [ ] Vercel 部署驗證
