# 模型說明文檔

## 概述

專案使用 PyTorch 實現多個 AI/ML 模型，涵蓋癌症分類、治療推薦、藥物發現、文獻分析等核心功能。

## 模型列表

### 1. CancerClassifier — 癌症分類器

**檔案**: `src/models/cancer_classifier.py`

多任務神經網路，同時預測癌症類型、亞型與分期。

**架構**:
```
Input (20500 維基因表現)
  → Linear(20500→1024) → BN → ReLU → Dropout
  → Linear(1024→512) → BN → ReLU → Dropout
  → Linear(512→256) → BN → ReLU → Dropout
  → Linear(256→128) → BN → ReLU → Dropout
  → 三個輸出頭:
      ├── cancer_type_head: 128 → 3 (肺癌/乳腺癌/大腸癌)
      ├── subtype_head: 128 → 6
      └── stage_head: 128 → 4 (I/II/III/IV期)
```

**配置**:
| 參數 | 預設值 | 說明 |
|------|--------|------|
| input_dim | 20500 | 輸入基因維度 |
| hidden_dims | (1024, 512, 256, 128) | 隱藏層維度 |
| dropout | 0.3 | Dropout 比率 |
| num_cancer_types | 3 | 癌症類型數 |
| num_subtypes | 6 | 亞型數 |
| num_stages | 4 | 分期數 |
| use_batch_norm | true | 是否使用 BatchNorm |

**使用方式**:
```python
from src.models.cancer_classifier import CancerClassifier, CancerClassifierConfig

config = CancerClassifierConfig()
model = CancerClassifier(config)
outputs = model(torch.randn(1, 20500))
# outputs = {"cancer_type": ..., "subtype": ..., "stage": ...}
```

---

### 2. Molecule VAE — 分子生成模型

**檔案**: `src/models/drug_discovery.py`

基於 RNN 的變分自編碼器，用於 SMILES 分子字串的生成與潛在空間表示。

**架構**:
```
Encoder: Embedding → GRU(雙向) → mu/logvar
Decoder: Embedding → GRU → Linear(vocab)
Reparameterization: mu + eps * exp(0.5 * logvar)
```

**配置**:
| 參數 | 預設值 | 說明 |
|------|--------|------|
| vocab_size | 70 | SMILES 字元表大小 |
| char_embed_dim | 128 | 字元嵌入維度 |
| encoder_hidden | 256 | 編碼器隱藏維度 |
| latent_dim | 128 | 潛在空間維度 |
| max_seq_len | 128 | 最大序列長度 |
| kl_weight | 0.1 | KL 散度權重 |

**功能**:
- `generate(num_molecules)` — 從潛在空間採樣生成新分子
- `encode_smiles(smiles)` — 將 SMILES 編碼為潛在向量
- `decode_latent(z)` — 將潛在向量解碼為 SMILES

---

### 3. DTIPredictor — 藥物-靶點交互預測

**檔案**: `src/models/drug_discovery.py`

預測藥物分子與蛋白質靶點之間的結合親和力。

**架構**:
```
Morgan Fingerprint (2048) ─┐
                           ├─→ Concat → MLP → Sigmoid
Target Embedding (128) ───┘
```

**配置**:
| 參數 | 預設值 | 說明 |
|------|--------|------|
| drug_fingerprint_dim | 2048 | 藥物指紋維度 |
| target_embed_dim | 128 | 靶點嵌入維度 |
| hidden_dims | (1024, 512, 256) | 隱藏層維度 |

---

### 4. DrugResponsePredictor — 藥物反應預測

**檔案**: `src/models/drug_response.py`

根據患者基因表現預測對特定藥物的反應機率。

**架構**:
```
Gene Expression (20500) → MLP Encoder →┐
                                       ├─→ Fusion MLP → Sigmoid
Drug ID → Embedding → Projection ──────┘
```

**功能**:
- `predict_response(gene_expr, drug_ids)` — 預測單一藥物反應
- `rank_drugs(gene_expr, drug_id_list)` — 對多種藥物排序

---

### 5. TreatmentRecommender — 治療推薦

**檔案**: `src/models/treatment_recommender.py`

融合基因表現與臨床數據，推薦個人化治療方案。

**架構**:
```
Gene Expression (20500) ─┐
                          ├─→ Fusion Encoder → Response Head → Sigmoid
Clinical Features (20) ──┘
```

內建 `CANCER_DRUG_DB` 知識庫，涵蓋肺癌、乳腺癌、大腸癌的化療、標靶與免疫治療方案。

**使用方式**:
```python
from src.models.treatment_recommender import TreatmentRecommender

model = TreatmentRecommender()
recommendations = model.recommend(gene_expr, clinical, "肺癌")
# 返回排序後的藥物建議清單
```

---

### 6. LiteratureAnalyzer — 文獻分析

**檔案**: `src/models/literature_analyzer.py`

端到端的文獻分析管線，整合 PubMed 搜尋、實體識別、摘要生成與趨勢分析。

**功能**:

| 方法 | 說明 |
|------|------|
| `analyze_from_pubmed(query)` | 從 PubMed 搜尋並分析文獻 |
| `trend_analysis(articles)` | 生成趨勢報告（癌種/藥物/基因頻率） |
| `analyze_cancer_type(cancer)` | 針對特定癌種進行文獻分析 |
| `extract_entities(text)` | NER 實體提取（癌症/藥物/基因/治療） |
| `summarize_abstract(text)` | 摘要生成 |

**支援模型**:
- NER: `dmis-lab/biobert-v1.1`
- 摘要: `philschmid/bart-large-cnn-samsum`
- PubMedBERT: `microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext`

---

### 7. DrugDiscoveryPipeline — 藥物發現管線

**檔案**: `src/models/drug_discovery.py`

整合 MoleculeVAE + DTIPredictor 的端到端藥物發現流程。

**功能**:
- `discover_candidate_drugs(target_emb, num_candidates, top_k)` — 生成新分子並篩選
- `screen_virtual_library(smiles_library, target_emb, top_k)` — 虛擬篩選

---

### 8. Predictor — 推論封裝

**檔案**: `src/models/predict.py`

封裝 CancerClassifier 的推論邏輯，載入 checkpoint 後可直接用於預測。

```python
from src.models.predict import Predictor

predictor = Predictor("checkpoints/best_model.pt")
result = predictor.predict(gene_expression_array)
# result = {
#   "samples": {
#     "cancer_type": {"label": 0, "name": "肺癌", "probability": 0.92, "all_probs": {...}},
#     "subtype": {"label": 0, "name": "肺腺癌", "probability": 0.87},
#     "stage": {"label": 1, "name": "II期", "probability": 0.73},
#   }
# }
```

## 訓練流程

**檔案**: `src/models/train.py`

提供完整的訓練框架：

```python
from src.models.train import Trainer, TrainingConfig, GeneExpressionDataset

dataset = GeneExpressionDataset(X, y_cancer, y_subtype, y_stage)
trainer = Trainer(model, config)
history = trainer.fit(train_loader, val_loader)
```

**訓練配置**:

| 參數 | 預設值 | 說明 |
|------|--------|------|
| batch_size | 64 | 批次大小 |
| learning_rate | 1e-3 | 學習率 |
| num_epochs | 100 | 最大訓練輪數 |
| early_stop_patience | 10 | 早停耐心值 |
| device | cuda/cpu | 運算設備 |
| loss_weights | {cancer: 1, subtype: 1, stage: 0.5} | 多任務損失權重 |
