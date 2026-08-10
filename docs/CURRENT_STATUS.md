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
Vercel quota-hardening baseline                   VERIFIED — Local Gate #162 PASS
```

## 1.0.3 release convergence

版本權威：

```text
VERSION = 1.0.3
Settings.APP_VERSION = 1.0.3
```

Frontend `package.json/package-lock.json` 為 private package metadata，不是產品 release authority。

已建立：

- `CHANGELOG.md`
- `RELEASE_NOTES_v1.0.3.md`
- `docs/RELEASE_CHECKLIST_v1.0.3.md`
- `WorkspaceImportRoute.test.tsx`

README 已刷新為目前 Local-First 架構與 Demo/Research 邊界。

## 第十八批：Vercel quota hardening

最新 production workflow 已通過 token、project link、rootDirectory、production env preflight，真正失敗於：

```text
Error: Resource is limited - try again in 24 hours
code: api-deployments-free-per-day
```

此為 Vercel Free plan daily deployment quota，不是 application build/runtime failure。

Production workflow 已修正：

- deploy failure 不再對 null stdout `.Trim()`；
- 明確辨識 `api-deployments-free-per-day`；
- 輸出 `VERCEL_DAILY_DEPLOYMENT_QUOTA_EXHAUSTED`；
- 禁止用 no-op commit 反覆重試；
- 保持只有最新通過 Local Gate 的 master SHA 可部署。

## 第十九批：release metadata consistency gate

本批完成 release-critical metadata 收斂。

新增：

```text
tests/test_release_metadata.py
```

Local Verification Gate 現在自動驗證：

- root `VERSION` 必須是 1.0.3；
- backend `Settings.APP_VERSION` 必須與 root VERSION 完全一致；
- 對應 `RELEASE_NOTES_v<version>.md` 必須存在；
- 對應 `docs/RELEASE_CHECKLIST_v<version>.md` 必須存在；
- `CHANGELOG.md` 必須包含目前產品版本；
- frontend package 必須保持 private，避免誤當產品版本權威。

倉庫 `1.0.2` 掃描結果：未發現 release-critical runtime authority 仍回報 1.0.2。剩餘命中屬舊測試說明文字或 private frontend/package-lock metadata；auth hardening 測試說明已同步更新至 v1.0.3。

`docs/RELEASE_CHECKLIST_v1.0.3.md` 已把 runtime metadata scan 標為完成，並記錄 Local Gate #162 PASS。

本批狀態：

**IMPLEMENTED — WAITING FOR LATEST METADATA-CONSISTENCY LOCAL GATE**

## Local SQLite Acceptance Gate

- [x] config / schema bootstrap / FK / busy timeout；
- [x] file persistence；
- [x] integrity / backup / restore；
- [x] restart persistence；
- [x] workspace status API；
- [x] local CSV import v1/v2；
- [x] duplicate-aware preview / import history；
- [x] pre-upgrade backup hook；
- [x] traceability persistence E2E；
- [x] Workspace Import UI + route/nav regression；
- [x] quota-hardening baseline Local Gate #162 PASS；
- [ ] latest metadata-consistency Local Verification Gate PASS。

## Vercel Demo Acceptance Gate

- [x] deterministic synthetic CSV bootstrap；
- [x] demo status/cases API；
- [x] synthetic deep-link / major-route hydration；
- [x] navbar query propagation；
- [x] dataset validators；
- [x] previous Production API JSON smoke PASS；
- [x] previous multi-route Chromium gate PASS；
- [ ] 1.0.3 candidate production deploy — BLOCKED BY VERCEL DAILY QUOTA；
- [ ] latest API JSON smoke / Chromium gate — waiting for successful deployment。

## 下一批

1. 驗證 metadata-consistency Local Gate；若 fail 直接修到全綠；
2. release candidate 期間不再擴功能、不製造 no-op deploy；
3. Vercel quota reset 後，用下一個真實 verified master SHA 觸發 production deploy；
4. production page/API/Chromium 全綠後建立 `v1.0.3` tag / release；
5. tag 完成後才開下一個功能 milestone。

## 安全邊界

所有 synthetic demo 輸出只用於研究軟體流程展示，不代表真實醫學證據、患者資料、診斷、臨床決策或治療建議。1.0.3 的版本成熟度只描述軟體工程成熟度，不等同臨床有效性驗證。
