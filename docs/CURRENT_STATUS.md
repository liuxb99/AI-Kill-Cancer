# Current Status

更新日期：2026-08-09

AI-Kill-Cancer 已經遠超早期 Phase 3A/3B 階段。近期實作已進入 Phase 3F～3H，包含 Recommendation/Clinical contract 解耦、Treatment ID、Outbox event_id、Clinical Safety Gate、真實公共資料下載、Vercel API routing 修復，以及本地 SQLite runtime 相容。

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
Vercel Python API routing                             IMPLEMENTED
Frontend HTML-vs-JSON routing guard                   IMPLEMENTED
Local SQLite runtime / ORM compatibility              IMPLEMENTED — WAITING FOR SELF-HOSTED VERIFICATION
```

## 当前阶段

```text
Phase 3F-1 treatment ID contract      COMPLETE
Phase 3F-2 outbox event contract      COMPLETE
Phase 3F-3 recommendation decoupling  COMPLETE
Phase 3G clinical safety gate         COMPLETE
Phase 3H public data downloads        IMPLEMENTED
SQLite local compatibility            IMPLEMENTED — WAITING FOR SELF-HOSTED VERIFICATION
Full production verification          IN_PROGRESS
```

## Database runtime policy

目前正式資料庫策略分成兩條：

```text
PostgreSQL
→ production / Alembic migration / concurrency / restart persistence 權威

SQLite
→ local / demo / research / Windows self-hosted regression
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
- Windows `[self-hosted, Windows, X64, ai-ci]` 自動 SQLite Action。

`APP_MODE=production` 明確禁止 SQLite，避免把本地相容模式誤當 production database parity。

完整說明：`docs/SQLITE_LOCAL_COMPATIBILITY_ZH.md`。

## CI 現況

2026-08-09 已新增 `.github/workflows/sqlite-local.yml`：

```text
push master
pull_request master
workflow_dispatch
→ Windows self-hosted ai-ci
→ SQLite local compatibility regression
```

原 PostgreSQL CI 與 PostgreSQL migration/persistence 驗證仍保留其獨立責任；SQLite self-hosted PASS 不得取代 PostgreSQL production verification。

## 真正剩余缺口

1. Windows self-hosted runner 完成 SQLite compatibility Action 並保留 PASS 證據。
2. Windows self-hosted runner 上擴大全量 backend/frontend/database 測試。
3. PostgreSQL persistence/restart/migration 實機驗證。
4. Public-data adapter 的真實網路與錯誤恢復長期穩定性。
5. Clinical Safety Gate 的跨頁面/跨流程 E2E。
6. Knowledge Graph、推薦、Treatment Plan、公共數據間的完整 traceability E2E。
7. Production deployment smoke test。
8. 只有上述全部通過後，才可標記 FULLY VERIFIED。

## 安全邊界

本項目屬於研究與臨床決策輔助軟體工程項目。任何推薦、治療計畫或風險判斷均不得替代合格醫療專業人員的診斷與治療決策。軟體完成度與醫學有效性必須分開評價。
