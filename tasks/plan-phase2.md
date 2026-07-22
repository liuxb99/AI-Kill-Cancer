# Phase 2 — Multi-Agent Clinical Decision Workspace 详细实施计划

> **基线版本**: 322a59a3a066bcf802512cf375c3e1dc330df794  
> **目标**: 将 Phase 1 Clinical Workbench 的孤立模块转变为协作式临床决策工作空间

---

## 架构总览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         Phase 2 核心工作流                                    │
│                                                                             │
│  Case ─→ ClinicalContextBuilder ─→ EvidenceCollector ─→ Multi-Agent         │
│                               │                    │     Discussion          │
│                               │                    │         │              │
│                               ▼                    ▼         ▼              │
│                         ClinicalContext      EvidenceBundle  6 Agents       │
│                               │                    │         │              │
│                               └────────┬───────────┘         │              │
│                                        │                     │              │
│                                        ▼                     │              │
│                                  ConsensusEngine ◄───────────┘              │
│                                        │                                    │
│                                        ▼                                    │
│                              RecommendationGenerator                        │
│                                        │                                    │
│                                        ▼                                    │
│                                  Digital Thread                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 阶段划分

| 阶段 | 名称 | 任务数 | 估计工时 | 描述 |
|------|------|--------|---------|------|
| **Phase 2a** | 核心后端基础 | 6 | ~36h | ClinicalContextBuilder, EvidenceCollector, 数据库迁移, API 端点 |
| **Phase 2b** | 多代理系统 | 8 | ~48h | 6 个 Agent, ConsensusEngine, RecommendationGenerator |
| **Phase 2c** | Digital Thread | 3 | ~18h | 决策节点模型, 追踪服务, API |
| **Phase 2d** | 前端新分页 | 7 | ~32h | 6 个新 Tab 组件, 路由, API 客户端 |
| **Phase 2e** | 测试与整合 | 5 | ~24h | Unit/Integration/E2E 测试, CI 集成 |
| **总计** | | **29** | **~158h** | |

---

## 任务清单

### Phase 2a: 核心后端基础

---

#### TASK-P2-001: ClinicalContextBuilder 数据模型

| 字段 | 值 |
|------|-----|
| **ID** | TASK-P2-001 |
| **名称** | 定义 ClinicalContext 数据模型 |
| **描述** | 创建 `ClinicalContext` Pydantic 模型，包含所有临床上下文数据：诊断、分期、病理、生物标志物、变异、治疗史、用药、过敏史、ECOG 评分、年龄、性别。此模型将被所有下游模块消费，避免重复查数据库。 |
| **依赖** | 无（基线 322a59a3） |
| **预估工时** | 4h |
| **负责角色** | db-modeler |
| **产出文件** | `src/backend/clinical/models.py`（新增） |
| **验收标准** | `ClinicalContext` 模型定义完整，所有字段有 type hint 和 validation；可通过 `pytest` 创建实例 |
| **风险** | 需与 Phase 1 的 CancerCaseModel、PatientModel 等对齐字段名 |

**详细说明**:
- `ClinicalContext` 是一个不可变的 frozen dataclass / Pydantic model
- 包含字段：
  - `case_id: str`
  - `patient_id: str`
  - `age: int`, `gender: str`
  - `diagnosis: str`, `stage: str`, `histology: str`, `cancer_type: str`
  - `oncotree_code: Optional[str]`
  - `biomarkers: list[dict]`
  - `variants: list[dict]` — 每个包含 gene_symbol, hgvs, protein_change, vaf, clinical_significance
  - `treatment_history: list[dict]`
  - `current_medications: list[dict]`
  - `allergies: list[str]`
  - `ecog_score: Optional[int]`
  - `metastatic_sites: list[str]`
  - `recurrence_status: Optional[str]`
  - `clinical_notes: Optional[str]`
  - `context_hash: str` — SHA256 of serialized context for traceability
- 方法 `freeze() -> str` 计算 context_hash
- 导入路径: `from src.backend.clinical.models import ClinicalContext`

---

#### TASK-P2-002: CaseContextBuilder 服务

| 字段 | 值 |
|------|-----|
| **ID** | TASK-P2-002 |
| **名称** | 实现 CaseContextBuilder 服务 |
| **描述** | 实现 `CaseContextBuilder` 类，从数据库加载 Case → Patient → Variants → 组装 ClinicalContext。所有下游模块必须通过此 builder 获取上下文。 |
| **依赖** | TASK-P2-001 |
| **预估工时** | 6h |
| **负责角色** | backend-logic |
| **产出文件** | `src/backend/clinical/builder.py`（新增） |
| **验收标准** | 给定有效的 case_id，能组装完整的 ClinicalContext；无效 ID 返回空上下文（不抛异常）；所有字段从真实数据库获取，无 fake data |
| **风险** | 需处理 Phase 1 数据库中某些字段可能为 NULL 的情况 |

**详细说明**:
- `CaseContextBuilder(db: AsyncSession)` 接收数据库 session
- 方法 `async build(case_id: str) -> ClinicalContext`:
  1. 调用 `CancerCaseRepository.get(case_id)` 获取案件
  2. 调用 `PatientRepository.get(case.patient_id)` 获取患者信息
  3. 调用 `VariantRepository.find_by_case(case_id)` 获取变异列表
  4. 组装所有字段到 ClinicalContext
  5. 调用 `context.freeze()` 计算 context_hash
  6. 返回 ClinicalContext
- 若 case_id 无效 → 返回 `ClinicalContext()`（空实例，非 None）
- 不触发任何外部 API 调用，纯数据库查询
- 导入路径: `from src.backend.clinical.builder import CaseContextBuilder`

---

#### TASK-P2-003: EvidenceBundle 数据模型

| 字段 | 值 |
|------|-----|
| **ID** | TASK-P2-003 |
| **名称** | 定义 EvidenceBundle 证据包模型 |
| **描述** | 创建 `EvidenceBundle` Pydantic 模型，整合 NCCN, ESMO, FDA, ClinVar, CIViC, OncoKB, PMIDs, internal evidence 来源。每个证据项包含 evidence level, citation, confidence, conflicts 信息。 |
| **依赖** | TASK-P2-001 |
| **预估工时** | 4h |
| **负责角色** | db-modeler |
| **产出文件** | `src/backend/clinical/evidence_models.py`（新增） |
| **验收标准** | 模型定义完整；支持按来源、基因、药物筛选；可通过 pytest 创建 |
| **风险** | 需兼容 Phase 1 EvidenceItemModel/EvidenceItemResponse 的字段命名 |

**详细说明**:
- `EvidenceItem` 模型:
  - `source: str` — NCCN, ESMO, FDA, ClinVar, CIViC, OncoKB, PubMed, Internal
  - `source_record_id: Optional[str]`
  - `gene_symbol: Optional[str]`
  - `drug_name: Optional[str]`
  - `disease: Optional[str]`
  - `evidence_type: str` — predictive, prognostic, diagnostic, etc.
  - `evidence_direction: str` — supporting, conflicting, neutral
  - `evidence_level: str` — 归一化级别 (A, B, C, D, E 或 Level_1-5)
  - `source_native_level: Optional[str]`
  - `clinical_significance: Optional[str]`
  - `citation: Optional[str]`
  - `pmid: Optional[str]`
  - `url: Optional[str]`
  - `confidence: Optional[str]` — high, medium, low
  - `match_level: Optional[str]` — exact_variant, gene_level_only, etc.
  - `conflict_status: Optional[str]` — supporting, conflicting, uncertain
  - `description: Optional[str]`
- `EvidenceBundle` 模型:
  - `items: list[EvidenceItem]`
  - `total_count: int`
  - `by_source: dict[str, list[EvidenceItem]]` — 按来源分组的证据
  - `by_gene: dict[str, list[EvidenceItem]]`
  - `by_drug: dict[str, list[EvidenceItem]]`
  - `highest_level: Optional[str]`
  - `conflicts_summary: list[dict]` — 从 ConflictAnalyzer 获取
  - `retrieved_at: str`
  - `context_hash: Optional[str]` — 关联的 ClinicalContext hash
- 方法 `filter(gene=None, drug=None, source=None, min_level=None) -> EvidenceBundle`

---

#### TASK-P2-004: EvidenceCollector 服务

| 字段 | 值 |
|------|-----|
| **ID** | TASK-P2-004 |
| **名称** | 实现 EvidenceCollector 服务 |
| **描述** | 实现 `EvidenceCollector` 类，从 Phase 1 的 evidence 模块、knowledge 模块、以及各 adapter 收集证据，组装为 EvidenceBundle。利用现有 EvidenceMerger、KnowledgeRepository 等基础设施，不重写。 |
| **依赖** | TASK-P2-002, TASK-P2-003 |
| **预估工时** | 8h |
| **负责角色** | backend-logic |
| **产出文件** | `src/backend/clinical/collector.py`（新增） |
| **验收标准** | 给定 ClinicalContext，能从数据库和 knowledge sources 收集证据；返回 EvidenceBundle；不使用 mock/fake data；通过现有缓存机制 |
| **风险** | 外部 API (ClinVar, PubMed) 可能不可用；需 graceful degradation |

**详细说明**:
- `EvidenceCollector(db: AsyncSession)` 接收数据库 session
- 方法 `async collect(context: ClinicalContext) -> EvidenceBundle`:
  1. 遍历 context.variants 中的 gene_symbol
  2. 调用 `EvidenceMerger.merge_gene_evidence()` 获取 CIViC/DGIdb 证据
  3. 调用 `KnowledgeRepository` 获取 ClinVar、PubMed 数据
  4. 调用 ConflictAnalyzer 分析冲突
  5. 按 source、gene、drug 分组
  6. 返回 EvidenceBundle
- 方法 `async collect_by_variant(gene: str, hgvs: str) -> EvidenceBundle` — 单变异收集
- 使用 Phase 1 的 TTLCache (gene_cache, variant_cache) 减少重复查询
- 外部 API 失败时记录日志但不中断流程，返回部分证据
- 不需引入 NCCN/ESMO/OncoKB 的实际 adapter（这些可能需要许可证），预留接口但返回空列表 + warning

---

#### TASK-P2-005: ClinicalContext + EvidenceBundle API 端点

| 字段 | 值 |
|------|-----|
| **ID** | TASK-P2-005 |
| **名称** | 新增 Clinical 模块 API 端点 |
| **描述** | 在 `src/backend/api/v1/` 下新增 `clinical.py` 路由模块，提供 ClinicalContext 和 EvidenceBundle 的 REST API。注册到 `router.py`。 |
| **依赖** | TASK-P2-002, TASK-P2-004 |
| **预估工时** | 6h |
| **负责角色** | api-designer |
| **产出文件** | `src/backend/api/v1/clinical.py`（新增）；修改 `src/backend/api/v1/router.py` |
| **验收标准** | `GET /api/v1/clinical/context/{case_id}` 返回 ClinicalContext JSON；`GET /api/v1/clinical/evidence/{case_id}` 返回 EvidenceBundle JSON；遵循现有 auth 模式（require_case_access）；通过 ruff check |
| **风险** | 无 |

**详细说明**:
- 新路由文件 `src/backend/api/v1/clinical.py`
- `APIRouter(prefix="/clinical", tags=["clinical"])`
- 端点:
  1. `GET /context/{case_id}` → 返回 ClinicalContext
     - 调用 CaseContextBuilder.build(case_id)
     - 依赖: `require_case_access(CaseRole.VIEWER)`
  2. `GET /evidence/{case_id}` → 返回 EvidenceBundle
     - 调用 CaseContextBuilder.build(case_id) 获取上下文
     - 调用 EvidenceCollector.collect(context) 获取证据包
  3. `GET /evidence/gene/{gene_symbol}` → 按基因查询证据包
     - 直接调用 EvidenceCollector.collect_by_variant()
- 在 `router.py` 中添加 `from src.backend.api.v1.clinical import router as clinical_router` 和 `router.include_router(clinical_router)`

---

#### TASK-P2-006: 数据库迁移 — Phase 2 clinical 扩展

| 字段 | 值 |
|------|-----|
| **ID** | TASK-P2-006 |
| **名称** | Phase 2 数据库迁移脚本 |
| **描述** | 创建新的 Alembic 迁移脚本 `016_phase2_clinical_workspace.py`，添加 Phase 2 所需的数据库表：DecisionNodeModel、AgentOpinionModel、ConsensusResultModel、RecommendationModel。不在已有表上做破坏性修改。 |
| **依赖** | TASK-P2-001, TASK-P2-003 |
| **预估工时** | 8h |
| **负责角色** | db-modeler |
| **产出文件** | `migrations/versions/016_phase2_clinical_workspace.py`（新增） |
| **验收标准** | 迁移成功执行 `alembic upgrade head`；所有新表创建完成；可回滚 `alembic downgrade -1` |
| **风险** | 与 Phase 1 现有表的 foreign key 关系需准确 |

**详细说明**:
- 新增表:
  1. `clinical_decision_nodes` — Digital Thread 决策节点
     - id, case_id, parent_id, node_type, input_snapshot (JSON), evidence_snapshot (JSON), agent_id, agent_type, reasoning, confidence, decision_label, timestamp, context_hash
  2. `clinical_agent_opinions` — Agent 意见
     - id, case_id, run_id, agent_type, agent_version, summary, pros (JSON), cons (JSON), confidence, references (JSON), created_at
  3. `clinical_consensus_results` — 共识结果
     - id, case_id, run_id, agreement_level, conflicts (JSON), confidence, recommended_option (JSON), alternative_options (JSON), unresolved_questions (JSON), created_at
  4. `clinical_recommendations` — 治疗方案推荐
     - id, case_id, run_id, recommendation_type, first_line (JSON), second_line (JSON), clinical_trial (JSON), supporting_evidence (JSON), expected_benefit (JSON), potential_risk (JSON), monitoring_plan (JSON), structured_json (JSON), markdown (Text), created_at
- 所有表使用 CompatUUID 主键
- 添加 `context_hash` 索引
- 迁移脚本包含 upgrade() 和 downgrade()

---

### Phase 2b: 多代理系统

---

#### TASK-P2-007: Agent 基础框架

| 字段 | 值 |
|------|-----|
| **ID** | TASK-P2-007 |
| **名称** | Agent 基类与 AgentOpinion 模型 |
| **描述** | 定义 `BaseAgent` 抽象基类和 `AgentOpinion` Pydantic 模型。Agent 基类提供通用接口：输入 ClinicalContext + EvidenceBundle，输出 AgentOpinion。Agent 不可直接修改彼此状态。 |
| **依赖** | TASK-P2-001, TASK-P2-003 |
| **预估工时** | 6h |
| **负责角色** | backend-logic |
| **产出文件** | `src/backend/agents/__init__.py`（新增），`src/backend/agents/base.py`（新增），`src/backend/agents/models.py`（新增） |
| **验收标准** | BaseAgent 抽象类定义完整；AgentOpinion 模型包含所有必要字段；派生类可实现 analyze() 方法；通过 ruff check、pytest |
| **风险** | 无 |

**详细说明**:
- `src/backend/agents/` 包结构:
  - `__init__.py` — 导出所有 Agent 类
  - `base.py` — BaseAgent 抽象基类
  - `models.py` — AgentOpinion 模型
  - `diagnosis_agent.py`
  - `variant_agent.py`
  - `drug_agent.py`
  - `resistance_agent.py`
  - `guideline_agent.py`
  - `clinical_trial_agent.py`
  - `orchestrator.py` — Agent 编排器

- `AgentOpinion` 模型:
  - `agent_type: str`
  - `agent_version: str`
  - `summary: str` — 该 Agent 的分析摘要
  - `pros: list[str]` — 支持的理由
  - `cons: list[str]` — 反对/风险的理由
  - `confidence: float` — 0.0 ~ 1.0
  - `references: list[dict]` — 引用的证据（每个含 evidence_id, source, summary）
  - `key_findings: list[str]`
  - `uncertainties: list[str]`
  - `context_hash: Optional[str]`
  - `created_at: str`

- `BaseAgent` 抽象类:
  - `__init__(self, config: Optional[dict] = None)`
  - `@abstractmethod async analyze(context: ClinicalContext, evidence: EvidenceBundle) -> AgentOpinion`
  - `@property name(self) -> str`
  - `@property version(self) -> str`
  - Agent 之间不共享状态；每个 agent 独立运行

---

#### TASK-P2-008: 六个具体 Agent 实现

| 字段 | 值 |
|------|-----|
| **ID** | TASK-P2-008 |
| **名称** | 实现六个临床决策 Agent |
| **描述** | 分别实现 DiagnosisAgent, VariantAgent, DrugAgent, ResistanceAgent, GuidelineAgent, ClinicalTrialAgent。每个 Agent 接收 ClinicalContext + EvidenceBundle，输出 AgentOpinion。Agent 使用 LLM 辅助分析（通过 Phase 1 的 LLMAdapter）但不做最终决策。 |
| **依赖** | TASK-P2-007 |
| **预估工时** | 16h |
| **负责角色** | backend-logic |
| **产出文件** | `src/backend/agents/diagnosis_agent.py`, `src/backend/agents/variant_agent.py`, `src/backend/agents/drug_agent.py`, `src/backend/agents/resistance_agent.py`, `src/backend/agents/guideline_agent.py`, `src/backend/agents/clinical_trial_agent.py`（均新增） |
| **验收标准** | 每个 Agent 继承 BaseAgent，实现 analyze()；LLM 不可用时返回结构化非 LLM 版本；Agent 间不共享状态；通过 pytest |
| **风险** | LLM 可能不可用；每个 Agent 需 graceful degradation |

**详细说明**:
1. **DiagnosisAgent** (`diagnosis_agent.py`)
   - 分析 ClinicalContext 中的 diagnosis, stage, histology, biomarkers
   - 对照 evidence 判断诊断准确性、完整性
   - 输出：诊断确认度、建议补充检查、鉴别诊断
   
2. **VariantAgent** (`variant_agent.py`)
   - 分析 variants 列表 + EvidenceBundle 中变异相关证据
   - 识别可靶向变异、驱动变异、VUS
   - 输出：变异解读、可靶向性评分、推荐检测方法

3. **DrugAgent** (`drug_agent.py`)
   - 利用 EvidenceBundle 中的 drug 证据 + Phase 1 DrugRankingEngine
   - 评估可用药物、匹配度、证据级别
   - 输出：候选药物列表（含证据级别、匹配度）、推荐排序

4. **ResistanceAgent** (`resistance_agent.py`)
   - 分析 variants 和 treatment_history 中的耐药信息
   - 识别已知耐药突变、潜在交叉耐药
   - 输出：耐药风险、已耐药药物、建议避免的药物

5. **GuidelineAgent** (`guideline_agent.py`)
   - 对照 ClinicalContext 查找适用临床指南（NCCN/ESMO）
   - 使用 Phase 1 knowledge 模块的 GuidelineItem 模型
   - 输出：适用指南、推荐方案、证据级别、指南版本

6. **ClinicalTrialAgent** (`clinical_trial_agent.py`)
   - 查询 ClinicalTrials.gov adapter 获取相关临床试验
   - 输出：匹配临床试验列表（含 NCT ID、phase、status、location）、入组条件匹配度

---

#### TASK-P2-009: Agent Orchestrator 编排器

| 字段 | 值 |
|------|-----|
| **ID** | TASK-P2-009 |
| **名称** | 实现 Agent Orchestrator 编排器 |
| **描述** | 实现 `AgentOrchestrator` 类，并行或串行调度 6 个 Agent，收集所有 AgentOpinion 列表。提供带超时的执行控制。 |
| **依赖** | TASK-P2-008 |
| **预估工时** | 6h |
| **负责角色** | backend-logic |
| **产出文件** | `src/backend/agents/orchestrator.py`（新增） |
| **验收标准** | 能同时运行 6 个 Agent；单个 Agent 超时不影响其他 Agent；返回完整 AgentOpinion[]；通过 pytest |
| **风险** | 6 个 Agent 同时运行可能消耗大量 LLM token；需超时控制 |

**详细说明**:
- `AgentOrchestrator` 类:
  - `__init__(self, agents: list[BaseAgent], config: Optional[dict] = None)`
  - `async run_all(context: ClinicalContext, evidence: EvidenceBundle, timeout: int = 60) -> list[AgentOpinion]`
    - 使用 `asyncio.gather()` 并行执行所有 Agent
    - 每个 Agent 有独立超时（默认 60s）
    - 超时的 Agent 返回带有 timeout 标记的 AgentOpinion
  - 注册所有 6 个 Agent 的工厂方法
  - 提供 `run_selected(agent_types: list[str], ...)` 运行指定子集

---

#### TASK-P2-010: ConsensusEngine 共识引擎

| 字段 | 值 |
|------|-----|
| **ID** | TASK-P2-010 |
| **名称** | 实现 ConsensusEngine 共识引擎 |
| **描述** | 实现 `ConsensusEngine` 类，输入 AgentOpinion[]，输出 ConsensusResult（含 agreement, conflicts, confidence, recommended option, alternative options, unresolved questions）。 |
| **依赖** | TASK-P2-009 |
| **预估工时** | 6h |
| **负责角色** | backend-logic |
| **产出文件** | `src/backend/agents/consensus.py`（新增），`src/backend/agents/models.py`（更新） |
| **验收标准** | 能计算 Agent 意见一致性；识别冲突；输出 ConsensusResult；通过 pytest |
| **风险** | Agent 意见高度分歧时的处理策略需明确 |

**详细说明**:
- `ConsensusResult` 模型（添加到 models.py）:
  - `run_id: str`
  - `case_id: str`
  - `agreement_level: str` — high, moderate, low, none
  - `agreement_score: float` — 0.0 ~ 1.0 量化一致性
  - `conflicts: list[dict]` — {agent_types, issue, severity}
  - `confidence: float` — 整体置信度
  - `recommended_option: dict` — {summary, supporting_agents, evidence_refs}
  - `alternative_options: list[dict]`
  - `unresolved_questions: list[str]`
  - `agent_count: int`
  - `context_hash: Optional[str]`
  - `created_at: str`

- `ConsensusEngine` 类:
  - `__init__(self, config: Optional[dict] = None)`
  - `async reach_consensus(opinions: list[AgentOpinion]) -> ConsensusResult`
  - 算法：
    1. 按 agent_type 分组
    2. 比较各 Agent 的 recommended drug/category
    3. 计算加权置信度（按 evidence count + agent confidence）
    4. 识别冲突（agent 间明显矛盾的意见）
    5. 确定 agreement_level
    6. 生成 recommended_option（最高置信度的选项）
    7. 收集替代方案和未解决问题
  - 不调用 LLM，纯算法驱动

---

#### TASK-P2-011: RecommendationGenerator 推荐生成器

| 字段 | 值 |
|------|-----|
| **ID** | TASK-P2-011 |
| **名称** | 实现 RecommendationGenerator |
| **描述** | 实现 `RecommendationGenerator` 类，输入 ConsensusResult + ClinicalContext + EvidenceBundle，输出结构化治疗方案：First-line, Second-line, Clinical Trial, Supporting Evidence, Expected Benefit, Potential Risk, Monitoring Plan。同时输出 structured JSON 和 markdown。 |
| **依赖** | TASK-P2-010 |
| **预估工时** | 6h |
| **负责角色** | backend-logic |
| **产出文件** | `src/backend/clinical/recommendation.py`（新增） |
| **验收标准** | 输出包含结构化的 JSON 和 markdown 两种格式；所有字段基于实际数据；不包含 fake/mock data；通过 pytest |
| **风险** | 无 |

**详细说明**:
- `TreatmentRecommendation` 模型（在 models.py 中增强）:
  - `first_line: list[dict]` — {drug, rationale, evidence_level, confidence}
  - `second_line: list[dict]`
  - `clinical_trial: list[dict]` — {nct_id, title, phase, rationale}
  - `supporting_evidence: list[dict]` — {evidence_id, source, summary}
  - `expected_benefit: list[str]`
  - `potential_risk: list[str]`
  - `monitoring_plan: list[str]`
  - `structured_json: dict` — 完整的结构化数据
  - `markdown: str` — 可读的 Markdown 格式报告

- `RecommendationGenerator` 类:
  - `__init__(self, config: Optional[dict] = None)`
  - `async generate(consensus: ConsensusResult, context: ClinicalContext, evidence: EvidenceBundle) -> TreatmentRecommendation`
  - 逻辑：
    1. 从 consensus.recommended_option 提取首选方案
    2. 从 alternative_options 提取二线方案
    3. 从 ClinicalTrialAgent 意见提取临床试验选项
    4. 从 EvidenceBundle 提取支持证据
    5. 从 DrugAgent/ResistanceAgent 提取 benefit/risk
    6. 组装 markdown

---

#### TASK-P2-012: Agents API 端点

| 字段 | 值 |
|------|-----|
| **ID** | TASK-P2-012 |
| **名称** | Agents 模块 API 端点 |
| **描述** | 在 `clinical.py` 中新增 Agents/Consensus/Recommendation 的 REST API 端点。 |
| **依赖** | TASK-P2-009, TASK-P2-010, TASK-P2-011 |
| **预估工时** | 4h |
| **负责角色** | api-designer |
| **产出文件** | 修改 `src/backend/api/v1/clinical.py`（新增端点） |
| **验收标准** | 各端点返回正确的结构化数据；遵循 auth 模式；通过 ruff check |
| **风险** | 同步 LLM 调用可能阻塞 API；需异步处理 |

**详细说明**:
- 新增端点:
  1. `POST /agents/run/{case_id}` — 运行所有 Agent
     - Body: `{agent_types: Optional[list[str]]}` — 指定运行哪些 Agent（默认全部）
     - 调用 AgentOrchestrator.run_all()
     - 返回 `{opinions: list[AgentOpinion], run_id: str}`
  2. `POST /consensus/{case_id}` — 达成共识
     - Body: `{run_id: str}` — 关联的 Agent 运行 ID
     - 调用 ConsensusEngine.reach_consensus()
     - 返回 ConsensusResult
  3. `POST /recommendation/{case_id}` — 生成推荐
     - Body: `{run_id: str}`
     - 调用 RecommendationGenerator.generate()
     - 返回 TreatmentRecommendation（含 structured_json 和 markdown）
  4. `POST /analyze/{case_id}` — 一键全流程（Agent → Consensus → Recommendation）
     - 依次调用 Orchestrator → ConsensusEngine → RecommendationGenerator
     - 返回完整结果（含每个阶段的输出）

---

### Phase 2c: Digital Thread

---

#### TASK-P2-013: DecisionNode 数据模型与持久化

| 字段 | 值 |
|------|-----|
| **ID** | TASK-P2-013 |
| **名称** | Digital Thread — DecisionNode 模型与持久化 |
| **描述** | 定义 `DecisionNode` Pydantic 模型和 SQLAlchemy 模型。每个重要决策产生一个节点，包含 input, evidence, agent, reason, timestamp, parent decision。实现 `DecisionThreadRepository` 进行持久化。 |
| **依赖** | TASK-P2-006（数据库迁移） |
| **预估工时** | 8h |
| **负责角色** | backend-logic, db-modeler |
| **产出文件** | `src/backend/clinical/decision_thread.py`（新增），`src/backend/clinical/models.py`（更新） |
| **验收标准** | 可创建、查询、遍历决策节点；支持父子关系形成决策树；通过 pytest |
| **风险** | 无 |

**详细说明**:
- `DecisionNode` Pydantic 模型:
  - `id: str`
  - `case_id: str`
  - `parent_id: Optional[str]` — 父决策节点 ID，形成 DAG
  - `node_type: str` — context_built, evidence_collected, agent_opinion, consensus_reached, recommendation_generated
  - `step_name: str` — 可读的步骤名
  - `input_summary: str` — 该节点输入摘要
  - `input_snapshot: dict` — 输入数据快照（如 context_hash, evidence_bundle_summary）
  - `output_summary: str` — 该节点输出摘要
  - `output_snapshot: dict` — 输出数据快照
  - `agent_id: Optional[str]` — 哪个 Agent 产生
  - `agent_type: Optional[str]`
  - `confidence: Optional[float]`
  - `timestamp: str`
  - `context_hash: Optional[str]`
  - `metadata: dict`

- `DecisionNodeModel` SQLAlchemy 模型（在 models.py 或 decision_thread.py 中定义）
  - 映射到 `clinical_decision_nodes` 表
  - 字段同 DecisionNode，使用 JSON 存储 snapshot

- `DecisionThreadRepository` 类:
  - `async create_node(node: DecisionNode) -> DecisionNode`
  - `async get_node(node_id: str) -> Optional[DecisionNode]`
  - `async get_case_thread(case_id: str) -> list[DecisionNode]` — 按时间排序
  - `async get_decision_tree(case_id: str) -> list[DecisionNode]` — 按父子关系排序
  - `async get_latest_node(case_id: str, node_type: str) -> Optional[DecisionNode]`

---

#### TASK-P2-014: Digital Thread 集成服务

| 字段 | 值 |
|------|-----|
| **ID** | TASK-P2-014 |
| **名称** | Digital Thread 集成到核心工作流 |
| **描述** | 在 CaseContextBuilder、EvidenceCollector、AgentOrchestrator、ConsensusEngine、RecommendationGenerator 中插入 Digital Thread 节点记录。每个重要步骤自动生成 DecisionNode。 |
| **依赖** | TASK-P2-013 |
| **预估工时** | 6h |
| **负责角色** | backend-logic |
| **产出文件** | 修改 `src/backend/clinical/builder.py`、`src/backend/clinical/collector.py`、`src/backend/agents/orchestrator.py`、`src/backend/agents/consensus.py`、`src/backend/clinical/recommendation.py` |
| **验收标准** | 每次运行核心工作流后，数据库中有完整的决策节点链；节点间通过 parent_id 连接；通过 pytest |
| **风险** | 需注意不要破坏现有 Phase 1 代码的行为 |

**详细说明**:
- 在每个关键步骤末尾调用 `DecisionThreadRepository.create_node()`
- 节点链:
  ```
  context_built → evidence_collected → agent_opinion (×6) → consensus_reached → recommendation_generated
  ```
- 每个节点记录 parent_id 形成完整链路
- context_hash 跨节点关联，确保可追溯
- 使用 lazy initialization 模式：首次使用 `DecisionThreadRepository` 时自动创建表（如需要）

---

#### TASK-P2-015: Digital Thread API 端点

| 字段 | 值 |
|------|-----|
| **ID** | TASK-P2-015 |
| **名称** | Digital Thread API 端点 |
| **描述** | 在 `clinical.py` 中新增 Digital Thread 查询端点。 |
| **依赖** | TASK-P2-014 |
| **预估工时** | 4h |
| **负责角色** | api-designer |
| **产出文件** | 修改 `src/backend/api/v1/clinical.py`（新增端点） |
| **验收标准** | 端点和返回数据符合设计；通过 ruff check；通过 pytest |
| **风险** | 无 |

**详细说明**:
- 新增端点:
  1. `GET /thread/{case_id}` — 获取案例的完整决策线程（按时间排序）
     - 返回 `DecisionNode[]`
  2. `GET /thread/{case_id}/tree` — 获取决策树（按父子关系）
     - 返回嵌套结构 `{nodes: [...], edges: [{parent_id, child_id, type}]}`
  3. `GET /thread/{case_id}/latest/{node_type}` — 获取某种类型的最新节点

---

### Phase 2d: 前端新分页

---

#### TASK-P2-016: Phase 2 API 客户端扩展

| 字段 | 值 |
|------|-----|
| **ID** | TASK-P2-016 |
| **名称** | 前端 API 客户端 — Phase 2 端点 |
| **描述** | 在 `src/frontend/src/api/workbench.ts` 中添加 Phase 2 端点的请求函数：ClinicalContext, EvidenceBundle, Agent 运行, Consensus, Recommendation, Digital Thread。 |
| **依赖** | TASK-P2-005, TASK-P2-012, TASK-P2-015 |
| **预估工时** | 4h |
| **负责角色** | frontend-logic |
| **产出文件** | 修改 `src/frontend/src/api/workbench.ts` |
| **验收标准** | 函数签名完整，与后端返回类型匹配；通过 `npm run build` |
| **风险** | 后端 API 变更时需同步更新 |

**详细说明**:
- 新增 TypeScript 类型:
  - `ClinicalContext`, `EvidenceItem`, `EvidenceBundle`
  - `AgentOpinion`, `ConsensusResult`
  - `TreatmentRecommendationExtended`（增强版）
  - `DecisionNode`
- 新增 API 函数:
  - `getClinicalContext(caseId)`, `getEvidenceBundle(caseId)`
  - `runAgents(caseId, agentTypes?)`, `runConsensus(caseId, runId)`, `getRecommendation(caseId, runId)`
  - `runFullAnalysis(caseId)` — 一键全流程
  - `getDecisionThread(caseId)`, `getDecisionTree(caseId)`

---

#### TASK-P2-017: ContextTab 组件

| 字段 | 值 |
|------|-----|
| **ID** | TASK-P2-017 |
| **名称** | 前端 — ContextTab 临床上下文分页 |
| **描述** | 创建 `ContextTab` React 组件，展示 ClinicalContext 数据。独立加载，不依赖其他 Tab。包含患者信息、诊断、分期、生物标志物、变异清单、治疗史等子部分。 |
| **依赖** | TASK-P2-016 |
| **预估工时** | 6h |
| **负责角色** | frontend-logic, ui-designer |
| **产出文件** | `src/frontend/src/components/tabs/ContextTab.tsx`（新增） |
| **验收标准** | 组件独立渲染；数据从 API 获取；有 loading/error/empty 状态；通过 `npm run build` |
| **风险** | 无 |

**详细说明**:
- 文件位置: `src/frontend/src/components/tabs/ContextTab.tsx`
- 组件功能:
  - 从 `getClinicalContext()` 获取数据
  - 显示：患者基本信息卡、诊断摘要、分期/分级、生物标志物标签云、变异表格、治疗史时间线、当前用药
  - 每个部分可折叠/展开
  - 使用 Phase 1 现有的 `InfoCard`、`Section`、`LoadingSkeleton`、`ErrorState`、`EmptyState` 组件
- 遵循 Phase 1 Workbench 组件的设计模式

---

#### TASK-P2-018: EvidenceTab 组件

| 字段 | 值 |
|------|-----|
| **ID** | TASK-P2-018 |
| **名称** | 前端 — EvidenceTab 证据浏览分页 |
| **描述** | 创建 `EvidenceTab` 组件，展示 EvidenceBundle 数据。支持按来源、基因、药物筛选。显示证据级别、冲突标记。 |
| **依赖** | TASK-P2-016 |
| **预估工时** | 6h |
| **负责角色** | frontend-logic, ui-designer |
| **产出文件** | `src/frontend/src/components/tabs/EvidenceTab.tsx`（新增） |
| **验收标准** | 可筛选、搜索证据；显示冲突标记；独立渲染；通过 `npm run build` |
| **风险** | 证据量较大时需虚拟滚动或分页 |

**详细说明**:
- 组件功能:
  - 从 `getEvidenceBundle()` 获取数据
  - 按来源（CIViC, DGIdb, ClinVar, PubMed）分组展示
  - 每个证据项卡片：来源、药物、基因、证据方向（支持/冲突）、证据级别、PM ID
  - 筛选器：source, gene, drug, evidence_direction, min_level
  - 冲突标记：红色高亮 conflicting 证据
  - 支持展开查看详情
  - 证据数量显示（总量 + 各来源数量）

---

#### TASK-P2-019: AgentsTab 组件

| 字段 | 值 |
|------|-----|
| **ID** | TASK-P2-019 |
| **名称** | 前端 — AgentsTab 多代理讨论分页 |
| **描述** | 创建 `AgentsTab` 组件，展示 6 个 Agent 的意见。每个 Agent 有独立面板，可展开查看详情。提供 "运行全部" 按钮。 |
| **依赖** | TASK-P2-016 |
| **预估工时** | 6h |
| **负责角色** | frontend-logic, ui-designer |
| **产出文件** | `src/frontend/src/components/tabs/AgentsTab.tsx`（新增） |
| **验收标准** | 显示 6 个 Agent 面板；支持单独/全部运行；显示置信度；通过 `npm run build` |
| **风险** | 无 |

**详细说明**:
- 组件功能:
  - 6 个 Agent 面板，每个显示：agent_type 图标、summary、pros/cons 列表、confidence 进度条、references
  - 顶部按钮："运行所有 Agent"（调用 `runAgents()`）
  - 每个 Agent 面板可独立展开/折叠
  - 运行状态指示器（running/completed/failed/timeout）
  - 置信度可视化（颜色编码：high=green, medium=yellow, low=red）
  - 水平排列（3×2 网格）或垂直列表

---

#### TASK-P2-020: ConsensusTab 组件

| 字段 | 值 |
|------|-----|
| **ID** | TASK-P2-020 |
| **名称** | 前端 — ConsensusTab 共识结果分页 |
| **描述** | 创建 `ConsensusTab` 组件，展示 ConsensusResult。包含一致性评分、冲突分析、推荐选项、替代方案、未解决问题。 |
| **依赖** | TASK-P2-016 |
| **预估工时** | 4h |
| **负责角色** | frontend-logic, ui-designer |
| **产出文件** | `src/frontend/src/components/tabs/ConsensusTab.tsx`（新增） |
| **验收标准** | 显示共识结果；可视化冲突；显示推荐/替代方案；通过 `npm run build` |
| **风险** | 无 |

**详细说明**:
- 组件功能:
  - 显示 agreement_level 指示器（颜色 + 文本）
  - 圆形进度图显示 agreement_score
  - 冲突列表：每个冲突显示涉及的 agent_types、问题、严重程度
  - 推荐选项卡片：summary、supporting_agents 标签、关联证据
  - 替代方案列表（折叠面板）
  - 未解决问题列表
  - 按钮："生成推荐"（调用 `getRecommendation()`）

---

#### TASK-P2-021: RecommendationTab 组件

| 字段 | 值 |
|------|-----|
| **ID** | TASK-P2-021 |
| **名称** | 前端 — RecommendationTab 治疗推荐分页 |
| **描述** | 创建 `RecommendationTab` 组件，展示 TreatmentRecommendation。分 First-line, Second-line, Clinical Trial 卡片。可切换 JSON/Markdown 视图。 |
| **依赖** | TASK-P2-016 |
| **预估工时** | 4h |
| **负责角色** | frontend-logic, ui-designer |
| **产出文件** | `src/frontend/src/components/tabs/RecommendationTab.tsx`（新增） |
| **验收标准** | 三种治疗方案卡片；JSON/Markdown 视图切换；通过 `npm run build` |
| **风险** | 无 |

**详细说明**:
- 组件功能:
  - 三个等级卡片：一线治疗（绿色边框）、二线治疗（蓝色边框）、临床试验（紫色边框）
  - 每张卡片含：drug name、rationale、evidence level badge、confidence indicator
  - Supporting Evidence 表格：evidence_id, source, summary
  - Expected Benefit / Potential Risk 列表
  - Monitoring Plan 清单
  - 视图切换按钮："结构化视图" / "Markdown 报告"
  - Markdown 视图使用简单的 markdown 渲染（如 `react-markdown`）

---

#### TASK-P2-022: DecisionThreadTab 组件

| 字段 | 值 |
|------|-----|
| **ID** | TASK-P2-022 |
| **名称** | 前端 — DecisionThreadTab 决策追溯分页 |
| **描述** | 创建 `DecisionThreadTab` 组件，展示决策节点的树形/时间线视图。支持展开每个节点查看输入输出快照。 |
| **依赖** | TASK-P2-016 |
| **预估工时** | 6h |
| **负责角色** | frontend-logic, ui-designer |
| **产出文件** | `src/frontend/src/components/tabs/DecisionThreadTab.tsx`（新增） |
| **验收标准** | 时间线/树形视图切换；节点可展开查看详情；通过 `npm run build` |
| **风险** | 无 |

**详细说明**:
- 组件功能:
  - 双视图模式：
    - **时间线视图**：垂直时间线，每个节点按时间排列，显示 node_type 图标、step_name、timestamp
    - **树形视图**：父子关系树，从 context_built 到 recommendation_generated
  - 每个节点可点击展开：
    - 输入摘要 + snapshot JSON（语法高亮）
    - 输出摘要 + snapshot JSON
    - Agent 信息（如果有）
    - 置信度
  - 节点类型颜色编码
  - 搜索/过滤节点类型

---

#### TASK-P2-023: Workbench Tab 集成

| 字段 | 值 |
|------|-----|
| **ID** | TASK-P2-023 |
| **名称** | 将新分页集成到 Workbench |
| **描述** | 在 `Workbench.tsx` 中添加 6 个新 Tab：Context, Evidence, Agents, Consensus, Recommendation, Decision Thread。每个 Tab 独立加载。更新侧边栏导航。 |
| **依赖** | TASK-P2-017, TASK-P2-018, TASK-P2-019, TASK-P2-020, TASK-P2-021, TASK-P2-022 |
| **预估工时** | 6h |
| **负责角色** | frontend-logic, ui-designer |
| **产出文件** | 修改 `src/frontend/src/pages/Workbench.tsx` |
| **验收标准** | 新 Tab 出现在 Workbench 中；各自独立加载；不破坏现有 Tab；通过 `npm run build`、`npm test` |
| **风险** | 需确保与现有 Tab 的加载/错误状态不冲突 |

**详细说明**:
- 在 `TABS` 数组中新增:
  ```tsx
  { id: 'context', label: '临床上下文', icon: '📋' },
  { id: 'evidence', label: '证据', icon: '🔍' },
  { id: 'agents', label: 'AI 代理', icon: '🤖' },
  { id: 'consensus', label: '共识', icon: '⚖️' },
  { id: 'recommendation', label: '推荐方案', icon: '💊' },
  { id: 'thread', label: '决策追溯', icon: '🔗' },
  ```
- 在 `renderTabContent()` 中添加新 case:
  ```tsx
  case 'context': return <ContextTab caseId={caseId} />
  case 'evidence': return <EvidenceTab caseId={caseId} />
  case 'agents': return <AgentsTab caseId={caseId} />
  case 'consensus': return <ConsensusTab caseId={caseId} />
  case 'recommendation': return <RecommendationTab caseId={caseId} />
  case 'thread': return <DecisionThreadTab caseId={caseId} />
  ```
- 每个 Tab 组件独立管理自己的 loading/error/empty 状态
- 更新左侧导航栏，添加对应条目
- 确保右侧 AI 助手面板能展示新数据（如共识结果、推荐方案摘要）

---

### Phase 2e: 测试与整合

---

#### TASK-P2-024: 单元测试 — ClinicalContext & EvidenceBundle

| 字段 | 值 |
|------|-----|
| **ID** | TASK-P2-024 |
| **名称** | 单元测试：ClinicalContextBuilder 和 EvidenceCollector |
| **描述** | 为 ClinicalContextBuilder 和 EvidenceCollector 编写 pytest 单元测试。测试正常路径、空数据路径、错误路径。 |
| **依赖** | TASK-P2-002, TASK-P2-004 |
| **预估工时** | 6h |
| **负责角色** | unit-tester |
| **产出文件** | `tests/unit/test_clinical_context.py`（新增），`tests/unit/test_evidence_collector.py`（新增） |
| **验收标准** | 测试覆盖率 > 80%；所有测试通过 `pytest`；通过 `ruff check` |
| **风险** | 无 |

**详细说明**:
- 使用 pytest fixtures 创建测试数据库和 mock
- `test_clinical_context.py`:
  - `test_build_with_valid_case` — 完整数据路径
  - `test_build_with_missing_fields` — NULL 字段处理
  - `test_build_with_invalid_id` — 无效 case_id
  - `test_context_freeze_hash` — context_hash 一致性
  - `test_context_hash_changes_on_data_change` — 数据变更导致 hash 变更
- `test_evidence_collector.py`:
  - `test_collect_with_valid_context` — 正常收集
  - `test_collect_with_no_variants` — 无变异的 case
  - `test_filter_by_source` — 按来源筛选
  - `test_filter_by_gene` — 按基因筛选

---

#### TASK-P2-025: 单元测试 — Agents & Consensus & Recommendation

| 字段 | 值 |
|------|-----|
| **ID** | TASK-P2-025 |
| **名称** | 单元测试：Agents, ConsensusEngine, RecommendationGenerator |
| **描述** | 为 6 个 Agent、ConsensusEngine、RecommendationGenerator 编写单元测试。Agent 测试使用 mock 的 ClinicalContext 和 EvidenceBundle。 |
| **依赖** | TASK-P2-008, TASK-P2-010, TASK-P2-011 |
| **预估工时** | 8h |
| **负责角色** | unit-tester |
| **产出文件** | `tests/unit/test_agents.py`（新增），`tests/unit/test_consensus.py`（新增），`tests/unit/test_recommendation.py`（新增） |
| **验收标准** | 每个 Agent 至少 3 个测试用例；ConsensusEngine 覆盖不同 agreement 级别；通过 `pytest` |
| **风险** | Agent 测试需 mock LLM 调用 |

**详细说明**:
- `test_agents.py`:
  - 每个 Agent 的 `test_analyze_with_data`、`test_analyze_empty_data`、`test_analyze_llm_unavailable`
  - AgentOrchestrator 的 `test_run_all_agents`、`test_run_selected`、`test_timeout_handling`
- `test_consensus.py`:
  - `test_high_agreement` — 所有 Agent 一致
  - `test_moderate_agreement` — 多数一致
  - `test_low_agreement` — 高度分歧
  - `test_empty_opinions` — 空输入
- `test_recommendation.py`:
  - `test_generate_full` — 完整数据
  - `test_generate_minimal` — 最小数据
  - `test_markdown_output` — markdown 格式验证

---

#### TASK-P2-026: 单元测试 — Digital Thread

| 字段 | 值 |
|------|-----|
| **ID** | TASK-P2-026 |
| **名称** | 单元测试：Digital Thread |
| **描述** | 为 DecisionNode 模型和 DecisionThreadRepository 编写单元测试。测试 CRUD、决策树遍历、工作流集成。 |
| **依赖** | TASK-P2-013 |
| **预估工时** | 4h |
| **负责角色** | unit-tester |
| **产出文件** | `tests/unit/test_decision_thread.py`（新增） |
| **验收标准** | CRUD 测试通过；工作流集成测试验证完整节点链；通过 `pytest` |
| **风险** | 无 |

**详细说明**:
- `test_decision_thread.py`:
  - `test_create_node` — 创建单个节点
  - `test_create_node_chain` — 创建父子链
  - `test_get_case_thread` — 按 case 查询
  - `test_get_decision_tree` — 父子关系遍历
  - `test_workflow_integration` — 模拟完整工作流，验证所有节点类型和 parent_id 链
  - `test_empty_case` — 无决策的 case

---

#### TASK-P2-027: 集成测试

| 字段 | 值 |
|------|-----|
| **ID** | TASK-P2-027 |
| **名称** | 集成测试：Phase 2 全流程 |
| **描述** | 编写端到端集成测试，覆盖完整 Phase 2 工作流：API → ClinicalContext → EvidenceCollection → Agents → Consensus → Recommendation → Digital Thread。使用测试数据库。 |
| **依赖** | TASK-P2-005, TASK-P2-012, TASK-P2-015 |
| **预估工时** | 8h |
| **负责角色** | integration-tester |
| **产出文件** | `tests/integration/test_phase2_workflow.py`（新增），`tests/integration/test_phase2_api.py`（新增） |
| **验收标准** | 完整工作流测试通过；API 端点测试覆盖所有状态码；通过 `pytest` |
| **风险** | 需准备测试数据库 fixture |

**详细说明**:
- `test_phase2_api.py`:
  - 测试所有新增 API 端点的 HTTP 状态码和响应结构
  - 认证测试（未认证 → 401，无权限 → 403）
  - 输入验证测试（无效 UUID → 422/400）
  - 使用 `TestClient` 和测试数据库
- `test_phase2_workflow.py`:
  - 创建测试 case（含 patient, case, variants）
  - 调用 `POST /analyze/{case_id}` 全流程
  - 验证返回包含所有阶段的输出
  - 验证决策线程包含完整的节点链
  - 验证各阶段数据正确关联

---

#### TASK-P2-028: 前端测试

| 字段 | 值 |
|------|-----|
| **ID** | TASK-P2-028 |
| **名称** | 前端组件测试 |
| **描述** | 为 6 个新 Tab 组件编写 React Testing Library 测试。测试渲染、交互、API 调用。 |
| **依赖** | TASK-P2-017 ~ TASK-P2-023 |
| **预估工时** | 6h |
| **负责角色** | unit-tester |
| **产出文件** | `src/frontend/src/test/tabs/ContextTab.test.tsx`、`EvidenceTab.test.tsx`、`AgentsTab.test.tsx`、`ConsensusTab.test.tsx`、`RecommendationTab.test.tsx`、`DecisionThreadTab.test.tsx`（均新增） |
| **验收标准** | 每个组件有加载/数据/错误三种状态测试；通过 `npm test` |
| **风险** | 无 |

**详细说明**:
- 使用 `vitest` + `@testing-library/react`（沿用 Phase 1 测试框架）
- 每个测试文件覆盖:
  - `renders loading state` — 检查骨架屏
  - `renders data correctly` — mock API 返回数据，检查内容渲染
  - `renders error state` — mock API 抛出错误，检查错误显示
  - `renders empty state` — mock API 返回空数据
- API 调用使用 `vi.mock()` mock `workbench.ts` 模块

---

#### TASK-P2-029: CI 集成与最终验证

| 字段 | 值 |
|------|-----|
| **ID** | TASK-P2-029 |
| **名称** | CI 集成、lint 检查、最终构建验证 |
| **描述** | 更新 CI 配置以包含 Phase 2 测试；运行 `ruff check`、`pytest`、`npm test`、`npm run build` 确保全部通过。更新 `.github/workflows/ci.yml`。 |
| **依赖** | TASK-P2-024 ~ TASK-P2-028 |
| **预估工时** | 4h |
| **负责角色** | exec-dev |
| **产出文件** | 修改 `.github/workflows/ci.yml` |
| **验收标准** | CI 全部通过；`ruff check` 零警告；`pytest` 全部通过；`npm test` 全部通过；`npm run build` 成功 |
| **风险** | 无 |

**详细说明**:
- 更新 CI pipeline:
  - 在 pytest 步骤中添加 Phase 2 测试目录
  - 在 npm test 步骤中添加新组件测试
  - 验证 `npm run build` 成功
- 运行全量 ruff check 确保零新增警告
- 运行全量 pytest 确保不破坏 Phase 1 测试
- 创建 Phase 2 完成检查清单（见下方）

---

## 依賴關係圖

```
Phase 2a (Core Backend)
  TASK-P2-001 (ClinicalContext models) ──→ TASK-P2-002 (CaseContextBuilder)
  TASK-P2-003 (EvidenceBundle models) ───→ TASK-P2-004 (EvidenceCollector)
  TASK-P2-001, TASK-P2-002, TASK-P2-003, TASK-P2-004 ──→ TASK-P2-005 (API endpoints)
  TASK-P2-001, TASK-P2-003 ──→ TASK-P2-006 (DB migration)

Phase 2b (Multi-Agent)
  TASK-P2-001, TASK-P2-003 ──→ TASK-P2-007 (Agent base framework)
  TASK-P2-007 ──→ TASK-P2-008 (6 Agents)
  TASK-P2-008 ──→ TASK-P2-009 (Orchestrator)
  TASK-P2-009 ──→ TASK-P2-010 (ConsensusEngine)
  TASK-P2-010 ──→ TASK-P2-011 (RecommendationGenerator)
  TASK-P2-009, TASK-P2-010, TASK-P2-011 ──→ TASK-P2-012 (Agents API)

Phase 2c (Digital Thread)
  TASK-P2-006 ──→ TASK-P2-013 (DecisionNode model + repo)
  TASK-P2-013 ──→ TASK-P2-014 (Thread integration)
  TASK-P2-014 ──→ TASK-P2-015 (Thread API)

Phase 2d (Frontend)
  TASK-P2-005, TASK-P2-012, TASK-P2-015 ──→ TASK-P2-016 (API client)
  TASK-P2-016 ──→ TASK-P2-017 (ContextTab)
  TASK-P2-016 ──→ TASK-P2-018 (EvidenceTab)
  TASK-P2-016 ──→ TASK-P2-019 (AgentsTab)
  TASK-P2-016 ──→ TASK-P2-020 (ConsensusTab)
  TASK-P2-016 ──→ TASK-P2-021 (RecommendationTab)
  TASK-P2-016 ──→ TASK-P2-022 (DecisionThreadTab)
  TASK-P2-017~022 ──→ TASK-P2-023 (Workbench integration)

Phase 2e (Testing)
  TASK-P2-002, TASK-P2-004 ──→ TASK-P2-024 (Unit: Context + Evidence)
  TASK-P2-008, TASK-P2-010, TASK-P2-011 ──→ TASK-P2-025 (Unit: Agents + Consensus + Rec)
  TASK-P2-013 ──→ TASK-P2-026 (Unit: Digital Thread)
  TASK-P2-005, TASK-P2-012, TASK-P2-015 ──→ TASK-P2-027 (Integration)
  TASK-P2-017~023 ──→ TASK-P2-028 (Frontend tests)
  TASK-P2-024~028 ──→ TASK-P2-029 (CI + final validation)
```

### 关键路径
```
TASK-P2-001 → TASK-P2-002 → TASK-P2-004 → TASK-P2-005
                                        ↘
TASK-P2-003 ↗                            → TASK-P2-007 → TASK-P2-008 → TASK-P2-009 → TASK-P2-010 → TASK-P2-011 → TASK-P2-012
                                                                                                             ↘
                                                                        TASK-P2-006 → TASK-P2-013 → TASK-P2-014 → TASK-P2-015
                                                                                                                      ↘
                                                                                   TASK-P2-016 → (TASK-P2-017~022) → TASK-P2-023
```

---

## 返工预案

当 REVIEWER 评分不合格时，根据问题类型采取以下调整策略：

### 类型 A：架构/设计问题（评分 < 6）
- **症状**：模块间耦合过高、数据流不清晰、不符合 Phase 1 架构风格
- **策略**：冻结所有编码工作，PLANNER 和 backend-logic 共同修订设计文档
- **具体措施**：
  1. REVIEWER 提供具体架构批评
  2. PLANNER 更新本计划中的相关任务
  3. 受影响的模块重写（通常 1-2 个任务）
  4. 重新提交 REVIEWER 检查

### 类型 B：功能缺失/边界情况未处理（评分 6-7）
- **症状**：核心功能实现但缺少错误处理、边界情况、空数据路径
- **策略**：定位到具体任务，补充实现
- **具体措施**：
  1. 根据 REVIEWER 指出的缺失点，创建子任务补充
  2. 优先修复：空数据安全、数据库查询错误处理、external API 超时
  3. 补充相应的单元测试
  4. 无需重写，通常 2-4h 修复

### 类型 C：测试覆盖不足（评分 7-8）
- **症状**：功能实现正确但测试覆盖率低于阈值
- **策略**：补充测试用例
- **具体措施**：
  1. 检查各模块测试覆盖率
  2. 为缺失路径添加测试（空数据、错误、边界值）
  3. 补充集成测试中的异常场景
  4. 通常 2-3h 补充

### 类型 D：代码质量问题（评分 7-8）
- **症状**：ruff check 警告、类型提示不完整、文档缺失
- **策略**：运行自动化修复 + 人工审查
- **具体措施**：
  1. `ruff check --fix` 自动修复
  2. 补充缺失的 type hints
  3. 添加 docstrings（Google style）
  4. 通常 1-2h 修复

### 类型 E：前端样式/交互问题（评分 6-7）
- **症状**：UI 与 Phase 1 风格不一致、响应式问题、加载状态缺失
- **策略**：前端修复
- **具体措施**：
  1. 统一使用 Phase 1 的 CSS 类名和组件
  2. 补充 loading skeleton、error state、empty state
  3. 确保 `npm run build` 和 `npm test` 通过
  4. 通常 2-4h 修复

---

## 完成检查清单

### Phase 2a 完成条件
- [ ] `ClinicalContext` 模型定义完成，包含所有必需字段
- [ ] `CaseContextBuilder` 能从数据库组装完整上下文
- [ ] `EvidenceBundle` 和 `EvidenceItem` 模型定义完成
- [ ] `EvidenceCollector` 能收集证据并组装 EvidenceBundle
- [ ] `GET /api/v1/clinical/context/{case_id}` 端点工作正常
- [ ] `GET /api/v1/clinical/evidence/{case_id}` 端点工作正常
- [ ] 数据库迁移脚本 `016_phase2_clinical_workspace.py` 执行成功
- [ ] `ruff check` 通过

### Phase 2b 完成条件
- [ ] `BaseAgent` 基类和 `AgentOpinion` 模型定义完成
- [ ] 6 个 Agent 均实现并可通过 pytest
- [ ] `AgentOrchestrator` 可并行运行所有 Agent
- [ ] `ConsensusEngine` 可计算共识
- [ ] `RecommendationGenerator` 可输出 JSON + Markdown
- [ ] Agents/Consensus/Recommendation API 端点工作正常
- [ ] `ruff check` 通过

### Phase 2c 完成条件
- [ ] `DecisionNode` 模型和 `DecisionNodeModel` 表定义完成
- [ ] `DecisionThreadRepository` CRUD 操作完整
- [ ] 核心工作流各步骤自动生成决策节点
- [ ] Digital Thread API 端点工作正常
- [ ] `ruff check` 通过

### Phase 2d 完成条件
- [ ] API 客户端扩展完成
- [ ] 6 个新 Tab 组件各自独立渲染
- [ ] Workbench 集成 6 个新 Tab
- [ ] `npm run build` 成功

### Phase 2e 完成条件
- [ ] 单元测试全部通过（pytest）
- [ ] 集成测试全部通过（pytest）
- [ ] 前端测试全部通过（npm test）
- [ ] CI pipeline 更新并全部通过
- [ ] `ruff check` 零警告
- [ ] `npm run build` 成功

---

## 文件清单汇总

### 新增文件

| 路径 | 关联任务 |
|------|---------|
| `src/backend/clinical/__init__.py` | TASK-P2-001 |
| `src/backend/clinical/models.py` | TASK-P2-001, TASK-P2-003 |
| `src/backend/clinical/builder.py` | TASK-P2-002 |
| `src/backend/clinical/evidence_models.py` | TASK-P2-003 |
| `src/backend/clinical/collector.py` | TASK-P2-004 |
| `src/backend/clinical/recommendation.py` | TASK-P2-011 |
| `src/backend/clinical/decision_thread.py` | TASK-P2-013 |
| `src/backend/agents/__init__.py` | TASK-P2-007 |
| `src/backend/agents/base.py` | TASK-P2-007 |
| `src/backend/agents/models.py` | TASK-P2-007, TASK-P2-010 |
| `src/backend/agents/diagnosis_agent.py` | TASK-P2-008 |
| `src/backend/agents/variant_agent.py` | TASK-P2-008 |
| `src/backend/agents/drug_agent.py` | TASK-P2-008 |
| `src/backend/agents/resistance_agent.py` | TASK-P2-008 |
| `src/backend/agents/guideline_agent.py` | TASK-P2-008 |
| `src/backend/agents/clinical_trial_agent.py` | TASK-P2-008 |
| `src/backend/agents/orchestrator.py` | TASK-P2-009 |
| `src/backend/agents/consensus.py` | TASK-P2-010 |
| `src/backend/api/v1/clinical.py` | TASK-P2-005, TASK-P2-012, TASK-P2-015 |
| `migrations/versions/016_phase2_clinical_workspace.py` | TASK-P2-006 |
| `src/frontend/src/components/tabs/ContextTab.tsx` | TASK-P2-017 |
| `src/frontend/src/components/tabs/EvidenceTab.tsx` | TASK-P2-018 |
| `src/frontend/src/components/tabs/AgentsTab.tsx` | TASK-P2-019 |
| `src/frontend/src/components/tabs/ConsensusTab.tsx` | TASK-P2-020 |
| `src/frontend/src/components/tabs/RecommendationTab.tsx` | TASK-P2-021 |
| `src/frontend/src/components/tabs/DecisionThreadTab.tsx` | TASK-P2-022 |
| `tests/unit/test_clinical_context.py` | TASK-P2-024 |
| `tests/unit/test_evidence_collector.py` | TASK-P2-024 |
| `tests/unit/test_agents.py` | TASK-P2-025 |
| `tests/unit/test_consensus.py` | TASK-P2-025 |
| `tests/unit/test_recommendation.py` | TASK-P2-025 |
| `tests/unit/test_decision_thread.py` | TASK-P2-026 |
| `tests/integration/test_phase2_workflow.py` | TASK-P2-027 |
| `tests/integration/test_phase2_api.py` | TASK-P2-027 |
| `src/frontend/src/test/tabs/ContextTab.test.tsx` | TASK-P2-028 |
| `src/frontend/src/test/tabs/EvidenceTab.test.tsx` | TASK-P2-028 |
| `src/frontend/src/test/tabs/AgentsTab.test.tsx` | TASK-P2-028 |
| `src/frontend/src/test/tabs/ConsensusTab.test.tsx` | TASK-P2-028 |
| `src/frontend/src/test/tabs/RecommendationTab.test.tsx` | TASK-P2-028 |
| `src/frontend/src/test/tabs/DecisionThreadTab.test.tsx` | TASK-P2-028 |

### 修改文件

| 路径 | 关联任务 |
|------|---------|
| `src/backend/api/v1/router.py` | TASK-P2-005 |
| `src/backend/api/v1/clinical.py` | TASK-P2-005, TASK-P2-012, TASK-P2-015 |
| `src/backend/agents/models.py` | TASK-P2-010 |
| `src/backend/clinical/models.py` | TASK-P2-013 |
| `src/backend/clinical/builder.py` | TASK-P2-014 |
| `src/backend/clinical/collector.py` | TASK-P2-014 |
| `src/backend/agents/orchestrator.py` | TASK-P2-014 |
| `src/backend/agents/consensus.py` | TASK-P2-014 |
| `src/backend/clinical/recommendation.py` | TASK-P2-014 |
| `src/frontend/src/api/workbench.ts` | TASK-P2-016 |
| `src/frontend/src/pages/Workbench.tsx` | TASK-P2-023 |
| `.github/workflows/ci.yml` | TASK-P2-029 |

---

## 执行顺序建议

按以下顺序执行可最小化阻塞：

1. **Phase 2a 串行**: TASK-P2-001 → P2-002 → P2-003 → P2-004 → P2-005 → P2-006
   - 先完成数据模型（P2-001, P2-003），再实现服务（P2-002, P2-004），最后 API 和迁移

2. **Phase 2b 与 Phase 2c 可并行**（依赖 Phase 2a 完成后）：
   - Phase 2b: P2-007 → P2-008 → P2-009 → P2-010 → P2-011 → P2-012
   - Phase 2c: P2-013 → P2-014 → P2-015

3. **Phase 2d** 需 Phase 2a 的 API 端点（P2-005）和 Phase 2b/2c 的 API（P2-012, P2-015）完成后开始：
   - P2-016 → (P2-017~P2-022 可并行) → P2-023

4. **Phase 2e** 可在各阶段完成后立即开始对应测试，最终统一 CI 集成
