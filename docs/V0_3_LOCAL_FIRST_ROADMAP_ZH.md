# AI-Kill-Cancer v0.3.0 中文進版 Roadmap

更新日期：2026-08-10

## 1. 版本定位

v0.3.0 名稱：**Local-First Research & Demo Showcase**。

本版的核心不是繼續堆疊更多功能，而是把目前已有的 Precision Oncology、PTC Research、Recommendation、Clinical Decision、Treatment Plan、Knowledge Graph 與公共資料能力，整理成兩個清楚、可驗收、用途不同的運行模式。

### 模式 A：Vercel Demo Showcase

用途：公開展示網站功能、UI、完整研究流程與 API 合約。

資料策略：

```text
bundled demo CSV
→ serverless bootstrap
→ /tmp demo SQLite
→ API / UI
```

規則：

1. Demo CSV 是線上展示資料的 Source of Truth。
2. `/tmp` SQLite 僅是 runtime projection，可隨時丟失並由 CSV 重建。
3. 不在 Vercel 儲存正式研究資料。
4. 所有 Demo 病例、推薦、Treatment Plan、Graph 與報告必須標記為 Demo / Synthetic / Research Only。
5. 至少提供 3～5 個具有不同分子特徵的 PTC 示例病例。
6. 網站首頁與核心頁面必須開箱即有可看的資料，不得只有空白 state。

### 模式 B：Local Research Workspace

用途：真正研究使用、資料持久化與本地工作空間。

預設：

```text
APP_MODE=local
DB_BACKEND=sqlite
SQLITE_PATH=data/ai-kill-cancer.db
```

規則：

1. SQLite 是本地主資料庫與權威工作資料來源。
2. 本地病例、variant、evidence、recommendation、clinical decision、treatment plan、graph 等均持久化。
3. 關閉程式、重開電腦、重新啟動服務後資料不得消失。
4. 版本升級前須有 SQLite backup。
5. migration、integrity、FK、restart persistence、backup/restore 都必須納入永久測試。

PostgreSQL 不再是 v0.3.0 必要條件，改列 Optional Scale-out Backend，待多人協作、中央伺服器、高併發或 SaaS 化再啟用。

## 2. Demo Dataset 規格

目錄：

```text
data/demo/
  patients.csv
  cancer_cases.csv
  specimens.csv
  sequencing_tests.csv
  variants.csv
  evidence.csv
  drugs.csv
  publications.csv
  clinical_trials.csv
  README_ZH.md
```

CSV 間必須使用固定 demo key 串聯，不依賴執行時隨機 UUID。bootstrap 時可轉換為 deterministic UUID 或以 mapping table 對應。

### 第一批病例建議

- `PTC-DEMO-001`：BRAF V600E 型 PTC。
- `PTC-DEMO-002`：RET fusion 型 PTC。
- `PTC-DEMO-003`：NTRK fusion / RAI-refractory 展示病例。
- 後續可加入 RAS-like、TERT promoter、高風險復發等案例。

所有資料均為合成展示資料，不代表真實患者，也不得暗示是個案治療建議。

## 3. v0.3.0 開發 Epic

### Epic 0 — 文件與版本治理

- [x] 採用 Local-First SQLite + Vercel Demo Showcase。
- [x] CURRENT_STATUS 更新。
- [x] v0.3.0 中文 Roadmap 建立。
- [ ] VERSION / CHANGELOG 與 roadmap 對齊。

### Epic 1 — Demo CSV Dataset

- [ ] 建立 patients/cases/specimens/sequencing/variants。
- [ ] 建立 evidence/drugs/publications/trials。
- [ ] 固定 demo key 與 provenance。
- [ ] CSV schema validator。
- [ ] 永久測試：缺欄、重複 key、斷鏈、非法 enum。

### Epic 2 — Demo Bootstrap Runtime

- [ ] `DemoDatasetLoader`。
- [ ] deterministic ID mapping。
- [ ] SQLite idempotent bootstrap。
- [ ] Vercel cold-start bootstrap guard。
- [ ] reset / rebuild demo database。
- [ ] `/api/v1/demo/status`。
- [ ] `/api/v1/demo/cases`。

### Epic 3 — Demo UI

- [ ] 首頁 Demo Case Selector。
- [ ] Case Snapshot。
- [ ] Variant / Evidence / Drug 展示。
- [ ] Recommendation / Clinical Decision / Treatment Plan 連結。
- [ ] Knowledge Graph / Research 頁帶入同一 demo case。
- [ ] Demo provenance banner 一致。

### Epic 4 — Local SQLite Workspace

- [ ] 標準資料目錄 `data/`。
- [ ] 預設 `data/ai-kill-cancer.db`。
- [ ] 初次啟動 schema bootstrap。
- [ ] 本地 CSV import。
- [ ] restart persistence E2E。
- [ ] `PRAGMA integrity_check` gate。
- [ ] upgrade-before-backup。
- [ ] backup/restore smoke。

### Epic 5 — Traceability Baseline

需要固定以下鏈：

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

所有衍生結果統一攜帶：

```text
source
provenance
data_mode
version
created_at
created_by/event_id（適用時）
```

### Epic 6 — Release Gate

v0.3.0 不得只靠 HTTP 200 宣告成功。

必須通過：

```text
backend compile/lint/tests
SQLite schema/integrity/persistence
Demo CSV validation/bootstrap
frontend build
API smoke
Chromium browser render
core route E2E
console fatal error = 0
JS/CSS bad response = 0
backup/restore smoke
```

## 4. v0.3.0 完成定義

### Vercel Demo Done

1. 開啟首頁立即能看見示範資料。
2. 至少 3 個 demo case 可選。
3. Case → Variant → Evidence → Recommendation → Treatment Plan → Graph 可導航。
4. redeploy / cold-start 後 demo 可自行重建。
5. Demo/Synthetic provenance 清楚。
6. 真實 Chromium E2E 全通。

### Local Workspace Done

1. 首次啟動自動產生本地 SQLite。
2. 可新增／匯入研究資料。
3. 完整核心流程可落庫。
4. 關閉／重啟後資料持續存在。
5. 升級前有備份。
6. restore 可還原。
7. integrity / FK / traceability 全通。

## 5. 後續版本

```text
v0.4.0  Precision Oncology Traceability
v0.5.0  Real Data + Knowledge Graph + AI
v0.6.0  Clinical Research Workbench
v0.7.0  Scientific Validation & Evaluation
v0.8.x  Security / Reliability / Observability Hardening
v0.9.x  Release Candidate / Compatibility / Migration
v1.0.0  Research-Grade Stable
```

## 6. 安全界線

所有示範資料必須為虛構或合成資料；不得使用可識別真實患者資訊。Demo 推薦與 Treatment Plan 僅用於展示軟體流程。v1.0 的「Research-Grade Stable」只代表軟體工程成熟度，不代表完成臨床有效性驗證或可取代醫療專業判斷。
