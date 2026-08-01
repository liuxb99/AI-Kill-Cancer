"""Reproducible, checksum-protected PTC research snapshots.

Snapshots contain de-identified public research data only. They are designed
for audit, comparison and reproducibility, not clinical decision making.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.backend.database.session import get_db
from src.backend.domain.ptc_knowledge import (
    PTCClinicalTrialModel,
    PTCEvidenceRecordModel,
    PTCTherapyModel,
    PTCTherapyTargetModel,
)
from src.backend.domain.ptc_research import PTCImportBatchModel, PTCResearchCaseModel

router = APIRouter(prefix="/ptc-snapshots", tags=["ptc-snapshots"])
SNAPSHOT_SCHEMA = "ptc-research-snapshot-v1"


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _canonical_bytes(content: dict[str, Any]) -> bytes:
    return json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def _checksum(content: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_bytes(content)).hexdigest()


def verify_snapshot_document(document: dict[str, Any]) -> dict[str, Any]:
    expected = str(document.get("checksum_sha256") or "")
    content = document.get("content")
    if not isinstance(content, dict):
        return {"valid": False, "expected": expected or None, "actual": None, "reason": "Snapshot content is missing or invalid."}
    actual = _checksum(content)
    return {
        "valid": bool(expected) and expected == actual,
        "expected": expected or None,
        "actual": actual,
        "schema": document.get("schema"),
        "case_id": content.get("case", {}).get("case_id") if isinstance(content.get("case"), dict) else None,
        "reason": None if expected == actual and expected else "SHA-256 checksum does not match snapshot content.",
    }


@router.get("/case/{case_id}")
async def create_case_snapshot(
    case_id: str,
    gene: str | None = Query(default=None, max_length=32),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    case = (await db.execute(
        select(PTCResearchCaseModel)
        .options(
            selectinload(PTCResearchCaseModel.variants),
            selectinload(PTCResearchCaseModel.outcomes),
        )
        .where(PTCResearchCaseModel.case_id == case_id)
    )).scalar_one_or_none()
    if case is None:
        raise HTTPException(status_code=404, detail="PTC research case not found")

    selected_gene = gene.upper() if gene else None
    variants = [item for item in case.variants if not selected_gene or item.gene.upper() == selected_gene]
    if selected_gene and not variants:
        raise HTTPException(status_code=404, detail="Requested gene is not present in this case")
    genes = sorted({item.gene.upper() for item in variants if item.gene})

    target_rows = list((await db.execute(
        select(PTCTherapyTargetModel, PTCTherapyModel)
        .join(PTCTherapyModel, PTCTherapyModel.id == PTCTherapyTargetModel.therapy_id)
        .where(PTCTherapyTargetModel.gene_symbol.in_(genes))
        .order_by(PTCTherapyModel.name)
    )).all()) if genes else []

    evidence = list((await db.execute(
        select(PTCEvidenceRecordModel)
        .where(PTCEvidenceRecordModel.gene_symbol.in_(genes))
        .order_by(PTCEvidenceRecordModel.evidence_key)
    )).scalars()) if genes else []

    trials = list((await db.execute(
        select(PTCClinicalTrialModel)
        .where(or_(*[PTCClinicalTrialModel.target_genes.contains([item]) for item in genes]))
        .order_by(PTCClinicalTrialModel.nct_id)
    )).scalars()) if genes else []

    batches = list((await db.execute(
        select(PTCImportBatchModel)
        .order_by(PTCImportBatchModel.started_at.desc())
        .limit(20)
    )).scalars())

    content: dict[str, Any] = {
        "case": {
            "case_id": case.case_id,
            "source_dataset": case.source_dataset,
            "source_project": case.source_project,
            "disease": case.disease,
            "sex": case.sex,
            "age_range": case.age_range,
            "pathologic_stage": case.pathologic_stage,
            "tnm": {"t": case.t_status, "n": case.n_status, "m": case.m_status},
            "vital_status": case.vital_status,
            "days_to_last_follow_up": case.days_to_last_follow_up,
            "days_to_death": case.days_to_death,
            "source_record_id": case.source_record_id,
            "created_at": _iso(case.created_at),
            "updated_at": _iso(case.updated_at),
        },
        "selected_gene": selected_gene,
        "variants": [
            {
                "variant_id": item.variant_id,
                "gene": item.gene,
                "chromosome": item.chromosome,
                "position": item.position,
                "reference": item.reference,
                "alternate": item.alternate,
                "variant_type": item.variant_type,
                "classification": item.classification,
                "protein_change": item.protein_change,
                "source_record_id": item.source_record_id,
                "created_at": _iso(item.created_at),
            }
            for item in sorted(variants, key=lambda value: (value.gene, value.variant_id))
        ],
        "outcomes": [
            {
                "outcome_id": item.outcome_id,
                "outcome_type": item.outcome_type,
                "outcome_value": item.outcome_value,
                "observed_at": _iso(item.observed_at),
                "source_record_id": item.source_record_id,
                "created_at": _iso(item.created_at),
            }
            for item in sorted(case.outcomes, key=lambda value: value.outcome_id)
        ],
        "therapies": [
            {
                "therapy_key": therapy.therapy_key,
                "name": therapy.name,
                "generic_name": therapy.generic_name,
                "approval_status": therapy.approval_status,
                "mechanism": therapy.mechanism,
                "target": {
                    "gene": target.gene_symbol,
                    "variant": target.variant,
                    "interaction_type": target.interaction_type,
                    "evidence_level": target.evidence_level,
                },
                "source_name": therapy.source_name,
                "source_record_id": therapy.source_record_id,
                "source_url": therapy.source_url,
                "source_version": therapy.source_version,
                "retrieved_at": _iso(therapy.retrieved_at),
            }
            for target, therapy in target_rows
        ],
        "evidence": [
            {
                "evidence_key": item.evidence_key,
                "source_name": item.source_name,
                "source_record_id": item.source_record_id,
                "title": item.title,
                "summary": item.summary,
                "evidence_type": item.evidence_type,
                "evidence_level": item.evidence_level,
                "direction": item.direction,
                "gene_symbol": item.gene_symbol,
                "variant": item.variant,
                "publication_id": item.publication_id,
                "citation": item.citation,
                "source_url": item.source_url,
                "payload": item.payload or {},
                "retrieved_at": _iso(item.retrieved_at),
            }
            for item in evidence
        ],
        "clinical_trials": [
            {
                "nct_id": item.nct_id,
                "brief_title": item.brief_title,
                "overall_status": item.overall_status,
                "phases": item.phases or [],
                "conditions": item.conditions or [],
                "interventions": item.interventions or [],
                "target_genes": item.target_genes or [],
                "eligibility": item.eligibility,
                "locations": item.locations or [],
                "source_url": item.source_url,
                "source_version": item.source_version,
                "last_update_posted": item.last_update_posted,
                "retrieved_at": _iso(item.retrieved_at),
            }
            for item in trials
        ],
        "import_batches": [
            {
                "batch_id": item.batch_id,
                "source_dataset": item.source_dataset,
                "source_version": item.source_version,
                "status": item.status,
                "record_count": item.record_count,
                "error_count": item.error_count,
                "checksum": item.checksum,
                "started_at": _iso(item.started_at),
                "completed_at": _iso(item.completed_at),
            }
            for item in batches
        ],
        "counts": {
            "variants": len(variants),
            "outcomes": len(case.outcomes),
            "therapies": len(target_rows),
            "evidence": len(evidence),
            "clinical_trials": len(trials),
            "import_batches": len(batches),
        },
    }
    checksum = _checksum(content)
    return {
        "schema": SNAPSHOT_SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "checksum_algorithm": "SHA-256",
        "checksum_sha256": checksum,
        "content": content,
        "trace": [
            {"step": 1, "name": "load_deidentified_case", "records": 1},
            {"step": 2, "name": "collect_research_dependencies", "records": sum(content["counts"].values())},
            {"step": 3, "name": "canonicalize_json", "records": 1},
            {"step": 4, "name": "calculate_sha256", "records": 1},
        ],
        "disclaimer": "Research reproducibility artifact only. It is not a medical record, medical advice, or treatment recommendation.",
    }


@router.post("/verify")
async def verify_snapshot(document: dict[str, Any] = Body(...)) -> dict[str, Any]:
    return verify_snapshot_document(document)


__all__ = ["router", "create_case_snapshot", "verify_snapshot", "verify_snapshot_document"]
