# Task Status — Phase 3A Hardening

## 場景分類

- **主要場景**：feature-dev（功能開發加固）
  - 說明：P0-1/P0-2 資料庫持久化、P0-3 前端路由接入、新增 Model/Repository/Service/Migration/Tests 皆屬新功能模組開發
- **次要場景**：bug-fix（錯誤修復）
  - 說明：P1 HTTP 500 洩漏 Exception 屬安全修復

## 分派角色

| 角色 | 職責 |
|------|------|
| planner | 制定執行計劃，產出 tasks/plan-phase3a-hardening.md |
| backend-logic | 後端業務邏輯：Model、Repository、Service、Engine 改造、API 加固 |
| db-modeler | 資料庫建模：Alembic Migration、SQLAlchemy Model 設計 |
| api-designer | API 加固：POST/GET /recommendation 改為全 Database 操作、Error Handler |
| frontend-logic | 前端路由接入：App Router、Navigation、Menu、Link |
| security-fixer | HTTP Error Security：logger.exception() + 固定 Error Code + Generic Message（由 backend-logic 兼） |
| unit-tester | 單元測試：Model Tests、Repository Tests、Service Tests |
| integration-tester | 整合測試：API Integration Tests、Restart Recovery Test、Trace Persistence Test、Migration Tests |
| frontend-tester | 前端測試：Frontend Route Test |
| doc-writer | 文件撰寫：恢復 requirements.md 歷史、清理 artefacts |
| reviewer | 評分代理：產出 review 報告 |

## 任務清單（初步）

| ID | 任務 | 狀態 | 負責角色 | 依賴 | 備註 |
|----|------|------|----------|------|------|
| H-01 | **RecommendationModel**：建立正式 SQLAlchemy Model（id, patient_id, case_id, trace_id, engine_version, status, request_payload, result_payload, report_html, created_by, created_at, updated_at）及關聯 Trace Model | [ ] 待辦 | db-modeler | 無 | JSON round-trip, Index, Trace relation |
| H-02 | **CalculationTraceModel**：建立 RecommendationTraceModel / RecommendationTraceStepModel，保存完整計算鏈 Input→Evidence→Score→Rank→Explanation | [ ] 待辦 | db-modeler | H-01 | 與 RecommendationModel 建立外鍵關聯 |
| H-03 | **Alembic Migration**：新增正式 Migration，upgrade/downgrade 安全，包含所有新 Table | [ ] 待辦 | db-modeler | H-01, H-02 | 需支援 downgrade |
| H-04 | **RecommendationRepository**：建立正式 Repository（create, get_by_id, get_by_trace_id, list_by_patient_id），不自行 commit，交由 Service 管理 Transaction | [ ] 待辦 | backend-logic | H-01, H-02 | 配合 Unit of Work 模式 |
| H-05 | **RecommendationService**：建立正式 Service（執行 Pipeline、建立 Record + Trace、生成 HTML Report、同一 Transaction），取代記憶體 dict | [ ] 待辦 | backend-logic | H-04 | 整合 Engine Pipeline |
| H-06 | **API 加固**：保留 POST /api/v1/recommendation 和 GET /api/v1/recommendation/{recommendation_id}，改為全 Database 操作 | [ ] 待辦 | api-designer | H-05 | 移除記憶體 dict 依賴 |
| H-07 | **HTTP Error Security**：所有非預期 500 改用 logger.exception()，Client 只收固定 error code + generic message，不洩漏 Exception | [ ] 待辦 | backend-logic / security-fixer | 無 | 修改 error handler middleware |
| H-08 | **Frontend Router 接入**：RecommendationPage 正式接入 App.tsx、Route、Navigation、Menu、Link | [ ] 待辦 | frontend-logic | 無 | 確保 Navigation clickable、Page renders |
| H-09 | **Frontend API Integration**：確保 RecommendationPage 呼叫正式 API 端點，不 fake data | [ ] 待辦 | frontend-logic | H-08 | API path correct |
| H-10 | **Restart Recovery**：確保伺服器重啟後 Recommendation 和 Trace 仍可查詢，新增 Restart Recovery Integration Test | [ ] 待辦 | integration-tester | H-05, H-06 | 真實新 App、新 Engine、新 Session |
| H-11 | **清理 Phase E/Vercel artefacts**：移除無關檔案，確認無其他正式功能引用 | [ ] 待辦 | doc-writer | 無 | 先確認引用關係再刪除 |
| H-12 | **恢復 requirements.md 歷史**：保留舊有 Vercel/Phase E 需求、保留 Phase 3A 原始需求、新增 Phase 3A Hardening 章節，從此只 append | [ ] 待辦 | doc-writer | 無 | 不可覆蓋，只追加 |
| H-13 | **Backend Model Tests**：RecommendationModel JSON round-trip, Index, Trace relation | [ ] 待辦 | unit-tester | H-01, H-02 | 需覆蓋序列化/反序列化 |
| H-14 | **Repository Tests**：create, get_by_id, get_by_trace_id, list_by_patient_id, not found, rollback | [ ] 待辦 | unit-tester | H-04 | 使用 Test Database |
| H-15 | **Service Tests**：成功建立、同 transaction、Report failure、Pipeline failure rollback | [ ] 待辦 | unit-tester | H-05 | 驗證 Transaction 邊界 |
| H-16 | **API Integration Tests**：POST→DB、GET→DB、404、422、500 generic | [ ] 待辦 | integration-tester | H-06, H-07 | 使用 TestClient |
| H-17 | **Trace Persistence Test**：Evidence→Weight→Score→Rank→Explanation 可從 DB 還原 | [ ] 待辦 | integration-tester | H-02, H-05 | 驗證完整計算鏈 |
| H-18 | **Migration Tests**：upgrade→downgrade→upgrade again | [ ] 待辦 | integration-tester | H-03 | 確保 Migration 可逆 |
| H-19 | **Frontend Route Test**：Route registered、Navigation clickable、Page renders、API path correct | [ ] 待辦 | frontend-tester | H-08 | 可使用 React Testing Library |
| H-20 | **全量測試驗證**：go test ./...、Frontend build、Backend build、API Smoke Test | [ ] 待辦 | integration-tester | H-13~H-19 | 最終整合驗證 |

## 依賴圖

```
H-01 ──→ H-03 ──→ H-04 ──→ H-05 ──→ H-06
H-02 ──→ H-03 ──→ H-04 ──→ H-05 ──→ H-10
                              H-05 ──→ H-15
H-01,H-02 ──→ H-13
H-04 ──→ H-14
H-06,H-07 ──→ H-16
H-02,H-05 ──→ H-17
H-03 ──→ H-18
H-08 ──→ H-19
H-08,H-09 ──→ H-19
H-07（無依賴，可並行）
H-11（無依賴，可並行）
H-12（無依賴，可並行）
```

## 注意事項

1. 所有新 Model 須使用 SQLAlchemy + PostgreSQL，禁止 dict、global variable、singleton cache、module-level cache、process memory、temporary file、JSON file、SQLite fallback
2. Repository 不自行 commit，由 Service 管理 Transaction
3. Migration 必須支援安全 downgrade
4. Frontend 不重新設計，只補頁面和路由
5. Hardening Commit 只包含指定內容，不得混入無關修改
6. 完成標記使用 `[v]`，待辦使用 `[ ]`
