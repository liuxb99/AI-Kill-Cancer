# AI-Kill-Cancer 本地 SQLite 相容模式

更新日期：2026-08-09

狀態：`IMPLEMENTED — WAITING FOR SELF-HOSTED VERIFICATION`

## 定位

AI-Kill-Cancer 正式支援兩種資料庫執行模式：

```text
PostgreSQL
→ production / 完整 migration / 正式部署權威

SQLite
→ local / demo / research / Windows self-hosted verification
```

SQLite 是本地開發與單機研究模式，不取代 PostgreSQL 的 production 權威。

## 啟用方式

最簡單的本地設定：

```powershell
$env:APP_MODE = 'research'
$env:DB_BACKEND = 'sqlite'
$env:SQLITE_PATH = './data/ai-kill-cancer.db'
$env:MODEL_ENABLED = 'false'
python -m uvicorn src.backend.main:app --host 127.0.0.1 --port 8000
```

也可直接給完整 URL：

```powershell
$env:DATABASE_URL = 'sqlite+aiosqlite:///./data/ai-kill-cancer.db'
```

若 `DATABASE_URL` 已明確設定，它優先於 `DB_BACKEND / SQLITE_PATH`。

## 已實作的 SQLite policy

`src/backend/database/session.py` 對 SQLite 採獨立 policy：

1. 檔案型 SQLite 自動建立父目錄；
2. 每個 SQLite connection 強制 `PRAGMA foreign_keys=ON`；
3. 設定 `PRAGMA busy_timeout=5000`，降低短暫鎖競爭造成的立即失敗；
4. `:memory:` 使用 `StaticPool`，避免不同 session 取得不同空白 in-memory database；
5. `init_db()` 會載入核心 domain 與 PTC extension ORM metadata，再執行 `Base.metadata.create_all()`；
6. 初始化後立即驗證 foreign-key enforcement；
7. `close_db()` 會同時清除 engine 與 session factory，允許測試/本地程序安全重新初始化不同 DB URL。

## 不得回退的邊界

- `APP_MODE=production` 不允許 SQLite；production 必須使用 PostgreSQL。
- PostgreSQL Alembic migration chain 仍是正式 schema evolution 權威。
- SQLite 本地模式使用 ORM metadata 建立當前 schema；不要把 SQLite migration 結果宣稱為 PostgreSQL migration parity。
- 不可為了 SQLite 相容而降低 FK、transaction 或 audit 約束。
- SQLite 不用來模擬 PostgreSQL-specific locking / concurrency / service-container 行為。

## 永久 regression

新增：

```text
tests/backend/test_sqlite_local_compat.py
```

目前鎖定：

- file DB parent directory 自動建立；
- ORM insert → close session → reopen session → read round-trip；
- SQLite FK enforcement；
- invalid FK 必須拋出 `IntegrityError`；
- in-memory schema 跨 session 保留；
- file / memory URL builder。

原專案既有 `tests/test_analysis_persistence.py` 已使用 `sqlite+aiosqlite://` + `Base.metadata.create_all()` 驗證 Analysis Job persistence，證明 ORM 層本來已有局部 SQLite 基礎；本段把它提升為正式 runtime contract。

## Self-hosted Action

新增：

```text
.github/workflows/sqlite-local.yml
```

觸發：

```text
push master
pull_request master
workflow_dispatch
```

Runner：

```text
[self-hosted, Windows, X64, ai-ci]
```

Action 會：

```text
install backend deps
→ compile database/domain layer
→ run SQLite compatibility regression
→ 用 Settings(DB_BACKEND=sqlite) 實際 init_db
→ 驗證 .ci/ai-kill-cancer.db 真實產生且非空
→ git diff --check
```

## 驗證狀態

目前 production code、永久 regression 與 self-hosted workflow 均已提交。

在 Windows self-hosted Action 成功前，狀態維持：

```text
IMPLEMENTED — WAITING FOR SELF-HOSTED VERIFICATION
```
