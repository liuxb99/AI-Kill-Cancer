# AI-Kill-Cancer v0.3.0 中文進版 Roadmap

更新日期：2026-08-10

## 1. 版本定位

v0.3.0：**Local-First Research & Demo Showcase**。Vercel 使用 bundled synthetic CSV 作公開展示；Local Research Workspace 使用持久化 SQLite。PostgreSQL 保留為 Optional Scale-out Backend。

## 2. Demo Dataset

`data/demo/` 九張 CSV 已完成：patients、cancer_cases、specimens、sequencing_tests、variants、drugs、publications、clinical_trials、evidence。固定三個 synthetic PTC showcase：BRAF V600E、RET fusion、NTRK1 fusion / RAI-refractory。

## 3. Epic 進度

### Epic 0 — 文件與版本治理
- [x] Local-First SQLite + Vercel Demo Showcase。
- [x] CURRENT_STATUS / v0.3.0 Roadmap。
- [ ] VERSION / CHANGELOG 對齊。

### Epic 1 — Demo CSV Dataset
- [x] 九張標準 synthetic CSV。
- [x] 固定 demo key / provenance。
- [x] CSV schema / duplicate-key / broken-reference validator。
- [ ] enum/value-domain validator 擴充。

### Epic 2 — Demo Bootstrap Runtime
- [x] bootstrap service / deterministic UUIDv5 / idempotent SQLite bootstrap。
- [x] Vercel demo bootstrap guard。
- [x] `/api/v1/demo/status`，現在包含 validation.ok/errors。
- [x] `/api/v1/demo/cases`，資料集驗證失敗時拒絕提供 showcase payload。
- [ ] reset / rebuild command。

### Epic 3 — Demo UI / Context
- [x] Homepage Demo Case Selector。
- [x] Case → Variant → Evidence → Drug → Publication → Trial 展示。
- [x] `demo_case` + `data_mode=synthetic` deep-link contract。
- [x] 共用 `DemoContextBanner` + `useDemoContext()`。
- [x] Recommendation hydrate 同一 demo case。
- [x] Clinical Decision hydrate 同一 demo case，僅展示 synthetic decision workflow preview，不冒充正式 Patient UUID。
- [x] Treatment Plan hydrate 同一 demo case，僅展示 synthetic treatment workflow preview，不寫入正式計畫。
- [x] Knowledge Graph hydrate 同一 demo case，由 CSV 投影 6 entities / 5 relations synthetic graph。
- [ ] PTC Workbench / Research 頁完整 hydrate 同一 context。
- [ ] multi-route Chromium E2E。

### Epic 4 — Local SQLite Workspace
- [x] `data/ai-kill-cancer.db` 預設路徑能力。
- [x] schema bootstrap / FK / busy timeout / file persistence。
- [x] `PRAGMA integrity_check` utility。
- [x] verified SQLite backup / atomic restore。
- [x] restart persistence + backup/restore regression。
- [x] `/api/v1/workspace/status`：回報 app mode、backend、persistent、DB path、size、integrity、backup directory。
- [ ] local CSV import 工作流。
- [ ] upgrade 流程自動 pre-upgrade backup。
- [ ] 將 workspace status / integrity / backup smoke 接入 release gate。

### Epic 5 — Traceability Baseline
Demo context 已能保持同一 `demo_case` 穿越 Recommendation / Clinical Decision / Treatment Plan / Knowledge Graph，且 synthetic provenance 不再遺失。正式 domain persistence E2E 仍待後續批次。

### Epic 6 — Release Gate
- [x] Windows self-hosted Local Verification Gate。
- [x] Vercel deploy + API smoke + Chromium render。
- [x] Demo bootstrap regression。
- [x] Demo API contract regression。
- [x] SQLite integrity / backup / restore regression — **Local Gate #90 PASS**。
- [x] Demo deep-link / Recommendation hydration — **Local Gate #90 PASS**。
- [x] Demo CSV validator regression 已加入，等待最新 gate。
- [ ] multi-route demo Chromium E2E。
- [ ] pre-upgrade backup release gate。

## 4. 驗證紀錄

Local Verification Gate #90，head `899e143f...`：**PASS**。

因此上一批正式升格 VERIFIED：

```text
Homepage demo deep-link contract                 VERIFIED
Recommendation demo_case hydration               VERIFIED
SQLite PRAGMA integrity utility                  VERIFIED
SQLite verified backup / atomic restore          VERIFIED
Restart persistence regression                   VERIFIED
```

## 5. 本批開發摘要

第四批完成：

```text
Shared DemoContextBanner/useDemoContext          IMPLEMENTED
Clinical Decision synthetic hydration            IMPLEMENTED
Treatment Plan synthetic hydration               IMPLEMENTED
Knowledge Graph synthetic projection             IMPLEMENTED
Demo CSV schema/reference validator              IMPLEMENTED
Demo status validation contract                  IMPLEMENTED
/api/v1/workspace/status                         IMPLEMENTED
Demo validator regression                        IMPLEMENTED
```

狀態：**IMPLEMENTED — WAITING FOR LATEST SELF-HOSTED VERIFICATION**。

## 6. 下一批

1. PTC Workbench / Research hydrate `demo_case`；
2. workspace status regression；
3. pre-upgrade backup hook / command；
4. local CSV import 第一版；
5. enum/value-domain validator；
6. multi-route Chromium E2E 驗證首頁 → Recommendation → Clinical Decision → Treatment Plan → Graph；
7. VERSION / CHANGELOG / v0.3.0 release checklist。

## 7. 安全界線

所有 demo 病例、Evidence、Drug、Publication、Clinical Trial、Recommendation、Clinical Decision 與 Treatment Plan 都是 synthetic / research-only 展示資料。Demo 頁不得把 synthetic preview 宣稱為真實診斷、臨床決策或治療計畫。
