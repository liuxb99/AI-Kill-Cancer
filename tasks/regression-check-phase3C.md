# 需求回歸檢查 — Phase 3C

## 總評：PARTIAL

| 需求章節 | 狀態 | 說明 |
|----------|------|------|
| §4 核心目標 | PASS | ConsensusEngine 已建立，輸入包含 patient_id / recommendation_id / clinical_decision_id / specialist_opinions / meeting_context，輸出包含 consensus_id / consensus_status / consensus_score / final_recommendation / supporting_rationale / dissenting_opinions / unresolved_questions / required_follow_up / participating_specialties / created_by / created_at / trace_id |
| §5 專科意見模型 & SpecialtyType Enum | PASS | SpecialtyType 含 9 個專科（medical_oncology / surgical_oncology / radiation_oncology / pathology / radiology / genomics / pharmacy / nursing / palliative_care），無大量 if/elif |
| §5 Position Enum | PASS | Position 含 support / oppose / abstain |
| §6 ConsensusStatus Enum | PASS | ConsensusStatus 含 unanimous / strong_consensus / majority_consensus / split_decision / insufficient_information / deferred，共 6 種 |
| §7 ConsensusRuleSet | PASS | ConsensusRuleSet 集中於 `consensus_rules.py`，包含 specialty_weights、confidence_high/medium/low、unanimous_threshold、strong_consensus_threshold、majority_consensus_threshold、split_decision_upper、min_opinions、min_confidence、abstain_weight |
| §7 計算規則 | PASS | Opinion Weight = Specialty Weight × Confidence Weight × Evidence Weight；產生 support_score / oppose_score / abstain_score / consensus_ratio / confidence_score |
| §8 P0 資料一致性 | PASS | Service._validate_links() 檢查 Recommendation.patient_id == ClinicalDecision.patient_id == Request.patient_id 以及 ClinicalDecision.recommendation_id == Recommendation.id，不一致時 raise ValueError → API 422 |
| §9 Audit Trail | PASS | created_by 從 API（require_auth 取得 user.id）→ Service 入參 → TumorBoardConsensusModel.created_by，非 NULL |
| §10 Database Models | PASS | TumorBoardConsensusModel（16 欄位含所有建議欄位）、TumorBoardOpinionModel（12 欄位含所有建議欄位）、TumorBoardConsensusTraceModel（7 欄位含所有建議欄位），關聯完整：Consensus → Opinions (1:N)、Consensus → Traces (1:N)，Cascade delete |
| §11 Migration 020 | PASS | 020_phase3c_tumor_board_consensus.py 建立三張表：domain_tumor_board_consensus、domain_tumor_board_opinions、domain_tumor_board_consensus_traces；FK 正確、Index 正確、UNIQUE(trace_id, step_order) 正確、upgrade 正確；downgrade 拋 IrreversibleMigrationError（保護資料安全） |
| §12 Repository | PASS | 三個 Repository：TumorBoardConsensusRepository（create / get_by_id / get_by_uuid / list_by_patient_id / list_by_clinical_decision_id / count_by_patient_id）、TumorBoardOpinionRepository（create / create_many / list_by_consensus_id）、TumorBoardConsensusTraceRepository（create / create_many / list_by_consensus_id / get_by_trace_id）；Repository 無 commit/rollback |
| §13 Service | PASS | TumorBoardConsensusService：P0 驗證 → Engine 執行 → Consensus Model + Opinion Models + Trace Models 建立 → 同一個 Transaction 寫入 → Commit/Rollback |
| §14 Consensus Trace | PASS | 8 步驟 trace：load_context、validate_links、normalize_opinions、calculate_weights、calculate_consensus、resolve_dissent、finalize_consensus、prepare_persistence；每步有 step_order / step_type / input_summary / output_summary |
| §15 API | PASS | 5 端點：POST /api/v1/tumor-board-consensus（201）、GET /api/v1/tumor-board-consensus/{consensus_id}、GET /api/v1/tumor-board-consensus?patient_id=&skip=&limit=、GET /api/v1/tumor-board-consensus/{consensus_id}/opinions、GET /api/v1/tumor-board-consensus/{consensus_id}/trace；skip>=0、1<=limit<=100；錯誤：404/422/500 generic message |
| §16 Frontend ListPage | PASS | TumorBoardConsensusListPage 存在，支援輸入 patient_id 查詢、顯示 status/score/specialties/created_at、進入 Detail |
| §16 Frontend DetailPage | PASS | TumorBoardConsensusPage 存在，顯示 Consensus Status / Score / Final Recommendation / Supporting Rationale / Dissenting Opinions / Unresolved Questions / Required Follow-up / Specialist Opinions / Trace Summary |
| §16 Router & Navigation | PASS | App.tsx 含 /tumor-board 和 /tumor-board/:id 路由，Navigation 含「腫瘤委員會」連結 |
| §17 建立入口 | PASS | ClinicalDecisionPage 包含建立 Tumor Board Consensus 表單，POST 後 navigate 到 Detail Page |
| §18 Report Section | PASS | report_generator.py 包含 _render_tumor_board_consensus()，含 Consensus Status / Score / Participating Specialties / Final Recommendation / Supporting Rationale / Dissenting Opinions / Unresolved Questions / Required Follow-up |
| §19 Engine Tests | PASS | 39 個測試，涵蓋 unanimous / strong_consensus / majority_consensus / split_decision / insufficient_information / deferred / specialty weighting / confidence weighting / contraindication impact / dissent extraction |
| §19 Model Tests | PASS | 19 個測試，涵蓋 Model creation / Relations / Cascade / JSON round-trip / Unique constraints |
| §19 Repository Tests | PASS | 28 個測試，涵蓋 create / get / list / count / create_many / pagination / not found |
| §19 Service Tests | PASS | 22 個測試，涵蓋 successful consensus / patient mismatch / recommendation mismatch / clinical decision mismatch / created_by persistence / transaction rollback / opinion persistence failure / trace persistence failure / commit failure |
| §19 API Tests | PASS | 20 個測試，涵蓋 POST success / GET success / List empty / List one / Pagination / 401 / 404 / 422 / 500 generic |
| §19 Digital Thread Test | PASS | 5 個測試，驗證 Patient → Recommendation → Clinical Decision → Tumor Board Consensus → Opinions → Trace 全部可從 Database 還原 |
| §19 Restart Recovery Test | PASS | 1 個測試，App1 POST → GET → Shutdown → App2 GET / Opinions / Trace |
| §19 Migration Tests | PASS | 13 個測試（020 相關），涵蓋 upgrade / downgrade (irreversible) / re-upgrade / FK / Index / Unique / Columns / Preserves 019 |
| §19 Frontend Tests | PASS | 3 個測試檔案（TumorBoardConsensusListPage.test.tsx、TumorBoardConsensusPage.test.tsx、ClinicalDecisionPage.test.tsx），涵蓋 List route / Detail route / Navigation / Create form / POST API / Redirect / Empty state / Error state |
| §20 Postgres Gate | **PARTIAL** | CI workflows/ci.yml 未包含 Phase 3C 測試檔案於 Postgres 閘道中（缺少 test_tumor_board_engine.py / test_tumor_board_models.py / test_tumor_board_repo.py / test_tumor_board_service.py / test_api_tumor_board.py / test_tumor_board_digital_thread.py / test_tumor_board_restart_recovery.py）。Alembic upgrade head 涵蓋 020，但 downgrade 僅到 016 而非 019→020 專用。Migration verification 使用 SQLite 非 Postgres。 |
| §21 禁止事項 | PASS | 未使用 dict/memory cache 作 Storage、未 Mock Repository 代替 Integration、未跳過 Postgres Test、未 xfail 核心測試、未刪除失敗測試、未修改已驗收 Migration、未修改 Phase 3A/3B 核心功能、未修改 AGENTS.md |
| §22 Commit Scope | PASS | 僅包含 Tumor Board 相關變更 |
| 前端-後端型別匹配 | **PARTIAL** | 前端類型 `TumorBoardConsensus` 使用 `status`（後端回傳 `consensus_status`）、`required_followup`（後端回傳 `required_follow_up`）；`SpecialistOpinion.confidence` 前端為 `string` 後端為 `float`；`CreateTumorBoardConsensusRequest` 缺少 `recommendation_id`（後端必填）；列表端點回傳 `participating_specialties` 但前端期望 `specialist_opinions`；Detail 頁面使用 `consensus.status` 應為 `consensus.consensus_status` |

---

## 缺漏項目

### 1. CI Postgres Gate 未涵蓋 Phase 3C 測試（§20）

CI Workflow `.github/workflows/ci.yml` 中 "Postgres Integration Gate - Run Tests on Postgres" 步驟**未包含**以下 Phase 3C 測試檔案：

- `tests/test_tumor_board_engine.py`（純計算，不需 DB）
- `tests/test_tumor_board_models.py`
- `tests/test_tumor_board_repo.py`
- `tests/test_tumor_board_service.py`
- `tests/test_api_tumor_board.py`
- `tests/test_tumor_board_digital_thread.py`
- `tests/test_tumor_board_restart_recovery.py`

此外，"Alembic downgrade & re-upgrade" 步驟只 downgrade 到 016，未針對 020 做 downgrade 測試（雖然 020 的 downgrade 設計為 irreversible，但應驗證 upgrade→(downgrade blocked)→re-upgrade 流程）。

**影響**：依照 §20 規範，CI 未通過時 Reviewer 最高 89 分，Phase 3C = PARTIAL，Ready for Next Phase = NO。

### 2. 前端類型與後端 API 回應不一致

前端 `src/frontend/src/api/workbench.ts` 中對 API 回應的 TypeScript 類型定義與後端實際回傳存在多處不匹配：

| 欄位 | 前端類型 | 後端實際回傳 |
|------|---------|-------------|
| `TumorBoardConsensus.status` | `string` | `consensus_status` |
| `TumorBoardConsensus.required_followup` | `string[]` | `required_follow_up` |
| `SpecialistOpinion.confidence` | `string` | `float`（數字） |
| `CreateTumorBoardConsensusRequest` | 缺少 `recommendation_id` | 後端要求必填 |
| List 端點的 `specialist_opinions` | 前端期望陣列 | 後端回傳 `participating_specialties`（`string[]`） |
| `TumorBoardConsensus.dissenting_opinions` | `string[]` | `list[dict]` |
| `TumorBoardConsensus.trace_summary` | `string` | 後端無此欄位（回傳 `trace_id`） |

這些不匹配會導致前端在執行時出現 undefined 錯誤或型別錯誤。

---

## 總結

Phase 3C 的核心功能（Engine、Models、Repositories、Service、API、Trace、Migration）**完全實作**且測試**完整**。但存在以下問題：

1. **CI Postgres Gate 未涵蓋 Phase 3C 測試**（§20 違規）— 部分測試未在 Postgres 上執行
2. **前端 TypeScript 類型與後端 API 不匹配** — 欄位名稱、型別不一致

根據 §23 Reviewer Gate 規範：若任一項 FAIL 或 PARTIAL 或未驗證，則滿足需求 = NO，Reviewer 最高 89，Ready for Next Phase = NO。

因此本輪評定為 **PARTIAL**，需修正上述兩個問題後方可標記完成。
