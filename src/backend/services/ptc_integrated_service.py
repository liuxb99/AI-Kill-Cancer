"""Integrated PTC research workbench service.

This module produces research-support outputs only. It does not diagnose,
prescribe, or replace clinician review.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.backend.domain.ptc_integrated import (
    PTCCaseSimilarityModel,
    PTCHerbCompoundModel,
    PTCHerbDrugInteractionModel,
    PTCHerbModel,
    PTCRecommendationSnapshotModel,
)
from src.backend.domain.ptc_knowledge import (
    PTCClinicalTrialModel,
    PTCEvidenceRecordModel,
    PTCTherapyModel,
    PTCTherapyTargetModel,
)
from src.backend.domain.ptc_research import PTCResearchCaseModel


STARTER_HERBS: list[dict[str, Any]] = [
    {
        "herb_key": "tcm:herb:astragalus-membranaceus:root",
        "chinese_name": "黃耆",
        "english_name": "Astragalus",
        "latin_name": "Astragalus membranaceus",
        "medicinal_part": "root",
        "traditional_functions": ["tonify_qi"],
        "investigated_genes": ["BRAF", "AKT1", "PIK3CA"],
        "investigated_pathways": ["MAPK", "PI3K_AKT"],
        "evidence_level": "preclinical",
        "evidence_summary": "PTC relevance remains investigational; retain as pathway-level research evidence only.",
        "source_name": "curated_research_seed",
        "source_record_id": "PTC-HERB-001",
        "license": "internal-curation",
    },
    {
        "herb_key": "tcm:herb:scutellaria-baicalensis:root",
        "chinese_name": "黃芩",
        "english_name": "Chinese skullcap",
        "latin_name": "Scutellaria baicalensis",
        "medicinal_part": "root",
        "traditional_functions": ["clear_heat"],
        "investigated_genes": ["BRAF", "EGFR", "AKT1"],
        "investigated_pathways": ["MAPK", "APOPTOSIS"],
        "evidence_level": "preclinical",
        "evidence_summary": "Compounds are studied in cancer models; no claim of clinical PTC efficacy.",
        "source_name": "curated_research_seed",
        "source_record_id": "PTC-HERB-002",
        "license": "internal-curation",
    },
    {
        "herb_key": "tcm:herb:curcuma-longa:rhizome",
        "chinese_name": "薑黃",
        "english_name": "Turmeric",
        "latin_name": "Curcuma longa",
        "medicinal_part": "rhizome",
        "traditional_functions": ["move_blood"],
        "investigated_genes": ["BRAF", "AKT1", "TP53"],
        "investigated_pathways": ["NF_KB", "PI3K_AKT", "APOPTOSIS"],
        "evidence_level": "preclinical",
        "evidence_summary": "Curcumin has broad preclinical literature; clinical relevance and exposure are uncertain.",
        "source_name": "curated_research_seed",
        "source_record_id": "PTC-HERB-003",
        "license": "internal-curation",
    },
]

STARTER_COMPOUNDS: list[dict[str, Any]] = [
    {
        "compound_key": "compound:astragaloside-iv",
        "herb_key": "tcm:herb:astragalus-membranaceus:root",
        "compound_name": "Astragaloside IV",
        "target_genes": ["AKT1", "PIK3CA"],
        "pathways": ["PI3K_AKT"],
        "source_name": "curated_research_seed",
        "source_record_id": "PTC-CMP-001",
    },
    {
        "compound_key": "compound:baicalein",
        "herb_key": "tcm:herb:scutellaria-baicalensis:root",
        "compound_name": "Baicalein",
        "target_genes": ["BRAF", "EGFR", "AKT1"],
        "pathways": ["MAPK", "APOPTOSIS"],
        "source_name": "curated_research_seed",
        "source_record_id": "PTC-CMP-002",
    },
    {
        "compound_key": "compound:curcumin",
        "herb_key": "tcm:herb:curcuma-longa:rhizome",
        "compound_name": "Curcumin",
        "target_genes": ["AKT1", "TP53"],
        "pathways": ["NF_KB", "PI3K_AKT"],
        "source_name": "curated_research_seed",
        "source_record_id": "PTC-CMP-003",
    },
]


@dataclass(slots=True)
class IntegratedDashboard:
    case_count: int
    variant_count: int
    therapy_count: int
    evidence_count: int
    trial_count: int
    herb_count: int
    interaction_count: int
    top_genes: list[dict[str, Any]]


class PTCIntegratedService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def bootstrap_herbal_research(self) -> dict[str, int]:
        herbs = 0
        compounds = 0
        try:
            for payload in STARTER_HERBS:
                result = await self.db.execute(select(PTCHerbModel).where(PTCHerbModel.herb_key == payload["herb_key"]))
                row = result.scalar_one_or_none()
                if row is None:
                    self.db.add(PTCHerbModel(**payload))
                    herbs += 1
                else:
                    for key, value in payload.items():
                        setattr(row, key, value)
            for payload in STARTER_COMPOUNDS:
                result = await self.db.execute(
                    select(PTCHerbCompoundModel).where(PTCHerbCompoundModel.compound_key == payload["compound_key"])
                )
                row = result.scalar_one_or_none()
                if row is None:
                    self.db.add(PTCHerbCompoundModel(**payload))
                    compounds += 1
                else:
                    for key, value in payload.items():
                        setattr(row, key, value)
            await self.db.commit()
            return {"herbs_created": herbs, "compounds_created": compounds}
        except Exception:
            await self.db.rollback()
            raise

    async def add_interaction(self, payload: dict[str, Any]) -> PTCHerbDrugInteractionModel:
        stmt = select(PTCHerbDrugInteractionModel).where(
            PTCHerbDrugInteractionModel.herb_key == payload["herb_key"],
            PTCHerbDrugInteractionModel.therapy_key == payload["therapy_key"],
            PTCHerbDrugInteractionModel.interaction_type == payload["interaction_type"],
        )
        try:
            result = await self.db.execute(stmt)
            row = result.scalar_one_or_none()
            if row is None:
                row = PTCHerbDrugInteractionModel(**payload)
                self.db.add(row)
            else:
                for key, value in payload.items():
                    setattr(row, key, value)
            await self.db.commit()
            await self.db.refresh(row)
            return row
        except Exception:
            await self.db.rollback()
            raise

    async def calculate_similarities(self, case_id: str, limit: int = 10) -> list[dict[str, Any]]:
        cases = await self._load_cases()
        target = next((item for item in cases if item.case_id == case_id), None)
        if target is None:
            raise ValueError("PTC research case not found")
        target_genes = {variant.gene.upper() for variant in target.variants}
        rows: list[dict[str, Any]] = []
        for other in cases:
            if other.case_id == case_id:
                continue
            other_genes = {variant.gene.upper() for variant in other.variants}
            union = target_genes | other_genes
            gene_score = len(target_genes & other_genes) / len(union) if union else 0.0
            stage_bonus = 0.15 if target.pathologic_stage and target.pathologic_stage == other.pathologic_stage else 0.0
            score = min(1.0, gene_score * 0.85 + stage_bonus)
            if score <= 0:
                continue
            rows.append(
                {
                    "case_id": case_id,
                    "similar_case_id": other.case_id,
                    "score": round(score, 4),
                    "shared_genes": sorted(target_genes & other_genes),
                    "shared_stage": target.pathologic_stage if stage_bonus else None,
                    "rationale": "Similarity uses gene-set Jaccard overlap plus a small stage match bonus.",
                }
            )
        rows.sort(key=lambda item: (-item["score"], item["similar_case_id"]))
        rows = rows[:limit]
        try:
            await self.db.execute(delete(PTCCaseSimilarityModel).where(PTCCaseSimilarityModel.case_id == case_id))
            self.db.add_all([PTCCaseSimilarityModel(**row) for row in rows])
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise
        return rows

    async def generate_research_recommendation(self, case_id: str) -> dict[str, Any]:
        cases = await self._load_cases()
        case = next((item for item in cases if item.case_id == case_id), None)
        if case is None:
            raise ValueError("PTC research case not found")
        genes = sorted({variant.gene.upper() for variant in case.variants})
        therapies = await self._rank_therapies(genes)
        trials = await self._matching_trials(genes)
        evidence = await self._matching_evidence(genes)
        herbs = await self._matching_herbs(genes)
        interactions = await self._matching_interactions({item["therapy_key"] for item in therapies})
        similar = await self.calculate_similarities(case_id)
        signal_count = len(therapies) + len(trials) + len(evidence)
        confidence = min(0.95, 0.2 + min(signal_count, 15) * 0.05)
        recommendation_id = "ptc-rec-" + hashlib.sha256(
            f"{case_id}|{'|'.join(genes)}|ptc-research-v1".encode()
        ).hexdigest()[:20]
        explanation = (
            "Research-support ranking based on observed genes, imported therapy targets, public evidence, "
            "clinical trials and similar research cases. It is not a prescription and requires clinician review."
        )
        payload = {
            "recommendation_id": recommendation_id,
            "case_id": case_id,
            "genes": genes,
            "ranked_therapies": therapies,
            "matching_trials": trials,
            "supporting_evidence": evidence,
            "herb_research": herbs,
            "interaction_warnings": interactions,
            "similar_cases": similar,
            "explanation": explanation,
            "confidence": round(confidence, 3),
            "engine_version": "ptc-research-v1",
            "generated_at": datetime.utcnow().isoformat(),
        }
        try:
            result = await self.db.execute(
                select(PTCRecommendationSnapshotModel).where(
                    PTCRecommendationSnapshotModel.recommendation_id == recommendation_id
                )
            )
            row = result.scalar_one_or_none()
            values = {
                "recommendation_id": recommendation_id,
                "case_id": case_id,
                "ranked_therapies": therapies,
                "matching_trials": trials,
                "supporting_evidence": evidence,
                "herb_research": herbs,
                "interaction_warnings": interactions,
                "similar_cases": similar,
                "explanation": explanation,
                "confidence": confidence,
            }
            if row is None:
                self.db.add(PTCRecommendationSnapshotModel(**values))
            else:
                for key, value in values.items():
                    setattr(row, key, value)
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise
        return payload

    async def dashboard(self) -> IntegratedDashboard:
        cases = await self._load_cases()
        therapies = list((await self.db.execute(select(PTCTherapyModel))).scalars())
        evidence = list((await self.db.execute(select(PTCEvidenceRecordModel))).scalars())
        trials = list((await self.db.execute(select(PTCClinicalTrialModel))).scalars())
        herbs = list((await self.db.execute(select(PTCHerbModel))).scalars())
        interactions = list((await self.db.execute(select(PTCHerbDrugInteractionModel))).scalars())
        counts: dict[str, int] = {}
        variant_count = 0
        for case in cases:
            for variant in case.variants:
                variant_count += 1
                gene = variant.gene.upper()
                counts[gene] = counts.get(gene, 0) + 1
        top_genes = [
            {"gene": gene, "case_count": count}
            for gene, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:15]
        ]
        return IntegratedDashboard(
            case_count=len(cases),
            variant_count=variant_count,
            therapy_count=len(therapies),
            evidence_count=len(evidence),
            trial_count=len(trials),
            herb_count=len(herbs),
            interaction_count=len(interactions),
            top_genes=top_genes,
        )

    async def _load_cases(self) -> list[PTCResearchCaseModel]:
        result = await self.db.execute(
            select(PTCResearchCaseModel)
            .options(selectinload(PTCResearchCaseModel.variants), selectinload(PTCResearchCaseModel.outcomes))
            .order_by(PTCResearchCaseModel.case_id)
        )
        return list(result.scalars().unique())

    async def _rank_therapies(self, genes: list[str]) -> list[dict[str, Any]]:
        result = await self.db.execute(
            select(PTCTherapyModel).options(selectinload(PTCTherapyModel.targets)).order_by(PTCTherapyModel.name)
        )
        rows = []
        gene_set = set(genes)
        for therapy in result.scalars().unique():
            target_genes = {target.gene_symbol.upper() for target in therapy.targets}
            shared = sorted(gene_set & target_genes)
            if not shared:
                continue
            score = min(1.0, 0.45 + 0.2 * len(shared) + (0.15 if therapy.approval_status else 0.0))
            rows.append(
                {
                    "therapy_key": therapy.therapy_key,
                    "name": therapy.name,
                    "generic_name": therapy.generic_name,
                    "matched_genes": shared,
                    "approval_status": therapy.approval_status,
                    "score": round(score, 3),
                    "source_name": therapy.source_name,
                }
            )
        return sorted(rows, key=lambda item: (-item["score"], item["name"]))

    async def _matching_trials(self, genes: list[str]) -> list[dict[str, Any]]:
        rows = list((await self.db.execute(select(PTCClinicalTrialModel))).scalars())
        gene_set = set(genes)
        result = []
        for trial in rows:
            matched = sorted(gene_set & {gene.upper() for gene in (trial.target_genes or [])})
            if matched or not trial.target_genes:
                result.append(
                    {
                        "nct_id": trial.nct_id,
                        "brief_title": trial.brief_title,
                        "overall_status": trial.overall_status,
                        "phases": trial.phases or [],
                        "matched_genes": matched,
                    }
                )
        return result[:25]

    async def _matching_evidence(self, genes: list[str]) -> list[dict[str, Any]]:
        rows = list((await self.db.execute(select(PTCEvidenceRecordModel))).scalars())
        gene_set = set(genes)
        result = []
        for row in rows:
            matched = sorted(gene_set & {gene.upper() for gene in (row.genes or [])})
            if matched:
                result.append(
                    {
                        "evidence_key": row.evidence_key,
                        "title": row.title,
                        "source_name": row.source_name,
                        "source_record_id": row.source_record_id,
                        "evidence_level": row.evidence_level,
                        "matched_genes": matched,
                        "summary": row.summary,
                    }
                )
        return result[:50]

    async def _matching_herbs(self, genes: list[str]) -> list[dict[str, Any]]:
        rows = list((await self.db.execute(select(PTCHerbModel))).scalars())
        gene_set = set(genes)
        result = []
        for row in rows:
            matched = sorted(gene_set & {gene.upper() for gene in (row.investigated_genes or [])})
            if matched:
                result.append(
                    {
                        "herb_key": row.herb_key,
                        "chinese_name": row.chinese_name,
                        "latin_name": row.latin_name,
                        "matched_genes": matched,
                        "evidence_level": row.evidence_level,
                        "evidence_summary": row.evidence_summary,
                        "clinical_claim": False,
                    }
                )
        return result

    async def _matching_interactions(self, therapy_keys: set[str]) -> list[dict[str, Any]]:
        if not therapy_keys:
            return []
        rows = list(
            (
                await self.db.execute(
                    select(PTCHerbDrugInteractionModel).where(
                        PTCHerbDrugInteractionModel.therapy_key.in_(therapy_keys)
                    )
                )
            ).scalars()
        )
        return [
            {
                "herb_key": row.herb_key,
                "therapy_key": row.therapy_key,
                "interaction_type": row.interaction_type,
                "severity": row.severity,
                "mechanism": row.mechanism,
                "clinical_effect": row.clinical_effect,
                "recommendation": row.recommendation,
                "evidence_level": row.evidence_level,
                "source_name": row.source_name,
            }
            for row in rows
        ]


def dashboard_dict(value: IntegratedDashboard) -> dict[str, Any]:
    return asdict(value)


__all__ = ["PTCIntegratedService", "IntegratedDashboard", "dashboard_dict"]
