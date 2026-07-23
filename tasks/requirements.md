# 需求：Vercel 部署調查與修復

## 來源
用戶提供詳細的 Vercel 部署修復指南（359 行）

## 核心目標
調查並修復 GitHub Actions → Vercel 部署流程

## 任務清單（依用戶指南）

### 任務 1：確認部署 workflow 是否存在
- 列出 .github/workflows/ 所有檔案
- 搜尋 Vercel 相關引用
- 確認 trigger 條件、路徑排除、production 部署

### 任務 2：檢查 GitHub Secrets 引用名稱
- 檢查 workflow 中 secrets 名稱是否一致
- 不得輸出 secret 值
- 若無權確認，只能回報特定訊息

### 任務 3：查看真正的 GitHub Actions 失敗 log
- 使用 gh CLI 查詢失敗 run
- 定位第一個失敗 step 和錯誤訊息
- 輸出結構化錯誤報告

### 任務 4：修復標準部署流程
- 核對 Vercel root directory、vercel.json、package.json、vite.config
- 修正 workflow 使用 Vercel CLI 官方流程
- 正確設定 working-directory 與環境變數

### 任務 5：分別回報三種狀態
- GitHub Actions workflow conclusion
- Vercel deployment conclusion
- GitHub commit status

### 任務 6：正常重新觸發部署
- git add / commit / push
- 觸發 workflow（push 或 workflow_dispatch）
- 監看直到最終結論

## 完成證據（需回報 18 項）
1. 部署 workflow 文件路徑
2. workflow trigger
3. 使用的 Secret 名稱（不得輸出值）
4. 原失敗 run ID
5. 原失敗 job 與 step
6. 第一個有效錯誤
7. 根因
8. 修改的 workflow diff
9. 新 commit SHA
10. 新 GitHub Actions run ID
11. frontend test 結果
12. frontend build 結果
13. Vercel CLI build 結果
14. Vercel deploy 結果
15. 最終 GitHub Actions conclusion
16. 最終 commit status
17. 部署 URL（若 log 有提供才可回報）
18. 尚未完成或 BLOCKED 項目
