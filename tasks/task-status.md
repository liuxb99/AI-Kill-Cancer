# Task Status

## 場景
devops（CI/CD 診斷）

## 角色分派
- planner: 規劃診斷步驟
- devops: CI 診斷與 Workflow 修復執行
- reviewer: 驗證確認

## 範圍限制
- 只做 CI Trigger / Workflow 診斷
- 不得修改：Engine、Service、Repository、Migration 020、Frontend、Tests、AGENTS.md
- 只允許修改：.github/workflows/ci.yml（如有必要）
