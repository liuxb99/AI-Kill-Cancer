"""Complete PTC MVP orchestration, graph snapshot and outcome analytics."""

from __future__ import annotations

import asyncio
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.backend.domain.ptc_integrated import PTCHerbCompoundModel, PTCHerbDrugInteractionModel, PTCHerbModel
from src.backend.domain.ptc_knowledge import PTCClinicalTrialModel, PTCEvidenceRecordModel, PTCTherapyModel
from src.backend.domain.ptc_research import PTCResearchCaseModel
from src.backend.importers.ptc_tcga.downloader import GDCClient
from src.backend.importers.ptc_tcga.service import PTCTCGAImportService
from src.backend.services.ptc_integrated_service import PTCIntegratedService
from src.backend.services.ptc_knowledge_service import PTCKnowledgeService
from src.backend.services.ptc_literature_service import PTCLiteratureService

DEFAULT_PTC_DRUGS = [
    "selpercatinib", "pralsetinib", "larotrectinib", "repotrectinib",
    "dabrafenib", "trametinib", "lenvatinib", "sorafenib", "cabozantinib",
]
DEFAULT_GENES = ["BRAF", "RET", "NTRK1", "NTRK2", "NTRK3", "NRAS", "HRAS", "KRAS", "TERT", "TP53"]


def _node(node_id: str, kind: str, label: str, **properties: Any) -> dict[str, Any]:
    return {"id": node_id, "type": kind, "label": label, "properties": properties}


def _edge(source: str, target: str, relation: str, **properties: Any) -> dict[str, Any]:
    return {
        "id": f"edge:{relation}:{source}:{target}",
        "source": source,
        "target": target,
        "relation": relation,
        "properties": properties,
    }


class PTCCompletionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def sync_all(
        self,
        *,
        gdc_size: int = 100,
        gdc_mutation_files: int = 1,
        trial_size: int = 100,
        pubmed_size: int = 100,
        drug_names: list[str] | None = None,
        include_civic: bool = False,
    ) -> dict[str, Any]:
        started_at = datetime.utcnow()
        stages: dict[str, dict[str, Any]] = {}

        async def run_stage(name: str, operation: Any) -> None:
            try:
                value = await operation()
                if hasattr(value, "__dataclass_fields__"):
                    value = asdict(value)
                stages[name] = {"status": "success", "result": value}
            except Exception as exc:  # public sources are isolated by design
                stages[name] = {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}

        async def import_gdc() -> dict[str, Any]:
            download = await asyncio.to_thread(
                GDCClient().fetch_ptc_cases_with_mutations,
                size=gdc_size,
                offset=0,
                mutation_files=gdc_mutation_files,
            )
            result = await PTCTCGAImportService(self.db).import_records(
                download.records,
                source_version=download.source_version,
            )
            return {
                **asdict(result),
                "downloaded_cases": len(download.records),
                "gdc_total_cases": download.total,
                "mutation_files": download.mutation_files,
                "mutation_variants": download.mutation_variants,
            }

        knowledge = PTCKnowledgeService(self.db)
        literature = PTCLiteratureService(self.db)
        integrated = PTCIntegratedService(self.db)
        await run_stage("gdc_tcga_thca", import_gdc)
        await run_stage("clinical_trials", lambda: knowledge.sync_clinical_trials(page_size=trial_size))
        await run_stage("openfda", lambda: knowledge.sync_openfda_labels(drug_names or DEFAULT_PTC_DRUGS))
        await run_stage("pubmed", lambda: literature.sync_pubmed(retmax=pubmed_size))
        if include_civic:
            await run_stage("civic", lambda: literature.sync_civic(gene_symbols=DEFAULT_GENES))
        else:
            stages["civic"] = {"status": "skipped", "reason": "include_civic=false"}
        await run_stage("scientific_chinese_medicine_seed", integrated.bootstrap_herbal_research)

        summary = await self.source_status()
        finished_at = datetime.utcnow()
        return {
            "status": "completed_with_errors" if any(v["status"] == "failed" for v in stages.values()) else "completed",
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "duration_seconds": round((finished_at - started_at).total_seconds(), 3),
            "stages": stages,
            "summary": summary,
        }

    async def source_status(self) -> dict[str, Any]:
        cases = await self._cases()
        therapies = list((await self.db.execute(select(PTCTherapyModel))).scalars())
        evidence = list((await self.db.execute(select(PTCEvidenceRecordModel))).scalars())
        trials = list((await self.db.execute(select(PTCClinicalTrialModel))).scalars())
        herbs = list((await self.db.execute(select(PTCHerbModel))).scalars())
        compounds = list((await self.db.execute(select(PTCHerbCompoundModel))).scalars())
        interactions = list((await self.db.execute(select(PTCHerbDrugInteractionModel))).scalars())
        sources = Counter(item.source_name for item in [*therapies, *evidence] if item.source_name)
        return {
            "cases": len(cases),
            "variants": sum(len(case.variants) for case in cases),
            "outcomes": sum(len(case.outcomes) for case in cases),
            "therapies": len(therapies),
            "evidence": len(evidence),
            "clinical_trials": len(trials),
            "herbs": len(herbs),
            "compounds": len(compounds),
            "interactions": len(interactions),
            "knowledge_sources": dict(sorted(sources.items())),
        }

    async def outcome_by_gene(self) -> list[dict[str, Any]]:
        cases = await self._cases()
        stats: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"case_ids": set(), "vital_status": Counter(), "outcomes": Counter()}
        )
        for case in cases:
            genes = {variant.gene.upper() for variant in case.variants if variant.gene}
            for gene in genes:
                stats[gene]["case_ids"].add(case.case_id)
                stats[gene]["vital_status"][case.vital_status or "unknown"] += 1
                for outcome in case.outcomes:
                    key = f"{outcome.outcome_type}:{outcome.outcome_value or 'unknown'}"
                    stats[gene]["outcomes"][key] += 1
        return [
            {
                "gene": gene,
                "case_count": len(value["case_ids"]),
                "vital_status": dict(value["vital_status"]),
                "outcomes": dict(value["outcomes"]),
            }
            for gene, value in sorted(stats.items(), key=lambda item: (-len(item[1]["case_ids"]), item[0]))
        ]

    async def full_graph(self, *, case_limit: int = 500) -> dict[str, Any]:
        cases = (await self._cases())[:case_limit]
        therapies = list(
            (
                await self.db.execute(
                    select(PTCTherapyModel)
                    .options(selectinload(PTCTherapyModel.targets))
                    .order_by(PTCTherapyModel.name)
                )
            ).scalars().unique()
        )
        evidence = list((await self.db.execute(select(PTCEvidenceRecordModel))).scalars())
        trials = list((await self.db.execute(select(PTCClinicalTrialModel))).scalars())
        herbs = list((await self.db.execute(select(PTCHerbModel))).scalars())
        compounds = list((await self.db.execute(select(PTCHerbCompoundModel))).scalars())
        interactions = list((await self.db.execute(select(PTCHerbDrugInteractionModel))).scalars())
        therapy_keys_by_id = {str(item.id): item.therapy_key for item in therapies}

        nodes: dict[str, dict[str, Any]] = {}
        edges: dict[str, dict[str, Any]] = {}

        def add_node(item: dict[str, Any]) -> None:
            nodes[item["id"]] = item

        def add_edge(item: dict[str, Any]) -> None:
            edges[item["id"]] = item

        disease_id = "disease:papillary_thyroid_carcinoma"
        add_node(_node(disease_id, "Disease", "Papillary Thyroid Carcinoma"))

        for case in cases:
            case_id = f"ptc:case:{case.source_dataset}:{case.case_id}"
            add_node(_node(case_id, "ResearchCase", case.case_id, stage=case.pathologic_stage, vital_status=case.vital_status))
            add_edge(_edge(case_id, disease_id, "HAS_DISEASE"))
            for variant in case.variants:
                variant_id = f"ptc:variant:{case.source_dataset}:{variant.variant_id}"
                gene_id = f"gene:{variant.gene.upper()}"
                add_node(_node(variant_id, "Variant", variant.protein_change or variant.variant_id, classification=variant.classification))
                add_node(_node(gene_id, "Gene", variant.gene.upper()))
                add_edge(_edge(case_id, variant_id, "HAS_VARIANT"))
                add_edge(_edge(variant_id, gene_id, "AFFECTS_GENE"))
            for outcome in case.outcomes:
                outcome_id = f"ptc:outcome:{case.source_dataset}:{outcome.outcome_id}"
                add_node(_node(outcome_id, "ClinicalOutcome", outcome.outcome_value or outcome.outcome_type, outcome_type=outcome.outcome_type))
                add_edge(_edge(case_id, outcome_id, "HAS_OUTCOME"))

        for therapy in therapies:
            therapy_id = f"therapy:{therapy.therapy_key}"
            add_node(_node(therapy_id, "Therapy", therapy.name, approval_status=therapy.approval_status, source=therapy.source_name))
            add_edge(_edge(therapy_id, disease_id, "STUDIED_FOR"))
            for target in therapy.targets:
                gene_id = f"gene:{target.gene_symbol.upper()}"
                add_node(_node(gene_id, "Gene", target.gene_symbol.upper()))
                add_edge(_edge(therapy_id, gene_id, "TARGETS", variant=target.variant, evidence_level=target.evidence_level))

        for item in evidence:
            evidence_id = f"evidence:{item.evidence_key}"
            add_node(_node(evidence_id, "Evidence", item.title or item.source_record_id, source=item.source_name, level=item.evidence_level))
            if item.gene_symbol:
                gene_id = f"gene:{item.gene_symbol.upper()}"
                add_node(_node(gene_id, "Gene", item.gene_symbol.upper()))
                add_edge(_edge(evidence_id, gene_id, "SUPPORTS_GENE_ASSERTION", direction=item.direction))
            therapy_key = therapy_keys_by_id.get(str(item.therapy_id)) if item.therapy_id else None
            if therapy_key:
                add_edge(_edge(f"therapy:{therapy_key}", evidence_id, "SUPPORTED_BY"))

        for trial in trials:
            trial_id = f"trial:{trial.nct_id}"
            add_node(_node(trial_id, "ClinicalTrial", trial.brief_title, status=trial.overall_status, phases=trial.phases or []))
            add_edge(_edge(trial_id, disease_id, "STUDIES_DISEASE"))
            for gene in trial.target_genes or []:
                gene_id = f"gene:{gene.upper()}"
                add_node(_node(gene_id, "Gene", gene.upper()))
                add_edge(_edge(trial_id, gene_id, "STUDIES_GENE"))

        for herb in herbs:
            herb_id = f"herb:{herb.herb_key}"
            add_node(_node(herb_id, "ChineseHerb", herb.chinese_name, latin_name=herb.latin_name, evidence_level=herb.evidence_level))
            add_edge(_edge(herb_id, disease_id, "STUDIED_FOR"))
            for gene in herb.investigated_genes or []:
                gene_id = f"gene:{gene.upper()}"
                add_node(_node(gene_id, "Gene", gene.upper()))
                add_edge(_edge(herb_id, gene_id, "INVESTIGATED_TARGET"))

        for compound in compounds:
            compound_id = f"compound:{compound.compound_key}"
            herb_id = f"herb:{compound.herb_key}"
            add_node(_node(compound_id, "HerbCompound", compound.compound_name, pubchem_cid=compound.pubchem_cid))
            add_edge(_edge(herb_id, compound_id, "CONTAINS_COMPOUND"))
            for gene in compound.target_genes or []:
                gene_id = f"gene:{gene.upper()}"
                add_node(_node(gene_id, "Gene", gene.upper()))
                add_edge(_edge(compound_id, gene_id, "INVESTIGATED_TARGET"))

        for interaction in interactions:
            add_edge(
                _edge(
                    f"herb:{interaction.herb_key}",
                    f"therapy:{interaction.therapy_key}",
                    "INTERACTS_WITH",
                    interaction_type=interaction.interaction_type,
                    severity=interaction.severity,
                    evidence_level=interaction.evidence_level,
                )
            )

        return {
            "generated_at": datetime.utcnow().isoformat(),
            "node_count": len(nodes),
            "edge_count": len(edges),
            "nodes": list(nodes.values()),
            "edges": list(edges.values()),
        }

    async def _cases(self) -> list[PTCResearchCaseModel]:
        result = await self.db.execute(
            select(PTCResearchCaseModel)
            .options(selectinload(PTCResearchCaseModel.variants), selectinload(PTCResearchCaseModel.outcomes))
            .order_by(PTCResearchCaseModel.case_id)
        )
        return list(result.scalars().unique())


__all__ = ["PTCCompletionService", "DEFAULT_PTC_DRUGS", "DEFAULT_GENES"]
