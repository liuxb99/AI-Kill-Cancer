# Requirements — Phase 3F-1：Clinical Graph Contract Hardening

## 目標

關閉 Python 與 KnowGraphGo 治療計畫圖譜 ID 契約不完整問題，並強化所有 ID Factory 對空白與非法輸入的防禦。

## 必須完成

1. Python `ClinicalGraphIDFactory` 新增：
   - `treatment_plan_id`
   - `treatment_phase_id`
   - `treatment_item_id`
   - `monitoring_id`
   - `safety_rule_id`
2. Canonical prefix 必須與 Go `ClinicalIDFactory` 一致。
3. 所有 entity／relation key 必須執行 trim + lowercase。
4. 空字串、純空白字串必須拒絕。
5. 非字串 key 必須明確拋出 `TypeError`。
6. 新增 UUIDv5、正規化、無碰撞、非法輸入測試。
7. 更新 Clinical Graph ID 規格文件。
8. 完整 CI 通過後方可合併 `master`。

## 不在本批範圍

- Domain ORM 大規模拆分
- Outbox Retry Policy 重構
- KnowGraphGo Adapter God Class 拆分
- API Error Contract 統一
