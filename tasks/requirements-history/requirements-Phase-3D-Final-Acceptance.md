# Phase 3D Final Acceptance（最後驗收）

本輪不是新功能開發。

本輪唯一目標：

> **修正 ChatGPT Review 指出的所有 P0/P1 問題，使 Phase 3D 正式 Accepted。**

不得新增任何功能。

不得重構。

不得修改 API。

不得修改資料模型。

只允許修正 Reviewer 指出的缺口。

---

# 必須完成（P0）

## P0-1 Cross-language ID Parity（真正跨語言）

目前 CI 只是：

Python == Python

這不是 Cross-language。

必須新增：

knowgraph clinical id patient P001

CLI。

至少支援：

patient
recommendation
decision
consensus
opinion
specialty
drug
evidence
variant
relation

CLI 回傳：

{
  "kind":"patient",
  "business_key":"P001",
  "graph_id":"xxxxxxxx"
}

CI 必須真正：

Python ID == Go CLI ID

逐項 assert。

不是 UUID v5。

不是 deterministic。

是真正：

Python == Go

全部一致。

---

## P0-2 Cross Repository Digital Thread

CI 必須真正建立：

Temporary SQLite Graph DB

然後：

Patient Event → Recommendation Event → Clinical Decision Event → Consensus Event

全部：CLI apply

完成後：

CLI Query：Patient → Recommendation → Decision → Consensus

完整查詢。

驗證：

Node Count、Relation Count、Thread、Properties 全部正確。

不能只跑 unit test。

不能只 build CLI。

是真正：End-to-End

---

## P0-3 Store Level Idempotent Replay

Replay：

第一次：Entities Created, Relations Created

第二次：Entity Count 不增加, Relation Count 不增加, Update Count 正常

必須驗證：No Duplicate

---

# P1

## P1-1 Stub Entity

驗證：

先：patient.created 有完整資料（name, sex, age, cancer_type）

之後：recommendation.created 建立 stub

驗證：Stub 不能覆蓋完整 Entity。Properties 不得遺失。

---

## P1-2 Relation Provenance

目前只有：Imported 不足。

每一條 Relation 必須保留：event_id, event_type, aggregate_type, aggregate_id, correlation_id, causation_id, occurred_at, source_system

可追蹤來源。

---

## P1-3 Panic

目前：panic(...) 改成 return error

Adapter：Validation Error → Worker mark_failed → retry → dead_letter

不得 crash CLI。

---

# CI

新增：Cross-language parity, Cross repository E2E, Replay, Stub overwrite, Relation provenance

全部加入 GitHub Actions。不得只存在 local。

---

# 驗收標準

必須全部 PASS：Python == Go ID, Replay PASS, SQLite Graph PASS, Digital Thread PASS, Stub PASS, Relation Provenance PASS, No panic PASS, CI PASS

---

# 完成後

不要開始 Phase 4。不要新增任何功能。

只提交：Graph Acceptance Fix

完成後請提供：git status, git diff --stat, git log -1, 全部新增測試, CI Run, GitHub Actions URL

等待 ChatGPT 再次 Review。

---

**預計 Reviewer 分數可從約 82 分提升到 95～98 分。**
