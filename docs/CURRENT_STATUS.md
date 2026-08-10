# Current Status

更新日期：2026-08-10

AI-Kill-Cancer 已進入版本化推進階段。現行架構正式採用「Local-First SQLite + Vercel Demo Showcase」雙模式：

- 本地 SQLite 是主要可用、可持久化、可累積研究資料的工作資料庫；
- Vercel 僅作線上展示與部署驗證，使用內建示範 CSV 資料集啟動展示流程；
- Vercel `/tmp` SQLite 僅是由 demo CSV 投影出的暫存 runtime，不承擔正式資料持久化責任；
- PostgreSQL 降級為未來多人協作／中央伺服器／高併發時的 Optional Scale-out Backend，不阻塞目前版本推進。

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
Local SQLite runtime / ORM compatibility              VERIFIED ON SELF-HOSTED RUNNER
Vercel Python API routing                             VERIFIED
Vercel static asset routing                           VERIFIED
Production browser render via Chromium                VERIFIED
Production alias page/API smoke                       VERIFIED
```

## 當前版本主線

```text
v0.3.0 — Local-First Research & Demo Showcase
```

v0.3.0 不以新增大量新癌症功能為目標，而是把現有能力整理成兩個可明確驗收的運行模式。

### A. Vercel Demo Showcase

```text
Bundled demo CSV
→ bootstrap /tmp demo SQLite
→ Patient / Case / Variant / Evidence
→ Recommendation / Clinical Decision
→ Treatment Plan / Knowledge Graph / Report
→ Chromium browser E2E
```

要求：

- demo CSV 是 Vercel 展示資料的 Source of Truth；
- serverless cold start 或重新部署後可重新由 CSV bootstrap；
- Vercel 不保存正式研究資料；
- 所有示範病例與推薦結果必須清楚標示 Demo / Synthetic / Research Only；
- 頁面需可直接選擇 3～5 個固定示範病例，展示完整流程，而不是只展示空白頁或功能卡。

### B. Local Research Workspace

```text
APP_MODE=local
DB_BACKEND=sqlite
SQLITE_PATH=data/ai-kill-cancer.db
```

本地 SQLite 為主要資料庫，要求：

- 新建 Patient / Case / Specimen / Variant；
- 可匯入 CSV / variants；
- 可執行 evidence / recommendation / treatment plan / graph 流程；
- 關閉程式、重新啟動電腦或應用後資料仍存在；
- schema version、migration、FK、integrity、backup/restore 有永久測試；
- 正式研究資料不得依賴 Vercel `/tmp`。

## Database runtime policy

```text
Local SQLite
→ 主要／權威工作資料庫
→ local research workspace
→ patient/case/variant/evidence/recommendation/treatment-plan/graph persistence

Vercel Demo SQLite (/tmp)
→ 僅供 demo CSV runtime projection
→ ephemeral
→ 可隨時從 bundled CSV 重建
→ 不視為正式資料保存

PostgreSQL
→ Optional Scale-out Backend
→ 未來多人協作、中央 Server、高併發或 SaaS 化時再啟用
→ 不阻塞 v0.3.0～目前版本主線
```

SQLite 本地模式現有能力：

- `DB_BACKEND=sqlite` / `SQLITE_PATH=...`；
- explicit `DATABASE_URL=sqlite+aiosqlite:///...` 優先；
- SQLite file parent directory 自動建立；
- `PRAGMA foreign_keys=ON`；
- `PRAGMA busy_timeout=5000`；
- in-memory `StaticPool`；
- ORM metadata local schema bootstrap；
- file persistence / FK / memory-session regression；
- Windows self-hosted SQLite Action；
- DB-backed request lazy initialization guard。

## Vercel 線上狀態

正式 alias：`https://ai-kill-cancer-zqpi.vercel.app`

2026-08-10 已完成：

```text
Production page                              PASS
/api/v1/health                               PASS — 200 JSON
/api/v1/ptc-readiness                        PASS — 200 JSON
/api/v1/ptc-completion/status                PASS — 200 JSON
/api/v1/ptc-data-quality/overview            PASS — 200 JSON
Chromium browser render                      PASS
React root rendered                          PASS
Console fatal errors                         0
JS/CSS bad responses                         0
```

此前白屏根因為 SPA catch-all 將 `/assets/*.js` 也 rewrite 成 `/index.html`，導致瀏覽器收到 `text/html` module；已改成 filesystem-first，再做 SPA fallback，且由真實 Chromium 永久驗證。

## v0.3.0 Acceptance Gate

### Vercel Demo

- [ ] 標準 demo CSV dataset 已建立；
- [ ] 至少 3 個可切換示範病例；
- [ ] cold start 可由 CSV 自動 bootstrap；
- [ ] 核心頁面可讀到示範資料；
- [ ] demo banner / provenance / synthetic 標記一致；
- [ ] Chromium E2E 覆蓋首頁與主要功能 route；
- [ ] Vercel 不宣稱資料持久化。

### Local SQLite

- [ ] 預設本地工作資料庫路徑標準化；
- [ ] 初次啟動 bootstrap；
- [ ] Patient → Case → Variant → Evidence → Recommendation → Treatment Plan 可完整落庫；
- [ ] 關閉／重啟後資料仍存在；
- [ ] SQLite integrity check；
- [ ] upgrade 前自動備份；
- [ ] backup/restore smoke；
- [ ] traceability ID/provenance chain E2E；
- [ ] Browser E2E + backend/frontend/database tests 全通過。

## 版本路線

```text
v0.3.0  Local-First Research & Demo Showcase
v0.4.0  Precision Oncology Traceability
v0.5.0  Real Data + Knowledge Graph + AI
v0.6.0  Clinical Research Workbench
v0.7.0  Scientific Validation & Evaluation
v0.8.x  Security / Reliability / Observability Hardening
v0.9.x  Release Candidate / Data Migration / Compatibility
v1.0.0  Research-Grade Stable
```

v1.0.0 僅代表軟體達到穩定研究級交付標準，不代表已完成臨床有效性驗證，也不代表可取代醫療專業人員的診斷或治療決策。

## v0.3.0 下一批開發順序

1. 建立標準示範 CSV dataset；
2. 實作 Demo CSV bootstrap service；
3. Vercel cold start 自動將 demo CSV 投影到 `/tmp` SQLite；
4. 建立示範病例選擇／查詢 API 與前端入口；
5. 本地 SQLite 預設 workspace 路徑與 bootstrap；
6. local persistence + restart E2E；
7. SQLite backup/restore + integrity gate；
8. 擴充 Chromium E2E 到核心功能 route；
9. 完成 v0.3.0 release checklist / changelog / tag。

## 安全邊界

本項目屬於研究與臨床決策輔助軟體工程項目。任何推薦、治療計畫、風險評估與示範病例輸出均不得替代合格醫療專業人員的診斷與治療決策。Demo 資料、Synthetic 資料、真實公共研究資料與本地使用者資料必須有明確 provenance，軟體完成度與醫學有效性必須分開評價。
