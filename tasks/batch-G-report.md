# Batch G：Migration 驗證報告

## 017 Migration 定義

**檔案**: `migrations/versions/017_phase3a_recommendation_tables.py`  
**Revision**: 017  
**Down Revision**: 016  
**目的**: 新增 Phase 3A 推薦引擎所需的 3 張資料表

### 建立的 Tables

#### 1. `domain_recommendations`
| 欄位 | 類型 | Nullable | 約束 / 備註 |
|------|------|----------|-------------|
| id | String(36) | NO | Primary Key |
| recommendation_id | String(64) | NO | UNIQUE, INDEX |
| patient_id | String(36) | NO | FK → domain_patients.id (ON DELETE CASCADE), INDEX |
| case_id | String(36) | YES | FK → domain_cancer_cases.id (ON DELETE SET NULL), INDEX |
| trace_id | String(64) | YES | INDEX |
| engine_version | String(32) | NO | server_default = "1.0.0" |
| status | String(32) | NO | server_default = "pending" |
| request_payload | JSON | YES | |
| result_payload | JSON | YES | |
| report_html | Text | YES | |
| created_by | String(36) | YES | FK → domain_users.id (ON DELETE SET NULL) |
| created_at | DateTime | NO | server_default = func.now() |
| updated_at | DateTime | NO | server_default = func.now() |

**Foreign Keys**:
- `patient_id` → `domain_patients(id)` ON DELETE CASCADE
- `case_id` → `domain_cancer_cases(id)` ON DELETE SET NULL
- `created_by` → `domain_users(id)` ON DELETE SET NULL

**Indexes**: recommendation_id (unique), patient_id, case_id, trace_id

**JSON/JSONB 使用**: `request_payload` (JSON), `result_payload` (JSON)

---

#### 2. `domain_recommendation_traces`
| 欄位 | 類型 | Nullable | 約束 / 備註 |
|------|------|----------|-------------|
| id | String(36) | NO | Primary Key |
| trace_id | String(64) | NO | UNIQUE, INDEX |
| recommendation_id | String(36) | YES | FK → domain_recommendations.id (ON DELETE CASCADE), INDEX |
| created_at | DateTime | NO | server_default = func.now() |

**Foreign Keys**:
- `recommendation_id` → `domain_recommendations(id)` ON DELETE CASCADE

**Indexes**: trace_id (unique), recommendation_id

---

#### 3. `domain_recommendation_trace_steps`
| 欄位 | 類型 | Nullable | 約束 / 備註 |
|------|------|----------|-------------|
| id | String(36) | NO | Primary Key |
| trace_id | String(36) | NO | FK → domain_recommendation_traces.id (ON DELETE CASCADE), INDEX |
| step_order | Integer | NO | |
| step_type | String(64) | NO | |
| input_summary | JSON | YES | |
| output_summary | JSON | YES | |
| evidence_references | JSON | YES | |
| weight | Float | YES | |
| score | Float | YES | |
| rank | Integer | YES | |
| status | String(32) | NO | server_default = "pending" |
| created_at | DateTime | NO | server_default = func.now() |

**Foreign Keys**:
- `trace_id` → `domain_recommendation_traces(id)` ON DELETE CASCADE

**Indexes**: trace_id

**JSON/JSONB 使用**: `input_summary` (JSON), `output_summary` (JSON), `evidence_references` (JSON)

---

## Migration 測試結果

**檔案**: `tests/test_migration.py`

注意：因本環境無 shell 指令執行工具，**無法實際執行 pytest**，以下為靜態分析結果。

### Test Cases（TestMigration017）

| Test Case | 預期結果 |
|-----------|----------|
| `test_upgrade_016_to_017_creates_tables` | 016→017 upgrade 後三張新 table 存在 |
| `test_downgrade_017_to_016_removes_tables` | 017→016 downgrade 後三張 table 被移除 |
| `test_upgrade_again_after_downgrade` | downgrade 後重新 upgrade 仍成功 |
| `test_migration_017_file_exists` | 017 檔案存在且 revision/down_revision 正確 |
| `test_migration_016_exists_as_prerequisite` | 016 檔案存在 |
| `test_upgrade_017_tables_have_expected_columns` | 各 table 欄位符合預期 |
| `test_upgrade_017_preserves_016_tables` | 017 upgrade 不破壞 016 既有的 table |

**結論**: 測試案例設計完整，涵蓋 upgrade、downgrade、idempotent、欄位驗證、向後相容。若環境可執行，預期全數 PASS。

---

## Model vs Migration 比對

**Model 檔案**: `src/backend/domain/recommendation.py`

### 核心發現：`CompatUUID` vs `String(36)`

在 `src/backend/database/models.py` 中，`CompatUUID` 定義為：
```python
class CompatUUID(TypeDecorator):
    impl = String(36)
    cache_ok = True
```

因此 `CompatUUID` 在資料庫層實際儲存為 `String(36)`。Migration 中的 `String(36)` 與 Model 中的 `CompatUUID` **在資料庫 schema 層級完全一致**。

### 逐欄位比對

#### `domain_recommendations`

| 欄位 | Migration 類型 | Model 類型 | 一致？ |
|------|---------------|-----------|--------|
| id | String(36) | CompatUUID | ✅ (CompatUUID → String(36)) |
| recommendation_id | String(64) | String(64) | ✅ |
| patient_id | String(36) FK | CompatUUID FK | ✅ |
| case_id | String(36) FK, NULL | CompatUUID FK, NULL | ✅ |
| trace_id | String(64), NULL | String(64), NULL | ✅ |
| engine_version | String(32), server_default | String(32), default | ⚠️ 機制不同但值同 |
| status | String(32), server_default | String(32), default | ⚠️ 機制不同但值同 |
| request_payload | JSON, NULL | JSON, NULL | ✅ |
| result_payload | JSON, NULL | JSON, NULL | ✅ |
| report_html | Text, NULL | Text, NULL | ✅ |
| created_by | String(36) FK, NULL | CompatUUID FK, NULL | ✅ |
| created_at | DateTime, server_default=now() | DateTime, default=utcnow | ⚠️ 機制不同 |
| updated_at | DateTime, server_default=now() | DateTime, default=utcnow, onupdate | ⚠️ Model 多了 onupdate |

#### `domain_recommendation_traces`

| 欄位 | Migration 類型 | Model 類型 | 一致？ |
|------|---------------|-----------|--------|
| id | String(36) | CompatUUID | ✅ |
| trace_id | String(64) | String(64) | ✅ |
| recommendation_id | String(36) FK, NULL | CompatUUID FK, NULL | ✅ |
| created_at | DateTime, server_default=now() | DateTime, default=utcnow | ⚠️ 機制不同 |

#### `domain_recommendation_trace_steps`

| 欄位 | Migration 類型 | Model 類型 | 一致？ |
|------|---------------|-----------|--------|
| id | String(36) | CompatUUID | ✅ |
| trace_id | String(36) FK | CompatUUID FK | ✅ |
| step_order | Integer | Integer | ✅ |
| step_type | String(64) | String(64) | ✅ |
| input_summary | JSON, NULL | JSON, NULL | ✅ |
| output_summary | JSON, NULL | JSON, NULL | ✅ |
| evidence_references | JSON, NULL | JSON, NULL | ✅ |
| weight | Float, NULL | Float, NULL | ✅ |
| score | Float, NULL | Float, NULL | ✅ |
| rank | Integer, NULL | Integer, NULL | ✅ |
| status | String(32), server_default | String(32), default | ⚠️ 機制不同但值同 |
| created_at | DateTime, server_default=now() | DateTime, default=utcnow | ⚠️ 機制不同 |

### 不一致項目說明

| 差異 | 說明 | 嚴重性 |
|------|------|--------|
| `server_default` vs `default` | Migration 使用資料庫層預設值，Model 使用 Python/ORM 層預設值。兩者並存是標準做法，Alembic 自動產生的 migration 通常只保留 `server_default`。 | ⚠️ 低 — 設計選擇，非錯誤 |
| Model `updated_at` 有 `onupdate` | `onupdate` 是 SQLAlchemy ORM 層功能，不會也不應該出現在 migration 中。 | ✅ 正常 |
| `CompatUUID` vs `String(36)` | `CompatUUID` 底層即為 `String(36)`，資料庫定義一致。 | ✅ 完全一致 |

### 綜合結論

**Model 與 Migration 功能上一致**，所有欄位名稱、型別、nullable、FK、index 皆吻合。細微差異僅為 ORM 層 vs 資料庫層的設計取捨，不影響 schema 正確性。

---

## 是否需要 018 Migration

### 判斷：不需要 ❌

**原因**：
1. **Model 與 Migration 017 的 schema 定義一致** — 無遺漏欄位、無型別衝突、無缺少的 FK 或 index
2. **無 018 檔案存在** — 目前未建立也未需要
3. **所有差異屬正常設計模式**：
   - `server_default` vs `default`：兩者互補，非衝突
   - `CompatUUID` vs `String(36)`：底層相同
   - `onupdate`：為 ORM 層功能，不影響 migration
4. **無新欄位需求** — 目前 Model 不需要新增欄位

### 未來若需建立 018 的情境
- 新增或修改任何 table 欄位定義
- 新增 index 或唯一約束
- 改變 FK 行為（如 ondelete 策略）
- 引入新 table

---
*報告產生時間：2026-07-22*  
*驗證人：Batch G 子代理*
