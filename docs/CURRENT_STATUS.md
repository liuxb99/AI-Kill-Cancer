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

目前已支援：

- Homepage Demo Case Selector；
- Recommendation：自動載入同一 demo case / variant；
- Clinical Decision：synthetic decision workflow preview，不查正式 Patient UUID；
- Treatment Plan：synthetic treatment workflow preview，不建立正式計畫；
- Knowledge Graph：由同一 demo case 投影 6 entities / 5 relations；
- 共用 `DemoContextBanner` / `useDemoContext()`，跨頁 synthetic provenance 一致。

## Demo Dataset Validation

`src/backend/demo/validator.py` 現在檢查：

- 九張必要 CSV 是否存在；
- 必要欄位；
- blank key；
- duplicate key；
- Patient → Case → Specimen → Sequencing → Variant → Evidence → Drug / Publication / Trial 斷鏈；
- CSV row shape / 額外欄位，避免欄位右移直到 ORM 才爆炸；
- 重要 variant categorical value domains；
- synthetic `data_mode` 邊界。

`/api/v1/demo/status` 包含 `validation.ok/errors`；`/api/v1/demo/cases` 在資料集 validation fail 時回 503，避免展示半斷鏈資料。

`tests/test_demo_validator.py` 已增加 broken reference、extra CSV field、invalid variant value-domain regression。

## Local SQLite Workspace

已驗證：SQLite file persistence、FK、busy timeout、integrity、backup、atomic restore、restart persistence。

`GET /api/v1/workspace/status` 回報：

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

本批新增 `tests/test_workspace_status.py`，覆蓋：

- local/research SQLite persistent workspace contract；
- demo SQLite ephemeral contract；
- non-SQLite backend contract。

## 本批狀態

第五批新增／修復：

```text
Vercel demo cold-start root-cause fixes           VERIFIED IN PRODUCTION
Production API JSON smoke                         VERIFIED
Demo CSV row-shape validation                     IMPLEMENTED
Demo categorical value-domain validation          IMPLEMENTED
Workspace status regression                       IMPLEMENTED
Validator failure regression                      IMPLEMENTED
```

本批新增的 validator/workspace regression 已提交，等待最新 head 的 self-hosted gate；因此新增項目狀態為：

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
- [x] 共用 provenance banner；
- [x] CSV schema / duplicate / broken-reference validator；
- [x] CSV row-shape / enum-value validator（待 latest gate）；
- [ ] PTC Workbench / Research hydrate；
- [ ] multi-route Chromium E2E。

### Local SQLite
- [x] config / schema bootstrap / FK / busy timeout；
- [x] file persistence；
- [x] integrity utility；
- [x] backup / atomic restore；
- [x] restart regression；
- [x] workspace status API；
- [x] workspace status regression（待 latest gate）；
- [ ] local CSV import；
- [ ] pre-upgrade automatic backup hook；
- [ ] traceability persistence E2E。

## 下一批

優先順序：

1. PTC Workbench / Research demo hydration，讓三個 showcase case 可沿同一 `demo_case` contract 進入研究工作台；
2. multi-route Chromium E2E，覆蓋 Homepage → Recommendation → Clinical Decision → Treatment Plan → Knowledge Graph → PTC Research；
3. local CSV import 第一版，採 validate → preview → explicit import，不允許靜默覆寫；
4. pre-upgrade automatic backup hook；
5. traceability persistence E2E；
6. VERSION / CHANGELOG / release checklist 收斂。

## 安全邊界

所有 synthetic demo 輸出只用於研究軟體流程展示，不代表真實醫學證據、患者資料、診斷、臨床決策或治療建議。v1.0 Research-Grade Stable 只描述軟體工程成熟度，不等同臨床有效性驗證。
