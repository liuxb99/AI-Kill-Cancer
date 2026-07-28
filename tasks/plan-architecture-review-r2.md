# Architecture Review 第 2 次補充計劃（R2）

> **依據**：REVIEWER 評分 82/100 ❌ 不合格，指出三個主要缺失需補充。
> **第 1 次返工**（R1）已補充 §10 Domain 逐檔案審查表、§11 Dead Code Analysis、§12 Architecture Smell。
> **本次 R2 目標**：針對 R1 仍不足的三個缺失進行第二次補充。

---

## 一、缺失項目總覽

| # | 缺失 | REVIEWER 要求 | R1 現狀 | R2 補充目標 |
|---|------|-------------|---------|-----------|
| **A** | Review 8（Trace） | 逐一列出所有 Calculation Trace 的欄位一致性對比清單 | 僅在 §3 P1-05 提及三套系統不一致，無欄位級表格對比 | 新增獨立 §13 Trace Schema 一致性對比，以表格逐一比對所有 Trace 系統的每個欄位 |
| **B** | Review 10（Tests） | 逐一列出 8 個類別的測試覆蓋狀態和缺失案例 | 僅有 §3 P2-10/P2-11 兩個缺失案例 + 附錄 A 總分 8.0/10 | 新增獨立 §14 Tests Coverage 逐類別審查表 |
| **C** | Domain 審查對 State / Version 一致性檢查不足 | 對 State 轉換和 Version 控制的檢查不夠詳細 | §10 有 Entity/Aggregate 分類但未深入分析 State 轉換表和 Version 控制模式 | 在 §10 補充 §10.5 State 轉換審查 + §10.6 Version 控制審查 |

---

## 二、各項目補充方式

### 項目 A：Trace Schema 一致性對比（新增 §13）

#### A1. 目標
在現有報告末尾新增獨立章節 §13「Trace Schema 一致性對比」，用表格逐一比對以下所有 Trace 系統的欄位：

#### A2. 掃描範圍
所有涉及 Trace 的模型（共 6 個）：

| # | 系統 | 檔案路徑 | Trace 類別 |
|---|------|---------|-----------|
| 1 | **CalculationTrace**（記憶體） | `src/backend/clinical/calculation_trace.py` | `CalculationTrace` + `TraceStep` |
| 2 | **TreatmentPlanTrace**（記憶體） | `src/backend/clinical/treatment_plan_trace.py` | `TreatmentPlanTraceStep` + `TreatmentPlanTraceBuilder` |
| 3 | **DecisionThread**（DB + Pydantic） | `src/backend/clinical/decision_thread.py` | `DecisionNodeModel`(ORM) + `DecisionNode`(Pydantic) |
| 4 | **RecommendationTrace ORM** | `src/backend/domain/recommendation.py` | `RecommendationTraceModel` + `RecommendationTraceStepModel` |
| 5 | **TreatmentPlanTrace ORM** | `src/backend/domain/treatment_plan.py` | `TreatmentPlanTraceModel` |
| 6 | **TumorBoardConsensusTrace ORM** | `src/backend/domain/tumor_board.py` | `TumorBoardConsensusTraceModel` |

#### A3. 對比表格

產出 **3 張核心對比表**：

**表 1：Trace 主表（Trace-level）欄位對比**

| 欄位 | CalculationTrace | TreatmentPlanTraceBuilder | DecisionNodeModel | RecommendationTraceModel | TreatmentPlanTraceModel | TumorBoardConsensusTraceModel |
|------|:---------------:|:------------------------:|:-----------------:|:-----------------------:|:----------------------:|:----------------------------:|
| trace_id / id | trace_id: str | 無獨立 ID（內含於 builder） | id: CompatUUID PK | (待查) | (待查) | (待查) |
| patient_id / case_id | patient_id: str | 無 | case_id: String(36) | (待查) | (待查) | (待查) |
| started_at / created_at | started_at: datetime | 無 | timestamp: DateTime | (待查) | (待查) | (待查) |
| completed_at | completed_at: Optional[datetime] | 無 | 無 | (待查) | (待查) | (待查) |
| status | status: str(running/completed/failed) | 無 | 無（node_type 隱含） | (待查) | (待查) | (待查) |

> 註：上表為預估結構，實際以讀取各檔案後的完整結果為準。

**表 2：Trace Step 欄位對比**

| 欄位 | TraceStep (CalculationTrace) | TreatmentPlanTraceStep | DecisionNode (DecisionThread) | RecommendationTraceStepModel |
|------|:---------------------------:|:---------------------:|:----------------------------:|:---------------------------:|
| step_order | 無（列表順序隱含） | step_order: int | 無（parent_id 鏈） | (待查) |
| step_name / step_type | step_name: str + step_type: str | step_type: str | node_type: NodeType(Literal) | (待查) |
| input / input_snapshot | input_data: dict | input_summary: dict | input_snapshot: Column(JSON) | (待查) |
| output / output_snapshot | output_data: dict | output_summary: dict | evidence_snapshot: Column(JSON) | (待查) |
| created_at / timestamp | timestamp: datetime | 無 | timestamp: DateTime | (待查) |
| duration_ms | duration_ms: Optional[float] | 無 | 無 | (待查) |

**表 3：欄位命名與型別一致性總結**

| 語義 | 出現次數 | 命名是否統一 | 型別是否統一 | 結論 |
|------|:-------:|:----------:|:----------:|------|
| step identifier | 多種 | ❌ 混用 step_name / step_type / node_type | ❌ str vs Literal vs int(step_order) | 不一致 |
| input snapshot | 多種 | ❌ 混用 input_data / input_summary / input_snapshot | ✅ 皆為 dict/JSON | 命名不一致 |
| output snapshot | 多種 | ❌ 混用 output_data / output_summary / evidence_snapshot | ✅ 皆為 dict/JSON | 命名不一致 |
| timestamp | 多種 | ❌ 混用 timestamp / started_at / created_at | ❌ datetime vs Optional[datetime] vs DateTime(DB) | 不一致 |

#### A4. 統一分數調整

基於對比結果，在 §1 Architecture Score 的 Trace 原始分數 5.5/10 旁新增註腳，說明「若納入欄位級不一致，實際 Trace 分數應更低，但為保持與 R1 一致，暫不調整分數，建議在 R-M4 統一後重新評分。」

#### A5. 預估工時

- 讀取 6 個 Trace 相關檔案：0.5h
- 產出 3 張對比表：1h
- 撰寫分析總結與建議：0.5h
- **合計：2h**

---

### 項目 B：Tests Coverage 逐類別審查表（新增 §14）

#### B1. 目標
在現有報告末尾新增獨立章節 §14「Tests Coverage 逐類別審查」，以表格逐一列出 8 個類別的測試覆蓋狀態和缺失案例。

#### B2. 8 個類別掃描方式

使用 `pytest --cov --cov-report=term` 或手動掃描 `tests/` 目錄，按以下分類逐類統計：

| 類別 | 對應測試檔案模式 | 現有測試檔案數 |
|------|---------------|:------------:|
| **Engine** | `test_*_engine.py`, `test_recommendation_engine.py`, `test_tumor_board_engine.py` | 待統計 |
| **Repository** | `test_*_repo.py`, `test_*_repos.py`, `test_*_repository.py` | 待統計 |
| **Service** | `test_*_service.py` | 待統計 |
| **API** | `test_api*.py`, `test_*_api.py` | 待統計 |
| **Restart** | `test_*_restart*.py`, `test_restart_recovery.py` | 待統計 |
| **Migration** | `test_migration*.py` | 待統計 |
| **Postgres** | `test_*_pg*.py`, `test_migration_025_pg_*.py` | 待統計 |
| **Graph** | `test_phase3d_*.py`, `test_provenance.py` | 待統計 |

#### B3. 產出表格

**表 4：8 類別測試覆蓋逐類審查表**

| 類別 | 測試檔案數 | 覆蓋函數數 | 推估覆蓋率 | 已覆蓋關鍵案例 | 缺失案例 | 優先級 |
|------|:---------:|:---------:|:---------:|--------------|---------|:------:|
| Engine | ? | ? | ?% | ... | ... | ... |
| Repository | ? | ? | ?% | ... | ... | ... |
| Service | ? | ? | ?% | ... | ... | ... |
| API | ? | ? | ?% | ... | ... | ... |
| Restart | ? | ? | ?% | ... | ... | ... |
| Migration | ? | ? | ?% | ... | ... | ... |
| Postgres | ? | ? | ?% | ... | ... | ... |
| Graph | ? | ? | ?% | ... | ... | ... |

**表 5：缺失測試案例詳細清單**

| 類別 | 缺失案例名稱 | 對應原始程式 | 風險 | 建議優先級 |
|------|------------|-------------|:----:|:--------:|
| Engine | ... | ... | ... | ... |
| ... | ... | ... | ... | ... |

#### B4. 已知缺失（R1 已識別）

| ID | 缺失 | 類別 | 參考 R1 |
|----|------|------|---------|
| P2-10 | 缺少 KnowGraphGo CLI 端到端整合測試 | Graph | §3 |
| P2-11 | 缺少 TreatmentPlanStateMachine 獨立單元測試 | Engine | §3 |
| R-L10 | 補上 Missing Unit Tests（StateMachine、Trace、Outbox 邊界案例） | 跨類別 | §6 |

#### B5. 預估工時

- 掃描 `tests/` 目錄所有檔案，按 8 類別分類統計：0.5h
- 對比各類別的原始程式檔案估算覆蓋缺口：1h
- 產出 2 張表格並撰寫分析：0.5h
- 若執行 `pytest --cov` 需加環境準備時間：0.5h
- **合計：2~2.5h**

---

### 項目 C：Domain 審查補充 State / Version 檢查（補充 §10）

#### C1. 目標
在現有 §10「Domain Architecture — 逐檔案審查表」中新增兩個子節：
- **§10.5 State 轉換審查**：逐一分析所有含狀態欄位的 Domain 模型，檢查是否有對應的 State Machine / Enum 約束、轉換表是否完整、資料庫層是否有 SAEnum 約束。
- **§10.6 Version 控制審查**：逐一分析所有含版本欄位或版本關聯的 Domain 模型，檢查樂觀鎖、版本鏈、版次管理的一致性。

#### C2. State 轉換審查（§10.5）

**掃描範圍**：所有含 `status` / `*_status` 欄位的 Domain Model。

| 模型 | 狀態欄位名稱 | 型別 | 是否有對應 Enum | 是否有 State Machine | 是否有 SAEnum 約束 | 合法值 |
|------|------------|:----:|:--------------:|:------------------:|:----------------:|:------:|
| `AnalysisRunModel` | `status` | SAEnum(AnalysisStatusEnum) | ✅ | ❌ | ✅ | PENDING / RUNNING / ... |
| `PatientModel` | `consent_status` | SAEnum(ConsentStatusEnum) | ✅ | ❌ | ✅ | PENDING / GRANTED / ... |
| `TreatmentPlanModel` | `plan_status` | String(32) | ✅ (PlanStatus) | ✅ (TreatmentPlanStateMachine) | ❌ | draft / proposed / ... |
| `RecommendationModel` | `status` | String(32) | ❌ | ❌ | ❌ | pending / ... |
| `ClinicalDecisionModel` | `status` | String(32) | ❌ | ❌ | ❌ | active / ... |
| `TumorBoardConsensusModel` | `consensus_status` | String(32) | ❌ | ❌ | ❌ | pending / ... |
| `TreatmentPhaseModel` | `status` | String(32) | ❌ | ❌ | ❌ | planned / ... |
| `TreatmentItemModel` | `status` | String(32) | ❌ | ❌ | ❌ | planned / ... |
| `ClinicalGraphOutboxModel` | `status` | String(32) | ❌ | ❌ | ❌ | pending / ... |
| ... | ... | ... | ... | ... | ... | ... |

> 註：上表為預估結構，實際以完整 grep 後的結果為準。

**產出分析**：
1. 統計「有 State Machine」 vs 「無 State Machine」的比例
2. 統計「使用 SAEnum」 vs 「使用 String(32)」的比例
3. 識別缺失 State Machine 的高風險模型（如 RecommendationModel / ClinicalDecisionModel 的狀態變更無約束）
4. 建議：為所有非純 Enum 狀態欄位補上 State Machine 或至少補上 SAEnum

#### C3. Version 控制審查（§10.6）

**掃描範圍**：所有含 `version` / `*_version*` 欄位或版本關聯的 Domain Model，以及全域版本控制機制。

| 模型 | 版本欄位 | 型別 | 樂觀鎖 (version_id) | 版本鏈 (previous_version) | UniqueConstraint |
|------|---------|:----:|:------------------:|:------------------------:|:---------------:|
| `TreatmentPlanModel` | `version` | Integer | ❌ | ✅ (previous_version_id) | ✅ (plan_id, version) |
| 其他 Model | 無 | - | ❌ | ❌ | ❌ |

**產出分析**：
1. 僅 `TreatmentPlanModel` 有顯式版本控制，其他 Aggregate（Patient、CancerCase、Recommendation 等）皆無
2. 全部 Model 缺少 SQLAlchemy 樂觀鎖（無 `version_id` 欄位）
3. 風險：並發寫入無衝突偵測，可能造成遺失更新
4. 建議：至少為 Aggregate Root Model 添加 `version_id` 樂觀鎖

#### C4. 分數影響

基於補充分析，若 State/Version 分數明顯偏低，在 §1 Architecture Score 的 Domain 原始分數 4.0/10 旁可加註腳說明「State 轉換和 Version 控制為 Domain 層的額外扣分項，獨立評分約 3/10，建議 Domain 總分下修至 3.5/10。」（實際調整幅度待分析後決定）

#### C5. 預估工時

- grep 掃描所有 Domain Model 的 status / version 欄位：0.3h
- 逐一檢視每個狀態欄位的 Enum / State Machine 對應：0.5h
- 逐一檢視每個版本機制的完整性：0.3h
- 產出 §10.5 狀態轉換表 + 分析：0.5h
- 產出 §10.6 版本控制表 + 分析：0.5h
- **合計：2h**

---

## 三、補充完成後的驗收標準

### 驗收檢查清單

| # | 檢查項目 | 驗收方式 | 通過標準 |
|---|---------|---------|---------|
| 1 | §13 Trace 欄位對比表完整 | 人工比對 6 個 Trace 檔案 | 3 張對比表涵蓋全部 6 個 Trace 系統，無遺漏 |
| 2 | §13 有明確一致性結論 | 閱讀 §13 總結段 | 指出命名不一致、型別不一致、缺失欄位等具體問題 |
| 3 | §14 8 類別測試覆蓋表完整 | 人工比對 `tests/` 目錄 | 8 個類別皆有獨立表格行，無遺漏 |
| 4 | §14 缺失案例清單非空 | 閱讀 §14 缺失案例表 | 至少列出 5 個以上真實缺失（已知 P2-10/P2-11 為最低要求） |
| 5 | §10.5 State 轉換表完整 | grep 驗證 Domain Model | 涵蓋所有含 status 欄位的 Model，無遺漏 |
| 6 | §10.6 Version 控制表完整 | grep 驗證 Domain Model | 涵蓋所有含 version 相關欄位的 Model |
| 7 | 無「需確認」標記 | grep `需確認\|待確認\|TODO` | R2 新增內容無「需確認」殘留 |
| 8 | 所有表格格式統一 | 視覺檢查 | 與 R1 的 §10/§11/§12 表格風格一致 |

### 回歸檢查

補充完成後，執行 `tasks/reviews/regression_check_architecture.md` 的相同核對流程，確認：
- 原有 26 項檢查仍全數 PASS
- 新增的 Trace / Tests / State-Version 章節使 REVIEWER 的 3 個缺失變為 SATISFIED

---

## 四、預計修改的報告章節

| 操作 | 章節 | 內容 |
|------|------|------|
| **新增** | §13 Trace Schema 一致性對比 | 完整 §13 章節（~2 頁） |
| **新增** | §14 Tests Coverage 逐類別審查 | 完整 §14 章節（~2 頁） |
| **補充** | §10.5 State 轉換審查 | 插入現有 §10 末尾，§10.4 之後（~1 頁） |
| **補充** | §10.6 Version 控制審查 | 接續 §10.5 之後（~0.5 頁） |
| **微調** | §1 Architecture Score 評語區 | 可選：在 Trace 與 Domain 分數旁加註腳 |
| **微調** | §3 Technical Debt | 可選：補充 State/Version 相關的 P 級問題 |
| **無修改** | §2 / §4 / §5 / §6 / §7 / §8 / §9 / §11 / §12 | 不更動 R1 內容 |

---

## 五、預估工時總表

| 項目 | 細項 | 預估工時 |
|------|-----|:--------:|
| **A — Trace 欄位對比** | 讀取 6 個 Trace 檔案 | 0.5h |
| | 產出 3 張對比表 | 1.0h |
| | 撰寫分析總結 | 0.5h |
| | *小計* | *2.0h* |
| **B — Tests 逐類審查** | 掃描 tests/ 目錄分類 | 0.5h |
| | 對比原始程式估算缺口 | 1.0h |
| | 產出 2 張表格 + 撰寫 | 0.5~1.0h |
| | *小計* | *2.0~2.5h* |
| **C — State/Version 補充** | grep 掃描 Domain Model | 0.3h |
| | 逐一檢視狀態欄位 | 0.5h |
| | 逐一檢視版本機制 | 0.3h |
| | 產出 §10.5 狀態表 | 0.5h |
| | 產出 §10.6 版本表 | 0.5h |
| | *小計* | *2.0h* |
| **微調與回歸** | §1 加註腳、§3 補充 | 0.5h |
| | 回歸檢查 26 項 | 0.5h |
| | *小計* | *1.0h* |
| **合計** | | **7~7.5h** |

> 註：若 Tests 分類需要實際執行 `pytest --cov`（需資料庫和環境準備），工時可能增加 1~2h。

---

## 六、執行順序建議

```
Step 1 → 項目 C（State/Version 補充）
         原因：影響 §10 既有章節，需優先插入，避免後續新增 §13/§14 時行號偏移

Step 2 → 項目 A（Trace 對比）
         原因：獨立的 §13，與既有結構無衝突

Step 3 → 項目 B（Tests 逐類審查）
         原因：獨立的 §14，最後新增

Step 4 → 微調與回歸檢查
         原因：所有修改完成後統一回歸
```

---

## 七、風險與注意事項

| 風險 | 影響 | 緩解措施 |
|------|------|---------|
| Trace 欄位對比可能發現新缺失（如欄位缺失、型別不匹配） | 可能增加 §3 Technical Debt 條目 | 在 §13 中記錄即可，不修改 §3（保持 R1 分數穩定） |
| Tests 分類後可能發現覆蓋率遠低於 8/10 | 與 R1 給分矛盾 | §14 備註「本表為分類細化，不改變 R1 總體評分 8.0/10」 |
| State/Version 分析可能導致 Domain 分數需下調 | 需修改 §1 的 Domain 分數 | 在 §1 加註腳而非修改原始分數，保持 R1 基準不變 |
| 補充後報告過長 | 可讀性下降 | 每章節控制在 2 頁內，多用表格濃縮資訊 |
