# Phase 3D Final Acceptance 提交流程計劃

> 檔案路徑：`D:\AI-Future\AI-Kill-Cancer\tasks\plan-Phase-3D-Final-Acceptance-Submit.md`
> 場景：devops | 角色：devops（執行）、reviewer（驗證）

---

## 1. 任務清單（含依賴關係）

```
Phase 3D Final Acceptance Submit
├── [T1] 檢查倉庫當前狀態（無依賴）
├── [T2] 確認需求項目是否存在於本地 Commit（依賴 T1）
│   ├── 2a. scripts/cross_repo_e2e_test.py
│   ├── 2b. Cross-language ID parity
│   ├── 2c. CI-01~CI-05
│   ├── 2d. Digital Thread E2E
│   ├── 2e. Idempotent Replay
│   ├── 2f. Stub Preservation
│   └── 2g. Relation Provenance
├── [T3] 分階段 git add（依賴 T2 確認未提交）
│   ├── 3a. add 已修改（M）的 Phase 3D 檔案
│   └── 3b. add 未跟踪的關鍵檔案
├── [T4] git commit（依賴 T3）
├── [T5] git push（依賴 T4）
├── [T6] reviewer 驗證提交結果（依賴 T5）
└── [T7] 最終報告（依賴 T6）
```

---

## 2. 每個步驟的負責角色

| 步驟 | 負責角色 | 說明 |
|------|----------|------|
| T1   | devops   | 執行 `git status`、`git log`、`git diff` 等檢查命令 |
| T2   | devops   | 逐項確認需求項目的存在性，記錄結果 |
| T3   | devops   | 執行 `git add`，嚴格只加 Phase 3D Final Acceptance 相關檔案 |
| T4   | devops   | 執行 `git commit -m "fix(phase3d): complete graph final acceptance gate"` |
| T5   | devops   | 執行 `git push origin master` |
| T6   | reviewer | 驗證 push 後的 SHA、檔案列表、狀態 |
| T7   | reviewer | 彙總最終報告 |

---

## 3. 預計操作（具體 git 命令順序）

### 3.1 前置確認

```bash
cd "D:\AI-Future\AI-Kill-Cancer"

# T1: 檢查倉庫狀態
git status --short
git log --oneline -5
git rev-parse HEAD
git rev-parse origin/master
git diff --stat origin/master
```

### 3.2 逐項確認需求項目

```bash
# T2a: scripts/cross_repo_e2e_test.py
git log --all --oneline -- scripts/cross_repo_e2e_test.py
# → 預期：無輸出（該文件從未被提交）

# T2b: Cross-language ID parity
# 檢查 src/backend/clinical_graph/id_factory.py 中的 UUIDv5 實現
git log --all --oneline -- src/backend/clinical_graph/id_factory.py
# → 預期：d9335de 已包含

# T2c: CI-01~CI-05
git diff origin/master -- .github/workflows/ci.yml
# → 預期：包含 CI-01~CI-05 步驟

# T2d~T2g: 在 scripts/cross_repo_e2e_test.py 和 ci.yml 中確認
grep -n "Digital Thread\|Idempotent Replay\|Stub Preservation\|Relation Provenance" scripts/cross_repo_e2e_test.py .github/workflows/ci.yml
```

### 3.3 git add 命令

```bash
# T3: 只加 Phase 3D Final Acceptance 檔案
# 已修改檔案（M 狀態）：
git add .github/workflows/ci.yml
git add agent_workflow.md
git add agent_workflow_History.md
git add src/backend/clinical_graph/id_factory.py
git add tasks/requirements.md
git add tasks/task-status.md
git add tests/test_phase3d_id_parity.py
git add tests/unit/test_phase3d_outbox_repo.py
git add tests/unit/test_phase3d_worker.py

# 未跟踪的核心檔案：
git add scripts/cross_repo_e2e_test.py

# 驗證 add 結果
git status --short
```

> ⚠️ **排除檔案**：`AGENTS.md`（已從 git 追蹤移除，無此文件）。所有 `tasks/` 下的計劃/審查/報告文件（如 `plan-phase3d-final-acceptance.md`、`summary-report-*.md`、`reviews/` 等）為中間工作文檔，**不提交**，以保持主線乾淨。`KnowGraphGo/` 目錄為 CI checkout 產物，**不提交**。`tests/integration/test_phase3d_query_api.py` 為新增整合測試，與 Phase 3D 最終驗收相關但非需求清單中的核心檢查項，**不提交**。

### 3.4 git commit

```bash
# T4: 提交
git commit -m "fix(phase3d): complete graph final acceptance gate"

# 驗證 commit
git log --oneline -3
git rev-parse HEAD
```

### 3.5 git push

```bash
# T5: 推送
git push origin master

# 驗證 push
git rev-parse origin/master
```

---

## 4. 驗證方式

### 4.1 T6 reviewer 驗證清單

| 驗證項目 | 命令 | 預期結果 |
|----------|------|----------|
| 提交 SHA | `git rev-parse HEAD` | 非空、與 origin/master 同步 |
| 提交訊息 | `git log -1 --pretty=format:%s` | `fix(phase3d): complete graph final acceptance gate` |
| 修改檔案數 | `git diff --stat HEAD~1..HEAD` | ≥ 10 個檔案 |
| 核心檔案檢查 | `git diff --name-only HEAD~1..HEAD` | 包含 scripts/cross_repo_e2e_test.py |
| AGENTS.md 未提交 | `git diff --name-only HEAD~1..HEAD \| grep -i agents.md` | 無輸出（不應包含） |
| 推送成功 | `git rev-parse origin/master` 是否等於 HEAD | 相等 |
| git status --short | `git status --short` | 僅剩未跟踪文件（工作區乾淨） |
| Cross-language ID parity | 檢查 commit 中 id_factory.py  | 包含 UUIDv5 實現 |
| CI-01~CI-05 | 檢查 commit 中 ci.yml  | 包含 CI-01~CI-05 步驟 |
| Digital Thread E2E | 檢查 commit 中 cross_repo_e2e_test.py  | 包含 E2E 測試邏輯 |
| Idempotent Replay | 檢查 commit 中 cross_repo_e2e_test.py  | 包含 Idempotent Replay 驗證 |
| Stub Preservation | 檢查 ci.yml 中 CI-03~CI-05 步驟 | 包含 Go adapter 測試 |
| Relation Provenance | 檢查 ci.yml 中 CI-03~CI-05 步驟 | 包含 Go adapter 測試 |

### 4.2 確認命令腳本

```bash
echo "=== Commit Info ==="
git log -1 --pretty=format:"SHA: %H%nAuthor: %an%nDate: %ad%nSubject: %s"
echo ""
echo "=== Files Changed ==="
git diff --name-only HEAD~1..HEAD
echo ""
echo "=== Push Status ==="
if [ "$(git rev-parse HEAD)" = "$(git rev-parse origin/master)" ]; then
    echo "Push: SUCCESS (HEAD matches origin/master)"
else
    echo "Push: FAILED (HEAD != origin/master)"
fi
echo ""
echo "=== Working Tree ==="
git status --short
echo ""
echo "=== Origin SHA ==="
git rev-parse origin/master
```

---

## 5. 返工預案

### 5.1 git add 遺漏檔案

```bash
# 若 push 前發現遺漏
git add <遺漏的檔案路徑>
git commit --amend --no-edit
git push --force-with-lease origin master
```

### 5.2 commit 訊息錯誤

```bash
# push 前修正
git commit --amend -m "fix(phase3d): complete graph final acceptance gate"
```

### 5.3 push 失敗（網路/認證問題）

```bash
# 重試 push
git push origin master

# 若認證過期，確認 remote URL 中的 token 有效
git remote -v

# 若多次失敗，採用 --force-with-lease（僅在確定無衝突時）
git push --force-with-lease origin master
```

### 5.4 push 被拒絕（遠端有新 commit）

```bash
# 先拉取再推送
git pull --rebase origin master
# 解決衝突（如有）
git push origin master
```

### 5.5 誤提交不該提交的文件

```bash
# 若已 commit 但未 push
git reset --soft HEAD~1
git restore --staged <誤加檔案>
git commit -m "fix(phase3d): complete graph final acceptance gate"

# 若已 push
git revert HEAD
# 或使用 git reset + git push --force-with-lease（謹慎使用）
```

### 5.6 驗證失敗補救

若 reviewer 驗證發現遺漏需求項目：
1. 記錄缺失項目
2. 檢查是否因檔案未 add 導致
3. 補 add → `git commit --amend --no-edit` → `git push --force-with-lease`

---

## 附錄 A：需求項目與實際檔案映射

| 需求項目 | 實現檔案 | 狀態 |
|----------|---------|------|
| `scripts/cross_repo_e2e_test.py` | `scripts/cross_repo_e2e_test.py` | 未跟踪，待 add |
| Cross-language ID parity | `src/backend/clinical_graph/id_factory.py` + `tests/test_phase3d_id_parity.py` | M（已修改待提交） |
| CI-01~CI-05 | `.github/workflows/ci.yml` | M（已修改待提交） |
| Digital Thread E2E | `scripts/cross_repo_e2e_test.py`（第 5 行） | 未跟踪，待 add |
| Idempotent Replay | `scripts/cross_repo_e2e_test.py`（第 224~241 行） | 未跟踪，待 add |
| Stub Preservation | `.github/workflows/ci.yml`（CI-03~CI-05 Go adapter tests） | M（已修改待提交） |
| Relation Provenance | `.github/workflows/ci.yml`（CI-03~CI-05 Go adapter tests） | M（已修改待提交） |

## 附錄 B：當前倉庫快照（Plan 撰寫時）

```
HEAD SHA:    0f10ff5b98b42883485d3ddf74e045a8789397da
origin SHA:  0f10ff5b98b42883485d3ddf74e045a8789397da
分支:        master（HEAD 與 origin/master 相同）
已修改檔案:  9 個（M 狀態）
未跟踪檔案:  若干（含 scripts/cross_repo_e2e_test.py）
```

## 附錄 C：git add 完整檔案列表

```
.github/workflows/ci.yml                  # CI-01~CI-05 配置
agent_workflow.md                          # 工作流文檔
agent_workflow_History.md                  # 工作流歷史
src/backend/clinical_graph/id_factory.py   # Cross-language ID parity 實現
tasks/requirements.md                      # 需求文檔
tasks/task-status.md                       # 任務狀態
tests/test_phase3d_id_parity.py            # ID parity 測試（含 Go golden 比對）
tests/unit/test_phase3d_outbox_repo.py     # Outbox 存儲庫測試
tests/unit/test_phase3d_worker.py          # Worker 測試
scripts/cross_repo_e2e_test.py             # Digital Thread E2E + Idempotent Replay
```
