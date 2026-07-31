# ADR-002: External Evidence Adapter Strategy

**Status**: Accepted (Phase 4)

**Date**: 2026-07-31

## Context

Phase 4 需要將 8 個外部證據源 adapter 從 stub 升級為真實 REST API 連接：

| Adapter | 資料源 | 當前狀態 |
|---------|--------|---------|
| CIViC | 臨床變異解讀資料庫 | stub |
| DGIdb | 藥物-基因交互資料庫 | stub |
| OncoTree | 腫瘤類型 ontology | stub |
| MyVariant.info | 變異註釋服務 | stub |
| DRKG | 藥物關聯知識圖譜 | stub |
| PharmCAT | 藥物基因組學 | stub |
| Ensembl VEP (local) | 變異效應預測 | stub |
| OpenCRAVAT | 綜合變異註釋 pipeline | stub |

需要決策的核心問題：

1. **Adapter 架構模式**：每個 adapter 獨立實作，還是共用統一的 adapter 框架？
2. **同步 vs 非同步**：查詢外部 API 應採用同步請求還是非同步事件驅動？
3. **快取策略**：是否需要快取？快取的生命週期如何管理？
4. **錯誤處理**：外部服務不可用時的行為（重試、降級、熔斷）？
5. **配置管理**：API key、endpoint URL、rate limit 等配置如何管理？
6. **Adapter Registry**：是否需要 registry 機制讓 adapter 可被動態發現？

## Decision

### 1. 採用「統一 Adapter 基底類別 + 獨立實作」模式

建立 `src/backend/adapters/base.py` 定義抽象基底類別 `BaseEvidenceAdapter`：

```python
class BaseEvidenceAdapter(ABC):
    """所有外部證據源的統一介面基底"""
    
    # 中繼資料
    source_id: str          # 唯一識別碼，如 "civic"
    display_name: str
    version: str
    config_schema: dict     # JSON Schema for adapter 配置
    
    @abstractmethod
    async def search(self, query: EvidenceQuery) -> EvidenceResult: ...
    
    @abstractmethod
    async def health_check(self) -> HealthStatus: ...
    
    # 可覆寫的生命週期方法
    async def initialize(self) -> None: ...
    async def shutdown(self) -> None: ...
```

每個 adapter 獨立繼承此基底類別，各自實作 API 呼叫邏輯。

### 2. 採用同步請求模式（非事件驅動）

- 使用 `httpx.AsyncClient` 進行非阻塞 HTTP 請求
- 不引入事件佇列（Kafka/Redis）— 目前流量不足以證明其必要性
- 未來若需大規模非同步處理，可在 adapter 內部加入 queue，不影響外部介面

### 3. 兩層快取策略

| 層級 | 儲存位置 | TTL | 用途 |
|------|---------|-----|------|
| L1: In-Memory Cache | Python dict / LRU | 5-15 分鐘 | 同 request 生命週期內的重複查詢 |
| L2: Database Cache | `evidence_cache` table | 1-24 小時（依資料源類型） | 跨 request 的快取 |

- L1 使用 `cachetools.TTLCache` 實作
- L2 使用既有 Database + Repository 模式
- 快取失效策略：TTL 過期後被動失效，不主動推送

### 4. 錯誤處理採用「Fail-fast + Circuit Breaker + Graceful Degradation」

| 錯誤類型 | 行為 | 適用情境 |
|---------|------|---------|
| 暫時性錯誤（Timeout/429/5xx） | 重試 2 次（指數退避）→ 回傳 degraded 結果 | 所有 adapter |
| 持續性錯誤 | Circuit Breaker 開啟（30s）→ 回傳 cached/empty | API-based adapter |
| 配置錯誤 | 啟動時即失敗（fail-fast），不影響系統運行 | 所有 adapter |
| 資料源離線 | `health_check()` 回傳 degraded，不阻斷系統 | 可離線執行的 adapter |

Circuit Breaker 使用 `pybreaker` 或自實作輕量版本。

### 5. 配置外部化

- Adapter 配置（API key, endpoint, timeout, rate limit）透過環境變數或 YAML 設定檔注入
- 使用 Pydantic `BaseSettings` 管理配置
- 支援 runtime 重新載入（透過 health check 端點觸發）

### 6. 不建立獨立的 Adapter Registry（沿用現有載入機制）

目前系統在啟動時靜態載入所有 adapter。Phase 4 維持此模式：
- 在 `src/backend/adapters/__init__.py` 中匯入所有 adapter 實例
- 透過 `AdapterService` 統一管理
- Adapter Registry 留待 Phase 5 引入多專科證據源時再實作

## Consequences

### Positive

- **統一介面降低新 adapter 開發成本**：新人只需繼承 `BaseEvidenceAdapter` 並實作 `search()` 和 `health_check()`
- **快取減少外部 API 呼叫**：減少 latency 和 API 用量配額消耗
- **Graceful Degradation 確保系統韌性**：單一外部資料源不可用時不影響整體系統
- **配置外部化便於部署**：不同環境（dev/staging/prod）可設定不同的 endpoint
- **適配器快取層可與 B4（Infrastructure & Observability）的 Redis 共用**：L2 快取無需獨立 Redis 實例，可複用 B4 既有的 Redis 基礎設施，降低運維成本

### Negative

- **缺乏動態註冊**：新增 adapter 需修改程式碼重新部署（Phase 5 才解決）
- **同步模型對長時間查詢不友好**：若某 adapter 回應時間 > 30s，會阻塞請求線程
- **L2 快取可能提供過時資料**：需依賴 TTL 控制，無法即時反映外部資料源的變更

### Risk

| 風險 | 影響 | 緩解措施 |
|------|------|---------|
| 外部 API 速率限制導致查詢失敗 | 中 | 實現 rate limiter + queue；L2 快取優先回傳 |
| API key 洩漏 | 高 | 使用環境變數 + .env 檔案，不寫入程式碼；CI 掃描 secret |
| 外部服務變更 API | 中 | 每個 adapter 標記版本；CI 中執行 adapter health check |
| 跨 Batch 共用基礎設施未在 B4 設計中考慮 | 中 | 適配器快取層共用 B4 Redis 等跨 Batch 基礎設施依賴，需在 B4（Infrastructure & Observability）設計階段明確納入考量，避免後續整合衝突 |

## Related

- Phase 4 Master Plan §2.2.1 Clinical Intelligence Layer (Evidence Store)
- Phase 4 Master Plan §8 External Evidence Boundary
- ADR-006 (Specialty Module Architecture) — Phase 5 的 EvidenceSourceRegistry
