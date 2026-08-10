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
SQLite integrity / backup / restore               VERIFIED
Restart persistence regression                    VERIFIED
```

## Production multi-route gate 實際發現

第十批新增的 production gate 已真正發揮作用。Local Verification #127 成功，但 Vercel Production run #123 失敗；失敗發生在 browser verification 之前的 `/api/v1/demo/cases` API smoke，而不是首頁、health、PTC readiness、completion 或 data-quality。

Production 回報兩類 demo dataset contract 錯誤：

```text
publications.csv CSV quoting / extra fields
evidence.csv demo_variant_key 與 variants.csv 不一致
```

這代表之前的 demo cold-start / API smoke 雖能驗證核心五張 bootstrap CSV，但九張 showcase CSV 的完整關聯仍存在資料契約缺口。新 gate 已把這個缺口從 production 中攔下。

## 本批修復

第十一批已修正：

```text
publications.csv RFC4180 JSON quoting              FIXED
drugs.csv RFC4180 JSON quoting                     FIXED
clinical_trials.csv RFC4180 JSON quoting           FIXED
evidence → variants foreign-key contract           FIXED
JSON-list field validation                         IMPLEMENTED
Malformed JSON-list regression                     IMPLEMENTED
```

`evidence.csv` 現在使用 `VAR-DEMO-001/002/003`，與 `variants.csv.demo_variant_key` 完全一致。

為避免同類問題再次只在 Vercel 才暴露，`src/backend/demo/validator.py` 現在除了 schema、row-shape、enum domain 與 cross-file reference 外，也會對以下 CSV 欄位做真正 `json.loads()` + list type 驗證：

```text
cancer_cases.csv:
  metastatic_sites
  treatment_history
  current_medications

drugs.csv:
  atc_codes

publications.csv:
  authors
  keywords

clinical_trials.csv:
  conditions
  interventions
  biomarkers
  locations
```

`tests/test_demo_validator.py` 同步新增 malformed JSON list regression。

本批狀態：

**FIXED / IMPLEMENTED — WAITING FOR LATEST SELF-HOSTED + PRODUCTION GATE**

## Demo Showcase 現況

九張 synthetic CSV 與三個固定 PTC showcase case已建立。跨頁 contract：

```text
demo_case=<PTC-DEMO-xxx>&data_mode=synthetic
```

目前已支援 Homepage、Recommendation、Clinical Decision、Treatment Plan、Knowledge Graph、PTC Research、PTC Integrated Workbench、PTC Command Center，以及 synthetic navbar query propagation。

Production multi-route gate 會在 `/api/v1/demo/status`、`/api/v1/demo/cases` 通過後，以 Chromium 真正驗證：

```text
/recommendation
/clinical-decision
/treatment-plans
/clinical-graph
/ptc-research
/ptc-workbench
/ptc-command-center
```

並檢查白屏、query continuity、synthetic context、pageerror 與 JS/CSS bad responses。

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
- [x] Production multi-route E2E gate implemented；
- [ ] Production multi-route E2E latest run PASS。

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

1. 让 latest self-hosted gate + production API/demo + Chromium multi-route gate 全綠；若仍 fail，依精確 route/report 立即修復；
2. Local CSV Import v1：`validate → preview → explicit import`，禁止 silent overwrite；
3. pre-upgrade automatic backup hook；
4. traceability persistence E2E；
5. VERSION / CHANGELOG / release checklist 收斂。

## 安全邊界

所有 synthetic demo 輸出只用於研究軟體流程展示，不代表真實醫學證據、患者資料、診斷、臨床決策或治療建議。v1.0 Research-Grade Stable 只描述軟體工程成熟度，不等同臨床有效性驗證。
