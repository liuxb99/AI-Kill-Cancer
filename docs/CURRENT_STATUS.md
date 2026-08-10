# Current Status

更新日期：2026-08-10

AI-Kill-Cancer 已經遠超早期 Phase 3A/3B 階段。近期實作已進入 Phase 3F～3H，包含 Recommendation/Clinical contract 解耦、Treatment ID、Outbox event_id、Clinical Safety Gate、真實公共資料下載、本地 SQLite runtime 相容，以及 Vercel FastAPI + SPA 的完整部署修復與線上 JSON smoke 驗證。

## 已實作／已有永久測試證據

```text
Drug Recommendation / Clinical Decision contracts     IMPLEMENTED
Treatment Plan dual-mode UI/API                       IMPLEMENTED
Clinical Graph deterministic treatment IDs            IMPLEMENTED
Outbox event_id persistence contract                  IMPLEMENTED
Recommendation service/API decoupling                 IMPLEMENTED
Treatment-plan clinical safety readiness gate         IMPLEMENTED
GDC/TCGA public data adapter                          IMPLEMENTED
ClinicalTrials.gov adapter                            IMPLEMENTED
OpenFDA adapter                                       IMPLEMENTED
PubMed/PMC adapter                                    IMPLEMENTED
CIViC adapter                                         IMPLEMENTED
Content-addressed public-data storage / dedup          IMPLEMENTED
Vercel Python API routing                             VERIFIED
Frontend HTML-vs-JSON routing guard                   VERIFIED
Local SQLite runtime / ORM compatibility              VERIFIED ON SELF-HOSTED RUNNER
Vercel demo SQLite bootstrap                          VERIFIED
Vercel writable public-data cache                     VERIFIED
Production alias page smoke                           VERIFIED
Production alias API JSON smoke                       VERIFIED
```

## 当前阶段

```text
Phase 3F-1 treatment ID contract      COMPLETE
Phase 3F-2 outbox event contract      COMPLETE
Phase 3F-3 recommendation decoupling  COMPLETE
Phase 3G clinical safety gate         COMPLETE
Phase 3H public data downloads        IMPLEMENTED
SQLite local compatibility            VERIFIED
Vercel demo deployment                VERIFIED
Persistent production database        NOT YET VERIFIED
Full production verification          IN_PROGRESS
```

## 2026-08-10 Vercel 線上修復結果

正式 alias：`https://ai-kill-cancer-zqpi.vercel.app`

目前 gated deployment 已完成以下線上 smoke：

```text
Production page                              PASS
/api/v1/health                               PASS — 200 JSON
/api/v1/ptc-readiness                        PASS — 200 JSON
/api/v1/ptc-completion/status                PASS — 200 JSON
/api/v1/ptc-data-quality/overview            PASS — 200 JSON
```

本輪修復的主要根因包括：

- unique deployment URL 的保護頁曾被誤判成 SPA/API routing 問題，smoke 已改驗 canonical production alias；
- FastAPI serverless core requirements 曾漏掉 `httpx`，導致 v1 router import / Function cold start 失敗；
- Vercel demo runtime 未配置 PostgreSQL，已明確使用 `/tmp/ai-kill-cancer.db` 作為 ephemeral SQLite demo database；
- `PTCCompletionService` 即使執行 read-only readiness/status，也會建立 `PublicDataStore`；其原預設 `var/public-data` 位於 Vercel 唯讀部署檔案系統，已改以 `/tmp/ai-kill-cancer-public-data` 作為 Vercel writable cache；
- database session 已增加 request-time initialization guard，避免 serverless cold start / 部分初始化後直接讓 DB-backed endpoint 失敗。

## Database runtime policy

目前正式資料庫策略分成三層：

```text
PostgreSQL
→ 真正 production / Alembic migration / concurrency / restart persistence 權威

SQLite local
→ local / demo / research / Windows self-hosted regression

Vercel /tmp SQLite
→ 僅供部署 smoke 與空資料 demo runtime
→ ephemeral、不可視為持久化 production database
```

SQLite 本地模式已加入：

- `DB_BACKEND=sqlite` / `SQLITE_PATH=...` 設定；
- explicit `DATABASE_URL=sqlite+aiosqlite:///...` 仍優先；
- SQLite file parent directory 自動建立；
- `PRAGMA foreign_keys=ON`；
- `PRAGMA busy_timeout=5000`；
- in-memory `StaticPool`；
- ORM metadata local schema bootstrap；
- file persistence / FK / memory-session 永久 regression；
- Windows self-hosted 自動 SQLite Action；
- DB-backed request 的 lazy initialization guard。

`APP_MODE=production` 仍明確禁止 SQLite。Vercel 現階段使用 `APP_MODE=demo` + `/tmp` SQLite，目的只是讓線上 UI/API 可驗證並正確呈現空資料／not-ready 狀態，不得把此狀態宣稱為 production persistence parity。

完整說明：`docs/SQLITE_LOCAL_COMPATIBILITY_ZH.md`。

## CI / Deployment 現況

Local Verification Gate 已由 Windows self-hosted runner 自動驗證：

```text
push master
→ backend compile / lint / SQLite regression
→ configured SQLite bootstrap
→ local DB file verification
→ diff check
→ PASS 後才允許 Vercel production deployment
```

Vercel deployment workflow 再驗證：

```text
verified SHA only
→ Vercel project/root correction
→ production environment pull / preflight
→ deploy canonical production alias
→ page smoke
→ 4 個關鍵 API JSON smoke
```

原 PostgreSQL CI 與 PostgreSQL migration/persistence 驗證仍保留其獨立責任；SQLite/Vercel demo PASS 不得取代 PostgreSQL production verification。

## 真正剩余缺口

1. 為正式線上環境接入持久化 PostgreSQL，完成 `DATABASE_URL`、production JWT/CORS 等正式環境配置。
2. PostgreSQL migration / restart / persistence 實機驗證，確認跨 Function instance 與重新部署後資料仍存在。
3. 將目前 Vercel `/tmp` demo database 與 `/tmp` public-data cache 明確限制在 smoke/demo，不作為權威研究資料儲存。
4. Windows self-hosted runner 上擴大全量 backend/frontend/database 測試。
5. Public-data adapter 的真實網路與錯誤恢復長期穩定性。
6. Clinical Safety Gate 的跨頁面/跨流程 E2E。
7. Knowledge Graph、推薦、Treatment Plan、公共數據間的完整 traceability E2E。
8. 修正 health API 中仍存在的簡化 database_connected 表示，讓 health/readiness 直接反映真實 DB initialization / connectivity 狀態。
9. 只有上述 production persistence 與 E2E 驗證全部通過後，才可標記 FULLY VERIFIED。

## 安全邊界

本項目屬於研究與臨床決策輔助軟體工程項目。任何推薦、治療計畫或風險判斷均不得替代合格醫療專業人員的診斷與治療決策。軟體完成度與醫學有效性必須分開評價。
