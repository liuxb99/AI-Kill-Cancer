# ADR-001: FHIR Canonical Model Strategy

**Status**: Accepted (Phase 4)

**Date**: 2026-07-31

## Context

Phase 4 需要將系統從僅有簡化版 `FHIRExporter`（位於 `reporting/renderer.py`，約 60 行）升級為完整的 FHIR R4 互通能力，包括：

- 支援 FHIR R4 核心資源：Patient, Observation, MedicationRequest, DiagnosticReport, Condition, Procedure, CarePlan
- 提供標準 FHIR REST API（read/search/create/update）
- 支援 SMART-on-FHIR 授權框架
- 產出符合規範的 FHIR 資源（需驗證）

目前系統已有 25+ 領域模型（Domain Model），這些模型是系統的核心資料結構，被 Agent Engine、Clinical Engine、Knowledge Graph 等元件廣泛使用。引入 FHIR 時面臨的核心問題是：**如何處理 FHIR 資源與內部 Domain Model 之間的映射關係**。

具體需要決策的子問題：

1. 是否建立獨立的「FHIR Canonical Model」層？
2. FHIR 資源與 Domain Model 的映射邏輯應放在哪裡？
3. 映射方向：單向（Domain → FHIR）還是雙向（FHIR → Domain）？
4. FHIR 驗證在什麼時機執行？
5. SMART-on-FHIR 授權如何整合到現有 RBAC/ACL 系統？

## Decision

### 1. 建立獨立的 FHIR Layer（含 Canonical Model），不直接擴充 Domain Model

建立一個新的 `src/backend/fhir/` 模組，包含：

- **FHIR Canonical Model**（`src/backend/fhir/models/`）：與 FHIR R4 規範一一對應的 Pydantic model，獨立於現有 Domain Model
- **FHIR REST API**（`src/backend/fhir/api/`）：符合 FHIR R4 規範的 RESTful 端點
- **Mapping Layer**（`src/backend/fhir/mappings/`）：Domain Model ↔ FHIR Resource 的雙向轉換器
- **Validation Layer**（`src/backend/fhir/validation/`）：基於 FHIR Path 的資源驗證

### 2. 採用「雙向映射但以 Domain Model 為真實來源」策略

- **Domain Model 是真實來源（Source of Truth）**：所有業務邏輯、Agent 決策、Knowledge Graph 操作都基於 Domain Model
- **FHIR Resource 是互通表示（Interchange Representation）**：僅用於與外部 EHR/HIS 系統交換資料
- **映射方向**：支援雙向（Domain → FHIR 用於輸出，FHIR → Domain 用於輸入），但 FHIR → Domain 映射僅處理核心欄位，不接受 FHIR 直接修改 Domain 的全部狀態
- **寫入路徑**：外部系統透過 FHIR API 寫入 → Mapping Layer 轉換為 Domain Model → 既有 Service Layer 處理業務邏輯 → 存入 Database

### 3. FHIR Validation 在 API Entry 和 API Exit 兩個點執行

- **寫入時**（Entry 驗證）：接收 FHIR Resource 後立即驗證結構符合性，拒絕無效資源
- **讀出時**（Exit 驗證）：Domain → FHIR 轉換後再次驗證，確保輸出的 FHIR 資源合法
- 內部 Domain Model 不儲存 FHIR 驗證狀態

### 4. SMART-on-FHIR 與現有 RBAC 整合

- SMART-on-FHIR 僅作為授權框架的**入口通道**（EHR 系統透過 SMART-on-FHIR 啟動 session）
- 內部授權仍使用既有 RBAC/ACL 系統（6 角色 + JWT + Case 層級 ACL）
- SMART-on-FHIR scope 對應到內部角色權限

### 5. 不採用「直接擴充 Domain Model 加入 FHIR 序列化」方案

理由：
- Domain Model 的變更會影響整個系統（25+ models, 23 repositories, 100+ endpoints）
- 保持關注點分離（Separation of Concerns）
- FHIR R4 資源結構複雜，與 Domain Model 的設計哲學不同（FHIR 強調互通性，Domain Model 強調業務語義）

## Consequences

### Positive

- **關注點分離**：FHIR 相關邏輯與業務邏輯完全解耦，任一方的變更不影響另一方
- **獨立演進**：FHIR 版本升級（如 R4 → R5）時只需修改 FHIR Layer，Domain Model 不受影響
- **測試便利**：FHIR mapping 可獨立單元測試，不依賴 Database 或 Service Layer
- **開發平行化**：FHIR Layer 和既有系統可由不同開發者同時開發

### Negative

- **額外維護成本**：需要維護兩套 Model + Mapping Code
- **映射複雜度**：某些 FHIR Resource（如 Observation）與 Domain Model 的對應不是 1:1，需要組合/拆分邏輯
- **效能開銷**：每次 FHIR API 呼叫需執行 Domain ↔ FHIR 轉換，引入微小的延遲

### Risk

| 風險 | 影響 | 緩解措施 |
|------|------|---------|
| Mapping 維護工作量大 | 中 | 優先實作唯讀（Read/Search）端點，寫入端點延後 |
| FHIR 資源結構變動 | 低 | 使用 Pydantic 嚴格模式，明確欄位版本 |
| 效能 overhead | 低 | Mapping 為純記憶體操作，benchmark 確認 < 5ms 延遲 |

## Related

- Phase 4 Master Plan §2.2.2 Hospital Integration Layer
- Phase 4 Master Plan §6 FHIR Boundary
