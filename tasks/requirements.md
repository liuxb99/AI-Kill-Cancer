# AI-Kill-Cancer × KnowGraphGo — Phase 3D Graph Correctness Hardening

AI-Kill-Cancer Repository：https://github.com/liuxb99/AI-Kill-Cancer（master, Base Commit: 5882612a42df044a7acdabb85a15ebd2a24acc8f）
KnowGraphGo Repository：https://github.com/liuxb99/KnowGraphGo（main, Base Commit: 4b63405d3f4e6186ba2488b068f6046ecd7a49cf）

目前審查結果：Phase 3D PARTIAL，ChatGPT Review Score 約 60/100，Accepted NO，Ready for Treatment Plan NO。

本輪任務：Phase 3D Graph Correctness Hardening
本輪不是重新設計 Outbox，不是 Treatment Plan。
只修知識圖譜的：Identity, Relations, Idempotency, Provenance, Query Consistency, Worker Correctness, Cross-repository Integration。

---

## 一、工作方式
嚴格遵守兩個 Repository 各自的 AGENTS.md 與既有流程。一次完成。不要中途回報。完成兩個 Repository、測試、CI、Commit、Push 後一次回報。不得自行開始下一階段。

## 二、目前已確認的 P0 問題
P0-1：Entity ID 每次隨機產生（graph.NewEntityID() / graph.NewRelationID()）→ 必須改成 Deterministic Entity/Relation ID
P0-2：Relation Target 指向不存在的隨機 Entity（To: graph.NewEntityID() 但 Target Entity 未加入 GraphDelta）
P0-3：Python Query ID 與 Graph ID 不一致（Python 用 patient_id/recommendation_id/consensus_id 但 Graph 內部是隨機 UUID）
P0-4：Provenance 不完整（只有 ProvenanceImported，缺少 event_id/event_type/schema_version/source_system/source_table/source_id/actor_id/correlation_id/causation_id/occurred_at）
P0-5：跨倉庫 CI checkout 分支錯誤（CI 用 ref: master 但 KnowGraphGo 正式分支是 main，且未 pin 特定 Commit）

## 三、Deterministic ID 設計
在 KnowGraphGo 建立 ClinicalIDFactory，提供 PatientID/RecommendationID/ClinicalDecisionID/ConsensusID/OpinionID/SpecialtyID/DrugID/EvidenceID/VariantID 以及 RelationID 方法。
使用 UUIDv5 + 固定 Namespace UUID + 標準化 key。
格式例如：clinical:patient:{patient_id}、clinical:recommendation:{recommendation_id} 等。
要求：相同輸入永遠得到相同 ID、不同 Entity Kind 不得 collision、大小寫與空白需標準化、空 ID 必須拒絕。
不得依賴 runtime random UUID、database auto increment、event_id 作為 entity identity。

## 四、真正建立 Target Entities
Patient Event：建立 Patient Entity（patient_id, display_name/pseudonym, sex, age_range, cancer_type, source_system, source_id）
Recommendation Event：建立/upsert Recommendation + Patient + Drug + Evidence Entities，Relation：FOR_PATIENT / RECOMMENDS / SUPPORTED_BY
Clinical Decision Event：建立/upsert ClinicalDecision + Patient + Recommendation + Evidence Entities，Relation：FOR_PATIENT / BASED_ON / SUPPORTED_BY
Tumor Board Consensus Event：建立/upsert Consensus + Patient + ClinicalDecision + SpecialistOpinion + Specialty + Evidence Entities，Relation：FOR_PATIENT / DERIVED_FROM / HAS_OPINION / PROVIDED_BY_SPECIALTY / SUPPORTED_BY
若 payload 缺少 opinion_id / specialty / evidence_ids，須在 AI-Kill-Cancer Event Payload 中補足。

## 五、GraphDelta 完整性規則
每個 Relation.From/To 必須在本次 Delta 中存在或可由 deterministic ID 對應既有節點。
所有 Relation 依賴的 Entity 全部加入本次 GraphDelta 作 Upsert。
不得假設 patient.created 一定先執行。

## 六、Idempotent Replay
測試：Apply 同一 patient.created 兩次 → Entity 數量不增加
Apply 同一 recommendation.created 兩次 → 不重複
Apply created 後再 apply updated → 同一 Entity 被更新，不新增第二個
Full rebuild 執行兩次 → Entity/Relation 數量一致
驗收：ID 完全一致、Count 一致、Properties 更新正確

## 七、Provenance 正式設計
每個 Entity Properties 保存：source_system, source_table, source_id, event_id, event_type, schema_version, actor_id, correlation_id, causation_id, occurred_at, aggregate_type, aggregate_id
每個 Relation 也必須保存對應 Provenance。
Evidence Entity 保存：evidence_id, source, citation, evidence_level, confidence

## 八、AI-Kill-Cancer Outbox Schema 補強
Outbox 新增欄位：correlation_id, causation_id, occurred_at
如需改 DB：新增 Migration 022（不得修改 Migration 021）
Worker 重建 ClinicalGraphEvent 時完整傳遞所有欄位。

## 九、Event Payload 必須與真實模型一致
逐一檢查 RecommendationService / ClinicalDecisionService / TumorBoardConsensusService 的 Domain Model 欄位。
不得使用不存在或永遠為空的 title/description/drug_ids/evidence_ids/opinion_id。
Recommendation Event：recommendation_id, patient_id, recommended_drugs, evidence_references, rank/score
Clinical Decision Event：decision_id, patient_id, recommendation_id, decision_type, rationale, evidence_references, contraindications, alternatives
Consensus Event：consensus_id, patient_id, clinical_decision_id, final_recommendation, consensus_status, consensus_score, supporting_evidence, specialist_opinions, participating_specialties

## 十、Python Query ID 統一
建立共享規格文件 docs/clinical-graph-id-spec.md。
定義 UUID namespace、canonical key format、normalization rules、UUID version、relation key format。
Python 實作 ClinicalGraphIDFactory，查詢時用 ClinicalGraphIDFactory.patient(patient_id) 等。
必須有跨語言測試：Python ID == Go ID（至少測 patient/recommendation/decision/consensus/opinion/specialty/drug/evidence/relation）

## 十一、Explain Query 修正
不得把 Entity ID 當 Relation ID。
Recommendation Explain 至少找到 Patient/Recommendation/Drug/Evidence/Clinical Decision
Consensus Explain 至少找到 ClinicalDecision/Consensus/Opinions/Specialties/Evidence
不得只因 CLI 回傳 success 就標記 projection_status = connected，必須確認 entities 或 path 非空。

## 十二、ClinicalGraphClient 非阻塞化
async def 內使用 subprocess.run() → 改為 asyncio.create_subprocess_exec()
要求：shell=False, stdin pipe, stdout pipe, stderr pipe, timeout, process kill on timeout, return code validation, JSON parse validation
新增測試：success, non-zero exit, timeout, invalid JSON, CLI not found, large stdout

## 十三、Worker Transaction 修正
Claim Transaction：SELECT FOR UPDATE SKIP LOCKED → status=processing → claim_token → processing_started_at → commit
External Work：不持有 DB lock → 執行 CLI
Result Transaction：成功→completed，失敗→failed/pending retry
新增 Outbox 欄位：claim_token, processing_started_at, last_failed_at（Migration 022）
支援 stale recovery：processing 超過 timeout → 重新變為 pending

## 十四、Failed Events 狀態一致性
mark_failed() 將事件設為 failed（不是 pending），status 統一為：pending/processing/failed/completed/dead_letter
claim_pending 查 status in (pending, failed) AND available_at <= now

## 十五、Status API 真實健康度
不得固定 {"status": "operational"}
Status 必須結合：Outbox pending/failed/dead_letter, CLI availability, clinical verify, last completed projection time, oldest pending event age, stale processing count
狀態：operational / degraded / unavailable

## 十六、CI 修正
先完成 KnowGraphGo → Push → 取得 SHA → AI-Kill-Cancer CI ref 固定該 SHA → 再完成 AI-Kill-Cancer Commit
不得使用 ref: master 或浮動 branch。

## 十七、真正跨倉庫 Integration Test
Build CLI → 建立臨時 SQLite Graph DB → AI-Kill-Cancer 產生 Event → CLI apply → 再次 apply → CLI query → 驗證冪等 + Digital Thread
事件順序：patient.created → recommendation.created → clinical_decision.created → tumor_board_consensus.created
驗證：所有 Relation Target 存在、無 orphan relation、相同 Event 重放後 Count 不變、Provenance 可讀

## 十八、KnowGraphGo 測試要求
Deterministic ID golden tests, Patient/Recommendation/Decision/Consensus/Opinion/Specialty/Evidence/Drug mapping tests, Relation target integrity test, Duplicate replay test, Updated event upsert test, Rebuild idempotency test, Provenance test, Unknown schema version rejection, Sensitive payload rejection
必須執行 go test ./... / go vet ./... / go build ./cmd/knowgraph

## 十九、AI-Kill-Cancer 測試要求
Outbox full provenance round-trip, Migration 022 upgrade/downgrade/re-upgrade, Worker short transaction test, Concurrent worker claim test, Stale processing recovery, Failed event visibility, Async subprocess timeout, Python/Go ID parity, Recommendation/Decision/Consensus payload correctness, Patient thread real graph query, Recommendation explain real path, Consensus explain real path, Restart recovery with graph projection

## 二十、Commit Scope
AI-Kill-Cancer：Migration 022, Outbox model/repository/service, Graph Event DTO, Graph client, Worker, Query API, Status API, Service event payload, Tests, CI, Phase 3D review/workflow documents
KnowGraphGo：Clinical ID Factory, Clinical Adapter, Clinical Ontology, Clinical CLI, 相關 tests/docs
不得混入 Treatment Plan/Phase 3E/其他功能/AGENTS.md 大型修改

## 二十一、Reviewer Gate
逐項確認 20 項（Entity ID deterministic, Relation ID deterministic, Same Event replay idempotent, created→updated 不重複, 所有 Relation Target 存在, Patient→Recommendation 正確, Recommendation→Drug/Evidence 正確, Decision→Recommendation 正確, Consensus→Decision 正確, Consensus→Opinion→Specialty 正確, Python ID==Go ID, Provenance 完整, Event Payload 來自真實 Domain Model, async subprocess 不阻塞, Worker 不長時間持有 DB lock, stale processing 可恢復, failed events API 可見, Status API 反映 CLI 真實狀態, CI pin KnowGraphGo SHA, Cross-repository Digital Thread 測試通過）
以下任一未完成則滿足需求=NO、Reviewer 最高 89：Deterministic ID / Relation Integrity / Idempotency / Digital Thread / Cross-language ID parity / Cross-repository integration
Reviewer 必須 >=95 才可停止。

## 二十二、Git 提交順序
先 KnowGraphGo：fix(clinical): make graph projection deterministic and idempotent → push origin/main
取得 SHA → AI-Kill-Cancer CI pin 該 SHA
AI-Kill-Cancer：fix(phase3d): harden graph identity projection and worker → push origin/master
禁止 force push / rebase / 修改舊 Commit

## 二十三、完成後回報格式
輸出 KnowGraphGo SHA、AI-Kill-Cancer SHA、Deterministic ID Algorithm、UUID Namespace、Python/Go ID Parity、Entity/Relation Kinds、Orphan Relation Count、Idempotency Results、Digital Thread Paths、Provenance Fields、Migration 022、Worker Correctness、Async Result、Status API、Explain Results、測試結果、CI Run IDs、Reviewer Score
最終判定：Phase 3D Graph Correctness Hardening：PASS / PARTIAL / FAIL
Phase 3D Accepted：YES / NO
Ready for Treatment Plan：YES / NO

只有 Deterministic ID PASS / Relation Integrity PASS / Idempotent Replay PASS / Digital Thread PASS / Provenance PASS / Python/Go ID Parity PASS / Worker Correctness PASS / Cross-repository CI PASS / Reviewer >=95 才允許 YES。

推送後停止。不得自行開始 Treatment Plan。
