# API 文檔

## 概述

基於 FastAPI 的 RESTful API，提供癌症診斷預測與治療推薦服務。

- **基礎 URL**: `http://localhost:8000`
- **自動文檔**: `/docs` (Swagger) 或 `/redoc` (ReDoc)
- **版本**: `v1`

## 系統端點

### GET /api/v1/health

健康檢查。

**回應**:
```json
{
  "status": "ok",
  "version": "1.0.0",
  "model_loaded": true,
  "database_connected": true
}
```

### GET /api/v1/info

系統資訊。

**回應**:
```json
{
  "app_name": "AI Kill Cancer API",
  "version": "1.0.0",
  "endpoints": [
    {"path": "/api/v1/predict", "method": "POST", "description": "Cancer diagnosis prediction"},
    {"path": "/api/v1/recommend", "method": "POST", "description": "Treatment recommendation"},
    {"path": "/api/v1/health", "method": "GET", "description": "Health check"},
    {"path": "/api/v1/info", "method": "GET", "description": "System information"}
  ]
}
```

## 預測端點

### POST /api/v1/predict

癌症診斷風險預測。

**請求體**:
```json
{
  "age": 55,
  "gender": "M",
  "biomarkers": {
    "CEA": 5.2,
    "CA19-9": 37.0,
    "AFP": 3.1
  },
  "family_history": ["Lung Cancer"],
  "smoking_history": "current"
}
```

**參數說明**:

| 參數 | 型別 | 必填 | 說明 |
|------|------|------|------|
| age | int | 是 | 年齡 (0-120) |
| gender | string | 是 | 性別，`M` 或 `F` |
| biomarkers | object | 是 | 生物標記數值，key-value 對 |
| family_history | string[] | 否 | 家族癌症病史 |
| smoking_history | string | 否 | 吸菸史：`never`, `former`, `current` |

**回應**:
```json
{
  "patient_id": "a1b2c3d4-...",
  "cancer_type": "Lung Cancer",
  "probability": 0.76,
  "risk_level": "High",
  "recommendations": [
    "Recommended screening: Lung Cancer panel",
    "Consult with oncologist for further evaluation",
    "Maintain regular follow-up schedule"
  ]
}
```

**風險等級**: `probability >= 0.8` → High, `>= 0.4` → Moderate, `< 0.4` → Low.

## 推薦端點

### POST /api/v1/recommend

治療方案推薦。

**請求體**:
```json
{
  "cancer_type": "Lung Cancer",
  "stage": "2",
  "biomarkers": {"EGFR": 0.8, "PD-L1": 0.6},
  "age": 60,
  "prior_treatments": ["Surgery"]
}
```

**參數說明**:

| 參數 | 型別 | 必填 | 說明 |
|------|------|------|------|
| cancer_type | string | 是 | 確診癌症類型 |
| stage | string | 是 | 癌症分期 (0-4) |
| biomarkers | object | 是 | 當前生物標記數值 |
| age | int | 是 | 年齡 (0-120) |
| prior_treatments | string[] | 否 | 先前接受過的治療 |

**回應**:
```json
{
  "patient_id": "e5f6g7h8-...",
  "cancer_type": "Lung Cancer",
  "stage": "2",
  "primary_option": {
    "name": "Lung Cancer — Stage 2 Standard Protocol",
    "description": "First-line treatment based on NCCN guidelines",
    "success_rate": 0.85,
    "side_effects": ["Fatigue", "Nausea", "Hair loss"],
    "estimated_cost": "$50,000 – $120,000"
  },
  "alternative_options": [
    {
      "name": "Targeted Therapy",
      "description": "Precision medicine based on genetic markers",
      "success_rate": 0.72,
      "side_effects": ["Skin rash", "Diarrhea", "Liver enzyme elevation"],
      "estimated_cost": "$80,000 – $200,000"
    }
  ]
}
```

## 環境變數

| 變數 | 預設值 | 說明 |
|------|--------|------|
| DEBUG | false | 除錯模式 |
| CORS_ORIGINS | * | CORS 允許來源 |
| DB_HOST | localhost | 資料庫主機 |
| DB_PORT | 5432 | 資料庫埠號 |
| DB_USER | postgres | 資料庫用戶 |
| DB_PASSWORD | postgres | 資料庫密碼 |
| DB_NAME | cancer_db | 資料庫名稱 |
| MODEL_PATH | ./models/cancer_prediction.pkl | 模型路徑 |
| MODEL_ENABLED | true | 啟用模型載入 |
| LOG_LEVEL | INFO | 日誌級別 |
