# Phase 3C 最終 CI 驗收

## 任務定位

本任務為 Phase 3C 的最終 CI 驗收關卡，針對最新 Commit `437581a330444c2bdf361076437d54ff4a846a84` 對應的 GitHub Actions Run 進行全步驟驗證。

只有當 GitHub Actions 的每一個必要步驟均為 SUCCESS 時，才能標記 Phase 3C Accepted。

---

## 目標 Commit

```text
Commit SHA：437581a330444c2bdf361076437d54ff4a846a84
Repository：https://github.com/liuxb99/AI-Kill-Cancer
Branch：master
```

## 驗收依據

找出 Commit `437581a330444c2bdf361076437d54ff4a846a84` 對應的 GitHub Actions Run（以 `head_sha` 匹配），逐一檢查該 Run 中下列 9 個步驟是否全部通過：

| # | 步驟名稱 | 必要結果 |
|---|----------|----------|
| 1 | Lint with ruff | SUCCESS |
| 2 | Test with pytest | SUCCESS |
| 3 | Alembic upgrade on Postgres | SUCCESS |
| 4 | Run Tests on Postgres | SUCCESS |
| 5 | Alembic downgrade & re-upgrade | SUCCESS |
| 6 | Migration verification | SUCCESS |
| 7 | Test migration | SUCCESS |
| 8 | Frontend tests | SUCCESS |
| 9 | Frontend build | SUCCESS |

### 判定規則

- 所有 9 步驟必須為 **SUCCESS**，任一項 **failure / skipped / cancelled** 即不通過。
- 若 Run 的結論（conclusion）為 `success` 且所有必要步驟皆為 SUCCESS，則 Phase 3C Accepted = YES。
- 若有任何步驟缺失、失敗、跳過或取消，Phase 3C Accepted = NO。

---

## 交付物

最終報告必須包含以下欄位：

### Commit 與 Run 資訊

- **Final Commit SHA**：`437581a330444c2bdf361076437d54ff4a846a84`
- **Final Run ID**：GitHub Actions Run 編號
- **Head SHA**：Run 實際執行的 head_sha（應等於目標 Commit SHA）
- **Run Event**：觸發事件（如 push / pull_request / workflow_dispatch）
- **Run Conclusion**：success / failure / cancelled / skipped

### Job 結論

- **Backend Conclusion**：Backend job 整體結果
- **Frontend Conclusion**：Frontend job 整體結果

### 9 步驟各別結果

逐條列出 9 步驟的名稱與 conclusion。

### 統計

- **Failed Steps 統計**：列出所有狀態非 SUCCESS 的步驟（若全數通過則為 0）
- **Skipped Required Steps 統計**：列出所有被跳過的步驟（若無則為 0）

### 最終判定

- **Phase 3C Accepted**：YES / NO
  - YES = 所有 9 步驟皆 SUCCESS 且 Run conclusion = success
  - NO = 任一步驟 failure / skipped / cancelled
- **Ready for Phase 3D**：YES / NO
  - YES = Phase 3C Accepted = YES
  - NO = Phase 3C Accepted = NO

---

## 執行順序

1. 使用 GitHub API 查詢 Commit SHA 對應的 GitHub Actions Run
   - 端點：`GET /repos/{owner}/{repo}/commits/{sha}/check-runs` 或
   - `GET /repos/{owner}/{repo}/actions/runs?head_sha={sha}`
2. 從回傳結果中提取 Run ID、Head SHA、Event、Conclusion
3. 逐步驟讀取每個 Job 的 Steps 列表，檢查每步的 conclusion
4. 比對 9 步驟是否全部為 SUCCESS
5. 生成最終報告

---

## 禁止事項

- 不得自行建立或修改 GitHub Actions Workflow
- 不得手動觸發新的 CI Run 來冒充本次驗收
- 不得 skip / xfail / 刪除任何測試
- 不得更改 Commit SHA
- 不得修改 Run 結果
- 不得降低驗收標準
- 不得以 SQLite 或其他資料庫代替 Postgres CI 驗證
- 不得開始 Phase 3D

---

## 完成條件

```text
✅ GitHub Actions Run 已找到且對應 Commit SHA 正確
✅ 9 步驟全部 SUCCESS
✅ Run Conclusion = success
✅ Phase 3C Accepted = YES
✅ Ready for Phase 3D = YES
✅ 最終報告已寫入 tasks/requirements.md
```

任一項不符合則：

```text
❌ Phase 3C Accepted = NO
❌ Ready for Phase 3D = NO
❌ 標記需修復後重新驗收
```
