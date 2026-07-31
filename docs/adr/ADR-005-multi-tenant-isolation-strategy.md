# ADR-005: Multi-Tenant Isolation Strategy

**Status**: Accepted (Phase 5)

**Date**: 2026-07-31

## Context

Phase 5 需要引入 Multi-Tenant（多租戶）架構，使同一個 Medical AI Platform 可以服務多個醫療機構（醫院、診所、研究機構），每個 Tenant 的資料嚴格隔離。

目前系統為單一 tenant 設計（單一 PostgreSQL database），所有 Case 和 Clinical Data 共用資料表。

需要決策的核心問題：

1. **隔離模式**：Shared Database vs Separate Database vs Schema-based Isolation？
2. **Tenant 識別**：如何確定當前請求屬於哪個 Tenant？
3. **資料層隔離**：Repository 層如何自動加入 tenant 過濾？
4. **檔案/快取/佇列隔離**：非結構化資料如何隔離？
5. **跨 Tenant 操作**：是否存在需要跨 Tenant 查詢的場景？
6. **Tenant 配置**：不同 Tenant 可能有不同的功能開關和配置參數？

## Decision

### 1. 採用「Shared Database + Row-Level Tenant Isolation」模式

| 維度 | 方案 | 理由 |
|------|------|------|
| **資料庫** | 單一 PostgreSQL database + 所有 tenant 共用表 | 降低運維複雜度；單一資料庫即可支撐初期 5-20 個 Tenant |
| **隔離方式** | 每張資料表增加 `tenant_id` 欄位 | 最輕量的隔離方案，無需 Schema 切換或跨 DB 查詢 |
| **存取控制** | Repository 層自動過濾 + API Middleware 驗證 | 確保開發者不會遺漏 tenant 過濾 |

**不採用**：
- ❌ Single Database per Tenant：初期運維成本過高，且 PostgreSQL 連線數可能不足
- ❌ Schema per Tenant：不支援 PostgreSQL 的 Schema 級別隔離不如 row-level 靈活
- ❌ Database per Tenant：留待 Phase 6 當 Tenant 數量 > 100 且合規要求更高時採用

### 2. Tenant 識別：JWT Claim + Middleware

```
請求流程：
1. Request → API Gateway
2. TenantMiddleware 從 JWT 解析 tenant_id
3. Middleware 將 tenant_id 存入 Request Context
4. Repository Layer 自動從 Context 讀取 tenant_id
5. 所有 SQL Query 自動附加 WHERE tenant_id = ?
```

- JWT 中必須包含 `tenant_id` claim（由 Tenant Admin API 配發）
- 不支援 URL Path-based tenant 識別（如 `/api/v1/hospital-a/patients`），避免 URL 設計複雜化
- 支援 Anonymous Tenant（公共資料，無需登入即可查詢的知識庫）

### 3. Repository 層隔離：TenantAwareRepository Mixin

```python
class TenantAwareRepository(ABC):
    """自動處理 tenant 隔離的 Repository 基底"""
    
    @property
    def tenant_id(self) -> UUID:
        """從當前請求上下文取得 tenant_id"""
        return get_current_tenant_id()
    
    async def _apply_tenant_filter(self, query: Query) -> Query:
        """為查詢自動附加 tenant 過濾"""
        if self.requires_tenant_filter():
            query = query.where(self.model.tenant_id == self.tenant_id)
        return query
    
    async def find_by_id(self, id: UUID) -> T | None:
        """自動過濾 tenant（override 父類別的 find_by_id）"""
        query = select(self.model).where(
            self.model.id == id,
            self.model.tenant_id == self.tenant_id  # 自動加入
        )
        ...
```

**隔離範圍**：

| 資料類型 | 隔離策略 | 備註 |
|---------|---------|------|
| 病患資料（Patient, Case） | ✅ Row-level tenant_id | 核心隔離需求 |
| 臨床決策（Decision, TreatmentPlan） | ✅ Row-level tenant_id | 核心隔離需求 |
| 知識庫資料（Knowledge, Evidence） | 🟡 可選隔離 | 部分知識庫為全域共用 |
| 設定（Config） | ✅ Tenant-specific config | 使用 TenantConfigRegistry |
| Audit Log | ✅ Row-level tenant_id | 包含 tenant 資訊以便審計 |

### 4. 檔案/快取隔離

| 資源 | 隔離策略 |
|------|---------|
| **File Storage** | 目錄隔離：`/data/{tenant_id}/uploads/` |
| **Vector DB** | 使用不同的 Collection Prefix：`{tenant_id}_documents` |
| **In-Memory Cache** | Key Prefix：`{tenant_id}:{key}` |
| **Background Jobs** | Job 資料結構包含 tenant_id，worker 依 tenant 分類處理 |

### 5. Tenant Admin API

提供 Tenant CRUD 管理端點，僅限 Platform Admin 角色存取：

```
POST   /api/v2/tenants                    — 建立 Tenant
GET    /api/v2/tenants                    — 列出所有 Tenant
GET    /api/v2/tenants/{id}               — 查詢 Tenant 詳情
PUT    /api/v2/tenants/{id}              — 更新 Tenant 配置
DELETE /api/v2/tenants/{id}              — 停用 Tenant（軟刪除）
```

- Tenant 建立時自動建立對應的 JWT signing key
- Tenant 配置儲存在 `tenant_config` 表中，支援 JSON Schema 驗證

### 6. 跨 Tenant 操作限制

- **預設禁止跨 Tenant 資料存取**：任何跨越 Tenant 邊界的資料查詢需明確宣告並經 Platform Admin 審核
- **例外場景**：Global Knowledge Base、Platform Health Dashboard、Cross-tenant Analytics（Phase 6 選項）
- 跨 Tenant 查詢使用明確的 `AdminQuery` 介面，不走普通 Repository

## Consequences

### Positive

- **最低運維複雜度**：單一資料庫、單一套部署，但支援多 Tenant
- **開發簡單**：Repository 層自動處理 tenant 過濾，開發者不需手動檢查
- **低成本起步**：支援從 1 個 Tenant 平滑擴充到數十個 Tenant
- **既有功能不受影響**：單 Tenant 部署時，tenant_id 使用預設值，隔離層透明

### Negative

- **Row-level 隔離不如 Database 級別安全**：無法防止程式 bug 導致的資料洩漏（需仰賴測試和審計）
- **所有資料表需 migration 增加 tenant_id**：影響既有 schema
- **查詢效率因 WHERE tenant_id= 而輕微下降**：需在 tenant_id 上建立索引
- **跨 Tenant 查詢需要特殊處理**

### Risk

| 風險 | 影響 | 緩解措施 |
|------|------|---------|
| 程式碼 bug 導致 tenant A 看到 tenant B 的資料 | 高 | Repository 層自動過濾 + Integration Test + Security Audit |
| Tenant 資料刪除需求 | 中 | 軟刪除（deactivated）+ 資料保留政策 |
| Tenant 數量增長導致查詢效能下降 | 低 | tenant_id 索引 + 必要時分表 |

## Related

- Phase 5 Master Plan §9 Tenant Isolation
- Phase 5 Master Plan §12.6 Batch 5 (Tenant Isolation + API Versioning)
- ADR-006 (Specialty Module Architecture) — Specialty 的 tenant-aware 行為
