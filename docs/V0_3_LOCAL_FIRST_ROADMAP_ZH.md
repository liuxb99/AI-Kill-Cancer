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
- [ ] CSV schema / broken-link / enum validator。

### Epic 2 — Demo Bootstrap Runtime
- [x] bootstrap service。
- [x] deterministic UUIDv5。
- [x] idempotent SQLite bootstrap。
- [x] Vercel demo bootstrap guard。
- [x] `/api/v1/demo/status`。
- [x] `/api/v1/demo/cases`。
- [ ] reset / rebuild command。

第一批 bootstrap regression 已由 Local Verification Gate #74 PASS。

### Epic 3 — Demo UI / Context
- [x] Homepage Demo Case Selector。
- [x] Case → Variant → Evidence → Drug → Publication → Trial 展示。
- [x] `demo_case` + `data_mode=synthetic` deep-link contract。
- [x] 首頁 Recommendation / Clinical Decision / Treatment Plan / Knowledge Graph / PTC Workbench 深連結入口。
- [x] Recommendation 頁可由 `demo_case` 自動載入 synthetic case 與 variant，並顯示 provenance banner。
- [ ] Clinical Decision / Treatment Plan / Knowledge Graph 各頁完整 hydrate 同一 demo context。
- [ ] Demo provenance banner 抽成跨頁共用元件。
- [ ] multi-route Chromium E2E。

### Epic 4 — Local SQLite Workspace
- [x] `data/ai-kill-cancer.db` 預設路徑能力。
- [x] schema bootstrap / FK / busy timeout。
- [x] file persistence 基礎 regression。
- [x] `PRAGMA integrity_check` utility。
- [x] timestamped SQLite backup utility，備份前後均做 integrity gate。
- [x] atomic restore utility，restore 前驗證 backup、replace 前驗證 staging DB。
- [x] restart persistence + backup/restore regression 第一版。
- [ ] local mode workspace status API / CLI。
- [ ] 本地 CSV import 工作流。
- [ ] upgrade 流程自動呼叫 pre-upgrade backup。
- [ ] 將 integrity + backup/restore 納入正式 release gate。

### Epic 5 — Traceability Baseline
目標仍為 patient → case → specimen → sequencing → variant → evidence → recommendation → clinical decision → treatment plan。Demo 已建立跨頁 `demo_case` context；正式 domain persistence E2E 尚待後續批次。

### Epic 6 — Release Gate
- [x] Windows self-hosted Local Verification Gate。
- [x] Vercel deploy + API smoke + Chromium render。
- [x] demo bootstrap regression。
- [x] demo showcase API contract regression。
- [x] SQLite workspace integrity / backup / restore regression 已加入測試套件，等待最新 gate 驗證。
- [ ] multi-route demo Chromium E2E。
- [ ] CSV validator gate。
- [ ] pre-upgrade backup release gate。

## 4. 本批開發摘要

第三批完成：

```text
Homepage demo deep-link contract                 IMPLEMENTED
Recommendation demo_case hydration               IMPLEMENTED
Synthetic provenance banner on Recommendation    IMPLEMENTED
SQLite PRAGMA integrity utility                  IMPLEMENTED
SQLite verified backup utility                   IMPLEMENTED
SQLite atomic restore utility                    IMPLEMENTED
Restart persistence regression                   IMPLEMENTED
Backup / restore regression                      IMPLEMENTED
```

上一批最新 Local Verification Gate #84 仍顯示 pending，沒有 runner job；因此上一批與本批新增項目均不得標記 VERIFIED，狀態維持 **IMPLEMENTED — WAITING FOR SELF-HOSTED VERIFICATION**。

## 5. 下一批

1. Clinical Decision / Treatment Plan / Knowledge Graph hydrate `demo_case`；
2. 共用 `DemoContextBanner` / route helper，避免各頁重複邏輯；
3. local workspace status API / CLI；
4. pre-upgrade backup hook；
5. CSV schema + referential validator；
6. multi-route Chromium E2E；
7. gate 通過後再更新 VERIFIED 狀態。

## 6. v0.3.0 完成定義

Vercel Demo 必須可從首頁固定病例一路導航到 Evidence / Recommendation / Treatment Plan / Graph，且 synthetic provenance 跨頁不丟失；Local Workspace 必須能持久化、restart 後存在、integrity PASS、upgrade 前備份並可 restore。

## 7. 安全界線

所有 demo 病例、Evidence、Drug、Publication、Clinical Trial、Recommendation 與 Treatment Plan 均為 synthetic / research-only 展示資料，不代表真實患者或臨床有效性；軟體工程成熟度與醫學有效性必須分開評價。
