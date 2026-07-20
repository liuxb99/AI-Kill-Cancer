# 数据溯源

> 最后更新：2026-07-20

## 当前状态

所有图表数据和 API 预测当前使用**模拟数据（synthetic）**。

## 模拟数据来源

| 端点 | 数据性质 | 来源 |
|------|---------|------|
| `/api/v1/predict` | 模拟 | 基于简单规则（biomarker 阈值） |
| `/api/v1/recommend` | 模拟 | 基于分期硬编码数值 |
| `/api/v1/charts/cancer-stats` | 模拟 | 示意性数值 |
| `/api/v1/charts/research-trends` | 模拟 | 示意性数值 |
| `/api/v1/charts/prediction-results` | 模拟 | 示意性数值 |
| `/api/v1/dashboard/kpis` | 模拟 | 示意性数值 |
| `/api/v1/research/sandbox/*` | 模拟 | Mock model runners |

## 真实数据计划

- [ ] TCGA (The Cancer Genome Atlas) 数据集
- [ ] GEO (Gene Expression Omnibus) 数据集
- [ ] DrugBank 数据（内置基础数据已就绪）
- [ ] PubMed 文献数据
- [ ] NCCN 指南结构化数据

## DataProvenance Schema

每个 API 响应中的 `provenance` 对象：

```json
{
  "data_mode": "synthetic",
  "source": "Simulated data for demonstration purposes only",
  "source_url": null,
  "retrieved_at": "2026-07-20T12:00:00+00:00",
  "model_version": null,
  "disclaimer": "This is simulated data for demonstration purposes only..."
}
```
