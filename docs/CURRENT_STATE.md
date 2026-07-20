# 当前项目状态

> 最后更新：2026-07-20

## 总体状态

| 项目 | 状态 | 说明 |
|------|------|------|
| 系统骨架 | ✅ 完成 | FastAPI + React 前后端分离 |
| AI 模型定义 | ✅ 完成 | CancerClassifier, DrugDiscovery, TreatmentRecommender 等 |
| 模型训练 | ❌ 未进行 | 需要真实数据集 |
| 模型验证 | ❌ 未进行 | 需要真实数据集 |
| 数据库 Schema | ✅ 完成 | SQLAlchemy ORM |
| 数据库部署 | 🟡 部分 | PostgreSQL 配置完成，但未连接真实实例 |
| 前端页面 | ✅ 完成 | 6 个页面 + 图表组件 |
| 前端部署 | ✅ 完成 | Vercel 部署 |
| API 部署 | ✅ 完成 | Vercel Serverless |
| 单元测试 | ✅ 完成 | 103 个测试（全部通过） |
| 医疗安全声明 | ✅ 完成 | DataProvenance 机制已加入 |
| 文档 | 🟡 部分 | AGENTS.md + docs/ 系列 |

## 已完成功能（系统骨架）

- FastAPI RESTful API（predict, recommend, charts, dashboard, research）
- React + TypeScript 前端（Home, Dashboard, KnowledgeBase, Research, Tools, ResearchPortal）
- PostgreSQL 数据库建模（Patient, Diagnosis, Treatment, Drug, ResearchPaper）
- 研究论文 CRUD API
- Sandbox 模拟模型运行
- 文件上传 API
- CORS 安全配置
- Health 端点（/health/live, /health/ready, /health/dependencies）
- APP_MODE 三模式（demo / research / production）

## Mock/Demo 功能

以下功能当前使用**模拟数据**：

1. `/api/v1/predict` — 癌症预测（无真实 checkpoint 时返回 synthetic 数据）
2. `/api/v1/recommend` — 治疗建议
3. `/api/v1/charts/*` — 统计图表
4. `/api/v1/dashboard/kpis` — 仪表盘 KPI
5. `/api/v1/research/sandbox/*` — 沙盒模型运行

所有模拟数据响应包含 `provenance.data_mode: "synthetic"` 标识。

## 未完成的核心研究

- [ ] 真实癌症数据集采集与整理
- [ ] CancerClassifier 模型训练与验证
- [ ] TreatmentRecommender 模型训练与验证
- [ ] DrugResponsePredictor 模型训练与验证
- [ ] MoleculeVAE 训练
- [ ] 模型基准测试与准确率验证
- [ ] 真实 NCCN guideline 规则整合
- [ ] 临床数据隐私合规
