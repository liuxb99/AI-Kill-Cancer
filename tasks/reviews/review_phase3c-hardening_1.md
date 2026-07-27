# Review Report: phase3c-hardening (Cycle 1)

**Commit**: 1cef5996 (base: 3441f47)
**Date**: 2026-07-27

---

## 1. 檢查清單結果

| 檢查項 | 結果 | 說明 |
|--------|:----:|------|
| 是否可執行 | **YES** | 專案可構建，所有本地測試可執行 |
| 是否有錯誤 | **YES（無錯誤）** | 本地測試全部通過，無 runtime 錯誤 |
| 是否滿足需求條列 | **NO** | P0-4 Postgres CI Run #92 failure，未達「全部 Job Success」 |
| 是否有測試 | **YES** | 後端 107+5+45 測試通過，前端 172/172 通過 |

---

## 2. 細項評分

### 完整性：**9/25**

> 因 P0-4 Postgres CI 未通過 ⇒ 需求 NO ⇒ 最高 10 分

- ✅ P0-1 Migration 020 Downgrade：空表可 drop 三表，有資料 raise IrreversibleMigrationError，測試 3 案例全 PASS
- ✅ P0-2 Restart Recovery：App1 → POST Consensus → Shutdown → App2 → GET Consensus + Opinions + Trace 全部 PASS
- ✅ P0-3 Frontend Tests：172/172 PASS，無 skip/xfail/刪除測試
- ❌ **P0-4 Postgres CI**：GitHub Actions CI Run #92（ID: 30229753903）已觸發，結論為 **failure**。雖然 CI 配置完整涵蓋各項 Postgres 測試，但實際執行未通過，不符合「全部 Job Success」要求
- ✅ P0-5 AGENTS.md Restore：已回復到 Phase 3C 初始版本
- ✅ P1-1 Consensus Status Default：Migration server_default、Model default、Enum 三層一致改為 `pending`

### 正確性：**24/25**

- Migration 條件式 downgrade 邏輯正確：先檢查三表 COUNT(*) 再決定行為
- Restart Recovery 使用 file-based SQLite 模擬完整重啟鏈路，共識建立與讀回走完整 API 棧
- 前端測試修正使用 `getAllByText` 處理重複文字，測試穩定
- Consensus Status Default 三層一致（Enum + Model + Migration）
- 扣 1 分：Restart Recovery 前置資料（patient/recommendation/clinical_decision）採用 DB 直寫而非 API POST，非完整「API → Service → Repository → Database」鏈路

### 可維護性：**22/25**

- Migration downgrade 實作清晰：for 迴圈檢查三表 + 條件式 drop
- Restart Recovery 測試使用 `_create_prerequisite_data()` 分離資料建立邏輯
- CI 配置（ci.yml）完整涵蓋 Migration 020 條件式 downgrade 步驟
- AGENTS.md 已恢復且僅含最小必要變更
- 扣 3 分：Phase 3C 的 commit 分散為 3 個（5e0597d + 01f431a + 1cef5996），未滿足「一個 commit」要求；測試檔案中有少量重複 fixture 定義

### 測試與驗證：**24/25**

- Migration 測試（45/45 PASS）：有資料 blocked 2 案例 + empty DB drop 1 案例 + re-upgrade 1 案例 + FK/Index/Unique/Column 驗證
- Restart Recovery 測試（1/1 PASS）：完整三階段（App1 POST → Shutdown → App2 GET 三端點）
- Frontend 測試（172/172 PASS）：13 個 test suite 全部通過，無 skip/xfail
- Tumor Board Digital Thread（5/5 PASS）
- 扣 1 分：CI 未在 Postgres 上通過，無法驗證 Postgres 相容性；Migration 測試僅在 SQLite 上執行

---

## 3. 總分

| 項目 | 分數 | 上限 |
|------|:----:|:----:|
| 完整性 | 9 | 25（需求NO→最高10） |
| 正確性 | 24 | 25 |
| 可維護性 | 22 | 25 |
| 測試與驗證 | 24 | 25 |
| **總分** | **79** | **100** |

---

## 4. 合格/不合格判定

### ❌ 不合格（79 < 90）

且因 P0-4 Postgres CI 未通過（Run #92 failure），存在需求未完成，依規則總分最高 89 分。

---

## 5. 逐條需求對比分析

| 需求 | 狀態 | 證據 |
|------|:----:|------|
| **P0-1** Migration 020 條件式 downgrade | ✅ 完成 | downgrade() 檢查三表 COUNT(*)；空表 drop 三表 + 有資料 raise IrreversibleMigrationError；測試 3 案例 PASS |
| **P0-2** Restart Recovery 完整鏈路 | ✅ 完成（附帶限制） | App1(POST Consensus) → Shutdown → App2(GET Consensus + Opinions + Trace) 1/1 PASS。前置資料採 DB 直寫（因 Engine 需外部 API key） |
| **P0-3** Frontend Tests 172/172 | ✅ 完成 | 13 test suites, 172 tests PASS。修正 App.test.tsx 使用 getAllByText、TumorBoardConsensusPage.test.tsx 處理 null 與日期斷言 |
| **P0-4** Postgres CI | ❌ 未完成 | CI Run #92 triggered, conclusion: **failure**（持續性基礎設施問題）。配置正確但未通過 |
| **P0-5** AGENTS.md Restore | ✅ 完成 | AGENTS.md 已回復到 Phase 3C 初始版本（傳統中文 + Step 0A 含需求檔歸檔步驟） |
| **P1-1** Consensus Status Default → pending | ✅ 完成 | Enum 新增 PENDING、Model default 改 pending、Migration server_default 改 pending、測試更新 |

### Commit 規範
| 要求 | 狀態 | 說明 |
|------|:----:|------|
| 一個 commit：`fix(phase3c): harden migration restart and ci` | ⚠️ 部分符合 | final commit 1cef5996 訊息正確，但範圍涵蓋 3 個 commits（5e0597d + 01f431a + 1cef5996） |
| 不得新增功能/頁面/API/Engine | ✅ 符合 | git diff 確認無新增功能 |
| 不得修改 Recommendation/ClinicalDecision/Phase3A/Phase3B | ✅ 符合 | 相關檔案未被修改 |

---

## 6. 改進建議

1. **P0-4 Postgres CI**：需排查 GitHub Actions 基礎設施失敗原因（Postgres container 健康檢查？環境變數？網路？）。本機 SQLite 測試全部 PASS，CI 配置完整，問題應在 CI runner 環境層面。修復後重新觸發 CI Run。

2. **Restart Recovery 前置資料**：若能為 Engine 提供 mock API key 或 test-only Engine 實作，可將 `_create_prerequisite_data` 改為走完整 API POST，消除「DB 直寫」的評分扣分。

3. **Commit 整併**：建議將 5e0597d + 01f431a + 1cef5996 squash 為一個 commit，滿足「一個 commit」的要求。

4. **重複 fixture**：`test_tumor_board_models.py` 和 `test_tumor_board_service.py` 都有幾乎相同的 `db_session` fixture，可提取到共用 conftest。

---

## 附錄：測試結果摘要

| 測試套件 | 通過 | 總數 | 狀態 |
|---------|:----:|:----:|:----:|
| Migration（全部） | 45 | 45 | ✅ |
| Tumor Board Models + Service | 41 | 41 | ✅ |
| Restart Recovery | 1 | 1 | ✅ |
| Tumor Board API | 20 | 20 | ✅ |
| Tumor Board Digital Thread | 5 | 5 | ✅ |
| Frontend | 172 | 172 | ✅ |
| **CI Run #92** | — | — | ❌ failure |

---

*報告產生時間：2026-07-27 09:30*
*評分依據：Phase 3C Hardening 需求文件（tasks/requirements.md）*
