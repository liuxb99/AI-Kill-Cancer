# Current Status

更新日期：2026-08-10

AI-Kill-Cancer 當前主線：**v0.3.0 — Local-First Research & Demo Showcase**。

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
PTC Command Center + navbar continuity             VERIFIED
Production multi-route synthetic browser gate     VERIFIED — workflow #130 PASS
SQLite integrity / backup / restore               VERIFIED
Restart persistence regression                    VERIFIED
Local CSV Import v1                               VERIFIED
Pre-upgrade SQLite backup hook                     VERIFIED — Local Gate #140 PASS
Traceability Persistence E2E                       VERIFIED — Local Gate #142 PASS
Local CSV Import v2                               VERIFIED — Local Gate #146 PASS
Workspace Import local UI                         IMPLEMENTED
```

## Local CSV Import v2

第十五批已通過 **Local Verification Gate #146**。Preview 現在會逐類回報 deterministic records 的 `total / existing / new / existing_keys / new_keys`；confirmed import 會追加 `import-history.jsonl`，並可由 `GET /api/v1/workspace/import/history` 讀回。Import policy 持續固定為 `overwrite_existing=false`。

## Workspace Import local UI

第十六批新增本機操作介面：

```text
/workspace-import
```

新增前端 API adapter `src/frontend/src/api/workspace.ts`，統一封裝：

```text
GET  /api/v1/workspace/status
POST /api/v1/workspace/import/csv/preview
POST /api/v1/workspace/import/csv/commit
GET  /api/v1/workspace/import/history
```

UI 流程：

```text
Workspace status
→ CSV dataset directory path
→ Validate / Preview
→ validation result
→ duplicate summary (Existing / Skip vs New / Import)
→ Explicit Import
→ import result
→ history refresh / viewer
```

安全邊界：

- 只有 `backend=sqlite`、`persistent=true`、`app_mode=local|research` 顯示可寫入流程；
- Demo / Vercel / non-persistent runtime 只顯示 read-only guard，不顯示 Validate / Import 控制；
- UI 不會繞過後端確認契約；真正 commit 仍由 adapter 固定提交 `confirm=IMPORT`；
- UI 明確顯示 `Overwrite existing: NO`；
- Browser 目前採 directory path 輸入，不假裝網頁可直接取得本機資料夾絕對路徑；desktop file picker bridge 留到後續版本評估。

新增 `WorkspaceImportPage.test.tsx` regression：

- demo/non-persistent mode 不顯示寫入控制；
- local persistent SQLite 顯示 Preview flow；
- duplicate summary 顯示 Existing / Skip 與 New / Import；
- Explicit Import 呼叫 confirmed commit；
- import 完成後重新載入 history。

`App.tsx` 已加入 `/workspace-import` route 與 navbar 入口。

本批狀態：

**IMPLEMENTED — WAITING FOR LATEST SELF-HOSTED VERIFICATION**

## Demo Showcase 現況

九張 synthetic CSV 與三個固定 PTC showcase case 已建立。跨頁 contract：

```text
demo_case=<PTC-DEMO-xxx>&data_mode=synthetic
```

目前已支援 Homepage、Recommendation、Clinical Decision、Treatment Plan、Knowledge Graph、PTC Research、PTC Integrated Workbench、PTC Command Center，以及 synthetic navbar query propagation。

## v0.3.0 Acceptance Gate

### Vercel Demo
- [x] 九張標準 synthetic CSV；
- [x] 3 個固定 demo cases；
- [x] CSV → SQLite idempotent bootstrap；
- [x] demo cold-start production recovery；
- [x] demo status/cases API contract；
- [x] Homepage selector；
- [x] demo_case deep-link contract；
- [x] Recommendation hydration；
- [x] Clinical Decision hydration；
- [x] Treatment Plan hydration；
- [x] Knowledge Graph hydration；
- [x] PTC Research hydration；
- [x] PTC Integrated hydration；
- [x] PTC Command Center synthetic isolation；
- [x] Navbar synthetic query propagation；
- [x] 共用 provenance banner；
- [x] CSV schema / duplicate / broken-reference validator；
- [x] CSV row-shape / enum-value validator；
- [x] JSON-list payload validator；
- [x] Production multi-route E2E gate PASS。

### Local SQLite
- [x] config / schema bootstrap / FK / busy timeout；
- [x] file persistence；
- [x] integrity utility；
- [x] backup / atomic restore；
- [x] restart regression；
- [x] workspace status API / regression；
- [x] local CSV import v1；
- [x] pre-upgrade automatic backup hook；
- [x] traceability persistence E2E；
- [x] duplicate-aware CSV preview；
- [x] import history JSONL / API；
- [x] Workspace Import UI（latest gate 驗證中）。

## 下一批

優先順序：

1. 驗證 Workspace Import UI latest self-hosted gate；若 fail，依 job log 修到全綠；
2. 增加 App route/nav regression，確認 `/workspace-import` 可達且 synthetic/demo runtime 只讀；
3. VERSION / CHANGELOG / release checklist 收斂，評估 v0.3.0 milestone closure；
4. 若 release gate 全綠，再規劃 desktop file picker bridge / import history filtering，避免在 v0.3.0 收尾前擴 scope。

## 安全邊界

所有 synthetic demo 輸出只用於研究軟體流程展示，不代表真實醫學證據、患者資料、診斷、臨床決策或治療建議。v1.0 Research-Grade Stable 只描述軟體工程成熟度，不等同臨床有效性驗證。
