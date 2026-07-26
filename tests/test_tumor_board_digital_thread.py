"""
Digital Thread tests for Patient → Recommendation → Clinical Decision → Tumor Board Consensus (Phase 3C).

Covers:
- Patient → Recommendation → Clinical Decision → Tumor Board Consensus full traceability
- All associations can be restored from the database
- From Consensus back to Patient
"""

from __future__ import annotations

import uuid
from datetime import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.backend.database.models import Base
from src.backend.domain.enums import ConsentStatusEnum, SexEnum
from src.backend.domain.patient import PatientModel
from src.backend.domain.recommendation import RecommendationModel
from src.backend.domain.clinical_decision import ClinicalDecisionModel
from src.backend.domain.tumor_board import (
    TumorBoardConsensusModel,
    TumorBoardConsensusTraceModel,
    TumorBoardOpinionModel,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
async def db_session():
    """In-memory SQLite database session for digital thread tests."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False,
    )
    async with async_session() as session:
        yield session
    await engine.dispose()


@pytest.fixture
async def patient(db_session):
    """Create a Patient record."""
    p = PatientModel(
        id=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
        display_name="DT-TEST-PATIENT",
        sex=SexEnum.F,
        consent_status=ConsentStatusEnum.GRANTED,
    )
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p


@pytest.fixture
async def recommendation(db_session, patient):
    """Create a Recommendation record."""
    rec = RecommendationModel(
        recommendation_id="rec-digital-thread-tb-001",
        patient_id=patient.id,
        engine_version="1.0.0",
        status="completed",
        request_payload={"variants": ["EGFR L858R"]},
        result_payload={
            "recommendations": [
                {
                    "drug_name": "Osimertinib",
                    "rank": 1,
                    "overall_score": 0.95,
                },
            ],
            "evidence": [],
        },
    )
    db_session.add(rec)
    await db_session.commit()
    await db_session.refresh(rec)
    return rec


@pytest.fixture
async def clinical_decision(db_session, patient, recommendation):
    """Create a ClinicalDecision record."""
    cd = ClinicalDecisionModel(
        decision_id="cd-digital-thread-tb-001",
        patient_id=patient.id,
        recommendation_id=recommendation.id,
        decision_type="approved",
        reason="Osimertinib approved for EGFR L858R NSCLC.",
        confidence="high",
        evidence_summary={"sources": ["CIViC"], "evidence_count": 1},
        alternatives=[],
        contraindications=[],
        status="active",
    )
    db_session.add(cd)
    await db_session.commit()
    await db_session.refresh(cd)
    return cd


# ═══════════════════════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestDigitalThread:
    """Full traceability: Patient → Recommendation → Clinical Decision → Consensus."""

    async def test_full_chain_creation(
        self,
        db_session,
        patient,
        recommendation,
        clinical_decision,
    ) -> None:
        """Create a Tumor Board Consensus and verify all FK links."""
        consensus = TumorBoardConsensusModel(
            consensus_id="tb-digital-thread-001",
            patient_id=patient.id,
            recommendation_id=recommendation.id,
            clinical_decision_id=clinical_decision.id,
            consensus_status="unanimous",
            consensus_score=1.0,
            final_recommendation="Osimertinib 80mg daily",
            supporting_rationale="All specialists agree.",
            participating_specialties=["medical_oncology", "surgical_oncology"],
        )
        db_session.add(consensus)
        await db_session.flush()

        # Add opinions
        opinions = [
            TumorBoardOpinionModel(
                consensus_id=consensus.id,
                specialty="medical_oncology",
                position="support",
                confidence=0.95,
            ),
            TumorBoardOpinionModel(
                consensus_id=consensus.id,
                specialty="surgical_oncology",
                position="support",
                confidence=0.90,
            ),
        ]
        db_session.add_all(opinions)

        # Add traces
        traces = [
            TumorBoardConsensusTraceModel(
                trace_id="tb-dt-trace-001",
                consensus_id=consensus.id,
                step_order=0,
                step_type="load_context",
            ),
            TumorBoardConsensusTraceModel(
                trace_id="tb-dt-trace-001",
                consensus_id=consensus.id,
                step_order=1,
                step_type="finalize_consensus",
            ),
        ]
        db_session.add_all(traces)
        await db_session.commit()

        # Verify all links via direct queries (avoid lazy-load issues in async)
        assert consensus.id is not None
        assert consensus.patient_id == patient.id
        assert consensus.recommendation_id == recommendation.id
        assert consensus.clinical_decision_id == clinical_decision.id

        from sqlalchemy import func, select

        result_opinions = await db_session.execute(
            select(func.count()).where(TumorBoardOpinionModel.consensus_id == consensus.id)
        )
        opinion_count = result_opinions.scalar()
        assert opinion_count == 2

        result_traces = await db_session.execute(
            select(func.count()).where(TumorBoardConsensusTraceModel.consensus_id == consensus.id)
        )
        trace_count = result_traces.scalar()
        assert trace_count == 2

    async def test_trace_back_to_patient(
        self,
        db_session,
        patient,
        recommendation,
        clinical_decision,
    ) -> None:
        """From Consensus, trace back through CD → Rec → Patient."""
        consensus = TumorBoardConsensusModel(
            consensus_id="tb-dt-traceback-001",
            patient_id=patient.id,
            recommendation_id=recommendation.id,
            clinical_decision_id=clinical_decision.id,
            consensus_status="strong_consensus",
            consensus_score=0.85,
        )
        db_session.add(consensus)
        await db_session.commit()
        await db_session.refresh(consensus)

        # Load the associated clinical decision
        cd_stmt = select(ClinicalDecisionModel).where(
            ClinicalDecisionModel.id == consensus.clinical_decision_id,
        )
        cd_result = await db_session.execute(cd_stmt)
        loaded_cd = cd_result.scalar_one()
        assert loaded_cd.decision_id == "cd-digital-thread-tb-001"

        # Load the recommendation from the CD
        rec_stmt = select(RecommendationModel).where(
            RecommendationModel.id == loaded_cd.recommendation_id,
        )
        rec_result = await db_session.execute(rec_stmt)
        loaded_rec = rec_result.scalar_one()
        assert loaded_rec.recommendation_id == "rec-digital-thread-tb-001"

        # Load the patient from the recommendation
        pat_stmt = select(PatientModel).where(
            PatientModel.id == loaded_rec.patient_id,
        )
        pat_result = await db_session.execute(pat_stmt)
        loaded_patient = pat_result.scalar_one()
        assert loaded_patient.display_name == "DT-TEST-PATIENT"

        # Verify end-to-end: consensus patient matches original patient
        assert consensus.patient_id == patient.id

    async def test_consensus_with_opinions_and_traces_retrievable(
        self,
        db_session,
        patient,
        recommendation,
        clinical_decision,
    ) -> None:
        """Consensus, opinions, and traces can all be retrieved from DB."""
        consensus = TumorBoardConsensusModel(
            consensus_id="tb-dt-retrieve-001",
            patient_id=patient.id,
            recommendation_id=recommendation.id,
            clinical_decision_id=clinical_decision.id,
            consensus_status="split_decision",
            consensus_score=0.45,
        )
        db_session.add(consensus)
        await db_session.flush()

        op1 = TumorBoardOpinionModel(
            consensus_id=consensus.id,
            specialty="medical_oncology",
            position="support",
            confidence=0.95,
        )
        op2 = TumorBoardOpinionModel(
            consensus_id=consensus.id,
            specialty="pathology",
            position="oppose",
            confidence=0.85,
        )
        db_session.add_all([op1, op2])

        trace = TumorBoardConsensusTraceModel(
            trace_id="tb-dt-retrieve-trace",
            consensus_id=consensus.id,
            step_order=0,
            step_type="load_context",
        )
        db_session.add(trace)
        await db_session.commit()

        # Retrieve and verify
        stmt = select(TumorBoardConsensusModel).where(
            TumorBoardConsensusModel.consensus_id == "tb-dt-retrieve-001",
        )
        result = await db_session.execute(stmt)
        loaded = result.scalar_one()

        assert loaded.consensus_status == "split_decision"
        assert loaded.consensus_score == 0.45
        assert len(loaded.opinions) == 2
        assert len(loaded.traces) == 1

        # Verify opinion details
        specialties = {o.specialty for o in loaded.opinions}
        assert specialties == {"medical_oncology", "pathology"}

        # Verify trace details
        assert loaded.traces[0].step_type == "load_context"

    async def test_multiple_consensuses_same_decision(
        self,
        db_session,
        patient,
        recommendation,
        clinical_decision,
    ) -> None:
        """Multiple consensuses can be linked to the same clinical decision."""
        for i in range(2):
            consensus = TumorBoardConsensusModel(
                consensus_id=f"tb-dt-multi-{i:02d}",
                patient_id=patient.id,
                recommendation_id=recommendation.id,
                clinical_decision_id=clinical_decision.id,
                consensus_status="unanimous",
                consensus_score=1.0,
            )
            db_session.add(consensus)
        await db_session.commit()

        # Query by clinical decision
        stmt = select(TumorBoardConsensusModel).where(
            TumorBoardConsensusModel.clinical_decision_id == clinical_decision.id,
        ).order_by(TumorBoardConsensusModel.created_at.desc())
        result = await db_session.execute(stmt)
        consensuses = result.scalars().all()
        assert len(consensuses) == 2
        assert all(c.clinical_decision_id == clinical_decision.id for c in consensuses)

    async def test_consensus_without_patient_still_links(
        self,
        db_session,
        patient,
        recommendation,
        clinical_decision,
    ) -> None:
        """Consensus patient_id must match the patient FK."""
        # This is enforced by FK constraint; patient_id is required.
        consensus = TumorBoardConsensusModel(
            consensus_id="tb-dt-fk-check",
            patient_id=patient.id,
            recommendation_id=recommendation.id,
            clinical_decision_id=clinical_decision.id,
        )
        db_session.add(consensus)
        await db_session.commit()

        # Verify FK chain from consensus to patient
        stmt = select(PatientModel).where(
            PatientModel.id == consensus.patient_id,
        )
        result = await db_session.execute(stmt)
        loaded_patient = result.scalar_one()
        assert loaded_patient.id == patient.id
        assert loaded_patient.display_name == "DT-TEST-PATIENT"
