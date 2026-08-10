# AI Kill Cancer

甲狀腺癌 Precision Oncology 研究平台：管理病例、檢體與分子檢測資料，整理變異、證據、候選藥物、臨床試驗與可追溯決策鏈。

> ⚠️ **重要聲明：本專案是研究型軟體，不是醫療產品。**
> 系統輸出不構成診斷、處方、停藥、換藥、劑量或治療建議。任何臨床決策必須由合格醫療專業人員依完整臨床資料判斷。

## 目前版本

- Product release candidate：**1.0.3**
- Engineering milestone：**Local-First Research & Demo Showcase（roadmap 代號 v0.3.0）**
- Product version authority：root `VERSION` + backend `Settings.APP_VERSION`

> roadmap 代號 v0.3.0 不是產品 SemVer，不再拿來覆蓋既有 1.x release line。

## 架構主線

```text
Local / Research
  persistent SQLite workspace
  → integrity / backup / restore
  → controlled CSV import
  → Case / Variant / Evidence / Recommendation / Decision traceability

Vercel Demo
  bundled synthetic CSV
  → ephemeral SQLite cold-start bootstrap
  → synthetic demo_case deep-link
  → multi-route showcase

Optional Scale-out
  PostgreSQL / external research integrations
```

Local SQLite 是目前主要持久化研究工作資料庫；Vercel 僅作 synthetic showcase，不保存正式研究工作資料。

## 已完成的核心能力

- Patient / Cancer Case / Specimen / Sequencing / Variant 資料模型與 SQLite 相容性。
- SQLite FK、busy timeout、integrity check、backup、atomic restore、restart persistence。
- Schema upgrade 前自動 timestamp backup。
- Local CSV Import：`validate → preview → explicit import`，禁止 silent overwrite。
- Duplicate-aware preview 與 `import-history.jsonl` audit trail。
- `/workspace-import` 本機 UI，只有 local/research persistent SQLite 可寫入。
- Traceability Persistence E2E：真實 SQLite close/re-init 後仍保留 Evidence / Recommendation / Decision chain。
- 三個固定 PTC synthetic showcase cases 與 deterministic UUIDv5 bootstrap。
- Demo dataset schema / row-shape / enum / broken-reference / JSON-list validation。
- Recommendation、Clinical Decision、Treatment Plan、Knowledge Graph、PTC Research、PTC Integrated、PTC Command Center synthetic hydration。
- Navbar 保留 `demo_case` / `data_mode=synthetic`。
- Production API JSON smoke 與 multi-route Chromium gate。

最新工程狀態見 [docs/CURRENT_STATUS.md](docs/CURRENT_STATUS.md)。

## Local Workspace Import

本機 research workspace 可使用：

```text
GET  /api/v1/workspace/status
POST /api/v1/workspace/import/csv/preview
POST /api/v1/workspace/import/csv/commit
GET  /api/v1/workspace/import/history
```

UI：

```text
/workspace-import
```

Import policy：

```text
validate
→ preview validation + duplicates
→ explicit confirm=IMPORT
→ idempotent insert
→ existing deterministic records skipped
→ append import-history.jsonl
```

## Demo Showcase

Synthetic deep-link contract：

```text
?demo_case=PTC-DEMO-001&data_mode=synthetic
```

主要 showcase routes：

- `/recommendation`
- `/clinical-decision`
- `/treatment-plans`
- `/clinical-graph`
- `/ptc-research`
- `/ptc-workbench`
- `/ptc-command-center`

Vercel synthetic runtime 與 Local research workspace 嚴格分離；demo route 不應執行正式同步或持久化研究操作。

## 安全邊界

系統禁止：

- 自動診斷癌症；
- 提供藥物劑量或直接用藥指令；
- 將 VUS 直接視為可用藥變異；
- 將細胞、動物或計算結果宣稱為人體療效；
- 將 synthetic showcase 冒充真實患者或真實臨床證據；
- 讓 LLM 無來源創造基因—藥物關聯。

所有研究結論應保留來源、證據層級、限制、不確定性與 provenance。

## 技術棧

- Backend：Python / FastAPI / SQLAlchemy
- Frontend：React / TypeScript / Vite / Tailwind CSS
- Local database：SQLite + aiosqlite
- Optional scale-out database：PostgreSQL
- Visualization：Three.js / graph components
- Testing：pytest / Vitest / Chromium production smoke
- Deployment：Vercel demo + local research runtime

## 快速開始

```bash
pip install -r requirements.txt
pip install -r requirements-ai.txt

# Local/research example
set APP_MODE=local
set DB_BACKEND=sqlite
set SQLITE_PATH=./data/ai-kill-cancer.db
uvicorn src.backend.main:app --reload

# Frontend
cd src/frontend
npm install
npm run dev
```

## Release 文件

- [CHANGELOG.md](CHANGELOG.md)
- [RELEASE_NOTES_v1.0.3.md](RELEASE_NOTES_v1.0.3.md)
- [docs/RELEASE_CHECKLIST_v1.0.3.md](docs/RELEASE_CHECKLIST_v1.0.3.md)
- [docs/CURRENT_STATUS.md](docs/CURRENT_STATUS.md)
- [docs/V0_3_LOCAL_FIRST_ROADMAP_ZH.md](docs/V0_3_LOCAL_FIRST_ROADMAP_ZH.md)
- [docs/MEDICAL_SAFETY.md](docs/MEDICAL_SAFETY.md)
- [docs/DATA_PROVENANCE.md](docs/DATA_PROVENANCE.md)

## Release 原則

1. `VERSION` 與 backend `APP_VERSION` 必須一致。
2. Local Verification Gate 必須全綠。
3. Vercel production API JSON smoke 必須全綠。
4. Synthetic multi-route Chromium gate 必須全綠。
5. Release 成熟度僅表示軟體工程成熟度，**不表示臨床驗證或醫療有效性**。
