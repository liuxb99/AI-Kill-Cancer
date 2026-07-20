# 開源專案整合與技術選型

## 1. 目的

本文件定義 AI-Kill-Cancer 在甲狀腺癌個人化基因分析、Three.js 視覺化、癌症變異證據匹配及舊藥再定位方面，應優先評估與整合的開源專案。

核心原則：

- 保留現有 FastAPI、React、PostgreSQL 架構作為產品總控。
- 不直接 Fork 一套大型癌症平台後全面重寫。
- 優先透過 CLI、Docker worker、REST API、資料同步或 npm 套件整合成熟元件。
- 所有資料必須保存來源、版本、license、更新日期與原始識別碼。
- 開源元件輸出的 annotation、interaction 或 graph score 不等於臨床療效證明。
- LLM 只負責解釋、摘要、衝突整理與報告生成，不得自行建立基因—藥物關聯。

---

## 2. 建議總體架構

```text
患者上傳 VCF / CSV / JSON / 檢測報告
        ↓
檔案驗證與 bcftools normalization
        ↓
Ensembl VEP：標準功能註釋
        ↓
OpenCRAVAT：多來源變異註釋與優先排序
        ↓
MyVariant.info：快速補充查詢
        ↓
CIViC：癌症變異與臨床證據
        ↓
DGIdb：藥物—基因互動候選
        ↓
OncoTree：癌種標準化
        ↓
PostgreSQL Evidence Store / Graph Tables
        ↓
React + react-force-graph + Three.js
        ↓
Evidence Card、患者版報告、醫療專業版報告
```

第二階段可加入：

```text
DRKG：舊藥再定位候選生成
ClinicalTrials.gov：臨床試驗匹配
PubMed：支持與反向文獻
PharmCAT：生殖系藥物基因體分析
```

---

## 3. 第一優先整合元件

### 3.1 OpenCRAVAT

用途：

- VCF、HGVS、rsID 等變異輸入。
- 多來源變異註釋。
- 變異優先排序。
- 可安裝不同 annotation modules。
- 產生可供後端處理的結構化結果。

建議整合方式：

```text
FastAPI Analysis Job
        ↓
OpenCRAVAT CLI / local worker
        ↓
標準化 JSON / TSV
        ↓
PostgreSQL
```

不建議直接採用 OpenCRAVAT GUI 作為產品前端。應使用其分析核心，並由 AI-Kill-Cancer 管理病例、權限、資料溯源與視覺化。

優先度：★★★★★

### 3.2 Ensembl VEP

用途：

- GRCh37 / GRCh38 變異註釋。
- Transcript consequence。
- HGVS genomic、coding、protein 表示。
- MANE Select transcript。
- Missense、frameshift、splice 等影響判斷。

建議整合方式：

- 以 Docker worker 或離線 cache 模式執行。
- 固定 VEP、Ensembl cache、reference genome 與 plugin 版本。
- 每次 analysis run 保存完整版本 manifest。

建議流程：

```text
bcftools normalize
        ↓
VEP
        ↓
OpenCRAVAT
```

VEP 負責標準生物學註釋，OpenCRAVAT 負責整合更多癌症與功能性來源。

優先度：★★★★★

### 3.3 CIViC

用途：

- 癌症變異臨床解讀。
- Variant、disease、drug、evidence item、assertion 關聯。
- 預測性、預後性、診斷性證據。
- 文獻與證據等級。
- 支持與衝突證據建模。

應重點參考及整合：

- Evidence model。
- Assertion model。
- Variant normalization。
- Citation 與 provenance 結構。
- Disease、therapy、evidence direction 與 significance 欄位。

建議採用 API 或定期資料同步，不複製整個網站。

優先度：★★★★★

### 3.4 DGIdb

用途：

- Gene → drug interaction 搜尋。
- Drug → target gene 搜尋。
- 彙整不同 drug–gene interaction 來源。
- 建立候選藥物清單。

安全規則：

- 找到 drug–gene interaction 不代表該藥對患者有效。
- DGIdb 結果不可直接當作治療排序。
- 每個 interaction 必須保留原始來源與 interaction type。
- 必須再經 CIViC、文獻、臨床試驗及癌種條件驗證。

建議整合方式：

- DGIdb API。
- Python client。
- 定期同步 TSV。

不建議把完整 Ruby / PostgreSQL 服務直接塞入現有後端。

優先度：★★★★★

### 3.5 react-force-graph / 3d-force-graph

用途：

- React 中建立 Three.js 3D force-directed graph。
- 顯示 variant、gene、protein、pathway、drug、trial、publication、evidence 節點。
- 支援節點選取、縮放、篩選、群組、hover 與相機定位。

建議前端依賴：

```bash
npm install react-force-graph three
```

建議 graph contract：

```json
{
  "nodes": [
    {"id": "BRAF_V600E", "type": "variant"},
    {"id": "BRAF", "type": "gene"},
    {"id": "MAPK", "type": "pathway"},
    {"id": "drug_x", "type": "drug"},
    {"id": "PMID_xxx", "type": "evidence"}
  ],
  "links": [
    {"source": "BRAF_V600E", "target": "BRAF", "relation": "affects"},
    {"source": "BRAF", "target": "MAPK", "relation": "activates"},
    {"source": "drug_x", "target": "BRAF", "relation": "inhibits"}
  ]
}
```

所有節點與連線必須由結構化資料庫產生，不得由 LLM 臨時生成。

優先度：★★★★★

### 3.6 OncoTree

用途：

- 標準化甲狀腺癌類型。
- 建立癌種階層與標準 code。
- 提升 CIViC、cBioPortal、臨床試驗與文獻匹配準確度。

資料庫應保存：

```text
oncotree_code
parent_code
display_name
version
source_id
```

不可只保存自由文字 `thyroid cancer`。

優先度：★★★★☆

---

## 4. 補充與第二優先元件

### 4.1 MyVariant.info

用途：

- 快速 REST 查詢變異。
- 補充 dbSNP、ClinVar、CADD、PolyPhen 等欄位。
- 在本地 worker 尚未完成或需要互相比對時提供快速查詢。

定位：快速查詢層，不是唯一真相來源。

每筆結果仍須保存：

- 原始資料來源。
- 查詢日期。
- 資料版本。
- 原始欄位。
- 使用條件與 license。

優先度：★★★★☆

### 4.2 cBioPortal

用途：

- 參考患者、樣本、研究、分子資料模型。
- 參考 OncoPrint、mutation table、pathway view 與癌症研究匯入格式。
- 透過 API 取得公開癌症研究資料。

不建議直接 Fork，原因：

- 系統規模大，會把開發重心轉成維護 cBioPortal。
- 技術棧與現有 FastAPI 架構差異大。
- 授權與衍生作品義務需單獨審查。

建議做法：

- 使用 REST API。
- 參考資料模型及 UI interaction。
- 使用 Datahub 公開資料。
- 不直接複製整套程式。

優先度：★★★★☆

### 4.3 DRKG

用途：

- Gene、drug、disease、biological process、side effect 等知識圖譜關聯。
- 以 graph embedding 或 link prediction 產生舊藥再定位研究候選。

定位：候選生成器，不是療效證明器。

限制：

- 圖譜及部分範例相對較舊。
- 上游資料來源各自具有使用條件。
- Link prediction score 不等於臨床有效性。
- 候選必須經癌種、變異、文獻、人體資料與安全性重新驗證。

優先度：★★★☆☆

### 4.4 PharmCAT

用途：

- 分析患者生殖系 pharmacogene。
- 推斷 diplotype、phenotype。
- 連接 CPIC、DPWG 與藥品標籤資訊。
- 提示藥物代謝、毒性及基因型相關警示。

必須與腫瘤 DNA 完全分離：

```text
Tumor DNA → 腫瘤驅動、訊號路徑、可能靶點
Germline DNA → 藥物代謝、毒性、遺傳相關資訊
```

不得把腫瘤 somatic variant 當成 PharmCAT 生殖系輸入，也不得把 germline PGx 結果當成抗癌療效證明。

優先度：★★★☆☆，第二階段加入。

---

## 5. 候選藥物證據鏈

任何候選不得只因為 DGIdb、DRKG 或 LLM 找到關聯就顯示為「有效」。

標準證據鏈：

```text
患者變異
  ↓
標準化基因與蛋白改變
  ↓
Oncogenic / functional significance
  ↓
甲狀腺癌 subtype 與 disease context
  ↓
受影響訊號路徑
  ↓
Drug–target interaction
  ↓
同癌種 / 同變異臨床證據
  ↓
其他癌種人體證據
  ↓
前臨床、細胞或計算證據
  ↓
反向證據、失敗試驗、抗藥機制
  ↓
安全性、交互作用、可及性與適用限制
```

候選分級：

1. 已在相同癌種及相同分子條件具有核准或指南證據。
2. 其他癌種已核准，甲狀腺癌具有人體研究證據。
3. 甲狀腺癌有早期臨床或病例證據。
4. 只有前臨床證據。
5. 只有知識圖譜、計算或機制假說。
6. 有明顯反證或生物學方向不符，應降級或排除。

---

## 6. 版本與資料溯源要求

每次 analysis run 必須保存：

```text
analysis_run_id
source_file_hash
genome_build
reference_genome_version
bcftools_version
vep_version
vep_cache_version
opencravat_version
opencravat_module_versions
civic_snapshot_version
dgidb_snapshot_version
oncotree_version
myvariant_query_date
code_commit
started_at
completed_at
status
```

每條 evidence edge 至少保存：

```text
source_system
source_record_id
source_url_or_identifier
source_version
retrieved_at
relation_type
evidence_level
evidence_direction
disease_context
variant_context
publication_id
review_status
```

---

## 7. 授權與合規檢查

整合前必須逐項確認：

- 程式碼 license。
- 資料內容 license。
- 商業使用限制。
- 再散布限制。
- API 使用條款。
- 是否可儲存本地 snapshot。
- 是否必須標示來源或引用。
- 是否包含需要另外授權的上游資料。

特別注意：程式碼是開源，不代表其整合的所有生醫資料都可自由再散布。

專案應建立：

```text
THIRD_PARTY_NOTICES.md
DATA_LICENSES.md
DEPENDENCY_MANIFEST.json
DATA_SOURCE_MANIFEST.json
```

---

## 8. 實作順序

### Stage A：資料契約

先完成：

- Uploaded file schema。
- Variant schema。
- Annotation result schema。
- Disease / OncoTree schema。
- Drug interaction schema。
- Evidence item / assertion schema。
- Visualization graph schema。
- Analysis manifest schema。

### Stage B：最小分析管線

```text
VCF upload
→ validation
→ bcftools normalization
→ VEP worker
→ result import
→ Evidence Card prototype
```

### Stage C：癌症證據與藥物互動

```text
CIViC sync
→ DGIdb sync/API
→ OncoTree normalization
→ patient variant matching
→ candidate list
```

### Stage D：Three.js 視覺化

```text
Graph API
→ react-force-graph
→ 節點篩選
→ Evidence Card 聯動
→ provenance drawer
```

### Stage E：舊藥再定位研究

```text
DRKG candidate generation
→ PubMed supporting/contradicting evidence
→ ClinicalTrials.gov matching
→ ranking with explicit factors
```

### Stage F：生殖系 PGx

```text
germline consent
→ separate VCF pipeline
→ PharmCAT
→ PGx report
```

---

## 9. 明確不採用的做法

- 不完整 Fork cBioPortal 作為主產品。
- 不讓 DRKG embedding 直接產生治療推薦。
- 不讓 LLM 自行搜尋後直接建立基因—藥物資料。
- 不因 DGIdb 有 interaction 就宣稱藥物有效。
- 不混合 tumor somatic DNA 與 germline DNA。
- 不把 OpenCRAVAT 或 VEP annotation 當作臨床結論。
- 不把 graph score、模型信心或相似度稱為療效機率。
- 不在沒有版本 manifest 的情況下產出正式研究報告。

---

## 10. 最終建議組合

第一版正式採用方向：

```text
OpenCRAVAT + Ensembl VEP
        ↓
CIViC + DGIdb + OncoTree
        ↓
FastAPI + PostgreSQL Evidence Store
        ↓
React Force Graph + Three.js
        ↓
Evidence Card + 可追溯研究報告
```

第二版研究擴充：

```text
MyVariant.info + cBioPortal API
DRKG + PubMed + ClinicalTrials.gov
PharmCAT（獨立 germline pipeline）
```

此組合能最大程度保留現有工程成果，同時避免從零重寫成熟的變異註釋、癌症證據、藥物互動及 3D 圖譜能力。