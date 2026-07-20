# AI Kill Cancer

甲狀腺癌患者個人化基因分析、分子機制視覺化、既有藥物再定位與可追溯證據報告平台。

> ⚠️ **重要聲明：本專案目前是研究型軟體，不是醫療產品。**
> 所有 AI 模型與資料流程仍處於開發或未完成驗證階段。
> 系統輸出不構成診斷、處方、停藥、換藥或治療建議，任何用藥決策必須由合格醫師結合完整臨床資料判斷。

## 產品主線

目標使用者是已確診甲狀腺癌、並已取得腫瘤 DNA 或其他分子檢測結果的患者、研究人員與醫療專業人員。

核心流程：

```text
患者建立甲狀腺癌病例
        ↓
上傳 VCF / CSV / JSON / 檢測報告
        ↓
變異標準化、註釋與品質檢查
        ↓
Three.js 染色體、基因、蛋白質與路徑視覺化
        ↓
搜尋已核准藥物、其他癌種藥物與舊藥再定位候選
        ↓
整理支持證據、反向證據、限制與不確定性
        ↓
產生患者版及醫療專業版研究報告
```

本專案不再以「判斷患者是否罹癌」作為主線，也不以自動治療推薦為產品目標。

## 目標功能

- 甲狀腺癌患者案例、檢體與分子檢測資料管理。
- VCF、CSV、TSV、JSON 與檢測報告上傳。
- SNV、indel、copy-number、fusion、TERT promoter 等變異標準化。
- BRAF、RAS、RET、NTRK、TERT、TP53、PTEN、PIK3CA 等甲狀腺癌核心基因分析。
- Three.js 染色體、變異、訊號路徑及 drug-target evidence graph。
- 已核准、off-label、臨床試驗、前臨床與研究假說分級。
- 支持證據與反向證據並列的 Evidence Card。
- 舊藥再定位候選、臨床試驗匹配與可追溯來源。
- 患者易懂版與醫療專業版報告。
- Consent、privacy、audit log、分析版本及 provenance。

## 安全邊界

系統可以提供研究型決策支援，但禁止：

- 自動診斷癌症。
- 提供藥物劑量或用藥指令。
- 將 VUS 直接視為可用藥變異。
- 將細胞、動物或計算結果宣稱為人體療效。
- 將舊藥再定位候選包裝成已證實治療。
- 讓 LLM 自行創造基因—藥物關聯。

所有基因、路徑、藥物及證據連線必須由結構化資料來源產生；LLM 僅負責解釋、摘要與衝突整理。

## 目前狀態

| 階段 | 內容 | 狀態 |
|------|------|------|
| Phase 0 | 現有推論、安全與模型契約修正 | 🟡 進行中 |
| Phase 1 | 甲狀腺癌 Precision Oncology 產品重構 | ⏳ 下一階段 |
| Phase 2 | DNA 上傳、變異標準化與品質報告 | ❌ 未開始 |
| Phase 3 | 甲狀腺癌基因、路徑、藥物與證據知識庫 | ❌ 未開始 |
| Phase 4 | Three.js 互動基因組與證據視覺化 | ❌ 未開始 |
| Phase 5 | 舊藥再定位、反證與臨床試驗匹配 | ❌ 未開始 |
| Phase 6 | 患者版、醫師版與腫瘤委員會報告 | ❌ 未開始 |

## 現有工程骨架

- FastAPI RESTful API。
- React + TypeScript 前端。
- PostgreSQL 資料庫模型。
- PyTorch 模型骨架。
- APP_MODE 三模式：demo / research / production。
- Health 端點：liveness、readiness、dependencies。
- 模擬資料 provenance 與醫療免責聲明。
- pytest 測試套件。

現有 predict、recommend、charts 等功能屬早期原型，不代表真實甲狀腺癌分析或臨床治療能力，後續將依新產品規劃重構。

## 專案結構

```text
├── src/
│   ├── frontend/    # React + TypeScript 前端
│   ├── backend/     # FastAPI API
│   ├── models/      # AI / 分析模型
│   └── tools/       # 資料處理與輔助工具
├── api/             # Vercel Serverless 入口
├── docs/            # 產品、醫療安全、資料與部署文件
├── tests/           # pytest 測試
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

## 主要文件

- [THYROID_PRECISION_ONCOLOGY_PRODUCT_PLAN.md](docs/THYROID_PRECISION_ONCOLOGY_PRODUCT_PLAN.md) — 新產品定位、患者流程、Three.js 規劃、舊藥再定位與開發路線。
- [CURRENT_STATE.md](docs/CURRENT_STATE.md) — 當前工程狀態。
- [MEDICAL_SAFETY.md](docs/MEDICAL_SAFETY.md) — 醫療安全聲明。
- [DATA_PROVENANCE.md](docs/DATA_PROVENANCE.md) — 資料溯源。
- [MODEL_CARD.md](docs/MODEL_CARD.md) — 模型卡片。
- [DEPLOYMENT.md](docs/DEPLOYMENT.md) — 部署說明。
- [AGENTS.md](AGENTS.md) — 開發者指南。

## 下一個正式任務

現有 P0 基礎修正完成並經 Git 審查後，進入：

> **Phase 1：甲狀腺癌 Precision Oncology 產品重構。**

第一輪應先完成領域模型與資料契約，不得用 synthetic 或 mock 結果冒充真實分析：

1. Patient case、specimen、sequencing test、uploaded file schema。
2. VCF / CSV 上傳 API contract。
3. Thyroid cancer variant schema 與首批核心基因格式。
4. Three.js visualization data contract。
5. Drug Candidate 與 Evidence Card schema。
6. 所有候選強制包含來源、證據層級、限制及反向證據。
7. 文件、API schema、測試同步更新。

## 技術棧

- **後端**：Python 3.10+ / FastAPI / SQLAlchemy / PyTorch
- **前端**：TypeScript / React / Vite / Tailwind CSS / Three.js
- **資料庫**：PostgreSQL；SQLite 僅供本地 MVP
- **部署**：Vercel Serverless / Docker
- **測試**：pytest
