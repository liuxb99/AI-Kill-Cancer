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
Production page/API JSON smoke                    VERIFIED
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

本批新增 `WorkspaceImportRoute.test.tsx`，補 App routing + navbar entry regression，避免頁面本身測試通過但實際 route 不可達。

## 第十七批：1.0.3 release convergence

本批已完成：

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

Release checklist 明確禁止在 release-candidate latest gates 尚未全綠前建立或移動 `v1.0.3` tag。

本批狀態：

**IMPLEMENTED — WAITING FOR LATEST RELEASE-CANDIDATE VERIFICATION**

## Demo Showcase 現況

九張 synthetic CSV 與三個固定 PTC showcase case 已建立。跨頁 contract：

```text
demo_case=<PTC-DEMO-xxx>&data_mode=synthetic
```

目前已支援 Homepage、Recommendation、Clinical Decision、Treatment Plan、Knowledge Graph、PTC Research、PTC Integrated Workbench、PTC Command Center，以及 synthetic navbar query propagation。

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
- [ ] latest 1.0.3 release-candidate Local Verification Gate PASS。

## Vercel Demo Acceptance Gate

- [x] deterministic synthetic CSV bootstrap；
- [x] demo status/cases API；
- [x] synthetic deep-link contract；
- [x] major-route hydration；
- [x] navbar query propagation；
- [x] dataset validators；
- [x] previous Production API JSON smoke PASS；
- [x] previous multi-route Chromium gate PASS；
- [ ] latest 1.0.3 release-candidate production deploy / smoke PASS。

## 下一批

優先順序：

1. 驗證 1.0.3 release-candidate latest Local Verification Gate；若 fail，依 job log 修到全綠；
2. 驗證 latest production deploy、API JSON smoke、multi-route Chromium gate；
3. 搜尋 release-critical runtime metadata 是否仍誤報 1.0.2；
4. 所有 release checklist 全綠後，再建立 `v1.0.3` tag / release；
5. release 完成前不再擴 scope 到 desktop file picker 或新研究功能。

## 安全邊界

所有 synthetic demo 輸出只用於研究軟體流程展示，不代表真實醫學證據、患者資料、診斷、臨床決策或治療建議。1.0.3 的版本成熟度只描述軟體工程成熟度，不等同臨床有效性驗證。
