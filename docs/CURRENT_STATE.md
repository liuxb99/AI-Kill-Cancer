# 当前项目状态

> 最后更新：2026-07-20
> 版本：0.2.0-dev → 0.2.0
> Phase 1: Precision Oncology Foundation ✅ 完成

## 总体状态

| 项目 | 状态 | 说明 |
|------|------|------|
| 系统骨架 | ✅ 完成 | FastAPI + React 前后端分离 |
| 产品定位 | ✅ 完成 | 从泛癌症预测重构为甲狀腺癌 Precision Oncology 平台 |
| Domain Models | ✅ 完成 | 20 个领域模型（Pydantic + SQLAlchemy） |
| Adapter Interfaces | ✅ 完成 | 8 个第三方 adapter（VEP, OpenCRAVAT, CIViC, DGIdb, OncoTree 等） |
| Repository Layer | ✅ 完成 | 10 个 repository（CRUD + pagination + filter） |
| API v1 Routes | ✅ 完成 | 15 个端點（patients, cases, specimens, variants, analyses 等） |
| Three.js Contract | ✅ 完成 | 前後端共享 graph contract（10 node types, 12 edge types） |
| Database Migration | ✅ 完成 | Alembic revision #001（19 張新表 + 索引 + 外鍵） |
| 版本統一 | ✅ 完成 | 單一 VERSION 檔案，pyproject.toml, config.py 同步 |
| 前端页面 | ✅ 完成 | 6 个页面 + 图表组件 |
| 前端部署 | ✅ 完成 | Vercel 部署 |
| API 部署 | ✅ 完成 | Vercel Serverless |
| 单元测试 | ✅ 完成 | 108 个测试（全部通过，3 个 torch 相依測試因環境跳過） |
| 医疗安全声明 | ✅ 完成 | DataProvenance 机制 + 禁止用語檢查 |
| 文档 | 🟡 部分 | AGENTS.md + docs/ 系列 |

## 已完成功能（Phase 1 — Precision Oncology Foundation）

### 领域模型
- Patient（匿名化、consent tracking）
- CancerCase（PTC/FTC/MTC/HCC/PDTC/ATC 支援）
- Specimen（FFPE, fresh frozen, blood, FNA 等）
- SequencingTest（assay versioning, genome build, VAF）
- UploadedFile（VCF/CSV/TSV/JSON/PDF 合約, sha256, validation status）
- Variant（SNV/indel/CNV/fusion/SV/TERT promoter/MSI-TMB, somatic/germline/unknown, HGVS）
- Gene, Protein, Pathway
- Drug, DrugTarget
- Evidence（supporting/conflicting/neutral/insufficient, Level 1-5）
- DrugCandidate（5 類候選分級, 支持+反向證據）
- Publication, ClinicalTrial
- AnalysisRun（完整版本 manifest）
- Report（patient/professional/MTB）
- Consent, AuditLog

### API v1 端點
| 方法 | 路徑 | 說明 |
|------|------|------|
| POST | /api/v1/patients | 建立患者 |
| GET | /api/v1/patients/{id} | 取得患者 |
| GET | /api/v1/patients | 列表患者 |
| PATCH | /api/v1/patients/{id} | 更新患者 |
| DELETE | /api/v1/patients/{id} | 刪除患者 |
| POST | /api/v1/cases | 建立癌症案例 |
| GET | /api/v1/cases/{id} | 取得案例 |
| GET | /api/v1/cases | 列表案例 |
| POST | /api/v1/specimens | 建立檢體 |
| GET | /api/v1/specimens/{id} | 取得檢體 |
| POST | /api/v1/sequencing-tests | 建立測序檢測 |
| GET | /api/v1/sequencing-tests/{id} | 取得測序檢測 |
| POST | /api/v1/uploads | 建立上傳記錄 |
| GET | /api/v1/uploads/{id} | 取得上傳記錄 |
| POST | /api/v1/variants/import | 批量匯入變異 |
| POST | /api/v1/analyses | 建立分析 |
| GET | /api/v1/analyses/{id} | 取得分析 |
| GET | /api/v1/analyses/{id}/graph | 取得分析圖譜 |
| GET | /api/v1/analyses/{id}/drug-candidates | 取得藥物候選 |
| GET | /api/v1/analyses/{id}/evidence | 取得證據 |

### Adapter Interfaces
- BaseAdapter（ABC + health_check + supports + validate_input + annotate + normalize_response）
- NotConfiguredAdapter（Phase 1 placeholder）
- AdapterResult（統一結果 envelope）
- AdapterRegistry（註冊 + 健康檢查）
- 8 個 adapter 已註冊（VEP, OpenCRAVAT, CIViC, DGIdb, OncoTree, MyVariant, DRKG, PharmCAT）

### Three.js Visualization Contract
- 10 node types（chromosome, gene, variant, protein, pathway, drug, evidence, publication, clinical_trial）
- 12 edge types（located_on, encodes, affects, activates, inhibits, participates_in, targets, supported_by, conflicts_with, studied_in, approved_for, off_label_for）
- GraphNode（id, type, label, category, status, evidence_level, metadata）
- GraphEdge（id, source, target, relation, direction, weight, evidence_ids, provenance）

## Mock/Demo 功能

以下功能当前使用**模拟数据**：

1. `/api/v1/predict` — 癌症预测（无真实 checkpoint 时返回 synthetic 数据）
2. `/api/v1/recommend` — 治疗建议
3. `/api/v1/charts/*` — 统计图表
4. `/api/v1/dashboard/kpis` — 仪表盘 KPI
5. `/api/v1/research/sandbox/*` — 沙盒模型运行

所有模拟数据响应包含 `provenance.data_mode: "synthetic"` 标识。

## 未完成的核心研究

- [ ] 真实 VEP 执行（Phase 2）
- [ ] 真实 OpenCRAVAT 执行（Phase 2）
- [ ] CIViC 真实資料同步（Phase 2）
- [ ] DGIdb 真實資料同步（Phase 2）
- [ ] Three.js 正式畫面（Phase 4）
- [ ] AI 模型訓練與驗證
- [ ] 藥物效果預測
- [ ] LLM 推論與 RAG
- [ ] 完整臨床試驗匹配
