# 使用者指南

## 系統需求

- Python 3.11+
- Node.js 20+
- PostgreSQL 15+
- Docker (選擇性)
- CUDA 相容 GPU (選擇性，用於模型訓練)

## 安裝

### 1. 克隆專案

```bash
git clone <repository-url>
cd AI_Kill_Cancer
```

### 2. Python 依賴

```bash
# 基礎依賴（後端）
pip install -r requirements-ai.txt

# 或使用 Poetry
poetry install
```

### 3. 資料庫設定

```bash
# 初始化 PostgreSQL 資料庫
python scripts/init_db.py --create-db

# 建立表格
python scripts/init_db.py --create-tables
```

### 4. 啟動 API 伺服器

```bash
uvicorn src.backend.main:app --reload --host 0.0.0.0 --port 8000
```

啟動後瀏覽 `http://localhost:8000/docs` 查看 Swagger API 文檔。

## 數據下載

### 從 TCGA 下載

```bash
# 下載乳癌基因表現數據
python scripts/fetch_data.py --source tcga --cancer-type BRCA

# 下載肺腺癌數據
python scripts/fetch_data.py --source tcga --cancer-type LUAD
```

### 從 cBioPortal 下載

```bash
python scripts/fetch_data.py --source cbioportal --study acc_2019
```

### 從 GEO 下載

```bash
python scripts/fetch_data.py --source geo --dataset GSE10072
```

### 從 UCSC Xena 下載

```bash
python scripts/fetch_data.py --source xena --study TCGA.BRCA.sampleMap
```

### 從 DepMap 下載

```bash
python scripts/fetch_data.py --source depmap --dataset 24Q4
```

> 所有下載數據預設存放於 `data/raw/` 目錄。

## 模型推論

### 使用 Predictor

```python
from src.models.predict import Predictor
import numpy as np

# 載入訓練好的模型
predictor = Predictor("checkpoints/best_model.pt")

# 準備基因表現數據 (20500 維)
gene_expr = np.random.randn(20500)

# 預測
result = predictor.predict(gene_expr)
print(result["cancer_type"]["name"])   # 預測癌症類型
print(result["stage"]["name"])         # 預測分期
```

### 治療推薦

```python
from src.models.treatment_recommender import (
    TreatmentRecommender, lookup_drug_knowledge, list_available_cancers
)

# 查看支援的癌症類型
print(list_available_cancers())  # ["肺癌", "乳腺癌", "大腸癌"]

# 查詢特定癌症的已知藥物
drugs = lookup_drug_knowledge("肺癌", category="標靶")
for d in drugs:
    print(f"{d['name']}: {d['indication']} (response: {d['avg_response']})")

# 使用模型推薦
model = TreatmentRecommender()
recommendations = model.recommend_from_numpy(gene_expr, clinical, "肺癌")
```

### 文獻分析

```python
from src.models.literature_analyzer import LiteratureAnalyzer

analyzer = LiteratureAnalyzer()
articles = analyzer.analyze_from_pubmed("lung cancer immunotherapy", max_results=10)
trend = analyzer.trend_analysis(articles)
print(trend.cancer_type_freq)
print(trend.key_findings)
```

### 藥物發現

```python
from src.models.drug_discovery import DrugDiscoveryPipeline

pipeline = DrugDiscoveryPipeline()
candidates = pipeline.discover_candidate_drugs(
    target_emb=target_embedding,
    num_candidates=100,
    top_k=10,
)
for c in candidates:
    print(f"Rank {c['rank']}: {c['smiles']} (prob: {c['interaction_probability']})")
```

## 訓練模型

```python
from src.models.cancer_classifier import CancerClassifier, CancerClassifierConfig
from src.models.train import Trainer, TrainingConfig, GeneExpressionDataset
from torch.utils.data import DataLoader

# 準備數據
dataset = GeneExpressionDataset(X_train, y_cancer, y_subtype, y_stage)
loader = DataLoader(dataset, batch_size=64, shuffle=True)

# 建立模型與訓練器
model = CancerClassifier(CancerClassifierConfig())
trainer = Trainer(model, TrainingConfig())

# 開始訓練
history = trainer.fit(train_loader, val_loader)
```

## Docker 部署

```bash
# 使用 Docker Compose 啟動完整環境
docker compose -f docker/docker-compose.yml up -d
```

## API 呼叫範例

### curl

```bash
curl -X POST http://localhost:8000/api/v1/predict \
  -H "Content-Type: application/json" \
  -d '{"age": 55, "gender": "M", "biomarkers": {"CEA": 5.2}, "smoking_history": "current"}'

curl -X POST http://localhost:8000/api/v1/recommend \
  -H "Content-Type: application/json" \
  -d '{"cancer_type": "Breast Cancer", "stage": "2", "biomarkers": {"HER2": 0.8}, "age": 45}'
```

### Python

```python
import requests

api = "http://localhost:8000/api/v1"

# 健康檢查
print(requests.get(f"{api}/health").json())

# 預測
resp = requests.post(f"{api}/predict", json={
    "age": 60, "gender": "M",
    "biomarkers": {"CEA": 8.5, "CYFRA21-1": 12.0},
    "smoking_history": "current",
})
print(resp.json())
```
