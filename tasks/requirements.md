# Phase 3D Final Acceptance Fix Round 2

本輪目標：

不是讓 CI 綠，而是真正完成 ChatGPT Review 提出的剩餘 P0 問題。

禁止：

- 不得使用 continue-on-error 掩蓋失敗
- 不得降低測試標準
- 不得把驗證移到問題發生之前
- 不得修改測試讓它繞過 Bug
- 不得只修改 workflow 文件
- 不得回報 PASS 而沒有客觀證據

==================================================
P0-1
Postgres Integration Gate
==================================================

目前 CI 將：

Alembic upgrade
Run Tests on Postgres
Downgrade/Re-upgrade

全部設為

continue-on-error: true

這是不允許的。

要求：

1.

移除所有 continue-on-error。

2.

真正修復 Migration 或 Postgres 相容性問題。

3.

直到：

Alembic upgrade PASS

Run Tests PASS

Downgrade PASS

Re-upgrade PASS

全部真正成功。

禁止：

因為 CI Failure 就加入 continue-on-error。

==================================================
P0-2
Stub Preservation
==================================================

目前 E2E：

patient.created

↓

立即驗證

↓

recommendation.created

這不能證明 Stub 不會覆蓋 Patient。

必須改成：

patient.created

↓

確認 Patient Properties

↓

recommendation.created

↓

再次確認 Patient Properties

↓

clinical_decision.created

↓

再次確認

↓

tumor_board_consensus.created

↓

再次確認

要求驗證：

display_name

sex

age_range

cancer_type

source_system

全部保持一致。

如果任何欄位被 Stub 覆蓋：

FAIL。

禁止：

把驗證提前。

禁止：

只驗第一次。

==================================================
P0-3
Relation Provenance
==================================================

目前只是取得 relation graph id。

這不是 Provenance 驗證。

要求：

新增真正 Relation Query。

可以：

query relation

或其他方式。

必須讀出真正 Relation Properties。

驗證：

event_id

event_type

aggregate_type

aggregate_id

correlation_id

causation_id

occurred_at

source_system

全部 assert。

不能只驗 graph_id。

==================================================
P0-4
KnowGraphGo Checkout
==================================================

CI 不得 checkout main。

必須固定：

KnowGraphGo

commit

6d2b20a68ba6ea25841e142918e186fb4beece0d

不得：

git fetch origin main

不得：

checkout FETCH_HEAD

必須固定 SHA。

==================================================
完成後

執行：

go test ./...

pytest

完整 GitHub Actions

不得人工略過。

==================================================
最後回報：

1.

KnowGraphGo Commit

2.

AI-Kill-Cancer Commit

3.

GitHub Actions Run ID

4.

Backend 每一步 PASS

5.

Frontend PASS

6.

Postgres Gate PASS（不得 continue-on-error）

7.

Stub Preservation 四次驗證結果

8.

Relation Provenance 八欄位驗證結果

9.

固定 SHA Checkout 證據

10.

REVIEWER 評分

沒有客觀證據不要回報 PASS。
