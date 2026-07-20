# AI Kill Cancer

用人工智慧輔助癌症研究 — 工具、網站、研究、開發。

> ⚠️ **重要声明：本项目不是医疗产品。**
> 所有 AI 模型仍处于**未训练/未验证**的原型阶段。
> API 返回的数据为模拟（synthetic）数据，**不可用于临床诊断或治疗**。

## 项目状态

| 階段 | 內容 | 狀態 |
|------|------|------|
| Phase 1 | 基礎建設（骨架搭建） | ✅ 完成 |
| Phase 2 | 核心模型開發 | ❌ 未開始 |
| Phase 3 | 後端與資料 | 🟡 部分（Schema 完成，無真實資料） |
| Phase 4 | 前端與可視化 | ✅ 完成（使用模擬資料） |
| Phase 5 | 進階研究工具 | 🟡 骨架完成 |
| Phase 6 | 整合與部署 | ✅ 完成（Vercel） |

## 完成的功能（系統骨架）

- FastAPI RESTful API（predict, recommend, charts, research）
- React + TypeScript 前端（6 個頁面 + 圖表）
- PostgreSQL 資料庫模型
- APP_MODE 三模式（demo / research / production）
- Health 端點（liveness, readiness, dependencies）
- 模擬資料附資料溯源（DataProvenance）與免責聲明
- 103 個單元測試全部通過

## 專案結構

```
├── src/
│   ├── frontend/    # 前端網站 (React + Vite)
│   ├── backend/     # 後端 API (FastAPI)
│   ├── models/      # AI 模型定義 (PyTorch)
│   └── tools/       # 輔助工具
├── api/             # Vercel Serverless 入口
├── docs/            # 文檔
├── tests/           # 測試 (pytest)
└── docker/          # Docker 配置
```

## 快速開始

```bash
# 安裝依賴
pip install -r requirements.txt
pip install -r requirements-ai.txt

# 啟動 API（demo 模式）
cd src/backend
uvicorn main:app --reload

# 啟動前端
cd src/frontend
npm install
npm run dev
```

## 文檔

- [CURRENT_STATE.md](docs/CURRENT_STATE.md) — 當前狀態
- [MEDICAL_SAFETY.md](docs/MEDICAL_SAFETY.md) — 醫療安全聲明
- [DATA_PROVENANCE.md](docs/DATA_PROVENANCE.md) — 數據溯源
- [MODEL_CARD.md](docs/MODEL_CARD.md) — 模型卡片
- [DEPLOYMENT.md](docs/DEPLOYMENT.md) — 部署說明
- [AGENTS.md](AGENTS.md) — 開發者指南

## 技術棧

- **後端**：Python 3.10+ / FastAPI / SQLAlchemy / PyTorch
- **前端**：TypeScript / React / Vite / Tailwind CSS
- **部署**：Vercel Serverless
- **資料庫**：PostgreSQL（可選）
- **測試**：pytest (103 tests)
