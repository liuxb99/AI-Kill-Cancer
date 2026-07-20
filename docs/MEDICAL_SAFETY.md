# 医疗安全声明

> 最后更新：2026-07-20

## 核心原则

1. **本项目不是医疗产品。** AI-Kill-Cancer 是一个研究探索项目，不应用于临床诊断、治疗决策或任何医疗用途。

2. **所有模型未经临床验证。** 项目中的 PyTorch 模型定义为研究原型，未在真实患者数据上训练或验证。任何输出都不应被视为医疗建议。

3. **模拟数据必须明确标识。** 所有 API 响应中的模拟数据包含 `provenance.data_mode: "synthetic"` 和免责声明。

## APP_MODE 安全规则

### demo 模式（默认）
- 所有数据标记为 `synthetic`
- 所有响应包含 `disclaimer`
- 模型可用时使用，不可用时回退模拟

### research 模式
- 无真实 checkpoint 时返回 `503 model_unavailable`
- 绝不使用随机初始化模型推理
- 不可用模拟数据替代真实模型输出

### production 模式
- 同 research 模式，加更严格 CORS
- 需要所有依赖就绪

## 禁止行为

- ❌ 不得声明 "based on NCCN guidelines" 除非有版本化规则和引用
- ❌ 不得显示未经验证的模型准确率
- ❌ 随机初始化模型绝不可用于正式推理
- ❌ 不得将模拟数据展示为真实医疗数据

## 数据溯源

所有 API 响应包含 `DataProvenance` 对象：

| 字段 | 说明 |
|------|------|
| `data_mode` | synthetic / research / production |
| `source` | 数据来源说明 |
| `source_url` | 来源 URL |
| `retrieved_at` | ISO 时间戳 |
| `model_version` | 模型版本（如适用） |
| `disclaimer` | 免责声明 |
