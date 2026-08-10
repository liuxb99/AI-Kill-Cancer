# AI-Kill-Cancer v0.3.0 中文進版 Roadmap

更新日期：2026-08-10

## 1. 版本定位

v0.3.0 名稱：**Local-First Research & Demo Showcase**。

本版把現有 Precision Oncology、PTC Research、Recommendation、Clinical Decision、Treatment Plan、Knowledge Graph 與公共資料能力整理為兩個明確運行模式：

- **Vercel Demo Showcase**：bundled synthetic CSV → demo API/UI，僅作公開展示；
- **Local Research Workspace**：本地 SQLite 為主要可持久化工作資料庫。

PostgreSQL 為 Optional Scale-out Backend，不阻塞 v0.3.0。

## 2. Demo Dataset 規格與目前成果

目前 `data/demo/` 已有：

```text
patients.csv                 DONE
cancer_cases.csv             DONE
specimens.csv                DONE
sequencing_tests.csv         DONE
variants.csv                 DONE
drugs.csv                    DONE
publications.csv             DONE
clinical_trials.csv          DONE
evidence.csv                 DONE
```

目前固定 3 個 synthetic PTC showcase case：

- `PTC-DEMO-001`：BRAF V600E；
- `PTC-DEMO-002`：RET fusion；
- `PTC-DEMO-003`：NTRK1 fusion / RAI-refractory showcase。

第二批已把每個病例串到 synthetic Drug / Evidence / Publication / Clinical Trial。所有這些資料都只用於展示 UI、API 與 traceability contract，不代表真實醫學證據或患者治療建議。

## 3. v0.3.0 Epic 進度

### Epic 0 — 文件與版本治理

- [x] 採用 Local-First SQLite + Vercel Demo Showcase。
- [x] CURRENT_STATUS 更新。
- [x] v0.3.0 中文 Roadmap 建立。
- [ ] VERSION / CHANGELOG 與 roadmap 對齊。

### Epic 1 — Demo CSV Dataset

- [x] patients/cases/specimens/sequencing/variants。
- [x] evidence/drugs/publications/trials。
- [x] 固定 demo key 與 synthetic provenance。
- [ ] CSV schema validator。
- [ ] 永久測試：缺欄、重複 key、斷鏈、非法 enum。

### Epic 2 — Demo Bootstrap Runtime

- [x] `DemoDatasetLoader` / bootstrap service。
- [x] deterministic UUIDv5 ID mapping。
- [x] SQLite idempotent bootstrap。
- [x] Vercel demo SQLite bootstrap guard。
- [ ] reset / rebuild demo database command。
- [x] `/api/v1/demo/status`。
- [x] `/api/v1/demo/cases`。

第一批 bootstrap regression 已由 Local Verification Gate #74 驗證 PASS：第一次建立 3 組核心資料，第二次 bootstrap 不重複插入。

### Epic 3 — Demo UI

- [x] 首頁 Demo Case Selector。
- [x] Case Snapshot 基本展示。
- [x] Variant / Evidence / Drug 展示。
- [x] Publication / Clinical Trial 展示。
- [ ] Recommendation / Clinical Decision / Treatment Plan 深連結。
- [ ] Knowledge Graph / Research 頁帶入同一 demo case。
- [ ] Demo provenance banner 跨頁一致。

首頁現在直接呼叫 `/api/v1/demo/cases`，可以切換 BRAF、RET、NTRK1 三個 synthetic showcase case，查看 `Case → Variant → Evidence → Drug → Publication → Trial` 展示鏈。

### Epic 4 — Local SQLite Workspace

- [x] 預設 `data/ai-kill-cancer.db` 路徑能力已存在。
- [x] SQLite schema bootstrap / FK / busy timeout 基礎已存在。
- [ ] local mode 預設啟動設定整理。
- [ ] 本地 CSV import 工作流。
- [ ] restart persistence E2E。
- [ ] `PRAGMA integrity_check` gate。
- [ ] upgrade-before-backup。
- [ ] backup/restore smoke。

### Epic 5 — Traceability Baseline

目標鏈：

```text
patient_id
→ case_id
→ specimen_id
→ sequencing_test_id
→ variant_id
→ evidence_id
→ recommendation_id
→ clinical_decision_id
→ treatment_plan_id
```

目前 Demo Showcase 已先完成前半段展示鏈與固定 demo keys；正式 SQLite domain traceability 仍需在後續批次完成 Evidence → Recommendation → Clinical Decision → Treatment Plan 的持久化 E2E。

### Epic 6 — Release Gate

目前已有：

- [x] Windows self-hosted Local Verification Gate；
- [x] Vercel deploy gate；
- [x] HTTP/API smoke；
- [x] 真實 Chromium browser render；
- [x] console/pageerror/static-asset 驗證；
- [x] demo bootstrap regression；
- [x] demo showcase API contract regression（本批新增，等待最新 gate 完成）；
- [ ] multi-route demo Chromium E2E；
- [ ] SQLite integrity + backup/restore release gate。

## 4. 本批開發摘要

第二批完成：

```text
Synthetic Drug CSV                   IMPLEMENTED
Synthetic Publication CSV            IMPLEMENTED
Synthetic Clinical Trial CSV         IMPLEMENTED
Synthetic Evidence CSV               IMPLEMENTED
/api/v1/demo/status                  IMPLEMENTED
/api/v1/demo/cases                   IMPLEMENTED
Homepage Demo Case Selector           IMPLEMENTED
Case→Variant→Evidence→Drug UI         IMPLEMENTED
Publication/Trial trace UI            IMPLEMENTED
Demo API regression                   IMPLEMENTED
```

狀態：**IMPLEMENTED — WAITING FOR LATEST SELF-HOSTED VERIFICATION**。

## 5. 下一批建議

下一批固定進入 Local SQLite Workspace 與 Demo 深連結：

1. demo case context / route parameter；
2. Recommendation、Clinical Decision、Treatment Plan、Knowledge Graph 帶入同一 demo case；
3. local mode 啟動指令與 workspace status API；
4. SQLite `PRAGMA integrity_check`；
5. restart persistence E2E；
6. backup/restore 第一版；
7. 擴 Chromium E2E 到 demo selector 與核心 route。

## 6. v0.3.0 完成定義

### Vercel Demo Done

1. 首頁立即能看見 synthetic showcase data。
2. 至少 3 個 demo case 可切換。
3. Case → Variant → Evidence → Recommendation → Treatment Plan → Graph 可導航。
4. cold-start 後 demo 可由 bundled CSV 重建。
5. Demo/Synthetic provenance 清楚。
6. 真實 Chromium multi-route E2E 全通。

### Local Workspace Done

1. 首次啟動自動產生本地 SQLite。
2. 可新增／匯入研究資料。
3. 完整核心流程可落庫。
4. 關閉／重啟後資料持續存在。
5. 升級前有備份，restore 可還原。
6. integrity / FK / traceability 全通。

## 7. 後續版本

```text
v0.4.0  Precision Oncology Traceability
v0.5.0  Real Data + Knowledge Graph + AI
v0.6.0  Clinical Research Workbench
v0.7.0  Scientific Validation & Evaluation
v0.8.x  Security / Reliability / Observability Hardening
v0.9.x  Release Candidate / Compatibility / Migration
v1.0.0  Research-Grade Stable
```

## 8. 安全界線

所有示範資料必須為虛構或合成資料；不得使用可識別真實患者資訊。Demo Evidence、Drug、Publication、Clinical Trial、Recommendation 與 Treatment Plan 僅用於展示軟體流程。v1.0 的「Research-Grade Stable」只代表軟體工程成熟度，不代表完成臨床有效性驗證或可取代醫療專業判斷。
