# Task Status

## 任務 ID
Phase-3E-Final-Hardening

## 場景
hardening（架構強化）

## 場景描述
修正 Migration 025 的 PostgreSQL constraint 問題、CI Gate 強化、降級環境改進、PostgreSQL 遷移穩健性

## 對應 scene_rules.yaml
- **id**: hardening
- **需求來源**: tasks/requirements.md（Phase 3E Final Hardening）

## 角色分派
| 角色 | 職責 |
|------|------|
| planner | 制定強化計劃與優先級排序 |
| backend-logic | 後端邏輯修正（Migration、CI、PostgreSQL 相容性） |
| test-writer | 撰寫 PostgreSQL Integration Test、Schema Compare Test、CI Migration Test |
| reviewer | 評分代理 |

## 優先級
- **P0-1**: PostgreSQL Trace Constraint（最高優先）
- **P0-2**: Migration 025 Downgrade
- **P0-3**: CI Migration Gate
- **P0-4**: Downgrade Environment
- **P1**: PostgreSQL Migration Robustness
- **P1**: Tests

---

## 任務：Phase 3E Final Hardening

### 場景
hardening（架構強化）— 修正 Migration 025 的 PostgreSQL constraint 問題、CI Gate 強化、降級環境改進、PostgreSQL 遷移穩健性

### 角色分派
| 角色 | 職責 |
|------|------|
| planner | 制定強化計劃與優先級排序 |
| backend-logic | 後端邏輯修正（Migration、CI、PostgreSQL 相容性） |
| test-writer | 撰寫 PostgreSQL Integration Test、Schema Compare Test、CI Migration Test |
| reviewer | 評分代理 |

### P0 任務清單
| ID | 描述 | 負責角色 |
|----|------|---------|
| P0-1 | PostgreSQL Trace Constraint：修正 Migration 025 的 constraint 問題，確保 PostgreSQL 相容性 | backend-logic |
| P0-2 | Migration 025 Downgrade：實作 Migration 025 的降級邏輯 | backend-logic |
| P0-3 | CI Migration Gate：強化 CI 流程中的 Migration 閘道檢查 | backend-logic |
| P0-4 | Downgrade Environment：改進降級環境的支援與測試 | backend-logic |
| P1 | PostgreSQL Migration Robustness：提升 PostgreSQL 遷移的穩健性與錯誤處理 | backend-logic |
| P1 | Tests：撰寫 PostgreSQL Integration Test、Schema Compare Test、CI Migration Test | test-writer |

### 完成定義
- [ ] P0-1 PostgreSQL Trace Constraint 修正完成並通過測試
- [ ] P0-2 Migration 025 降級邏輯實作完成
- [ ] P0-3 CI Migration Gate 強化完成
- [ ] P0-4 Downgrade Environment 改進完成
- [ ] P1 PostgreSQL Migration Robustness 實作完成
- [ ] P1 Tests 全部通過
- [ ] Reviewer 評分通過
