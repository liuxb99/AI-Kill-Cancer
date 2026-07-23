"""
WorkbenchService — orchestrates workbench operations with real database queries (v1.1).
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.domain.audit_log import AuditLogModel
from src.backend.repositories.cancer_case_repo import CancerCaseRepository
from src.backend.repositories.drug_repo import DrugRepository
from src.backend.repositories.patient_repo import PatientRepository
from src.backend.repositories.variant_repo import VariantRepository
from src.backend.workbench.models import (
    ActivityEntry,
    ActivityLog,
    CaseComparisonResult,
    DrugInfo,
    GraphEdge,
    GraphNode,
    KnowledgeGraph,
    PatientDemographics,
    PatientSummary,
    TreatmentRecommendation,
    WorkbenchTimeline,
)
from src.backend.workbench.repository import TumorBoardRepository

logger = logging.getLogger(__name__)


class WorkbenchService:
    """Orchestrates workbench operations with database-backed queries."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.tumor_repo = TumorBoardRepository(db)
        self.patient_repo = PatientRepository(db)
        self.case_repo = CancerCaseRepository(db)
        self.variant_repo = VariantRepository(db)
        self.drug_repo = DrugRepository(db)

    async def build_knowledge_graph(self, variant_id: str = "",
                                     case_id: str = "") -> KnowledgeGraph:
        """Build a knowledge graph from real database data.
        Returns empty graph when no data is found — never generates fake data.
        """
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []
        seen_genes: set[str] = set()
        seen_drugs: set[str] = set()

        if variant_id:
            try:
                vid = uuid.UUID(variant_id) if isinstance(variant_id, str) else variant_id
            except ValueError:
                logger.warning("Invalid variant_id in build_knowledge_graph: %s", variant_id)
                return KnowledgeGraph()

            try:
                v = await self.variant_repo.get(vid)
                if v:
                    gene = getattr(v, "gene_symbol", "") or "Unknown"
                    if gene not in seen_genes:
                        seen_genes.add(gene)
                        nodes.append(GraphNode(
                            id=f"gene-{gene}",
                            label=gene,
                            node_type="gene",
                            color="#4CAF50",
                        ))
                    v_short = str(v.id)[:8]
                    nodes.append(GraphNode(
                        id=f"var-{v_short}",
                        label=f"{gene} {getattr(v, 'hgvs_notation', '') or getattr(v, 'protein_change', '') or v_short}",
                        node_type="variant",
                        color="#2196F3",
                    ))
                    edges.append(GraphEdge(
                        source_id=f"gene-{gene}",
                        target_id=f"var-{v_short}",
                        label="has_variant",
                        edge_type="genomic",
                    ))
            except Exception as e:
                logger.error("Database error building variant graph for %s: %s", variant_id, e)
                return KnowledgeGraph()

        if case_id:
            try:
                cid = uuid.UUID(case_id) if isinstance(case_id, str) else case_id
            except ValueError:
                logger.warning("Invalid case_id in build_knowledge_graph: %s", case_id)
                return KnowledgeGraph()

            try:
                case = await self.case_repo.get(cid)
                if not case:
                    return KnowledgeGraph()

                # Add case node
                cancer_type = case.cancer_type.value if hasattr(case.cancer_type, 'value') else str(case.cancer_type)
                nodes.append(GraphNode(
                    id=f"case-{case_id[:8]}",
                    label=f"Case: {cancer_type}",
                    node_type="disease",
                    color="#9C27B0",
                ))

                # Add variants and their genes
                variants = await self.variant_repo.find_by_case(cid)
                for v in variants:
                    v_id = str(v.id)
                    gene = getattr(v, "gene_symbol", "") or ""
                    if gene and gene not in seen_genes:
                        seen_genes.add(gene)
                        nodes.append(GraphNode(
                            id=f"gene-{gene}",
                            label=gene,
                            node_type="gene",
                            color="#4CAF50",
                        ))
                        edges.append(GraphEdge(
                            source_id=f"case-{case_id[:8]}",
                            target_id=f"gene-{gene}",
                            label="has_gene",
                            edge_type="genomic",
                        ))
                    nodes.append(GraphNode(
                        id=f"var-{v_id[:8]}",
                        label=f"{gene} {getattr(v, 'hgvs_notation', '') or getattr(v, 'protein_change', '') or v_id[:8]}",
                        node_type="variant",
                        color="#2196F3",
                    ))
                    edges.append(GraphEdge(
                        source_id=f"gene-{gene}" if gene else f"case-{case_id[:8]}",
                        target_id=f"var-{v_id[:8]}",
                        label="has_variant",
                        edge_type="genomic",
                    ))

                # Add drug nodes connected to specific genes via variant-drug relationships
                if seen_genes:
                    drugs = await self.drug_repo.list()
                    for d in drugs:
                        d_name = getattr(d, "name", "") or ""
                        if not d_name:
                            continue
                        # Only include drug if it targets a known gene
                        drug_gene = getattr(d, 'gene_symbol', '') or ''
                        if drug_gene and drug_gene in seen_genes:
                            if d_name not in seen_drugs:
                                seen_drugs.add(d_name)
                                nodes.append(GraphNode(
                                    id=f"drug-{d_name.lower().replace(' ', '-')}",
                                    label=d_name,
                                    node_type="drug",
                                    color="#FF9800",
                                ))
                        elif not drug_gene and d_name not in seen_drugs:
                            # Include drug without specific gene link as unconnected node
                            seen_drugs.add(d_name)
                            nodes.append(GraphNode(
                                id=f"drug-{d_name.lower().replace(' ', '-')}",
                                label=d_name,
                                node_type="drug",
                                color="#FF9800",
                            ))

            except Exception as e:
                logger.error("Database error building case graph for %s: %s", case_id, e)
                return KnowledgeGraph()

        return KnowledgeGraph(nodes=nodes, edges=edges)

    async def get_case_timeline(self, case_id: str) -> WorkbenchTimeline:
        """Get timeline of events for a case from audit logs."""
        events: list[dict] = []

        try:
            cid = uuid.UUID(case_id) if isinstance(case_id, str) else case_id
        except ValueError:
            logger.warning("Invalid case_id in get_case_timeline: %s", case_id)
            return WorkbenchTimeline()

        try:
            case = await self.case_repo.get(cid)
            if not case:
                return WorkbenchTimeline()

            if hasattr(case, 'created_at') and case.created_at:
                events.append({
                    "type": "case_created",
                    "timestamp": case.created_at.isoformat() if hasattr(case.created_at, 'isoformat') else str(case.created_at),
                    "description": f"Case created — {case.cancer_type.value if hasattr(case.cancer_type, 'value') else str(case.cancer_type)}",
                })
            if hasattr(case, 'updated_at') and case.updated_at and case.updated_at != case.created_at:
                events.append({
                    "type": "case_updated",
                    "timestamp": case.updated_at.isoformat() if hasattr(case.updated_at, 'isoformat') else str(case.updated_at),
                    "description": "Case information updated",
                })

            variants = await self.variant_repo.find_by_case(cid)
            for v in variants:
                gene = getattr(v, "gene_symbol", "") or "Unknown"
                hgvs = getattr(v, "hgvs_notation", "") or ""
                var_created = getattr(v, 'created_at', None)
                events.append({
                    "type": "variant_identified",
                    "timestamp": (var_created.isoformat()
                                  if var_created and hasattr(var_created, 'isoformat')
                                  else datetime.now(UTC).isoformat()),
                    "description": f"Variant identified: {gene} {hgvs}",
                })
        except Exception as e:
            logger.error("Database error building timeline for %s: %s", case_id, e)
            return WorkbenchTimeline()

        # Get audit log entries
        try:
            stmt = (select(AuditLogModel)
                    .where(AuditLogModel.resource_id == str(case_id))
                    .order_by(AuditLogModel.created_at.desc())
                    .limit(50))
            result = await self.db.execute(stmt)
            audit_entries = list(result.scalars().all())
            for a in audit_entries:
                events.append({
                    "type": getattr(a, 'action', 'audit_event'),
                    "timestamp": (getattr(a, 'created_at', datetime.now(UTC)).isoformat()
                                  if hasattr(a, 'created_at') and a.created_at
                                  else datetime.now(UTC).isoformat()),
                    "description": str(getattr(a, 'details', {})),
                    "user_id": str(getattr(a, 'actor', '')),
                })
        except Exception as e:
            logger.debug("Audit log query failed (table may not exist): %s", e)

        events.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
        return WorkbenchTimeline(events=events)

    async def get_patient_summary(self, case_id: str) -> PatientSummary:
        """Get consolidated patient summary for a case."""
        try:
            cid = uuid.UUID(case_id) if isinstance(case_id, str) else case_id
        except ValueError:
            logger.warning("Invalid case_id in get_patient_summary: %s", case_id)
            return PatientSummary()

        try:
            case = await self.case_repo.get(cid)
            if not case:
                return PatientSummary()

            cancer_type = (case.cancer_type.value if hasattr(case.cancer_type, 'value')
                           else str(getattr(case, 'cancer_type', '')))
            stage = getattr(case, 'stage', '') or ''
            histology = getattr(case, 'histology', '') or ''
            diagnosis = f"{cancer_type} ({stage})" if stage else cancer_type

            tx_history = getattr(case, 'treatment_history', None)
            medications = getattr(case, 'current_medications', None)

            summary = PatientSummary(
                cancer_type=cancer_type,
                stage=stage,
                histology=histology,
                diagnosis=diagnosis,
                treatment_history=tx_history if isinstance(tx_history, list) else [],
                current_medications=medications if isinstance(medications, list) else [],
                case_status=getattr(case, 'status', 'active') or 'active',
                case_priority=getattr(case, 'priority', 'normal') or 'normal',
            )

            patient_id = getattr(case, 'patient_id', None)
            if patient_id:
                try:
                    pid = uuid.UUID(str(patient_id)) if isinstance(patient_id, str) else patient_id
                    patient = await self.patient_repo.get(pid)
                    if patient:
                        summary.patient = PatientDemographics(
                            id=str(patient.id),
                            mrn=getattr(patient, 'mrn', '') or '',
                            age=getattr(patient, 'age', 0) or 0,
                            sex=getattr(patient, 'sex', '') or '',
                            race=getattr(patient, 'race', '') or '',
                            ethnicity=getattr(patient, 'ethnicity', '') or '',
                        )
                except Exception as e:
                    logger.warning("Failed to fetch patient for %s: %s", patient_id, e)

            try:
                variants = await self.variant_repo.find_by_case(cid)
                summary.biomarkers = [
                    f"{getattr(v, 'gene_symbol', '')} {getattr(v, 'hgvs_notation', '') or getattr(v, 'protein_change', '') or ''}"
                    for v in variants if getattr(v, 'gene_symbol', '')
                ]
            except Exception as e:
                logger.debug("Failed to fetch variants for summary: %s", e)

            return summary

        except Exception as e:
            logger.error("Failed to build patient summary for %s: %s", case_id, e)
            return PatientSummary()

    async def get_activity_log(self, case_id: str, limit: int = 50) -> ActivityLog:
        """Get activity log for a case."""
        entries: list[ActivityEntry] = []

        try:
            stmt = (select(AuditLogModel)
                    .where(AuditLogModel.resource_id == str(case_id))
                    .order_by(AuditLogModel.created_at.desc())
                    .limit(limit))
            result = await self.db.execute(stmt)
            audit_entries = list(result.scalars().all())
            for a in audit_entries:
                entries.append(ActivityEntry(
                    id=str(getattr(a, 'id', '')),
                    case_id=case_id,
                    user_id=str(getattr(a, 'actor', '')),
                    action=str(getattr(a, 'action', 'unknown')),
                    entity_type=getattr(a, 'resource_type', ''),
                    entity_id=getattr(a, 'resource_id', ''),
                    details=getattr(a, 'details', {}) if isinstance(getattr(a, 'details', {}), dict) else {},
                    created_at=(getattr(a, 'created_at', datetime.now(UTC)).isoformat()
                                if hasattr(a, 'created_at') and a.created_at
                                else datetime.now(UTC).isoformat()),
                ))
        except Exception as e:
            logger.debug("Failed to fetch activity log: %s", e)
            # Return empty log instead of fake placeholder entries
            return ActivityLog()

        return ActivityLog(entries=entries, total=len(entries))

    async def get_treatment_recommendation(self, case_id: str) -> TreatmentRecommendation:
        """Get treatment recommendation for a case by integrating ranking results."""
        try:
            cid = uuid.UUID(case_id) if isinstance(case_id, str) else case_id
        except ValueError:
            logger.warning("Invalid case_id in get_treatment_recommendation: %s", case_id)
            return TreatmentRecommendation(case_id=case_id, generated_at=datetime.now(UTC).isoformat())

        rec = TreatmentRecommendation(case_id=case_id, generated_at=datetime.now(UTC).isoformat())

        try:
            case = await self.case_repo.get(cid)
            if not case:
                return rec

            variants = await self.variant_repo.find_by_case(cid)
            if not variants:
                return rec

            for v in variants:
                gene = getattr(v, 'gene_symbol', '') or ''
                if not gene:
                    continue

                drugs = await self.drug_repo.find_by_gene(gene)
                for d in (drugs or []):
                    d_name = getattr(d, 'name', '') or ''
                    if not d_name:
                        continue
                    rec.recommendations.append(DrugInfo(
                        name=d_name,
                        drugbank_id=getattr(d, 'drugbank_id', '') or '',
                        mechanism=getattr(d, 'mechanism_of_action', '') or getattr(d, 'mechanism', '') or '',
                        status=getattr(d, 'status', 'experimental') or 'experimental',
                        level="B",
                        match_level="gene_level",
                        confidence=0.7,
                    ))

        except Exception as e:
            logger.error("Failed to get treatment recommendation: %s", e)

        return rec

    async def compare_cases(self, case_ids: list[str]) -> CaseComparisonResult:
        """Compare multiple cases using real data."""
        if not case_ids or len(case_ids) < 2:
            return CaseComparisonResult(comparison_type="case", case_ids=case_ids)

        all_variants: dict[str, list[dict]] = {}
        all_genes: set[str] = set()
        gene_case_map: dict[str, set[str]] = {}

        for cid_str in case_ids:
            try:
                cid = uuid.UUID(cid_str)
            except ValueError:
                logger.warning("Invalid case ID in compare_cases: %s", cid_str)
                continue

            try:
                variants = await self.variant_repo.find_by_case(cid)
                case_variants = []
                for v in variants:
                    gene = getattr(v, 'gene_symbol', '') or 'Unknown'
                    all_genes.add(gene)
                    if gene not in gene_case_map:
                        gene_case_map[gene] = set()
                    gene_case_map[gene].add(cid_str)
                    case_variants.append({
                        "gene": gene,
                        "hgvs": getattr(v, 'hgvs_notation', '') or '',
                        "protein": getattr(v, 'protein_change', '') or '',
                        "variant_id": str(v.id),
                    })
                all_variants[cid_str] = case_variants
            except Exception as e:
                logger.warning("Failed to load case %s for comparison: %s", cid_str, e)

        shared = []
        unique_variants: dict[str, list[dict]] = {c: [] for c in case_ids}

        for gene, cases_with_gene in gene_case_map.items():
            if len(cases_with_gene) == len(case_ids):
                shared.append({"gene": gene})
            else:
                for cid_str in case_ids:
                    if cid_str in cases_with_gene:
                        if cid_str not in unique_variants:
                            unique_variants[cid_str] = []
                        unique_variants[cid_str].append({"gene": gene})

        return CaseComparisonResult(
            comparison_type="case",
            case_ids=case_ids,
            shared_variants=shared,
            unique_variants=unique_variants,
            ranking_differences=[],
        )
