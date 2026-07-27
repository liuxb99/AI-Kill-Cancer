# Review Report: phase3c-hardening (Cycle 0)

## 檢查清單
- 是否可執行：YES
- 是否有錯誤：YES（無錯誤）
- 是否滿足需求：YES（所有硬化範圍需求已滿足，P0-4 CI 配置已更新但因環境限制無法執行）
- 是否有測試：YES

## 細項評分
- 完整性：24/25
- 正確性：25/25
- 可維護性：24/25
- 測試與驗證：23/25

## 總分：89/100
## 判定：不合格

## 詳細說明

### 一、已驗證的交付成果

| # | 項目 | 狀態 | 驗證方式 |
|---|------|------|---------|
| P0-1 | Migration 020 條件式 downgrade | ✅ | 空資料庫正常 drop 三表，有資料 raise IrreversibleMigrationError。diff 確認 downgrade() 已從 always-raise 改為先檢查 COUNT(*) 再決定行為。 |
| P0-2 | Restart Recovery | ✅ | test_tumor_board_restart_recovery.py 1/1 PASS。改用 DB 直寫前置資料（patient → recommendation → clinical decision），不再依賴外部 API。 |
| P0-3 | Frontend Tests | ✅ | `npm test` 172/172 PASS（13 test suites, 172 tests）。4 項原本失敗的測試已修正：App.test.tsx 使用 `getAllByText` 避免重複文字衝突，TumorBoardConsensusPage.test.tsx 修正 null consensus 處理與日期斷言。 |
| P0-4 | Postgres CI | ⚠️ | CI 配置已更新（.github/workflows/ci.yml 涵蓋條件式 downgrade 步驟：先 insert data 驗證 blocked，再 delete data 驗證 empty DB drop 成功）。因本環境無 GitHub Actions，無法實際執行 Postgres CI。 |
| P0-5 | AGENTS.md Restore | ✅ | AGENTS.md 已還原上一輪修改，diff 顯示僅保留最小必要變更。 |
| P1-1 | Consensus Status Default | ✅ | Migration server_default 從 `"unanimous"` → `"pending"`（diff 確認）；Model default 從 `"unanimous"` → `"pending"`（diff 確認）；Enum 新增 `PENDING = "pending"`（diff 確認）。 |

### 二、測試結果彙總

| 測試套件 | 通過 | 總數 | 狀態 |
|---------|:----:|:----:|:----:|
| Migration（全部） | 45 | 45 | ✅ |
| Migration 020（Phase 3C） | 14 | 14 | ✅ |
| Restart Recovery | 1 | 1 | ✅ |
| Frontend | 172 | 172 | ✅ |

### 三、細項評分說明

**完整性（24/25）**
- 所有硬化範圍需求均已滿足：
  - P0-1：條件式 downgrade（空表 drop / 有資料 blocked）
  - P0-2：Restart Recovery 完整鏈路（App1 → POST → Shutdown → App2 → GET）
  - P0-3：Frontend 172/172 全線回歸
  - P0-5：AGENTS.md 已還原
  - P1-1：Consensus Status Default 改為 pending
- P0-4 Postgres CI 已更新配置但無法在本環境執行（環境限制，非實作缺失）
- 扣 1 分：CI 無法完全驗證

**正確性（25/25）**
- 所有測試通過，無任何錯誤
- Migration 條件式 downgrade 邏輯正確（先檢查三表 COUNT(*)）
- Restart Recovery 使用 DB 直寫前置資料，正確模擬完整鏈路
- Frontend 測試全數通過（無 skip/xfail/刪測試）
- Consensus Status Default 正確改為 pending（server_default + Model default + Enum）
- CI 配置中的條件式 downgrade 腳本邏輯正確（先 insert → 驗證 blocked → delete → 驗證 empty drop）

**可維護性（24/25）**
- 條件式 downgrade 實作清晰簡潔（for 迴圈檢查三表 + 條件式 drop）
- Restart Recovery 測試改用 `_create_prerequisite_data()` 分離資料建立邏輯
- Frontend 測試修正使用 `getAllByText` 處理重複文字，提高測試穩定性
- Consensus Status Default 從 Enum → Model → Migration 三層一致
- 扣 1 分：AGENTS.md 尚有少量簡體中文殘留（不影響功能）

**測試與驗證（23/25）**
- Migration 測試涵蓋完整：有資料 blocked（2 案例）+ empty DB drop（1 案例）+ re-upgrade（1 案例）+ FK/Index/Unique/Column 驗證
- Restart Recovery 測試從 0/1 → 1/1，已可獨立執行
- Frontend 測試從 168/172 → 172/172，未 skip/xfail/刪測試
- CI 未在 Postgres 上實際執行，無法驗證 Postgres 相容性（扣 2 分）

### 四、限制條件

根據 §20 規則：
> 「沒有 GitHub Actions 則 Reviewer 不得 >89」

本環境無法執行 GitHub Actions Postgres CI，因此最終評分強制上限為 **89/100**。

### 五、總評

本次 hardening 成功達成所有目標：
1. ✅ Migration 020 downgrade 從 always-blocked 改為條件式（空表可 drop）
2. ✅ Restart Recovery 脫離外部 API 依賴，使用 DB 直寫，測試通過
3. ✅ Frontend 全線回歸 172/172
4. ✅ AGENTS.md 已還原
5. ✅ Consensus Status Default 三層一致改為 pending
6. ✅ CI 配置已更新條件式 downgrade

但因 §20 規則限制（CI 未在 GitHub Actions 執行），**最終評分 89/100，判定不合格**。若後續在 GitHub Actions Postgres CI 上全線通過，可重新評分 ≥95 後標記 Accepted。

---

*報告產生時間：2026-07-26*
*評分規則：§20（CI 未通過最高 89）*
