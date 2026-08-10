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
PTC Research synthetic hydration                  VERIFIED — production workflow 97cb6a7 PASS
PTC Integrated synthetic hydration                VERIFIED — production workflow 729e643 PASS
PTC Command Center + navbar continuity             VERIFIED — production workflow bd30338 PASS
SQLite integrity / backup / restore               VERIFIED
Restart persistence regression                    VERIFIED
```

2026-08-10 production incident 已完成根因修復：demo cold-start 曾因 `cancer_cases.csv` JSON/CSV quoting 與 fusion variant 欄位錯位而失敗，導致 DB API 500/503。修正後 Vercel production deploy、page smoke 與 DB/API JSON smoke 已通過，`/api/v1/ptc-data-quality/overview` 已恢復。

## Demo Showcase 現況

九張 synthetic CSV 與三個固定 PTC showcase case 已完成。`/api/v1/demo/status` 與 `/api/v1/demo/cases` 已存在。

跨頁 contract：

```text
demo_case=<PTC-DEMO-xxx>&data_mode=synthetic
```

目前已支援：Homepage Demo Case Selector、Recommendation、Clinical Decision、Treatment Plan、Knowledge Graph、PTC Research、PTC Integrated Workbench、PTC Command Center synthetic isolation，以及 App-level synthetic navbar query propagation。

PTC Command Center 採 route-level isolation：帶 `demo_case` 時不 mount real command-center component，因此不觸發 source status、readiness、outcome、complete graph 或 full sync API；沒有 synthetic context 時仍沿用原本真實研究總控台。

## Demo Dataset Validation

`src/backend/demo/validator.py` 檢查九張必要 CSV、必要欄位、blank/duplicate key、跨表斷鏈、CSV row shape / 額外欄位、重要 categorical value domains 與 synthetic `data_mode` 邊界。

`/api/v1/demo/status` 包含 `validation.ok/errors`；`/api/v1/demo/cases` 在資料集 validation fail 時回 503。

## Local SQLite Workspace

已驗證 SQLite file persistence、FK、busy timeout、integrity、backup、atomic restore、restart persistence。`GET /api/v1/workspace/status` 回報 app mode、backend、local-first/persistent、database path、size、integrity 與 backup directory。

## 本批狀態

第十批新增：

```text
Production synthetic multi-route Chromium gate   IMPLEMENTED
Demo status/cases production API smoke            IMPLEMENTED
Per-route query continuity assertion              IMPLEMENTED
Per-route meaningful render assertion             IMPLEMENTED
Per-route synthetic-context assertion             IMPLEMENTED
JS/CSS bad-response gate                          IMPLEMENTED
Per-route screenshot evidence                     IMPLEMENTED
```

`.github/workflows/vercel-production-after-local.yml` 已從單一首頁 browser smoke 升級為 production synthetic multi-route gate。部署後 Chromium 會使用固定：

```text
?demo_case=PTC-DEMO-001&data_mode=synthetic
```

逐頁驗證：

```text
/recommendation
/clinical-decision
/treatment-plans
/clinical-graph
/ptc-research
/ptc-workbench
/ptc-command-center
```

每一頁都必須同時滿足：

- HTTP < 400；
- `#root` 有實際內容且 body 非白屏；
- URL 仍保留 `demo_case=PTC-DEMO-001`；
- URL 仍保留 `data_mode=synthetic`；
- 頁面能辨識 synthetic context（banner 或 synthetic 文案）；
- 不得有 JS/CSS >= 400；
- 不得有 browser `pageerror`。

失敗時 production workflow 直接失敗，不再把「首頁能開」誤判成整個 Demo Showcase 正常。每條 route 都輸出獨立 screenshot，另輸出 `production-browser-report.json` 作為 workflow artifact。

Production API smoke 同步新增：

```text
/api/v1/demo/status
/api/v1/demo/cases
```

上一批 `bd30338` 已完成 Vercel Production After Local Verification，結論為 success；因此 Command Center synthetic isolation 與 navbar continuity 已升級為 VERIFIED。

本批 workflow 變更已提交，等待 latest self-hosted gate + production workflow 實際跑過，因此本批狀態為：

**IMPLEMENTED — WAITING FOR PRODUCTION MULTI-ROUTE VERIFICATION**

## v0.3.0 Acceptance Gate

### Vercel Demo
- [x] 九張標準 synthetic CSV；
- [x] 3 個固定 demo cases；
- [x] CSV → SQLite idempotent bootstrap；
- [x] demo cold-start production recovery；
- [x] demo status/cases API；
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
- [x] Browser/Chromium production multi-route E2E gate（待 latest production run 驗證）。

### Local SQLite
- [x] config / schema bootstrap / FK / busy timeout；
- [x] file persistence；
- [x] integrity utility；
- [x] backup / atomic restore；
- [x] restart regression；
- [x] workspace status API / regression；
- [ ] local CSV import；
- [ ] pre-upgrade automatic backup hook；
- [ ] traceability persistence E2E。

## 下一批

優先順序：

1. 等 latest production multi-route gate 真實跑過；若某一 route fail，直接依 browser report / screenshot 修到全綠；
2. local CSV import 第一版，採 `validate → preview → explicit import`，不允許靜默覆寫；
3. pre-upgrade automatic backup hook；
4. traceability persistence E2E；
5. VERSION / CHANGELOG / release checklist 收斂。

## 安全邊界

所有 synthetic demo 輸出只用於研究軟體流程展示，不代表真實醫學證據、患者資料、診斷、臨床決策或治療建議。v1.0 Research-Grade Stable 只描述軟體工程成熟度，不等同臨床有效性驗證。
