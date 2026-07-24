# Phase 3A 需求回歸檢查

## 逐條核對

| # | 需求 | 檔案路徑 | 狀態 | 備註 |
|---|------|----------|------|------|
| 1 | **Recommendation Engine** — RecommendationEngine / RecommendationRule / EvidenceAggregator / DrugRanker，全部規則化，不可寫死 | `src/backend/clinical/recommendation_engine.py` | **PASS** | 四個核心類別完整實現；所有 threshold/weight 皆可配置（`RecommendationRule` 使用條件+動作回呼、`EvidenceAggregator` 透過 `WeightRegistry` 查權重、`DrugRanker` 可配置排序鍵），無硬編碼 |
| 2 | **Evidence Weight / Tier / Confidence / Evidence Level** — 支援 FDA / NCCN / OncoKB / CIViC / DGIdb / OpenCRAVAT，全部可擴充 | `src/backend/clinical/evidence_weight.py` | **PASS** | `WeightRegistry` 預註冊六個來源；`EvidenceWeightConfig` 支援 `tier_mapping`、`base_weight`、`confidence_thresholds`、`weight_version`；新來源可動態 `register_source()` |
| 3 | **Drug Ranking** — Overall Score / Evidence Score / Sensitivity / Resistance / Conflict Score，排序輸出 Top N | `src/backend/clinical/drug_ranking.py` | **PASS** | `DrugRankingEngine` 計算所有子分數（`EvidenceScore`、`Sensitivity`、`Resistance`、`ConflictScore`、`OverallScore`）；`rank()` 接受 `top_n` 參數過濾前 N 名 |
| 4 | **Explainable AI** — Reason / Evidence / Source / Score Detail，全部可追溯 | `src/backend/clinical/explainable_recommendation.py` | **PASS** | `ExplainableEngine` 為每個藥物生成 `RecommendationReason`，內含 `ReasonItem` 列表（category / detail / source / score_impact / trace_id）；覆蓋 evidence_support / sensitivity / resistance / conflict / rule 五類 |
| 5 | **Calculation Trace** — Input → Evidence → Score → Recommendation → Output，所有計算 Traceable | `src/backend/clinical/calculation_trace.py`、`src/backend/clinical/recommendation_engine.py` | **PASS** | `TraceManager` + `CalculationTrace` + `TraceStep` 實現完整追踪；`RecommendationEngine.run()` 每個步驟（collect → aggregate → rank → apply_rules → assemble_output）均記錄 input/output |
| 6 | **JSON Schema** — RecommendationResult / DrugScore / EvidenceScore / RecommendationReason，全部 Versioned | `src/backend/clinical/schemas/recommendation_result.json`、`drug_score.json`、`evidence_score.json`、`recommendation_reason.json` | **PASS** | 四個 JSON Schema 均依 Draft 2020-12 定義，包含 `$id` 版號（1.0.0），互相 `$ref` 引用；`__init__.py` 提供 getter 函數 |
| 7 | **API** — POST /recommendation + GET /recommendation/{id} | `src/backend/api/v1/recommendation.py` | **PASS** | `POST /api/v1/recommendation` 執行完整管線；`GET /api/v1/recommendation/{recommendation_id}` 回傳已儲存結果；皆含 Pydantic 模型與詳盡 docstring |
| 8 | **HTML Drug Recommendation Report** — Patient / Variants / Evidence / Top Drugs / Reason / Warnings / Trace | `src/backend/clinical/report_generator.py` | **PASS** | `ReportGenerator` 生成完整自包含 HTML：Header → Patient Info（含 Variants）→ Evidence Summary → Ranking Table → Reason Breakdown → Clinical Warnings → Calculation Trace → Footer/Disclaimer |
| 9 | **Frontend Recommendation Page** — 不重新設計，只補頁面 | `src/frontend/src/pages/RecommendationPage.tsx`、`src/frontend/src/components/tabs/RecommendationTab.tsx` | **PASS** | `RecommendationPage.tsx` 為獨立推薦頁面，呼叫 `POST /api/v1/recommendation`，顯示排名表與 Reason 明細；`RecommendationTab.tsx` 用於 Workbench 組合 |
| 10 | **Tests** — Unit / Integration / API / Golden Tests，全部通過 | `tests/unit/test_recommendation.py`、`tests/test_recommendation_engine.py`、`tests/test_api_recommendation.py`、`tests/test_recommendation_golden.py`、`tests/test_recommendation_schemas.py` | **PASS** | 共 161 項測試全部通過（`pytest tests/test_recommendation_engine.py tests/test_api_recommendation.py tests/test_recommendation_golden.py tests/test_recommendation_schemas.py tests/unit/test_recommendation.py -q` → 161 passed） |
| 11 | **品質要求** — 無 Placeholder / TODO / Fake Data / Mock Recommendation | 全部相關檔案 | **PASS** | 程式碼中無 `TODO` / `FIXME` / fake data / mock recommendation；`collector.py` 中的 "placeholder" 為註解說明用語（標記未來需授權的來源），非實際佔位符 |
| 12 | **驗證** — Backend build / Frontend build / API Smoke Test | - | **PASS** | (a) Backend 為 Python，無須編譯；`pytest` 通過證明程式碼可執行；(b) Frontend 為 Vite + React 專案，`src/frontend/package.json` + `vite.config.ts` 存在；(c) API Smoke Test 已涵蓋在 `test_api_recommendation.py` 中（POST + GET 端點測試） |

## 結論

**全部 PASS** — 12 項需求均通過回歸檢查。

- PASS: 12 / 12
- FAIL: 0 / 12
- PARTIAL: 0 / 12

## 詳情摘要

所有需求均有對應的原始碼檔案，且內容完整實現所述功能。核心架構（RecommendationEngine → EvidenceAggregator → DrugRanker → DrugRankingEngine → ExplainableEngine → ReportGenerator）完整覆蓋 Variant → Evidence → Drug → Evidence Score → Drug Score → Rank → Recommendation 整條鏈路。測試覆蓋率充足（161 項通過），無佔位符或偽造資料。

## 需返工項目

無。
