# Current Status

更新日期：2026-08-10

AI-Kill-Cancer 當前主線：**v0.3.0 — Local-First Research & Demo Showcase**。

架構政策：Local SQLite 是主要持久化研究工作資料庫；Vercel 使用 bundled synthetic CSV + ephemeral demo runtime；PostgreSQL 是 Optional Scale-out Backend。

## 已驗證底座

```text
Local SQLite runtime / ORM compatibility          VERIFIED
SQLite file persistence / FK / memory regression  VERIFIED
Vercel Python/static routing                      VERIFIED
Production page/API JSON smoke                    VERIFIED — commit 9fe8103
Demo cold-start bootstrap                         VERIFIED — production API smoke PASS
Demo core CSV bootstrap + UUIDv5 idempotency      VERIFIED — Local Gate #74 PASS
Demo deep-link / Recommendation hydration         VERIFIED — Local Gate #90 PASS
SQLite integrity / backup / restore               VERIFIED — Local Gate #90 PASS
Restart persistence regression                    VERIFIED — Local Gate #90 PASS
```

2026-08-10 production incident 已完成根因修復：demo cold-start 曾因 `cancer_cases.csv` JSON/CSV quoting 與 fusion variant 欄位錯位而失敗，導致 DB API 500/503。修正後 Vercel production deploy、page smoke 與 DB/API JSON smoke 已通過，`/api/v1/ptc-data-quality/overview` 已恢復。

## Demo Showcase 現況

九張 synthetic CSV 與三個固定 PTC showcase case 已完成。`/api/v1/demo/status` 與 `/api/v1/demo/cases` 已存在。

跨頁 contract：

```text
demo_case=<PTC-DEMO-xxx>&data_mode=synthetic
```

目前已支援：Homepage Demo Case Selector、Recommendation、Clinical Decision、Treatment Plan、Knowledge Graph，以及 PTC Research 工作台 synthetic hydration。所有頁面沿用 `DemoContextBanner` / `useDemoContext()`，保持 synthetic provenance 一致。

PTC Research 在 synthetic mode 下不再誤查研究資料庫，而是直接投影同一 demo case 的 Case、Variant、Evidence、Drug、Publication、Clinical Trial；沒有 `demo_case` 時仍保留原本公開研究資料查詢路徑。

## Demo Dataset Validation

`src/backend/demo/validator.py` 現在檢查九張必要 CSV、必要欄位、blank/duplicate key、跨表斷鏈、CSV row shape / 額外欄位、重要 categorical value domains 與 synthetic `data_mode` 邊界。

`/api/v1/demo/status` 包含 `validation.ok/errors`；`/api/v1/demo/cases` 在資料集 validation fail 時回 503，避免展示半斷鏈資料。

`tests/test_demo_validator.py` 已覆蓋 broken reference、extra CSV field、invalid variant value-domain regression。

## Local SQLite Workspace

已驗證 SQLite file persistence、FK、busy timeout、integrity、backup、atomic restore、restart persistence。`GET /api/v1/workspace/status` 回報 app mode、backend、local-first/persistent、database path、size、integrity 與 backup directory。

`tests/test_workspace_status.py` 覆蓋 local/research SQLite persistent、demo SQLite ephemeral 與 non-SQLite backend contract。

## 本批狀態

第六批新增：

```text
PTC Research synthetic hydration                  IMPLEMENTED
Synthetic Case → Variant → Evidence projection    IMPLEMENTED
Synthetic Drug / Publication / Trial projection   IMPLEMENTED
Research DB / synthetic mode isolation            IMPLEMENTED
PTC Research frontend regression                  IMPLEMENTED
```

新增 `src/frontend/src/test/PTCResearchPage.test.tsx`：驗證帶 `demo_case` 時載入 synthetic context 且不呼叫 `listPTCCases/getPTCGraphPath`；沒有 demo context 時仍走既有 research database path。

本批已提交，等待 latest self-hosted gate，因此狀態為：

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
- [x] PTC Research hydration（待 latest gate）；
- [x] 共用 provenance banner；
- [x] CSV schema / duplicate / broken-reference validator；
- [x] CSV row-shape / enum-value validator；
- [ ] PTC Workbench 其餘入口 hydration；
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

1. 把 synthetic `demo_case` contract 延伸到 PTC Workbench 其餘主要入口，避免 demo showcase 在進入 command/integrated workflow 後掉回空資料；
2. multi-route Chromium E2E，覆蓋 Homepage → Recommendation → Clinical Decision → Treatment Plan → Knowledge Graph → PTC Research；
3. local CSV import 第一版，採 validate → preview → explicit import，不允許靜默覆寫；
4. pre-upgrade automatic backup hook；
5. traceability persistence E2E；
6. VERSION / CHANGELOG / release checklist 收斂。

## 安全邊界

所有 synthetic demo 輸出只用於研究軟體流程展示，不代表真實醫學證據、患者資料、診斷、臨床決策或治療建議。v1.0 Research-Grade Stable 只描述軟體工程成熟度，不等同臨床有效性驗證。
