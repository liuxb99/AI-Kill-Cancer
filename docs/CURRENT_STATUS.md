# Current Status

更新日期：2026-08-10

AI-Kill-Cancer 當前主線：**v0.3.0 — Local-First Research & Demo Showcase**。

架構政策：Local SQLite 是主要持久化研究工作資料庫；Vercel 使用 bundled synthetic CSV + ephemeral demo runtime；PostgreSQL 是 Optional Scale-out Backend。

## 已驗證底座

```text
Local SQLite runtime / ORM compatibility          VERIFIED
SQLite file persistence / FK / memory regression  VERIFIED
Vercel Python/static routing                      VERIFIED
Production page/API/Chromium smoke                VERIFIED
Demo core CSV bootstrap + UUIDv5 idempotency      VERIFIED — Local Gate #74 PASS
Demo deep-link / Recommendation hydration         VERIFIED — Local Gate #90 PASS
SQLite integrity / backup / restore               VERIFIED — Local Gate #90 PASS
Restart persistence regression                    VERIFIED — Local Gate #90 PASS
```

## Demo Showcase 現況

九張 synthetic CSV 與三個固定 PTC showcase case 已完成。`/api/v1/demo/status` 與 `/api/v1/demo/cases` 已存在。

跨頁 contract：

```text
demo_case=<PTC-DEMO-xxx>&data_mode=synthetic
```

目前已支援：

- Homepage Demo Case Selector；
- Recommendation：自動載入同一 demo case / variant；
- Clinical Decision：synthetic decision workflow preview，不查正式 Patient UUID；
- Treatment Plan：synthetic treatment workflow preview，不建立正式計畫；
- Knowledge Graph：由同一 demo case 投影 6 entities / 5 relations；
- 共用 `DemoContextBanner` / `useDemoContext()`，跨頁 synthetic provenance 一致。

## Demo Dataset Validation

新增 `src/backend/demo/validator.py`：

- 檢查九張必要 CSV 是否存在；
- 必要欄位；
- blank key；
- duplicate key；
- Patient → Case → Specimen → Sequencing → Variant → Evidence → Drug / Publication / Trial 斷鏈。

`/api/v1/demo/status` 現在包含 `validation.ok/errors`；`/api/v1/demo/cases` 在資料集 validation fail 時回 503，避免展示半斷鏈資料。

新增 `tests/test_demo_validator.py`，包含 bundled dataset 正常與 broken patient reference 失敗案例。

## Local SQLite Workspace

已驗證：SQLite file persistence、FK、busy timeout、integrity、backup、atomic restore、restart persistence。

本批新增：

`GET /api/v1/workspace/status`

回報：

```text
app_mode
backend
local_first
persistent
database_path
exists
size_bytes
integrity.ok / message
backup_directory
```

此 API 讓本地 UI / CLI / release gate 可判斷目前是否真正運行在持久化 Local SQLite workspace。

## 本批狀態

第四批新增：

```text
Shared DemoContextBanner/useDemoContext          IMPLEMENTED
Clinical Decision synthetic hydration            IMPLEMENTED
Treatment Plan synthetic hydration               IMPLEMENTED
Knowledge Graph synthetic projection             IMPLEMENTED
Demo CSV validator                               IMPLEMENTED
Demo status validation contract                  IMPLEMENTED
Workspace status API                             IMPLEMENTED
Demo validator regression                        IMPLEMENTED
```

最新新增項目尚未由對應最新 head 的 self-hosted gate 完成，因此狀態為：

**IMPLEMENTED — WAITING FOR LATEST SELF-HOSTED VERIFICATION**

## v0.3.0 Acceptance Gate

### Vercel Demo
- [x] 九張標準 synthetic CSV；
- [x] 3 個固定 demo cases；
- [x] CSV → SQLite idempotent bootstrap；
- [x] demo status/cases API；
- [x] Homepage selector；
- [x] demo_case deep-link contract；
- [x] Recommendation hydration；
- [x] Clinical Decision hydration；
- [x] Treatment Plan hydration；
- [x] Knowledge Graph hydration；
- [x] 共用 provenance banner；
- [x] CSV schema / duplicate / broken-reference validator；
- [ ] PTC Workbench / Research hydrate；
- [ ] multi-route Chromium E2E。

### Local SQLite
- [x] config / schema bootstrap / FK / busy timeout；
- [x] file persistence；
- [x] integrity utility；
- [x] backup / atomic restore；
- [x] restart regression；
- [x] workspace status API；
- [ ] workspace status regression；
- [ ] local CSV import；
- [ ] pre-upgrade automatic backup hook；
- [ ] traceability persistence E2E。

## 下一批

PTC Workbench / Research demo hydration、workspace status regression、pre-upgrade backup hook、local CSV import 第一版、enum/value-domain validator、multi-route Chromium E2E，以及 VERSION / CHANGELOG / release checklist。

## 安全邊界

所有 synthetic demo 輸出只用於研究軟體流程展示，不代表真實醫學證據、患者資料、診斷、臨床決策或治療建議。v1.0 Research-Grade Stable 只描述軟體工程成熟度，不等同臨床有效性驗證。
