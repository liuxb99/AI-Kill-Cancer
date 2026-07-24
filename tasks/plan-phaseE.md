# Phase E：統一 Vercel Project — 執行計劃

> **文件狀態**：初版（待審核）
> **負責角色**：PLANNER → devops（執行）、reviewer（覆審）
> **建立時間**：2026-07-25
> **產出檔案**：本計劃（tasks/plan-phaseE.md）+ 最終回報（tasks/vercel-phaseE-report.md）

---

## 一、現狀摘要

| 項目 | 狀態 | 說明 |
|------|------|------|
| GitHub Actions CI | ✅ success | Run #34 (30033762944) — frontend test 47 passed, build success |
| GitHub Actions Deploy | ✅ success | Run #57 (30029172018) — Vercel CLI pull/build/deploy 成功 |
| 部署目標 Project | ⚠️ **frontend** | GitHub Actions 目前部署到 `liuxb99-9860s-projects/frontend` |
| Vercel Git Integration | ❌ failure | 自動部署到 `ai-kill-cancer-zqpi` 但失敗 |
| vercel.json | ✅ 配置正確 | rootDirectory: src/frontend, nodeVersion: 22, install: npm ci, build: npm run build, output: dist |
| deploy.yml | ✅ 功能正常 | 使用 VERCEL_TOKEN、VERCEL_ORG_ID、VERCEL_PROJECT_ID |
| 誤建 frontend project | ⚠️ 待清理 | 由 GitHub Actions 部署建立/使用 |

### 核心問題

GitHub Actions 和 Vercel GitHub Integration 是兩條獨立部署路徑，分別部署到兩個不同的 Vercel Project。GitHub Actions 部署到 `frontend` project（成功），而 Vercel GitHub Integration 部署到 `ai-kill-cancer-zqpi` project（失敗）。目標是統一成一條路徑：**GitHub Actions → ai-kill-cancer-zqpi**。

---

## 二、任務清單（含 ID、描述、依賴、負責角色、返工預案）

### Phase E1：讀取兩個 Project 的非敏感資訊

| ID | 任務 | 描述 | 依賴 | 負責 | 驗證方式 | 返工預案 |
|----|------|------|------|------|---------|----------|
| E1.1 | **查詢 frontend project 資訊** | 使用 `vercel project ls` 列出所有 project，再用 `vercel project inspect frontend` 取得詳細資訊。記錄 project name、ID（可遮蔽）、team、linked Git repo、root directory、framework、build command、output directory、production domains、created time、last deployment。**不得輸出 Token 或完整環境變數。** | 無 | devops | 回報非敏感資訊結構化摘要 | 若 `vercel` CLI 未安裝 → `npm install -g vercel@latest`；若未認證 → `vercel login` 或使用 VERCEL_TOKEN 環境變數 |
| E1.2 | **查詢 ai-kill-cancer-zqpi project 資訊** | 同上，使用 `vercel project inspect ai-kill-cancer-zqpi`。記錄相同欄位。 | 無 | devops | 回報非敏感資訊結構化摘要 | 同上 |
| E1.3 | **比對兩個 project 配置差異** | 比對 E1.1 與 E1.2 的配置，重點關注 root directory、framework、build command、output directory、linked Git repo 的差異。 | E1.1, E1.2 | devops | 輸出比對表格 | 若任一 project 無法查詢，記錄已取得資訊繼續 |

### Phase E2：將 ai-kill-cancer-zqpi 修正為正式前端 Project

| ID | 任務 | 描述 | 依賴 | 負責 | 驗證方式 | 返工預案 |
|----|------|------|------|------|---------|----------|
| E2.1 | **更新 ai-kill-cancer-zqpi 的 Project 設定** | 使用 `vercel project update ai-kill-cancer-zqpi` 設定：Root Directory = `src/frontend`、Framework = `Vite`、Install Command = `npm ci`、Build Command = `npm run build`、Output Directory = `dist`、Node.js 版本 = `22`。若 CLI 不支援直接 update，則修改 Vercel Dashboard 設定或透過 `vercel.json` 關聯。 | E1.2 | devops | 回報設定前後對照（隱藏敏感值） | CLI 無 update 命令 → 使用 `vercel link` 在本地建立專案關聯後 push，或透過 Vercel REST API |
| E2.2 | **確認 Git repository 連結正確** | 確認 project linked Git repository = `liuxb99/AI-Kill-Cancer`，production branch = `master`。若不正確，透過 Vercel CLI 或 Dashboard 修正。 | E2.1 | devops | 回報 linked repo 與 branch | 若無權限修改 Git 連結 → 回報 BLOCKED，轉由用戶手動操作 |
| E2.3 | **核對 vercel.json 與 Project 設定一致** | 確保 `vercel.json` 中的設定與 E2.1 的 Project 設定一致，避免衝突。 | E2.1 | devops | 比對表格 | 若不一致，以 `vercel.json` 為準（Vercel 以 vercel.json 優先） |

### Phase E3：修正 GitHub Actions 使用的 Project ID

| ID | 任務 | 描述 | 依賴 | 負責 | 驗證方式 | 返工預案 |
|----|------|------|------|------|---------|----------|
| E3.1 | **確認目前 VERCEL_PROJECT_ID 指向哪個 Project** | 透過 `vercel project inspect` 或比對 Actions log 中的 project ID，確認 `VERCEL_PROJECT_ID` 目前指向 `frontend` 還是 `ai-kill-cancer-zqpi`。**不得在 log 或原始碼輸出 secret 值。** | E1.1, E1.2 | devops | 確定 Project ID 對應關係 | 若無法從 CLI 取得，從已成功的 Actions deploy log 推斷 |
| E3.2 | **更新 GitHub Secrets 中的 VERCEL_PROJECT_ID** | 若 E3.1 確認指向 `frontend`，則需要更新為 `ai-kill-cancer-zqpi` 的 Project ID。透過 GitHub API 更新 repository secret。若無 GitHub API token 權限，則引導用戶手動更新。**不得輸出 secret 值。** | E3.1 | devops | 確認 secret 已更新（透過比對更新前後 hash 或 API response） | 無 API 權限 → 回報 BLOCKED，提供用戶手動操作步驟 |
| E3.3 | **驗證 Secret 更新生效** | 觸發一個 dry-run 測試或檢查 Actions 是否能正確讀取 secret（不輸出值）。可以透過新增一個測試 workflow 來驗證 secret 存在（不輸出值）。 | E3.2 | devops | 回報 secret 驗證結果 | 若無法直接驗證，透過後續 E4 實際部署驗證 |

### Phase E4：執行正式部署驗證

| ID | 任務 | 描述 | 依賴 | 負責 | 驗證方式 | 返工預案 |
|----|------|------|------|------|---------|----------|
| E4.1 | **推送變更並觸發 CI/CD** | 修改完成後正常 `git push`（**不得**使用 `--no-verify`）。確認觸發 CI workflow。 | E2.3, E3.3 | devops | 回報 push 的 commit SHA | push 失敗 → 檢查 remote 連線與權限 |
| E4.2 | **監看 CI 結果** | 確認 CI run 的 conclusion = success。若失敗，分析錯誤原因並修復。 | E4.1 | devops | 回報 CI run ID 與 conclusion | CI 失敗 → 分析 log，回報根因並修復後重新推送 |
| E4.3 | **監看 Deploy 結果** | 確認 Deploy workflow 被觸發（CI success 後）且 conclusion = success。確認 deployment 的 project = `ai-kill-cancer-zqpi`、environment = `production`。 | E4.2 | devops | 回報 Deploy run ID、conclusion、deployed project name | Deploy 未觸發 → 檢查 workflow_run 條件；Deploy 失敗 → 分析 Vercel CLI log |
| E4.4 | **擷取 production URL** | 從 Deploy log 或 Vercel CLI 輸出中取得 production deployment URL。若 log 未公開，從 Vercel Dashboard 取得。 | E4.3 | devops | 回報 production URL（完整公開） | 若 URL 無法取得 → 回報 BLOCKED，需手動查詢 Dashboard |
| E4.5 | **curl 驗證 production URL** | 執行：`curl -sI https://<production-url>` 確認 HTTP 200/合理 redirect；`curl -s https://<production-url> | head -c 500` 確認 Content-Type HTML、非 404/error page；curl 主要 JS/CSS asset 確認可讀取。 | E4.4 | devops | 回報 HTTP 狀態碼、Content-Type、body 前綴、asset 可讀性 | HTTP 非 200 → 分析回應（redirect/404/500），回報錯誤類型 |

### Phase E5：停用重複的 Vercel Git Integration

| ID | 任務 | 描述 | 依賴 | 負責 | 驗證方式 | 返工預案 |
|----|------|------|------|------|---------|----------|
| E5.1 | **確認 GitHub Actions 部署成功** | 雙重確認 E4.3 中 Deploy 已成功部署到 `ai-kill-cancer-zqpi` 的 production environment。 | E4.3 | devops | 回報確認結果 | 部署未成功 → 先修復再繼續，不得跳過 |
| E5.2 | **停用 Vercel Git Integration 的 Auto Deploy** | 透過 Vercel CLI 或 API 停用 Git Integration 的自動部署。若 CLI 不支援，引導用戶在 Vercel Dashboard → Project → Settings → Git 中停用 "Auto Deploy"。**注意：不得移除整個帳號上的 Vercel GitHub App。** | E5.1 | devops | 回報停用操作結果 | CLI 無此功能 → 回報 MANUAL STEP REQUIRED，提供詳細操作步驟 |
| E5.3 | **驗證 Integration 已停用** | 確認 Vercel project 的 Git Integration 狀態為 disabled 或 auto deploy = off。可透過 Vercel API 查詢 project 的 git 設定。 | E5.2 | devops | 回報 Integration 最終狀態 | 若無法直接查詢 → 透過後續新 commit 是否觸發 Vercel 自動部署來間接驗證 |

### Phase E6：處理誤建的 frontend project

| ID | 任務 | 描述 | 依賴 | 負責 | 驗證方式 | 返工預案 |
|----|------|------|------|------|---------|----------|
| E6.1 | **記錄 frontend project 的關鍵資訊** | 記錄 E1.1 中取得的 frontend project ID（可遮蔽）、domain、最後 deployment 時間與狀態。 | E1.1 | devops | 回報記錄摘要 | 資訊已取得 → 直接使用 |
| E6.2 | **確認正式 project 驗證通過** | 確認 E4.5 的 production URL 驗證通過，且 Project 是 `ai-kill-cancer-zqpi`。確保 canonical project 運作正常後再清理。 | E4.5 | devops | 回報確認結果 | 驗證未通過 → 先修復，不可刪除 frontend |
| E6.3 | **刪除 frontend project** | 使用 `vercel project rm frontend` 或 Vercel Dashboard 刪除誤建的 project。需確認不影響正在運作的 production 服務。 | E6.2, E5.3 | devops | 回報刪除結果（含 project ID 遮蔽） | 無刪除權限 → 回報 MANUAL CLEANUP REQUIRED，提供 Vercel Dashboard 操作步驟 |
| E6.4 | **驗證 frontend project 已移除** | 確認 `vercel project ls` 不再列出 frontend，且 production URL 仍正常運作。 | E6.3 | devops | 回報驗證結果 | 若無法刪除 → 記錄狀態，標記 MANUAL CLEANUP REQUIRED |

---

## 三、任務依賴關係圖

```
E1.1 ─┐         可並行
E1.2 ─┤
      │
      ▼
E1.3 ── 依賴 E1.1, E1.2
      │
      ▼
E2.1 ── 依賴 E1.2
E2.2 ── 依賴 E2.1
E2.3 ── 依賴 E2.1
      │
      ▼
E3.1 ── 依賴 E1.1, E1.2
E3.2 ── 依賴 E3.1
E3.3 ── 依賴 E3.2
      │
      ▼
E4.1 ── 依賴 E2.3, E3.3
E4.2 ── 依賴 E4.1
E4.3 ── 依賴 E4.2
E4.4 ── 依賴 E4.3
E4.5 ── 依賴 E4.4
      │
      ├─────────────────┐
      ▼                  ▼
E5.1 ── 依賴 E4.3      E6.1 ── 依賴 E1.1（可提前執行）
E5.2 ── 依賴 E5.1      E6.2 ── 依賴 E4.5
E5.3 ── 依賴 E5.2      E6.3 ── 依賴 E6.2, E5.3
                        E6.4 ── 依賴 E6.3
```

### 關鍵路徑

```
E1.1 → E1.3 → E2.1 → E2.3 → E4.1 → E4.2 → E4.3 → E4.4 → E4.5 → E5.1 → E5.2 → E5.3
                                                                  → E6.2 → E6.3 → E6.4
```

**估計最短執行輪次**：6-8 輪（含等待 CI/CD 執行時間）

---

## 四、各階段負責角色

| Phase | 主要執行 | 輔助/審核 | 說明 |
|-------|---------|-----------|------|
| E1（讀取資訊） | devops | — | Vercel CLI 查詢，結構化回報 |
| E2（修正 Project） | devops | — | Project 設定修改 |
| E3（修正 Project ID） | devops | — | GitHub Secrets 更新 |
| E4（部署驗證） | devops | reviewer（覆審） | Push → CI → Deploy → curl 驗證 |
| E5（停用 Integration） | devops | 用戶（Dashboard 操作） | 可能需要手動操作 |
| E6（清理 frontend） | devops | 用戶（確認） | 確認後刪除或標記待辦 |

---

## 五、返工預案

### 常見障礙與對應措施

| 情境 | 觸發條件 | 措施 |
|------|---------|------|
| Vercel CLI 未安裝 | `vercel` 命令不存在 | `npm install -g vercel@latest` |
| Vercel CLI 未認證 | 回傳 Not authenticated | 設定 `VERCEL_TOKEN` 環境變數：`export VERCEL_TOKEN=<token>` 或 `vercel login` |
| GitHub API rate limit | API 回傳 403/429 | 使用已認證請求（含 Token），每秒限速 1 請求 |
| 無 Project 修改權限 | CLI 回傳 permission denied | 回報 BLOCKED，引導用戶在 Vercel Dashboard 手動操作 |
| 無 GitHub Secrets 更新權限 | API 回傳 403/404 | 回報 BLOCKED，提供用戶手動更新步驟 |
| CI 因變更失敗 | CI conclusion = failure | 分析 Actions log，修復後重新推送 |
| Deploy 失敗 | Deploy conclusion = failure | 分析 Vercel CLI log，確認 Project ID / Token 正確性 |
| Production URL 無法訪問 | curl 非 200 | 確認 deployment 狀態，檢查 Build 是否成功 |
| Vercel Integration 無法停用 | CLI/Dashboard 無選項 | 回報 MANUAL STEP REQUIRED，提供替代方案 |
| frontend 刪除失敗 | CLI 無權限 | 標記 MANUAL CLEANUP REQUIRED |

### 回滾方案

| 情境 | 措施 |
|------|------|
| 新部署導致 production 異常 | 1. 還原 GitHub Secrets 中的 VERCEL_PROJECT_ID 回原值 2. 還原 commit 前一版本 3. 通知用戶 |
| Integration 停用後需要重新啟用 | 在 Vercel Dashboard → Project → Settings → Git 重新啟用 Git Integration |
| frontend project 誤刪 | 透過 Vercel Dashboard 或支援回復（Vercel 可能保留一段時間） |

---

## 六、注意事項

### Token/Secret 處理原則（嚴格遵守）

1. **絕不輸出 Token 值**：在任何 log、回報、檔案中皆不得輸出 `VERCEL_TOKEN`、`VERCEL_ORG_ID`、`VERCEL_PROJECT_ID` 的實際值
2. **Project ID 可部分遮蔽**：如 `prj_XXXX...XXXX` 顯示前 4 尾 4，中間遮蔽
3. **環境變數優先**：使用 `$VERCEL_TOKEN` 環境變數而非命令列直接傳入
4. **GitHub Secrets 操作**：使用 GitHub API 更新 secret 時，僅回報操作成功/失敗，不輸出值
5. **日誌清理**：若工具意外輸出 secret 值，立即標記並要求清除

### Dashboard 手動操作的安全指引

若需要用戶在 Vercel Dashboard 手動操作：
1. 提供精確的操作路徑（如：Vercel Dashboard → Project → Settings → Git）
2. 說明每一步的目的
3. 提醒不要誤觸其他設定
4. 操作完成後通知 devops 驗證

### 執行順序建議

1. **E1.1 與 E1.2 可完全並行**，同時查詢兩個 project
2. **E6.1 可在 E1.1 完成後提前執行**（記錄 frontend 資訊），不必等到 E4
3. **E4.1 推送前務必確認所有變更已完成**（E2 + E3），避免多次 push 造成混淆
4. **E5 與 E6 在 E4.5 驗證通過後可部分並行**（E5.1 依賴 E4.3，E6.2 依賴 E4.5）

### 最終驗收條件（8 項）

1. ✅ 唯一正式 Project = `ai-kill-cancer-zqpi`
2. ✅ GitHub Actions 部署到該 Project
3. ✅ CI success
4. ✅ Deploy workflow success
5. ✅ Production URL 可正常開啟（HTTP 200, HTML content）
6. ✅ Vercel Git Integration 不再重複部署
7. ✅ 新 commit 不再出現 Vercel failure
8. ✅ `frontend` 誤建 Project 已清理或列為人工待辦

---

## 七、完成證據清單（20 項）

| # | 證據項 | 對應任務 | 說明 |
|---|--------|---------|------|
| 1 | canonical Vercel project name | E1.2 | `ai-kill-cancer-zqpi` |
| 2 | canonical project ID（可部分遮蔽） | E1.2 | 如 `prj_XXXX...XXXX` |
| 3 | 原 frontend project ID（可部分遮蔽） | E1.1 | 如 `prj_XXXX...XXXX` |
| 4 | GitHub Actions 原先部署錯誤 Project 的原因 | E3.1 | 分析 `VERCEL_PROJECT_ID` 指向 |
| 5 | VERCEL_PROJECT_ID 是否已修正 | E3.2, E3.3 | 是/否 |
| 6 | Project root directory | E2.1 | `src/frontend` |
| 7 | Framework | E2.1 | Vite |
| 8 | Build command | E2.1 | `npm run build` |
| 9 | Output directory | E2.1 | `dist` |
| 10 | 新 commit SHA | E4.1 | 推送的 commit hash |
| 11 | CI run ID 與 conclusion | E4.2 | 如 #XX → success |
| 12 | Deploy run ID 與 conclusion | E4.3 | 如 #XX → success |
| 13 | Deploy workflow 的 head SHA | E4.3 | 部署的 commit hash |
| 14 | 實際部署 project name | E4.3 | `ai-kill-cancer-zqpi` |
| 15 | Production URL | E4.4 | `https://...` |
| 16 | Production URL HTTP 驗證結果 | E4.5 | HTTP 200 / HTML / asset ok |
| 17 | Vercel Git Integration 最終狀態 | E5.2, E5.3 | disabled / manual step required |
| 18 | 新 commit 的 Vercel commit status | E5.3 | success / removed / pending |
| 19 | frontend 誤建 project 的處理結果 | E6.3, E6.4 | deleted / manual cleanup required |
| 20 | 尚未完成或 BLOCKED 項目 | 全部 | 如實記錄 |

---

## 八、執行順序時間線

```
Round 1 (Phase E1):
  E1.1 ──── 查詢 frontend project ──── 10 min
  E1.2 ──── 查詢 ai-kill-cancer-zqpi ── 10 min （可並行）

Round 2 (Phase E1 + E2):
  E1.3 ──── 比對配置差異 ──── 5 min
  E2.1 ──── 更新 ai-kill-cancer-zqpi 設定 ── 10 min
  E2.2 ──── 確認 Git repository 連結 ── 5 min
  E2.3 ──── 核對 vercel.json ── 5 min
  E6.1 ──── 記錄 frontend 資訊（可提前）── 5 min

Round 3 (Phase E3):
  E3.1 ──── 確認 Project ID 指向 ── 5 min
  E3.2 ──── 更新 GitHub Secret ── 10 min
  E3.3 ──── 驗證 Secret 更新 ── 5 min

Round 4 (Phase E4):
  E4.1 ──── git push ──── 5 min
  E4.2 ──── 監看 CI（等待 ~10 min）── 15 min
  E4.3 ──── 監看 Deploy（等待 ~5 min）── 10 min
  E4.4 ──── 擷取 production URL ── 5 min
  E4.5 ──── curl 驗證 ── 5 min

Round 5 (Phase E5 + E6):
  E5.1 ──── 確認部署成功 ── 2 min
  E5.2 ──── 停用 Git Integration ── 10 min
  E5.3 ──── 驗證 Integration 已停用 ── 5 min
  E6.2 ──── 確認正式 project 驗證通過 ── 2 min
  E6.3 ──── 刪除 frontend project ── 5 min
  E6.4 ──── 驗證移除 ── 5 min

Round 6:
  最終回報彙整 ──── 15 min
  REVIEWER 審核
```

**估計總時間**：約 2-3 小時（含等待 CI/CD 執行時間）

---

## 九、審核與簽收

- [ ] PLANNER 產出計劃（本文件）
- [ ] devops 完成 Phase E1（E1.1–E1.3）調查
- [ ] devops 完成 Phase E2（E2.1–E2.3）Project 修正
- [ ] devops 完成 Phase E3（E3.1–E3.3）Project ID 修正
- [ ] devops 完成 Phase E4（E4.1–E4.5）部署驗證
- [ ] devops 完成 Phase E5（E5.1–E5.3）Integration 停用
- [ ] devops 完成 Phase E6（E6.1–E6.4）清理 frontend
- [ ] reviewer 覆審 20 項證據完整性
- [ ] 最終報告輸出至 `tasks/vercel-phaseE-report.md`

---

> **版本**: 1.0
> **建立者**: PLANNER
> **下一階段**: devops 開始 Phase E1 調查（讀取兩個 Vercel Project 資訊）
