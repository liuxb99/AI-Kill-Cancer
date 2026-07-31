# ADR-004: Clinical Terminology Strategy

**Status**: Accepted (Phase 5)

**Date**: 2026-07-31

## Context

Phase 5 將系統從單一 Oncology 專科擴充為多專科 Medical AI Platform，不同專科使用不同的臨床術語系統：

| 專科 | 常用術語標準 |
|------|------------|
| Oncology（既有） | OncoTree, DOID, HGVS, CIViC variants |
| Cardiology（新建） | ICD-10-CM I00-I99, LOINC cardiac panel, SNOMED CT cardiac concepts |
| Neurology（新建） | ICD-10-CM G00-G99, SNOMED CT neuro concepts |
| Radiology（新建） | LOINC radiology, SNOMED CT imaging, RadLex |

此外，Phase 4 導入的 FHIR R4 互通層也依賴統一的術語系統（FHIR 使用 system/identifier 對表示 coding）。

需要決策的核心問題：

1. **術語標準選型**：選擇哪些術語標準作為系統的 canonical 表示？
2. **內部規範化 vs 外部保留**：內部儲存應使用 canonical code 還是保留原始編碼？
3. **映射策略**：不同編碼系統之間的映射如何管理？
4. **版本管理**：術語系統本身有版本（如 ICD-10-CM 每年更新），如何處理？
5. **與既有系統的相容性**：OncoTree 等現有術語如何使用？

## Decision

### 1. 採用「SNOMED CT 為 Canonical Clinical Concept + ICD/LOINC/RxNorm 為領域編碼」策略

| 用途 | Canonical 表示 | 備註 |
|------|---------------|------|
| **臨床概念（診斷/症狀/發現）** | SNOMED CT | 最全面的臨床概念編碼系統，與 FHIR 原生相容 |
| **疾病分類（統計/申報）** | ICD-10-CM | 法規要求，與 SNOMED 保持映射 |
| **檢驗檢查** | LOINC | 實驗室檢驗、影像檢查的標準編碼 |
| **藥物** | RxNorm | 臨床藥物標準編碼（美國市場為主） |

OncoTree 保留為 Oncology 專科的**專科專用編碼**，但會透過映射表關聯到 SNOMED CT。

### 2. 內部儲存採用「Canonical Code + Original Code」雙記錄模式

資料庫 Schema 設計：

```sql
-- 所有臨床編碼欄位遵循以下模式
diagnosis_code      VARCHAR(50)   -- Canonical SNOMED CT code
diagnosis_system    VARCHAR(20)   -- 'SNOMED' (固定)
diagnosis_display   VARCHAR(255)  -- 人類可讀名稱

-- 保留原始編碼（可直接查詢）
original_code       VARCHAR(50)   -- 原始系統的 code（如 OncoTree:THYROID_PTC）
original_system     VARCHAR(20)   -- 原始系統（如 'ONCOTREE', 'ICD10', 'LOINC'）
```

這樣做的好處：
- Canonical code 確保跨專科互通
- Original code 保留原始語義，支援既有查詢邏輯
- 不需要大規模遷移既有資料

### 3. 建立 TerminologyService 管理所有術語操作

`src/backend/platform/terminology/service.py`：

```python
class TerminologyService:
    """統一的術語查詢、驗證、映射服務"""
    
    # 核心功能
    async def normalize(self, code: str, source_system: str) -> NormalizedConcept: ...
    async def map_to(self, code: str, target_system: str) -> list[MappingResult]: ...
    async def validate(self, code: str, system: str) -> ValidationResult: ...
    async def search(self, term: str, system: str | None) -> list[Concept]: ...
    
    # 批量
    async def bulk_lookup(self, codes: list[CodeRef]) -> dict[str, NormalizedConcept]: ...
```

### 4. 映射資料管理

- **靜態映射檔**：以 JSON/YAML 儲存在 `src/backend/platform/terminology/mappings/`，包含 ICD-10 ↔ SNOMED、LOINC ↔ SNOMED 等映射表
- **來源**：使用公開可用的映射資料（NIH UMLS、FHIR terminology server、NLM 提供的映射表）
- **啟動載入**：TerminologyService 啟動時將映射檔載入記憶體（+ Lazy Loading for 大型映射表）
- **版本控制**：映射表檔案納入 Git 版本管理，隨程式碼部署

### 5. 術語版本管理

- 程式碼中直接更新映射檔（依賴系統升級週期）
- 不實作 runtime 動態更新術語版本（Phase 6 選項）
- 每年更新一次映射庫，對應 ICD 和 SNOMED 的發布週期

### 6. 既有系統相容性

- `ClinicalContext.cancer_type` 保留為名（alias 指向 `original_code`），確保向下相容
- Phase 3 的 `variant.py`（HGVS）不受影響
- OncoTree 碼在 `TerminologyService` 中註冊為可辨識的 source_system

## Consequences

### Positive

- **跨專科互通**：Cardiology 的 ICD-10 診斷可對應到 SNOMED，與 Oncology 的 SNOMED 診斷在同一語義空間
- **FHIR 相容**：FHIR R4 的 `CodeableConcept` 使用 `system` + `code` 模式，與本決策一致
- **既有系統不受影響**：OncoTree 和 `cancer_type` 繼續運作
- **擴充性**：新專科只需提供新的術語映射檔即可整合

### Negative

- **映射檔維護負擔**：需要定期更新映射表，依賴外部術語庫的發布
- **Canonical + Original 的雙記錄增加資料庫複雜度**
- **SNOMED CT 授權問題**：部分國家需要付費授權才能使用 SNOMED CT（臺灣已免費授權，中國大陸需確認）

### Risk

| 風險 | 影響 | 緩解措施 |
|------|------|---------|
| SNOMED CT 授權限制 | 中 | 初期先以 ICD-10 為主要 canonical，SNOMED 為選配 |
| 映射不完整導致資訊遺失 | 中 | 支援部分映射 + 「未映射」的明確錯誤處理 |
| 既有 Oncology 資料使用 OncoTree 碼，跨專科查詢時無法對應 | 低 | TerminologyService 同時支援 OncoTree ↔ SNOMED 映射 |

## Related

- Phase 5 Master Plan §7 Clinical Terminology Mapping
- Phase 5 Master Plan §12.3 Batch 2 (Cardiology Terminology Mapping)
- Phase 5 Master Plan §12.5 Batch 4 (TerminologyService 完成)
- ADR-001 (FHIR Canonical Model Strategy) — FHIR 的 CodeableConcept 使用方式
