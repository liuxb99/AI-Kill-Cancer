# Phase 3E 返工計劃 #2（Rework #2）

> 基於 Reviewer 評分 51/100：2 項問題（E-1 HIGH、E-2 MEDIUM）

---

## 總覽

| 項次 | 問題編號 | 問題摘要 | 嚴重程度 | 預計工時 |
|------|---------|---------|---------|---------|
| 1 | E-1 | Python 3.11 f-string 語法錯誤（反斜杠） | **HIGH** | 0.2 人時 |
| 2 | E-2 | State Machine ACTIVE→CANCELLED 轉換缺失 | **MEDIUM** | 0.2 人時 |
| | | **總計** | | **~0.4 人時** |

---

## 1. E-1：Python 3.11 f-string 反斜杠語法錯誤（HIGH）

### 角色
backend-logic

### 修改檔案
`src/backend/clinical/report_generator.py`

### 問題描述
第 1738 行 `f"Monitoring #{i+1}"` 中，f-string 的 `{...}` 表達式內使用了 `\`（反斜杠轉義），Python 3.11 不允許此寫法。

### 具體修改內容

**檔案**：`src/backend/clinical/report_generator.py`

**第 1738 行** 原始代碼：

```python
<div class="mon-label">{html_lib.escape(str(m.get("name", m.get("monitoring_type", f"Monitoring #{i+1}"))))}</div>
```

改為（提取變數，避免 f-string 內嵌反斜杠）：

```python
mon_label = f"Monitoring #{i+1}"
```

並在 enumerate loop 內，第 1735~1744 行調整為：

```python
mon_cards = "".join(
    f"""\
<div class="tp-monitoring-card">
  <div class="mon-label">{html_lib.escape(str(m.get("name", m.get("monitoring_type", mon_label))))}</div>
  ...
</div>"""
    for i, m in enumerate(monitoring)
)
```

或者更簡潔的方式——直接使用字串拼接取代 f-string：

```python
html_lib.escape(str(m.get("name", m.get("monitoring_type", "Monitoring #" + str(i+1))))
```

**建議採用變數提取方案**，保持程式碼可讀性：

1. 在 `for i, m in enumerate(monitoring)` 迴圈內第一行加入：
   ```python
   mon_label = f"Monitoring #{i+1}"
   ```
2. 將第 1738 行中的 `f"Monitoring #{i+1}"` 替換為 `mon_label`

### 驗收條件

| 檢查項 | 預期結果 |
|--------|---------|
| Python 3.11 語法檢查 | `python -c "import ast; ast.parse(open('src/backend/clinical/report_generator.py').read())"` 通過無誤 |
| 現有單元測試 | `pytest tests/ -k "report"` 全部通過 |
| Monitoring 渲染 | 監控項目的標籤正確顯示「Monitoring #1」、「Monitoring #2」... |

---

## 2. E-2：State Machine ACTIVE→CANCELLED 轉換缺失（MEDIUM）

### 角色
backend-logic

### 修改檔案
`src/backend/clinical/treatment_plan_state_machine.py`

### 問題描述
需求 §七 要求「任意非 completed → cancelled」，但 `TreatmentPlanStateMachine.TRANSITIONS` 中 `PlanStatus.ACTIVE` 的允許轉換列表缺少 `PlanStatus.CANCELLED`。

當前第 57 行：
```python
PlanStatus.ACTIVE: [PlanStatus.PAUSED, PlanStatus.COMPLETED, PlanStatus.SUPERSEDED],
```

### 具體修改內容

**檔案**：`src/backend/clinical/treatment_plan_state_machine.py`

**第 57 行** 將：
```python
PlanStatus.ACTIVE: [PlanStatus.PAUSED, PlanStatus.COMPLETED, PlanStatus.SUPERSEDED],
```

改為：
```python
PlanStatus.ACTIVE: [PlanStatus.PAUSED, PlanStatus.COMPLETED, PlanStatus.SUPERSEDED, PlanStatus.CANCELLED],
```

### 驗收條件

| 檢查項 | 預期結果 |
|--------|---------|
| `TreatmentPlanStateMachine.can_transition(PlanStatus.ACTIVE, PlanStatus.CANCELLED)` | 返回 `True` |
| `TreatmentPlanStateMachine.transition(PlanStatus.ACTIVE, PlanStatus.CANCELLED)` | 返回 `PlanStatus.CANCELLED`，不拋異常 |
| 既有 ACTIVE 轉換不受影響 | `PAUSED`、`COMPLETED`、`SUPERSEDED` 仍可正常轉換 |
| 需求 §七 覆蓋 | 任意非 completed 狀態均可轉到 CANCELLED |

---

## 3. 執行順序

```
E-1 (report_generator.py)  ← 無依賴
E-2 (state_machine.py)     ← 無依賴
```

兩個修復完全獨立，可並行執行。建議順序：
1. **E-2**（修改一行，風險最低，先完成可快速提升評分）
2. **E-1**（需注意 Python AST 驗證）

---

## 4. 不做的事

- ✅ 不涉及資料庫 Migration
- ✅ 不修改 Frontend
- ✅ 不修改 API Router / Service 層
- ✅ 不修改 Engine 邏輯
- ✅ 不新增測試檔案（既有測試覆蓋足夠）
- ❌ 不重構 report_generator.py 的 monitoring 渲染邏輯整體結構

---

## 5. 風險與注意事項

- **E-1 向後相容**：改為變數提取後，所有 Python 版本（3.8+）均相容。修改後需通過 AST 解析驗證。
- **E-2 語意正確性**：加入 CANCELLED 後，ACTIVE 狀態的 plan 可被取消。需確認業務邏輯中取消 ACTIVE plan 的流程（例如副作用：取消通知、資源釋放等）由呼叫方處理，state machine 僅做轉換校驗。
