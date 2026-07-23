# 任務狀態

## 場景
Vercel 部署調查與修復

## 任務清單

| ID | 任務 | 狀態 | 負責 | 備註 |
|----|------|------|------|------|
| A1 | 審查所有 workflow 檔案 | ✅ 完成 | devops | |
| A2 | 審查前端建置相關檔案 | ✅ 完成 | devops | |
| A3 | 確認 gh CLI 可用性 | ✅ 完成 | devops | gh 不可用，改用 curl |
| A4 | 查詢最近 failed GitHub Actions run | ✅ 完成 | devops | run ID: 30018075089, 30018073484 |
| B1 | 定位第一個失敗 step 與錯誤訊息 | ✅ 完成 | devops | frontend: npm ci, backend: ruff |
| B2 | 分析根因並撰寫結構化錯誤報告 | ✅ 完成 | devops | ruff 無配置 + 無版本鎖定確定根因 |
| C1 | 比對 Vercel 官方部署流程 | ✅ 完成 | devops | 採用 Vercel CLI 方案 |
| C2 | 修正 vercel.json 配置 | ✅ 完成 | devops | nodeVersion: 18→22 |
| C3 | 重寫 deploy.yml 為 Vercel CLI 部署 | ✅ 完成 | devops | SSH/Docker → Vercel CLI |
| C4 | 確認 GitHub Secrets 名稱一致性 | ✅ 完成 | devops | VERCEL_TOKEN/ORG_ID/PROJECT_ID |
| C5 | git commit/push | ⏳ 待辦 | devops | |
| D1 | 觸發並監看 CI 結果 | ⏳ 待辦 | devops | |
| D2 | 監看 deploy workflow 結果 | ⏳ 待辦 | devops | |
| D3 | 回報三種狀態 | ⏳ 待辦 | devops | |
| D4 | 彙整 18 項完成證據 | ⏳ 待辦 | devops | |
