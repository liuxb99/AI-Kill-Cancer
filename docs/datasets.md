# 可用癌症數據集清單與取得方式

## 1. TCGA (The Cancer Genome Atlas)

| 屬性 | 說明 |
|------|------|
| **網址** | https://portal.gdc.cancer.gov/ |
| **資料類型** | 基因體、轉錄體、表觀基因體、蛋白質體 |
| **癌症類型** | 33 種癌症，包含 11,000+ 樣本 |
| **存取方式** | GDC API、gdc-client CLI、UCSC Xena Browser |
| **Python 套件** | `gdc-client`, `TCGA-Assembler` (R), `cBioPortal API` |
| **注意事項** | 需要 dbGaP 授權存取受控資料；開放資料可免費下載 |

### 常用 TCGA 數據集 ID
- **TCGA-BRCA**: 乳癌 (~1,098 樣本)
- **TCGA-LUAD**: 肺腺癌 (~585 樣本)
- **TCGA-LUSC**: 肺鱗癌 (~504 樣本)
- **TCGA-COAD**: 大腸癌 (~480 樣本)
- **TCGA-GBM**: 多形性膠質母細胞瘤 (~617 樣本)
- **TCGA-OV**: 卵巢癌 (~606 樣本)

---

## 2. GEO (Gene Expression Omnibus)

| 屬性 | 說明 |
|------|------|
| **網址** | https://www.ncbi.nlm.nih.gov/geo/ |
| **資料類型** | 基因表現微陣列、RNA-seq、ChIP-seq、甲基化 |
| **癌症類型** | 廣泛，含癌症與正常組織 |
| **存取方式** | GEO API、`GEOquery` (R/Bioconductor) |
| **Python 套件** | `GEOparse` (Python) |
| **注意事項** | 公開數據，無需授權；但需要仔細篩選樣本品質 |

### 代表性 GEO 數據集
- **GSE10072**: 肺癌 vs 正常組織
- **GSE2034**: 乳癌預後基因標誌
- **GSE17536**: 大腸癌預後

---

## 3. ICGC (International Cancer Genome Consortium)

| 屬性 | 說明 |
|------|------|
| **網址** | https://dcc.icgc.org/ |
| **資料類型** | 基因體突變、拷貝數變異、基因表現、甲基化 |
| **癌症類型** | 25 種癌症，約 20,000 樣本 |
| **存取方式** | ICGC Data Portal REST API、`icgc-get` CLI |
| **Python 套件** | `icgc` (官方 Python client) |
| **注意事項** | 部分數據需要授權；與 TCGA 有部分重疊 |

---

## 4. CPTAC (Clinical Proteomic Tumor Analysis Consortium)

| 屬性 | 說明 |
|------|------|
| **網址** | https://cptac-data-portal.georgetown.edu/ |
| **資料類型** | 蛋白質體、磷酸化蛋白質體、基因體 |
| **癌症類型** | 乳癌、卵巢癌、大腸癌等，約 1,000+ 樣本 |
| **存取方式** | CPTAC Portal、LinkedOmics |
| **注意事項** | 蛋白質體數據是目前最全面的公開資源之一 |

---

## 5. cBioPortal

| 屬性 | 說明 |
|------|------|
| **網址** | https://www.cbioportal.org/ |
| **資料類型** | 整合性基因體數據（突變、CNV、表現、存活） |
| **癌症類型** | 200+ 研究，30,000+ 樣本 |
| **存取方式** | REST API、Python 套件 `cbioportal-api` |
| **Python 套件** | `cbioportal` (pypi)、`cbioportal-api-client` |
| **注意事項** | 完全公開，提供網頁視覺化與 API 查詢 |

---

## 6. TCGA Pan-Cancer Atlas (via UCSC Xena)

| 屬性 | 說明 |
|------|------|
| **網址** | https://xena.ucsc.edu/ |
| **資料類型** | 已處理的 TCGA 數據（正規化後） |
| **存取方式** | UCSC Xena Hub API、Python `ucsc-xena-client` |
| **注意事項** | 數據已標準化處理，適合直接分析使用 |

---

## 7. GDSC (Genomics of Drug Sensitivity in Cancer)

| 屬性 | 說明 |
|------|------|
| **網址** | https://www.cancerrxgene.org/ |
| **資料類型** | 藥物敏感性 + 基因體數據 |
| **癌症類型** | ~1,000 細胞株 |
| **存取方式** | 網頁下載、REST API |
| **注意事項** | 適合藥物反應預測模型訓練 |

---

## 8. DepMap (Cancer Dependency Map)

| 屬性 | 說明 |
|------|------|
| **網址** | https://depmap.org/portal/ |
| **資料類型** | CRISPR 篩選、RNAi、基因表現、藥物敏感性 |
| **癌症類型** | ~1,800 細胞株 |
| **存取方式** | API、CSV 下載、Python `depmap` |
| **注意事項** | 最全面的癌症依賴性數據庫 |

---

## 9. TCGA 數據下載快速參考 (GDC API)

```python
# 使用 GDC API 查詢 TCGA-BRCA 的 RNA-seq 數據
import requests

url = "https://api.gdc.cancer.gov/files"
params = {
    "filters": {
        "op": "and",
        "content": [
            {"op": "in", "content": {"field": "cases.project.project_id", "value": ["TCGA-BRCA"]}},
            {"op": "in", "content": {"field": "files.data_type", "value": ["Gene Expression Quantification"]}}
        ]
    },
    "format": "JSON",
    "size": 100
}
response = requests.post(url, json=params)
```

---

## 10. 資料使用摘要

| 數據源 | 開放程度 | 適合用途 | 下載方式 |
|--------|---------|---------|---------|
| TCGA | 部分開放 | 基因體分析、分類模型 | GDC API / gdc-client |
| GEO | 開放 | 驗證數據集、比較分析 | GEOparse |
| ICGC | 部分授權 | 跨國癌症比較 | ICGC API |
| CPTAC | 開放 | 蛋白質體標誌物 | CPTAC Portal |
| cBioPortal | 完全開放 | 快速原型驗證 | REST API |
| UCSC Xena | 完全開放 | 已處理標準化數據 | Python client |
| GDSC | 開放 | 藥物反應預測 | 網站下載 |
| DepMap | 開放 | 基因依賴性分析 | depmap Python |

## 建議優先順序

1. **TCGA (via UCSC Xena)** — 規模最大、標準化程度最高，優先使用
2. **cBioPortal API** — 快速查詢與驗證，適合原型開發
3. **GEO** — 外部驗證與跨數據集比較
4. **CPTAC** — 蛋白質體層面補充
5. **GDSC / DepMap** — 藥物反應預測的輔助數據
