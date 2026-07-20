# 甲狀腺癌個人化基因分析與舊藥再定位平台規劃

## 1. 專案新定位

AI-Kill-Cancer 的主線應由「泛癌症預測展示網站」調整為：

> **甲狀腺癌患者個人化基因分析、分子機制視覺化、既有藥物再定位與可追溯證據報告平台。**

目標使用者是已確診甲狀腺癌、並已取得腫瘤 DNA 或相關分子檢測結果的患者、研究人員與醫療專業人員。

本平台不負責判斷使用者是否罹癌，也不自動開立處方。系統負責把患者的檢測資料轉換為：

1. 標準化基因變異資料。
2. 可互動的染色體、基因、蛋白質與訊號路徑視覺化。
3. 與患者變異相關的既有藥物及舊藥再定位候選。
4. 支持證據、反向證據、限制與不確定性。
5. 可供患者與醫師或分子腫瘤委員會討論的研究報告。

核心問題不是「患者有沒有癌症」，而是：

```text
患者的腫瘤有哪些重要基因變異？
        ↓
變異影響哪些蛋白質、訊號路徑與癌症機制？
        ↓
哪些已核准藥物或既有藥物可能干預這些機制？
        ↓
支持與反對這個候選的證據是什麼？
        ↓
證據強度、適用條件、風險與不確定性有多高？
```

---

## 2. 醫療與產品邊界

### 2.1 平台可以做的事

- 解讀已存在的腫瘤分子檢測結果。
- 將變異標準化並連接基因、蛋白質、路徑、疾病、藥物及研究證據。
- 搜尋已核准藥物、其他癌種藥物與舊藥再定位候選。
- 建立支持證據與反向證據並列的證據鏈。
- 產生患者易懂版與醫療專業版研究報告。
- 顯示可討論的臨床試驗或進一步檢測方向。

### 2.2 平台禁止做的事

- 自動診斷癌症。
- 自動決定患者應服用哪一種藥物。
- 提供藥物劑量、停藥、換藥或合併用藥指令。
- 將細胞、動物或電腦模擬結果宣稱為人體療效。
- 將意義未明變異（VUS）直接視為可用藥變異。
- 將消費級祖源 DNA 資料當作腫瘤基因檢測。
- 將研究候選包裝成已證實療法。

所有輸出必須清楚聲明：

> 本平台輸出是研究型決策支援資訊，不構成診斷、處方或治療建議。任何用藥決策必須由合格醫師結合病理、分期、既往治療、器官功能、共病及完整臨床資料判斷。

---

## 3. 目標使用流程

### 3.1 建立患者案例

患者先建立病例並輸入必要臨床背景：

- 甲狀腺癌類型：
  - 乳突型甲狀腺癌（PTC）
  - 濾泡型甲狀腺癌（FTC）
  - 髓質型甲狀腺癌（MTC）
  - Hurthle cell carcinoma
  - 低分化甲狀腺癌（PDTC）
  - 未分化甲狀腺癌（ATC）
- 病理分期與診斷日期。
- 手術與放射碘治療歷史。
- 是否屬於放射碘難治。
- 局部復發或遠端轉移位置。
- 目前及過去用藥。
- 重要共病與器官功能資訊。
- 檢體來源與採樣日期。

相同變異在不同甲狀腺癌類型、病程與治療階段可能具有不同意義，因此上述資料不可由系統自行猜測。

### 3.2 上傳 DNA 與分子檢測資料

MVP 優先支援：

- VCF / VCF.GZ。
- 醫院或檢測公司的 CSV、TSV、JSON 匯出。
- 由合格實驗室產生的癌症基因 panel 結果。
- PDF 檢測報告，僅作資料擷取與人工核對，不應直接成為唯一推論依據。

後續階段再支援：

- FASTQ。
- BAM / CRAM。
- RNA-seq。
- Copy-number 與 fusion 原始分析檔。

MVP 不應直接從 FASTQ 開始，因為完整流程還需要品質控制、序列比對、變異檢出、污染評估與驗證。

### 3.3 必須保存的檢測 Metadata

- 檢測實驗室。
- 檢測 panel 或 assay 名稱與版本。
- Genome build：GRCh37 或 GRCh38。
- 檢體類型與部位。
- 腫瘤純度。
- 測序深度與最低可偵測 VAF。
- 檢測日期。
- Somatic、germline 或 unknown origin。
- 是否有 matched normal。
- 報告的限制及未覆蓋區域。

---

## 4. DNA 分析與標準化引擎

資料處理主流程：

```text
原始檔案
  ↓
格式與完整性驗證
  ↓
Genome build 辨識或轉換
  ↓
Variant normalization
  ↓
HGVS 與轉錄本註釋
  ↓
Somatic / germline / unknown 分類
  ↓
腫瘤驅動與功能性評估
  ↓
路徑與疾病關聯分析
  ↓
藥物及證據匹配
  ↓
可追溯分析報告
```

### 4.1 標準化變異資料

每個變異至少應轉為：

```json
{
  "gene": "BRAF",
  "hgvs_c": "c.1799T>A",
  "hgvs_p": "p.Val600Glu",
  "variant_type": "SNV",
  "chromosome": "7",
  "position": 140753336,
  "reference": "A",
  "alternate": "T",
  "genome_build": "GRCh38",
  "transcript": "NM_004333.6",
  "vaf": 0.32,
  "origin": "somatic",
  "clinical_significance": "oncogenic",
  "cancer_context": "papillary thyroid carcinoma",
  "source_record_id": "...",
  "annotation_version": "..."
}
```

### 4.2 需要支援的變異類型

- SNV。
- Insertion / deletion。
- Copy-number amplification / deletion。
- Gene fusion，例如 RET、NTRK、ALK fusion。
- TERT promoter 變異。
- Structural variant。
- MSI / TMB，僅在原始報告確實提供並可追溯時顯示。
- RNA expression，僅在存在 RNA 資料時分析。

### 4.3 甲狀腺癌首批核心基因

MVP 知識庫優先涵蓋：

- BRAF
- NRAS
- HRAS
- KRAS
- RET
- NTRK1
- NTRK2
- NTRK3
- ALK
- TERT
- EIF1AX
- TP53
- PTEN
- PIK3CA
- DICER1
- PPARG

知識庫必須可擴充，不能把基因與藥物關聯硬編碼在 API route 或前端元件中。

---

## 5. Three.js 互動視覺化

Three.js 的目的不是僅展示 DNA 雙螺旋動畫，而是提供真正的資料探索介面。

### 5.1 染色體與基因組全景

- 顯示 23 對染色體。
- 將患者變異標在實際染色體位置。
- 支援旋轉、縮放、搜尋與篩選。
- 點擊染色體可展開基因。
- 點擊基因可顯示變異、VAF、來源、臨床意義與證據等級。
- 篩選 somatic、germline、unknown。
- 篩選 driver、likely driver、passenger、VUS。
- 不同顏色代表不同證據層級，而不是由 LLM 自由決定顏色語義。

### 5.2 基因—蛋白質—路徑網路

以 3D graph 顯示：

```text
患者變異
  ↕
基因
  ↕
蛋白質
  ↕
訊號路徑
  ↕
癌症表型
```

例如：

```text
BRAF V600E
   ↓
BRAF 持續活化
   ↓
MEK
   ↓
ERK
   ↓
MAPK 訊號增加
   ↓
細胞增殖與分化改變
```

節點與連線只能由結構化知識庫產生。LLM 可以解釋連線，但不可自行創造連線。

### 5.3 藥物—靶點—證據網路

顯示：

```text
患者變異
  ↕
可干預靶點
  ↕
已核准藥物
  ↕
其他癌種藥物
  ↕
舊藥再定位候選
  ↕
文獻與臨床試驗
```

- 節點距離代表關聯程度。
- 連線粗細代表證據強度。
- 節點標籤必須區分 approved、off-label、trial、preclinical、hypothesis。
- 點擊任何藥物後，在側邊顯示完整證據卡。

### 5.4 證據時間線

依序顯示：

```text
機制研究
  ↓
細胞研究
  ↓
動物研究
  ↓
病例報告
  ↓
臨床試驗
  ↓
指南或監管核准
```

患者必須能清楚看出候選藥物目前停留在哪一個證據層級。

---

## 6. 既有藥物與舊藥再定位引擎

### 6.1 完整證據鏈

候選不能只由「基因名稱對藥物名稱」產生。系統必須建立：

```text
患者變異
  ↓
蛋白質功能改變
  ↓
訊號路徑活化或失活
  ↓
疾病機制
  ↓
可干預節點
  ↓
藥物作用機制
  ↓
甲狀腺癌證據
  ↓
其他癌種證據
  ↓
人體安全與限制
  ↓
候選證據等級
```

### 6.2 候選藥物分類

#### A. 已有甲狀腺癌或分子條件直接證據

屬於已知分子配對治療或高證據候選，不能與實驗性舊藥再定位混在同一層級。

#### B. 其他癌種已有核准、甲狀腺癌仍在研究

必須明確標示：

- Off-label。
- 非甲狀腺癌核准。
- 證據來自哪一癌種。
- 是否為相同變異、相同路徑或僅相似機制。
- 是否存在甲狀腺癌臨床試驗。

#### C. 真正的舊藥再定位候選

候選可來自：

- Drug–target interaction。
- Pathway inhibition。
- Gene-expression signature reversal。
- Network pharmacology。
- 類器官或細胞藥敏資料。
- 文獻與臨床試驗資料。

此類候選只能標示為「研究候選」或「機制假說」，不得標示為推薦治療。

### 6.3 候選排序原則

排序必須由可檢查的規則或模型產生，而不是由 LLM 主觀決定。初版可採：

```text
候選分數
=
分子匹配度
× 癌種匹配度
× 靶點與路徑匹配度
× 臨床證據權重
× 研究一致性
× 人體資料權重
× 安全性與適用性修正
```

建議初始研究權重：

- 40%：分子與機制匹配。
- 25%：人體臨床證據。
- 15%：甲狀腺癌專一性。
- 10%：藥物可取得性與研究可行性。
- 10%：安全、交互作用與患者條件修正。

這些權重屬研究設定，必須版本化，並禁止宣稱已獲臨床驗證。

---

## 7. 證據與「證明原因」系統

每一個候選藥物都必須產生完整 Evidence Card。

### 7.1 Evidence Card 必要欄位

- 候選藥物與既有適應症。
- 患者變異與檢測來源。
- 變異對蛋白質的影響。
- 涉及的訊號路徑與疾病機制。
- 藥物作用靶點與機制。
- 與患者變異的連接理由。
- 甲狀腺癌直接證據。
- 其他癌種間接證據。
- 人體、動物、細胞或計算證據類別。
- 支持研究。
- 反向或無效研究。
- 已知抗藥機制。
- 樣本數、研究設計與主要限制。
- 藥物交互作用與重要安全警示。
- 證據等級。
- 系統信心與不確定性。
- 最後更新日期與資料來源。

### 7.2 支持與反證必須並列

「證明原因」不等於只搜尋支持資料。系統必須主動尋找：

- 未達主要終點的試驗。
- 相同藥物在甲狀腺癌中無效或效果有限的研究。
- 只在細胞或動物中成立的情況。
- 患者癌種、分期或變異不一致。
- 旁觀者變異的可能性。
- 已知先天或後天抗藥機制。
- 因毒性而無法達到有效濃度的問題。

### 7.3 建議證據等級

- Level 1：同癌種、同分子條件，已有監管核准或高品質指南支持。
- Level 2：同癌種、同分子條件，有人體臨床試驗支持。
- Level 3：其他癌種、相同分子條件，有人體證據。
- Level 4：同路徑或相關機制的前臨床證據。
- Level 5：計算推論、網路藥理或弱機制假說。

任何 Level 4–5 候選都必須突出標示「尚無足夠人體療效證據」。

---

## 8. LLM 的正確角色

LLM 適合：

- 將結構化證據轉換成患者可理解文字。
- 產生專業醫師版研究摘要。
- 整理研究間的一致與衝突。
- 提醒缺少的檢測資料。
- 對每個結論附上來源 ID。

LLM 禁止：

- 自行建立不存在的基因—藥物關聯。
- 自行產生藥物劑量。
- 自行決定換藥或停藥。
- 把 VUS 當作 actionable mutation。
- 省略反向證據。
- 使用無法回溯來源的內容作為結論。

正確架構：

```text
結構化知識庫與規則引擎
        ↓
候選生成與證據分級
        ↓
LLM 僅負責解釋、摘要與衝突整理
        ↓
所有句子連回證據來源
```

---

## 9. 資料與知識庫架構

核心資料表至少包括：

```text
patients
cases
specimens
sequencing_tests
uploaded_files
variants
genes
transcripts
proteins
pathways
diseases
drugs
drug_targets
drug_indications
drug_interactions
variant_disease_evidence
variant_drug_evidence
pathway_drug_evidence
clinical_trials
publications
evidence_assertions
analysis_runs
candidate_rankings
reports
consents
audit_logs
```

每條證據至少保存：

- 來源資料庫。
- 來源 ID、PMID、DOI、試驗編號或監管文件 ID。
- 原始 URL。
- 抓取與更新日期。
- 證據種類。
- 癌種與患者族群。
- 樣本數。
- 研究設計。
- 變異、靶點、藥物與療效指標。
- 支持或反向證據。
- 研究限制。
- 資料授權。
- 自動擷取或人工審核狀態。

### 9.1 建議儲存配置

- PostgreSQL：患者資料、結構化證據、分析紀錄。
- Object Storage：VCF、PDF、原始報告與分析產物。
- Vector store：文獻語義搜尋，但不得作為唯一真實來源。
- Graph tables 或圖資料庫：基因—蛋白—路徑—藥物關聯。
- SQLite：僅用於本地 MVP 或單機開發。

---

## 10. 前端資訊架構

建議主選單：

```text
Patient Case
DNA Upload
Genome Viewer
Variant Analysis
Pathway Explorer
Drug Repurposing
Evidence Graph
Clinical Trials
Research Report
Privacy & Consent
System Status
```

首頁應顯示：

- 患者案例摘要。
- 檢測資料完整度。
- 重要 driver 與 actionable variants。
- 變異證據等級。
- 候選研究方向。
- 缺少或建議補充的檢測。
- 可供醫師討論的問題清單。

不應以「立即預測」或「治療推薦」作為首頁主要操作。

---

## 11. 報告輸出

系統應同時產生兩種報告。

### 11.1 患者易懂版

- 這次檢測發現了什麼。
- 哪些變異可能較重要。
- 這些變異可能影響哪些癌症機制。
- 有哪些已知或研究中的藥物方向。
- 證據目前有多強。
- 哪些問題需要向醫師詢問。
- 重要限制及免責聲明。

### 11.2 醫療專業版

- 原始變異與標準化結果。
- Genome build、transcript 與 HGVS。
- VAF、depth、tumor purity 與 assay 限制。
- 分子機制與路徑。
- 可操作性分類。
- 候選藥物、核准狀態與適應症。
- 支持與反向證據。
- 證據來源及版本。
- 臨床試驗。
- 藥物交互作用與安全限制。
- 未確定事項。
- 分析軟體、資料庫及模型版本。

---

## 12. MVP 範圍

第一版只做：

```text
甲狀腺癌患者案例
+
VCF / CSV / JSON 上傳
+
重要甲狀腺癌基因變異標準化
+
Three.js 染色體與路徑網路
+
藥物與靶點資料匹配
+
支持與反向證據
+
臨床試驗關聯
+
患者版與醫師版研究報告
```

MVP 暫不做：

- FASTQ 完整 variant calling。
- 自動處方或劑量。
- 自動多藥組合。
- 全癌種支援。
- 自動預測生存期。
- 宣稱候選藥物已證實有效。

---

## 13. 分階段開發路線

### Phase 0：完成現有推論與安全基礎

- 真實 DB readiness。
- 固定 feature schema。
- Versioned label manifest。
- Checkpoint 與 manifest 相容性。
- 模型 hash、版本與 loaded_at。
- Production 仍保留醫療免責聲明。
- Demo、research、production 嚴格隔離。

### Phase 1：產品重新定位

- 更新 README、產品文案與 API 名稱。
- 移除或降級泛癌症「預測」和「治療推薦」用語。
- 建立甲狀腺癌病例與檢體資料模型。
- 加入 consent、privacy、audit log 設計。

### Phase 2：DNA 上傳與標準化

- VCF parser。
- CSV / TSV / JSON adapters。
- Genome build 處理。
- Variant normalization。
- HGVS 與 transcript annotation。
- Somatic / germline / unknown 標記。
- 檢測品質與完整性報告。

### Phase 3：甲狀腺癌知識庫

- 建立首批核心基因、變異與路徑。
- 建立藥物、靶點、適應症與核准狀態。
- 建立證據來源、證據分級與更新流程。
- 支援支持證據與反向證據。

### Phase 4：Three.js 可視化

- 染色體全景。
- 患者變異節點。
- 基因—蛋白—路徑網路。
- Drug–target graph。
- Evidence timeline。
- 點擊節點聯動 Evidence Card。

### Phase 5：藥物再定位

- 可檢查的候選生成規則。
- 候選分數與版本化權重。
- 臨床試驗匹配。
- 反向證據與抗藥機制搜尋。
- 安全與藥物交互作用警示。

### Phase 6：報告與專業工作流

- 患者版報告。
- 醫師版報告。
- 分子腫瘤委員會討論摘要。
- 證據來源與版本快照。
- 分析重跑與差異比較。

---

## 14. 下一個實作任務

現有 P0 基礎修正完成並經 Git 審查後，下一輪應執行：

> **Phase 1：甲狀腺癌 Precision Oncology 產品重構。**

驗收條件：

1. README 與主要頁面不再將產品描述為泛癌症自動預測工具。
2. 新增 patient case、specimen、sequencing test 與 uploaded file 的領域模型設計。
3. 建立 VCF / CSV 上傳 API 契約，但先不虛構分析結果。
4. 建立 thyroid cancer variant schema 與首批核心基因資料格式。
5. 建立 Three.js visualization data contract。
6. 建立 Drug Candidate 與 Evidence Card schema。
7. 所有候選結論均要求來源、證據等級、限制與反向證據欄位。
8. 不得以 mock 或 synthetic 結果宣稱完成真實基因分析。
9. 文件、測試及 API schema 同步更新。
10. 完成後推 Git，再進行程式碼與資料契約審查。

---

## 15. 成功標準

專案成功不是「畫出漂亮的 DNA」或「列出很多藥名」，而是：

- 每一個患者變異都能回到原始檢測記錄。
- 每一條基因—路徑—藥物連線都有可追溯來源。
- 每一個候選同時顯示支持與反向證據。
- 使用者能分辨已核准、off-label、臨床試驗、前臨床與純假說。
- LLM 不掌握事實來源，只負責解釋已驗證資料。
- 報告可以交給醫師討論，但不冒充醫師處方。
- 分析結果可重跑、可比較、可審計、可版本化。
