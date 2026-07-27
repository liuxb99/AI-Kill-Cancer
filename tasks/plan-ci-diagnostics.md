# CI 診斷計劃 — ci-diagnostics

> **任務 ID**：ci-diagnostics  
> **場景**：devops（CI/CD 診斷）  
> **目標**：對 Phase 3C 的 CI GitHub Actions Workflow 進行診斷，不修改任何業務程式碼  
> **範圍限制**：只允許修改 `.github/workflows/ci.yml`，不得修改 Engine / Service / Repository / Migration 020 / Frontend / Tests / AGENTS.md

---

## Batch A：YAML 驗證

### A1 ─ 讀取並驗證 `.github/workflows/ci.yml` 的 YAML 語法
- [ ] 使用 `yaml.parse` 或系統 YAML parser 載入該檔案
- [ ] 若 parser 報錯，記錄錯誤位置與內容
- [ ] 若 YAML 語法無效，進入 Batch D 修復

### A2 ─ 檢查 trigger 配置
- [ ] 確認 `on` 區塊存在至少：
  ```yaml
  on:
    push:
      branches:
        - master
    workflow_dispatch:
  ```
- [ ] 不得僅有 `pull_request` 觸發器，因為目前直接 push 到 master
- [ ] 記錄遺漏的 trigger 項目

### A3 ─ 檢查 job 定義與基本結構
- [ ] 檢查 `jobs` 區塊是否存在
- [ ] 檢查每個 job 的 `runs-on`、`steps` 是否齊全
- [ ] 檢查 `permissions` 設定（特別是 id-token / contents 權限）
- [ ] 檢查 `working-directory` 是否正確指向子模組路徑（如有）

---

## Batch B：GitHub CLI 診斷

### B1 ─ 確認 workflow 是否被 GitHub 識別為 active
- [ ] 執行：
  ```bash
  gh workflow list --repo liuxb99/AI-Kill-Cancer
  ```
- [ ] 確認 `ci.yml` 出現且狀態為 `active`
- [ ] 若未出現或狀態為 `disabled`，記錄並進入 Batch D

### B2 ─ 取得 workflow 詳細資訊
- [ ] 執行：
  ```bash
  gh workflow view ci.yml --repo liuxb99/AI-Kill-Cancer
  ```
- [ ] 記錄 workflow ID、name、state、path

### B3 ─ 查詢最近 20 個 Runs
- [ ] 執行：
  ```bash
  gh run list \
    --repo liuxb99/AI-Kill-Cancer \
    --workflow ci.yml \
    --limit 20
  ```
- [ ] 記錄每個 Run 的 ID、headSha、event、status、conclusion、createdAt

### B4 ─ 確認 Commit `1cef5996` 是否存在對應 Run
- [ ] 在 B3 結果中搜尋 `headSha == 1cef5996`（或前綴匹配）
- [ ] 若有對應 Run → 記錄 Run ID，進入 Batch C 讀取細節
- [ ] 若無對應 Run → 代表 workflow 未因該 Commit 觸發，記錄為「無觸發」

---

## Batch C：手動觸發與結果讀取

### C1 ─ 手動觸發 workflow（如已配置 `workflow_dispatch`）
- [ ] 執行：
  ```bash
  gh workflow run ci.yml \
    --repo liuxb99/AI-Kill-Cancer \
    --ref master
  ```
- [ ] 確認觸發成功（exit code 0）

### C2 ─ 取得新 Run ID
- [ ] 執行：
  ```bash
  gh run list \
    --repo liuxb99/AI-Kill-Cancer \
    --workflow ci.yml \
    --limit 5
  ```
- [ ] 從結果中擷取最新一個 Run 的 ID

### C3 ─ 讀取 Run 的 Jobs 詳細結果
- [ ] 執行：
  ```bash
  gh run view <RUN_ID> \
    --repo liuxb99/AI-Kill-Cancer \
    --json status,conclusion,headSha,event,jobs
  ```
- [ ] 記錄每個 job 的名稱、狀態、結論

### C4 ─ 讀取失敗日誌
- [ ] 若有任何 job 失敗，執行：
  ```bash
  gh run view <RUN_ID> \
    --repo liuxb99/AI-Kill-Cancer \
    --log-failed
  ```
- [ ] 從日誌中提取：
  - Failing Step
  - First Traceback
  - File & Line number
  - Exception type & message
- [ ] 若無失敗日誌，記錄「all jobs passed」

---

## Batch D：修復與驗證

### D1 ─ 修正 YAML 問題（如適用）
- [ ] 僅修改 `.github/workflows/ci.yml`
- [ ] 可修正範圍：
  - push trigger（確保 branches: - master）
  - workflow_dispatch
  - YAML syntax errors
  - job dependency
  - permissions
  - working-directory
  - dependency install
- [ ] 不可修正：
  - Engine / Service / Repository / Migration 020 / Frontend / Tests / AGENTS.md

### D2 ─ Git Commit & Push
- [ ] Commit message 格式：
  ```
  fix(ci): restore phase3c postgres workflow trigger
  ```
- [ ] 確認只包含 `.github/workflows/ci.yml` 的變更

### D3 ─ 確認新 Run 全部通過
- [ ] 等待 workflow 執行完畢（或使用 `gh run watch`）
- [ ] 重新執行 B3 + C3 確認所有 jobs 狀態為 `success`（或 `neutral`）

### D4 ─ 產出最終診斷報告
- [ ] 彙整以下資訊：

| 項目 | 值 |
|---|---|
| Workflow File | `.github/workflows/ci.yml` |
| Workflow Active | YES / NO |
| Push Trigger | YES / NO |
| Workflow Dispatch | YES / NO |
| Correct Run ID | |
| Head SHA | |
| Event | |
| Jobs Count | |
| Backend Job | pass / fail |
| Frontend Job | pass / fail |
| Postgres Job | pass / fail |
| Postgres Service | pass / fail |
| Migration 020 Upgrade | pass / fail |
| Tumor Board Tests | pass / fail |
| Restart Recovery | pass / fail |
| Digital Thread | pass / fail |
| Empty DB Downgrade | pass / fail |
| Re-upgrade | pass / fail |
| Failing Step | |
| Root Cause | |
| Fix Commit | |
| Final Run ID | |
| Final Run Conclusion | success / failure |
| Phase 3C Accepted | YES / NO |
| Ready for Phase 3D | YES / NO |

- [ ] **判定標準**：只有找到真正的 CI Run，且 Postgres job 全綠，才允許 `Phase 3C Accepted: YES`

---

## 注意事項

1. **不得自行推測 Run ID** — 必須透過 `gh run list` 取得真實 ID
2. **不得聲稱「Postgres CI 因 runner、分鐘額度或 GitHub 基礎設施問題失敗」** — 無證據支持
3. **Vercel failure 不屬於本輪範圍** — 除非是 GitHub branch protection 的必要檢查，即使如此也應分開回報
4. **若 Postgres tests 真失敗** — 只修 traceback 指向的根因，不得 skip / xfail / 排除測試 / 改成 SQLite / 移除 Restart Recovery / 移除 Migration Gate
5. **所有 `gh` 指令均需加上 `--repo liuxb99/AI-Kill-Cancer`** 以確保指向正確倉庫
