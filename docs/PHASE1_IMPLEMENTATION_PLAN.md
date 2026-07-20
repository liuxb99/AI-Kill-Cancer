# Phase 1 Implementation Plan — Precision Oncology Foundation

> 版本：0.2.0
> 建立日期：2026-07-20
> 狀態：進行中

## 1. 現有架構盤點

### 現有後端（可重用）

| 元件 | 路徑 | 狀態 | 說明 |
|------|------|------|------|
| FastAPI 應用工廠 | `src/backend/main.py` | ✅ 可重用 | create_app() 與 lifespan |
| Config | `src/backend/config.py` | 🟡 需要更新 | 版本從 1.0.0 → 0.2.0 |
| 現有 ORM 模型 | `src/backend/database/models.py` | 🟡 保留相容 | Patient, Diagnosis, Treatment, Drug, ResearchPaper |
| 現有 Pydantic schema | `src/backend/models/__init__.py` | 🟡 保留相容 | Predict, Recommend, Health, Charts |
| CRUD | `src/backend/database/crud.py` | 🟡 保留相容 | 既有 CRUD 保留不動 |
| Session | `src/backend/database/session.py` | ✅ 可重用 | AsyncSession |
| ETL | `src/backend/database/etl.py` | ❌ 暫不修改 | |
| Alembic | `migrations/` | 🟡 無版本 | 需要首次 migration |
| Router（routes.py） | `src/backend/api/routes.py` | 🟡 保留相容 | 保留既有端點，新增 v1 端點 |
| Router（research.py） | `src/backend/api/research.py` | 🟡 保留相容 | 保留既有端點 |
| Tests | `tests/` | 🟡 保留相容 | 既有測試保留 |

### 現有前端（可重用）

| 元件 | 路徑 | 狀態 |
|------|------|------|
| Vite + React + TS | `src/frontend/` | ✅ |
| 頁面元件 | `src/frontend/src/pages/` | 🟡 需要更新文案 |
| 圖表元件 | `src/frontend/src/components/charts/` | 🟡 保留相容 |

### 現有 Docker
- docker-compose.yml、Dockerfile、init.sql — 保留

## 2. 新增檔案清單

### Domain Models（新檔案）

```
src/backend/domain/
├── __init__.py
├── enums.py                    # 所有 enum 定義
├── patient.py                  # Patient
├── cancer_case.py              # CancerCase
├── specimen.py                 # Specimen
├── sequencing_test.py          # SequencingTest
├── uploaded_file.py            # UploadedFile
├── variant.py                  # Variant
├── gene.py                     # Gene
├── protein.py                  # Protein
├── pathway.py                  # Pathway
├── drug.py                     # Drug / DrugTarget
├── evidence.py                 # Evidence / EvidenceAssertion
├── drug_candidate.py           # DrugCandidate
├── publication.py              # Publication
├── clinical_trial.py           # ClinicalTrial
├── analysis_run.py             # AnalysisRun
├── report.py                   # Report
├── consent.py                  # Consent
├── audit_log.py                # AuditLog
└── visualization_graph.py      # Three.js Graph Contract
```

每組包含 Pydantic request/response schema + SQLAlchemy model（在同檔案內）。

### Adapter Interfaces（新檔案）

```
src/backend/adapters/
├── __init__.py
├── base.py                     # BaseAdapter 抽象類別
├── envelope.py                 # AdapterResult envelope
├── ensembl_vep.py              # Ensembl VEP adapter
├── opencravat.py               # OpenCRAVAT adapter
├── civic.py                    # CIViC adapter
├── dgidb.py                   # DGIdb adapter
├── oncotree.py                 # OncoTree adapter
├── myvariant.py                # MyVariant.info adapter
├── drkg.py                     # DRKG adapter
├── pharmcat.py                 # PharmCAT adapter
└── registry.py                 # Adapter registry
```

### Repository Layer（新檔案）

```
src/backend/repositories/
├── __init__.py
├── base.py                     # BaseRepository
├── patient_repo.py
├── cancer_case_repo.py
├── specimen_repo.py
├── sequencing_test_repo.py
├── uploaded_file_repo.py
├── variant_repo.py
├── drug_repo.py
├── evidence_repo.py
├── analysis_run_repo.py
└── report_repo.py
```

### API Routes（新檔案）

```
src/backend/api/v1/
├── __init__.py
├── patients.py                 # /api/v1/patients
├── cases.py                    # /api/v1/cases
├── specimens.py                # /api/v1/specimens
├── sequencing.py               # /api/v1/sequencing-tests
├── uploads.py                  # /api/v1/uploads
├── variants.py                 # /api/v1/variants
├── analyses.py                 # /api/v1/analyses
└── router.py                   # V1 router 聚合
```

### Tests（新檔案）

```
tests/
├── test_domain_models.py       # Pydantic schema 測試
├── test_repositories.py        # Repository 測試
├── test_migration.py           # Migration upgrade/downgrade 測試
├── test_api_v1.py              # API contract 測試
├── test_adapters.py            # Adapter interface 測試
├── test_visualization.py       # Graph contract 測試
├── test_provenance.py          # Provenance 測試
└── test_safety.py              # Medical safety wording 測試
```

### 文件（新檔案或更新）

```
docs/PHASE1_IMPLEMENTATION_PLAN.md  ← 本文件
docs/PHASE1_COMPLETION_REPORT.md    ← 完成時建立
docs/API_CONTRACT.md                ← 更新
docs/DATABASE_SCHEMA.md             ← 更新或新增
README.md                           ← 更新
docs/CURRENT_STATE.md               ← 更新
```

## 3. 需要修改的檔案

| 檔案 | 修改內容 |
|------|----------|
| `src/backend/config.py` | 版本 1.0.0 → 0.2.0；APP_NAME 更新 |
| `src/backend/main.py` | 掛載 v1 router |
| `migrations/env.py` | 加入新 domain models 到 target_metadata |
| `pyproject.toml` | 版本更新至 0.2.0 |
| `package.json`（frontend） | 版本同步 |
| `README.md` | 更新版本、現狀、路線圖 |
| `docs/CURRENT_STATE.md` | 更新狀態 |
| `VERSION`（新增） | 建立單一版本來源 |

## 4. Database Migration 計畫

第一次正式 migration（`001_precision_oncology_foundation`）：

建立以下新表：
- patients_v2（新版 Patient，保留舊 patients 表相容）
- cancer_cases
- specimens
- sequencing_tests
- uploaded_files
- variants
- genes
- proteins
- pathways
- drugs
- drug_targets
- evidences
- evidence_assertions
- drug_candidates
- publications
- clinical_trials
- analysis_runs
- reports
- consents
- audit_logs

策略：建立新表（以 `_v2` 後綴處理命名衝突），不對既有表做破壞性修改。

## 5. 相容性風險

| 風險 | 影響 | 緩解措施 |
|------|------|----------|
| 舊 patients 表與新 patients 命名衝突 | 高 | 新 domain model 用不同 tablename |
| 既有 API 端點路徑衝突 | 低 | v1 prefix 區隔 |
| Alembic 尚未有版本 | 中 | 建立初始 migration |
| 既有 tests 使用舊 models | 低 | 保留舊 models，新增新 tests |
| 前端現有頁面 | 低 | 逐步更新文案 |

## 6. 測試計畫

### Schema Tests
- 每個 Pydantic model 的必填欄位驗證
- Enum 值範圍
- Optional 與 default

### Repository Tests
- SQLite in-memory CRUD
- Pagination
- Filter queries
- Transaction rollback

### Migration Tests
- Upgrade 建立所有新表
- Downgrade 移除新表
- 既有資料不受影響

### API Contract Tests
- 每個新端點 200/400/404/503
- Request validation
- Response schema 符合 OpenAPI

### Adapter Interface Tests
- BaseAdapter contract
- 每個 adapter 的 NotConfigured 狀態
- Envelope 格式

### Provenance Tests
- DataProvenance 必填欄位
- Medical disclaimer 存在
- data_mode 標示

### Safety Tests
- 禁止用語檢查（diagnosis, prescribe, dosage）
- Synthetic 標示
- Model unavailable 狀態

## 7. 完成標準

1. ✅ 所有 Domain Models 定義完成（Pydantic + SQLAlchemy）
2. ✅ 所有 Adapter Interfaces 定義完成
3. ✅ 所有 Repositories 實作完成
4. ✅ 所有 API Routes 掛載完成
5. ✅ Database Migration 可 upgrade/downgrade
6. ✅ 版本統一為 0.2.0
7. ✅ Three.js Visualization Contract 完成
8. ✅ 所有 Tests 通過（pytest -v）
9. ✅ Frontend build 通過
10. ✅ OpenAPI schema 驗證通過
11. ✅ 文件同步更新
12. ✅ Git push 成功
