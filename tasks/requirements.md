# 需求 — REVIEW-PHASE3F0-R4 + Master Plan 統一

> 任務 ID：Phase-3F0-R4
> 記錄時間：2026-07-31

---

## 1. REVIEW-PHASE3F0-R4-P0-01 / REVIEW-OPEN（阻斷性）

**位置**：`src/backend/services/variant_ingestion_service.py`（bulk_create_variants 內，L33-44）

### 問題
- `bulk_create_variants` 在 Service 返回前即 `await self.db.commit()`
- 之後若 endpoint 的 response model validation、序列化或其他後段處理失敗，已提交的 variants 無法由 `get_db()` rollback → 「請求失敗但資料已落庫」的部分成功
- R3 測試只證明 get_db 不會提交 Service 之後新增的資料 B，但允許 Service 已提交的資料 A 保留，與原 REVIEW 要求「Service 返回後 endpoint 失敗不留下部分提交資料」不一致

### 修改要求
1. 明確選定並實作唯一請求交易邊界
2. 將完整 response DTO 建構納入 Service transaction 成功條件（commit 前完成 DTO 建構；DTO 建構失敗 → rollback → 資料不落庫）
3. **不得只修改測試文字放寬原需求**
4. REVIEW 註解保留原文字，狀態改 REVIEW-RESOLVED，附 RESOLUTION

### 驗證要求（真實 endpoint 測試）
1. 真實呼叫 `POST /api/v1/variants/import` endpoint，讓 Service 寫入後的 response validation/序列化失敗 → **fresh session 查不到本次新增 variants**
2. 成功路徑仍只能 commit 一次

---

## 2. Master Plan 統一

### 2.1 B1/B2 關係改為「部分重疊、具明確啟動 Gate」

現狀（三份文件三種說法）：
- `tasks/plan-phase4-clinical-ai-productization.md`：B1/B2 完全並行、無前置依賴（:921、:982-983、:1071-1072）
- `tasks/phase4-phase5-dependency-map.md`：部分並行但自身矛盾（:86/:88 說並行，:96/:128 說需 B1 核心，:114 同一句矛盾）
- `tasks/roadmap-phase4-phase5.md`：串行（B1 合併後 B2 才啟動，:95/:265/:562-564）

**統一為**：B1/B2 **部分重疊、具明確啟動 Gate**：
- B2 的啟動 Gate = B1 完成「Patient Import + Evidence Collection 核心」（B1 子集）
- Gate 通過後 B2 啟動，與 B1 剩餘部分（Treatment Plan、FHIR Export、Audit、Frontend）重疊並行
- 三份文件（plan-phase4、dependency-map、roadmap）表述一致；dependency-map 內部矛盾一併修正
- gap-analysis 若引用舊 Batch 結構（如「Phase 4 B4 Infrastructure」）一併更新為 3-Batch 結構

### 2.2 External Adapter 數量與清單全文件一致

現狀（7/8/10 三種數字）：
- `plan-phase4` 內部矛盾：:51「7 個」、:159「8 個」、:774-785 分類表「同步 7 + 非同步 3 = 10 個」、:1224 G2「7 個」
- `roadmap` :55 列 8 個檔案（含 OpenCRAVAT，與 phase4「不完成 OpenCRAVAT」衝突）
- `plan-phase5` :1084「8 個 stub」
- `dependency-map` 清單成員不同（DGIdb 歸 B3 vs phase4 歸 B1；缺 DRKG/PharmCAT/Ensembl VEP/非同步）

**統一基準**（以 plan-phase4 8.3 節分類表為準）：

| 分類 | Adapter | 數量 |
|------|---------|------|
| 同步（Evidence Retrieval / Clinical Decision） | CIViC、DGIdb、OncoTree、MyVariant.info、DRKG、Ensembl VEP、PharmCAT | 7 |
| 非同步（Guideline Sync / Background Refresh / Cache Refresh） | Guideline Sync、Background Refresh、Cache Refresh | 3 |
| **總計** | | **10** |

- OpenCRAVAT 明確排除（stub 保持 stub，不納入完成清單）
- 修正所有文件的數量與清單表述，全文件一致為 10 個（7 同步 + 3 非同步）

---

## 3. 完成條件

- [ ] R4 代碼修正完成（response DTO 建構在 commit 前）
- [ ] R4 真實 endpoint 驗證測試（2 情境）新增並通過
- [ ] R3 既有測試保持原樣未放寬
- [ ] REVIEW 註解改 REVIEW-RESOLVED（附 RESOLUTION）
- [ ] Master Plan 三份文件 B1/B2「部分重疊 + 啟動 Gate」表述一致
- [ ] Master Plan 全文件 External Adapter 數量統一為 10（7 同步 + 3 非同步）
- [ ] 完整返工循環（Step 6 回歸 + Step 7 REVIEWER 評分）通過
- [ ] 完整測試通過後 Commit / Push
