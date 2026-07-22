# Plan: Phase 2 Rework 1 — 导出/导入一致性修正

## 背景

Phase 2 開發完成後 REVIEWER 評分為 **85/100 ❌ 不合格**。

### 評分摘要

| 項目 | 分數 | 備註 |
|------|------|------|
| 完整性 | 22/25 | |
| 正確性 | **18/25** | ← 主要問題 |
| 可維護性 | 22/25 | |
| 測試驗證 | 23/25 | |
| **總分** | **85 ❌** | 門檻：90 |

### 關鍵問題

**🔴 前端匯出/導入不一致** — `Workbench.tsx` 使用具名導入（`import { ContextTab }`），但所有 6 個 Tab 元件使用預設匯出（`export default function`）。這導致：
- TypeScript/Vite 在開發模式下可能警告或無法正確解析
- 程式碼風格不一致，降低可維護性
- 是正確性扣分的主要原因（18/25）

---

## 修正策略

**方案：統一為具名匯出（Named Export）**

選擇理由：
1. 具名匯出更顯式，IDE 重構支援更好
2. `Workbench.tsx` 已使用具名導入，無需修改
3. 與現代 React/TypeScript 最佳實踐一致
4. 僅需修改 6 個元件 + 6 個測試檔案，變更範圍可控

---

## 修正任務

### FIX-001：將 6 個 Tab 元件改為具名匯出

修改 6 個檔案，將 `export default function ComponentName` 改為 `export function ComponentName`。

| 檔案 | 行號 | 原始內容 | 修改後內容 |
|------|------|----------|------------|
| `src/components/tabs/AgentsTab.tsx` | 157 | `export default function AgentsTab({ caseId }: AgentsTabProps) {` | `export function AgentsTab({ caseId }: AgentsTabProps) {` |
| `src/components/tabs/ConsensusTab.tsx` | 52 | `export default function ConsensusTab({ caseId }: ConsensusTabProps) {` | `export function ConsensusTab({ caseId }: ConsensusTabProps) {` |
| `src/components/tabs/ContextTab.tsx` | 63 | `export default function ContextTab({ caseId }: ContextTabProps) {` | `export function ContextTab({ caseId }: ContextTabProps) {` |
| `src/components/tabs/DecisionThreadTab.tsx` | 210 | `export default function DecisionThreadTab({ caseId }: DecisionThreadTabProps) {` | `export function DecisionThreadTab({ caseId }: DecisionThreadTabProps) {` |
| `src/components/tabs/EvidenceTab.tsx` | 116 | `export default function EvidenceTab({ caseId }: EvidenceTabProps) {` | `export function EvidenceTab({ caseId }: EvidenceTabProps) {` |
| `src/components/tabs/RecommendationTab.tsx` | 188 | `export default function RecommendationTab({ caseId }: RecommendationTabProps) {` | `export function RecommendationTab({ caseId }: RecommendationTabProps) {` |

> `Workbench.tsx` 的第 30-35 行（具名導入）**無需修改**。

### FIX-002：修正 6 個測試檔案的 import 語句

將測試檔案中的預設導入改為具名導入。

| 檔案 | 行號 | 原始內容 | 修改後內容 |
|------|------|----------|------------|
| `src/test/tabs/AgentsTab.test.tsx` | 36 | `import AgentsTab from '../../components/tabs/AgentsTab'` | `import { AgentsTab } from '../../components/tabs/AgentsTab'` |
| `src/test/tabs/ConsensusTab.test.tsx` | 40 | `import ConsensusTab from '../../components/tabs/ConsensusTab'` | `import { ConsensusTab } from '../../components/tabs/ConsensusTab'` |
| `src/test/tabs/ContextTab.test.tsx` | 44 | `import ContextTab from '../../components/tabs/ContextTab'` | `import { ContextTab } from '../../components/tabs/ContextTab'` |
| `src/test/tabs/DecisionThreadTab.test.tsx` | 64 | `import DecisionThreadTab from '../../components/tabs/DecisionThreadTab'` | `import { DecisionThreadTab } from '../../components/tabs/DecisionThreadTab'` |
| `src/test/tabs/EvidenceTab.test.tsx` | 26 | `import EvidenceTab from '../../components/tabs/EvidenceTab'` | `import { EvidenceTab } from '../../components/tabs/EvidenceTab'` |
| `src/test/tabs/RecommendationTab.test.tsx` | 48 | `import RecommendationTab from '../../components/tabs/RecommendationTab'` | `import { RecommendationTab } from '../../components/tabs/RecommendationTab'` |

### FIX-003：執行 lint 檢查並修復殘留問題

```bash
# 前端目錄下
cd src/frontend

# 執行 TypeScript 編譯檢查
npx tsc --noEmit

# 執行 lint（如果有 eslint 配置）
npx eslint --ext .ts,.tsx src/ --fix

# 執行測試確認通過
npx vitest run
```

預期結果：
- TypeScript 編譯無錯誤
- 所有測試通過
- 無 lint 警告

---

## 影響範圍

| 面向 | 變更數 | 說明 |
|------|--------|------|
| 元件檔案 | 6 個 | 僅修改 `export default function` → `export function` |
| 測試檔案 | 6 個 | 僅修改 import 語句（預設導入 → 具名導入） |
| 其他檔案 | 0 個 | Workbench.tsx 無需修改 |
| 外部 API | 無 | 無 runtime 行為變更 |

## 驗收標準

1. ✅ `npm run build` 或 `npx tsc --noEmit` 通過
2. ✅ `npx vitest run` 全部測試通過
3. ✅ REVIEWER 檢查清單中「無錯誤」項目通過
4. ✅ 總分 ≥ 90

---

## 預期分數提升

| 項目 | 修復前 | 修復後預期 | 說明 |
|------|--------|------------|------|
| 正確性 | 18/25 | 22-23/25 | 修正匯出不一致 + 測試正確性 |
| 可維護性 | 22/25 | 23-24/25 | 統一模組語法風格 |
| 測試驗證 | 23/25 | 24-25/25 | 測試 import 同步修正 |
| **總分** | **85** | **90-92 ✅** | 達到合格門檻 |
