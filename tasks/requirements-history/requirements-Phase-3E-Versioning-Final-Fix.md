# Phase 3E Versioning Final Fix

本輪禁止開始 Phase 3F。

只允許修正 ChatGPT GitHub Review 發現的問題。

依 AGENTS.md 完整流程執行。

======================================================
P0-1 Migration Compatibility（最高優先）
======================================================

禁止修改已發布 Migration 023。

恢復 Migration 023 為已發布版本。

新增：

Migration 025

負責：

1. 把 UNIQUE(plan_id) 改成 UNIQUE(plan_id, version)

2. 把 UNIQUE(trace_id) 改成 UNIQUE(trace_id, step_order)

3. 保留既有資料，不得 destroy data

必須真正支援：

024 Database → upgrade 025 → Schema 修正完成

新增 Migration Test：

Old DB (023/024) → upgrade 025 → 建立：

- plan version1, plan version2 必須成功
- trace step1, trace step2, trace step3 必須成功

======================================================
P0-2 Repository Version Chain
======================================================

目前 get_by_plan_id() 已經不再合法。因為：plan_id 可以有 version1, version2, version3。

禁止：scalar_one_or_none() 直接查 plan_id。

請拆成：

- get_current_by_plan_id(): WHERE plan_id AND is_current=true ORDER BY version DESC LIMIT 1
- get_plan_version(plan_id, version)
- list_versions(plan_id)

所有操作（GET, Approve, Activate, Pause, Complete, Cancel, Revise）全部改成使用 Current Version。

新增完整測試：

v1 → revise → v2 → GET 得到 v2 → revise → v3 → GET 得到 v3 → Versions: v3, v2, v1

======================================================
P0-3 Version Link
======================================================

目前 previous_plan_id, supersedes_plan_id 都只是保存 plan_id，沒有真正 Version Link。

改成：previous_version_id, supersedes_version_id，使用 TreatmentPlanModel.id 建立 self reference。

如果目前架構較適合：previous_version, superseded_by_version 也可以。

但不得只是保存同一個 plan_id。

新增測試：v1 → v2 → v3，驗證 version chain 完整。

======================================================
P0-4 Phase Mapping
======================================================

目前 Engine Output 的 Treatment Item 沒有 phase_type，導致全部 fallback 第一個 Phase。

禁止 fallback。

Engine 必須輸出 phase_type，例如：preparation, primary_treatment, monitoring, follow_up。

Service 必須依 phase_type 找到對應 phase。找不到直接 Validation Error，不得自動塞第一個 phase。

新增測試：Medication → primary_treatment, Monitoring → monitoring, Supportive Care → supportive_care，全部驗證。

======================================================
禁止事項
======================================================

不得新增功能、不得修改需求、不得進入 Phase 3F、不得修改 AGENTS.md、不得修改既有 API 行為（除 Version API）。

======================================================
驗證
======================================================

全部完成後：Python Tests, Go Tests, Migration Tests, Version Tests, Restart Recovery, Digital Thread 全部 PASS。GitHub Actions 全綠。

======================================================
完成後一次回報：

1. Commit SHA
2. GitHub Actions Run
3. Migration 025
4. Version Chain Tests
5. Phase Mapping Tests
6. Reviewer Score

等待 ChatGPT GitHub Review。
