# Current Status

更新日期：2026-08-10

AI-Kill-Cancer 當前產品 release line：**1.0.3 candidate**。

工程 roadmap milestone：**Local-First Research & Demo Showcase（代號 v0.3.0）**。

> `v0.3.0` 是 roadmap / engineering milestone，不再當作產品 SemVer。倉庫既有產品版本已是 1.0.2，因此本輪 release 正確向前收斂到 1.0.3，避免版本倒退。

架構政策：Local SQLite 是主要持久化研究工作資料庫；Vercel 使用 bundled synthetic CSV + ephemeral demo runtime；PostgreSQL 是 Optional Scale-out Backend。

## 已驗證底座

```text
Local SQLite runtime / ORM compatibility          VERIFIED
SQLite file persistence / FK / memory regression  VERIFIED
Vercel Python/static routing                      VERIFIED
Production page/API JSON smoke                    VERIFIED (previous gate)
Demo cold-start bootstrap                         VERIFIED
Demo core CSV bootstrap + UUIDv5 idempotency      VERIFIED
Demo deep-link / Recommendation hydration         VERIFIED
PTC Research synthetic hydration                  VERIFIED
PTC Integrated synthetic hydration                VERIFIED
PTC Command Center + navbar continuity            VERIFIED
Production multi-route synthetic browser gate     VERIFIED — workflow #130 PASS
SQLite integrity / backup / restore               VERIFIED
Restart persistence regression                    VERIFIED
Local CSV Import v1                               VERIFIED
Pre-upgrade SQLite backup hook                     VERIFIED — Local Gate #140 PASS
Traceability Persistence E2E                       VERIFIED — Local Gate #142 PASS
Local CSV Import v2                               VERIFIED — Local Gate #146 PASS
Workspace Import local UI                         VERIFIED — Local Gate #152 PASS
```

## Workspace Import local UI

`/workspace-import` 已完成並通過 Local Gate #152。UI 支援：

```text
Workspace status
→ CSV dataset directory path
→ Validate / Preview
→ duplicate summary
→ Explicit Import
→ import result
→ history viewer
```

安全邊界：只有 `backend=sqlite`、`persistent=true`、`app_mode=local|research` 顯示可寫入流程；Demo/Vercel/non-persistent runtime 為 read-only guard。Import policy 固定 `overwrite_existing=false`。

`WorkspaceImportRoute.test.tsx` 已補 App routing + navbar entry regression，避免頁面本身測試通過但實際 route 不可達。

## 第十七批：1.0.3 release convergence

已完成：

```text
root VERSION                         1.0.2 → 1.0.3
backend Settings.APP_VERSION        1.0.2 → 1.0.3
CHANGELOG.md                        ADDED
RELEASE_NOTES_v1.0.3.md            ADDED
docs/RELEASE_CHECKLIST_v1.0.3.md   ADDED
README.md                           REFRESHED
Workspace Import App route test     ADDED
```

版本權威定義：

```text
Product SemVer authority:
  VERSION
  src/backend/config.py::Settings.APP_VERSION

Frontend package.json:
  private package metadata
  不作為產品 release authority
```

## 第十八批：release gate failure triage / Vercel quota hardening

最新 1.0.3 candidate 的 Local Verification Gate 已成功觸發 production workflow，但 production deploy 在 Vercel 建置前被平台 quota 擋下。Actions log 的根因為：

```text
Error: Resource is limited - try again in 24 hours
code: api-deployments-free-per-day
```

這不是應用程式 build/test/runtime failure，也不是 VERCEL_TOKEN、project link、rootDirectory 或 production env preflight failure；上述步驟均已通過。因 deploy 沒有建立成功，後續 production page smoke、API JSON smoke、Chromium multi-route gate 被正確跳過。

本批已 harden `.github/workflows/vercel-production-after-local.yml`：

- 不再對失敗 deploy 的 null stdout 直接 `.Trim()`，避免二次 PowerShell null exception 掩蓋真正根因；
- 捕捉 `api-deployments-free-per-day` / `Resource is limited - try again in 24 hours`；
- 輸出明確 `VERCEL_DAILY_DEPLOYMENT_QUOTA_EXHAUSTED` 訊息；
- 明確禁止用 no-op commit 反覆消耗/重試 production deploy；
- 保持「只有最新通過 Local Gate 的 master SHA 才可 deploy」契約。

因此 1.0.3 release 目前的唯一已知外部 blocker 是 **Vercel Free plan daily deployment quota**。在 quota reset 或有可用 deployment quota 前，不建立 `v1.0.3` tag。

## Local SQLite Acceptance Gate

- [x] config / schema bootstrap / FK / busy timeout；
- [x] file persistence；
- [x] integrity utility；
- [x] backup / atomic restore；
- [x] restart regression；
- [x] workspace status API / regression；
- [x] local CSV import v1；
- [x] duplicate-aware CSV preview；
- [x] import history JSONL / API；
- [x] pre-upgrade automatic backup hook；
- [x] traceability persistence E2E；
- [x] Workspace Import UI；
- [x] Workspace Import App route/nav regression implemented；
- [ ] latest head after quota-hardening Local Verification Gate PASS。

## Vercel Demo Acceptance Gate

- [x] deterministic synthetic CSV bootstrap；
- [x] demo status/cases API；
- [x] synthetic deep-link contract；
- [x] major-route hydration；
- [x] navbar query propagation；
- [x] dataset validators；
- [x] previous Production API JSON smoke PASS；
- [x] previous multi-route Chromium gate PASS；
- [ ] 1.0.3 candidate production deploy — BLOCKED BY VERCEL DAILY QUOTA；
- [ ] latest API JSON smoke / Chromium gate — waiting for successful deployment。

## 下一批

優先順序：

1. 驗證 quota-hardening commit 的 latest Local Verification Gate；
2. 不以 no-op commit 反覆重試 Vercel；等待 daily quota reset 後，由下一個真實、已驗證 master SHA 觸發 production deploy；
3. production deploy 成功後立即跑 page/API JSON/Chromium multi-route gates；
4. 所有 release checklist 全綠後，再建立 `v1.0.3` tag / release；
5. release 完成前不擴 scope 到 desktop file picker 或新研究功能。

## 安全邊界

所有 synthetic demo 輸出只用於研究軟體流程展示，不代表真實醫學證據、患者資料、診斷、臨床決策或治療建議。1.0.3 的版本成熟度只描述軟體工程成熟度，不等同臨床有效性驗證。
