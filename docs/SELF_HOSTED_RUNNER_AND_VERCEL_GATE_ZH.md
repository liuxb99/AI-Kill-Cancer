# AI-Kill-Cancer 本機驗證 → Vercel Production Gate

更新日期：2026-08-09

## 發布鐵律

```text
Push master
→ Windows self-hosted Local Verification Gate
→ SUCCESS
→ Vercel Production Action
→ Production smoke test
```

本機驗證未成功，不得更新 Vercel Production。

## 為什麼目前會 queued

2026-08-09 交叉檢查顯示：

- `DWG_todo` 的 self-hosted CI 同時間能進入 `in_progress`；
- `AI-Kill-Cancer` 的 `Local Verification Gate` 長時間停在 queued；
- 因此不是所有本機 runner 離線，而是 AI-Kill-Cancer 很可能沒有可用的 repo-level runner 註冊/授權。

Workflow 已只要求：

```text
[self-hosted, Windows, X64]
```

所以額外 `ai-ci` label 不是阻塞原因。

## AI-Kill-Cancer runner 註冊

使用官方 Windows x64 GitHub Actions runner package。將 runner 解壓到例如：

```text
C:\actions-runner-ai-kill-cancer
```

取得 AI-Kill-Cancer repository 的一次性 runner registration token 後，以系統管理員 PowerShell 執行：

```powershell
.\scripts\register-ai-kill-cancer-runner.ps1 -RunnerToken '<ONE_TIME_TOKEN>'
```

如果該目錄已經註冊過其他 runner，可使用：

```powershell
.\scripts\register-ai-kill-cancer-runner.ps1 -RunnerToken '<ONE_TIME_TOKEN>' -Replace
```

註冊成功後服務會啟動，queued 的 `Local Verification Gate` 應自動被接走。

> Registration token 是短期的一次性憑證，不要寫入 Git、文件或 workflow secret。

## Vercel gate

`.github/workflows/vercel-production-after-local.yml` 只會在以下條件全部成立時執行：

```text
Local Verification Gate = success
branch = master
event = push
verified SHA = current origin/master SHA
```

因此過時 commit 即使驗證成功，也不能部署 Production。

直接 Git push 觸發的 Vercel Git Integration build 由 `vercel.json` 的 `ignoreCommand` 擋掉；Production 由 GitHub Action 使用 Vercel CLI 控制。

## 必要 GitHub Secret

AI-Kill-Cancer repository 必須設定：

```text
VERCEL_TOKEN
```

沒有 token 時 production deploy 必須 fail-closed。

## 不得回退

1. 不可改回 GitHub-hosted runner 來繞過本機 gate。
2. 不可因 SQLite local test 通過就跳過正式發布 gate。
3. Vercel Production 必須部署已通過 Local Verification Gate 的同一個 SHA。
4. Production deployment 後必須執行 HTTP smoke test。
5. SQLite 仍是 local/research backend；Vercel Production database policy 仍以 PostgreSQL 為權威。
