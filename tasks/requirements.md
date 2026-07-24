# AI-Kill-Cancer Phase 3A

Repository：https://github.com/liuxb99/AI-Kill-Cancer

Branch：master

目前狀態：
- Phase 1 ✅ 完成
- Phase 2 ✅ 完成（CI/CD、GitHub Actions、Vercel、Production、Secrets 已驗收）
- Phase 3 開始

---

# 本輪目標

開始真正的 Clinical Intelligence。

不是再做部署、CI、Workflow、Docker、Vercel — 那些全部停止。

---

# 本輪一次完成

建立 Drug Recommendation Engine V1，完整鏈路：

Variant → Evidence → Drug → Evidence Score → Drug Score → Rank → Recommendation

---

# 必做功能

## 1. Recommendation Engine
建立 RecommendationEngine、RecommendationRule、EvidenceAggregator、DrugRanker。不要寫死，全部規則化。

## 2. Evidence Weight / Tier / Confidence / Evidence Level
支援 FDA、NCCN、OncoKB、CIViC、DGIdb、OpenCRAVAT 等來源。全部可擴充。

## 3. Drug Ranking
包含 Overall Score、Evidence Score、Sensitivity、Resistance、Conflict Score。最終排序輸出 Top N。

## 4. Explainable AI
每個 Recommendation 必須產生 Reason、Evidence、Source、Score Detail。例如：為何第一名、為何第二名、為何被扣分、哪些證據支持。全部可追溯。

## 5. Calculation Trace
沿用既有架構：Input → Evidence → Score → Recommendation → Output。所有計算必須 Traceable。

## 6. JSON Schema
建立 RecommendationResult、DrugScore、EvidenceScore、RecommendationReason，全部 Versioned。

## 7. API
POST /recommendation 以及 GET /recommendation/{id}

## 8. Report
HTML Drug Recommendation Report，包含 Patient、Variants、Evidence、Top Drugs、Reason、Warnings、Trace。

## 9. Frontend
不要重新設計，只補 Recommendation Page。

## 10. Test
至少 Unit Tests、Integration Tests、API Tests、Golden Tests，全部通過。

---

# 品質要求

不得有 Placeholder、TODO、Fake Data、Mock Recommendation。正式完成。

---

# 驗證

完成後須執行：go test ./...、Frontend build、Backend build、API Smoke Test、Coverage、Git Diff，全部完成。

---

# Git

全部完成後一次 git add、git commit、git push。不要中途回報。

---

# Reviewer

Reviewer 重新閱讀 tasks/requirements.md，重新確認需求是否全部完成。必須執行 Step 4b Requirement Regression Check。低於 90 分直接返工。

---

# 最後回報

只回報：Commit SHA、修改檔案數、新增 API、新增 Package、新增 Tests、Coverage、Build、Test、Push、Reviewer Score。不要貼程式碼。
