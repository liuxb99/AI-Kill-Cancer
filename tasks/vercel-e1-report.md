# Phase E1 調查報告 — Vercel Project 資訊比對

> 時間：2026-07-24 10:00
> 狀態：⛔ BLOCKED — 需要人工介入

---

## 一、Token 狀態

| 項目 | 結果 |
|------|------|
| VERCEL_TOKEN 存在性 | ✅ 存在（Windows 系統環境變數） |
| VERCEL_TOKEN 有效性 | ❌ **無效**（Vercel API 回傳 403 Forbidden） |
| CLI 驗證命令 | `vercel project inspect` → `Not authorized` |
| REST API 驗證 | `GET /v2/user` → HTTP 403 Forbidden |

**結論：** 目前的 VERCEL_TOKEN 已被撤銷或過期，無法用於任何 Vercel CLI 或 API 操作。

---

## 二、兩個 Project 對比

| 欄位 | frontend | ai-kill-cancer-zqpi |
|------|----------|---------------------|
| **Project Name** | `frontend` | `ai-kill-cancer-zqpi` |
| **Team** | `liuxb99-9860s-projects` | `liuxb99-9860s-projects`（推測） |
| **Production Domain** | `frontend-liuxb99-9860s-projects.vercel.app` | `ai-kill-cancer-zqpi.vercel.app` |
| **HTTP 狀態** | ✅ 302 Redirect | ❌ **500 FUNCTION_INVOCATION_FAILED** |
| **Git 關聯** | 由 GitHub Actions 部署關聯 | 由 Vercel Git Integration 自動關聯 |
| **建立方式** | GitHub Actions 透過 `vercel pull` 自動建立 | Vercel GitHub Integration 自動建立 |
| **最後部署** | ✅ success（Run #30029948264） | ❌ failure |
| **Root Directory** | `src/frontend`（來自 vercel.json） | ⚠️ 未設定或預設值 |
| **Framework** | Vite（來自 vercel.json） | ⚠️ 可能未正確指定 |

---

## 三、GitHub Actions 配置分析

### deploy.yml 現狀
```yaml
env:
  VERCEL_ORG_ID: ${{ secrets.VERCEL_ORG_ID }}
  VERCEL_PROJECT_ID: ${{ secrets.VERCEL_PROJECT_ID }}

# 然後執行：
vercel pull --yes --environment=production --token=${{ secrets.VERCEL_TOKEN }}
vercel build --prod --token=${{ secrets.VERCEL_TOKEN }}
vercel deploy --prebuilt --prod --token=${{ secrets.VERCEL_TOKEN }}
```

### 關鍵發現
1. `VERCEL_PROJECT_ID` 目前指向 **frontend** project（推測）
2. `vercel pull` 若缺少正確的 Project ID，會自動建立新 project（這就是 frontend 被建立的原因）
3. 所有操作都在 `src/frontend` 目錄下執行
4. Node.js 版本：**20**（與 vercel.json 的 22 不一致）

### 需要修正
1. `VERCEL_PROJECT_ID` → 改為 `ai-kill-cancer-zqpi` 的 Project ID
2. Node.js 版本 → 統一為 **22**（與 vercel.json 一致）

---

## 四、Public URL 驗證

### frontend（誤建 Project）
```
curl -I https://frontend-liuxb99-9860s-projects.vercel.app/
→ HTTP/2 302
→ content-type: text/plain
→ Body: Redirecting...
```

### ai-kill-cancer-zqpi（正式目標 Project）
```
curl -I https://ai-kill-cancer-zqpi.vercel.app/
→ HTTP/2 500
→ content-type: text/plain; charset=utf-8
→ Body: FUNCTION_INVOCATION_FAILED
→ Server: hkg1::dghwp-1784858826091-c2f0a47f3a7f
```

---

## 五、BLOCKED 項目清單

以下為需要使用者人工介入的項目：

| # | 項目 | 精確需要修改的欄位 | 建議操作 |
|---|------|-------------------|---------|
| 1 | **VERCEL_TOKEN 失效** | Windows 環境變數 `VERCEL_TOKEN` + GitHub Secret `VERCEL_TOKEN` | 登入 Vercel Dashboard → Settings → Tokens → 建立新 Token → 更新兩處 |
| 2 | **VERCEL_PROJECT_ID 指向錯誤** | GitHub Secret `VERCEL_PROJECT_ID` | 需取得 `ai-kill-cancer-zqpi` 的 Project ID（Dashboard 中可見），更新 GitHub Secret |
| 3 | **ai-kill-cancer-zqpi 設定未校正** | Vercel Dashboard → Project Settings → General | 設定 Root Directory = `src/frontend`、Framework = `Vite`、Build = `npm run build`、Output = `dist` |
| 4 | **Vercel Git Integration 需停用** | Vercel Dashboard → Project → Settings → Git | 停用 Auto Deploy，但保留 GitHub App 安裝 |
| 5 | **frontend 誤建 Project 需清理** | Vercel Dashboard → 手動刪除 `frontend` Project | 先確認 canonical project 正常運作後再刪除 |

---

## 六、已完成項目

- [v] E1.1：查詢 frontend project 公開資訊（domain、HTTP 狀態、建立方式）
- [v] E1.2：查詢 ai-kill-cancer-zqpi 公開資訊（domain、HTTP 狀態）
- [v] E1.3：比對兩個 project 配置差異
- [v] 分析 GitHub Actions workflow 配置（deploy.yml、ci.yml）
- [v] 確認 VERCEL_TOKEN 無效為核心阻塞原因
- [v] 列出所有需要人工修改的欄位

---

## 七、下一步建議

1. **使用者手動操作：** 依上方 BLOCKED 清單更新 Token 與設定
2. **重新啟動：** 完成後通知主代理繼續執行 E2–E6
3. **預計工時：** 人工操作約 10–15 分鐘
