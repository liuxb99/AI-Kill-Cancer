# ChatGPT × DeepSeek 行內審查註解協作流程

日期：2026-07-31

## 1. 背景

目前 AI-Kill-Cancer 的主要協作模式為：

```text
DeepSeek 負責主要開發與推送 GitHub
        ↓
ChatGPT 透過 GitHub Connector 進行獨立審查
        ↓
DeepSeek 依審查結果返工
        ↓
ChatGPT 再次驗收
```

原本的審查方式通常由 ChatGPT 撰寫完整 Review Report，再由使用者複製貼給 DeepSeek。這種方式雖然完整，但存在以下成本：

- DeepSeek 必須重新從長篇報告定位檔案、函式與代碼行。
- 審查意見與實際代碼位置分離，容易漏改或改錯位置。
- DeepSeek 可能因上下文不足而自行猜測，甚至宣稱完成但實際未處理。
- 使用者需要在 ChatGPT 與 DeepSeek 之間反覆複製貼上。
- ChatGPT 第二輪審查時，仍需重新比對原意見與實際修改位置。

## 2. 今日突破

新的協作方式是：

> ChatGPT 不再以長篇報告作為主要返工載體，而是直接在正確的原始碼位置加入 `REVIEW-*` 行內註解，讓 DeepSeek 透過 Git diff 立即知道問題在哪裡、應該修改什麼，以及需要補充哪些測試。

這些註解不是一般備註，而是嵌入代碼中的返工座標、驗收依據與追蹤標記。

## 3. 新流程

```text
DeepSeek 完成一個 Phase 或完整模組
        ↓
Push GitHub
        ↓
ChatGPT 透過 GitHub Connector 審查
        ↓
ChatGPT 在問題代碼旁加入 REVIEW-* 註解
        ↓
DeepSeek 拉取最新審查版本並查看 Git diff
        ↓
DeepSeek 直接在註解附近完成修改
        ↓
保留 REVIEW-* 註解，不立即刪除
        ↓
Push 修正結果
        ↓
ChatGPT 依 REVIEW-* 註解與附近 diff 逐項驗收
        ↓
全部通過後標記 REVIEW-VERIFIED
        ↓
正式發布前統一清除所有 REVIEW-* 註解
```

## 4. 建議標記格式

```text
REVIEW-P0       阻斷性問題，必須修正
REVIEW-P1       重要問題，本輪必須修正
REVIEW-P2       品質改善，建議本輪完成
REVIEW-TEST     必須補充或修改測試
REVIEW-DOC      必須同步文件或契約
REVIEW-OPEN     尚未完成
REVIEW-RESOLVED DeepSeek 宣稱已完成，等待 ChatGPT 驗收
REVIEW-VERIFIED ChatGPT 已驗收通過
```

範例：

```python
# REVIEW-P0 / REVIEW-OPEN
# 此處缺少明確的 transaction 邊界。
# 請由 Service 層統一管理 commit / rollback，
# Repository 不得自行 commit。
# 同時補充 rollback 與 commit failure 測試。
async def create_case(...):
    ...
```

DeepSeek 修改後保留原註解，並在附近補上狀態：

```python
# REVIEW-P0 / REVIEW-RESOLVED
# 此處缺少明確的 transaction 邊界。
# 請由 Service 層統一管理 commit / rollback，
# Repository 不得自行 commit。
# 同時補充 rollback 與 commit failure 測試。
#
# RESOLUTION:
# - transaction 已移至 Service 層
# - Repository commit 已移除
# - 已新增 rollback 與 commit failure 測試
async def create_case(...):
    ...
```

ChatGPT 驗收通過後，再改為：

```text
REVIEW-P0 / REVIEW-VERIFIED
```

## 5. 為什麼保留註解直到發布前

DeepSeek 修正後不立即刪除 `REVIEW-*` 註解，原因如下：

- 註解是 DeepSeek 的精確工作清單。
- 註解是 ChatGPT 第二輪審查的驗收座標。
- 可直接確認修改是否真的對應原審查要求。
- 避免只刪除標記、未真正解決問題。
- 多輪返工時，可清楚區分 OPEN、RESOLVED、VERIFIED。
- 正式發布前再一次清除，開發期間保留完整追蹤脈絡。

## 6. 極短總覽取代長篇報告

ChatGPT 仍可保留一份極短總覽，但不再重複所有細節：

```text
本輪審查：P0 2 項、P1 4 項、TEST 3 項。
請查看最新 Git diff 中全部 REVIEW-* 註解。
逐項完成實際修改與測試，不得跳過或自行改寫要求。
修正後保留註解並改為 REVIEW-RESOLVED。
完成品質返工循環後再 Commit / Push。
```

真正的修改要求全部放在正確的代碼位置。

## 7. 對各角色的價值

### DeepSeek

- 不必從長篇報告重新定位問題。
- 一看 Git diff 即可知道修正位置。
- 可依檔案與函式批次完成返工。
- 降低漏改、誤解與自行瞎編的機率。
- 不必重複分析整個專案，只需聚焦明確缺口。

### ChatGPT

- 不必撰寫大量重複的長篇報告。
- 第二輪審查可直接查看註解附近的修改 diff。
- 更容易判斷是否只做表面修正。
- 更容易確認是否補足測試與解決根因。
- 審查由全量重新理解轉為增量驗收。

### 使用者

- 不必反覆複製貼上審查意見。
- 不必向 DeepSeek 解釋哪條意見對應哪個檔案。
- 減少人工中轉與版本錯置。
- 可以專注於方向、需求與最終決策。

## 8. 適用範圍

特別適合：

- Transaction 邊界
- 錯誤處理
- 型別與輸入驗證
- Repository / Service 職責錯置
- 測試缺口
- API 契約不一致
- 命名與資料模型問題
- 局部 bug
- 跨檔案但位置明確的返工項目

若問題屬於整體架構方向錯誤、完整資料模型重設或端到端流程缺失，仍應增加一段極短的總體修改原則，再搭配各代碼位置的行內註解。

## 9. 分支建議

為避免污染 `master` 或與 DeepSeek 同時修改同一分支，建議使用：

```text
功能分支
        ↓
review-annotation/<phase-or-task>
        ↓
DeepSeek 在審查分支完成返工
        ↓
ChatGPT 驗收
        ↓
正式清理 REVIEW-* 註解
        ↓
合併或發布
```

第一輪實測可先選擇一個模組或一個 Phase，不必立即套用至整個專案。

## 10. DeepSeek 執行規則

```text
1. 拉取最新審查分支。
2. 查看全部 Git diff 與 REVIEW-* 註解。
3. 逐條完成實際代碼修正，不得只改註解狀態。
4. 補足註解要求的測試、文件與契約更新。
5. 保留原 REVIEW-* 註解。
6. 完成後改為 REVIEW-RESOLVED，並簡短說明 RESOLUTION。
7. 執行完整測試與品質返工循環。
8. 驗證通過後才可 Commit / Push。
9. 不得自行將 REVIEW-RESOLVED 改為 REVIEW-VERIFIED。
10. REVIEW-* 註解只能在正式發布清理階段統一刪除。
```

## 11. ChatGPT 驗收規則

```text
1. 以原審查提交與 DeepSeek 修正提交做 Git diff。
2. 逐條定位 REVIEW-* 註解。
3. 檢查註解附近是否存在對應的實質修改。
4. 確認是否解決根因，而非只繞過測試或修改表面行為。
5. 確認要求的測試與文件是否存在且有效。
6. 通過後標記 REVIEW-VERIFIED。
7. 未通過則保留 REVIEW-OPEN 或補充更精確要求。
8. 全部 VERIFIED 後，才允許進入發布清理。
```

## 12. 正式發布清理閘門

只有在以下條件全部滿足時，才允許統一清除 `REVIEW-*` 註解：

- 所有項目均為 `REVIEW-VERIFIED`
- 所有必要測試通過
- 完成一次完整返工循環
- 無新增 P0 / P1 缺口
- Git diff 已完成最終審查
- 文件與契約已同步

清理後再次執行完整測試，方可正式發布或合併主線。

## 13. 實測指標

第一輪實測應記錄：

- DeepSeek 從收到審查到開始修改的時間
- 完成所有返工的總時間
- 漏改數量
- 第二輪與第三輪返工次數
- 使用者複製貼上次數
- ChatGPT 再審查所需工作量
- 最終驗收一次通過率

若指標明顯改善，應將本流程正式納入 AI-Kill-Cancer 與其他專案的標準 Agent Workflow。

## 14. 核心結論

這套方法將審查意見從「獨立長篇報告」轉換為「與代碼綁定的可追蹤工作座標」。

它同時解決三個問題：

```text
DeepSeek 不必找位置
ChatGPT 不必重新定位
使用者不必人工轉貼
```

好的流程不是只讓某個角色更方便，而是讓 DeepSeek、ChatGPT 與使用者都能減少無效工作，並將時間集中在真正的代碼品質改善上。
