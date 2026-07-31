# Phase 5 — Medical AI Platform Master Plan

> **目的**：將目前以 Oncology（精準腫瘤學）為主的系統，提煉為多專科 Medical AI Platform，支援 Cardiology、Neurology、Radiology 等專科模組的插件式擴充。
>
> **原則**：
> 1. 不得要求大規模重寫 Oncology 模組 — 以抽象化、註冊化為主
> 2. 基於實際盤點結果（見 `tasks/research/current-capability-inventory.md`）
> 3. 每個 Batch 必須是完整功能交付
> 4. 明確區分 Phase 4 完成後才能做的事（例如 FHIR R4、HL7/DICOM、RAG/Vector DB）vs Phase 5 專屬工作

---

## 目錄

1. [Oncology 耦合盤點](#1-oncology-耦合盤點)
2. [Registry／Plugin 化設計](#2-registryplugin-化設計)
3. [Specialty Module Contract](#3-specialty-module-contract)
4. [Workflow Module Contract](#4-workflow-module-contract)
5. [Clinical Agent Contract](#5-clinical-agent-contract)
6. [Knowledge Graph Namespace](#6-knowledge-graph-namespace)
7. [Clinical Terminology Mapping](#7-clinical-terminology-mapping)
8. [Versioning](#8-versioning)
9. [Tenant Isolation](#9-tenant-isolation)
10. [Platform API](#10-platform-api)
11. [Sample Specialty Modules](#11-sample-specialty-modules)
12. [Batch 拆分](#12-batch-拆分)
13. [驗收標準](#13-驗收標準)
14. [Phase 4 依賴項目](#14-phase-4-依賴項目)

---

## 1. Oncology 耦合盤點

### 1.1 盤點方法

逐一檢視現有 production code 中與 oncology 直接耦合的檔案，分類為：
- **🟢 可通用**：無 oncology-specific 邏輯，可直接複用
- **🟡 需抽象化**：有 cancer/oncology 參考但可提取介面
- **🔴 Oncology 專屬**：強依賴 cancer-specific 語義

### 1.2 盤點結果

| 層級 | 模組 | 分類 | 關鍵耦合點 | 重構策略 |
|------|------|------|-----------|----------|
| Domain | `enums.py:CancerTypeEnum` | 🔴 | 硬編碼 PTC/FTC/MTC/HCC/PDTC/ATC | 保留為 built-in oncology 實例；Specialty Registry 可註冊自己的 DiagnosisCodeEnum |
| Domain | `enums.py:SpecialtyType` | 🟡 | 列舉含 oncology 專科但本身通用 | 移至 Platform Enum Registry，oncology 為預設值 |
| Domain | `cancer_case.py` | 🔴 | CancerCaseModel 名稱與結構皆 oncology | 提取 `AbstractCase` 介面，CancerCase 繼承 |
| Domain | `tumor_board.py` | 🟡 | TumorBoard 需跨專科，結構可通用 | 提取 `AbstractConsensus` 介面 |
| Domain | `treatment_plan.py` | 🟡 | 通用治療計畫結構，少數 cancer_type 參考 | 拆出通用 TreatmentPlanBase |
| Domain | `evidence.py` | 🟢 | 完全 disease-agnostic | 直接複用 |
| Domain | `variant.py` | 🟢 | 基因變異非 oncology 獨有 | 直接複用 |
| Domain | `patient.py` | 🟢 | 通用病患模型 | 直接複用 |
| Clinical | `models.py:ClinicalContext` | 🟡 | `cancer_type` field 名稱為 oncology 特定 | 加 `diagnosis_code` 別名，保持向下相容 |
| Clinical | `recommendation_engine.py` | 🟢 | 規則驅動、無硬編碼 | 直接複用 |
| Clinical | `clinical_decision_engine.py` | 🟢 | 無 disease-specific 規則 | 直接複用 |
| Clinical | `tumor_board_engine.py` | 🟡 | SpecialtyType 參考 | 透過 Registry 解析 |
| Clinical | `treatment_plan_engine.py` | 🟡 | cancer_type 作為參數 | 改為 diagnosis_code + specialty 命名空間 |
| Clinical | `treatment_plan_rules.py` | 🟡 | 預設 phase 定義含 thyroid-specific 監控項 | 拆為 oncology default + 註冊點 |
| Clinical | `evidence_weight.py` | 🟢 | 通用權重邏輯 | 直接複用 |
| Clinical | `decision_rules.py` | 🟢 | 無 disease-specific | 直接複用 |
| Clinical | `consensus_rules.py` | 🟡 | SpecialtyType 權重表含 oncology | 移至 Consensus Registry |
| Clinical | `evidence_models.py` | 🟢 | 完全通用 | 直接複用 |
| Agents | `base.py` | 🟢 | ABC 介面完全通用 | 直接複用 |
| Agents | `diagnosis_agent.py` | 🟡 | `_COMMON_HISTOLOGY_MAP` 含 cancer 組織學 | 提取為 Specialty-specific 資料 |
| Agents | `guideline_agent.py` | 🟡 | NCCN/ESMO 為 oncology 來源 | 改為 `GuidelineSourceRegistry` |
| Agents | `clinical_trial_agent.py` | 🟡 | ClinicalTrials.gov 通用但 cancer 篩選邏輯 | 提取 oncology filter 為 plugin |
| Agents | `drug_agent.py` | 🟡 | 部分 oncology-specific 藥物知識 | 藥物知識可抽象 | 
| Agents | `variant_agent.py` | 🟢 | 變異解讀通用 | 直接複用 |
| Agents | `resistance_agent.py` | 🟢 | 抗藥性邏輯通用 | 直接複用 |
| Agents | `orchestrator.py` | 🟢 | 完全通用 | 直接複用 |
| Agents | `consensus.py` | 🟢 | 完全通用 | 直接複用 |
| Ranking | `engine.py` | 🟢 | 通用排序引擎 | 直接複用 |
| Ranking | `scorers.py` | 🟡 | 少量 oncology-specific mapping（如 thyroid drug list） | 移至 oncology module |
| Pipeline | `vep_adapter.py` | 🟢 | VEP 通用 | 直接複用 |
| Pipeline | `civic_adapter.py` | 🟡 | CIViC 主要為 cancer 數據 | 保留但標記為 oncology-specific source |
| Pipeline | `dgidb_adapter.py` | 🟢 | 藥物-基因交互通用 | 直接複用 |
| Knowledge | `identifiers.py` | 🟡 | OncoTree/DOID map 含 oncology | 提取 oncology map 至 plugin |
| Knowledge | `models.py` | 🟢 | 知識實體通用 | 直接複用 |
| Services | `clinical_decision_service.py` | 🟢 | 通用 service 邏輯 | 直接複用 |
| Services | `recommendation_service.py` | 🟢 | 通用 | 直接複用 |
| Services | `treatment_plan_service.py` | 🟡 | oncology trace 邏輯 | 提取 oncology-specific trace handler |
| Services | `tumor_board_service.py` | 🟡 | SpecialtyType 耦合 | 透過 Registry 解耦 |
| Repositories | 全部 | 🟢 | 通用 CRUD 模式 | 直接複用 |
| API Routes | `clinical.py` | 🟡 | 端點含 cancer case 路徑 | 路徑保持，內部解耦 |
| API Routes | `treatment_plans.py` | 🟢 | 通用 REST | 直接複用 |
| API Routes | `workbench.py` | 🟢 | 通用 | 直接複用 |
| KnowGraphGo | 全部 13 packages | 🟢 | 通用知識圖譜 | 直接複用 |

### 1.3 耦合總覽

| 分類 | 數量 | 佔比 |
|------|------|------|
| 🟢 可通用（直接複用） | ~45 檔案 | ~65% |
| 🟡 需抽象化（提取介面） | ~18 檔案 | ~26% |
| 🔴 Oncology 專屬 | ~6 檔案 | ~9% |

**結論**：系統核心（engines、agents framework、repositories、knowledge graph、pipeline 基礎）絕大部分可通用。僅 Domain 層的 CancerTypeEnum、CancerCaseModel 以及部分 agent/engine 的 cancer-specific 邏輯需抽象化。

---

## 2. Registry／Plugin 化設計

### 2.1 Specialty Registry

**用途**：管理所有註冊的醫療專科模組。

```python
# src/backend/platform/registry/specialty_registry.py

class SpecialtyManifest(BaseModel):
    id: str                                # e.g. "oncology", "cardiology"
    version: str                           # semver
    display_name: str                      # 人類可讀名稱
    description: str
    entry_point: str                       # module path
    dependencies: list[str] = []           # 依賴的其他 specialty
    config_schema: dict | None = None      # JSON Schema for module config
    health_check_endpoint: str | None = None

class SpecialtyRegistry:
    """
    專科註冊中心。
    - 註冊：install_specialty(manifest, plugin_path)
    - 生命週期：load / start / stop / unload
    - 版本管理：支援 >=, ~, ^ 語義版本約束
    - 隔離：每個 specialty 有獨立配置命名空間
    """
    
    _instance: SpecialtyRegistry | None = None
    
    def register(self, manifest: SpecialtyManifest) -> None: ...
    def unregister(self, specialty_id: str) -> None: ...
    def get(self, specialty_id: str) -> SpecialtyManifest | None: ...
    def list_active(self) -> list[SpecialtyManifest]: ...
    def health_all(self) -> dict[str, dict]: ...
```

**註冊介面**（由每個 Specialty Module 的 `__init__.py` 匯出）：

```python
# 每個 specialty module 必須提供：
SPECIALTY_MANIFEST: SpecialtyManifest = { ... }

def create_specialty(config: dict) -> SpecialtyBase: ...
```

### 2.2 Clinical Agent Registry

**用途**：動態註冊各專科的臨床決策 Agent。

```python
# src/backend/platform/registry/agent_registry.py

class AgentRegistration(BaseModel):
    agent_type: str                        # e.g. "diagnosis_agent"
    agent_version: str
    specialty_id: str                      # 所屬專科
    agent_class: str                       # 完整類路徑
    config_schema: dict | None = None
    enabled: bool = True

class AgentRegistry:
    """
    Agent 註冊中心。
    - 每個 specialty 可註冊多個 agent
    - 跨 specialty agent 可共存（例如 oncology diagnosis_agent 與 cardiology diagnosis_agent）
    - Orchestrator 依 context.specialty 動態選擇 agent set
    """
    def register(self, specialty_id: str, agent_type: str, registration: AgentRegistration) -> None: ...
    def get_agents_for_specialty(self, specialty_id: str) -> dict[str, AgentRegistration]: ...
    def get_agent(self, specialty_id: str, agent_type: str) -> AgentRegistration | None: ...
    def list_all(self) -> dict[str, dict[str, AgentRegistration]]: ...
```

### 2.3 Workflow Registry

**用途**：管理專科特定工作流程定義。

```python
# src/backend/platform/registry/workflow_registry.py

class WorkflowDefinition(BaseModel):
    workflow_id: str
    specialty_id: str
    version: str
    steps: list[WorkflowStep]              # 有序步驟
    transitions: dict[str, str]            # state -> next state
    config_schema: dict | None = None

class WorkflowRegistry:
    """
    工作流註冊中心。
    - 每個 specialty 可定義自己的 clinical workflow
    - 支援 step 的 condition/action 可擴充
    """
    def register_workflow(self, workflow: WorkflowDefinition) -> None: ...
    def get_workflow(self, specialty_id: str, workflow_id: str) -> WorkflowDefinition | None: ...
    def get_default_workflow(self, specialty_id: str) -> WorkflowDefinition | None: ...
```

### 2.4 Evidence Source Registry

**用途**：管理各專科適用的證據來源。

```python
# src/backend/platform/registry/evidence_source_registry.py

class EvidenceSourceRegistration(BaseModel):
    source_id: str
    specialty_id: str
    adapter_class: str
    config_schema: dict | None = None
    priority: int = 0                     # 查詢優先級
    required_licenses: list[str] = []

class EvidenceSourceRegistry:
    """
    證據來源註冊中心。
    - oncology 可註冊 CIViC, OncoKB, NCCN
    - cardiology 可註冊 ESC Guidelines, ClinicalTrials.gov filter
    - radiology 可註冊 DICOM query, AI models
    """
    def register_source(self, specialty_id: str, source: EvidenceSourceRegistration) -> None: ...
    def get_sources_for_specialty(self, specialty_id: str) -> list[EvidenceSourceRegistration]: ...
    def get_source(self, source_id: str) -> EvidenceSourceRegistration | None: ...
```

### 2.5 Rule Set Registry

**用途**：管理各專科的業務規則集。

```python
# src/backend/platform/registry/rule_registry.py

class RuleSetRegistration(BaseModel):
    rule_set_id: str
    specialty_id: str
    version: str
    rules: list[RuleDefinition]           # condition -> action
    priority: int = 0

class RuleSetRegistry:
    """
    規則集註冊中心。
    - 支援規則疊加：platform default → specialty default → tenant override
    - 規則以 JSON/YAML 定義，可熱更新
    """
    def register_rule_set(self, rule_set: RuleSetRegistration) -> None: ...
    def get_rule_sets(self, specialty_id: str, context: dict) -> list[RuleDefinition]: ...
    def evaluate(self, specialty_id: str, context: dict) -> list[RuleResult]: ...
```

### 2.6 生命週期管理

所有 Registry 共享統一的 Plugin Lifecycle：

```
                     ┌─────────────────────┐
                     │     DISCOVERED      │ (scan module path)
                     └─────────┬───────────┘
                               │ install
                     ┌─────────▼───────────┐
                     │     REGISTERED      │ (metadata registered)
                     └─────────┬───────────┘
                               │ load
                     ┌─────────▼───────────┐
                     │      LOADED         │ (init & config validated)
                     └─────────┬───────────┘
                               │ start
                     ┌─────────▼───────────┐
                     │      ACTIVE         │ (serving)
                     └─────────┬───────────┘
                          ┌────┴────┐
                          │         │
                     ┌────▼──┐ ┌────▼────┐
                     │ STOP  │ │  ERROR  │
                     └───┬───┘ └────┬────┘
                         │          │
                     ┌───▼──────────▼────┐
                     │    UNREGISTERED   │
                     └───────────────────┘
```

---

## 3. Specialty Module Contract

### 3.1 Module 目錄結構

```
src/backend/specialties/
├── oncology/                    # 現有 oncology 模組（保留，逐步遷移）
├── cardiology/                  # Phase 5 sample
├── neurology/                   # Phase 5 sample
├── radiology/                   # Phase 5 sample
└── .template/                   # 模版供第三方開發
    ├── __init__.py
    ├── config.py
    ├── models.py
    ├── agents/
    ├── workflows/
    ├── rules/
    ├── services/
    ├── adapters/
    ├── tests/
    └── manifest.json
```

### 3.2 必備介面

每個 Specialty Module **必須**實作：

```python
class SpecialtyBase(ABC):
    """專科基底類，每個 specialty 必須繼承。"""
    
    @property
    @abstractmethod
    def manifest(self) -> SpecialtyManifest: ...
    
    @abstractmethod
    async def initialize(self, config: dict) -> None:
        """初始化：註冊 agent、workflow、evidence source、rule set"""
    
    @abstractmethod
    async def health_check(self) -> dict: ...
    
    @abstractmethod
    async def shutdown(self) -> None: ...
```

**選擇性實作**：

```python
class SpecialtyConfigMixin:
    def get_config_schema(self) -> dict: ...

class SpecialtyMigrationMixin:
    def get_migrations(self) -> list[str]: ...    # Alembic migration paths

class SpecialtySeedDataMixin:
    async def seed_data(self, db: AsyncSession) -> None: ...
```

### 3.3 配置方式

```
# config/specialties.yaml 或 environment variables:
SPECIALTIES__ONCOLOGY__ENABLED=true
SPECIALTIES__ONCOLOGY__VERSION=1.0.0
SPECIALTIES__CARDIOLOGY__ENABLED=true
SPECIALTIES__CARDIOLOGY__CONFIG__API_KEY=${CARDIO_API_KEY}
```

Platform 啟動時自動掃描 `src/backend/specialties/` 目錄，讀取每個 module 的 `manifest.json` 並註冊。

### 3.4 依賴注入

使用 FastAPI `Depends` 與 Platform-level container：

```python
# src/backend/platform/di.py

class PlatformContainer:
    db: AsyncSession
    specialty_registry: SpecialtyRegistry
    agent_registry: AgentRegistry
    workflow_registry: WorkflowRegistry
    evidence_source_registry: EvidenceSourceRegistry
    rule_registry: RuleSetRegistry
    config: AppConfig

def get_platform() -> PlatformContainer: ...
def get_specialty(specialty_id: str = "oncology") -> SpecialtyBase: ...
```

### 3.5 測試要求

每個 Specialty Module 必須包含：

1. **Unit tests**：覆蓋所有 agent 與 service（≥80%）
2. **Integration tests**：至少一個端到端 workflow
3. **Contract tests**：驗證符合 SpecialtyBase 介面
4. **Test fixtures**：提供 mock data generator

---

## 4. Workflow Module Contract

### 4.1 定義

Workflow 是一組有序的臨床步驟，每個步驟有 input / output / condition / action。

```python
class WorkflowStep(BaseModel):
    step_id: str
    name: str
    description: str
    step_type: str          # "agent_eval" | "human_review" | "data_collect" | "notification" | "external_call"
    agent_type: str | None  # 若為 agent_eval，指定使用哪個 agent
    input_mapping: dict     # context -> step input
    output_mapping: dict    # step output -> context
    conditions: list[RuleDefinition]  # 何時執行此步驟
    timeout_seconds: int = 300
    retry_policy: dict | None = None
```

### 4.2 Workflow Engine

```python
class WorkflowEngine:
    """
    通用 workflow 執行引擎。
    - 讀取 WorkflowRegistry 中的定義
    - 根據 context.specialty_id 路由到對應 workflow
    - 支援暫停/恢復、超時、重試
    - 產出 execution trace（Digital Thread 整合）
    """
    async def execute(self, workflow_id: str, context: ClinicalContext) -> WorkflowResult: ...
    async def get_status(self, execution_id: str) -> WorkflowExecutionStatus: ...
    async def pause(self, execution_id: str) -> None: ...
    async def resume(self, execution_id: str) -> None: ...
```

### 4.3 預設 Workflow

每個 specialty 必須註冊一個 Default Clinical Workflow：

| 步驟 | Oncology | Cardiology | Neurology | Radiology |
|------|----------|------------|-----------|-----------|
| 1 | VCF Upload & Pipeline | ECG/Holter Import | MRI/CT Import | DICOM Study Import |
| 2 | Variant Annotation | Biomarker Analysis | Lesion Segmentation | Image Enhancement |
| 3 | Evidence Collection | Guideline Matching | Diagnostic Criteria Eval | AI Model Inference |
| 4 | Multi-Agent Reasoning | Risk Score Calculation | Progression Assessment | Report Generation |
| 5 | Tumor Board Consensus | Heart Team Review | Multi-Disciplinary | Radiologist Review |
| 6 | Treatment Plan | Treatment Plan | Treatment Plan | Findings Output |

---

## 5. Clinical Agent Contract

### 5.1 Agent 介面（維持現有 BaseAgent）

現有 `BaseAgent` 介面已足夠通用，**無需修改**：

```python
class BaseAgent(ABC):
    agent_type: str = "base"
    agent_version: str = "1.0.0"
    
    def __init__(self, db: AsyncSession) -> None: ...
    
    @abstractmethod
    async def analyze(self, context: ClinicalContext, evidence: EvidenceBundle) -> AgentOpinion: ...
```

### 5.2 擴充：Specialty-Aware Agent

為支援多專科，新增 `SpecialtyAgentMixin`：

```python
class SpecialtyAgentMixin:
    """讓 agent 感知所屬專科 context。"""
    
    specialty_id: str = "oncology"
    
    async def before_analyze(self, context: ClinicalContext) -> ClinicalContext:
        """Hook：可在 analyze 前根據專科轉換 context"""
        return context
    
    async def after_analyze(self, opinion: AgentOpinion) -> AgentOpinion:
        """Hook：可在 analyze 後過濾或增強 opinion"""
        return opinion
```

### 5.3 Agent Selection 策略

Orchestrator 的 Agent 選擇邏輯改為：

```python
class AgentOrchestrator:
    async def run(
        self,
        context: ClinicalContext,
        specialty_id: str = "oncology",
    ) -> list[AgentOpinion]:
        # 1. 取得該專科註冊的所有 agent
        agents = self.agent_registry.get_agents_for_specialty(specialty_id)
        # 2. 若無專科特定 agent，fallback 到 default（oncology）
        if not agents:
            agents = self.agent_registry.get_agents_for_specialty("oncology")
        # 3. 平行執行
        opinions = await asyncio.gather(*[
            self._run_agent(agent_type, reg, context)
            for agent_type, reg in agents.items()
            if reg.enabled
        ])
        return opinions
```

### 5.4 跨專科 Agent 共存範例

```
Agent Registry 中的註冊內容：

oncology:
  diagnosis_agent:     version 1.2.0 (enabled)
  guideline_agent:     version 1.1.0 (enabled)
  clinical_trial_agent: version 1.0.0 (enabled)
  variant_agent:       version 1.0.0 (enabled)
  drug_agent:          version 1.0.0 (enabled)
  resistance_agent:    version 1.0.0 (enabled)

cardiology:
  diagnosis_agent:     version 1.0.0 (enabled)     ← 心臟科專用診斷 agent
  guideline_agent:     version 1.0.0 (enabled)     ← 心臟科 guideline agent
  risk_agent:          version 1.0.0 (enabled)     ← 心臟科特有 agent 類型

neurology:
  diagnosis_agent:     version 1.0.0 (enabled)
  imaging_agent:       version 1.0.0 (enabled)     ← 神經科特有
```

---

## 6. Knowledge Graph Namespace

### 6.1 命名空間設計

KnowGraphGo 擴充 namespace 支援，使不同專科的知識實體可在同一圖譜中共存：

```
Entity ID 格式：
  {namespace}:{type}:{id}
  
範例：
  oncology:gene:BRAF
  oncology:drug:Lenvatinib
  oncology:disease:PTC
  
  cardiology:disease:HeartFailure
  cardiology:drug:Metoprolol
  cardiology:procedure:Angioplasty
  
  neurology:disease:MultipleSclerosis
  neurology:drug:Rituximab
```

### 6.2 Graph Store 擴充

```go
// KnowGraphGo/graph/store/namespace.go (新檔案)

type Namespace struct {
    ID       string
    Label    string
    Ontology string // 參考的 ontology schema
}

type NamespacedStore interface {
    Store
    WithNamespace(ns string) Store    // 回傳 bound to namespace 的 store
    ListNamespaces() []Namespace
    CreateNamespace(ns Namespace) error
}
```

### 6.3 查詢路由

支援跨命名空間查詢：

```python
# 查詢範例
GET /api/v1/graph/query?namespace=cardiology&type=disease&q=HeartFailure
GET /api/v1/graph/query?namespace=*&type=drug&q=Metoprolol   # 跨所有 namespace
```

---

## 7. Clinical Terminology Mapping

### 7.1 Terminology Service

```python
# src/backend/platform/terminology/service.py

class TerminologyService:
    """
    臨床術語映射服務。
    - 統一名稱解析（不同專科可能用不同編碼系統）
    - 支援 ICD-10, SNOMED-CT, LOINC, RxNorm, OncoTree, DOID, MONDO
    - 每個 specialty 可註冊自己的 terminology mapping
    """
    
    async def normalize_code(
        self,
        code: str,
        source_system: str,
        target_system: str,
        specialty_id: str | None = None,
    ) -> list[TerminologyMapping]: ...
    
    async def search(
        self,
        term: str,
        systems: list[str],
        specialty_id: str | None = None,
    ) -> list[TerminologyConcept]: ...
```

### 7.2 Specialty-Specific 映射表

```
terminology/
├── base/                          # 通用映射（ICD-10, SNOMED）
│   ├── icd10_codes.json
│   └── snomed_map.json
├── oncology/                      # Oncology 專屬映射
│   ├── oncotree_map.json           (現有 IdentifierMapper)
│   └── doid_map.json
├── cardiology/
│   ├── icd10_cardiac.json
│   └── echocardiography_loinc.json
└── neurology/
    ├── icd10_neuro.json
    └── mri_protocols.json
```

### 7.3 動態解析流程

```
User Input: "Heart Failure"
    ↓
TerminologyService.search("Heart Failure", specialty="cardiology")
    ↓
1. ICD-10: I50.9 (Heart failure, unspecified)
2. SNOMED: 84114007 (Heart failure)
3. LOINC: 41969-0 (Heart failure panel)
    ↓
回傳 Unified Concept 物件
    ↓
ClinicalContext.diagnosis_code = "I50.9"
ClinicalContext.diagnosis_system = "ICD-10"
```

---

## 8. Versioning

### 8.1 多層級版本管理

```
Platform Version: 5.0.0
  ├── API Version: v1 (stable), v2 (beta)
  ├── Schema Version: 025 (database migration)
  ├── Specialty Versions:
  │   ├── oncology: 1.2.0
  │   ├── cardiology: 1.0.0
  │   └── neurology: 0.5.0 (alpha)
  ├── Agent Versions:
  │   ├── oncology.diagnosis_agent: 1.2.0
  │   └── cardiology.diagnosis_agent: 1.0.0
  └── Knowledge Graph Version:
      └── ontology: 2.0.0
```

### 8.2 API 版本策略

```python
# 所有端點保持 v1 向下相容
# 新端點使用 v2
# 每個端點回傳 X-API-Version header

@router.get("/v2/specialties/{specialty_id}/cases", response_model=CaseListResponse)
async def list_cases_v2(
    specialty_id: str,
    platform: PlatformContainer = Depends(get_platform),
):
    # v2 使用 specialty-aware service
    ...
```

### 8.3 資料庫 Migration 策略

```
migrations/
├── versions/
│   ├── 001_initial_oncology.py
│   ├── ...
│   ├── 025_phase3e_composite_unique.py
│   └── 026_platform_specialty_registry.py   # Phase 5 第一個 migration
│
├── specialties/
│   ├── cardiology/
│   │   └── 001_cardiology_base_tables.py
│   └── neurology/
│       └── 001_neurology_base_tables.py
```

- 共用表（users、patients、cases_base、evidence_items 等）在 platform migrations
- 專科特定表（cardiology_echo_results、neurology_lesions 等）在 specialty migrations
- Platform 啟動時自動執行所有 migrations

---

## 9. Tenant Isolation

### 9.1 現有架構

目前無 multi-tenant 支援（僅 Case ACL 提供病患層級隔離）。

### 9.2 Phase 5 Tenant 模型

```yaml
# config/tenants.yaml
tenants:
  default:
    specialties: ["oncology"]
    database: "sqlite:///./data/default.db"
  
  hospital_a:
    specialties: ["oncology", "cardiology", "radiology"]
    database: "postgresql://..."
    feature_flags:
      rag_enabled: true
      fhir_enabled: true
  
  research_org:
    specialties: ["oncology", "neurology"]
    database: "postgresql://..."
    feature_flags:
      ml_pipeline: true
```

### 9.3 隔離策略

| 層級 | 策略 | 實作方式 |
|------|------|---------|
| **資料庫** | 可選：同庫 schema 隔離 / 分庫隔離 | 連線字串 per tenant |
| **資料列** | `tenant_id` 過濾所有查詢 | BaseRepository 自動注入 |
| **配置** | Tenant-specific config overlay | Config registry |
| **快取** | Tenant-prefixed cache keys | Redis namespace |
| **檔案** | Tenant 子目錄隔離 | `storage/{tenant_id}/` |
| **Queue** | Tenant-specific queue | `queue:{tenant_id}:*` |
| **認證** | JWT claims 含 tenant_id | AuthService 擴充 |
| **Rate Limit** | Per-tenant quota | Throttling middleware |
| **計費** | Per-tenant usage tracking | AuditLogger 擴充 |

### 9.4 Tenant-Aware Repository

```python
class TenantAwareRepository(BaseRepository):
    """所有 tenant-aware 操作的基底。"""
    
    async def _apply_tenant_filter(self, stmt: Select, tenant_id: str | None = None) -> Select:
        tid = tenant_id or self._get_current_tenant()
        return stmt.where(self.model.tenant_id == tid)
    
    async def find(self, *criteria, tenant_id: str | None = None) -> list:
        stmt = await self._apply_tenant_filter(super()._build_query(*criteria), tenant_id)
        return await self._execute(stmt)
```

---

## 10. Platform API

### 10.1 端點總覽

```
# ── Platform Core（新）──
GET    /api/v1/platform/health
GET    /api/v1/platform/version
GET    /api/v1/platform/specialties
GET    /api/v1/platform/specialties/{id}/health
POST   /api/v1/platform/specialties/{id}/reload

# ── Terminology（新）──
GET    /api/v1/terminology/normalize?code=...&source=...&target=...
GET    /api/v1/terminology/search?q=...&system=...&specialty=...

# ── Workflow（新）──
POST   /api/v1/workflows/{workflow_id}/execute
GET    /api/v1/workflows/{execution_id}/status
POST   /api/v1/workflows/{execution_id}/pause
POST   /api/v1/workflows/{execution_id}/resume

# ── Tenant（新）──
POST   /api/v1/admin/tenants
GET    /api/v1/admin/tenants/{id}
PUT    /api/v1/admin/tenants/{id}
DELETE /api/v1/admin/tenants/{id}

# ── 現有端點（維持不變，逐步擴充 specialty_id 參數）──
GET    /api/v1/patients/{id}
POST   /api/v1/patients
GET    /api/v1/cases?specialty=oncology         ← 新增 specialty 篩選
GET    /api/v1/cases/{id}
POST   /api/v1/cases                           ← 新增 specialty 欄位
...
```

### 10.2 端點合約範例

```yaml
openapi: 3.0.0
info:
  title: Medical AI Platform API
  version: 5.0.0
  x-platform-version: 5.0.0
  x-default-specialty: oncology

paths:
  /api/v1/specialties:
    get:
      summary: 列出所有已註冊專科
      responses:
        200:
          schema:
            type: array
            items:
              $ref: '#/definitions/SpecialtyManifest'
  
  /api/v1/workflows/execute:
    post:
      parameters:
        - name: X-Tenant-ID
          in: header
          required: true
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                workflow_id: { type: string }
                specialty_id: { type: string, default: "oncology" }
                case_id: { type: string }
      responses:
        202:
          description: Workflow execution accepted
```

### 10.3 Middleware 變更

```python
# 新增 middleware chain：
# 1. TenantMiddleware → 解析 X-Tenant-ID header
# 2. SpecialtyMiddleware → 解析 X-Specialty-ID header
# 3. ContextMiddleware → 建立 PlatformContainer 注入
# 4. AuthMiddleware → 驗證 tenant 權限（現有）
```

---

## 11. Sample Specialty Modules

### 11.1 Cardiology（心臟科）

**Scope**：Phase 5 第一個非 oncology sample module。

| 元件 | 實作內容 | 來源 |
|------|---------|------|
| Domain | CardioCaseModel, EchoResult, ECGReport, CardioMedication | 新寫 |
| Agents | DiagnosisAgent（心衰竭分類）、GuidelineAgent（ESC/HFSA）、RiskAgent（SCORE2/ASCVD） | 新寫 |
| Workflow | 胸痛診斷流程、心衰竭評估流程 | 新寫 |
| Evidence | ESC Guidelines adapter、ClinicalTrials.gov heart filter、PubMed cardiac filter | 新寫 |
| Rules | NYHA Classification rule、LVEF assessment rule | 新寫 |
| Adapters | ECG/Holter parser（stub）、Echocardiography DICOM->measurement | stub |
| Terminology | ICD-10 I00-I99 mapping、LOINC cardiac panel codes | 新增 mapping |
| Tests | 10+ test 檔案 | 新寫 |

**Module 結構**：
```
src/backend/specialties/cardiology/
├── __init__.py                  # 匯出 SpecialtyManifest + create_specialty
├── manifest.json                # 版本、依賴、描述
├── config.py                    # Pydantic config model
├── models/
│   ├── cardio_case.py
│   ├── echo_result.py
│   └── ecg_report.py
├── agents/
│   ├── diagnosis_agent.py
│   ├── guideline_agent.py
│   └── risk_agent.py
├── workflows/
│   └── chest_pain_workflow.py
├── rules/
│   ├── nyha_rules.yaml
│   └── lvef_rules.yaml
├── adapters/
│   ├── esc_guidelines_adapter.py
│   └── ecg_parser.py
├── services/
│   └── cardio_assessment_service.py
├── terminology/
│   ├── icd10_cardiac.json
│   └── loinc_cardiac.json
├── tests/
│   ├── test_diagnosis_agent.py
│   ├── test_workflow.py
│   └── test_integration.py
└── migrations/
    └── 001_cardiology_base.py
```

### 11.2 Neurology（神經科）

| 元件 | 實作內容 | 優先級 |
|------|---------|--------|
| Domain | NeuroCaseModel, LesionModel, MSAssessment, StrokeScale | P1 |
| Agents | DiagnosisAgent（MS 診斷 criteria）、ImagingAgent（MRI lesion 分析）、StrokeAgent（NIHSS） | P1 |
| Workflow | 多發性硬化症診斷流程、急性中風評估流程 | P2 |
| Evidence | PubMed neuro filter、ClinicalTrials.gov neuro trials | P2 |
| Rules | McDonald criteria、EDSS scoring、NIHSS scoring | P1 |
| Terminology | ICD-10 G00-G99、SNOMED neuro concepts | P1 |

### 11.3 Radiology（放射科）

| 元件 | 實作內容 | 優先級 |
|------|---------|--------|
| Domain | RadiologyStudy, ImageFinding, AIFinding, ReportTemplate | P2 |
| Agents | ImageAnalysisAgent（分類/分割/檢測）、ReportAgent（報告生成） | P2 |
| Workflow | 影像上傳→AI推論→放射師審閱→報告產出 | P2 |
| DICOM | DICOMweb WADO-RS、STOW-RS 支援（依賴 Phase 4 DICOM 基礎） | P2 |
| Adapters | DICOM parser、AI model inference adapter | P2 |

---

## 12. Batch 拆分

### 12.1 整體時程

```
Phase 5 總預估工期：16-20 週（4-5 個月）
```

### 12.2 Batch 1 — Platform Core (Weeks 1-3)

**目標**：完成 Platform 骨架與 Registry 基礎，不影響 Oncology 模組。

| 交付項 | 內容 | 依賴 |
|--------|------|------|
| B1.1 | SpecialtyRegistry + 生命週期管理 | 無 |
| B1.2 | AgentRegistry + Agent selection strategy | B1.1 |
| B1.3 | WorkflowRegistry + WorkflowEngine 基礎 | B1.1 |
| B1.4 | EvidenceSourceRegistry | B1.1 |
| B1.5 | RuleSetRegistry | B1.1 |
| B1.6 | Platform API 端點 (health/version/specialties) | B1.1-B1.5 |
| B1.7 | PlatformContainer + DI 注入 | B1.1 |
| B1.8 | Migration 026 (platform_registry_tables) | 無 |
| B1.9 | 現有 oncology 模組自動註冊為 built-in specialty | B1.1 |
| B1.10 | 測試：Registry unit tests + contract tests | B1.1-B1.5 |

**驗收標準**：
- 啟動時自動掃描並註冊 oncology 模組
- API `/api/v1/platform/specialties` 回傳 oncology 資訊
- 現有 oncology 功能完全不受影響（regression test pass）
- All registry unit tests pass

### 12.3 Batch 2 — Specialty Module Contract + Cardiology Sample (Weeks 4-7)

**目標**：定義 Specialty Module Contract，實作 Cardiology 樣板。

| 交付項 | 內容 | 依賴 |
|--------|------|------|
| B2.1 | SpecialtyBase 介面定義 | B1.1 |
| B2.2 | .template/ 模版目錄 | B2.1 |
| B2.3 | Cardiology Module 建立（manifest + base structure） | B2.1 |
| B2.4 | Cardiology Domain Models | B2.3 |
| B2.5 | Cardiology Agents（diagnosis + guideline + risk） | B2.3, B1.2 |
| B2.6 | Cardiology Workflow（胸痛評估） | B2.3, B1.3 |
| B2.7 | Cardiology Terminology Mapping（ICD-10 cardiac + LOINC） | B1.1 |
| B2.8 | Cardiology Tests | B2.3-B2.7 |
| B2.9 | TerminologyService 實作 | B1.1 |

**驗收標準**：
- Cardiology module 可獨立註冊/啟動/停止
- `POST /api/v1/workflows/cardiology.chest_pain/execute` 可執行
- `GET /api/v1/terminology/normalize` 正確映射 cardiac codes
- Cardiology agent 可分析 CardiologyCase 並回傳有意義的 opinion
- 所有 test pass

### 12.4 Batch 3 — Oncology 抽象化 (Weeks 8-10)

**目標**：逐步提取 Oncology 模組中的通用介面，**不破壞現有功能**。

| 交付項 | 內容 | 依賴 |
|--------|------|------|
| B3.1 | AbstractCase 介面 + CancerCase 繼承 | B1.1 |
| B3.2 | AbstractConsensus 介面 + TumorBoardConsensus 繼承 | B1.1 |
| B3.3 | ClinicalContext 擴充（diagnosis_code + diagnosis_system） | B2.9 |
| B3.4 | ClinicalContext.specialty_id 欄位 | B1.1 |
| B3.5 | Agent 改造（SpecialtyAgentMixin + 註冊化） | B1.2, B2.5 |
| B3.6 | 治療計畫 rules 中的 oncology-specific 邏輯提取 | B1.5 |
| B3.7 | Oncology-specific terminology 提取至 plugin | B2.9 |
| B3.8 | scorer 中 oncology mapping 提取 | B1.5 |
| B3.9 | 回歸測試（確保 oncology 功能不變） | 全部 |

**驗收標準**：
- Oncology module 仍可正常運作（regression test suite pass）
- CancerCaseModel 仍可正常 CRUD（繼承 AbstractCase）
- ClinicalContext.cancer_type 仍可讀取（alias 保留）
- Agent selection 可正確選擇 oncology agent
- 無任何 breaking change

### 12.5 Batch 4 — Knowledge Graph Namespace + Terminology (Weeks 11-12)

**目標**：擴充 KnowGraphGo 支援 namespace，完善 terminology 映射。

| 交付項 | 內容 | 依賴 |
|--------|------|------|
| B4.1 | KnowGraphGo NamespacedStore 實作 | 無（Go 專案） |
| B4.2 | Knowledge Graph API 擴充（namespace 參數） | B4.1 |
| B4.3 | TerminologyService 完成（含 cache + bulk lookup） | B2.9 |
| B4.4 | Specialty-specific terminology mapping CLI 工具 | B4.3 |
| B4.5 | Oncology namespace 遷移（現有 graph data 加 prefix） | B4.1 |
| B4.6 | Go pipeline in CI/CD（go build + test + lint） | 無 |

**驗收標準**：
- KnowGraphGo 支援 `WithNamespace(ns)` 查詢
- 跨 namespace 查詢正確路由
- TerminologyService 可解析 ICD-10 / SNOMED / LOINC
- CI 包含 Go pipeline

### 12.6 Batch 5 — Tenant Isolation + API Versioning (Weeks 13-14)

**目標**：引入 multi-tenant 架構與 API 版本管理。

| 交付項 | 內容 | 依賴 |
|--------|------|------|
| B5.1 | TenantMiddleware + JWT tenant claims | B1.1 |
| B5.2 | TenantAwareRepository（共用表加 tenant_id） | B5.1 |
| B5.3 | Tenant config registry（YAML + env） | B1.1 |
| B5.4 | Tenant admin API（CRUD） | B5.1 |
| B5.5 | API v2 端點規劃（首個 v2 端點：workflows） | B1.6 |
| B5.6 | 現有 v1 端點標記 specialty_id 支援 | B5.1 |
| B5.7 | 檔案/queue/快取隔離策略實作 | B5.1 |

**驗收標準**：
- Multi-tenant 可正常運作（至少 2 tenant 各自隔離）
- 無 tenant 可存取另一 tenant 資料
- Tenant config 可動態 overlay
- API 端點同時支援 v1 與 v2

### 12.7 Batch 6 — Neurology + Radiology Samples (Weeks 15-17)

**目標**：基於完成的 Platform 快速建立 Neurology 與 Radiology 樣板。

| 交付項 | 內容 | 依賴 |
|--------|------|------|
| B6.1 | Neurology Module（domain + agents + workflow） | B2.1-B2.8 |
| B6.2 | Neurology Terminology（ICD-10 G00-G99 + SNOMED） | B4.3 |
| B6.3 | Neurology Tests | B6.1 |
| B6.4 | Radiology Module（基礎結構 + DICOM study model） | B2.1, Phase 4 DICOM |
| B6.5 | Radiology AI Agent（stub） | B6.4 |
| B6.6 | Radiology Tests | B6.4-B6.5 |
| B6.7 | Cross-specialty 整合測試 | 全部 |

**驗收標準**：
- Neurology module 可獨立運作
- Radiology module 可接收 DICOM study
- 跨專科 Workflow 可查詢（例如 Cardiology 轉診至 Radiology）
- 全部 3 個 sample specialty 在 production 配置中同時啟用

### 12.8 Batch 7 — 文件、遷移指南、驗收 (Week 18)

| 交付項 | 內容 |
|--------|------|
| B7.1 | Phase 5 開發者文件（如何建立新 Specialty） |
| B7.2 | API 文件更新（OpenAPI 3.0） |
| B7.3 | 從單一 Oncology 遷移至 Multi-Specialty 指南 |
| B7.4 | 效能測試報告（multi-tenant + multi-specialty） |
| B7.5 | 安全審查（tenant isolation + specialty isolation） |
| B7.6 | 最終驗收測試 |

---

## 13. 驗收標準

### 13.1 強制標準（Must-Have）

| # | 標準 | 驗證方式 |
|---|------|---------|
| AC1 | Oncology 模組完全不受影響 | 全部現有 test suite pass |
| AC2 | 至少 1 個非 oncology specialty（cardiology）可完整運作 | E2E test |
| AC3 | Registry 可正確註冊/啟動/停止 specialty | API test |
| AC4 | Agent selection 依 specialty 正確路由 | Integration test |
| AC5 | Knowledge Graph 支援 namespace 隔離 | Go test |
| AC6 | Terminology Service 可正確映射 ICD-10/SNOMED | Unit test |
| AC7 | Multi-tenant 資料隔離 | Security test |
| AC8 | API 向下相容（v1 端點不改） | Regression test |
| AC9 | 所有 Batch 測試覆蓋率 ≥80% | Coverage report |

### 13.2 期望標準（Should-Have）

| # | 標準 | 優先級 |
|---|------|--------|
| SC1 | Neurology module 可基本運作 | P1 |
| SC2 | Radiology module 可接收 DICOM study | P2 |
| SC3 | Cross-specialty terminology lookup | P1 |
| SC4 | Platform API 版本管理（v1/v2） | P1 |
| SC5 | CI/CD 包含 Go pipeline | P1 |
| SC6 | 開發者文件完成 | P1 |

### 13.3 未來標準（Could-Have，Phase 6+）

| # | 標準 | 
|---|------|
| CC1 | 第三方 Specialty Module 套件管理（pip 安裝） |
| CC2 | Specialty Marketplace |
| CC3 | Dynamic hot-reload of specialty modules |
| CC4 | Cross-specialty clinical pathway engine |
| CC5 | Multi-specialty federated knowledge graph |

---

## 14. Phase 4 依賴項目

以下為 Phase 5 依賴但需 Phase 4 完成的事項。若 Phase 4 未完成，Phase 5 的對應 Batch 將受阻。

| Phase 4 交付項 | 依賴的 Phase 5 Batch | 風險等級 |
|---------------|---------------------|---------|
| **FHIR R4 完整實作**（Patient/Observation/MedicationRequest/DiagnosticReport） | B6.4（Radiology DICOM→FHIR） | 🟡 Medium |
| **HL7/DICOM/PACS 基礎**（DICOMweb WADO-RS, STOW-RS） | B6.4（Radiology Module） | 🟠 High |
| **RAG/Vector DB/Embedding Pipeline** | B6.1-B6.6（所有 specialty 的語義搜尋） | 🟡 Medium |
| **ML Model Pipeline**（train/eval/deploy） | B6.5（Radiology AI Agent） | 🟡 Medium |
| **Adapters 實作**（8 個 stub 完成真實連接） | B2.7, B6.1（Cardio/Neuro evidence sources） | 🟢 Low |
| **Observability 強化**（metrics/tracing） | B1.1-B7.6（平台監控） | 🟢 Low |
| **Frontend API Client 統一封裝** | B2.3-B6.6（新 specialty 前端整合） | 🟢 Low |

### 14.1 相依性矩陣

```
Phase 4 完成度     Phase 5 Batch 風險
─────────────────────────────────────────────────
FHIR:    □ 未完成 → B6.4 (Radiology) 受阻
DICOM:   □ 未完成 → B6.4 (Radiology) 受阻  
RAG:     □ 未完成 → 語義搜尋功能受限
ML:      □ 未完成 → AI Agent 部分功能受限
Adapters: □ 未完成 → 證據來源受限但不阻斷
Observ:  □ 未完成 → 平台監控受限但不阻斷
```

建議 Phase 4 優先完成 FHIR R4 與 DICOM 基礎，確保 Phase 5 Batch 6（Radiology）可如期交付。

---

## 附錄 A：檔案變更清單

### A.1 新檔案

```
src/backend/platform/
├── __init__.py
├── config.py
├── di.py
├── middleware.py
├── container.py
├── version.py
└── registry/
    ├── __init__.py
    ├── base.py                    # BaseRegistry
    ├── specialty_registry.py
    ├── agent_registry.py
    ├── workflow_registry.py
    ├── evidence_source_registry.py
    └── rule_registry.py

src/backend/platform/terminology/
├── __init__.py
├── service.py
├── models.py
├── repository.py
└── mappings/
    ├── icd10.json
    ├── snomed.json
    ├── loinc.json
    └── rxnorm.json

src/backend/specialties/
├── __init__.py
├── .template/
│   ├── __init__.py
│   ├── manifest.json
│   ├── config.py
│   ├── models.py
│   ├── agents/
│   ├── workflows/
│   ├── rules/
│   ├── services/
│   ├── adapters/
│   └── tests/
├── cardiology/
│   ├── ... (module structure)
├── neurology/
│   ├── ... (module structure)
└── radiology/
    ├── ... (module structure)

src/backend/api/v2/
├── __init__.py
├── router.py
├── specialties.py
├── workflows.py
├── terminology.py
└── tenants.py

migrations/versions/
└── 026_platform_specialty_registry.py

migrations/specialties/cardiology/
└── 001_cardiology_base.py

KnowGraphGo/graph/store/namespace.go
KnowGraphGo/graph/store/namespace_test.go
```

### A.2 修改檔案

```
src/backend/domain/cancer_case.py       → 繼承 AbstractCase
src/backend/domain/enums.py             → SpecialtyType 移至 platform
src/backend/clinical/models.py          → 加 diagnosis_code/diagnosis_system/specialty_id
src/backend/agents/orchestrator.py      → 使用 AgentRegistry
src/backend/agents/base.py              → 加 SpecialtyAgentMixin（選擇性）
src/backend/database/base.py            → 加 tenant_id mixin
src/backend/repositories/base.py        → 加 TenantAwareRepository
src/backend/auth/dependencies.py        → 加 tenant dependency
src/backend/main.py                     → 初始化 PlatformContainer + Registry
src/backend/middleware.py               → 加 TenantMiddleware + SpecialtyMiddleware
```

### A.3 無需修改檔案（直接複用）

以下檔案於 Phase 5 **完全不需要修改**：

- 所有 domain models 除 cancer_case.py（~24 檔案保持原樣）
- 所有 repositories 除 base.py（~22 檔案保持原樣）
- 所有 engines（recommendation_engine.py, clinical_decision_engine.py, ranking/engine.py, reasoning/service.py, explainable_recommendation.py）
- 所有現有 API v1 routes（23 檔案保持原樣）
- KnowGraphGo 全部 13 packages（新增而非修改）
- 所有 frontend 程式碼
- 所有現有 services（僅 tumor_board_service 與 treatment_plan_service 需微調）
- 所有現有 tests（~99 backend tests + 35 Go tests）

---

*本 Master Plan 基於 `tasks/research/current-capability-inventory.md` 盤點結果制定，確保 Phase 5 工作有據可依、可拆分交付。*
