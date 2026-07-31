# Architecture Decision Records

本目錄包含基於 Phase 4 (Clinical AI Productization) 與 Phase 5 (Medical AI Platform) Master Plan 產出的架構決策記錄。

## 評估結果

| # | ADR 主題 | 判斷 | 原因 |
|---|---------|------|------|
| 1 | FHIR Canonical Model Strategy | ✅ ADR-001 | FHIR 與 Domain Model 的映射策略會影響整體架構，且有多種可行方案需選擇 |
| 2 | External Evidence Adapter Strategy | ✅ ADR-002 | 8 個 adapter 的統一架構、快取、錯誤處理需要標準化決策 |
| 3 | RAG vs Knowledge Graph Responsibilities | ✅ ADR-003 | 兩個知識基礎設施的職責邊界模糊，需明確分工避免重複建設 |
| 4 | Clinical Terminology Strategy | ✅ ADR-004 | 跨專科術語標準選擇影響深遠，且涉及 Canonical Code 與既有系統相容性 |
| 5 | Multi-Tenant Isolation Strategy | ✅ ADR-005 | 資料隔離方案選擇（shared DB / schema / separate DB）影響資料安全與運維成本 |
| 6 | Specialty Module Architecture | ✅ ADR-006 | Phase 5 核心架構決策，包含模組邊界、生命週期、註冊機制等 |
| 7 | Workflow Registry Architecture | ❌ 併入 ADR-006 | Workflow Registry 是 Specialty Module Architecture 的自然子元件，無需獨立決策 |
| 8 | Model and Prompt Versioning | ❌ 不需要 | Phase 4 明確排除 ML Model Training Pipeline；Prompt 版本管理現有機制足以應付，無重大架構分歧 |
| 9 | Background Job Architecture | ❌ 不需要 | Phase 4 B4（Infrastructure & Observability）已規劃透過 ARQ + Redis 實作 Background Jobs，技術選型已在 Phase 4 Master Plan 中充分論證，無需獨立 ADR。若後續引入 Kafka 或其他 message broker 時可重新評估 |
| 10 | Audit and Provenance Strategy | ❌ 不需要 | Phase 3 已有的 Digital Thread + Audit Log 機制完整，Phase 4/5 無需根本性改變 |

## ADR 列表

| 檔案 | 適用階段 | 簡要描述 |
|------|---------|---------|
| [ADR-001](ADR-001-fhir-canonical-model-strategy.md) | Phase 4 | FHIR 資源與 Domain Model 的映射層設計 |
| [ADR-002](ADR-002-external-evidence-adapter-strategy.md) | Phase 4 | 外部證據源 Adapter 的統一架構與錯誤處理策略 |
| [ADR-003](ADR-003-rag-knowledge-graph-responsibilities.md) | Phase 4 | RAG 與 Knowledge Graph 的職責邊界與協同模式 |
| [ADR-004](ADR-004-clinical-terminology-strategy.md) | Phase 5 | 臨床術語標準選型（SNOMED/ICD/LOINC/RxNorm）與映射策略 |
| [ADR-005](ADR-005-multi-tenant-isolation-strategy.md) | Phase 5 | 多租戶隔離方案（Shared DB + Row-level tenant_id） |
| [ADR-006](ADR-006-specialty-module-architecture.md) | Phase 5 | 專科模組架構（Module Contract + Registry + Lifecycle） |

## ADR 格式

每個 ADR 文件使用以下格式：

- **Status**: 目前狀態（Accepted / Proposed / Deprecated）
- **Date**: 決策日期
- **Context**: 背景與需要決策的問題
- **Decision**: 明確的決策描述
- **Consequences**: Positive / Negative / Risk
- **Related**: 相關文件或 ADR
