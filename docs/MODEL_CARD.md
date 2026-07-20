# Model Card — AI-Kill-Cancer

> 最后更新：2026-07-20
> 状态：**未训练 / 未验证** — 仅定义模型架构

## CancerClassifier

| 属性 | 值 |
|------|-----|
| 架构 | MLP (BatchNorm + ReLU + Dropout) |
| 输入维度 | 20,500 (基因表达) |
| 隐藏层 | [1024, 512, 256, 128] |
| 输出 | cancer_type (3), subtype (6), stage (4) |
| 训练状态 | ❌ 未训练 |
| 验证状态 | ❌ 未验证 |
| checkpoint 格式 | `{"config": {...}, "model_state_dict": ..., "model_version": "..."}` |

## TreatmentRecommender

| 属性 | 值 |
|------|-----|
| 架构 | MLP |
| 输入 | 基因表达 + 临床特征 |
| 输出 | 药物类别得分 |
| 训练状态 | ❌ 未训练 |
| 内置知识库 | CANCER_DRUG_DB（硬编码参考数据） |

## DrugResponsePredictor

| 属性 | 值 |
|------|-----|
| 架构 | Embedding + MLP |
| 输入 | 基因表达 + 药物索引 |
| 输出 | 响应概率 [0, 1] |
| 训练状态 | ❌ 未训练 |

## MoleculeVAE

| 属性 | 值 |
|------|-----|
| 架构 | RNN Encoder-Decoder + VAE |
| 潜在维度 | 128 |
| 训练状态 | ❌ 未训练 |

## DTIPredictor

| 属性 | 值 |
|------|-----|
| 架构 | MLP |
| 输入 | Drug fingerprint + Target embedding |
| 输出 | 交互概率 [0, 1] |
| 训练状态 | ❌ 未训练 |

## DrugBankIntegrator

| 属性 | 值 |
|------|-----|
| 数据来源 | DrugBank 内置子集（硬编码） |
| 药物数 | ~100 |
| 靶点数 | ~50 |
| 状态 | ✅ 内置数据可用 |

## 已知限制

1. 所有模型为**随机初始化**，未经过任何训练
2. 内置 DrugBank 数据仅为示意性子集
3. 模型准确率（如 97.8%）为**模拟数值**，不代表真实性能
4. 无真实患者数据用于训练或验证
