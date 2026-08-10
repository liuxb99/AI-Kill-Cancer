# Current Status

更新日期：2026-08-10

AI-Kill-Cancer 已進入版本化推進階段。現行架構正式採用 **Local-First SQLite + Vercel Demo Showcase**：

- 本地 SQLite 是主要可用、可持久化、可累積研究資料的工作資料庫；
- Vercel 僅作線上展示與部署驗證，使用 bundled synthetic CSV；
- Vercel `/tmp` SQLite 只作 runtime projection，不承擔正式資料持久化；
- PostgreSQL 是 Optional Scale-out Backend，不阻塞目前版本主線。

## 當前版本

```text
v0.3.0 — Local-First Research & Demo Showcase
```

## v0.3.0 目前完成度

### 已驗證底座

```text
Local SQLite runtime / ORM compatibility          VERIFIED
SQLite file persistence / FK / memory regression  VERIFIED
Vercel Python API routing                         VERIFIED
Vercel static asset filesystem-first routing      VERIFIED
Production page/API smoke                         VERIFIED
Production Chromium browser render                VERIFIED
Demo core CSV → SQLite bootstrap                  VERIFIED — Local Gate #74 PASS
Demo deterministic UUIDv5 / idempotent reload     VERIFIED — Local Gate #74 PASS
```

### Demo Showcase 第一批

已完成：

```text
data/demo/patients.csv
data/demo/cancer_cases.csv
data/demo/specimens.csv
data/demo/sequencing_tests.csv
data/demo/variants.csv
```

3 個固定 synthetic PTC 病例：

- BRAF V600E；
- RET fusion；
- NTRK1 fusion / RAI-refractory showcase。

### Demo Showcase 第二批

本批新增：

```text
data/demo/drugs.csv
data/demo/publications.csv
data/demo/clinical_trials.csv
data/demo/evidence.csv
/api/v1/demo/status
/api/v1/demo/cases
Homepage Demo Case Selector
Case → Variant → Evidence → Drug UI
Publication / Clinical Trial trace UI
Demo showcase API regression tests
```

首頁現在會直接讀 `/api/v1/demo/cases`，可切換三個 synthetic case，展示：

```text
Case
→ Variant
→ Evidence
→ Drug
→ Publication
→ Clinical Trial
```

所有新增 Evidence / Drug / Publication / Trial 都是 **synthetic demo data**，只用來展示軟體流程與資料契約，不代表真實醫學證據或患者治療建議。

第二批狀態：

```text
IMPLEMENTED — WAITING FOR LATEST SELF-HOSTED VERIFICATION
```

## Database runtime policy

```text
Local SQLite
→ 主要／權威工作資料庫
→ local research workspace
→ 正式研究資料持久化

Vercel Demo SQLite (/tmp)
→ synthetic CSV runtime projection
→ ephemeral
→ 可從 bundled CSV 重建

PostgreSQL
→ Optional Scale-out Backend
→ 未來多人協作、中央 Server、高併發或 SaaS 化再啟用
```

## Vercel 線上狀態

正式 alias：`https://ai-kill-cancer-zqpi.vercel.app`

目前永久 deployment gate 已包含：

```text
verified SHA only
→ deploy canonical alias
→ production page smoke
→ API JSON smoke
→ Playwright/Chromium render
→ React root / body text verification
→ console error / pageerror capture
→ JS/CSS bad-response check
→ screenshot / browser report artifact
```

此前白屏根因為 SPA catch-all 把 `/assets/*.js` rewrite 成 `/index.html`；已修成 filesystem-first，Chromium 已驗證正常 render。

## v0.3.0 Acceptance Gate 進度

### Vercel Demo

- [x] 標準 core demo CSV dataset；
- [x] Evidence / Drug / Publication / Trial synthetic CSV；
- [x] 3 個固定可切換 demo cases；
- [x] CSV → SQLite idempotent bootstrap；
- [x] `/api/v1/demo/status`；
- [x] `/api/v1/demo/cases`；
- [x] 首頁 Demo Case Selector；
- [x] Variant / Evidence / Drug / Publication / Trial 基本展示；
- [ ] Recommendation / Clinical Decision / Treatment Plan 深連結；
- [ ] Knowledge Graph / Research 頁共用 demo case context；
- [ ] multi-route Chromium E2E；
- [ ] CSV schema / broken-link validator。

### Local SQLite

- [x] `DB_BACKEND=sqlite` / `SQLITE_PATH`；
- [x] `data/ai-kill-cancer.db` 預設路徑能力；
- [x] schema bootstrap；
- [x] FK + busy timeout；
- [x] file persistence regression；
- [ ] local mode 啟動與 workspace status；
- [ ] 本地 CSV import；
- [ ] restart persistence E2E；
- [ ] `PRAGMA integrity_check` gate；
- [ ] upgrade-before-backup；
- [ ] backup/restore smoke；
- [ ]完整 traceability persistence E2E。

## 下一批

下一批進入兩條主線：

1. **Demo 深連結**：建立 demo case context，讓 Recommendation、Clinical Decision、Treatment Plan、Knowledge Graph、Research 共用同一病例；
2. **Local SQLite Workspace Hardening**：workspace status、integrity check、restart persistence、backup/restore 第一版。

## 版本路線

```text
v0.3.0  Local-First Research & Demo Showcase
v0.4.0  Precision Oncology Traceability
v0.5.0  Real Data + Knowledge Graph + AI
v0.6.0  Clinical Research Workbench
v0.7.0  Scientific Validation & Evaluation
v0.8.x  Security / Reliability / Observability Hardening
v0.9.x  Release Candidate / Compatibility / Migration
v1.0.0  Research-Grade Stable
```

## 安全邊界

本項目屬於研究與臨床決策輔助軟體工程項目。任何推薦、治療計畫、風險評估與 synthetic demo 輸出均不得替代合格醫療專業人員的診斷與治療決策。Demo、真實公共研究資料與本地使用者資料必須有明確 provenance；軟體完成度與醫學有效性必須分開評價。
