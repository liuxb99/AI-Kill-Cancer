# Current Status

更新日期：2026-08-10

AI-Kill-Cancer 當前主線：**v0.3.0 — Local-First Research & Demo Showcase**。

架構政策不變：Local SQLite 是主要持久化研究工作資料庫；Vercel 使用 bundled synthetic CSV + ephemeral demo runtime；PostgreSQL 是 Optional Scale-out Backend。

## 已驗證底座

```text
Local SQLite runtime / ORM compatibility          VERIFIED
SQLite file persistence / FK / memory regression  VERIFIED
Vercel Python/static routing                      VERIFIED
Production page/API/Chromium smoke                VERIFIED
Demo core CSV bootstrap + UUIDv5 idempotency      VERIFIED — Local Gate #74 PASS
```

## Demo Showcase 已實作

九張 synthetic CSV 與三個固定 PTC showcase case 已完成。API：`/api/v1/demo/status`、`/api/v1/demo/cases`。首頁可切換 BRAF、RET、NTRK1 三病例並查看 Case → Variant → Evidence → Drug → Publication → Clinical Trial。

第三批新增跨頁 context：

```text
demo_case=<PTC-DEMO-xxx>&data_mode=synthetic
```

首頁現在提供 Recommendation、Clinical Decision、Treatment Plan、Knowledge Graph、PTC Workbench 深連結。Recommendation 已正式支援讀取 `demo_case`，自動帶入 synthetic Patient/Case key 與 variant，並顯示 Synthetic Demo Context provenance banner。

Clinical Decision / Treatment Plan / Knowledge Graph 目前已有 deep-link 入口，但各目的頁完整 hydrate 同一 context 尚待下一批。

## Local SQLite Workspace Hardening

本批新增 `src/backend/database/sqlite_workspace.py`：

- `check_sqlite_integrity()`：執行 `PRAGMA integrity_check`；
- `backup_sqlite_database()`：只允許完整 DB 進行 SQLite online backup，備份完成後再次 integrity check；
- `restore_sqlite_database()`：拒絕損壞 backup，先還原到 staging，再驗證完整性後 atomic replace 正式 DB。

新增 `tests/test_sqlite_workspace.py`，覆蓋：

- 建庫 / 寫入 / 關閉 / 重開後資料仍存在；
- backup snapshot；
- backup 後繼續修改正式 DB；
- restore 後回到 snapshot 狀態；
- restored DB integrity PASS；
- missing DB integrity failure；
- invalid backup restore rejection。

這代表 v0.3.0 的 local persistence / integrity / backup / restore 已從「設計缺口」進入「已有程式與永久 regression，等待 runner 驗證」。

## 驗證狀態

上一批最新 `master` gate：Local Verification Gate #84，head `19d60bbf...`，目前仍是 **pending**，尚無 runner job，因此不能宣告上一批 VERIFIED。本批最新程式與文檔同樣標記：

```text
IMPLEMENTED — WAITING FOR SELF-HOSTED VERIFICATION
```

不以 HTTP 200、程式已提交或測試檔存在取代真正 runner PASS。

## v0.3.0 Acceptance Gate

### Vercel Demo
- [x] 九張標準 synthetic CSV；
- [x] 3 個固定 demo cases；
- [x] CSV → SQLite idempotent bootstrap；
- [x] demo status/cases API；
- [x] Homepage selector + Evidence/Drug/Publication/Trial 展示；
- [x] 跨頁 `demo_case` deep-link contract；
- [x] Recommendation demo hydration；
- [ ] Clinical Decision / Treatment Plan / Knowledge Graph demo hydration；
- [ ] 共用 provenance banner；
- [ ] multi-route Chromium E2E；
- [ ] CSV schema / broken-link validator。

### Local SQLite
- [x] SQLite config / schema bootstrap / FK / busy timeout；
- [x] file persistence 基礎；
- [x] integrity utility；
- [x] backup utility；
- [x] atomic restore utility；
- [x] restart + backup/restore regression 已編寫；
- [ ] 最新 self-hosted runner PASS；
- [ ] workspace status API / CLI；
- [ ] local CSV import；
- [ ] pre-upgrade automatic backup hook；
- [ ] traceability persistence E2E。

## 下一批

下一批繼續完成 Demo context 全鏈與 Local Workspace release integration：Clinical Decision / Treatment Plan / Knowledge Graph hydrate、共用 DemoContextBanner、workspace status、pre-upgrade backup hook、CSV validator、multi-route Chromium E2E。

## 安全邊界

所有 synthetic demo 輸出只用於研究軟體流程展示，不代表真實醫學證據、患者資料、診斷或治療建議。v1.0 的 Research-Grade Stable 只描述軟體工程成熟度，不等同臨床有效性驗證。
