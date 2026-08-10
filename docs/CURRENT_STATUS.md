# Current Status

更新日期：2026-08-10

AI-Kill-Cancer 當前產品 release line：**1.0.3 candidate**。

工程 roadmap milestone：**Local-First Research & Demo Showcase（代號 v0.3.0）**。

> `v0.3.0` 是 roadmap / engineering milestone，不再當作產品 SemVer。倉庫既有產品版本已是 1.0.2，因此本輪 release 正確向前收斂到 1.0.3，避免版本倒退。

架構政策：Local SQLite 是主要持久化研究工作資料庫；Vercel 使用 bundled synthetic CSV + ephemeral demo runtime；PostgreSQL 是 Optional Scale-out Backend。

## 已驗證底座

```text
Local SQLite runtime / ORM compatibility          VERIFIED
SQLite file persistence / FK / memory regression  VERIFIED
Vercel Python/static routing                      VERIFIED
Production page/API JSON smoke                    VERIFIED (previous gate)
Demo cold-start bootstrap                         VERIFIED
Demo core CSV bootstrap + UUIDv5 idempotency      VERIFIED
Demo deep-link / Recommendation hydration         VERIFIED
PTC Research synthetic hydration                  VERIFIED
PTC Integrated synthetic hydration                VERIFIED
PTC Command Center + navbar continuity            VERIFIED
Production multi-route synthetic browser gate     VERIFIED — workflow #130 PASS
SQLite integrity / backup / restore               VERIFIED
Restart persistence regression                    VERIFIED
Local CSV Import v1                               VERIFIED
Pre-upgrade SQLite backup hook                     VERIFIED — Local Gate #140 PASS
Traceability Persistence E2E                       VERIFIED — Local Gate #142 PASS
Local CSV Import v2                               VERIFIED — Local Gate #146 PASS
Workspace Import local UI                         VERIFIED — Local Gate #152 PASS
Vercel quota-hardening baseline                   VERIFIED — Local Gate #162 PASS
Release metadata consistency                      VERIFIED — Local Gate #167 PASS
```

## 1.0.3 release convergence

版本權威：

```text
VERSION = 1.0.3
Settings.APP_VERSION = 1.0.3
```

Frontend `package.json/package-lock.json` 為 private package metadata，不是產品 release authority。

已建立：`CHANGELOG.md`、`RELEASE_NOTES_v1.0.3.md`、`docs/RELEASE_CHECKLIST_v1.0.3.md`、Workspace Import route/nav regression，以及 release metadata consistency regression。

## 第十八批：Vercel quota hardening

Production workflow 已通過 token、project link、rootDirectory、production env preflight，真正失敗於：

```text
Error: Resource is limited - try again in 24 hours
code: api-deployments-free-per-day
```

此為 Vercel Free plan daily deployment quota，不是 application build/runtime failure。Workflow 已能明確分類 quota failure，不再以 null stdout `.Trim()` 產生次生 PowerShell 錯誤，也禁止用 no-op commit 反覆重試。

## 第十九批：release metadata consistency gate

新增 `tests/test_release_metadata.py` 並接入 Local Verification Gate，固定驗證 VERSION、backend APP_VERSION、release notes、release checklist、CHANGELOG 與 private frontend package 邊界。

倉庫 `1.0.2` 掃描未發現 release-critical runtime authority 殘留；舊測試說明亦已同步。

## 第二十批：local release-candidate closure

Local Verification Gate #167 已完成且 **PASS**。因此 1.0.3 candidate 的軟體本地側 release gates 已全部收斂為綠色：Local-first persistence/import/traceability、Workspace Import UI/routing、Vercel quota error hardening、release metadata consistency 均已通過。

## 第二十一批：quota-free production verification gate

Release freeze 期間新增 `.github/workflows/production-verify-only.yml`。此 workflow 只允許手動 `workflow_dispatch`，**不呼叫 `vercel deploy`，因此不消耗 Vercel deployment quota**。

它直接驗證 canonical production：

```text
Homepage HTTP smoke
6 個 production API JSON smoke
7 個 synthetic Chromium routes
Screenshot evidence
production-browser-report.json artifact
```

API 範圍：health、PTC readiness、PTC completion、PTC data quality overview、demo status、demo cases。

Browser 範圍：Recommendation、Clinical Decision、Treatment Plan、Knowledge Graph、PTC Research、PTC Integrated、PTC Command Center，全部帶同一 `demo_case=PTC-DEMO-001&data_mode=synthetic` contract。

重要邊界：Verification-Only Gate 只能證明**目前已部署 production**仍健康；它不證明 latest master 已經部署，因此不能取代最終的 release-candidate production deploy gate。這個設計讓 Vercel quota 被擋住期間仍能檢查線上服務，而不靠 no-op commit 或重複部署。

本批狀態：

**IMPLEMENTED — WAITING FOR LATEST LOCAL GATE / MANUAL PRODUCTION VERIFY**

## Local SQLite Acceptance Gate

- [x] config / schema bootstrap / FK / busy timeout；
- [x] file persistence；
- [x] integrity / backup / restore；
- [x] restart persistence；
- [x] workspace status API；
- [x] local CSV import v1/v2；
- [x] duplicate-aware preview / import history；
- [x] pre-upgrade backup hook；
- [x] traceability persistence E2E；
- [x] Workspace Import UI + route/nav regression；
- [x] quota-hardening baseline Local Gate #162 PASS；
- [x] metadata-consistency Local Gate #167 PASS。

## Vercel Demo Acceptance Gate

- [x] deterministic synthetic CSV bootstrap；
- [x] demo status/cases API；
- [x] synthetic deep-link / major-route hydration；
- [x] navbar query propagation；
- [x] dataset validators；
- [x] previous Production API JSON smoke PASS；
- [x] previous multi-route Chromium gate PASS；
- [x] quota-free Production Verification Only workflow implemented；
- [ ] latest manual Production Verification Only PASS；
- [ ] 1.0.3 candidate production deploy — BLOCKED BY VERCEL DAILY QUOTA；
- [ ] latest-head API JSON smoke / Chromium gate — waiting for successful deployment。

## 下一批

1. 驗證第二十一批 latest Local Verification Gate；
2. 手動執行 `Production Verification Only`，確認目前 canonical production 的 page/API/Chromium 仍全綠；
3. 保持 1.0.3 release freeze，不擴產品 scope；
4. Vercel quota 恢復後，以最新 verified master SHA 完成真正 production deploy；
5. latest-head production API/Chromium 全綠後建立 `v1.0.3` tag / GitHub Release。

## 安全邊界

所有 synthetic demo 輸出只用於研究軟體流程展示，不代表真實醫學證據、患者資料、診斷、臨床決策或治療建議。1.0.3 的版本成熟度只描述軟體工程成熟度，不等同臨床有效性驗證。
