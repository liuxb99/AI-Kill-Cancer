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
Local CSV Import v2                               IMPLEMENTED
```

## Local CSV Import v1

受控 Local CSV Import 已完成：`validate → preview → explicit import`。只允許 local/research SQLite；commit 必須 `confirm=IMPORT`；deterministic records 採 idempotent insert，禁止 silent overwrite。

## Traceability Persistence E2E

第十四批已通過 **Local Verification Gate #142**。真實 SQLite file 經 `close_db()` / `init_db()` restart 後，Patient → Case → Specimen → Sequencing → Variant → Evidence → Recommendation/Trace → Clinical Decision/Trace 全鏈保持可追溯。

## Local CSV Import v2

第十五批新增兩個核心能力：**duplicate preview** 與 **persistent import history**。

Preview 現在除了 validator/counts，也會把 deterministic UUID 對應到目前 workspace，逐類回報：

```text
patients
cancer_cases
specimens
sequencing_tests
variants
```

每類包含：

```text
total
existing
new
existing_keys[]
new_keys[]
```

因此使用者在按下真正 import 前，就能明確知道哪些資料會新增、哪些因 deterministic identity 已存在而跳過。Import policy 仍維持 `overwrite_existing=false`。

新增 history API：

```text
GET /api/v1/workspace/import/history?limit=50
```

每次 confirmed import 都會 append 到與 SQLite workspace 同目錄的：

```text
import-history.jsonl
```

history entry 保存：

- UTC timestamp；
- source_dir；
- validation result；
- duplicate preview snapshot；
- actual imported counts；
- overwrite_existing=false；
- app_mode；
- database_path。

`GET /api/v1/workspace/status` 也新增 `import_history_path`，讓本機 UI 可直接顯示 workspace audit location。

`tests/test_workspace_status.py` 已擴充 regression：

- preview 回報 existing/new；
- confirmed import 保留 duplicate snapshot；
- commit 寫入 JSONL history；
- history endpoint 可讀回最新紀錄；
- malformed history line 被安全忽略；
- history limit 生效；
- 原 v1 explicit confirmation / no-overwrite contract 保留。

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
- [x] duplicate-aware CSV preview（latest gate 驗證中）；
- [x] import history JSONL / API（latest gate 驗證中）。

## 下一批

優先順序：

1. 驗證 Local CSV Import v2 latest self-hosted gate；若 fail，依 job log 修到全綠；
2. 增加本機 Workspace Import UI：directory path、Validate/Preview、duplicate summary、explicit Import、history viewer；
3. 對 Import UI 補 frontend regression / local-mode guard；
4. VERSION / CHANGELOG / release checklist 收斂，評估 v0.3.0 milestone closure。

## 安全邊界

所有 synthetic demo 輸出只用於研究軟體流程展示，不代表真實醫學證據、患者資料、診斷、臨床決策或治療建議。v1.0 Research-Grade Stable 只描述軟體工程成熟度，不等同臨床有效性驗證。
