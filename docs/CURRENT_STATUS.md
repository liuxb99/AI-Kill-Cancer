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
```

## Production multi-route gate

第十批加入的 production gate 已完成實戰驗證。第一次 run #123 因 `/api/v1/demo/cases` 發現 publications CSV quoting 與 evidence→variant key 斷鏈而失敗；第十一批修正九張 showcase CSV contract 並擴充 JSON-list validator 後，最新 commit `18c357f` 對應 **Vercel Production workflow #130 已 completed / success**。

因此目前 production gate 已實際驗證：

```text
/api/v1/health
/api/v1/ptc-readiness
/api/v1/ptc-completion/status
/api/v1/ptc-data-quality/overview
/api/v1/demo/status
/api/v1/demo/cases
```

以及 Chromium synthetic multi-route：

```text
/recommendation
/clinical-decision
/treatment-plans
/clinical-graph
/ptc-research
/ptc-workbench
/ptc-command-center
```

## Local CSV Import v1

第十二批已實作第一版 **Local CSV Import**，定位是本機 research workspace 的受控資料匯入入口，不提供 Vercel/demo runtime 寫入。

API：

```text
POST /api/v1/workspace/import/csv/preview
POST /api/v1/workspace/import/csv/commit
```

request：

```json
{
  "source_dir": "D:/research/ptc-dataset"
}
```

commit 必須顯式提交：

```json
{
  "source_dir": "D:/research/ptc-dataset",
  "confirm": "IMPORT"
}
```

安全契約：

- 只允許 `DB_BACKEND=sqlite`；
- 只允許 `APP_MODE=local|research`；
- preview 僅執行 validator，不寫資料庫；
- validation fail 時 commit 回 422；
- 未提供 `confirm=IMPORT` 時 commit 回 409；
- v1 import scope：Patient → Cancer Case → Specimen → Sequencing Test → Variant；
- 使用 deterministic UUIDv5 / idempotent bootstrap；
- existing deterministic records 保留，不 silent overwrite；
- response 明確回報 `overwrite_existing=false`。

`tests/test_workspace_status.py` 已新增 regression，覆蓋：

- demo/non-persistent mode 禁止 local CSV import；
- preview validation 不寫庫；
- explicit confirmation guard；
- confirmed commit 呼叫 idempotent bootstrap；
- overwrite contract 固定為 false。

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
- [x] local CSV import v1（待 latest gate）；
- [ ] pre-upgrade automatic backup hook；
- [ ] traceability persistence E2E。

## 下一批

優先順序：

1. 驗證 Local CSV Import v1 最新 self-hosted gate；若 fail 直接修到全綠；
2. pre-upgrade automatic backup hook：任何 schema/migration/upgrade 前先建立帶 timestamp 的 SQLite backup；
3. traceability persistence E2E：跨 restart 驗證 Case → Variant → Evidence / Recommendation / Decision chain；
4. Local CSV Import v2：增加 UI / file picker、duplicate preview、import history；
5. VERSION / CHANGELOG / release checklist 收斂。

## 安全邊界

所有 synthetic demo 輸出只用於研究軟體流程展示，不代表真實醫學證據、患者資料、診斷、臨床決策或治療建議。v1.0 Research-Grade Stable 只描述軟體工程成熟度，不等同臨床有效性驗證。
