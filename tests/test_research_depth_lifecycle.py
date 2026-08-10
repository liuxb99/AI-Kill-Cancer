import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.backend.database.models import Base
from src.backend.domain.research_depth import ResearchHypothesisModel
from src.backend.research_depth.lifecycle import (
    prioritize_research_tasks,
    transition_hypothesis_status,
)


@pytest.mark.asyncio
async def test_hypothesis_status_transition_persists_auditable_event():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as db:
        hypothesis = ResearchHypothesisModel(
            hypothesis_key="HYP-1",
            gene_symbol="BRAF",
            protein_change="p.V600E",
            hypothesis_type="cohort_outcome_association",
            version=1,
            status="open",
            claim="Research-only claim",
            rationale={},
            supporting_observations=[],
            counter_evidence=[],
            uncertainties=["small_sample"],
            falsification_criteria="Independent cohort does not reproduce the association.",
            next_data_needed=["independent cohort", "higher outcome completeness"],
            input_fingerprint="f" * 64,
            clinical_use="false",
        )
        db.add(hypothesis)
        await db.flush()

        event = await transition_hypothesis_status(
            db,
            hypothesis,
            status="inconclusive",
            rationale="Outcome completeness remains too low for a stable research conclusion.",
            source_id="review-1",
        )
        await db.commit()

        assert hypothesis.status == "inconclusive"
        assert event.event_type == "hypothesis_status_changed"
        assert event.hypothesis_id == hypothesis.id
        assert event.payload["previous_status"] == "open"
        assert event.payload["new_status"] == "inconclusive"
        assert event.payload["clinical_use"] is False
        assert event.provenance["input_fingerprint"] == "f" * 64

    await engine.dispose()


def test_next_research_tasks_aggregate_active_hypothesis_needs():
    def hypothesis(status, gene, tasks):
        return type(
            "Hypothesis",
            (),
            {
                "id": uuid.uuid4(),
                "hypothesis_key": f"{gene}-{status}",
                "version": 1,
                "gene_symbol": gene,
                "status": status,
                "next_data_needed": tasks,
                "uncertainties": [],
            },
        )()

    tasks = prioritize_research_tasks(
        [
            hypothesis("open", "BRAF", ["independent cohort", "higher outcome completeness"]),
            hypothesis("inconclusive", "RET", ["independent cohort"]),
            hypothesis("refuted", "NTRK1", ["independent cohort"]),
        ]
    )

    assert tasks[0]["task"] == "independent cohort"
    assert tasks[0]["hypotheses"] == 2
    assert tasks[0]["genes"] == ["BRAF", "RET"]
    assert all(item["research_only"] is True for item in tasks)
