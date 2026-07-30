# Plan: Architecture Findings Validation Gate R1 — 證據補強計劃

> **目標**：補強 architecture_findings_validation.md 中 5 項 INSUFFICIENT EVIDENCE 和 6 項 PARTIALLY CONFIRMED 的驗證證據，使 Validation Gate 滿足「確認是否仍成立」的需求，評分從 78→目標 90+。
>
> **執行方式**：逐項執行驗證工具（grep / 檔案讀取 / git log），更新 architecture_findings_validation.md 中對應條目的 Status、當前證據、建議。

---

## 第一階段：補強 5 項 INSUFFICIENT EVIDENCE

### IE-1：P2-09 — Migration 017 trace_id UNIQUE 約束問題

**當前狀態**：INSUFFICIENT EVIDENCE — 需要深入檢查 migration 017 的具體 SQL

**驗證操作**：
1. 讀取 migration 017 檔案，檢查 upgrade/downgrade 中 trace_id 的 UNIQUE 約束定義
   - 路徑：`migrations/versions/` — 使用 glob 找到 `*017*` 或 `*trace_id*` 開頭的檔案
   - 重點：檢查 `create_unique_constraint` / `UniqueConstraint` / `sa.UniqueConstraint` 是否存在
2. 用 grep 在 `migrations/versions/` 目錄搜索 `trace_id` 確認約束使用模式
3. 讀取 migration 019 做比對（原始報告提到 017 與 019 類似問題）
4. 檢查 017 的 downgrade 是否正確移除 UNIQUE 約束（冪等性）

**證據記錄範例**：
```
**當前程式碼驗證：** 讀取 migrations/versions/XXXXXX_..._trace_id.py，發現 upgrade() 中 ...
第 XX 行使用 `op.create_unique_constraint(...)` 建立 trace_id UNIQUE 約束，
但 downgrade() 第 XX 行缺少對應的 `op.drop_constraint(...)`，導致 downgrade 不冪等。
```

**更新建議**：若確認問題仍存在 → `CONFIRMED`；若已修復 → `OUTDATED` + commit hash；若仍無法確認 → 記錄具體阻礙原因

---

### IE-2：R-L8 — 添加 409 Conflict 處理

**當前狀態**：INSUFFICIENT EVIDENCE — 未確認

**驗證操作**：
1. 用 grep 在 `src/backend/api/v1/` 目錄搜索所有 `@router.post` 和 `@router.put` 路由，檢查 `status_code` 參數
2. 特別檢查重複/衝突相關的 endpoint 是否有 409 處理：
   - 搜索 `HTTP_409_CONFLICT` / `status_code=409` / `Conflict` / `conflict`
3. 搜索 `services/` 目錄中是否已有 `raise Conflict` 或 `HTTPException(status_code=409)`
4. 搜索 `repositories/` 中是否有唯一約束衝突的捕獲邏輯（`IntegrityError` / `UniqueViolation`）

**證據記錄範例**：
```
**當前程式碼驗證：** grep 搜索 `status_code=409` 在 api/v1/ 下無結果。
grep 搜索 `HTTP_409_CONFLICT` 無結果。
grep 搜索 `IntegrityError` 在 repositories/ 下發現 ...（如有）。
確認所有 POST/PUT 路由均未設定 409 Conflict 處理邏輯。
```

**更新建議**：確認無 409 處理 → `CONFIRMED`（仍成立；尚未添加 409 處理）

---

### IE-3：R-L9 — 統一代碼標記/註釋語言

**當前狀態**：INSUFFICIENT EVIDENCE — 未確認

**驗證操作**：
1. 針對 `src/backend/` 目錄，用 grep 搜索中文註釋模式：
   - `// 中文` / `# 中文` / `"""中文` / `'''中文` — 使用正則表達式匹配常見中文字元
2. 搜索英文/中文註釋混雜情況：如 `// TODO:` vs `// 待辦：`
3. 搜索 `# Section` / `# 章節` / `# ===` 等標記性註釋的語言一致性
4. 搜索 `KnowGraphGo/` 目錄下的註釋語言一致性

**證據記錄範例**：
```
**當前程式碼驗證：** grep 搜索中文字元正則 `[\u4e00-\u9fff]` 在註釋行（`#.*` / `//.*`）中，
發現 src/backend/ 下 ... 個檔案包含中文註釋，KnowGraphGo/ 下 ... 個檔案包含中文註釋。
無統一語言規範的證據（部分英文、部分中文、部分雙語）。
```

**更新建議**：確認無統一規範 → `CONFIRMED`（仍成立）

---

### IE-4：RSK-11 — Recommendation Engine Exception 靜默吞沒

**當前狀態**：INSUFFICIENT EVIDENCE — 需確認 Engine 異常處理

**驗證操作**：
1. 讀取 `src/backend/clinical/recommendation_engine.py`，搜索所有 `except` 區塊
2. 檢查是否存在裸 `except:` / `except Exception:` 且沒有 logging 或 re-raise 的靜默吞沒模式
3. 特別關注 `run()` 方法（L440-715）內的異常處理邏輯
4. 搜索 `log.exception` / `logger.exception` / `traceback` 在 recommendation_engine.py 中的使用情況
5. 確認是否有 `try/except/pass` 模式

**證據記錄範例**：
```
**當前程式碼驗證：** recommendation_engine.py 中共有 ... 個 except 區塊。
其中第 ... 行 `except Exception:` 後僅 `pass` 無 logging（靜默吞沒）。
第 ... 行 `except:` 裸捕獲未記錄異常。
run() 方法內 ... 處異常被吞沒，未傳播上層。
```

**更新建議**：確認存在靜默吞沒 → `CONFIRMED`（風險成立）；若無 → `FALSE POSITIVE`（罕見）

---

### IE-5：（補充項）其他隱含 INSUFFICIENT EVIDENCE

若驗證過程中發現尚有其他項目驗證不足（如驗證報告中 Code Smell 部分僅一句話無具體證據的條目），一併補強行號、grep 命令、檔案大小等具體證據。

**操作**：對第四章 Code Smell 中以下僅一句話的條目補強證據：
- `God Class — TreatmentPlanService（57KB）`：補 ls 命令輸出
- `God Class — ClinicalAdapter（40KB）`：補 wc -l 或 ls 輸出
- `God File — report_generator.py（64KB）`：補 ls 命令輸出
- `Copy-Paste Patient Stub`：補 grep 命令輸出
- `Copy-Paste Evidence ID 去重`：補 grep 命令輸出

---

## 第二階段：補強 6 項 PARTIALLY CONFIRMED

### PC-1：P1-04 — Repository 型別註解不完整

**當前狀態**：PARTIALLY CONFIRMED — 部分 Repository 仍有型別註解缺失

**驗證操作**：
1. 逐個檔案檢查 `src/backend/repositories/` 下所有 22 個 `.py` 檔案的 `__init__` 方法
2. 記錄每個檔案的檢查結果：有/無 `AsyncSession` 型別註解
3. 創建清晰的清單表格：

| 檔案 | __init__ 參數 | 有 AsyncSession 註解？ |
|------|-------------|:--------------------:|
| base.py | `self, db` | ❌ 無 |
| xxx_repo.py | `self, db: AsyncSession` | ✅ 有 |
| ... | ... | ... |

4. 計算：X/22 個有完整註解，Y/22 個缺失

**證據記錄範例**：
```
**當前程式碼驗證：** 逐檔檢查 repositories/ 下 22 個 .py 檔案的 __init__ 方法：
- 有 AsyncSession 型別註解：12/22（如 recommendation_repo.py、clinical_decision_repo.py）
- 缺失 AsyncSession 型別註解：8/22（如 analysis_run_repo.py、specimen_repo.py、...）
- 不含 __init__（如 __init__.py）：2/22
```

**更新建議**：更新為 `CONFIRMED`（確認缺失的具體數字），或若全部已補則 `OUTDATED`

---

### PC-2：P1-09 — Migration SQLite/PostgreSQL 不一致

**當前狀態**：PARTIALLY CONFIRMED — 部分 Migration（如 015）已獲相容性修復

**驗證操作**：
1. 逐檔檢查原始報告提到的三個 migration：015、022、025
   - 檢查 downgrade() 函數是否存在且正確反轉 upgrade()
   - 檢查是否使用了 SQLite 不支援的操作（如 `ALTER COLUMN`、`DROP CONSTRAINT`）
2. 確認 015 的修復 commit 是否徹底解決了問題
3. 對比其他未報告的 migration 是否有類似問題

**證據記錄範例**：
```
**當前程式碼驗證：** 逐檔檢查：
- 015_xxx.py：downgrade() 第 XX 行仍缺少對應的 drop_constraint → 不冪等
- 022_xxx.py：downgrade() 完整，upgrade/downgrade 互為反操作 ✅
- 025_xxx.py：使用 `op.alter_column(...)` 在 SQLite 下不支援 ❌
```

**更新建議**：根據檢查結果決定 → 若全部已修復 `OUTDATED`；若部分仍存在 `CONFIRMED`

---

### PC-3：R-L4 — 補充 Repository 型別註解

**當前狀態**：PARTIALLY CONFIRMED（與 P1-04 重疊但視角不同）

**注意**：此項與 P1-04 是同一組驗證（Repository 型別註解），合併執行。

**驗證操作**：同 PC-1（P1-04），但著重於 Refactor LOW 視角的建議（補充 3h 工時估算是否有變）

**更新建議**：`CONFIRMED` 或 `OUTDATED`（與 P1-04 保持一致）

---

### PC-4：R-L6 — 修正 Migration 不冪等（PARTIALLY OUTDATED）

**當前狀態**：PARTIALLY OUTDATED — 部分已修正（015）

**驗證操作**：
1. 同 PC-2（P1-09）的 migration 檢查方法
2. 額外檢查其他未在原始報告中提到的 migration 版本
3. 重點確認 013 的冪等性修復 commit（`264dedb`）是否完整

**證據記錄範例**：
```
**當前程式碼驗證：** 基於 PC-2 的完整 migration 掃描：
- 已修復：013（冪等性）、015（SQLite compat）
- 仍有問題：017（downgrade 不冪等）、025（SQLite ALTER COLUMN）
```

**更新建議**：若發現更多已修復 → `OUTDATED`；若仍有大量未修復 → `CONFIRMED`

---

### PC-5：R-L10 — 補上 Missing Unit Tests（PARTIALLY CONFIRMED）

**當前狀態**：PARTIALLY CONFIRMED — Phase 3D 已加 e2e 但 StateMachine 等仍缺

**驗證操作**：
1. 搜索 `test_treatment_plan_state_machine.py` 是否存在於 `tests/` 目錄
2. 搜索 `tests/` 下所有測試檔案，檢查是否有針對 TreatmentPlanStateMachine 的單元測試
3. 列舉原始報告提到的缺測試項目，逐項確認：
   - TreatmentPlanStateMachine（P2-11）— 原始確認無測試
   - ClinicalDecisionEngine Trace（R-L3）
   - 其他 Engine 單元測試
4. 確認 Phase 3D 補的 e2e 測試涵蓋哪些範圍

**證據記錄範例**：
```
**當前程式碼驗證：**
- TreatmentPlanStateMachine 單元測試：❌ 不存在
- ClinicalDecisionEngine Trace 測試：❌ 不存在
- KnowGraphGo CLI e2e 測試：✅ 存在（Phase 3D）
- 原始報告提到的 ... 項缺失測試中 ... 項仍缺失
```

**更新建議**：更新缺失測試的精確數量 → `CONFIRMED`（精確化）

---

### PC-6：RSK-08 — Migration 不冪等導致生產環境升降級失敗（PARTIALLY OUTDATED）

**當前狀態**：PARTIALLY OUTDATED — 部分已修復（015 SQLite compat）

**注意**：此項與 P1-09 / R-L6 是同一組問題的 Risk List 視角，合併執行 Migration 全面掃描。

**驗證操作**：同 PC-2（P1-09）+ PC-4（R-L6）的完整 migration 掃描結果

**更新建議**：與 P1-09 和 R-L6 的檢查結果保持一致

---

## 第三階段：彙總與更新

1. 將所有更新後的 Status 寫入 architecture_findings_validation.md
2. 更新最終統計表（CONFIRMED / PARTIALLY CONFIRMED / OUTDATED / INSUFFICIENT EVIDENCE 數量）
3. 更新佔比分析與關鍵結論
4. 提交更新後的 architecture_findings_validation.md 供 REVIEWER 重新評分

### 預期評分提升

| 評分項 | 當前 | 預期 | 關鍵改善 |
|-------|:---:|:---:|---------|
| 完整性 | 9/10 | 9-10/10 | INSUFFICIENT EVIDENCE 降為 0 或 ≤2 |
| 正確性 | 24/25 | 24-25/25 | 補充精確的逐檔清單 |
| 可維護性 | 23/25 | 23-24/25 | Code Smell 證據補強 |
| 測試與驗證 | 22/25 | 23-24/25 | 所有驗證有具體 grep/讀檔記錄 |
| **總分** | **78/100** | **88-95/100** | 目標 ≥90 合格 |

---

## 執行順序建議

```
Phase 1：IE-1 (P2-09) Migration 017 檢查
Phase 2：IE-4 (RSK-11) Engine Exception 檢查
         IE-2 (R-L8) 409 Conflict 檢查
Phase 3：IE-3 (R-L9) 註釋語言檢查
         IE-5 Code Smell 證據補強
Phase 4：PC-1/PC-3 (P1-04 + R-L4) Repository 型別註解全面清單
         PC-2/PC-4/PC-6 (P1-09 + R-L6 + RSK-08) Migration 全面掃描
Phase 5：PC-5 (R-L10) Missing Unit Tests 確認
Phase 6：彙總更新 + 統計表刷新
```

---

*計劃完成 — 請按 Phase 順序執行，每完成一項用 complete_step 簽收。*
