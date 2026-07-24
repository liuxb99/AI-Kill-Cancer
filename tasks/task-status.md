# 任務狀態

## 場景
Phase 3A：Drug Recommendation Engine V1 — 臨床智能功能開發

## 場景分類
feature-dev（功能開發）

## 任務清單

| ID | 任務 | 狀態 | 負責角色 | 備註 |
|----|------|------|----------|------|
| P3A-01 | Recommendation Engine 核心（Engine/Rule/Aggregator/Ranker） | [ ] 待辦 | backend-logic | 全部規則化，不可寫死 |
| P3A-02 | Evidence Weight / Tier / Confidence / Evidence Level 模型 | [ ] 待辦 | db-modeler | 支援 FDA/NCCN/OncoKB/CIViC/DGIdb/OpenCRAVAT |
| P3A-03 | Drug Ranking 系統（Overall/Evidence/Sensitivity/Resistance/Conflict Score） | [ ] 待辦 | backend-logic | 排序輸出 Top N |
| P3A-04 | Explainable AI（Reason/Evidence/Source/Score Detail） | [ ] 待辦 | backend-logic | 全部可追溯 |
| P3A-05 | Calculation Trace（Input→Evidence→Score→Recommendation→Output） | [ ] 待辦 | backend-logic | 整合既有 DecisionThread |
| P3A-06 | JSON Schema（RecommendationResult/DrugScore/EvidenceScore/RecommendationReason） | [ ] 待辦 | backend-logic | Versioned |
| P3A-07 | API 端點（POST /recommendation + GET /recommendation/{id}） | [ ] 待辦 | api-designer | |
| P3A-08 | HTML Drug Recommendation Report | [ ] 待辦 | backend-logic | Patient/Variants/Evidence/Top Drugs/Reason/Warnings/Trace |
| P3A-09 | Frontend Recommendation Page | [ ] 待辦 | frontend-logic | 只補頁面，不重新設計 |
| P3A-10 | 測試（Unit/Integration/API/Golden Tests） | [ ] 待辦 | unit-tester + integration-tester | 全部通過 |
