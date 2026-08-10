from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime
from typing import Any, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.domain.research_depth import (
    ResearchEventModel,
    ResearchHypothesisModel,
    ResearchRunModel,
)
from src.backend.research_depth.engine import (
    build_hypotheses,
    cohort_biomarker_stratification,
    evidence_conflict_summary,
)


def _norm(value: str | None) -> str:
    return (value or "").strip().upper()


def research_input_fingerprint(cases: Sequence[Any], evidence: Sequence[Any]) -> str:
    """Stable fingerprint of research facts that can alter a loop result."""
    case_facts = []
    for case in cases:
        case_facts.append(
            {
                "case_id": str(getattr(case, "case_id", "")),
                "source_dataset": str(getattr(case, "source_dataset", "")),
                "stage": getattr(case, "pathologic_stage", None),
                "variants": sorted(
                    (
                        _norm(getattr(item, "gene", None)),
                        _norm(getattr(item, "protein_change", None)),
                        str(getattr(item, "variant_id", "")),
                    )
                    for item in (getattr(case, "variants", []) or [])
                ),
                "outcomes": sorted(
                    (
                        str(getattr(item, "outcome_type", "")),
                        str(getattr(item, "outcome_value", "")),
                        str(getattr(item, "observed_at", "")),
                    )
                    for item in (getattr(case, "outcomes", []) or [])
                ),
            }
        )
    evidence_facts = sorted(
        {
            "id": str(getattr(item, "id", "")),
            "source": str(getattr(item, "source_name", "")),
            "record": str(getattr(item, "source_record_id", "")),
            "direction": str(getattr(getattr(item, "evidence_direction", None), "value", getattr(item, "evidence_direction", ""))),
            "level": str(getattr(getattr(item, "evidence_level", None), "value", getattr(item, "evidence_level", ""))),
        }
        for item in evidence
    )
    payload = {"cases": sorted(case_facts, key=lambda item: item["case_id"]), "evidence": evidence_facts}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _hypothesis_key(gene: str, protein_change: str | None, hypothesis: dict[str, Any]) -> str:
    identity = "|".join(
        [
            gene.strip().upper(),
            (protein_change or "").strip().upper(),
            str(hypothesis.get("type") or "unknown"),
            str(hypothesis.get("claim") or ""),
        ]
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


async def _next_version(db: AsyncSession, hypothesis_key: str) -> int:
    current = (
        await db.execute(
            select(func.max(ResearchHypothesisModel.version)).where(
                ResearchHypothesisModel.hypothesis_key == hypothesis_key
            )
        )
    ).scalar_one_or_none()
    return int(current or 0) + 1


async def execute_research_loop(
    db: AsyncSession,
    *,
    gene: str,
    protein_change: str | None,
    cases: Sequence[Any],
    evidence: Sequence[Any],
) -> dict[str, Any]:
    """Run and persist a deterministic research-only analysis loop.

    The loop never performs clinical actions. Re-running unchanged inputs reuses
    the previous persisted result rather than inventing a new hypothesis version.
    """
    normalized_gene = gene.strip().upper()
    fingerprint = research_input_fingerprint(cases, evidence)
    existing = (
        await db.execute(
            select(ResearchRunModel)
            .where(
                ResearchRunModel.gene_symbol == normalized_gene,
                ResearchRunModel.protein_change == protein_change,
                ResearchRunModel.input_fingerprint == fingerprint,
                ResearchRunModel.status == "completed",
            )
            .order_by(ResearchRunModel.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if existing is not None:
        hypotheses = list(
            (
                await db.execute(
                    select(ResearchHypothesisModel)
                    .where(
                        ResearchHypothesisModel.gene_symbol == normalized_gene,
                        ResearchHypothesisModel.protein_change == protein_change,
                        ResearchHypothesisModel.input_fingerprint == fingerprint,
                    )
                    .order_by(ResearchHypothesisModel.created_at.asc())
                )
            ).scalars()
        )
        return {
            "run_id": str(existing.id),
            "run_key": existing.run_key,
            "input_fingerprint": fingerprint,
            "reused": True,
            "trace": existing.trace,
            "result_summary": existing.result_summary,
            "hypotheses": [_serialize_hypothesis(item) for item in hypotheses],
            "research_only": True,
            "clinical_use": False,
        }

    stratification = cohort_biomarker_stratification(cases, normalized_gene, protein_change)
    conflict = evidence_conflict_summary(evidence)
    generated = build_hypotheses(stratification, conflict)
    now = datetime.utcnow()
    run_key = f"research-run:{normalized_gene}:{uuid.uuid4()}"
    trace = [
        {"step": 1, "name": "fingerprint_inputs", "fingerprint": fingerprint},
        {"step": 2, "name": "outcome_blind_biomarker_stratification", "cases": len(cases)},
        {"step": 3, "name": "post_selection_outcome_feedback"},
        {"step": 4, "name": "evidence_conflict_resolution", "evidence_records": len(evidence)},
        {"step": 5, "name": "falsifiable_hypothesis_generation", "hypotheses": len(generated)},
        {"step": 6, "name": "identify_next_research_data"},
        {"step": 7, "name": "persist_research_digital_thread"},
    ]
    summary = {
        "gene": normalized_gene,
        "protein_change": protein_change,
        "cohort_cases": len(cases),
        "biomarker_positive_cases": stratification["positive"]["cases"],
        "biomarker_negative_cases": stratification["negative"]["cases"],
        "evidence_records": len(evidence),
        "conflict_severity": conflict["conflict_severity"],
        "hypotheses_generated": len(generated),
        "small_sample_warning": stratification["small_sample_warning"],
        "clinical_use": False,
    }
    run = ResearchRunModel(
        run_key=run_key,
        gene_symbol=normalized_gene,
        protein_change=protein_change,
        input_fingerprint=fingerprint,
        status="completed",
        trace=trace,
        result_summary=summary,
        created_at=now,
    )
    db.add(run)
    await db.flush()

    db.add(
        ResearchEventModel(
            event_key=f"{run_key}:cohort",
            event_type="cohort_stratified",
            gene_symbol=normalized_gene,
            run_id=run.id,
            observed_at=now,
            date_semantics="generated_at",
            source_type="research_loop",
            source_id=run_key,
            provenance={"input_fingerprint": fingerprint},
            payload={
                "positive_cases": stratification["positive"]["cases"],
                "negative_cases": stratification["negative"]["cases"],
                "small_sample_warning": stratification["small_sample_warning"],
            },
        )
    )
    db.add(
        ResearchEventModel(
            event_key=f"{run_key}:conflict",
            event_type="evidence_conflict_assessed",
            gene_symbol=normalized_gene,
            run_id=run.id,
            observed_at=now,
            date_semantics="generated_at",
            source_type="research_loop",
            source_id=run_key,
            provenance={"input_fingerprint": fingerprint, "evidence_records": len(evidence)},
            payload={
                "severity": conflict["conflict_severity"],
                "weighted_support": conflict["weighted_support"],
                "weighted_conflict": conflict["weighted_conflict"],
                "unresolved_reasons": conflict["unresolved_reasons"],
            },
        )
    )

    persisted: list[ResearchHypothesisModel] = []
    for hypothesis in generated:
        key = _hypothesis_key(normalized_gene, protein_change, hypothesis)
        version = await _next_version(db, key)
        model = ResearchHypothesisModel(
            hypothesis_key=key,
            gene_symbol=normalized_gene,
            protein_change=protein_change,
            hypothesis_type=str(hypothesis["type"]),
            version=version,
            status="open",
            claim=str(hypothesis["claim"]),
            rationale=hypothesis.get("rationale") or {},
            supporting_observations=hypothesis.get("supporting_observations") or [],
            counter_evidence=hypothesis.get("counter_evidence") or [],
            uncertainties=hypothesis.get("uncertainties") or [],
            falsification_criteria=str(hypothesis["falsification_criteria"]),
            next_data_needed=hypothesis.get("next_data_needed") or [],
            input_fingerprint=fingerprint,
            clinical_use="false",
            created_at=now,
            updated_at=now,
        )
        db.add(model)
        await db.flush()
        persisted.append(model)
        db.add(
            ResearchEventModel(
                event_key=f"{run_key}:hypothesis:{key}:v{version}",
                event_type="hypothesis_generated",
                gene_symbol=normalized_gene,
                hypothesis_id=model.id,
                run_id=run.id,
                observed_at=now,
                date_semantics="generated_at",
                source_type="research_loop",
                source_id=run_key,
                provenance={"input_fingerprint": fingerprint, "version": version},
                payload={
                    "hypothesis_key": key,
                    "hypothesis_type": model.hypothesis_type,
                    "claim": model.claim,
                    "next_data_needed": model.next_data_needed,
                },
            )
        )

    await db.flush()
    return {
        "run_id": str(run.id),
        "run_key": run_key,
        "input_fingerprint": fingerprint,
        "reused": False,
        "trace": trace,
        "result_summary": summary,
        "cohort_stratification": stratification,
        "evidence_conflict": conflict,
        "hypotheses": [_serialize_hypothesis(item) for item in persisted],
        "research_only": True,
        "clinical_use": False,
        "disclaimer": (
            "Controlled research automation only. This loop identifies research signals, "
            "evidence conflicts, falsifiable hypotheses, and data gaps; it performs no clinical action."
        ),
    }


def _serialize_hypothesis(item: ResearchHypothesisModel) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "hypothesis_key": item.hypothesis_key,
        "gene_symbol": item.gene_symbol,
        "protein_change": item.protein_change,
        "hypothesis_type": item.hypothesis_type,
        "version": item.version,
        "status": item.status,
        "claim": item.claim,
        "rationale": item.rationale,
        "supporting_observations": item.supporting_observations,
        "counter_evidence": item.counter_evidence,
        "uncertainties": item.uncertainties,
        "falsification_criteria": item.falsification_criteria,
        "next_data_needed": item.next_data_needed,
        "input_fingerprint": item.input_fingerprint,
        "clinical_use": False,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


__all__ = ["execute_research_loop", "research_input_fingerprint"]
