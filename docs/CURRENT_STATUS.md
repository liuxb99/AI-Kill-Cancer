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

目前已支援：Homepage Demo Case Selector、Recommendation、Clinical Decision、Treatment Plan、Knowledge Graph、PTC Research，以及 PTC Integrated Workbench synthetic hydration。所有 synthetic 頁面沿用 `DemoContextBanner` / `useDemoContext()`，保持 provenance 一致。

PTC Research / Integrated 在 synthetic mode 下不再誤查研究資料庫。Integrated Workbench 直接投影 Case、Variant、Evidence、Drug、Publication、Clinical Trial，並停用 dashboard、最近病例、integrated recommendation、similarity、中藥 bootstrap 與 interaction API；沒有 `demo_case` 時保留原本 research database path。

## Demo Dataset Validation

`src/backend/demo/validator.py` 檢查九張必要 CSV、必要欄位、blank/duplicate key、跨表斷鏈、CSV row shape / 額外欄位、重要 categorical value domains 與 synthetic `data_mode` 邊界。

`/api/v1/demo/status` 包含 `validation.ok/errors`；`/api/v1/demo/cases` 在資料集 validation fail 時回 503。

`tests/test_demo_validator.py` 已覆蓋 broken reference、extra CSV field、invalid variant value-domain regression。

## Local SQLite Workspace

已驗證 SQLite file persistence、FK、busy timeout、integrity、backup、atomic restore、restart persistence。`GET /api/v1/workspace/status` 回報 app mode、backend、local-first/persistent、database path、size、integrity 與 backup directory。

`tests/test_workspace_status.py` 覆蓋 local/research SQLite persistent、demo SQLite ephemeral 與 non-SQLite backend contract。

## 本批狀態

第七批新增：

```text
PTC Integrated synthetic hydration                IMPLEMENTED
Integrated synthetic / research API isolation     IMPLEMENTED
Case → Variant → Evidence → Drug projection       IMPLEMENTED
Publication / Trial projection                    IMPLEMENTED
Integrated frontend regression                    IMPLEMENTED
Previous PTC Research hydration                   VERIFIED IN PRODUCTION
```

`src/frontend/src/test/PTCIntegratedSelectionPage.test.tsx` 現在同時驗證：

- normal mode 仍只載入最近 100 個 research cases；
- synthetic mode 載入 `demo_case`；
- synthetic mode 不呼叫 dashboard / latest cases / herbs / interactions / recommendation / similarity API。

本批 Integrated 變更已提交，等待最新 head self-hosted gate，因此本批狀態為：

**IMPLEMENTED — WAITING FOR LATEST SELF-HOSTED VERIFICATION**

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
- [x] PTC Integrated hydration（待 latest gate）；
- [x] 共用 provenance banner；
- [x] CSV schema / duplicate / broken-reference validator；
- [x] CSV row-shape / enum-value validator；
- [ ] PTC Command Center synthetic isolation；
- [ ] multi-route Chromium E2E。

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

1. PTC Command Center synthetic isolation：demo mode 顯示 bundled dataset readiness / provenance，不啟動正式公開資料同步與 complete graph API；
2. multi-route Chromium E2E，覆蓋 Homepage → Recommendation → Clinical Decision → Treatment Plan → Knowledge Graph → PTC Research → PTC Integrated；
3. local CSV import 第一版，採 validate → preview → explicit import，不允許靜默覆寫；
4. pre-upgrade automatic backup hook；
5. traceability persistence E2E；
6. VERSION / CHANGELOG / release checklist 收斂。

## 安全邊界

所有 synthetic demo 輸出只用於研究軟體流程展示，不代表真實醫學證據、患者資料、診斷、臨床決策或治療建議。v1.0 Research-Grade Stable 只描述軟體工程成熟度，不等同臨床有效性驗證。
