# AI Kill Cancer 知識庫

用人工智慧全方位對抗癌症 — 工具、網站、研究、開發。

## 文件總覽

| 文件 | 說明 |
|------|------|
| [API 文檔](api.md) | FastAPI 後端 API 使用說明與端點參考 |
| [模型說明](models.md) | AI/ML 模型架構、訓練與推論流程 |
| [使用者指南](guide.md) | 系統安裝、配置與操作指引 |
| [開發者指南](development.md) | 開發環境建置、程式碼規範與貢獻流程 |
| [技術選型](tech-stack.md) | 前端 / 後端 / AI / 資料庫技術棧 |
| [資料集](datasets.md) | 可用癌症數據集清單與取得方式 |

## 專案結構

```
AI_Kill_Cancer/
├── src/
│   ├── frontend/         # React 前端網站
│   ├── backend/          # FastAPI 後端 API
│   │   ├── api/          # API 路由
│   │   ├── database/     # 資料庫模型與 CRUD
│   │   └── models/       # Pydantic 請求/回應模型
│   ├── models/           # PyTorch AI 模型
│   │   ├── cancer_classifier.py    # 癌症分類器
│   │   ├── drug_discovery.py       # 藥物發現管線
│   │   ├── drug_response.py        # 藥物反應預測
│   │   ├── treatment_recommender.py # 治療建議
│   │   ├── literature_analyzer.py  # 文獻分析
│   │   ├── pubmed_fetcher.py       # PubMed 資料抓取
│   │   ├── molecule_utils.py       # 分子工具函數
│   │   ├── predict.py              # 推論封裝
│   │   └── train.py                # 訓練流程
│   └── tools/            # 輔助工具
├── data/                 # 資料集（raw / processed / cache）
├── notebooks/            # Jupyter notebooks
├── scripts/              # CLI 工具腳本
│   ├── init_db.py        # 資料庫初始化
│   └── fetch_data.py     # 資料下載管線
├── tests/                # 測試
├── docker/               # Docker 配置
└── docs/                 # 文檔
```

## 核心功能

- **癌症風險預測** — 基於生物標記物與臨床資訊的癌症診斷預測
- **治療方案推薦** — 根據癌症類型與分期提供標準與替代治療方案
- **藥物發現** — 分子 VAE 生成 + DTI 預測的藥物發現管線
- **藥物反應預測** — 基因表現數據驅動的個體化藥物反應評估
- **文獻分析** — PubMed 文獻抓取、NER 實體提取與趨勢分析

## 開發階段

| 階段 | 內容 | 狀態 |
|------|------|------|
| Phase 1 | 基礎建設 | 進行中 |
| Phase 2 | 核心模型開發 | 待開始 |
| Phase 3 | 後端與資料 | 待開始 |
| Phase 4 | 前端與可視化 | 待開始 |
| Phase 5 | 進階研究工具 | 待開始 |
| Phase 6 | 整合與部署 | 待開始 |
