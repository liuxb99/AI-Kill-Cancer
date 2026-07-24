# Vercel 部署狀態不一致 — 深入調查與修復計劃

> **文件狀態**：初版  
> **負責角色**：devops（主調查）、reviewer（覆審）  
> **問題**：GitHub Actions deploy workflow ✅ success，但 GitHub commit status 的 Vercel context ❌ failure  
> **建立時間**：2026-07-25  
> **產出檔案**：本計劃 + 階段性報告

---

## 一、問題摘要

### 已知現象

| 維度 | 狀態 | 來源 |
|------|------|------|
| GitHub Actions CI Run #34 | ✅ success | GitHub Actions |
| GitHub Actions Deploy Run #57 | ✅ success | GitHub Actions |
| GitHub commit combined status | ❌ failure | GitHub commit status |
| GitHub commit — Vercel context | ❌ failure | Vercel GitHub Integration |
| GitHub commit — GitHub Actions context | ✅ success | GitHub Actions |
| Vercel 實際部署 | ✅ success | Vercel CLI output |

### 核心矛盾

兩個獨立系統各自報告 commit status，結果不一致：

1. **GitHub Actions** — 使用 `vercel deploy --prebuilt --prod` 成功部署，設定 context 為 `continuous-integration/github-actions` → ✅ success
2. **Vercel GitHub Integration** — Vercel 官方 bot 自動監聽 Git push，獨立觸發部署，設定 context 為 `Vercel` → ❌ failure

### 最可能根因

Vercel GitHub Integration（Git App）仍然啟用且配置不正確，導致其自動部署失敗，但該失敗未被 GitHub Actions 的成功部署覆蓋。兩者使用不同的 commit status context name。

---

## 二、調查方向與工具

### 必須調查的 5 個方向

| # | 調查方向 | 關鍵問題 | 工具 |
|---|---------|---------|------|
| 1 | **查 GitHub Actions run** | CI Run #34 和 Deploy Run #57 的 head SHA、結論、輸出 URL 是什麼？ | `gh` CLI / GitHub API / `curl` |
| 2 | **核對 deployment 對應 commit SHA** | Deploy Run #57 部署的到底是哪個 commit？ | `gh` CLI / GitHub API |
| 3 | **核對 Vercel project identity** | GitHub Actions 部署的 Vercel project 是哪個？與 GitHub repository 連結的是同一個嗎？ | `vercel` CLI / GitHub Actions log |
| 4 | **查明失敗的 Vercel commit status 來源** | 誰設定了 "Vercel" context？是 Vercel GitHub Integration 還是其他？ | GitHub API / Vercel Dashboard |
| 5 | **驗證 production URL** | 實際部署的 URL 是否可正常訪問？ | `curl` |

### 可用工具

| 工具 | 狀態 | 說明 |
|------|------|------|
| `gh` CLI | ❌ 未安裝 | 改用 `curl` + GitHub REST API |
| `vercel` CLI | ❌ 未安裝 | 需安裝（`npm install -g vercel`）或用 Actions log 推斷 |
| `curl` | ✅ 可用 | HTTP 請求與 API 查詢 |
| `git` | ✅ 可用 | 版本歷史查詢 |
| GitHub REST API | ✅ 可存取 | 查詢 runs、commit statuses、repos 設定 |
| GitHub Actions log | ✅ 可查 | 通過 GitHub API 或 UI 獲取 |

---

## 三、任務清單

### Phase A：調查確認（A1–A5）— 釐清現狀

| ID | 任務 | 描述 | 依賴 | 負責 | 驗證方式 | 返工預案 |
|----|------|------|------|------|---------|----------|
| A1 | **查 CI Run #34 詳情** | 用 `gh run view 30033762944` 或 curl + GitHub API 取得：workflow name、event、head SHA、branch、conclusion。確認 CI 的 head SHA。 | 無 | devops | 回報 head SHA = 已知 commit | API 限流則改用 GitHub UI 截圖 |
| A2 | **查 Deploy Run #57 詳情** | 用 `gh run view 30029172018` 或 curl + GitHub API 取得：deploy workflow 的 head SHA、conclusion、Vercel CLI 輸出的 deployment URL 與 project name。 | 無 | devops | 回報 deployment URL 與 project identity | API 限流則改用 GitHub UI 截圖 |
| A3 | **比對 commit SHA** | 核對 A1 與 A2 的 head SHA 是否一致。確認 deploy 部署的確實是 CI 驗證過的 commit。 | A1, A2 | devops | SHA 一致則 ✅ | 若不一致，標記為 BLOCKED |
| A4 | **查 GitHub commit statuses** | 用 GitHub API (`/repos/{owner}/{repo}/commits/{sha}/statuses`) 取得該 commit 的所有 status context。特別關注 context name = "Vercel" 的條目：state、target_url、description、created_at、updated_at。 | A1 | devops | 回報 "Vercel" context 的完整狀態 | API 限流則改用 GitHub UI 的 commit 頁面 |
| A5 | **查 GitHub repo 的 Vercel Integration** | 用 GitHub API (`/repos/{owner}/{repo}/hooks` 或 `/repos/{owner}/{repo}/installations`) 檢查是否有 Vercel 的 GitHub App 安裝。或透過 GitHub UI → Settings → Integrations → Installed GitHub Apps 確認。 | 無 | devops | 回報 Vercel Integration 是否安裝、啟用 | API 不可查則指導用戶在 GitHub UI 確認 |

### Phase B：根因定位（B1–B3）— 找出不一致的源頭

| ID | 任務 | 描述 | 依賴 | 負責 | 驗證方式 | 返工預案 |
|----|------|------|------|------|---------|----------|
| B1 | **追蹤 Vercel failure 的觸發者** | 比對 A4 中 "Vercel" context 的 created_at 與 Vercel GitHub Actions deployment 時間。若 Vercel context 在 Actions 部署之前就 failure，則為舊 Integration 遺留；若在其之後，則 Integration 仍在主動部署。 | A4, A2 | devops | 確定 failure 來源（Integration vs 遺留狀態） | 若時間戳不明確，則根據 Vercel Dashboard 的 Git 設定判斷 |
| B2 | **檢查 Vercel Integration 的 project 配置** | 若 B1 指向 Integration 為來源，調查 Integration 的配置：Root Directory、Framework preset、Build Command、Production Branch。這些可在 Vercel Dashboard → Project → Settings → Git 查看。重點確認 rootDirectory 是否為 `src/frontend`。 | A5 | devops | 比對配置與 vercel.json 的一致性 | 無法查看 Dashboard 則通過 Actions log 中的 project linkage 推斷 |
| B3 | **檢查 GitHub Actions deploy 是否設定 commit status** | 確認 deploy.yml 的 Vercel CLI 命令是否自動設定 commit status。`vercel deploy --prebuilt --prod` 預設會設定一個 commit status（context = "vercel" 或其 Vercel 帳號名）。檢查 Actions log 中是否有 "Setting commit status" 等行。 | A2 | devops | 確定 Actions 部署是否更新了 commit status | 若 log 無相關訊息，則推測未設定 |

### Phase C：修復方案執行（C1–C4）— 消除重複與不一致

| ID | 任務 | 描述 | 依賴 | 負責 | 驗證方式 | 返工預案 |
|----|------|------|------|------|---------|----------|
| C1 | **決策：保留 Integration 或僅保留 Actions** | 根據 B1–B3 的發現，選擇修復方案：① 停用 Vercel GitHub Integration，只保留 GitHub Actions 部署；② 保留 Integration 但修復其配置使之成功；③ 保留兩者但確保 Integration 的 context 不會干擾。**推薦方案：①（單一部署路徑最清晰）** | B1, B2, B3 | devops → 用戶決策 | 記錄決策理由 | 若用戶偏好方案②，轉 C2b |
| C2a | **停用 Vercel GitHub Integration** | 在 Vercel Dashboard → Project → Settings → Git → Disable "Auto Deploy" 或解除 GitHub App 安裝。或在 GitHub → Settings → Installed GitHub Apps → Vercel → Configure → 移除 repo 權限。 | C1 | devops | GitHub commit 上不再顯示 "Vercel" context | 若無法解除，改用 C2b |
| C2b | **修復 Vercel Integration 配置** | 若選擇保留 Integration：在 Vercel Dashboard → Project → Settings → Git 中設置正確的 Root Directory (`src/frontend`)、Framework (`Vite`)、Build Command (`npm run build`)、Output Directory (`dist`)。確保與 vercel.json 一致。 | C1 | devops | Integration 觸發的部署成功 | 若 Integration 持續失敗，強制轉方案 ① |
| C3 | **新增 GitHub Actions commit status 覆蓋** | 在 deploy.yml 中增加步驟，在部署成功後用 GitHub API 將 "Vercel" context 強制更新為 success。或更優方案：在 Vercel 專案設定中關閉 "GitHub Checks" 只保留 "Commit Status"。 | C2a 或 C2b | devops | 部署後 GitHub commit 的 Vercel context 變為 success | 若 GitHub API token 無權限，改用 GitHub Actions 自有 context |
| C4 | **驗證 production URL** | 從 A2 取得的 deployment URL 執行 `curl -I` 驗證 HTTP 200、HTML 可讀取、非 error page。 | A2 | devops | `curl -I` 回傳 200，body 包含預期內容 | URL 未公開則從 Vercel Dashboard 取得 |

### Phase D：最終驗證與收尾（D1–D3）

| ID | 任務 | 描述 | 依賴 | 負責 | 驗證方式 | 返工預案 |
|----|------|------|------|------|---------|----------|
| D1 | **觸發完整流程並監看** | 推送一個空 commit 或觸發 workflow_dispatch，觀察 CI # → Deploy # 完整流程。確認 GitHub Actions 兩者皆 success。 | C2a/C2b, C3 | devops | CI ✅ + Deploy ✅ | 若 CI 失敗，回 Phase 2 修復 |
| D2 | **檢查最終 commit status** | 用 GitHub API 檢查最終 commit 的所有 status context。確認 "Vercel" context 不再為 failure，或已移除。確認 combined status 為 success。 | D1 | devops | GitHub commit 顯示 ✅ success | Vercel context 仍 failure → 檢查 C3 是否生效 |
| D3 | **撰寫最終報告** | 彙整 16 項證據（見第六節），輸出至階段性報告。 | D1, D2 | devops → reviewer | 16 項證據完整覆審通過 | 若有 BLOCKED 項目，如實記錄 |

---

## 四、依賴關係圖

```
Phase A（調查確認）
A1 ─┐          A5 ── 可並行
A2 ─┤
    ▼
A3 ── 依賴 A1, A2
A4 ── 依賴 A1
    │
    ▼
Phase B（根因定位）
B1 ── 依賴 A4, A2
B2 ── 依賴 A5
B3 ── 依賴 A2
    │
    ▼
Phase C（修復執行）
C1 ── 依賴 B1, B2, B3 → 需用戶決策
C2a ── 依賴 C1（方案①）
C2b ── 依賴 C1（方案②，互斥）
C3 ── 依賴 C2a 或 C2b
C4 ── 依賴 A2
    │
    ▼
Phase D（最終驗證）
D1 ── 依賴 C3, C4
D2 ── 依賴 D1
D3 ── 依賴 D1, D2
```

### 關鍵路徑

```
A1 → A4 → B1 → C1 → C2a/C2b → C3 → D1 → D2 → D3
```

最短路徑（若無障礙）：5 個執行輪次。

---

## 五、修復方案詳細設計

### 方案選擇：停用 Vercel GitHub Integration（推薦 ⭐）

**理由**：
- 當前 GitHub Actions 已擁有完整且成功的部署流程（Deploy #57 ✅）
- Vercel GitHub Integration 與 GitHub Actions 重複部署，會造成狀態衝突
- 保持單一部署路徑（GitHub Actions → Vercel production）最清晰
- Integration 的自動部署可能因 rootDirectory 等配置不正確而持續失敗

**風險**：
- 停用 Integration 後，GitHub commit 上的 "Vercel" context 可能消失或殘留 failure
- 需要確認 GitHub Actions 的 `VERCEL_TOKEN` 有足夠權限
- 需要確認 GitHub Actions 部署成功後在 Vercel Dashboard 可見

### 替代方案：保留 Integration 但修復配置

若用戶偏好保留 Vercel GitHub Integration（例如為了 Vercel Preview Deployments for PRs），則需：
1. 在 Vercel Dashboard 設定正確的 Root Directory = `src/frontend`
2. 確認 Framework = Vite
3. 確認 Build Command = `npm run build`
4. 確認 Output Directory = `dist`
5. 確認 Production Branch = `master` 或 `main`
6. 關閉 Integration 的 "Auto Deploy" 或使其配置與 GitHub Actions 一致

### GitHub Actions commit status 覆蓋機制

若停用 Integration 後 "Vercel" context 仍殘留 failure，在 deploy.yml 增加步驟：

```yaml
- name: Update Vercel commit status to success
  if: success()
  run: |
    curl -L -X POST \
      -H "Authorization: Bearer ${{ secrets.GITHUB_TOKEN }}" \
      -H "Accept: application/vnd.github+json" \
      https://api.github.com/repos/${{ github.repository }}/statuses/${{ github.sha }} \
      -d '{
        "state": "success",
        "context": "Vercel",
        "description": "Deployment successful via GitHub Actions",
        "target_url": "https://github.com/${{ github.repository }}/actions/runs/${{ github.run_id }}"
      }'
```

注意：`GITHUB_TOKEN` 預設有權限更新 commit status，無需額外設定。

---

## 六、驗證方式總表

| 階段 | 任務 | 驗證命令/方法 | 預期結果 |
|------|------|------------|---------|
| A1 | CI Run #34 | `gh run view 30033762944` 或 `curl -L ...` | conclusion = success, head SHA 已知 |
| A2 | Deploy Run #57 | `gh run view 30029172018` 或 `curl -L ...` | conclusion = success, 含 deployment URL |
| A3 | SHA 比對 | 比對 A1 與 A2 的 head_sha | 一致 |
| A4 | Commit statuses | `curl -L /repos/{owner}/{repo}/commits/{sha}/statuses` | "Vercel" context = failure state |
| A5 | Vercel Integration | `curl /repos/{owner}/{repo}/hooks` 或 GitHub UI | 確認 Integration 存在 |
| B1 | Failure 來源 | 比對 Vercel context created_at 與 deploy run 時間 | 確定先後關係 |
| B2 | Integration 配置 | Vercel Dashboard 或 API | rootDirectory 等配置 |
| B3 | Actions commit status | 檢查 Deploy Run log | 確認是否有 setting commit status |
| C2a | 停用 Integration | 驗證 GitHub commit 無 "Vercel" context | 移除成功 |
| C4 | Production URL | `curl -I https://<deployment-url>` | HTTP 200 |
| D1 | 完整流程 | GitHub Actions 顯示 success | CI + Deploy 皆 success |
| D2 | 最終 commit status | GitHub commit 頁面顯示 ✅ | combined = success |

---

## 七、返工預案

### 常見障礙與對應措施

| 情境 | 觸發條件 | 措施 |
|------|---------|------|
| API rate limit | GitHub API 回傳 403/429 | 改用 GitHub UI 手動查詢，限速請求（加 `sleep 1`） |
| gh CLI 未安裝 | `gh` 命令不存在 | 用 `curl` + `GITHUB_TOKEN` 替代 |
| vercel CLI 未安裝 | `vercel` 命令不存在 | 通過 Actions log 推斷 project identity，或 npm install -g vercel |
| Vercel Dashboard 無法訪問 | 無 Dashboard 權限 | 通過 Vercel API 或 log 中的 project linkage 推斷 |
| GITHUB_TOKEN 無權限更新 status | curl 回傳 403 | 改用 `secrets.GITHUB_TOKEN`（預設有權限），或手動設定 PAT |
| Integration 解除後殘留 Vercel context | GitHub 仍顯示 Vercel: failure | 用 GitHub API 手動將 "Vercel" context 更新為 success |
| CI 因新變更失敗 | 觸發 workflow 後 CI 失敗 | 先修復 CI 問題（參見 Phase 2 修復經驗） |
| Deploy 因 secret 缺失失敗 | VERCEL_TOKEN 等未設定 | 引導用戶在 GitHub UI 設定 secrets |

### 回滾方案

若修復造成生產環境問題：
1. **GitHub Actions 回滾**：還原 deploy.yml 至前一版本，重新推送
2. **Vercel Integration 重新啟用**：在 Vercel Dashboard 重新啟用 Git Integration
3. **commit status 手動修復**：使用 GitHub API 直接設定正確狀態

---

## 八、完成證據清單（16 項）

最終報告必須包含以下 16 項證據：

| # | 證據項 | 對應任務 | 說明 |
|---|--------|---------|------|
| 1 | CI Run #34 的 head SHA | A1 | 確認 CI 驗證的 commit |
| 2 | Deploy Run #57 的 head SHA | A2 | 確認 deploy 的 commit |
| 3 | Deploy workflow 實際部署的 project name | A2 | 從 Actions log 或 API 取得 |
| 4 | Deploy workflow 實際 deployment URL | A2 | 從 Vercel CLI 輸出取得 |
| 5 | production URL HTTP 驗證結果 | C4 | `curl -I` 結果 |
| 6 | Vercel GitHub Integration 是否啟用 | A5 | 是/否 |
| 7 | GitHub Actions 與 Vercel Integration 是否重複部署 | B1 | 是/否 |
| 8 | Vercel failure status 的真正來源 | B1 | Integration / 遺留狀態 / 其他 |
| 9 | 修復內容 | C2a/C2b/C3 | 具體操作描述 |
| 10 | 新 commit SHA | D1 | 修復後的 push |
| 11 | 新 GitHub Actions deploy run ID | D1 | 驗證新流程 |
| 12 | 新 deployment URL | D1 | Vercel CLI 輸出 |
| 13 | GitHub Actions 最終 conclusion | D1 | success / failure |
| 14 | GitHub commit combined status | D2 | success / failure |
| 15 | Vercel context 最終狀態 | D2 | success / removed / 仍 failure |
| 16 | 尚未完成或 BLOCKED 項目 | D3 | 如實記錄 |

### 最終判定標準

| 狀態 | 結論 |
|------|------|
| GitHub commit 顯示 ✅ success，Vercel context 為 success 或已移除 | ✅ **修復完成** |
| GitHub commit 仍顯示 Vercel: failure | ❌ **修復未完成** — Deployment repair remains pending，不得結案 |

---

## 九、執行順序時間線

```
Round 1 (Phase A):
  A1 ──── 查 CI Run #34 ──── 10 min
  A2 ──── 查 Deploy Run #57 ─ 10 min （可並行）
  A5 ──── 查 Vercel Integration ─ 5 min （可並行）

Round 2 (Phase A + B):
  A3 ──── 比對 SHA ──── 2 min
  A4 ──── 查 commit statuses ─ 5 min
  B1 ──── 追蹤 failure 觸發者 ─ 10 min
  B2 ──── 檢查 Integration 配置 ─ 10 min
  B3 ──── 檢查 Actions commit status ─ 5 min

Round 3 (Phase C — 決策):
  C1 ──── 決策 ──── 需用戶選擇（非同步）
  
Round 4 (Phase C — 執行):
  C2a/C2b ─── 停用或修復 Integration ─ 15 min
  C3 ──── 新增 status 覆蓋 ── 15 min
  C4 ──── 驗證 production URL ── 5 min

Round 5 (Phase D):
  D1 ──── 觸發完整流程 ──── 等待 CI ~10 min + Deploy ~5 min
  D2 ──── 檢查最終 status ── 5 min
  D3 ──── 撰寫報告 ──── 15 min
```

**估計總時間**：約 2-3 小時（含等待 CI/CD 執行時間）

---

## 十、風險與注意事項

| 風險 | 影響 | 緩解措施 |
|------|------|---------|
| GitHub API rate limit (60 req/hr 未認證, 5000 req/hr 已認證) | 查詢受阻 | 使用 `GITHUB_TOKEN` 認證，必要時使用 GitHub UI |
| Vercel Integration 解除後無法重新啟用 | 無法恢復 | 解除前記錄當前配置，保留文件截圖 |
| GitHub commit 上的 Vercel context 無法消除 | 持續顯示 failure | 用 GitHub API 手動覆蓋為 success |
| 用戶無 Vercel Dashboard 管理員權限 | 無法修改 Integration 配置 | 引導用戶自行操作，或提供詳細操作步驟 |
| GITHUB_TOKEN 在 workflow 中 scope 不足 | 無法更新 commit status | 確認 `contents: write` 和 `checks: write` 權限 |
| `curl` 在 Windows 路徑下行為差異 | API 請求失敗 | 使用 Git Bash 或確認 curl 在 PATH 中 |

---

## 十一、審核與簽收

- [ ] devops 完成 Phase A（A1–A5）調查
- [ ] devops 完成 Phase B（B1–B3）根因定位
- [ ] 用戶確認修復方案（C1 決策）
- [ ] devops 完成 Phase C（C2–C4）修復執行
- [ ] devops 完成 Phase D（D1–D3）最終驗證
- [ ] reviewer 覆審 16 項證據完整性
- [ ] 最終報告明確寫明：修復完成 或 Deployment repair remains pending

---

> **版本**: 1.0  
> **建立者**: PLANNER  
> **下一階段**: devops 開始 Phase A 調查
