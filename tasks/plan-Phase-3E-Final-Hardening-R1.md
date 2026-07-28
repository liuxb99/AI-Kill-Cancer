# Phase 3E Final Hardening — 返工修正計劃 R1

> 基於評分報告（70/100，不合格）的兩項關鍵缺失，針對性修正。  
> 原始計劃：`tasks/plan-Phase-3E-Final-Hardening.md`  
> 評分報告：`tasks/reviews/review_Phase-3E-Final-Hardening_0.md`  

---

## 評分缺失摘要

| 缺失 | 違反需求 | 權重 | 說明 |
|------|---------|------|------|
| **M1**: migration-gate job 未執行 `pytest tests/test_migration_gate.py` | P0-3 | 20% | CI 中缺少 pytest 執行步驟，`test_migration_gate.py` 被閒置 |
| **M2**: Integration tests (`test_migration_025_pg_*.py`) 在 backend job 使用共用資料庫 `cancer_db` | P0-4 | 20% | 違反 Migration Gate 與 Integration Test 隔離原則 |

其餘項目（Migration 025 邏輯、測試程式碼、SQLite 相容性）均通過審查，無需修正。

---

## 修正方案

### 核心策略

```
M1 + M2 合併解決方案：
┌─────────────────────────────────────────────────────────┐
│  backend job                   migration-gate job       │
│  ┌─────────────────────┐       ┌──────────────────────┐ │
│  │ Test with pytest    │       │ pytest (隔離 DB)     │ │
│  │ (排除 pg_migration  │       │ ├ test_migration_gate│ │
│  │  025 tests)         │       │ ├ integration/025_pg │ │
│  │ 使用 cancer_db      │       │ │  *.py              │ │
│  └─────────────────────┘       │ 使用 cancer_db_      │ │
│                                 │   migration_gate     │ │
│                                 └──────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

**要點**：
1. `backend` job 的 pytest 排除 `tests/integration/test_migration_025_pg_*.py`
2. `migration-gate` job 新增 pytest 步驟，執行 `test_migration_gate.py` + `tests/integration/test_migration_025_pg_*.py`
3. 所有 PostgreSQL migration 相關測試均在隔離資料庫 `cancer_db_migration_gate` 上執行
4. 可考慮移除 migration-gate job 中的 inline Python schema validation 步驟（因其邏輯已被 pytest 涵蓋，但保留也無害）

---

### 具體修改

#### 修改 1：`.github/workflows/ci.yml` — backend job 的 `Test with pytest` 步驟

**當前**（第 62-65 行）：
```yaml
      - name: Test with pytest
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/cancer_db
        run: pytest -v --tb=short --cov=src/backend --ignore=tests/integration/test_migration_016.py tests/unit/ tests/integration/
```

**問題**：`tests/integration/` 包含 `test_migration_025_pg_*.py`，這些測試在共用資料庫上執行。

**修正後**：
```yaml
      - name: Test with pytest
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/cancer_db
        run: pytest -v --tb=short --cov=src/backend \
          --ignore=tests/integration/test_migration_016.py \
          --ignore=tests/integration/test_migration_025_pg_trace_constraint.py \
          --ignore=tests/integration/test_migration_025_pg_schema_compare.py \
          --ignore=tests/integration/test_migration_025_pg_full_cycle.py \
          tests/unit/ tests/integration/
```

或者使用目錄排除更簡潔：
```yaml
          --ignore=tests/integration/test_migration_016.py \
          -k "not pg_migration_025" \
          tests/unit/ tests/integration/
```

但最穩妥的方式是明確 ignore 那三個檔案。

---

#### 修改 2：`.github/workflows/ci.yml` — migration-gate job 新增 pytest 步驟

**當前**：migration-gate job 有 "Migration schema validation (PostgreSQL)" 步驟（第 252-297 行），使用 inline Python 做 constraint 驗證，但**沒有執行 pytest**。

**修正**：在「Migration verify」之後、「Downgrade 024」之前，加入 pytest 步驟：

```yaml
      - name: Run Migration Gate tests (pytest)
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/cancer_db_migration_gate
          PYTHONPATH: .
        run: |
          pytest -v --tb=short tests/test_migration_gate.py \
            tests/integration/test_migration_025_pg_trace_constraint.py \
            tests/integration/test_migration_025_pg_schema_compare.py \
            tests/integration/test_migration_025_pg_full_cycle.py
```

**放置位置**：在「Migration verify」（alembic check）之後，但在「Downgrade 024」之前。這樣 pytest 在 upgrade head 後的 schema 上執行，驗證 composite unique constraints、foreign keys 等。

**關於 inline Python schema validation 步驟**：該步驟（第 252-297 行）的邏輯與 `test_migration_gate.py::test_composite_unique_constraints_exist` 和 `test_foreign_keys_exist` 重複。可選方案：

- **方案 A（推薦）**：保留 inline Python 步驟不改，直接在其後追加 pytest 步驟。雙重驗證無害。
- **方案 B**：移除 inline Python 步驟，完全由 pytest 取代。更簡潔，但需確認 pytest 涵蓋所有斷言。

本計劃採用**方案 A**（最小改動原則），僅新增 pytest 步驟，不動現有 inline 驗證。

---

#### 修改 3（可選）：`test_migration_gate.py` 檢查 conftest 中的 `pg_engine` fixture

確認 `test_migration_gate.py` 使用的 `pg_connection` 和 `alembic_runner` fixtures 來自 `tests/conftest.py`（第 161-205 行），這些 fixtures 從 `DATABASE_URL` 環境變數取得連線。在 migration-gate job 中 `DATABASE_URL` 指向 `cancer_db_migration_gate`，因此 pytest 會自動使用隔離資料庫。✅ 無需修改。

---

### 修改後 CI 流程對照

#### backend job（變更部分）

| 步驟 | 資料庫 | 變更 |
|------|--------|------|
| Test with pytest | `cancer_db` | 排除 `test_migration_025_pg_*` |
| （其餘步驟不變） | ... | 無 |

#### migration-gate job（完整流程）

| 步驟 | 資料庫 | 說明 |
|------|--------|------|
| Create isolated database | — | `createdb cancer_db_migration_gate` ✅ |
| Upgrade head | `cancer_db_migration_gate` | `alembic upgrade head` ✅ |
| Migration verify | `cancer_db_migration_gate` | `alembic check` ✅ |
| Migration schema validation (inline Python) | `cancer_db_migration_gate` | 保留不變 ✅ |
| **Run Migration Gate tests (pytest)** 🆕 | `cancer_db_migration_gate` | **新增**：執行 `test_migration_gate.py` + `test_migration_025_pg_*.py` |
| Downgrade 024 | `cancer_db_migration_gate` | `alembic downgrade 024` ✅ |
| Re-upgrade head | `cancer_db_migration_gate` | `alembic upgrade head` ✅ |
| Final verify | `cancer_db_migration_gate` | `alembic check` ✅ |
| Drop migration gate database | — | `dropdb ...` ✅ |

---

### 預期效益（對應評分缺失）

| 缺失 | 修正後狀態 | 分數影響 |
|------|-----------|---------|
| M1: CI 缺少 pytest 步驟 | ✅ migration-gate job 執行 `pytest tests/test_migration_gate.py` | 完整性 +10→18/25 |
| M2: Integration tests 使用共用資料庫 | ✅ `test_migration_025_pg_*.py` 在 migration-gate job 的隔離資料庫執行 | 測試與驗證 +5→23/25 |
| 預期總分 | **70 → 約 85+**（需第二次 reviewer 評分確認） | |

> **注意**：即使修正 M1+M2，預估分數約 85-90 分。若需達到 ≥95，可能需額外改進（如文件補齊、交付清單完整填寫等）。建議修正後提交 reviewer 再次評分。

---

## 執行順序

### Batch R1：CI YAML 修正（唯一需要修改的檔案）

| ID | 名稱 | 描述 | 依賴 | 預估工時 |
|----|------|------|------|---------|
| R1-01 | **backend job 排除 migration 025 integration tests** | 在 `Test with pytest` 步驟中加入 `--ignore` 排除三個 `test_migration_025_pg_*.py` 檔案 | 無 | 10min |
| R1-02 | **migration-gate job 新增 pytest 步驟** | 在「Migration schema validation」之後加入 pytest 執行步驟，使用 `cancer_db_migration_gate` 資料庫 | R1-01 | 15min |
| R1-03 | **CI YAML 語法驗證** | 確認 YAML 格式正確、無縮排錯誤 | R1-02 | 5min |

### Batch R2：驗證

| ID | 名稱 | 描述 | 依賴 | 預估工時 |
|----|------|------|------|---------|
| R2-01 | **本地 YAML lint 驗證** | 使用 `yamllint` 或 GitHub Actions 驗證 CI YAML 語法 | R1-03 | 5min |
| R2-02 | **提交 PR 或 push 觸發 CI** | 推送變更到分支，觀察 CI 運行 | R2-01 | — |
| R2-03 | **驗證 CI Run 結果** | 確認 migration-gate job 中 pytest 步驟 PASS，backend job 無 migration 025 測試被排除後仍全部 SUCCESS | R2-02 | 30min |
| R2-04 | **提交 reviewer 二次評分** | 更新交付清單後請 reviewer 重新評分 | R2-03 | 15min |

---

## 預計修改檔案清單

| 檔案 | 修改類型 | 說明 |
|------|---------|------|
| `.github/workflows/ci.yml` | 修改 | backend job 排除 migration 025 tests + migration-gate job 新增 pytest 步驟 |

僅此一個檔案需要修改。測試程式碼和 Migration 025 邏輯均無需變動。

---

## 風險與應對

| 風險 | 可能性 | 影響 | 應對 |
|------|--------|------|------|
| pytest 步驟使用 `cancer_db_migration_gate` 但 conftest.py 的 `pg_engine` fixture 解析 `DATABASE_URL` 時使用 sync driver，可能與 async driver 不匹配 | 低 | pytest 失敗 | `pg_engine` fixture 已正確處理 `+asyncpg` → `+psycopg2` 轉換（conftest.py 第 172-176 行），無需擔心 |
| `test_migration_gate.py` 的 `test_upgrade_head_success` 在 upgrade head 後再次執行 upgrade head，可能報錯 | 低 | pytest 失敗 | `alembic upgrade head` 是冪等的，已處於 head 時再次執行會提示 "already at head" 但不會失敗 |
| 排除 migration 025 tests 後 backend job 的 `--cov` 涵蓋率下降 | 低 | 覆蓋率報告變化 | 不影響測試正確性；migration 025 測試在 migration-gate job 中仍有執行 |
| 新增 pytest 步驟使 migration-gate job 延長約 1-2 分鐘 | 低 | CI 總時間增加 | 在可接受範圍內 |

---

## 交付驗收清單（更新後）

| # | 交付物 | 狀態 |
|---|--------|------|
| 1 | Commit SHA | ⏳ 待提交 |
| 2 | Files Changed | ✅ 僅 `.github/workflows/ci.yml` |
| 3 | Migration 025 修改內容 | ✅ 本次無變更（此前已通過審查） |
| 4 | 新增 PostgreSQL Tests | ✅ 已存在（本次無變更） |
| 5 | 新增 CI Tests | ✅✅ **已修正**：`test_migration_gate.py` 將在 CI 中執行 |
| 6 | Run ID | ⏳ 需實際 CI 運行 |
| 7 | Backend 結果 (SUCCESS) | ⏳ 需實際 CI 運行 |
| 8 | Frontend 結果 (SUCCESS) | ✅ 沿用（本次無 frontend 變更） |
| 9 | Migration Verification (PASS) | ✅ 已存在 |
| 10 | Migration Tests (PASS) | ✅✅ **已修正**：pytest 步驟將執行 migration tests |
| 11 | Downgrade (PASS) | ✅ 已存在 |
| 12 | Re-upgrade (PASS) | ✅ 已存在 |
| 13 | Schema Compare (PASS) | ✅ 已存在 |
| 14 | git status | ⏳ 待提交 |
| 15 | Reviewer Score (>=95) | ⏳ 待第二次評分 |

---

## 最終驗收條件

- [ ] Backend SUCCESS（backend job 全部 PASS）
- [ ] migration-gate job SUCCESS（含新增的 pytest 步驟）
- [ ] Frontend SUCCESS
- [ ] Migration Verification PASS
- [ ] Migration Tests PASS（`test_migration_gate.py` 在 CI 中執行 ✅）
- [ ] Upgrade PASS
- [ ] Downgrade PASS
- [ ] Re-upgrade PASS
- [ ] Schema Compare PASS
- [ ] Reviewer Score >= 95

> **本計劃僅針對評分缺失修正，不涉及任何業務功能、Engine、API、Frontend 修改。**

---

*計劃版本：R1（返工版），基於評分報告 review_Phase-3E-Final-Hardening_0.md 的兩項缺失修正。*
