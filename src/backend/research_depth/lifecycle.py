from __future__ import annotations

import uuid
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.domain.research_depth import ResearchEventModel, ResearchHypothesisModel

ALLOWED_HYPOTHESIS_STATUSES = {
    "open",
    "supported",
    "refuted",
    "inconclusive",
    "superseded",
}


async def transition_hypothesis_status(
    db: AsyncSession,
    hypothesis: ResearchHypothesisModel,
    *,
    status: str,
    rationale: str,
    source_id: str | None = None,
) -> ResearchEventModel:
    """Record a research hypothesis state transition with an auditable event."""
    normalized = status.strip().lower()
    if normalized not in ALLOWED_HYPOTHESIS_STATUSES:
        raise ValueError(f"Unsupported hypothesis status: {status}")
    if not rationale.strip():
        raise ValueError("Hypothesis status transition requires a rationale")

    previous = hypothesis.status
    hypothesis.status = normalized
    hypothesis.updated_at = datetime.utcnow()
    event = ResearchEventModel(
        event_key=f"hypothesis-status:{hypothesis.id}:{uuid.uuid4()}",
        event_type="hypothesis_status_changed",
        gene_symbol=hypothesis.gene_symbol,
        hypothesis_id=hypothesis.id,
        observed_at=hypothesis.updated_at,
        date_semantics="reviewed_at",
        source_type="research_annotation",
        source_id=source_id,
        provenance={
            "hypothesis_key": hypothesis.hypothesis_key,
            "version": hypothesis.version,
            "input_fingerprint": hypothesis.input_fingerprint,
        },
        payload={
            "previous_status": previous,
            "new_status": normalized,
            "rationale": rationale.strip(),
            "clinical_use": False,
        },
    )
    db.add(event)
    await db.flush()
    return event


def prioritize_research_tasks(hypotheses: Iterable[Any]) -> list[dict[str, Any]]:
    """Aggregate next-data needs across active hypotheses into research tasks."""
    active = [
        item
        for item in hypotheses
        if str(getattr(item, "status", "open")) in {"open", "inconclusive", "supported"}
    ]
    counts: Counter[str] = Counter()
    refs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    uncertainty_counts: Counter[str] = Counter()

    for item in active:
        for task in getattr(item, "next_data_needed", []) or []:
            normalized = str(task).strip()
            if not normalized:
                continue
            counts[normalized] += 1
            refs[normalized].append(
                {
                    "hypothesis_id": str(getattr(item, "id", "")),
                    "hypothesis_key": getattr(item, "hypothesis_key", None),
                    "version": getattr(item, "version", None),
                    "gene_symbol": getattr(item, "gene_symbol", None),
                    "status": getattr(item, "status", None),
                }
            )
        for uncertainty in getattr(item, "uncertainties", []) or []:
            uncertainty_counts[str(uncertainty)] += 1

    tasks = []
    for task, count in counts.items():
        related = refs[task]
        genes = sorted({str(item.get("gene_symbol") or "") for item in related if item.get("gene_symbol")})
        priority_score = count * 10 + len(genes) * 2
        if "independent" in task.lower() or "replication" in task.lower():
            priority_score += 5
        if "outcome" in task.lower() or "endpoint" in task.lower():
            priority_score += 3
        tasks.append(
            {
                "task": task,
                "priority_score": priority_score,
                "hypotheses": count,
                "genes": genes,
                "hypothesis_references": related,
                "research_only": True,
            }
        )

    tasks.sort(key=lambda item: (-item["priority_score"], item["task"]))
    return tasks


async def load_hypothesis_versions(
    db: AsyncSession,
    hypothesis_key: str,
) -> list[ResearchHypothesisModel]:
    return list(
        (
            await db.execute(
                select(ResearchHypothesisModel)
                .where(ResearchHypothesisModel.hypothesis_key == hypothesis_key)
                .order_by(ResearchHypothesisModel.version.asc())
            )
        ).scalars()
    )


__all__ = [
    "ALLOWED_HYPOTHESIS_STATUSES",
    "transition_hypothesis_status",
    "prioritize_research_tasks",
    "load_hypothesis_versions",
]
