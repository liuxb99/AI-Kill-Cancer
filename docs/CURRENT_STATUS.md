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
Local CSV Import v1                               IMPLEMENTED
Pre-upgrade SQLite backup hook                     IMPLEMENTED
```

## Production multi-route gate

Production synthetic browser gate 已完成實戰驗證。九張 showcase CSV contract 修復後，commit `18c357f` 對應 **Vercel Production workflow #130 completed / success**。API smoke 與 Chromium multi-route 均已全綠。

## Local CSV Import v1

第十二批已完成受控 Local CSV Import：

```text
POST /api/v1/workspace/import/csv/preview
POST /api/v1/workspace/import/csv/commit
```

契約維持：`validate → preview → explicit import`；只允許 local/research SQLite；commit 必須 `confirm=IMPORT`；deterministic records 採 idempotent insert，禁止 silent overwrite。

Local Verification Gate #137 已由最新 master 觸發；進度文檔更新時仍在執行中，因此不把尚未完成的 run 宣告為 PASS。

## Pre-upgrade automatic backup hook

第十三批新增 persistent Local SQLite 的 schema-change 防護。

`src/backend/database/session.py` 在 ORM `create_all()` 前會先檢查現有 SQLite schema 與 `Base.metadata`：

```text
existing database empty                 → fresh bootstrap，不備份
schema identical                        → 不備份
expected table missing                  → upgrade_required
expected column missing                 → upgrade_required
```

當 `upgrade_required=true` 且 `APP_MODE=local|research` 時，啟動流程會在 schema mutation 前呼叫既有 `backup_sqlite_database()`：

```text
integrity_check(source)
→ timestamped online SQLite backup
→ integrity_check(backup)
→ create_all / schema bootstrap
```

因此現在 local research workspace 的 schema 擴充不再直接碰原始 DB；先留下可恢復 snapshot。Demo/Vercel ephemeral SQLite、`:memory:` SQLite、全新空資料庫均不產生無意義備份。

`tests/test_sqlite_workspace.py` 新增 regression：

- identical schema 不觸發 upgrade；
- missing column 觸發 upgrade；
- missing table 觸發 upgrade；
- fresh/empty DB 不要求 pre-upgrade backup；
- 原有 integrity / backup / restore / restart persistence regression 保留。

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
- [x] local CSV import v1（latest gate 驗證中）；
- [x] pre-upgrade automatic backup hook（latest gate 驗證中）；
- [ ] traceability persistence E2E。

## 下一批

優先順序：

1. 驗證第十三批 self-hosted gate；若 fail，依 job log 修到全綠；
2. traceability persistence E2E：跨 process/database restart 驗證 Case → Specimen → Sequencing → Variant → Evidence / Recommendation / Decision chain；
3. Local CSV Import v2：duplicate preview、import history，再評估 UI / file picker；
4. VERSION / CHANGELOG / release checklist 收斂。

## 安全邊界

所有 synthetic demo 輸出只用於研究軟體流程展示，不代表真實醫學證據、患者資料、診斷、臨床決策或治療建議。v1.0 Research-Grade Stable 只描述軟體工程成熟度，不等同臨床有效性驗證。
