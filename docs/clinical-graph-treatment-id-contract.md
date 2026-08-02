# Clinical Graph Treatment ID Contract

本文件補充 `docs/clinical-graph-id-spec.md`，定義治療計畫相關實體在 Python 與 KnowGraphGo 間共用的 UUIDv5 canonical key。

## Namespace 與正規化

- Namespace：`a7b4e5c2-8d9f-4a3b-8c1d-6e9f2a7b3c5d`
- 演算法：UUIDv5
- Key 正規化：`trim + lowercase`
- 空字串、純空白與非字串 key：拒絕，不得產生圖譜 ID

## Entity Prefix

| Entity | Canonical key | Python method | Go method |
|---|---|---|---|
| Treatment Plan | `clinical:treatment_plan:{id}` | `treatment_plan_id` | `TreatmentPlanID` |
| Treatment Phase | `clinical:treatment_phase:{id}` | `treatment_phase_id` | `TreatmentPhaseID` |
| Treatment Item | `clinical:treatment_item:{id}` | `treatment_item_id` | `TreatmentItemID` |
| Monitoring | `clinical:monitoring:{id}` | `monitoring_id` | `MonitoringID` |
| Safety Rule | `clinical:safety_rule:{id}` | `safety_rule_id` | `SafetyRuleID` |

## Relation Prefix

```text
clinical:relation:{kind}:{from_key}:{to_key}
```

`kind`、`from_key`、`to_key` 三者都必须是非空字符串并执行相同正規化。

## Compatibility Rule

任何一端若变更 namespace、prefix 或正規化规则，必须同步更新另一端并新增固定 golden vector；否则视为 breaking change。事件重播、知识图谱去重与 Digital Thread 回溯均依赖此契约。
