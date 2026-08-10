# AI-Kill-Cancer 研究深度缺口與補完路線

更新日期：2026-08-10

## 1. 目標定義

本文件衡量的不是「頁面是否齊全」或「1.0.3 是否可發布」，而是 AI-Kill-Cancer 距離原始目標——**可持續吸收癌症研究資料、形成可追溯研究推理、提出可驗證假說、比較 cohort、處理證據衝突、用 outcome 回饋修正研究優先級的 AI 癌症研究平台**——還差多少研究深度。

所有能力均限定為 research-only。不得把 cohort association、hypothesis score、evidence consensus 或 outcome feedback 解讀為臨床診斷、預後或治療建議。

## 2. 當前深度評估

截至本文件建立時：

- 軟體平台／工程架構：約 90～95%；
- PTC 資料整合與研究工作台：約 85～90%；
- Evidence → Recommendation → Decision 可追溯鏈：約 80～90%；
- 外部癌症知識源／工具整合：約 75～85%；
- 真實 cohort / longitudinal research reasoning：約 60～70%；
- 自動研究假說生成與證據衝突處理：約 55～70%；
- 「AI 癌症研究員」自主研究閉環：約 50～65%。

綜合原始產品目標，研究深度約完成 70～80%，剩餘深度缺口約 20～30%。

## 3. 深度缺口

### D1 — Outcome Feedback Loop

現況：PTC research model 已保存 de-identified outcome，cohort matching 也刻意 outcome-blind，並在 cohort 選定後才做描述性 outcome aggregation；這是正確的防洩漏基礎。

缺口：尚缺「研究結論／假說 → 後續 outcome observation → research signal 更新」的明確分析層。

完成條件：

- 保持 cohort selection outcome-blind；
- cohort 選定後可計算 outcome signal summary；
- outcome signal 必須標註 descriptive / association-only；
- 不生成 patient-level prognosis；
- 每個 signal 有 numerator / denominator / missingness / provenance；
- 可輸出下一輪研究優先級，而非治療建議。

### D2 — Evidence Conflict Resolution

現況：Evidence、Evidence Matrix、Recommendation trace 已存在，但不同來源支持／反對同一 claim 時，缺少統一 conflict object。

完成條件：

- 將同一 research claim 的 supports / opposes / unknown 分組；
- 輸出 conflict severity、source diversity、agreement ratio；
- 不用簡單多數決掩蓋高等級反證；
- 明確列出 unresolved reasons；
- consensus 與 dissent 都必須可追溯到 evidence references。

### D3 — Hypothesis Generation

現況：系統有 reasoning / knowledge graph / cohort / evidence，但缺乏一個明確的「研究假說物件」。

完成條件：

- 從 cohort biomarker enrichment、outcome association、evidence conflict 產生 research hypothesis；
- hypothesis 具備 claim、rationale、supporting observations、counter-evidence、uncertainties；
- 有 falsification criteria；
- 有 evidence gap / next-data-needed；
- 僅產生研究假說，不產生臨床決策。

### D4 — Cross-patient Cohort Reasoning

現況：已有 outcome-blind similar-case scoring 與 cohort summary。

缺口：尚缺 gene / variant / stage / outcome 的 cohort-level enrichment 與分層比較。

完成條件：

- 支援 biomarker-positive vs biomarker-negative 分組；
- 計算 case counts、outcome availability、event proportions；
- 明確顯示 missingness；
- 小樣本必須標低可信度；
- 不做 causal inference；
- 可供 hypothesis generator 消費。

### D5 — Longitudinal Research Timeline

現況：已有 PTC timeline API。

缺口：需要把 timeline 從「事件展示」提升為「研究狀態轉移」：資料到達、variant 變更、evidence 更新、hypothesis 生成／反駁、outcome observation 都應形成可追溯事件。

完成條件：

- standardized research event schema；
- event provenance；
- event ordering / observed-at；
- hypothesis/evidence/outcome 關聯；
- restart persistence regression。

### D6 — Autonomous Research Loop

缺口：目前各模組已存在，但還缺一個受控 orchestration：

```text
Data ingest
→ cohort scan
→ conflict scan
→ hypothesis generation
→ evidence-gap identification
→ next research task
→ new evidence/outcome
→ re-evaluate
```

完成條件：

- 每一步輸出 machine-readable trace；
- 不自動執行臨床行為；
- external adapter failure 可降級但不可偽造資料；
- deterministic / testable；
- 可重跑並比較 hypothesis version。

## 4. 自動補完順序

```text
D1 outcome research signal
→ D4 cohort stratification
→ D2 evidence conflict engine
→ D3 hypothesis engine
→ D5 longitudinal research events
→ D6 autonomous research loop
→ API wiring
→ regression / restart persistence
→ frontend research workbench exposure
→ Local Verification Gate
→ depth-gap document update
```

## 5. 深度完成標準

只有以下條件全部滿足，才能把研究深度標記為 `DEPTH COMPLETE`：

- [ ] outcome feedback analysis 已實作且 outcome-blind selection boundary 不被破壞；
- [ ] cohort stratification 可重現；
- [ ] evidence conflict engine 可追溯 supports/opposes；
- [ ] hypothesis object 具 falsification criteria 與 next-data-needed；
- [ ] longitudinal research event 可持久化並跨 restart；
- [ ] autonomous research loop 有 machine-readable trace；
- [ ] 所有新 API 保持 research-only disclaimer；
- [ ] backend regression 全綠；
- [ ] frontend regression / build 全綠；
- [ ] latest Local Verification Gate PASS。

## 6. 安全與科學邊界

1. Outcome association 不是 prognosis。
2. Cohort enrichment 不是 causal inference。
3. Hypothesis score 不是 treatment recommendation。
4. Evidence consensus 不能消除 dissent evidence。
5. 小樣本與 missing data 必須顯式降級可信度。
6. Synthetic demo 不可混入 real research evidence。
7. 本專案研究深度完成只代表軟體研究工作流成熟度，不代表臨床有效性或監管認可。
