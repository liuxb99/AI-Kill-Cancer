# ADR-006: Specialty Module Architecture

**Status**: Accepted (Phase 5)

**Date**: 2026-07-31

## Context

Phase 5 的核心目標是將目前的 Oncology-only 系統提煉為多專科 Medical AI Platform，支援 Cardiology、Neurology、Radiology 等專科的插件式擴充。

根據盤點結果，現有系統約 65% 的程式碼可直接複用，26% 需抽象化，僅 9% 為 Oncology 專屬。這意味著一個良好的模組化架構可以讓新專科「即插即用」。

需要決策的核心問題：

1. **模組（Specialty Module）的邊界是什麼？** — 一個模組應包含哪些元件？
2. **註冊機制** — 模組如何被平台發現和載入？
3. **模組生命週期** — 模組的安裝、啟動、停止、卸載流程？
4. **隔離策略** — 模組之間如何避免互相干擾？
5. **依賴管理** — 模組之間可以互相依賴嗎？版本如何約束？
6. **與既有 Oncology 模組的關係** — 既有程式碼如何融入此架構？
7. **Workflow Registry 的位置** — 工作流定義是否屬於模組的一部分？

## Decision

### 1. Specialty Module 邊界定義

一個 Specialty Module 是一個自包含的 Python 套件，位於 `src/backend/specialties/{specialty_id}/`，包含以下元件：

```
specialties/{specialty_id}/
├── __init__.py           # 匯出 SPECIALTY_MANIFEST 和 create_specialty()
├── manifest.json         # 模組 metadata（id, version, display_name, dependencies）
├── config.py             # Pydantic BaseSettings 配置模型
├── models.py             # 專科領域模型（繼承 AbstractCase 等）
├── agents/               # 專科專屬 Agent（選擇性）
│   ├── __init__.py
│   └── diagnosis_agent.py
├── workflows/            # 專科工作流定義（選擇性）
│   ├── __init__.py
│   └── chest_pain.yaml
├── rules/                # 專科業務規則（選擇性）
│   ├── __init__.py
│   └── cardiac_rules.yaml
├── services/             # 專科專屬 Service（選擇性）
│   └── cardio_assessment.py
├── adapters/             # 專科專屬外部資料源 adapter（選擇性）
│   └── esc_guidelines.py
├── terminology/          # 專科術語映射檔
│   ├── icd10_cardiac.json
│   └── loinc_cardiac.json
├── tests/                # 專科測試
│   └── test_workflow.py
└── migrations/           # 專科資料庫遷移
    └── 001_cardiology_base.py
```

**強制要求**：`__init__.py`、`manifest.json`、`config.py`、`tests/`
**選擇性**：其他目錄

### 2. 註冊機制：Explicit Manifest + Python Entry Point

每個 Specialty Module 透過 `manifest.json` 和 Python 程式碼中的 Entry Point 註冊：

```json
{
  "id": "cardiology",
  "version": "0.1.0",
  "display_name": "Cardiology",
  "description": "心臟科臨床決策支援模組",
  "entry_point": "specialties.cardiology",
  "dependencies": [],
  "config_schema": {
    "type": "object",
    "properties": { ... }
  }
}
```

```python
# specialties/cardiology/__init__.py
from src.backend.platform.registry import SpecialtyManifest, SpecialtyBase

SPECIALTY_MANIFEST = SpecialtyManifest(
    id="cardiology",
    version="0.1.0",
    display_name="Cardiology",
    description="心臟科臨床決策支援模組",
    entry_point="specialties.cardiology",
    dependencies=[],
)

def create_specialty(config: dict) -> SpecialtyBase:
    """Factory function — 由 Platform 在啟動時呼叫"""
    ...
```

**掃描策略**：Platform 啟動時掃描 `specialties/` 目錄下的所有子目錄，載入其 `manifest.json`，然後透過 `create_specialty()` 初始化。

### 3. 模組生命週期：五階段模型

```
┌─────────────────────────────┐
│       DISCOVERED            │ ← Platform 啟動時掃描目錄
└──────────┬──────────────────┘
           │ install (載入 manifest + 驗證依賴)
┌──────────▼──────────────────┐
│       REGISTERED            │ ← Metadata 存入 registry
└──────────┬──────────────────┘
           │ load (呼叫 create_specialty + 執行 migration)
┌──────────▼──────────────────┐
│        LOADED               │ ← 配置驗證完成，Agent/Workflow 註冊
└──────────┬──────────────────┘
           │ start
┌──────────▼──────────────────┐
│        ACTIVE               │ ← 正常提供服務
└──────────┬──────────────────┘
           │ stop
┌──────────▼──────────────────┐
│        STOPPED              │ ← 優雅關閉（不再接受新請求）
└─────────────────────────────┘
```

- **DISCOVERED → REGISTERED**：自動執行（Platform 啟動時）
- **REGISTERED → LOADED**：驗證配置、執行 migration、註冊 agent/workflow
- **LOADED → ACTIVE**：health check 通過後自動切換
- **ACTIVE → STOPPED**：收到 stop 信號時關閉，不卸載 metadata
- 支援 hot-restart（STOPPED → LOADED → ACTIVE）

### 4. 隔離策略：Namespace-based + Config Isolation

| 層面 | 隔離方式 |
|------|---------|
| **API 命名空間** | 所有端點前綴 `{specialty_id}.`，如 `cardiology.chest_pain` |
| **Agent 命名空間** | Agent Registry 中以 `{specialty_id}.{agent_type}` 作為唯一鍵 |
| **Workflow 命名空間** | Workflow ID 前綴 `{specialty_id}.{workflow_id}` |
| **配置隔離** | 每個模組有獨立配置命名空間，透過 YAML 層疊（platform default → specialty default → tenant override） |
| **資料表隔離** | 模組專屬資料表使用 `{specialty_id}_` 前綴 |
| **Process 隔離** | 不採用（同 Process 內載入所有模組），留待 Phase 6 評估 microservice 拆分 |

### 5. 依賴管理

- 支援 specialty 之間的依賴宣告（`dependencies: ["oncology"]`）
- 使用 Semver 版本約束（`^0.1.0`, `~0.1.0`, `>=1.0.0`）
- 依賴解析在 REGISTERED → LOADED 階段執行
- **不支援循環依賴**（啟動時檢測並拋出錯誤）
- Oncology 模組是 Built-in Specialty，所有其他 specialty 不強制依賴它

### 6. 既有 Oncology 模組的遷移策略

- **保留原位**：既有 oncology 程式碼保留在原來位置（`src/backend/domain/`, `src/backend/clinical/` 等），不強制搬遷
- **自動註冊為 Built-in Specialty**：Platform 啟動時將既有 oncology 模組自動註冊為 `oncology` specialty
- **逐步抽象化**：在 Phase 5 Batch 3 中提取 `AbstractCase`、`AbstractConsensus` 等介面，但保留向下相容
- **不要求大規模重寫**：維持 Phase 5 的「不破壞現有功能」原則

### 7. Workflow Registry 作為 Platform Core 的一部分

Workflow Registry（`src/backend/platform/registry/workflow_registry.py`）是 Platform 層級的元件，不屬於單一 Specialty Module：

- Specialty Module 透過 `create_specialty()` 中的註冊呼叫來註冊自己的 workflow
- Workflow 定義支援 YAML/JSON 格式
- Workflow Engine 負責執行 workflow step + state transition
- 跨 specialty workflow（如 Cardiology 轉診至 Radiology）由 Platform Workflow Engine 協調

## Consequences

### Positive

- **插件化擴充**：新專科只需建立一個目錄 + 實作必要介面，即可整合到平台
- **既有系統零破壞**：Oncology 模組保持原樣運作，Platform 化過程不影響生產
- **標準化合約**：所有 Specialty Module 遵循相同結構，降低開發者學習成本
- **清晰的生命週期管理**：模組的啟動/停止/錯誤處理有統一機制
- **Workflow 與 Module 一體化**：工作流定義隨 module 發布，版本一致

### Negative

- **同 Process 隔離不足**：某個 specialty 的 bug 可能影響整個 Platform 穩定性
- **目錄結構約束**：開發者必須遵循特定目錄結構，無法自由組織程式碼
- **Manifest 維護負擔**：版本號和依賴需要手動更新
- **Oncology 模組的雙重位置**（既有路徑 + specialty 註冊）可能造成維護者困惑

### Risk

| 風險 | 影響 | 緩解措施 |
|------|------|---------|
| Specialty Module 之間的名稱衝突 | 中 | Namespace 前綴機制 + Registry 註冊時檢測衝突 |
| Module 版本升級導致平台不穩定 | 中 | 版本約束 + Integration Test Suite + 可以 rollback 到前一版本 |
| 開發者不熟悉 Module Contract 導致實作錯誤 | 低 | 提供 `.template/` 目錄作為專案範本 + 開發文件 |
| Workflow 定義與 Platform Workflow Engine 版本不匹配 | 低 | Workflow Registry 驗證 workflow schema 版本相容性 |

## Related

- Phase 5 Master Plan §1 (Oncology 耦合盤點)
- Phase 5 Master Plan §2 (Registry/Plugin 化設計)
- Phase 5 Master Plan §3 (Specialty Module Contract)
- Phase 5 Master Plan §4 (Workflow Module Contract)
- Phase 5 Master Plan §12.2 Batch 1 (Platform Core)
- Phase 5 Master Plan §12.3 Batch 2 (Cardiology Sample)
- Phase 5 Master Plan §12.4 Batch 3 (Oncology 抽象化)
