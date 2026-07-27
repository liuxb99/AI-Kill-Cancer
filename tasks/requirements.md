# Phase 3C CI Final Fix

## 目前狀態
- Workflow YAML：已修復（Commit 4ef1748）
- Jobs：已恢復正常建立（Run 30231119112：2 jobs）
- Backend：被 Ruff Lint 阻塞（46 errors）
- Frontend：Build 失敗
- Postgres Tests：尚未執行到

## 允許修正範圍
- Phase 3C 引入的 lint 問題（F401/F841/F541/I001）
- Phase 3C 引入的真實程式錯誤（F821 decision_rules.py:350）
- Frontend build 錯誤
- 後續 Postgres Test 真實失敗

## 禁止事項
- 不得放寬 lint 規則
- 不得降低 CI 標準
- 不得 skip/xfail 測試
- 不得移除 Postgres Gate
- 不得 ignore F821
- 不得 exclude Phase 3C files
- 不得把 lint 改成 continue-on-error
- 不得把 frontend build 改成可失敗

## 執行順序
1. ruff check --fix（I001 + F401 + F541）
2. 手動修正 F821（decision_rules.py:350）
3. 手動修正 F841（未使用變數）
4. 修復 Frontend Build
5. 完整測試序列：ruff → backend tests → frontend tests → frontend build → Postgres migration → Tumor Board tests → Restart Recovery → Digital Thread → Migration downgrade → Migration re-upgrade
6. Commit & Push

## Commit
fix(phase3c): resolve lint build and postgres ci failures
