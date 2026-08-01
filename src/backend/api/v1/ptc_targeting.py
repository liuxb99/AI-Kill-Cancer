"""PTC mutation-to-therapy targeting API.

Combines persisted therapy/evidence/trial records with a curated, deterministic
PTC pathway and protein-domain catalog. This is research decision support only.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.backend.database.session import get_db
from src.backend.domain.ptc_knowledge import (
    PTCClinicalTrialModel,
    PTCEvidenceRecordModel,
    PTCTherapyModel,
)

router = APIRouter(prefix="/ptc-targeting", tags=["ptc-targeting"])

GENE_TARGET_CATALOG: dict[str, dict[str, Any]] = {
    "BRAF": {
        "pathway": "MAPK / ERK",
        "protein_domain": "Serine/threonine kinase domain",
        "domain_range": [457, 717],
        "hotspots": {"V600E": 600, "K601E": 601},
        "downstream": ["MEK1/2", "ERK1/2", "proliferation"],
        "therapy_classes": ["BRAF inhibitor", "MEK inhibitor"],
    },
    "RET": {
        "pathway": "RET–RAS–MAPK / PI3K–AKT",
        "protein_domain": "Tyrosine kinase domain",
        "domain_range": [713, 1012],
        "hotspots": {"M918T": 918, "C634R": 634},
        "downstream": ["RAS", "RAF", "MEK", "ERK", "PI3K", "AKT"],
        "therapy_classes": ["Selective RET inhibitor", "Multi-kinase inhibitor"],
    },
    "NTRK1": {
        "pathway": "TRK–RAS–MAPK / PI3K–AKT",
        "protein_domain": "Tyrosine kinase domain",
        "domain_range": [510, 781],
        "hotspots": {},
        "downstream": ["RAS", "MAPK", "PI3K", "AKT"],
        "therapy_classes": ["TRK inhibitor"],
    },
    "NTRK2": {
        "pathway": "TRK–RAS–MAPK / PI3K–AKT",
        "protein_domain": "Tyrosine kinase domain",
        "domain_range": [538, 807],
        "hotspots": {},
        "downstream": ["RAS", "MAPK", "PI3K", "AKT"],
        "therapy_classes": ["TRK inhibitor"],
    },
    "NTRK3": {
        "pathway": "TRK–RAS–MAPK / PI3K–AKT",
        "protein_domain": "Tyrosine kinase domain",
        "domain_range": [538, 806],
        "hotspots": {},
        "downstream": ["RAS", "MAPK", "PI3K", "AKT"],
        "therapy_classes": ["TRK inhibitor"],
    },
    "NRAS": {
        "pathway": "RAS–RAF–MEK–ERK",
        "protein_domain": "Small GTPase domain",
        "domain_range": [1, 166],
        "hotspots": {"Q61R": 61, "Q61K": 61},
        "downstream": ["RAF", "MEK", "ERK"],
        "therapy_classes": ["MEK inhibitor", "Pathway combination"],
    },
    "HRAS": {
        "pathway": "RAS–RAF–MEK–ERK",
        "protein_domain": "Small GTPase domain",
        "domain_range": [1, 166],
        "hotspots": {"Q61R": 61, "G12V": 12},
        "downstream": ["RAF", "MEK", "ERK"],
        "therapy_classes": ["Farnesyltransferase inhibitor", "MEK inhibitor"],
    },
    "KRAS": {
        "pathway": "RAS–RAF–MEK–ERK",
        "protein_domain": "Small GTPase domain",
        "domain_range": [1, 166],
        "hotspots": {"G12C": 12, "G12D": 12, "Q61R": 61},
        "downstream": ["RAF", "MEK", "ERK"],
        "therapy_classes": ["Allele-specific KRAS inhibitor", "MEK inhibitor"],
    },
    "TERT": {
        "pathway": "Telomere maintenance",
        "protein_domain": "Reverse transcriptase catalytic domain",
        "domain_range": [601, 936],
        "hotspots": {},
        "downstream": ["telomere extension", "replicative immortality"],
        "therapy_classes": ["Clinical-trial strategy"],
    },
    "PIK3CA": {
        "pathway": "PI3K–AKT–mTOR",
        "protein_domain": "PI3/4-kinase catalytic domain",
        "domain_range": [697, 1068],
        "hotspots": {"E545K": 545, "H1047R": 1047},
        "downstream": ["AKT", "mTOR", "cell survival"],
        "therapy_classes": ["PI3K inhibitor", "AKT/mTOR inhibitor"],
    },
    "AKT1": {
        "pathway": "PI3K–AKT–mTOR",
        "protein_domain": "Protein kinase domain",
        "domain_range": [150, 408],
        "hotspots": {"E17K": 17},
        "downstream": ["mTOR", "cell survival", "metabolism"],
        "therapy_classes": ["AKT inhibitor", "mTOR inhibitor"],
    },
}


def _therapy_payload(item: PTCTherapyModel) -> dict[str, Any]:
    return {
        "therapy_key": item.therapy_key,
        "name": item.name,
        "generic_name": item.generic_name,
        "therapy_type": item.therapy_type,
        "approval_status": item.approval_status,
        "mechanism": item.mechanism,
        "indications": item.indications,
        "source_name": item.source_name,
        "source_url": item.source_url,
        "matched_targets": [
            {
                "gene": target.gene_symbol,
                "variant": target.variant,
                "interaction_type": target.interaction_type,
                "evidence_level": target.evidence_level,
            }
            for target in item.targets
        ],
    }


@router.get("/gene/{gene_symbol}")
async def gene_targeting(gene_symbol: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    gene = gene_symbol.strip().upper()
    catalog = GENE_TARGET_CATALOG.get(gene, {
        "pathway": "Uncurated PTC pathway",
        "protein_domain": "Unknown",
        "domain_range": None,
        "hotspots": {},
        "downstream": [],
        "therapy_classes": [],
    })

    therapy_rows = list((await db.execute(
        select(PTCTherapyModel)
        .options(selectinload(PTCTherapyModel.targets))
        .order_by(PTCTherapyModel.name)
    )).scalars().unique())
    therapies = [
        row for row in therapy_rows
        if any(target.gene_symbol.upper() == gene for target in row.targets)
    ]

    evidence = list((await db.execute(
        select(PTCEvidenceRecordModel)
        .where(PTCEvidenceRecordModel.gene_symbol == gene)
        .order_by(PTCEvidenceRecordModel.created_at.desc())
        .limit(100)
    )).scalars())

    trials = list((await db.execute(
        select(PTCClinicalTrialModel)
        .where(or_(
            PTCClinicalTrialModel.brief_title.ilike(f"%{gene}%"),
            PTCClinicalTrialModel.official_title.ilike(f"%{gene}%"),
        ))
        .order_by(PTCClinicalTrialModel.nct_id)
        .limit(50)
    )).scalars())

    return {
        "gene": gene,
        "pathway": catalog,
        "therapies": [_therapy_payload(item) for item in therapies],
        "evidence": [
            {
                "evidence_key": item.evidence_key,
                "source_name": item.source_name,
                "title": item.title,
                "summary": item.summary,
                "evidence_level": item.evidence_level,
                "direction": item.direction,
                "variant": item.variant,
                "citation": item.citation,
                "source_url": item.source_url,
            }
            for item in evidence
        ],
        "trials": [
            {
                "nct_id": item.nct_id,
                "brief_title": item.brief_title,
                "overall_status": item.overall_status,
                "phases": item.phases,
                "interventions": item.interventions,
                "source_url": item.source_url,
            }
            for item in trials
        ],
        "counts": {
            "therapies": len(therapies),
            "evidence": len(evidence),
            "trials": len(trials),
        },
        "disclaimer": "Research decision support only; not a treatment recommendation or prescribing instruction.",
    }


@router.get("/catalog")
async def targeting_catalog() -> dict[str, Any]:
    return {"count": len(GENE_TARGET_CATALOG), "genes": GENE_TARGET_CATALOG}


__all__ = ["router", "GENE_TARGET_CATALOG"]
