# v1.0.0 Implementation Audit — 功能矩阵

## Evidence Layer
| 功能 | 状态 | 备注 |
|------|------|------|
| Evidence ingestion | IMPLEMENTED | pipeline/civic_adapter.py + pipeline/dgidb_adapter.py |
| Evidence refresh | IMPLEMENTED | POST /evidence/refresh 真正查询来源 |
| Evidence persistence | IMPLEMENTED | EvidenceItemRepository 写入 DB |
| Evidence history | IMPLEMENTED | first_seen_at / last_seen_at |
| Evidence conflict preservation | IMPLEMENTED | conflict_status 字段 |
| CIViC | IMPLEMENTED | pipeline/civic_adapter.py (真实 REST) |
| DGIdb | IMPLEMENTED | pipeline/dgidb_adapter.py (真实 REST) |
| Variant exact matching | IMPLEMENTED | 5-level match chain in merger.py |

## Drug Ranking
| 功能 | 状态 | 备注 |
|------|------|------|
| Drug ranking by variant | IMPLEMENTED | POST /ranking/variant/{id} |
| Drug ranking by case | SCAFFOLD_ONLY | 返回 501 — 需修复 |
| Ranking persistence | IMPLEMENTED | RankingRunRepository |
| Ranking replay | IMPLEMENTED | 相同 snapshot 可重现 |
| Resistance scoring | IMPLEMENTED | ResistanceScorer |
| Conflict scoring | IMPLEMENTED | ConflictPenalty |

## Knowledge Sources
| 功能 | 状态 | 备注 |
|------|------|------|
| ClinVar | SCAFFOLD_ONLY | adapter placeholder — 需实现 |
| COSMIC | NOT_CONFIGURED | 需付费授权 |
| Cancer Hotspots | NOT_CONFIGURED | 需授权 |
| PharmGKB | NOT_CONFIGURED | 需 API key |
| PubMed | SCAFFOLD_ONLY | 有 PubMedFetcher 但未接入 Knowledge Layer |
| ClinicalTrials.gov | SCAFFOLD_ONLY | 未实现 |
| OncoKB | NOT_CONFIGURED | 需 API key |
| MyCancerGenome | NOT_CONFIGURED | 需授权 |
| Knowledge graph persistence | IMPLEMENTED | KnowledgeEntityModel + KnowledgeRelationModel |
| Identifier mapping | IMPLEMENTED | IdentifierMapper |

## Clinical Reasoning
| 功能 | 状态 | 备注 |
|------|------|------|
| Reasoning context | IMPLEMENTED | ReasoningContextBuilder |
| LLM provider | IMPLEMENTED | OpenAI-compatible, local, disabled |
| Citation validation | IMPLEMENTED | EvidenceCitationValidator |
| Hallucination guard | IMPLEMENTED | HallucinationGuard |
| Reasoning persistence | IMPLEMENTED | ReasoningRunRepository |
| Reasoning replay | IMPLEMENTED | 通过 GET /reasoning/run/{id} |

## Reports
| 功能 | 状态 | 备注 |
|------|------|------|
| HTML report | IMPLEMENTED | ReportRenderer + 模板 |
| PDF report | SCAFFOLD_ONLY | 依赖 weasyprint — 需实现 |
| JSON report | IMPLEMENTED | ReportRenderer |
| FHIR report | IMPLEMENTED | FHIRExporter |
| Report persistence | IMPLEMENTED | ClinicalReportModel |
| Report versioning | IMPLEMENTED | supersedes_report_id |
| Report authorization | SCAFFOLD_ONLY | 需添加权限检查 |

## Doctor Workbench
| 功能 | 状态 | 备注 |
|------|------|------|
| Workbench backend | IMPLEMENTED | 6 API endpoints |
| Workbench frontend | NOT_IMPLEMENTED | 需创建前端页面 |
| Knowledge graph frontend | NOT_IMPLEMENTED | 需前端可视化 |
| Tumor board | IMPLEMENTED | 后端完整流程 |
| Case comparison | IMPLEMENTED | 后端比较逻辑 |
| Manual override | IMPLEMENTED | decision_log |
| Audit history | IMPLEMENTED | WorkbenchTimeline API |

## Production Hardening
| 功能 | 状态 | 备注 |
|------|------|------|
| Authentication | PARTIAL | Bearer token 但固定 token |
| Authorization | IMPLEMENTED | RBAC + role_permissions |
| Case-level access control | NOT_IMPLEMENTED | 未实现 |
| Audit logging | IMPLEMENTED | AuditLogger |
| Security middleware | IMPLEMENTED | SecurityHeadersMiddleware |
| Privacy controls | IMPLEMENTED | 文档/策略 |
| Observability | IMPLEMENTED | HealthChecker |
| Backup | IMPLEMENTED | 文档 |
| Restore | IMPLEMENTED | 文档 |
| Docker | SCAFFOLD_ONLY | 需验证 |
| CI/CD | NOT_IMPLEMENTED | 需创建 |
| Production configuration | NOT_IMPLEMENTED | 需修复 .env.example |
