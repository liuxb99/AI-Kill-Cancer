# Current Status

更新日期：2026-08-08

AI-Kill-Cancer 已經遠超早期 Phase 3A/3B 階段。近期實作已進入 Phase 3F～3H，包含 Recommendation/Clinical contract 解耦、Treatment ID、Outbox event_id、Clinical Safety Gate、真實公共資料下載與 Vercel API routing 修復。

## 已實作／已有永久測試證據

```text
Drug Recommendation / Clinical Decision contracts     IMPLEMENTED
Treatment Plan dual-mode UI/API                       IMPLEMENTED
Clinical Graph deterministic treatment IDs            IMPLEMENTED
Outbox event_id persistence contract                  IMPLEMENTED
Recommendation service/API decoupling                 IMPLEMENTED
Treatment-plan clinical safety readiness gate         IMPLEMENTED
GDC/TCGA public data adapter                          IMPLEMENTED
ClinicalTrials.gov adapter                            IMPLEMENTED
OpenFDA adapter                                       IMPLEMENTED
PubMed/PMC adapter                                    IMPLEMENTED
CIViC adapter                                         IMPLEMENTED
Content-addressed public-data storage / dedup          IMPLEMENTED
Vercel Python API routing                             IMPLEMENTED
Frontend HTML-vs-JSON routing guard                   IMPLEMENTED
```

## 当前阶段

```text
Phase 3F-1 treatment ID contract      COMPLETE
Phase 3F-2 outbox event contract      COMPLETE
Phase 3F-3 recommendation decoupling  COMPLETE
Phase 3G clinical safety gate         COMPLETE
Phase 3H public data downloads        IMPLEMENTED
Full production verification          IN_PROGRESS
```

GitHub Actions 已于 2026-08-07 改为手动触发路线。后续应在 Windows self-hosted CI 上恢复全量验证，不能因为之前 GitHub-hosted Actions 分钟/帐务限制而把未执行的检查视为通过。

## 真正剩余缺口

1. Windows self-hosted runner 上全量 backend/frontend/database 测试。
2. PostgreSQL persistence/restart/migration 实机验证。
3. Public-data adapter 的真实网络与错误恢复长期稳定性。
4. Clinical Safety Gate 的跨页面/跨流程 E2E。
5. Knowledge Graph、推荐、Treatment Plan、公共数据间的完整 traceability E2E。
6. Production deployment smoke test。
7. 只有上述全部通过后，才可标记 FULLY VERIFIED。

## 安全边界

本项目属于研究与临床决策辅助软件工程项目。任何推荐、治疗计划或风险判断均不得替代合格医疗专业人员的诊断与治疗决策。软件完成度与医学有效性必须分开评价。
