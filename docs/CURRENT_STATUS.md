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
Pre-upgrade SQLite backup hook                     VERIFIED — Local Gate #140 PASS
Traceability Persistence E2E                       IMPLEMENTED
```

## Local CSV Import v1

受控 Local CSV Import 已完成：`validate → preview → explicit import`。只允許 local/research SQLite；commit 必須 `confirm=IMPORT`；deterministic records 採 idempotent insert，禁止 silent overwrite。

## Pre-upgrade automatic backup hook

第十三批已完成並通過 **Local Verification Gate #140**。Persistent Local SQLite 在 schema 擴充前會先比較現有 schema 與 `Base.metadata`；缺 table / column 才觸發 `integrity_check → timestamp backup → backup integrity check → create_all`。Fresh DB、schema identical、`:memory:` 與 Vercel/demo ephemeral SQLite 不備份。

## Traceability Persistence E2E

第十四批新增 `tests/test_traceability_persistence_e2e.py`，使用真實 SQLite file 做完整 restart 驗證，而不是只測單一 table persistence。

測試流程：

```text
init persistent SQLite
→ bootstrap deterministic Patient / Case / Specimen / Sequencing / Variant
→ persist Evidence
→ persist Recommendation + Recommendation Trace + Evidence reference
→ persist Clinical Decision + Decision Trace
→ commit
→ close engine/session factory
→ re-init against same SQLite file
→ query and verify the full chain
```

Restart 後必須保持：

```text
Patient
  ↓
Cancer Case
  ↓
Specimen
  ↓
Sequencing Test
  ↓
Variant
  ↓
Evidence
  ↓
Recommendation + Trace Step + evidence_references
  ↓
Clinical Decision + Decision Trace
```

驗收點包括：

- Case.patient_id 不變；
- Specimen.case_id 不變；
- Sequencing.specimen_id 不變；
- Variant.sequencing_test_id 不變；
- Evidence.variant_id 不變；
- Recommendation.case_id / patient_id 不變；
- Recommendation Trace Step 的 evidence reference 在 restart 後仍可解析；
- Clinical Decision.recommendation_id 不變；
- Decision evidence_summary 與 Decision Trace 關聯均保留。

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
- [x] traceability persistence E2E（latest gate 驗證中）。

## 下一批

優先順序：

1. 驗證 Traceability Persistence E2E latest self-hosted gate；若 fail，依 job log 修到全綠；
2. Local CSV Import v2：duplicate preview + import history；
3. 增加本機 UI / file picker，把 preview / commit 流程接到操作介面；
4. VERSION / CHANGELOG / release checklist 收斂，評估 v0.3.0 milestone closure。

## 安全邊界

所有 synthetic demo 輸出只用於研究軟體流程展示，不代表真實醫學證據、患者資料、診斷、臨床決策或治療建議。v1.0 Research-Grade Stable 只描述軟體工程成熟度，不等同臨床有效性驗證。
