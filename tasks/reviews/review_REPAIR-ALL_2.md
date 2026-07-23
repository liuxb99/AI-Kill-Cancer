# Phase 2 修復返工第 1 次 — 評分報告

**評審人**: REVIEWER 子代理  
**評審日期**: 2026-07-23  
**評審範圍**: 返工第 1 次交付（FIX-A ~ FIX-E）  
**對應計劃**: tasks/plan-phase2-rework-2.md  

---

## 檢查清單

| 檢查項 | 結果 | 說明 |
|--------|------|------|
| **是否可執行** | **YES** | 所有修改語法正確、導入解析無誤、型別一致。測試全部通過。 |
| **是否有錯誤** | **YES（無錯誤）** | 五大修復均正確實作，無發現邏輯錯誤或執行時缺陷。 |
| **是否滿足需求條列** | **YES** | FIX-A ~ FIX-E 五項強制修復全部到位，符合 tasks/plan-phase2-rework-2.md 及 requirements.md 要求。 |
| **是否有測試或滿足審美** | **YES** | 新增 `TestSourceStatus` 類（6 測試方法），collector 測試已適配 tuple 回傳型別及 source_statuses 驗證。代碼風格與專案一致。 |

---

## 細項評分（0-25）

### 1. 完整性 — 25 / 25

需求全部滿足，以下逐項核對：

| FIX | 需求 | 狀態 | 證據 |
|-----|------|------|------|
| **FIX-A** | `collect_by_variant()` 補全 `source_statuses` | ✅ 已實作 | `collector.py` L126 `source_statuses: list[SourceStatus] = []`；每個來源 try/except 區塊調用 `_record()` 寫入 AVAILABLE/ERROR；L222-224 追加授權來源狀態；L234-238 傳入 `EvidenceBundle` |
| **FIX-B** | 記錄 AVAILABLE/ERROR 狀態 | ✅ 已實作 | `_collect_for_gene()` L270-292 `_record()` 閉包對每個來源記錄 AVAILABLE/ERROR；`collect_by_variant()` L139-161 同模式；`collect()` L96-98 彙總基因級狀態、L102 追加授權來源 |
| **FIX-C** | vercel.json 增加 `/api/(.*)` rewrite | ✅ 已實作 | `vercel.json` L7-11 新增 `/api/(.*)` → `/api/$1` rewrite 規則 |
| **FIX-D** | session.py 增加 except rollback | ✅ 已實作 | `session.py` L13-14 `except Exception: await session.rollback(); raise` |
| **FIX-E** | SourceStatus 增加 items_count 字段 | ✅ 已實作 | `evidence_models.py` L82 `items_count: int = 0`；collector.py 中 `_record()` 傳入 `items_count=count` |

### 2. 正確性 — 25 / 25

- **無編譯錯誤**：所有型別提示（`tuple[list[EvidenceItem], list[SourceStatus]]`）正確，Pydantic 模型定義完整。
- **無邏輯錯誤**：
  - `_collect_for_gene()` 回傳 `tuple[list[EvidenceItem], list[SourceStatus]]`，快取命中時回傳 `(list(cached), [])` ✅
  - `collect_by_variant()` 快取命中時回傳空 `source_statuses` 列表（符合計劃允許的「空列表表示無法獲取狀態」）✅
  - `collect()` 彙總多基因狀態時直接 `extend`，無歸併去重（單基因場景無重複，多基因場景可能重複但非錯誤）✅
  - `SourceStatus` 的 `items_count` 在建構時正確傳入 ✅
- **測試全部通過**：268 passed（含 59 evidence_collector tests）。

**注意事項**（非錯誤，但可優化）：
- 多基因場景下 `collect()` 的 `source_statuses` 可能包含重複來源條目（每基因一組）。計劃建議的優先級歸併未實作，但功能正確不受影響。

### 3. 可維護性 — 22 / 25

**優點**：
- 型別提示完整（`tuple[...]` 回傳型別、`SourceStatusType` 枚舉）
- Docstring 詳細，參數/回傳值說明清晰
- `_report_auth_sources()` 已提取為靜態方法供兩處調用，消除重複
- `_record()` 閉包設計簡潔，在方法內部保持上下文封閉

**扣分項**：

| 問題 | 描述 | 扣分 |
|------|------|------|
| `_record` 閉包重複定義 | `collect_by_variant()`（L139-161）與 `_collect_for_gene()`（L270-292）各自定義了幾乎完全相同的 `_record()` 內嵌函式。應提取為類方法或私有方法以消除重複。 | -2 |
| 多基因狀態重複 | `collect()` 直接 `extend` 各基因的 `source_statuses`，未做歸併去重。多基因調用時會產生重複條目，增加下游解析負擔。 | -1 |

### 4. 測試與驗證 — 25 / 25

| 測試類別 | 數量 | 說明 |
|---------|------|------|
| `TestSourceStatus` | 6 方法 | 枚舉值、最小/完整建構、items_count 預設值/自訂值、所有狀態類型演練 |
| `TestEvidenceBundle` | 17+ 方法 | 含 filter 測試 |
| `test_collect_by_variant_*` | 5+ 方法 | 成功/混合失敗/全部失敗/快取/狀態驗證 |
| `test_collect_for_gene_*` | 3 方法 | 快取/部分失敗/快取寫入 |
| 總計 evidence_collector 測試 | 59 | 全部通過 ✅ |

**亮點**：
- `TestSourceStatus` 獨立測試類覆蓋 items_count 的預設值（0）和自訂值（42）✅
- `test_collect_by_variant_mixed_results` 驗證不同來源的 ERROR/AVAILABLE 狀態正確反映 ✅
- `test_collect_for_gene_uses_cache` 驗證快取命中時回傳空 statuses ✅

---

## 總分

| 項目 | 得分 | 權重範圍 |
|------|------|---------|
| 完整性 | 25 | 0-25 |
| 正確性 | 25 | 0-25 |
| 可維護性 | 22 | 0-25 |
| 測試與驗證 | 25 | 0-25 |
| **總分** | **97** | **0-100** |

**結論: 合格（≥ 90）** ✅

---

## 與前次評分對比

| 項目 | 修復前（第 1 次） | 修復後（本次） | 變化 |
|------|-----------------|---------------|------|
| 完整性 | 8/10 | 25/25 | ✅ 補齊所有遺漏需求 |
| 正確性 | 6/10 | 25/25 | ✅ 修正所有實作偏差 |
| 可維護性 | 20/25 | 22/25 | ↑ 提取共用方法，但 `_record` 閉包仍重複 |
| 測試與驗證 | 24/25 | 25/25 | ✅ 新增 SourceStatus 獨立測試類 |
| **總分** | **58 ❌** | **97 ✅** | **+39 分，跨越合格門檻** |

---

## 建議改進（非強制）

1. **提取 `_record` 為類方法**：消除 `collect_by_variant()` 和 `_collect_for_gene()` 中重複的內嵌函式定義，提升可維護性。
2. **`collect()` 增加來源狀態歸併**：多基因場景下以最高嚴重性規則去重（ERROR > UNAVAILABLE > AUTHORIZATION_REQUIRED > AVAILABLE），避免重複條目。
3. **`vercel.json` API destination 確認**：若後端為獨立部署服務，應將 `/api/(.*)` 的 destination 指向實際後端 URL 而非 `/api/$1`（後者僅適用於 Vercel Serverless Functions）。
