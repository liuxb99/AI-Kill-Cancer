# AI-Kill-Cancer — 项目指南

## 项目目标

用人工智慧辅助癌症研究，提供工具、数据分析和可视化平台。

**当前状态：Phase 1 — 基础建设（骨架搭建中）**
所有 AI 模型仍处于**未训练/未验证**状态，API 返回的数据为模拟（synthetic）数据。本项目**不是**可用于临床诊断或治疗的医疗产品。

## 技术架构

```
src/
├── frontend/          # Vite + React + TypeScript 前端
│   └── src/pages/     # 页面：Home, Dashboard, KnowledgeBase, Research, Tools, ResearchPortal
├── backend/
│   ├── api/           # FastAPI 路由
│   │   ├── routes.py        # 核心 API（predict, recommend, charts, dashboard）
│   │   └── research.py      # 研究相关 API（sandbox, papers, uploads）
│   ├── config.py      # 环境变量配置
│   ├── models/        # Pydantic 请求/响应模型
│   ├── database/      # SQLAlchemy ORM（PostgreSQL）
│   └── main.py        # FastAPI 应用工厂
├── models/            # PyTorch 模型定义
│   ├── cancer_classifier.py   # CancerClassifier (nn.Module)
│   ├── train.py               # Trainer
│   ├── predict.py             # Predictor 工具
│   ├── molecule_utils.py      # 分子工具（SMILES, fingerprints）
│   ├── drug_discovery.py      # MoleculeVAE, DTIPredictor, DrugDiscoveryPipeline
│   ├── drug_response.py       # DrugResponsePredictor
│   ├── drugbank_integrator.py # DrugBank 内置数据
│   ├── treatment_recommender.py # TreatmentRecommender + CANCER_DRUG_DB
│   ├── literature_analyzer.py # 文献分析
│   └── pubmed_fetcher.py      # PubMed 抓取
├── tools/             # 辅助工具
│   └── utils.py
├── tests/             # pytest 测试
├── api/index.py       # Vercel serverless 入口
├── docker/            # Docker 配置
└── docs/              # 文档
```

## APP_MODE 模式

| 模式 | 环境变量 | 行为 |
|------|---------|------|
| demo (默认) | `APP_MODE=demo` | API 返回模拟数据，所有页面标注"模拟数据" |
| research | `APP_MODE=research` | 需要真实模型 checkpoint，无模型时返回不可用 |
| production | `APP_MODE=production` | 严格模式，需要所有依赖就绪 |

## 核心规则

### 禁止虚构医疗资料
- 所有未经验证的医疗数值必须标注 `data_mode: "synthetic"`
- 不得声明 "based on NCCN guidelines" 除非有版本化规则和引用
- 不得显示模型准确率（如 97.8%）除非来自本项目的可重现 evaluation
- 随机初始化模型**绝不可**用于正式推理

### 模型结果可追溯
- 所有预测必须携带 `data_source`、`model_version`、`retrieved_at`
- checkpoint 必须与 config (input_dim, num_cancer_types 等) 兼容
- checkpoint 缺失或不兼容时返回 `model_unavailable` 状态

### 修改流程
1. 静态检查（flake8 / mypy 等）
2. 现有测试通过
3. 为新增/修改的功能编写测试
4. API integration test
5. 前端 build（如涉及）
6. smoke test

## 测试命令

```bash
# 运行全部测试
pytest -v

# 运行特定测试
pytest tests/test_api.py -v
pytest tests/test_models.py -v
pytest tests/test_database.py -v

# 跳过 DB 依赖测试（无需 PostgreSQL）
pytest -v -m "not db"

# API 测试
pytest tests/test_api.py -v --tb=short
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `APP_MODE` | `demo` | demo / research / production |
| `DEBUG` | `false` | 调试模式 |
| `CORS_ORIGINS` | `*` | 允许的 CORS 域名（production 需明确指定） |
| `DATABASE_URL` | `postgresql+asyncpg://...` | 数据库连接 |
| `MODEL_PATH` | `./models/cancer_prediction.pkl` | 模型 checkpoint 路径 |
| `MODEL_ENABLED` | `true` | 是否启用模型加载 |
| `LOG_LEVEL` | `INFO` | 日志级别 |

## Git 规范
- P0 修复必须独立 commit
- 测试通过后方可 push
- commit message 使用英文，格式：`type: description`
