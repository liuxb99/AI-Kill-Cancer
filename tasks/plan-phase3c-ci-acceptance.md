# Phase 3C 最終 CI 驗收計劃 — ci-acceptance

> **任務 ID**：phase3c-ci-acceptance  
> **場景**：最終 CI 驗收（Final Acceptance Gate）  
> **目標**：驗證最新 Commit `437581a330444c2bdf361076437d54ff4a846a84` 對應的 GitHub Actions Run 是否全部通過  
> **Commit**：`437581a330444c2bdf361076437d54ff4a846a84`  
> **Repository**：`liuxb99/AI-Kill-Cancer`  
> **Workflow**：`ci.yml`

---

## 1. 任務概要

### 1.1 背景

Phase 3C（Tumor Board Consensus Engine）已完成開發、硬化（hardening）與回歸檢查。現需對最新 Push 的 Commit 執行最終 CI 驗收，確認 GitHub Actions 上所有 Job 與 Step 全部通過，才能標記 Phase 3C 正式驗收完成。

### 1.2 範圍

| 範圍 | 狀態 |
|------|------|
| 查詢 GitHub Actions Runs（`gh run list`） | ✅ 執行 |
| 匹配 headSha == 目標 Commit | ✅ 執行 |
| 檢視 Run 詳細狀態與 Jobs（`gh run view --json`） | ✅ 執行 |
| 讀取失敗 log（`gh run view --log-failed`） | ✅ 條件執行 |
| 確認所有 Step 為 SUCCESS | ✅ 執行 |
| 標記驗收結果 | ✅ 執行 |
| 若失敗 → 修復根因 | ⚠️ 條件執行 |
| 修改業務邏輯 / Migration / Frontend / Tests | ❌ 本計劃不涵蓋（由返工預案引導至修復計劃） |
| 引用舊 Run 冒充成功 | ❌ 禁止 |
| skip / continue-on-error / 移除驗證步驟 | ❌ 禁止 |

### 1.3 已知資訊

- **最新 Commit SHA**：`437581a330444c2bdf361076437d54ff4a846a84`
- **Repository**：`liuxb99/AI-Kill-Cancer`
- **Workflow 檔案**：`.github/workflows/ci.yml`
- **Workflow Jobs**：`backend`（10 steps + postgres service）、`frontend`（5 steps）
- **關鍵驗證點**：
  - `Test with pytest` — 既有測試全部 PASS
  - `Postgres Integration Gate - Alembic upgrade on Postgres` — Migration 020 正確升級
  - `Postgres Integration Gate - Run Tests on Postgres` — Phase 3C 全部測試在真實 Postgres 上 PASS
  - `Postgres Integration Gate - Alembic downgrade & re-upgrade` — 有資料阻擋、空表可降、完整循環
  - `Postgres Integration Gate - Migration verification` — SQLite 上 Migration 測試
  - `Test migration` — 基本 Migration 驗證
  - `Test frontend` — 前端測試全部 PASS
  - `Build frontend` — 前端建置成功

---

## 2. 任務清單（Step-by-Step）

### Step 1 — 查詢最近 20 個 CI Runs

| 項目 | 說明 |
|------|------|
| **動作** | 執行 `gh run list` 取得最近 20 筆 Runs |
| **指令** | `gh run list --repo liuxb99/AI-Kill-Cancer --workflow ci.yml --limit 20 --json databaseId,headSha,status,conclusion,event,createdAt` |
| **負責角色** | executor（devops） |
| **驗證條件** | 成功回傳 Run 列表，包含所有要求的 JSON 欄位 |
| **返工** | 若 `gh` CLI 未安裝或認證失敗 → 安裝 GitHub CLI + `gh auth login`；若 workflow 不存在 → 檢查 `.github/workflows/ci.yml` 是否存在 |

### Step 2 — 匹配目標 Commit

| 項目 | 說明 |
|------|------|
| **動作** | 從 Step 1 結果中找到 `headSha == 437581a330444c2bdf361076437d54ff4a846a84` 的 Run |
| **負責角色** | executor |
| **驗證條件** | 精確匹配（完整 SHA），記錄對應的 `databaseId`、`status`、`conclusion`、`event`、`createdAt` |
| **返工** | **情況 A**：找到匹配 Run → 進入 Step 3 |
| | **情況 B**：無匹配 Run → 檢查 Commit 是否已 Push（`git fetch origin && git log origin/master` 確認 SHA 存在）；若已 Push 但無 Run → 可能 workflow 未觸發，手動觸發 `gh workflow run ci.yml --repo liuxb99/AI-Kill-Cancer --ref master` 後等待執行完成再重試 |
| | **情況 C**：Run 仍在 `in_progress` / `pending` → 等待完成（`gh run watch <RUN_ID> --repo liuxb99/AI-Kill-Cancer`） |

### Step 3 — 檢視 Run 詳細狀態與 Jobs

| 項目 | 說明 |
|------|------|
| **動作** | 執行 `gh run view` 取得 Run 的完整 JSON 狀態 |
| **指令** | `gh run view <RUN_ID> --repo liuxb99/AI-Kill-Cancer --json status,conclusion,headSha,event,jobs` |
| **負責角色** | executor |
| **驗證條件** | 確認 `status == "completed"`；確認 `conclusion`；逐一檢視 `jobs[]` 中每個 job 的 `status` 與 `conclusion` |
| **返工** | 若 job 仍在執行中 → `gh run watch` 等待；若任何 job 為 `failure` 或 `cancelled` → 進入 Step 4 讀取失敗 log |

### Step 4 — 讀取失敗日誌（條件執行）

| 項目 | 說明 |
|------|------|
| **動作** | 若 Step 3 發現任何 Job 失敗，執行此步驟 |
| **指令** | `gh run view <RUN_ID> --repo liuxb99/AI-Kill-Cancer --log-failed` |
| **負責角色** | executor |
| **驗證條件** | 成功提取失敗 Step 的名稱、Traceback、Exception Type & Message、檔案路徑與行號 |
| **返工** | 詳見 §5 返工預案 |

### Step 5 — 確認所有 Step 為 SUCCESS

| 項目 | 說明 |
|------|------|
| **動作** | 基於 Step 3 的 `jobs[*].steps[*]` 列表，逐個確認 `conclusion == "success"` |
| **負責角色** | executor |
| **驗證條件** | 所有 Step 的 `conclusion` 為 `"success"`（或 `"neutral"` 對跳過的步驟，但應確認無意外 skip） |
| **禁止事項** | ❌ 不得接受任何 `failure`、`cancelled`、`skipped`（非預期）的 Step |
| | ❌ 不得引用舊 Run 的結果冒充當前 Commit 的成功 |
| | ❌ 不得以「CI 環境問題」為由繞過驗證 |

### Step 6 — 標記驗收結果

| 項目 | 說明 |
|------|------|
| **動作** | 根據 Step 5 結果決定驗收標記 |
| **成功路徑** | 全部 SUCCESS → `Phase 3C Accepted: YES`、`Ready for Phase 3D: YES` |
| | 輸出最終報告（可直接寫入 `tasks/summary-report-phase3C.md` 或回報給父代理） |
| **失敗路徑** | 有 FAIL → `Phase 3C Accepted: NO`、`Ready for Phase 3D: NO` |
| | 進入 §5 返工預案 |
| **負責角色** | executor |

---

## 3. 依賴關係

```
Step 1 (gh run list)
  │
  ▼
Step 2 (Match SHA)
  │
  ▼
Step 3 (gh run view --json)
  │
  ├── (全部成功) ──→ Step 5 (確認 All SUCCESS) ──→ Step 6 (標記 Accepted: YES)
  │
  └── (有失敗) ──→ Step 4 (讀取失敗 log)
                        │
                        ▼
                   返工預案 §5
```

### 平行化

所有 Step 為**順序依賴**（每一步的輸出是下一步的輸入），無平行化空間。

---

## 4. 負責角色

| 角色 | 核心職責 | 對應步驟 |
|------|----------|----------|
| **executor（devops）** | 執行所有 `gh` 命令、解析 JSON、判斷結果、標記驗收 | Step 1–6 |
| **debugger（invoked on failure）** | 分析 Traceback、定位根因、提出修復方案 | Step 4 → 返工 |

> 由於本任務屬於 CI 驗收，無需業務開發角色。僅在失敗時需要 debugger 介入分析修復。

---

## 5. 返工預案

### 5.1 無對應 Commit 的 Run

| 觸發條件 | Step 2 找不到 `headSha == 437581a330444c2bdf361076437d54ff4a846a84` 的 Run |
|---------|----------------------------------------------------------------------|
| **診斷** | 1. 執行 `git fetch origin && git log origin/master` 確認 Commit 已在遠端 |
| | 2. 檢查 GitHub 上該 Commit 的狀態（是否有黃色圓點表示 CI 進行中） |
| | 3. 執行 `gh run list --repo liuxb99/AI-Kill-Cancer --limit 5` 看最近 Run |
| **處理** | 若 Commit 已 Push 但無 Run → 手動觸發：`gh workflow run ci.yml --repo liuxb99/AI-Kill-Cancer --ref master` |
| | 若 Commit 未 Push → 先 Push，等待 CI 觸發 |
| | 等待完成後回到 Step 1 |

### 5.2 Run 仍在進行中

| 觸發條件 | Step 3 中 `status != "completed"` |
|---------|-----------------------------------|
| **處理** | 使用 `gh run watch <RUN_ID> --repo liuxb99/AI-Kill-Cancer` 等待完成 |
| | 超時（>60 分鐘）→ 檢查 GitHub Actions Queue 狀態，必要時取消重跑 |

### 5.3 特定 Job 失敗 — 根因分析

| Job | 常見失敗原因 | 修復策略 |
|-----|-------------|----------|
| **Lint with ruff** | Phase 3C 程式碼有 lint 錯誤 | 修正 ruff 報錯（import 順序、命名、格式）→ Push → 重新驗證 |
| **Test with pytest** | 既有測試被 Phase 3C 變更破壞 | 檢查失敗測試的 traceback，修正測試或修復回歸 bug → Push → 重新驗證 |
| **Postgres Integration Gate - Alembic upgrade** | Migration 020 升級失敗（FK 衝突、重複 revision） | 檢查 Migration 檔案，修正 upgrade() → Push → 重新驗證 |
| **Postgres Integration Gate - Run Tests on Postgres** | Phase 3C 測試在 Postgres 上失敗（連線問題、FK 約束、型別差異） | 修正測試 fixture 或修復程式碼中的 Postgres 相容性 → Push → 重新驗證 |
| **Postgres Integration Gate - Alembic downgrade & re-upgrade** | 有資料阻擋邏輯錯誤、downgrade 順序錯誤 | 修正 `migrations/versions/020_*.py` 的 downgrade() → Push → 重新驗證 |
| **Postgres Integration Gate - Migration verification** | Migration 測試（SQLite）失敗 | 修正 `tests/test_migration.py` 或 Migration 檔案 → Push → 重新驗證 |
| **Test frontend / Build frontend** | 前端測試失敗或建置錯誤 | 修正前端程式碼或測試 → Push → 重新驗證 |
| **frontend job: Install dependencies** | `npm ci` 失敗（網路、cache、版本衝突） | 檢查 `package-lock.json`，確認 Node 版本兼容 → Push → 重新驗證 |

### 5.4 修復後重新驗證流程

```
修正程式碼 → git add + git commit + git push
       │
       ▼
回到 Step 1（重新查詢 Runs，找到新 Commit 對應的新 Run）
       │
       ▼
Step 2 → Step 3 → Step 5 → Step 6
```

**重要**：每次修復後必須使用**新的 Run** 重新驗證，不得引用舊 Run 的結果。

### 5.5 無法修復的 CI 基礎設施問題

| 情況 | 處理方式 |
|------|----------|
| GitHub Actions Runner 離線 / Queue 阻塞 | 等待後重試，或使用 `workflow_dispatch` 重新觸發 |
| `gh` CLI 無法認證 | `gh auth login` 重新認證 |
| Postgres service container 無法啟動 | 確認 CI YAML 中 service 定義正確（image tag、health check） |
| npm registry 不可達 | 等待基礎設施恢復後重試 |

> **禁止**：不得因基礎設施問題而跳過驗證步驟或標記 Accepted = YES。基礎設施問題應等待修復後重新執行。

### 5.6 禁止事項檢查清單

執行過程中，executor 必須確認以下禁止事項未被違反：

- [ ] ❌ 不得 **skip migration verification**（必須確認 `Alembic upgrade`、`downgrade & re-upgrade`、`Migration verification` 全部執行）
- [ ] ❌ 不得 **移除 downgrade test**（`Alembic downgrade & re-upgrade` 步驟必須存在且 PASS）
- [ ] ❌ 不得 **continue-on-error**（任何 Step 的 `continue-on-error: true` 必須移除）
- [ ] ❌ 不得 **引用舊 Run 冒充成功**（必須使用 `headSha == 437581a...` 的 Run）
- [ ] ❌ 不得以「CI 環境問題 / Runner 問題 / 分鐘額度」為由接受失敗的 Run
- [ ] ❌ 不得在未修復根因的情況下重新觸發 Workflow 期望「碰巧通過」
- [ ] ❌ 不得在失敗後僅修復 CI YAML 而不修復業務程式碼（如果根因在業務程式碼）
- [ ] ❌ 不得修改 `ci.yml` 以跳過或弱化任何驗證步驟

---

## 6. 驗收結論格式

### 成功結論（範例）

```json
{
  "phase": "Phase 3C",
  "commit": "437581a330444c2bdf361076437d54ff4a846a84",
  "run_id": "<RUN_ID>",
  "status": "completed",
  "conclusion": "success",
  "jobs": {
    "backend": "success",
    "frontend": "success"
  },
  "all_steps_success": true,
  "phase_3c_accepted": true,
  "ready_for_phase_3d": true,
  "timestamp": "<ISO-8601>"
}
```

### 失敗結論（範例）

```json
{
  "phase": "Phase 3C",
  "commit": "437581a330444c2bdf361076437d54ff4a846a84",
  "run_id": "<RUN_ID>",
  "status": "completed",
  "conclusion": "failure",
  "failed_job": "<JOB_NAME>",
  "failed_step": "<STEP_NAME>",
  "traceback_summary": "<EXCEPTION_TYPE>: <MESSAGE>",
  "root_cause_file": "<FILE_PATH>:<LINE>",
  "phase_3c_accepted": false,
  "ready_for_phase_3d": false,
  "fix_required": "<修復方向簡述>",
  "timestamp": "<ISO-8601>"
}
```

---

## 7. 參考文件

- [Phase 3C 執行計劃](plan-phase3C.md) — Phase 3C 原始開發計劃
- [Phase 3C Hardening 計劃](plan-phase3c-hardening.md) — 硬化階段計劃
- [Phase 3C 回歸檢查](regression-check-phase3C.md) — 前次回歸檢查報告
- [CI 診斷計劃](plan-ci-diagnostics.md) — CI 診斷參考
- [CI Workflow](https://github.com/liuxb99/AI-Kill-Cancer/blob/master/.github/workflows/ci.yml) — 當前 CI 配置

---

*計劃版本: 1.0*
*建立日期: 2026-07-27*
*負責角色: PLANNER*
