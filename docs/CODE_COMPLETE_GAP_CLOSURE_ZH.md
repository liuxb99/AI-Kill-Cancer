# AI-Kill-Cancer 代码完成缺口清单与收敛计划

更新日期：2026-08-10
目标版本：1.0.3 candidate
完成标准：**以代码写完并通过真实本机 Gate 为标准，不以“已实现”“已提交”“文档已写”作为完成。**

## 1. 当前结论

截至本文件建立时，AI-Kill-Cancer 已完成主要产品骨架、Local-First SQLite、Demo Showcase、Workspace Import、traceability、主要 PTC 页面与 production smoke 基线。当前缺口已经从“功能大面积缺失”收敛为“代码完整性与最终验证闭环”。

按“代码写完”口径估算：

- 核心功能代码完成度：约 **95%**；
- release-critical 代码完整性：约 **90%～95%**；
- 完整验证闭环：尚未完成，因为最新扩大的 Local Verification Gate 仍在失败；
- production release：尚未完成，最终 latest-head deploy 仍受 Vercel daily deployment quota 影响。

上述百分比只用于描述工程收敛程度，不代表临床成熟度。

## 2. 已完成且不再重复开发的主线

### Local-First Workspace
- [x] SQLite schema bootstrap / FK / busy timeout；
- [x] file persistence；
- [x] integrity check；
- [x] backup / atomic restore；
- [x] restart persistence；
- [x] pre-upgrade backup；
- [x] controlled CSV import v1/v2；
- [x] duplicate-aware preview；
- [x] import history；
- [x] Workspace Import UI；
- [x] traceability persistence E2E。

### Demo / Vercel Showcase
- [x] bundled synthetic CSV；
- [x] deterministic UUIDv5 bootstrap；
- [x] demo status / cases API；
- [x] dataset schema / enum / reference validation；
- [x] Recommendation / Clinical Decision / Treatment Plan / Knowledge Graph hydration；
- [x] PTC Research / Integrated / Command Center continuity；
- [x] previous production API JSON smoke；
- [x] previous multi-route Chromium gate；
- [x] quota-free Production Verification Only workflow。

### Release Governance
- [x] root `VERSION = 1.0.3`；
- [x] backend `APP_VERSION = 1.0.3`；
- [x] `pyproject.toml project.version = 1.0.3`；
- [x] CHANGELOG / release notes / release checklist；
- [x] release metadata regression；
- [x] Vercel quota error classification。

## 3. 当前真实缺口

### G0 — 最新 Local Gate 被 Ruff 阻断（立即修复）
当前 Local Verification Gate #201 在 lint 阶段失败，已确认不是业务测试失败，而是三个格式问题：

1. `src/backend/demo/bootstrap.py` 缺文件末尾 newline；
2. `tests/test_code_completeness.py` import block 未通过 Ruff I001；
3. `tests/test_release_metadata.py` import block 未通过 Ruff I001。

完成条件：最新 head 的 Ruff step PASS，并继续进入 pytest，而不是停在 lint。

### G1 — 扩大的 backend regression 尚未跑到底
最新 Gate 已纳入：

- code completeness；
- demo maintenance reset/rebuild；
- adapter registry；
- OpenCRAVAT；
- MyVariant；
- VEP；
- OncoTree；
- DRKG；
- PharmCAT；
- SQLite local/workspace/traceability；
- release metadata。

但由于 G0，pytest 尚未真正执行到结束。

完成条件：上述 release-critical backend suite 全绿；每次失败必须修根因后重跑，直到零失败。

### G2 — Frontend tests / production build 尚未在扩展 Gate 中跑到底
Local Gate 已加入 `npm test` 与 `npm run build`，但同样被 G0 提前阻断。

完成条件：frontend tests PASS + TypeScript/Vite production build PASS。

### G3 — 运行时代码完整性扫描必须清零
新增 `tests/test_code_completeness.py` 后，必须证明：

- API 不存在 501 / `not_implemented` runtime scaffold；
- stable adapter modules 不再暴露 generic `NotConfiguredAdapter` placeholder；
- VEP/OpenCRAVAT 不存在 terminal `Not implemented` result；
- release-critical adapter module 不保留 Phase placeholder banner。

完成条件：code-completeness regression PASS；若测试找出遗漏，必须实现真实代码或把该能力明确降级为 optional boundary，不能用跳过测试掩盖。

### G4 — 外部数据 adapter 最终一致性
已开始补齐真实 adapter / optional adapter，但必须由 Gate 证明 registry 与实现一致：

- Ensembl VEP；
- CIViC；
- DGIdb；
- MyVariant；
- OpenCRAVAT；
- OncoTree；
- DRKG；
- PharmCAT；
- bcftools。

原则：公共无需密钥的数据源应有可运行实现；依赖本地程序、授权数据或密钥的能力可以保持 explicit unavailable / optional，但不能伪装 success 或返回 synthetic 当真实数据。

完成条件：adapter tests + registry health aggregation 全绿。

### G5 — Demo reset/rebuild 工具必须完成闭环
`reset_demo_dataset` / `rebuild_demo_dataset` 与 CLI 已加入，但最新 Gate 尚未执行到它们。

完成条件：真实临时 SQLite 上 reset 只删除 deterministic demo records；rebuild 恢复 3 个固定 demo cases；CLI validate/rebuild 均通过。

### G6 — Python 运行时与 package metadata 一致性
旧 `pyproject.toml` 曾残留 `0.1.0` 与窄 Python range；现已对齐 1.0.3 / Python 3.10～3.14 family。

完成条件：release metadata regression PASS，且 Python 3.10 runner 与较新 runner 均不因 metadata 自相矛盾失败。

### G7 — Production release closure（代码写完之后的发布门）
这不是产品代码缺失，但仍是 1.0.3 正式 release 的必要条件：

1. latest Local Verification Gate PASS；
2. quota-free Production Verification Only PASS；
3. Vercel quota 恢复后将 latest verified master SHA 真正 deploy；
4. latest-head production API JSON smoke PASS；
5. latest-head Chromium multi-route PASS；
6. 才能建立 `v1.0.3` tag / GitHub Release。

Vercel quota 属于外部 blocker，不能用 no-op commit 反复重试。

## 4. 自动接续开发顺序

严格按以下顺序自动推进，不等待人工选择下一步：

```text
G0 Ruff / compile
→ G1 backend regression
→ 根据 pytest failure 修代码
→ G2 frontend tests/build
→ 根据 frontend failure 修代码
→ G3 code-completeness scan 清零
→ G4 adapter 一致性
→ G5 demo maintenance
→ G6 metadata/runtime consistency
→ latest Local Verification Gate 全绿
→ 更新 CURRENT_STATUS / RELEASE_CHECKLIST / 本文档
→ G7 production closure
```

如果某一 Gate 暴露新问题，新问题自动插入对应层级，不另开新功能 scope。

## 5. “代码完成”判定

只有同时满足以下条件，才能将项目标记为 **CODE COMPLETE**：

- [ ] release-critical Ruff/compile 全绿；
- [ ] release-critical backend pytest 全绿；
- [ ] code completeness regression 全绿；
- [ ] adapter regression 全绿；
- [ ] demo reset/rebuild regression 全绿；
- [ ] SQLite/workspace/traceability regression 全绿；
- [ ] frontend tests 全绿；
- [ ] frontend production build 全绿；
- [ ] `git diff --check` 全绿；
- [ ] 最新 Local Verification Gate PASS；
- [ ] 没有已知 release-critical TODO/501/not_implemented placeholder；
- [ ] 文档状态与实际代码一致。

Production deploy 与 tag 属于 **RELEASE COMPLETE**，在 CODE COMPLETE 之后执行；若唯一剩余项只是 Vercel 外部 quota，则可以标记“CODE COMPLETE — RELEASE BLOCKED BY EXTERNAL QUOTA”，但不能提前标记“RELEASE COMPLETE”。

## 6. 当前执行点

当前执行点：**G0**。

最新已知失败：Local Verification Gate #201，lint 阶段 3 个 Ruff fixable errors。修复后立即自动接续 G1，不等待人工指令。

## 7. 医疗安全边界

本项目仍为甲状腺癌 Precision Oncology 研究软件。代码完成、测试全绿、production release 都只代表软件工程状态，不代表临床有效性、监管批准、诊断能力或治疗建议能力。所有 synthetic demo 输出必须持续保留 research-only / non-clinical-use provenance。
