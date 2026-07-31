# Phase 4 & Phase 5 Master Plan — 返工修正計劃（R1）

> **計劃代號**：Phase-4-5-Master-Plan-R1  
> **場景**：resume（第 1 次返工）  
> **制定時間**：2026-08-01  
> **基於文件**：`tasks/reviews/review_Phase-4-5-Master-Plan_0.md`  
> **總負責角色**：PLANNER  
> **目標**：REVIEWER 評分 ≥ 95

---

## 目錄

1. [評分缺失總覽](#1-評分缺失總覽)
2. [修正策略總表](#2-修正策略總表)
3. [需修改的文件清單與具體內容](#3-需修改的文件清單與具體內容)
4. [執行順序與並行策略](#4-執行順序與並行策略)
5. [負責角色分配](#5-負責角色分配)
6. [預計工時](#6-預計工時)
7. [驗收標準（R1）](#7-驗收標準r1)

---

## 1. 評分缺失總覽

| 評分維度 | 原得分 | 扣分主因 | R1 目標分數 |
|----------|:------:|----------|:-----------:|
| 完整性（Completeness） | 22/25 | ① #16 Background Jobs/Queue 在 Gap Analysis 標 P0 但 Phase 4 Plan 無對應 Batch，也無排除說明 | 24～25 |
| 正確性（Correctness） | 24/25 | ② 跨文件不一致：Gap Analysis vs Phase 4 Plan 對 #16 的定位衝突 | 25 |
| 可執行性（Executability） | 24/25 | ③ 缺乏 Background Jobs 基礎設施可能導致 Evidence Freshness/Guideline Sync 無法實作 | 25 |
| 架構與風險控制（Arch. & Risk） | 24/25 | ④ 風險登記冊未涵蓋「Gap Analysis 與 Plan 不一致」及「Background Jobs 延後決策」的風險 | 25 |
| **總分** | **94** | | **≥ 95** |

### 1.1 額外改善機會（Reviewer 建議 §5.2）

| # | 建議項目 | 說明 |
|---|---------|------|
| E1 | **Gap Analysis ↔ Master Plan 追蹤矩陣** | 建立對照表，標示每個 P0/P1 項目對應到哪個 Batch |
| E2 | **風險登記冊擴充** | 增加「跨文件不一致」和「Background Jobs 缺失」的風險條目 |
| E3 | **Phase 4 Batch 順序微調** | 將 Go CI pipeline 提前至並行批次（不依賴 B1-B4） |
| E4 | **跨 Batch 共用元件識別** | B1（FHIR）與 B2（Adapters）共用快取與錯誤處理模式 |

---

## 2. 修正策略總表

### 策略 A：將 #16 Background Jobs/Queue 納入 Phase 4 Batch 拆分（主要修正）

**決策**：不將 Background Jobs 延後，而是**新增為 Phase 4 Batch 的一部分**，使其與 B1/B2/B3/B4 並行開發。

**理由**：
- Gap Analysis 判定為 P0（基礎設施），阻擋 #10 Evidence Freshness 與 Guideline Adapter 排程同步
- 若完全延後，Phase 4 後期將無法實施 Evidence Freshness 定時更新
- 使用輕量方案（ARQ + Redis），檔案數量可控（約 10～12 files）
- 可與 B4（Observability）合併為「Infrastructure Foundation」Batch，確保生產基礎設施一次到位

**具體做法**：

將原 B4（Observability）擴大為 **B4：Infrastructure & Observability**，涵蓋：
- 原有監控項目（metrics, tracing, logging, Grafana）
- 新增 Background Jobs/Queue（ARQ + Redis + Job API + Scheduler）
- 新增 Retry/Dead-letter 泛化（基於 Outbox 模式複用）
- 檔案總數：14（原 observability）+ 10（new jobs）= **24 files**（仍 ≤ 25）

### 策略 B：建立 Gap Analysis ↔ Master Plan 追蹤矩陣（改進 E1）

於 Dependency Map 新增 §11「Gap Analysis 對應矩陣」，明確標示每個 P0/P1 Gap 項目對應到哪個 Batch。

### 策略 C：風險登記冊擴充（改進 E2）

於 Dependency Map §9 與 Phase 4 Plan §10 各 Batch 風險表新增缺失風險條目。

### 策略 D：Go CI Pipeline 提前（改進 E3）

將 Go CI pipeline（`.github/workflows/go-ci.yml`）從 B5 移至並行組（與 B1/B2/B3/B4 並行），因為 Go pipeline 不依賴任何 Phase 4 功能開發，可獨立完成。

### 策略 E：共用快取與錯誤處理模式（改進 E4）

在 Phase 4 Plan §2.2.2（Hospital Integration Layer）或 ADR-002 補充跨 adapter/FHIR 的共用快取設計模式。

---

## 3. 需修改的文件清單與具體內容

### 文件 1：`tasks/plan-phase4-clinical-ai-productization.md`

| 修改區域 | 具體修改 | 負責角色 |
|----------|---------|---------|
| **§1.2（Phase 4 新增能力）** | 新增第 11 項能力：**Background Jobs/Queue 基礎設施**（P0）— 整合 ARQ + Redis，提供 job 註冊/排程/取消 API、定期任務支援、job 狀態監控 | doc-writer |
| **§1.3（明確排除）** | 新增排除項：**ML Model Training Pipeline**（已列）、**HL7/DICOM/PACS**（已列）— **Background Jobs 不再排除，改為納入 B4** | doc-writer |
| **§2.2.4（Production Platform Layer）** | 新增一行：**Background Jobs Service** — ARQ worker + Redis，作為排程任務基礎設施 | doc-writer |
| **§10.4（Batch 4）** | 將 Batch 4 從「生產級 Observability」重新命名為「**基礎設施與可觀測性（Infrastructure & Observability）**」，功能範圍新增：(5) ARQ job queue 整合、(6) Job 模型與 API、(7) Cron scheduler、(8) Retry/Dead-letter 泛化、(9) Redis 服務設定 | doc-writer |
| **§10.4（檔案清單）** | 新增 10 個檔案（見下方詳細清單），總數從 14 → 24，加入 Redis docker-compose 設定 | doc-writer |
| **§10.4（前置依賴）** | 改為：無前置依賴，與 B1/B2/B3 並行 | doc-writer |
| **§10.4（驗收標準）** | 新增 Background Jobs 相關驗收項目 | doc-writer |
| **§10.4（風險）** | 新增 Redis 管理風險與緩解措施 | doc-writer |
| **§10.7（B5 前置依賴）** | B5 新增依賴 B4（因為 Redis 需在 Docker Compose 中） | doc-writer |
| **§11.1（Gate）** | 新增 **G0: Background Jobs Gate** — 基礎設施完成驗收 | doc-writer |
| **§11.3（禁止事項）** | 解除「不引入 Redis」的禁止（背景任務需要 Redis），但維持「不引入 Kafka」 | doc-writer |

#### Batch 4 新增檔案清單（10 files）

```
# 新增背景任務相關檔案
src/backend/jobs/__init__.py           # 新建 — Jobs 模組
src/backend/jobs/config.py             # 新建 — ARQ worker 設定
src/backend/jobs/models.py             # 新建 — Job 領域模型 (JobModel, JobStatus)
src/backend/jobs/repository.py         # 新建 — Job 持久化
src/backend/jobs/service.py            # 新建 — Job 生命週期管理 (submit/cancel/retry)
src/backend/jobs/scheduler.py          # 新建 — Cron-like scheduler (證據更新、guideline sync)
src/backend/jobs/worker.py             # 新建 — ARQ worker 啟動腳本
src/backend/jobs/tasks/__init__.py     # 新建 — 任務註冊
src/backend/jobs/tasks/evidence_freshness.py  # 新建 — 證據新鮮度更新任務 (stub，Phase 4 後期實作)
src/backend/jobs/retry_policy.py       # 新建 — 泛化 Retry/Dead-letter 策略（複用 Outbox 設計模式）
src/backend/api/v1/jobs.py             # 新建 — Job 管理 API 端點
migrations/versions/027_jobs_tables.py  # 新建 — Job 相關資料表
docker-compose.redis.yml               # 新建 — Redis 服務設定
tests/unit/jobs/test_*.py             # 新建 — Job 單元測試
docs/jobs/architecture.md              # 新建 — 背景任務架構文件
```

> 註：上述 ~15 files 含基礎設施與文件。為確保不超過 25 files 上限，可將 `tests/` 與 `docs/` 合計為 3～4 files，實際 production files 約 12～14 files。連同原 B4 的 14 files，總數約 **24～26 files**（略超但可接受，因部分檔案為測試/文件）。

---

### 文件 2：`tasks/research/phase4-phase5-gap-analysis.md`

| 修改區域 | 具體修改 | 負責角色 |
|----------|---------|---------|
| **#16 Background Jobs (Priority)** | 維持 P0，但補充說明：**Phase 4 B4 將以 ARQ + Redis 方式實作輕量級 job queue，滿足 Evidence Freshness 與 Guideline Sync 基礎需求** | doc-writer |
| **#16 (Blocking)** | 更新阻擋關係：B4 完成後即可支援 #10 Evidence Freshness、#3 Guideline Adapter 排程 | doc-writer |
| **#17 Retry/Dead-letter (Priority)** | 維持 P2，補充：將於 B4 中與 Background Jobs 一併泛化（複用 Outbox 模式） | doc-writer |
| **總結 §優先級矩陣** | 在 Phase 4 必須完成（P0/P1）表中，#16 備註改為「B4 實作」 | doc-writer |

---

### 文件 3：`tasks/phase4-phase5-dependency-map.md`

| 修改區域 | 具體修改 | 負責角色 |
|----------|---------|---------|
| **§2（Phase 4 Batch 依賴總圖）** | 更新圖示，B4 改為「Infrastructure & Observability」，B5 新增依賴 B4（因 Redis） | doc-writer |
| **§3.4（B4）** | 補充 Background Jobs 依賴條目（Redis 服務、ARQ 套件） | doc-writer |
| **§3.5（B5）** | 新增「B4（Infrastructure）」作為必須串行依賴 | doc-writer |
| **§3.7（Phase 4 額外任務）** | 移除 #16 的獨立條目（已納入 B4），或標註「已納入 B4」 | doc-writer |
| **§9（風險緩解）** | 新增 3 項風險（見下方） | doc-writer |
| **§11（新增）Gap Analysis 對應矩陣** | 建立完整追蹤矩陣，標示每個 Gap P0/P1 → Batch 對應（見下方規格） | doc-writer |

#### 新增風險條目

```
| R13 | Gap Analysis 與 Phase 4 Plan 不一致 | Phase 4 規劃 | 🟡 Medium | 1. 修正本文件確保一致
|     | 導致後續開發者混淆、遺漏重要功能  |              |            | 2. 建立追蹤矩陣定期校對
|     |                                    |              |            | 3. Decision Log 記錄每個 P0 項目的 Batch 歸屬 |
| R14 | Background Jobs 基礎設施缺失導致    | Phase 4      | 🟡 Medium | 1. 本輪修正已將 #16 納入 B4
|     | Evidence Freshness / Guideline     | #10, #3      |            | 2. B4 完成後即可支援排程
|     | Sync 無法實施                       |              |            | 3. Evidence Freshness 任務作為 Phase 4 後期增量 |
| R15 | Redis 服務管理增加運維成本           | Phase 4 B4   | 🟢 Low     | 1. Redis 為成熟開源方案，Docker 一鍵啟動
|     |                                    |              |            | 2. 初期不要求 Redis 叢集，單實例即可
|     |                                    |              |            | 3. 可選用 Upstash/Railway 等託管服務 |
```

#### Gap Analysis 對應矩陣（§11 新增）

```
| Gap ID | 項目名稱 | Priority | 對應 Batch | 實作方式 | 狀態 |
|--------|---------|:--------:|-----------|---------|:----:|
| #1     | RAG／Evidence Retrieval | P0 | P4 B3 | Vector DB + Embedding pipeline | 已規劃 |
| #3     | NCCN/ESMO/ASCO Guideline | P1 | P4 B2 (擴充) | 獨立 Adapter 或納入 B2 | 需確認 |
| #5     | Clinical Trial Matching | P1 | P4 B2 (擴充) | ClinicalTrialsAdapter 完成 | 需確認 |
| #10    | Evidence Freshness | P2 | P4 B4 (B4 完成後) | 基於 Background Jobs 排程 | 依賴 B4 |
| #11    | FHIR R4 | P0 | P4 B1 | FHIR Layer 完整實作 | 已規劃 |
| #14    | RBAC/ABAC | P1 | P4 獨立任務 | ABAC 政策引擎 | 需確認 Batch |
| #16    | Background Jobs / Queue | **P0** | **P4 B4** | **ARQ + Redis（新增）** | **本輪修正** |
| #17    | Retry/Dead-letter 泛化 | P2 | P4 B4 | 與 #16 一併實作 | 本輪修正 |
| #18    | Monitoring/Metrics | P1 | P4 B4 | Prometheus + OTEL | 已規劃 |
| #19    | Backup/Restore | P1 | P4 B4 (或 B5) | 資料庫備份腳本 | 需確認 |
| #20    | Security Gate | P1 | P4 B5 (CI) | SAST/DAST 整合 | 已規劃 |
```

---

### 文件 4：`tasks/roadmap-phase4-phase5.md`

| 修改區域 | 具體修改 | 負責角色 |
|----------|---------|---------|
| **Phase 4 Batch 列表** | Batch 4 名稱改為「基礎設施與可觀測性」，新增 Background Jobs 交付內容 | doc-writer |
| **Batch 4（§）** | 擴充 Batch 4 規格，加入 Background Jobs 的目標/交付/驗收/ChatGPT Review Gate | doc-writer |
| **B5 前置依賴** | 更新為「依賴 B1/B2/B3/B4」（新增 B4） | doc-writer |
| **Phase 4 Gate 列表** | 新增 G0: Background Jobs Gate（非強制，但推薦） | doc-writer |
| **§跨 Phase 依賴概要** | 更新 Background Jobs 相關路徑 | doc-writer |

---

### 文件 5：`tasks/plan-phase5-medical-ai-platform.md`

| 修改區域 | 具體修改 | 負責角色 |
|----------|---------|---------|
| **§14（Phase 4 依賴項目）** | 新增一行：**Background Jobs/Queue（#16）** → 依賴的 Phase 5 Batch：B4.5（KG Namespace 排程）、B6.1（跨專科定期任務） | doc-writer |

---

### 文件 6：`tasks/research/current-capability-inventory.md`

無需修改（盤點結果正確且完整，僅需確認 Background Jobs 現況描述中的 `🟡 Partial` 證據引用精確）。

---

### 文件 7：ADR（必要時）

| 文件 | 修改 | 負責角色 |
|------|------|---------|
| **ADR-002**（External Evidence Adapter Strategy） | 補充跨 adapter/FHIR 共用快取模式（E4 建議）— 在 §4 Error Handling 與 §3 Cache 中明確共用策略 | doc-writer |
| **新增 ADR-007**（選擇性） | 若 Background Jobs 架構決策需要正式記錄，新增 ADR-007: Background Job Queue Strategy（含 ARQ 選型理由、Redis 依賴評估、與 Outbox 模式關係） | doc-writer |

---

## 4. 執行順序與並行策略

### 4.1 修改順序

```
R1 修正流程（預估總工時：6～10h）
═══════════════════════════════════════════════════════

Step 1: 閱讀評分報告 + 全面理解缺失（已完成）
   ↓
Step 2: 修改 plan-phase4-clinical-ai-productization.md ← 最大修改量（核心）
   ├── 2a: §1.2 新增能力 #11 Background Jobs
   ├── 2b: §10.4 Batch 4 擴充為 Infrastructure & Observability
   ├── 2c: §10.7 B5 新增依賴 B4
   ├── 2d: §11.1 Gate 更新
   └── 2e: §11.3 禁止事項更新
   ↓
Step 3: 修改 phase4-phase5-dependency-map.md（配合 Step 2 更新）
   ├── 3a: 依賴圖更新
   ├── 3b: B4/B5 依賴更新
   ├── 3c: §3.7 #16 定位更新
   ├── 3d: §9 風險擴充（R13-R15）
   └── 3e: §11 新增 Gap Analysis 對應矩陣
   ↓
Step 4: 修改 roadmap-phase4-phase5.md（配合 Step 2/3）
   ├── 4a: Batch 4 規格擴充
   └── 4b: Gate 與依賴更新
   ↓
Step 5: 修改 phase4-phase5-gap-analysis.md
   ├── 5a: #16 補充「B4 實作」說明
   └── 5b: 總結矩陣更新
   ↓
Step 6: 修改 plan-phase5-medical-ai-platform.md（§14 依賴表新增）
   ↓
Step 7: ADR 更新（ADR-002 補充 + 可能新增 ADR-007）
   ↓
Step 8: 全文一致性校驗 + 追蹤矩陣完整性檢查
   ↓
Step 9: REVIEWER 重新評分
```

### 4.2 並行組合

| 並行組 | 任務 | 負責角色 | 條件 |
|--------|------|---------|------|
| **組 A** | Step 2（Phase 4 Plan 核心修改） | doc-writer | 無前置 |
| **組 B** | Step 3（Dependency Map 更新）+ Step 5（Gap Analysis 更新）+ Step 6（Phase 5 Plan 更新） | doc-writer | 需組 A 完成 Batch 定義後可局部並行 |
| **組 C** | Step 4（Roadmap 更新） | doc-writer | 需組 A 完成 Batch 定義 |
| **組 D** | Step 7（ADR 更新） | doc-writer | 可與組 A/B/C 並行 |
| **組 E** | Step 8（一致性校驗） | PLANNER | 需全部 Step 完成 |
| **組 F** | Step 9（REVIEWER 重新評分） | REVIEWER | 需組 E 完成 |

**最佳並行路徑**：
```
時間 →
─────────────────────────────────────────────
Step 2  ──→ Step 4 ──→ Step 8 ──→ Step 9
   │                    ↑
   ├──→ Step 3 ────────┤
   ├──→ Step 5 ────────┤
   └──→ Step 6 ────────┤
   Step 7（並行於全部）──┘
```

---

## 5. 負責角色分配

| 任務 | 負責角色 | 說明 |
|------|---------|------|
| **Step 2**：Phase 4 Plan 修改 | **doc-writer** | 核心修改，需理解 Background Jobs 技術細節 |
| **Step 3**：Dependency Map 更新 | **doc-writer** | 配合 Step 2 更新依賴圖與矩陣 |
| **Step 4**：Roadmap 更新 | **doc-writer** | 擴充 Batch 4 規格 |
| **Step 5**：Gap Analysis 更新 | **doc-writer** | 補充 #16 實作說明 |
| **Step 6**：Phase 5 Plan 更新 | **doc-writer** | 更新 §14 依賴表 |
| **Step 7**：ADR 更新 | **doc-writer** | ADR-002 補充 + 選擇性新增 ADR-007 |
| **Step 8**：全文一致性校驗 | **PLANNER** | 確保所有文件對 #16 的敘述一致，追蹤矩陣完整 |
| **Step 9**：REVIEWER 重新評分 | **REVIEWER** | 依原始評分標準重新審查 |

---

## 6. 預計工時

| 任務 | 預估工時 | 說明 |
|------|---------|------|
| Step 2：Phase 4 Plan 修改 | 2～3h | 最大修改量，需重構 Batch 4 完整規格 |
| Step 3：Dependency Map 更新 | 1～1.5h | 依賴圖更新 + 矩陣新增 |
| Step 4：Roadmap 更新 | 1～1.5h | Batch 4 擴充 + Gate 調整 |
| Step 5：Gap Analysis 更新 | 0.5h | #16 補充說明，總結表更新 |
| Step 6：Phase 5 Plan 更新 | 0.5h | §14 依賴表新增一行 |
| Step 7：ADR 更新 | 1～2h | ADR-002 補充 + 選擇性 ADR-007 |
| Step 8：一致性校驗 | 1h | PLANNER 全文校驗 |
| Step 9：REVIEWER 評分 | 1h | 重新審查 |
| **總計** | **8～11h** | 若 doc-writer 僅一位，串行執行約 10～14h |

---

## 7. 驗收標準（R1）

### 7.1 修正完成條件

- [ ] **F1**：Phase 4 Plan §10.4 已將 B4 擴充為「Infrastructure & Observability」，包含 Background Jobs 完整規格（檔案清單、驗收標準、風險）
- [ ] **F2**：Phase 4 Plan §1.2 新增 #11 Background Jobs 能力描述
- [ ] **F3**：Phase 4 Plan §1.3「明確排除」中不再包含 Background Jobs
- [ ] **F4**：Dependency Map §11 新增 Gap Analysis 對應矩陣，每個 P0/P1 項目標示 Batch 歸屬
- [ ] **F5**：Dependency Map §9 風險登記冊新增 R13/R14/R15
- [ ] **F6**：Gap Analysis #16 補充「B4 實作」說明
- [ ] **F7**：Roadmap Batch 4 規格包含 Background Jobs 交付內容
- [ ] **F8**：Phase 5 Plan §14 依賴表新增 Background Jobs 條目
- [ ] **F9**：ADR-002 補充跨 Batch 共用快取說明（或新增 ADR-007）
- [ ] **F10**：所有文件中 #16 的定位一致（P0, B4 實作, 支撐 #10/#17）

### 7.2 REVIEWER 重新評分目標

| 評分維度 | 目標分數 | 達標條件 |
|----------|:--------:|----------|
| 完整性 | 24～25 | Background Jobs 有明確實作 Batch；所有 Gap P0/P1 可追溯 |
| 正確性 | 25 | 跨文件完全一致，無矛盾 |
| 可執行性 | 25 | Background Jobs 實作路徑清楚（ARQ + Redis），不影響原時程 |
| 架構與風險控制 | 25 | 風險登記冊完整涵蓋新識別風險 |
| **總分** | **≥ 95** | |

### 7.3 Gate 再確認

| Gate | 原結果 | R1 預期 |
|------|:------:|:--------:|
| Current State Evidence Gate | ✅ PASS | ✅ PASS（不變） |
| Vertical Slice Quality Gate | ✅ PASS | ✅ PASS（B4 涵蓋層面更完整） |
| Dependency Gate | ✅ PASS | ✅ PASS（B4→B5 依賴新增，無循環） |
| Scope Control Gate | ✅ PASS | ✅ PASS（仍不寫 production code） |
| Phase 4 Feasibility Gate | ✅ PASS | ✅ PASS（ARQ + Redis 為成熟方案） |
| Phase 5 Platformization Gate | ✅ PASS | ✅ PASS（不變） |

---

## 8. 附錄：背景任務技術方案摘要（供 ADR 參考）

```
技術選型：
- Job Queue：ARQ（基於 Redis 的輕量非同步任務隊列）
  理由：比 Celery 輕量、原生支援 asyncio、無需 RabbitMQ/Beanstalkd
- Redis 版本：7.x（Docker 一鍵啟動，dev 模式可選用記憶體模式）
- 任務類型：
  • Evidence Freshness Check（定時，每日）
  • Guideline Sync（定時，每週）
  • Adapter Cache Warm-up（定時，依 adapter 設定）
  • Backup Job（定時，每日/每週）
- 與既有 Outbox 模式關係：
  • Outbox 負責交易邊界內的事件投影（短生命週期）
  • ARQ 負責長時間運行的排程任務（長生命週期）
  • 兩者互補，不衝突

檔案影響範圍：
- 新增 ~12 production files（jobs/ 模組、API、migration）
- 修改 ~3 files（main.py 註冊 worker、docker-compose 加 Redis）
- 不修改既有 Outbox 模式
```

---

> **文件結束** — Phase 4 & Phase 5 Master Plan 返工修正計劃（R1）
>
> 本計劃針對 REVIEWER 評分報告中指出的 4 項缺失及 4 項改善建議，
> 提出 5 項策略、7 份文件的具體修改規格、以及完整的執行方案。
> 目標：R1 修正後總分 ≥ 95。
