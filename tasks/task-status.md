# Task Status — Phase 4 & Phase 5 Master Plan

## 場景
master-plan（大型規劃與調研）

## 場景描述
制定 Phase 4 Clinical AI Productization 與 Phase 5 Medical AI Platform 的完整 Master Plan，
包含現況盤點、Gap Analysis、架構規劃、Batch 拆分、Dependency Map、Roadmap 及 ADR。
只產出規劃文件，不修改 production code。

## 分派角色
| 角色 | 職責 |
|------|------|
| PLANNER | 制定整體規劃架構與 Batch 拆分策略 |
| doc-writer | 撰寫規劃文件、盤點報告 |
| explorer | 程式碼盤點與現況調查 |
| REVIEWER | 依 AGENTS.md 規定評分，>=90 合格 |

## 排除角色
- backend-logic（本輪禁止 production code 修改）
- frontend-logic（本輪禁止 production code 修改）
- api-designer（本輪禁止 production code 修改）
- db-modeler（本輪禁止 production code 修改）
- test-writer（本輪無測試任務）

## 當前階段
🔄 **返工循環第 2 次**（基於 ChatGPT 正式審查 Accepted=NO）

## 返工重點
1. **Phase 4 Batch 拆分**：6 技術模組 → 3 個 Vertical Slice Batch
2. **Transaction Boundary**：Service owns transaction（與 Phase 3F-0 一致）
3. **Adapter 分類**：同步/非同步分開描述
4. **禁止新增基礎元件**：Redis/Kafka/Vector DB 需共同證明
5. **Scope 控制**：移除大型 Service Refactor 與 Frontend 重構
6. **Phase 5 Batch**：最多 2～3 個 Batch
