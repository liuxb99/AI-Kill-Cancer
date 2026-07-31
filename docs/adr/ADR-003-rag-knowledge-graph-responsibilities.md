# ADR-003: RAG and Knowledge Graph Responsibilities

**Status**: Accepted (Phase 4)

**Date**: 2026-07-31

## Context

系統在 Phase 4 將同時擁有兩種知識檢索與推理基礎設施：

1. **Knowledge Graph (KnowGraphGo)** — 既有，13 個 Go packages，支援推論、模式匹配、遍歷、本體操作。儲存結構化臨床知識實體及其關係。
2. **RAG / Vector DB** — Phase 4 新建，預計使用 Chroma 或 Qdrant，搭配 Embedding Pipeline，支援臨床文獻與證據的語義搜尋。

這兩個元件在功能上有重疊可能：

- 兩者都能回答「某基因變異與某藥物的關係」
- 兩者都能用於 Agent 的知識檢索
- 兩者都可能作為 Clinical Decision Engine 的輸入來源

需要明確定義：

1. **RAG 和 Knowledge Graph 各自的職責邊界是什麼？**
2. **什麼場景應該使用 RAG，什麼場景應該使用 KG？**
3. **兩者如何協同工作？**
4. **資料一致性如何維護？**
5. **Agent 和 Engine 應該如何選擇資料來源？**

## Decision

### 1. 職責邊界：KG 為「結構化知識推理」，RAG 為「非結構化語義檢索」

| 維度 | Knowledge Graph (KnowGraphGo) | RAG / Vector DB |
|------|------------------------------|-----------------|
| **知識類型** | 結構化實體與關係（gene, drug, variant, evidence） | 非結構化文本（文獻全文、guideline PDF、臨床筆記） |
| **查詢方式** | 精確匹配、圖遍歷、推理、模式匹配 | 語義相似度檢索（向量距離） |
| **輸出** | 確定性的事實集合與推理結果 | 排序後的文本片段 + 相似度分數 |
| **確定性** | 高（規則驅動、可解釋、確定性） | 中（依賴 embedding 品質和檢索參數） |
| **適用場景** | 「這個變異已知的臨床意義是什麼？」「某藥物作用於哪些基因？」 | 「關於這個治療方案的最近文獻怎麼說？」「類似病例的處理方式？」 |
| **資料來源** | 結構化資料庫（CIViC, DGIdb, OncoTree） | 學術文獻、臨床指南 PDF、內部知識庫 |
| **實作技術** | Graph + Go 推理引擎 | Vector DB + Embedding Model + LLM |

### 2. 查詢路由策略：由 Clinical Intelligence Layer 統一調度

建立 `src/backend/clinical/intelligence_service.py`（Clinical Intelligence Service），作為 Agent 和 Engine 查詢知識的統一入口：

```
Agent / Engine
      │
      ▼
Clinical Intelligence Service
      │
      ├── Knowledge Type == 結構化事實 ? ──→ Knowledge Graph API
      │
      ├── Knowledge Type == 非結構化文本 ? ──→ RAG Service
      │
      └── Knowledge Type == 混合 ? ──→ 並行查詢 → Fusion
```

判斷依據：
- Agent 發出查詢時，需指定 `knowledge_type`（`structured` / `unstructured` / `mixed`）
- 若未指定，由 Intelligence Service 根據查詢內容自動推斷
- **預設路由**：臨床決策相關（變異意義、藥物交互、guideline 規則）→ KG；文獻回顧、最新研究 → RAG

### 3. 協同模式：KG 提供「已知確定事實」，RAG 提供「延伸語境」

在 Agent Decision Pipeline 中，兩者的協作方式：

```
Step 1: Agent 收到查詢
Step 2: Agent 呼叫 Clinical Intelligence Service
Step 3: Intelligence Service 並行查詢 KG 和 RAG（若需要）
Step 4: KG 回傳結構化事實（精確）
Step 5: RAG 回傳相關文獻片段（語義）
Step 6: Agent 合併結果 → Reasoning Service → 最終判斷
```

**不採用「RAG 結果餵入 KG」或「KG 結果餵入 RAG」的串聯模式**，以避免知識污染和延遲擴大。

### 4. 資料一致性：不作強一致性保證

- KG 和 RAG 的資料來源本質不同（結構化資料庫 vs 自然語言文本），不存在同一資料的兩份拷貝
- 若有重疊主題（如某藥物的資訊在 KG 和 RAG 中同時存在），以 KG 的結構化資料為準
- Vector DB 的 embedding 更新頻率獨立於 KG 更新

### 5. 不採用「純 RAG 取代 KG」或「純 KG 取代 RAG」

理由：
- KG 擅長的推理任務（模式匹配、路徑遍歷）是 RAG 無法做到的
- RAG 擅長的開放式語義檢索是 KG 無法做到的
- 兩者在臨床決策中扮演互補角色，缺一不可

## Consequences

### Positive

- **明確的職責分界**：開發者知道新功能應使用哪種基礎設施
- **避免重複建設**：不需要在 KG 中儲存全文資訊，也不需要將 RAG 設計成推理引擎
- **平行開發**：KG 團隊（Go）和 RAG 團隊（Python + Vector DB）可獨立工作
- **查詢效率**：Agent 可根據知識類型精準選擇查詢路徑，減少不必要的 API 呼叫

### Negative

- **增加 Intelligence Service 複雜度**：需要實現查詢路由邏輯和結果融合
- **混合查詢的延遲**：並行查詢兩套系統可能增加端到端延遲
- **推理鏈記錄複雜度增加**：Digital Thread 需要同時追蹤 KG 和 RAG 的貢獻

### Risk

| 風險 | 影響 | 緩解措施 |
|------|------|---------|
| Agent 不當選擇知識類型導致錯誤結果 | 中 | Intelligence Service 提供自動推斷；Digital Thread 記錄知識來源供審計 |
| RAG 回傳不相關結果 | 中 | 設定相似度 threshold；支援 Agent 要求最低分數 |
| KG 和 RAG 對同一問題給出矛盾資訊 | 低 | 以 KG 為準（結構化資料優先級高於非結構化） |

## Related

- Phase 4 Master Plan §2.2.1 Clinical Intelligence Layer
- Phase 4 Master Plan §7 Knowledge Graph Boundary
- Phase 4 Master Plan §3 Data Flow (Reasoning + RAG integration)
