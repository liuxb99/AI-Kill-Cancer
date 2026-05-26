# 開發者指南

## 開發環境建置

### 前置需求

- Python 3.11+
- Node.js 20+
- PostgreSQL 15+
- Git
- CUDA Toolkit 11.8+ (選擇性)

### 環境設定

```bash
# 克隆專案
git clone <repository-url>
cd AI_Kill_Cancer

# Python 虛擬環境
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# 安裝依賴
pip install -r requirements-ai.txt

# 安裝開發依賴（測試、格式化等）
pip install pytest pytest-asyncio black ruff mypy
```

## 專案慣例

### 程式碼風格

- **Python**: 遵循 PEP 8，使用 `ruff` 進行 lint，`black` 進行格式化
- **命名**:
  - 類別: `CamelCase`
  - 函數/方法: `snake_case`
  - 常數: `UPPER_SNAKE_CASE`
  - 私有成員: `_leading_underscore`
- **型別註解**: 所有公開函數必須包含型別提示
- **字串**: 使用雙引號 `"` (PEP 8 建議無關，但專案統一使用雙引號)

### 提交訊息格式

```
<type>(<scope>): <subject>

<body>
```

- **type**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`
- **scope**: `backend`, `models`, `scripts`, `docs`, `docker`
- **subject**: 中文或英文，不超過 50 字元

### 分支策略

| 分支 | 用途 |
|------|------|
| main | 穩定版本 |
| develop | 開發主線 |
| feature/* | 功能開發 |
| fix/* | 錯誤修復 |
| docs/* | 文檔更新 |

## 模組架構

### 後端 (`src/backend/`)

```
backend/
├── main.py              # FastAPI 應用建立與啟動
├── config.py            # 環境配置
├── api/
│   ├── __init__.py
│   └── routes.py        # API 路由定義
├── models/
│   ├── __init__.py      # Pydantic 請求/回應模型
└── database/
    ├── __init__.py
    ├── models.py        # SQLAlchemy ORM 模型
    ├── crud.py          # 資料庫 CRUD 操作
    └── etl.py           # ETL 管線
```

### AI 模型 (`src/models/`)

```
models/
├── cancer_classifier.py    # 多任務癌症分類器
├── drug_discovery.py       # MoleculeVAE + DTIPredictor
├── drug_response.py        # 藥物反應預測
├── treatment_recommender.py # 治療推薦
├── literature_analyzer.py  # 文獻分析 (NER + 摘要 + 趨勢)
├── pubmed_fetcher.py       # PubMed API 客戶端
├── molecule_utils.py       # RDKit 分子工具
├── predict.py              # 推論封裝
└── train.py                # 訓練框架
```

### 腳本 (`scripts/`)

| 腳本 | 說明 |
|------|------|
| `init_db.py` | 資料庫與表格初始化 |
| `fetch_data.py` | 多來源數據下載管線 |

## ETL 管線

`src/backend/database/etl.py` 提供可擴展的 ETL 框架：

```python
from pathlib import Path
from src.backend.database.etl import (
    ETLPipeline, CSVExtractor,
    CancerDataTransformer, BaseLoader
)

pipeline = ETLPipeline(
    extractor=CSVExtractor(),
    transformer=CancerDataTransformer(column_map={"old": "new"}),
    loader=CustomLoader(),
    name="cancer_data_import",
)
result = await pipeline.run(Path("data/raw/sample.csv"))
print(f"Loaded: {result.records_loaded}, Skipped: {result.records_skipped}")
```

可自訂的元件：
- `BaseExtractor` — 支援 CSV、JSON、Excel
- `BaseTransformer` — 資料清理與欄位映射
- `BaseLoader` — 資料庫批次寫入

## 資料庫實體關係

```
Patient (1) ──── (N) Diagnosis (1) ──── (N) Treatment (1) ──── (N) Drug
                                                          
ResearchPaper (獨立表格，儲存文獻數據)
```

### 關聯說明

- **Patient → Diagnosis**: 一對多，一個患者可能有多個診斷記錄
- **Diagnosis → Treatment**: 一對多，一個診斷對應多個治療方案
- **Treatment → Drug**: 一對多，一個治療方案包含多種藥物
- **ResearchPaper**: 獨立表格，用於存儲 PubMed 抓取的文獻資料

## 測試

```bash
# 執行所有測試
pytest

# 執行特定測試檔案
pytest tests/test_api.py

# 含涵蓋率報告
pytest --cov=src tests/
```

## 程式碼檢查

```bash
# Ruff lint
ruff check src/

# Black 格式化檢查
black --check src/

# 型別檢查
mypy src/
```

## Docker 建置

```bash
# API 映像
docker build -f docker/Dockerfile.api -t ai-kill-cancer-api .

# 前端映像
docker build -f docker/Dockerfile.frontend -t ai-kill-cancer-frontend .

# 完整環境
docker compose -f docker/docker-compose.yml up -d
```
