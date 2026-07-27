# Phase 3D Final Acceptance — 返工計劃 #1（CLI `id` 子命令缺失）

> 基於 reviewer 評分 80/100 ❌，唯一 P0 缺口：缺少 `knowgraph clinical id` CLI 命令。

---

## 1. 缺失修復：新增 `clinical id` 子命令

**檔案**：`KnowGraphGo/cmd/knowgraph/clinical.go`

### 1.1 在 `handleClinical` switch 中加入 `id` case

在 `case "verify":` 之後、`default:` 之前插入：

```go
case "id":
    return handleClinicalID(ctx, store, args[1:], gf)
```

### 1.2 新增 `handleClinicalID` 函數

```go
func handleClinicalID(ctx context.Context, store *sqlite.SQLiteStore, args []string, gf globalFlags) int {
    if len(args) < 2 {
        fmt.Fprintln(os.Stderr, "Error: clinical id requires <kind> <business_key>")
        return exitUsage
    }
    kind := args[0]
    businessKey := args[1]

    factory := &clinical.ClinicalIDFactory{}
    var graphID string

    switch kind {
    case "patient":
        graphID = factory.PatientID(businessKey).String()
    case "recommendation":
        graphID = factory.RecommendationID(businessKey).String()
    case "decision":
        graphID = factory.ClinicalDecisionID(businessKey).String()
    case "consensus":
        graphID = factory.ConsensusID(businessKey).String()
    case "opinion":
        graphID = factory.OpinionID(businessKey).String()
    case "specialty":
        graphID = factory.SpecialtyID(businessKey).String()
    case "drug":
        graphID = factory.DrugID(businessKey).String()
    case "evidence":
        graphID = factory.EvidenceID(businessKey).String()
    case "variant":
        graphID = factory.VariantID(businessKey).String()
    case "relation":
        // business_key format: "KIND:FROM:TO"
        parts := strings.SplitN(businessKey, ":", 3)
        if len(parts) != 3 {
            fmt.Fprintln(os.Stderr, "Error: relation business_key must be KIND:FROM:TO")
            return exitUsage
        }
        graphID = factory.RelationID(parts[0], parts[1], parts[2]).String()
    default:
        fmt.Fprintf(os.Stderr, "Error: unknown kind %q (use patient|recommendation|decision|consensus|opinion|specialty|drug|evidence|variant|relation)\n", kind)
        return exitUsage
    }

    out := map[string]string{
        "kind":         kind,
        "business_key": businessKey,
        "graph_id":     graphID,
    }
    enc := json.NewEncoder(os.Stdout)
    enc.SetIndent("", "  ")
    if err := enc.Encode(out); err != nil {
        fmt.Fprintln(os.Stderr, "Error: encode output:", err)
        return exitErr
    }
    return exitOK
}
```

需要新增 import：`"strings"`（已在 clinical.go 中無，需加入）。

### 1.3 更新 `printClinicalUsage`

在 `clinical apply|rebuild|verify` 行後追加 `clinical id` 用法：

```
  knowgraph clinical id <kind> <business_key>    Compute deterministic graph ID for a clinical entity/relation
```

### 1.4 更新 `root.go` 中的 `printUsage`

在 `clinical apply|rebuild|verify` 行改為：

```
  clinical apply|rebuild|verify|id     Clinical knowledge graph operations
```

---

## 2. CLI 輸出驗證

執行以下命令應輸出與 `golden_output.json` 一致的結果：

```bash
go build -o knowgraph.exe ./cmd/knowgraph/
./knowgraph.exe clinical id patient P001
# → {"kind":"patient","business_key":"P001","graph_id":"02fe1d2a-da12-5f27-a5ff-01d5ded671a5"}

./knowgraph.exe clinical id relation FOR_PATIENT:P001:REC-001
# → {"kind":"relation","business_key":"FOR_PATIENT:P001:REC-001","graph_id":"3e97bc60-cdea-5d08-b26d-a840cbcd6140"}
```

---

## 3. CI 更新：使用 CLI 輸出比對取代僅依賴 golden 文件

### 3.1 修改 `tests/test_phase3d_id_parity.py`

新增測試方法 `test_id_parity_via_cli`，直接調用 CLI binary 獲取 ID 並與 Python 結果比對：

```python
def test_id_parity_via_cli(self):
    """通过 CLI 获取 ID，验证 Python == Go CLI ID。"""
    import subprocess
    cli_path = os.environ.get("KNOWGRAPH_CLI", "../KnowGraphGo/knowgraph.exe")
    
    cases = [
        ("patient", "P001"),
        ("recommendation", "REC-001"),
        ("decision", "DC-001"),
        ("consensus", "CON-001"),
        ("opinion", "OP-001"),
        ("specialty", "SP-001"),
        ("drug", "DRUG-001"),
        ("evidence", "EV-001"),
        ("variant", "VAR-001"),
        ("relation", "FOR_PATIENT:P001:REC-001"),
    ]
    
    for kind, bk in cases:
        result = subprocess.run(
            [cli_path, "clinical", "id", kind, bk],
            capture_output=True, text=True, timeout=15
        )
        assert result.returncode == 0, f"CLI failed for {kind} {bk}: {result.stderr}"
        cli_out = json.loads(result.stdout)
        assert cli_out["kind"] == kind
        assert cli_out["business_key"] == bk
        
        # Python 端計算
        if kind == "relation":
            parts = bk.split(":", maxsplit=2)
            py_id = ClinicalGraphIDFactory.relation_id(parts[0], parts[1], parts[2])
        else:
            factory_method = getattr(ClinicalGraphIDFactory, f"{kind}_id")
            py_id = factory_method(bk)
        
        assert cli_out["graph_id"] == py_id, (
            f"Mismatch for {kind}={bk}: CLI got {cli_out['graph_id']}, Python got {py_id}"
        )
```

### 3.2 修改 `.github/workflows/ci.yml` 中的 CI-01 步驟

**當前**（僅 golden 比對）：
```yaml
- name: CI-01 Run Go golden test
  run: go test ./adapter/... -run TestGoldenIDOutput -v
- name: CI-01 Run Python ID parity test
  run: python -m pytest tests/test_phase3d_id_parity.py -v --tb=short
```

**改為**（保留 golden test 但追加 CLI 比對）：
```yaml
- name: CI-01 Run Go golden test
  working-directory: KnowGraphGo
  run: go test ./adapter/... -run TestGoldenIDOutput -v

- name: CI-01 Run Python ID parity test (golden)
  run: python -m pytest tests/test_phase3d_id_parity.py::TestClinicalGraphIDFactory::test_id_parity_with_go_golden -v --tb=short

- name: CI-01 Run Python ID parity test (CLI)
  env:
    KNOWGRAPH_CLI: KnowGraphGo/knowgraph.exe
  run: python -m pytest tests/test_phase3d_id_parity.py::TestClinicalGraphIDFactory::test_id_parity_via_cli -v --tb=short
```

或更簡潔地，在 `Cross-repository Integration Test` 步驟中增加一段直接調用 CLI 的 Python 腳本。

---

## 4. 不做的事

- ✅ 已有的 `TestGoldenIDOutput` golden test 保持不變
- ✅ 已有的 `test_id_parity_with_go_golden` 保留（它仍然有效）
- ✅ 不修改 API、資料模型
- ✅ 不新增功能
- ✅ 不重構

---

## 5. 驗收標準

| 檢查項 | 預期結果 |
|--------|---------|
| `knowgraph clinical id patient P001` | 輸出 JSON，`graph_id` 與 golden 一致 |
| `knowgraph clinical id relation FOR_PATIENT:P001:REC-001` | 輸出 JSON，`graph_id` 與 golden 一致 |
| 全部 10 種 kind 皆支援 | patient, recommendation, decision, consensus, opinion, specialty, drug, evidence, variant, relation |
| CLI 輸出格式 | `{"kind":"...","business_key":"...","graph_id":"..."}` |
| Python `test_id_parity_via_cli` 通過 | Python ID == Go CLI ID，逐項 assert |
| CI 中 golden test 仍通過 | `TestGoldenIDOutput` 繼續輸出 golden_output.json |
| 不影響現有測試 | 全部 Go test + Python test 仍 PASS |

---

## 6. 時間估計

| 步驟 | 估計 |
|------|------|
| 修改 `clinical.go`（新增 handler + switch case + import） | 15 min |
| 更新 usage text（clinical.go + root.go） | 5 min |
| 新增 Python `test_id_parity_via_cli` | 15 min |
| 更新 CI yml | 10 min |
| 本地驗證：build + test 全部通過 | 10 min |
| **總計** | **~55 min** |
