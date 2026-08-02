"""Longitudinal, auditable PTC research timeline.

The timeline combines de-identified public research records. Dates are labelled
by semantics so ingestion timestamps are never presented as clinical event time.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.backend.database.session import get_db
from src.backend.domain.ptc_knowledge import (
    PTCClinicalTrialModel,
    PTCEvidenceRecordModel,
    PTCTherapyTargetModel,
)
from src.backend.domain.ptc_research import (
    PTCImportBatchModel,
    PTCResearchCaseModel,
)

router = APIRouter(prefix="/ptc-timeline", tags=["ptc-timeline"])


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _event(
    event_type: str,
    title: str,
    timestamp: datetime | None,
    date_semantics: str,
    *,
    subtitle: str | None = None,
    gene: str | None = None,
    source: str | None = None,
    source_url: str | None = None,
    payload: dict[str, Any] | None = None,
    actions: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    return {
        "event_type": event_type,
        "title": title,
        "subtitle": subtitle,
        "timestamp": _iso(timestamp),
        "date_semantics": date_semantics,
        "gene": gene,
        "source": source,
        "source_url": source_url,
        "payload": payload or {},
        "actions": actions or [],
    }


@router.get("/case/{case_id}")
async def get_ptc_case_timeline(
    case_id: str,
    gene: str | None = Query(default=None, max_length=32),
    limit: int = Query(default=250, ge=1, le=1000),
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

    selected_gene = gene.strip().upper() if gene else None
    case_genes = {item.gene.strip().upper() for item in case.variants if item.gene}
    if selected_gene and selected_gene not in case_genes:
        raise HTTPException(status_code=404, detail="Gene is not present in this research case")
    genes = {selected_gene} if selected_gene else case_genes

    events: list[dict[str, Any]] = [
        _event(
            "case_ingested",
            f"Research case {case.case_id} ingested",
            case.created_at,
            "ingested_at",
            subtitle=f"{case.pathologic_stage or 'Stage unavailable'} · {case.vital_status or 'Outcome unavailable'}",
            source=case.source_dataset,
            payload={
                "stage": case.pathologic_stage,
                "tnm": [case.t_status, case.n_status, case.m_status],
                "sex": case.sex,
                "age_range": case.age_range,
            },
            actions=[{"type": "open_3d", "label": "Open case 3D"}],
        )
    ]
    if case.updated_at and case.updated_at != case.created_at:
        events.append(_event(
            "case_updated",
            "Research case metadata updated",
            case.updated_at,
            "ingested_at",
            source=case.source_dataset,
        ))

    for variant in case.variants:
        variant_gene = variant.gene.strip().upper()
        if selected_gene and variant_gene != selected_gene:
            continue
        events.append(_event(
            "variant_ingested",
            f"{variant_gene} {variant.protein_change or variant.variant_id}",
            variant.created_at,
            "ingested_at",
            subtitle=variant.classification,
            gene=variant_gene,
            source=variant.source_dataset,
            payload={
                "variant_id": variant.variant_id,
                "chromosome": variant.chromosome,
                "position": variant.position,
                "classification": variant.classification,
            },
            actions=[
                {"type": "open_protein", "label": f"Open {variant_gene} protein 3D"},
                {"type": "open_matrix", "label": f"Open {variant_gene} evidence matrix"},
            ],
        ))

    for outcome in case.outcomes:
        timestamp = outcome.observed_at or outcome.created_at
        semantics = "observed_at" if outcome.observed_at else "ingested_at"
        events.append(_event(
            "outcome_recorded",
            outcome.outcome_type,
            timestamp,
            semantics,
            subtitle=outcome.outcome_value,
            source=outcome.source_dataset,
            payload={"outcome_id": outcome.outcome_id, "value": outcome.outcome_value},
        ))

    if genes:
        targets = list((await db.execute(
            select(PTCTherapyTargetModel)
            .options(selectinload(PTCTherapyTargetModel.therapy))
            .where(PTCTherapyTargetModel.gene_symbol.in_(sorted(genes)))
        )).scalars().unique())
        for target in targets:
            therapy = target.therapy
            if therapy is None:
                continue
            events.append(_event(
                "therapy_knowledge_ingested",
                therapy.name,
                therapy.retrieved_at or therapy.created_at,
                "retrieved_at",
                subtitle=therapy.approval_status,
                gene=target.gene_symbol,
                source=therapy.source_name,
                source_url=therapy.source_url,
                payload={
                    "therapy_key": therapy.therapy_key,
                    "mechanism": therapy.mechanism,
                    "interaction_type": target.interaction_type,
                    "variant": target.variant,
                },
                actions=[{"type": "open_matrix", "label": "Open evidence matrix"}],
            ))

        evidence = list((await db.execute(
            select(PTCEvidenceRecordModel)
            .where(PTCEvidenceRecordModel.gene_symbol.in_(sorted(genes)))
        )).scalars())
        for item in evidence:
            payload = item.payload or {}
            events.append(_event(
                "evidence_ingested",
                item.title or item.evidence_key,
                item.retrieved_at or item.created_at,
                "retrieved_at",
                subtitle=f"{item.source_name} · {item.evidence_level or 'ungraded'}",
                gene=item.gene_symbol,
                source=item.source_name,
                source_url=item.source_url,
                payload={
                    "evidence_key": item.evidence_key,
                    "publication_id": item.publication_id,
                    "figures": len(payload.get("figures") or []),
                    "tables": len(payload.get("tables") or []),
                },
                actions=[{"type": "open_literature", "label": "Open publication assets"}],
            ))

        trials = list((await db.execute(
            select(PTCClinicalTrialModel).where(
                or_(*[PTCClinicalTrialModel.target_genes.contains([item]) for item in sorted(genes)])
            )
        )).scalars()) if genes else []
        for trial in trials:
            events.append(_event(
                "trial_ingested",
                trial.brief_title,
                trial.retrieved_at or trial.created_at,
                "retrieved_at",
                subtitle=f"{trial.nct_id} · {trial.overall_status or 'status unavailable'}",
                source="ClinicalTrials.gov",
                source_url=trial.source_url,
                payload={
                    "nct_id": trial.nct_id,
                    "phases": trial.phases,
                    "target_genes": trial.target_genes,
                    "last_update_posted": trial.last_update_posted,
                },
                actions=[{"type": "open_trial", "label": f"Open {trial.nct_id}"}],
            ))

    batches = list((await db.execute(
        select(PTCImportBatchModel)
        .where(PTCImportBatchModel.source_dataset == case.source_dataset)
        .order_by(PTCImportBatchModel.started_at.desc())
        .limit(20)
    )).scalars())
    for batch in batches:
        events.append(_event(
            "import_batch",
            f"Import batch {batch.batch_id}",
            batch.completed_at or batch.started_at,
            "completed_at" if batch.completed_at else "started_at",
            subtitle=f"{batch.status} · {batch.record_count} records",
            source=batch.source_dataset,
            payload={
                "status": batch.status,
                "record_count": batch.record_count,
                "error_count": batch.error_count,
                "source_version": batch.source_version,
                "checksum": batch.checksum,
            },
        ))

    events.sort(key=lambda item: item["timestamp"] or "", reverse=True)
    events = events[:limit]
    by_type: dict[str, int] = {}
    for item in events:
        by_type[item["event_type"]] = by_type.get(item["event_type"], 0) + 1

    return {
        "case_id": case.case_id,
        "selected_gene": selected_gene,
        "genes": sorted(case_genes),
        "count": len(events),
        "events": events,
        "summary": {
            "by_type": by_type,
            "first_timestamp": events[-1]["timestamp"] if events else None,
            "latest_timestamp": events[0]["timestamp"] if events else None,
        },
        "trace": [
            {"step": 1, "name": "load_case_variants_outcomes", "records": 1 + len(case.variants) + len(case.outcomes)},
            {"step": 2, "name": "resolve_gene_knowledge", "records": len(events)},
            {"step": 3, "name": "label_date_semantics", "records": len(events)},
            {"step": 4, "name": "sort_and_limit_timeline", "records": len(events)},
        ],
        "disclaimer": (
            "Research Digital Thread only. Ingestion and retrieval timestamps are not clinical event dates. "
            "This timeline is not a patient chart or treatment history."
        ),
    }


__all__ = ["router", "get_ptc_case_timeline"]
