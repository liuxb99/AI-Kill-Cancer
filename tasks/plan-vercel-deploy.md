# Vercel 部署修復執行計劃

> **文件狀態**：已核准  
> **負責角色**：devops（主代理）、reviewer（覆審）  
> **產出**：本計劃 + 最終回報 18 項證據  
> **建立時間**：2025-07-24 00:30

---

## 一、現狀摘要（調查前已知）

| 項目 | 狀態 |
|------|------|
| ci.yml | ✅ 存在，前端測試 + build 正常 |
| deploy.yml | ⚠️ 存在但為 SSH 部署（Docker），非 Vercel |
| vercel.json | ✅ 根目錄存在，rootDirectory: `src/frontend`，但 nodeVersion: `18`（環境為 v22） |
| package.json | ✅ 前端 Vite + React 專案，build script 正常 |
| vite.config.ts | ✅ 基本配置 |
| gh CLI | ❌ 未安裝，需改用 curl + GitHub API |
| Git | ✅ 可用，最近 commit `3674e4b` |
| Node.js | ✅ v22.14.0 可用 |
| npm | ✅ 11.16.0 可用 |
| .vercel/project.json | ❌ 不存在（尚未連結 Vercel 專案） |

---

## 二、任務清單（含 ID、依賴、返工預案）

### Phase A：現狀調查（A1–A4）

| ID | 任務 | 依賴 | 負責 | 返工預案 |
|----|------|------|------|----------|
| A1 | **審查所有 workflow 檔案** | 無 | devops | 若發現新 workflow 檔案，補充審查 |
| A2 | **審查前端建置相關檔案**（package.json、vite.config.ts、vercel.json、tsconfig.json） | 無 | devops | 若缺少任一檔案，標記 BLOCKED |
| A3 | **確認 gh CLI 可用性，改用 curl 查 GitHub API** | 無 | devops | gh 不可用則採用 curl + GitHub REST API |
| A4 | **查詢最近 failed GitHub Actions run** | A1, A3 | devops | 若 API 無結果，提供手動查詢指令 |

### Phase B：根因分析（B1–B2）

| ID | 任務 | 依賴 | 負責 | 返工預案 |
|----|------|------|------|----------|
| B1 | **定位第一個失敗 step 與錯誤訊息** | A4 | devops | 若 log 截斷，改用 GitHub UI 截圖對照 |
| B2 | **分析根因並撰寫結構化錯誤報告** | B1 | devops | reviewer 驗證分析合理性 |

### Phase C：修復部署流程（C1–C5）

| ID | 任務 | 依賴 | 負責 | 返工預案 |
|----|------|------|------|----------|
| C1 | **比對 Vercel 官方部署流程**（文檔 + 現有 vercel.json 配置） | A2 | devops | 參考 [Vercel GitHub Actions 官方文檔](https://vercel.com/docs/deployments/git#github-actions) |
| C2 | **修正 vercel.json 配置**（nodeVersion → 22，確認其他設定） | C1 | devops | reviewer 審查配置正確性 |
| C3 | **重寫 deploy.yml 為 Vercel CLI 部署** | C1, A1 | devops | 兩種方案擇一（見第三節），reviewer 審查 |
| C4 | **確認 GitHub Secrets 名稱一致性**（檢查 VERCEL_TOKEN 等） | C3 | devops | 若 secret 不存在，引導用戶在 GitHub UI 設定 |
| C5 | **撰寫 git commit message 並推送** | C2, C3, C4 | devops | 若 push 失敗，檢查 remote 連線 |

### Phase D：驗證與監看（D1–D4）

| ID | 任務 | 依賴 | 負責 | 返工預案 |
|----|------|------|------|----------|
| D1 | **觸發 workflow 並監看 CI 結果** | C5 | devops | 等待 3 分鐘未觸發則手動 workflow_dispatch |
| D2 | **監看 deploy workflow 結果** | D1 | devops | 若 deploy 跳過，檢查 CI 結論是否 success |
| D3 | **回報三種狀態**（GitHub Actions conclusion、Vercel deployment conclusion、commit status） | D1, D2 | devops | 若 Vercel 部署 URL 未公開，回報已知信息 |
| D4 | **彙整 18 項完成證據** | 全部 | devops → reviewer | reviewer 覆審證據完整性後結案 |

---

## 三、修復方案詳細設計

### 方案選擇：重寫 deploy.yml 為 Vercel 部署（推薦）

**理由**：
- 保持 CI（測試）與 CD（部署）分離
- 不影響現有 ci.yml 的 Python 後端測試
- 遵循 Vercel 官方推薦的 GitHub Actions 整合方式

### 新 deploy.yml 設計要點

```yaml
name: Deploy to Vercel

on:
  workflow_run:
    workflows: [CI]
    types: [completed]
    branches: [master, main]
  # 也支援手動觸發
  workflow_dispatch:

env:
  VERCEL_ORG_ID: ${{ secrets.VERCEL_ORG_ID }}
  VERCEL_PROJECT_ID: ${{ secrets.VERCEL_PROJECT_ID }}

jobs:
  deploy:
    runs-on: ubuntu-latest
    if: ${{ github.event.workflow_run.conclusion == 'success' || github.event_name == 'workflow_dispatch' }}
    steps:
      - uses: actions/checkout@v4

      - name: Install Vercel CLI
        run: npm install -g vercel@latest

      - name: Pull Vercel Environment Information
        run: vercel pull --yes --environment=production --token=${{ secrets.VERCEL_TOKEN }}

      - name: Build Project Artifacts
        run: vercel build --prod --token=${{ secrets.VERCEL_TOKEN }}

      - name: Deploy Project Artifacts to Vercel
        run: vercel deploy --prebuilt --prod --token=${{ secrets.VERCEL_TOKEN }}
```

### 所需 Secrets

| Secret 名稱 | 說明 | 取得方式 |
|-------------|------|----------|
| `VERCEL_TOKEN` | Vercel 個人存取 Token | Vercel Dashboard → Settings → Tokens |
| `VERCEL_ORG_ID` | Vercel 團隊/個人 ID | `vercel whoami` 或 Vercel Dashboard |
| `VERCEL_PROJECT_ID` | Vercel 專案 ID | `vercel link` 後從 `.vercel/project.json` 取得 |

### 替代方案：在 ci.yml 中合併部署步驟

若用戶偏好單一 workflow，可在 ci.yml 的 frontend job 末尾追加部署步驟。  
但這會使 CI 和 CD 耦合，不建議。

---

## 四、風險與注意事項

1. **gh CLI 不可用** → 使用 `curl` + `gh api` 替代，或直接輸出 GitHub UI 查詢指令
2. **Windows 路徑問題** → bash 子系統路徑為 `/mnt/d/...`，文件工具使用相對路徑
3. **Vercel 專案未連結** → 若 `.vercel/project.json` 不存在，需先在本機執行 `vercel link`
4. **Secrets 缺失** → 若 VERCEL_TOKEN 等未設定，需告知用戶手動添加
5. **vercel.json nodeVersion** → 18 與環境 22 不匹配，需更新為 22
6. **deploy.yml 舊配置** → SSH 部署全部替換為 Vercel，無需保留 rollback
7. **npm ci 可能失敗** → 確認 `package-lock.json` 存在 `src/frontend/` 下

---

## 五、完成證據表格（最終回報模板）

| # | 證據項 | 任務 ID | 狀態 |
|---|--------|---------|------|
| 1 | 部署 workflow 文件路徑 | A1 | ⬜ |
| 2 | workflow trigger | A1 | ⬜ |
| 3 | 使用的 Secret 名稱（不得輸出值） | C4 | ⬜ |
| 4 | 原失敗 run ID | A4 | ⬜ |
| 5 | 原失敗 job 與 step | B1 | ⬜ |
| 6 | 第一個有效錯誤 | B1 | ⬜ |
| 7 | 根因 | B2 | ⬜ |
| 8 | 修改的 workflow diff | C3 | ⬜ |
| 9 | 新 commit SHA | C5 | ⬜ |
| 10 | 新 GitHub Actions run ID | D1 | ⬜ |
| 11 | frontend test 結果 | D1 | ⬜ |
| 12 | frontend build 結果 | D1 | ⬜ |
| 13 | Vercel CLI build 結果 | D2 | ⬜ |
| 14 | Vercel deploy 結果 | D2 | ⬜ |
| 15 | 最終 GitHub Actions conclusion | D3 | ⬜ |
| 16 | 最終 commit status | D3 | ⬜ |
| 17 | 部署 URL（若 log 有提供才可回報） | D3 | ⬜ |
| 18 | 尚未完成或 BLOCKED 項目 | D4 | ⬜ |

---

## 六、執行順序（時間線）

```
A1 ─┐
A2 ─┤
A3 ─┤
A4 ─┘
    │
    ▼
B1 ─┐
B2 ─┘
    │
    ▼
C1 ─┐
C2 ─┤
C3 ─┤
C4 ─┤
C5 ─┘
    │
    ▼
D1 ─┐
D2 ─┤
D3 ─┤
D4 ─┘
```

所有 Phase A 任務可並行，Phase B 依賴 A，Phase C 依賴 A+B，Phase D 依賴 C。

---

## 七、審核與簽收

- [ ] devops 完成所有任務並填寫 18 項證據
- [ ] reviewer 覆審證據完整性
- [ ] 最終報告輸出至 `tasks/vercel-deploy-report.md`
