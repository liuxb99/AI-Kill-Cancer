"""PTC research data provenance, freshness, and coverage audit.

The audit reports objective repository state. Freshness thresholds are project
operational policies, not statements about clinical validity or legal reuse.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database.session import get_db
from src.backend.domain.ptc_knowledge import (
    PTCClinicalTrialModel,
    PTCEvidenceRecordModel,
    PTCTherapyModel,
    PTCTherapyTargetModel,
)
from src.backend.domain.ptc_research import (
    PTCImportBatchModel,
    PTCResearchCaseModel,
    PTCVariantModel,
)

router = APIRouter(prefix="/ptc-data-quality", tags=["ptc-data-quality"])

SOURCE_POLICIES: dict[str, dict[str, Any]] = {
    "TCGA-THCA": {
        "label": "GDC / TCGA-THCA",
        "stale_after_days": 180,
        "homepage": "https://portal.gdc.cancer.gov/projects/TCGA-THCA",
        "data_role": "de-identified public research cases and variants",
    },
    "ClinicalTrials.gov": {
        "label": "ClinicalTrials.gov",
        "stale_after_days": 14,
        "homepage": "https://clinicaltrials.gov/",
        "data_role": "trial registry metadata",
    },
    "openFDA": {
        "label": "openFDA Drug Label",
        "stale_after_days": 30,
        "homepage": "https://open.fda.gov/apis/drug/label/",
        "data_role": "drug label and safety metadata",
    },
    "PubMed": {
        "label": "PubMed / PMC",
        "stale_after_days": 30,
        "homepage": "https://pubmed.ncbi.nlm.nih.gov/",
        "data_role": "publication abstracts and open-full-text assets",
    },
    "CIViC": {
        "label": "CIViC",
        "stale_after_days": 14,
        "homepage": "https://civicdb.org/",
        "data_role": "community-curated clinical interpretation evidence",
    },
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _age_days(value: datetime | None, now: datetime) -> float | None:
    normalized = _as_utc(value)
    return round((now - normalized).total_seconds() / 86400, 2) if normalized else None


def _freshness(last_seen: datetime | None, stale_after_days: int, now: datetime) -> tuple[str, float | None]:
    age = _age_days(last_seen, now)
    if age is None:
        return "missing", None
    return ("stale" if age > stale_after_days else "fresh"), age


async def _load_inventory(db: AsyncSession) -> dict[str, Any]:
    case_count = await db.scalar(select(func.count()).select_from(PTCResearchCaseModel)) or 0
    variant_count = await db.scalar(select(func.count()).select_from(PTCVariantModel)) or 0
    therapy_count = await db.scalar(select(func.count()).select_from(PTCTherapyModel)) or 0
    evidence_count = await db.scalar(select(func.count()).select_from(PTCEvidenceRecordModel)) or 0
    trial_count = await db.scalar(select(func.count()).select_from(PTCClinicalTrialModel)) or 0
    batch_count = await db.scalar(select(func.count()).select_from(PTCImportBatchModel)) or 0
    return {
        "cases": case_count,
        "variants": variant_count,
        "therapies": therapy_count,
        "evidence": evidence_count,
        "trials": trial_count,
        "import_batches": batch_count,
    }


async def _load_sources(db: AsyncSession, now: datetime) -> list[dict[str, Any]]:
    evidence_rows = list((await db.execute(select(PTCEvidenceRecordModel))).scalars())
    therapy_rows = list((await db.execute(select(PTCTherapyModel))).scalars())
    trial_rows = list((await db.execute(select(PTCClinicalTrialModel))).scalars())
    batch_rows = list((await db.execute(select(PTCImportBatchModel))).scalars())

    evidence_by_source: dict[str, list[PTCEvidenceRecordModel]] = defaultdict(list)
    for row in evidence_rows:
        evidence_by_source[row.source_name].append(row)
    therapy_by_source: dict[str, list[PTCTherapyModel]] = defaultdict(list)
    for row in therapy_rows:
        therapy_by_source[row.source_name].append(row)

    result: list[dict[str, Any]] = []
    for source_name, policy in SOURCE_POLICIES.items():
        if source_name == "TCGA-THCA":
            records = [item for item in batch_rows if item.source_dataset == "TCGA-THCA"]
            count = sum(item.record_count for item in records)
            last_seen = max((item.completed_at or item.started_at for item in records), default=None)
            missing_url = 0
            missing_version = sum(not item.source_version for item in records)
            failures = sum(item.status not in {"completed", "success"} for item in records)
        elif source_name == "ClinicalTrials.gov":
            count = len(trial_rows)
            last_seen = max((item.retrieved_at for item in trial_rows), default=None)
            missing_url = sum(not item.source_url for item in trial_rows)
            missing_version = sum(not item.source_version for item in trial_rows)
            failures = 0
        elif source_name == "openFDA":
            records = therapy_by_source.get(source_name, [])
            count = len(records)
            last_seen = max((item.retrieved_at for item in records), default=None)
            missing_url = sum(not item.source_url for item in records)
            missing_version = sum(not item.source_version for item in records)
            failures = 0
        else:
            records = evidence_by_source.get(source_name, [])
            count = len(records)
            last_seen = max((item.retrieved_at for item in records), default=None)
            missing_url = sum(not item.source_url for item in records)
            missing_version = 0
            failures = 0

        freshness, age = _freshness(last_seen, policy["stale_after_days"], now)
        result.append({
            "source_name": source_name,
            **policy,
            "record_count": count,
            "last_retrieved_at": _as_utc(last_seen).isoformat() if last_seen else None,
            "age_days": age,
            "freshness": freshness,
            "missing_source_url": missing_url,
            "missing_source_version": missing_version,
            "failed_or_incomplete_batches": failures,
        })
    return result


async def _load_gene_coverage(db: AsyncSession) -> list[dict[str, Any]]:
    variants = list((await db.execute(select(PTCVariantModel))).scalars())
    targets = list((await db.execute(select(PTCTherapyTargetModel))).scalars())
    evidence = list((await db.execute(select(PTCEvidenceRecordModel))).scalars())
    trials = list((await db.execute(select(PTCClinicalTrialModel))).scalars())

    variant_counts = Counter(item.gene.upper() for item in variants if item.gene)
    target_counts = Counter(item.gene_symbol.upper() for item in targets if item.gene_symbol)
    evidence_counts = Counter(item.gene_symbol.upper() for item in evidence if item.gene_symbol)
    trial_counts: Counter[str] = Counter()
    for trial in trials:
        trial_counts.update(str(item).upper() for item in (trial.target_genes or []) if item)

    genes = sorted(set(variant_counts) | set(target_counts) | set(evidence_counts) | set(trial_counts))
    rows = []
    for gene in genes:
        gaps = []
        if variant_counts[gene] == 0:
            gaps.append("no_case_variant")
        if target_counts[gene] == 0:
            gaps.append("no_therapy_target")
        if evidence_counts[gene] == 0:
            gaps.append("no_evidence")
        if trial_counts[gene] == 0:
            gaps.append("no_trial")
        rows.append({
            "gene": gene,
            "case_variants": variant_counts[gene],
            "therapy_targets": target_counts[gene],
            "evidence_records": evidence_counts[gene],
            "clinical_trials": trial_counts[gene],
            "coverage_score": 4 - len(gaps),
            "gaps": gaps,
        })
    rows.sort(key=lambda item: (-item["coverage_score"], -item["case_variants"], item["gene"]))
    return rows


@router.get("/overview")
async def get_data_quality_overview(
    stale_only: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    now = _utcnow()
    inventory = await _load_inventory(db)
    sources = await _load_sources(db, now)
    gene_coverage = await _load_gene_coverage(db)
    if stale_only:
        sources = [item for item in sources if item["freshness"] != "fresh"]

    issues: list[dict[str, Any]] = []
    for source in sources:
        if source["freshness"] != "fresh":
            issues.append({"severity": "warning", "source": source["source_name"], "code": f"source_{source['freshness']}"})
        if source["missing_source_url"]:
            issues.append({"severity": "warning", "source": source["source_name"], "code": "missing_source_url", "count": source["missing_source_url"]})
        if source["failed_or_incomplete_batches"]:
            issues.append({"severity": "error", "source": source["source_name"], "code": "failed_or_incomplete_batch", "count": source["failed_or_incomplete_batches"]})
    uncovered = [item for item in gene_coverage if item["gaps"]]

    return {
        "generated_at": now.isoformat(),
        "inventory": inventory,
        "sources": sources,
        "gene_coverage": gene_coverage,
        "summary": {
            "fresh_sources": sum(item["freshness"] == "fresh" for item in sources),
            "stale_sources": sum(item["freshness"] == "stale" for item in sources),
            "missing_sources": sum(item["freshness"] == "missing" for item in sources),
            "quality_issues": len(issues),
            "genes_with_gaps": len(uncovered),
        },
        "issues": issues,
        "trace": [
            {"step": 1, "name": "count_persisted_records", "records": sum(inventory.values())},
            {"step": 2, "name": "audit_source_freshness", "records": len(sources)},
            {"step": 3, "name": "audit_gene_coverage", "records": len(gene_coverage)},
            {"step": 4, "name": "emit_objective_quality_gaps", "records": len(issues) + len(uncovered)},
        ],
        "policy_note": "Freshness thresholds are project operational policies and do not determine clinical validity, legal reuse, or medical suitability.",
    }


@router.get("/gene/{gene}")
async def get_gene_quality(gene: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    normalized = gene.upper()
    rows = await _load_gene_coverage(db)
    row = next((item for item in rows if item["gene"] == normalized), None)
    return {
        "gene": normalized,
        "found": row is not None,
        "coverage": row or {
            "gene": normalized,
            "case_variants": 0,
            "therapy_targets": 0,
            "evidence_records": 0,
            "clinical_trials": 0,
            "coverage_score": 0,
            "gaps": ["no_case_variant", "no_therapy_target", "no_evidence", "no_trial"],
        },
    }


__all__ = ["router", "get_data_quality_overview", "get_gene_quality"]
