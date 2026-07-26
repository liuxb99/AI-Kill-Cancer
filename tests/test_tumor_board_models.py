"""
Tests for Tumor Board ORM models (Phase 3C).

Covers ``TumorBoardConsensusModel``, ``TumorBoardOpinionModel``,
and ``TumorBoardConsensusTraceModel`` — fields, FK associations,
cascade delete, unique constraints, and JSON round-trip.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.backend.database.models import Base


@pytest.fixture
async def db_session():
    """Create an in-memory SQLite database for testing SQLAlchemy models."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()


@pytest.fixture
async def patient(db_session):
    """Create a minimal Patient for FK references."""
    from src.backend.domain.patient import PatientModel

    p = PatientModel(display_name="TBM-TEST-PATIENT")
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p


@pytest.fixture
async def recommendation(db_session, patient):
    """Create a minimal Recommendation for FK references."""
    from src.backend.domain.recommendation import RecommendationModel

    rec = RecommendationModel(
        recommendation_id="tbm-rec-001",
        patient_id=patient.id,
    )
    db_session.add(rec)
    await db_session.commit()
    await db_session.refresh(rec)
    return rec


@pytest.fixture
async def clinical_decision(db_session, patient, recommendation):
    """Create a minimal ClinicalDecision for FK references."""
    from src.backend.domain.clinical_decision import ClinicalDecisionModel

    cd = ClinicalDecisionModel(
        decision_id="tbm-cd-001",
        patient_id=patient.id,
        recommendation_id=recommendation.id,
        decision_type="treatment_selection",
        reason="Test reason",
        confidence="high",
    )
    db_session.add(cd)
    await db_session.commit()
    await db_session.refresh(cd)
    return cd


# ═══════════════════════════════════════════════════════════════════════════════
# TumorBoardConsensusModel Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestTumorBoardConsensusModel:
    """Tests for TumorBoardConsensusModel — core fields, JSON, relations."""

    async def test_create_all_fields(
        self,
        db_session,
        patient,
        recommendation,
        clinical_decision,
    ) -> None:
        """TumorBoardConsensusModel can be created with all fields populated."""
        from src.backend.domain.tumor_board import TumorBoardConsensusModel

        consensus = TumorBoardConsensusModel(
            consensus_id="tb-consensus-001",
            patient_id=patient.id,
            recommendation_id=recommendation.id,
            clinical_decision_id=clinical_decision.id,
            consensus_status="unanimous",
            consensus_score=1.0,
            final_recommendation="Osimertinib 80mg daily",
            supporting_rationale="All specialists agree on the treatment plan.",
            dissenting_opinions=[],
            unresolved_questions=[],
            required_follow_up=["Monitor liver function"],
            participating_specialties=["medical_oncology", "surgical_oncology"],
            created_by=None,
        )
        db_session.add(consensus)
        await db_session.commit()
        await db_session.refresh(consensus)

        assert consensus.id is not None
        assert consensus.consensus_id == "tb-consensus-001"
        assert consensus.consensus_status == "unanimous"
        assert consensus.consensus_score == 1.0
        assert consensus.final_recommendation == "Osimertinib 80mg daily"
        assert consensus.dissenting_opinions == []
        assert consensus.participating_specialties == [
            "medical_oncology", "surgical_oncology",
        ]
        assert consensus.created_at is not None
        assert consensus.updated_at is not None

    async def test_default_values(self, db_session, patient) -> None:
        """TumorBoardConsensusModel should have sensible defaults."""
        from src.backend.domain.tumor_board import TumorBoardConsensusModel

        consensus = TumorBoardConsensusModel(
            consensus_id="tb-default-001",
            patient_id=patient.id,
        )
        db_session.add(consensus)
        await db_session.commit()
        await db_session.refresh(consensus)

        assert consensus.consensus_status == "unanimous"  # default
        assert consensus.consensus_score is None
        assert consensus.final_recommendation is None
        assert consensus.dissenting_opinions is None
        assert consensus.participating_specialties is None
        assert consensus.recommendation_id is None
        assert consensus.clinical_decision_id is None

    async def test_consensus_id_unique(self, db_session, patient) -> None:
        """consensus_id must be unique."""
        from sqlalchemy.exc import IntegrityError

        from src.backend.domain.tumor_board import TumorBoardConsensusModel

        c1 = TumorBoardConsensusModel(
            consensus_id="unique-tb-001",
            patient_id=patient.id,
        )
        db_session.add(c1)
        await db_session.commit()

        c2 = TumorBoardConsensusModel(
            consensus_id="unique-tb-001",
            patient_id=patient.id,
        )
        db_session.add(c2)
        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_json_fields_round_trip(
        self,
        db_session,
        patient,
        recommendation,
        clinical_decision,
    ) -> None:
        """JSON fields survive write-read."""
        from src.backend.domain.tumor_board import TumorBoardConsensusModel

        complex_dissenting = [
            {
                "specialty": "pathology",
                "position": "oppose",
                "weight": 0.8,
                "raw_confidence": 0.85,
                "rationale": "Insufficient biopsy material",
            },
        ]
        complex_participating = [
            "medical_oncology", "surgical_oncology",
            "pathology", "radiology",
        ]

        consensus = TumorBoardConsensusModel(
            consensus_id="tb-json-rt",
            patient_id=patient.id,
            recommendation_id=recommendation.id,
            clinical_decision_id=clinical_decision.id,
            consensus_status="split_decision",
            dissenting_opinions=complex_dissenting,
            unresolved_questions=["Need more imaging"],
            required_follow_up=["Schedule PET-CT"],
            participating_specialties=complex_participating,
        )
        db_session.add(consensus)
        await db_session.commit()
        await db_session.refresh(consensus)

        assert consensus.dissenting_opinions == complex_dissenting
        assert consensus.dissenting_opinions[0]["specialty"] == "pathology"
        assert consensus.unresolved_questions == ["Need more imaging"]
        assert consensus.required_follow_up == ["Schedule PET-CT"]
        assert consensus.participating_specialties == complex_participating

    async def test_opinions_relation(self, db_session, patient) -> None:
        """Consensus can be linked to opinions."""
        from src.backend.domain.tumor_board import (
            TumorBoardConsensusModel,
            TumorBoardOpinionModel,
        )

        consensus = TumorBoardConsensusModel(
            consensus_id="tb-opinion-rel",
            patient_id=patient.id,
        )
        db_session.add(consensus)
        await db_session.flush()

        opinion = TumorBoardOpinionModel(
            consensus_id=consensus.id,
            specialty="medical_oncology",
            position="support",
            confidence=0.95,
        )
        db_session.add(opinion)
        await db_session.commit()

        await db_session.refresh(consensus)
        assert len(consensus.opinions) == 1
        assert consensus.opinions[0].specialty == "medical_oncology"

    async def test_traces_relation(self, db_session, patient) -> None:
        """Consensus can be linked to trace steps."""
        from src.backend.domain.tumor_board import (
            TumorBoardConsensusModel,
            TumorBoardConsensusTraceModel,
        )

        consensus = TumorBoardConsensusModel(
            consensus_id="tb-trace-rel",
            patient_id=patient.id,
        )
        db_session.add(consensus)
        await db_session.flush()

        trace = TumorBoardConsensusTraceModel(
            trace_id="tb-trace-001",
            consensus_id=consensus.id,
            step_order=1,
            step_type="load_context",
        )
        db_session.add(trace)
        await db_session.commit()

        await db_session.refresh(consensus)
        assert len(consensus.traces) == 1
        assert consensus.traces[0].trace_id == "tb-trace-001"

    async def test_cascade_delete_consensus_deletes_opinions_and_traces(
        self,
        db_session,
        patient,
    ) -> None:
        """Deleting a consensus cascade-deletes opinions and traces."""
        from src.backend.domain.tumor_board import (
            TumorBoardConsensusModel,
            TumorBoardConsensusTraceModel,
            TumorBoardOpinionModel,
        )

        consensus = TumorBoardConsensusModel(
            consensus_id="tb-cascade-del",
            patient_id=patient.id,
        )
        db_session.add(consensus)
        await db_session.flush()

        opinion = TumorBoardOpinionModel(
            consensus_id=consensus.id,
            specialty="medical_oncology",
            position="support",
            confidence=0.9,
        )
        db_session.add(opinion)

        trace = TumorBoardConsensusTraceModel(
            trace_id="tb-cascade-trace",
            consensus_id=consensus.id,
            step_order=1,
            step_type="test",
        )
        db_session.add(trace)
        await db_session.commit()

        # Delete the consensus
        await db_session.delete(consensus)
        await db_session.commit()

        # Verify opinion is gone
        stmt = select(TumorBoardOpinionModel).where(
            TumorBoardOpinionModel.specialty == "medical_oncology",
        )
        result = await db_session.execute(stmt)
        assert result.scalar_one_or_none() is None

        # Verify trace is gone
        stmt = select(TumorBoardConsensusTraceModel).where(
            TumorBoardConsensusTraceModel.trace_id == "tb-cascade-trace",
        )
        result = await db_session.execute(stmt)
        assert result.scalar_one_or_none() is None

    async def test_opinions_empty_by_default(self, db_session, patient) -> None:
        """New consensus should have no opinions."""
        from src.backend.domain.tumor_board import TumorBoardConsensusModel

        consensus = TumorBoardConsensusModel(
            consensus_id="tb-no-opinions",
            patient_id=patient.id,
        )
        db_session.add(consensus)
        await db_session.commit()
        await db_session.refresh(consensus)

        assert consensus.opinions == []

    async def test_traces_empty_by_default(self, db_session, patient) -> None:
        """New consensus should have no traces."""
        from src.backend.domain.tumor_board import TumorBoardConsensusModel

        consensus = TumorBoardConsensusModel(
            consensus_id="tb-no-traces",
            patient_id=patient.id,
        )
        db_session.add(consensus)
        await db_session.commit()
        await db_session.refresh(consensus)

        assert consensus.traces == []


# ═══════════════════════════════════════════════════════════════════════════════
# TumorBoardOpinionModel Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestTumorBoardOpinionModel:
    """Tests for TumorBoardOpinionModel — fields, FK, JSON."""

    async def test_create_all_fields(
        self,
        db_session,
        patient,
    ) -> None:
        """TumorBoardOpinionModel can be created with all fields."""
        from src.backend.domain.tumor_board import (
            TumorBoardConsensusModel,
            TumorBoardOpinionModel,
        )

        consensus = TumorBoardConsensusModel(
            consensus_id="tb-opinion-create",
            patient_id=patient.id,
        )
        db_session.add(consensus)
        await db_session.flush()

        opinion = TumorBoardOpinionModel(
            consensus_id=consensus.id,
            specialty="medical_oncology",
            participant_id="dr-smith",
            position="support",
            confidence=0.95,
            rationale="Strong evidence from FLAURA trial",
            supporting_evidence=["PMID: 34567890", "CIViC-123"],
            contraindications=["Liver impairment"],
            preferred_option="Osimertinib",
            alternative_option="Gefitinib",
            requires_more_information=False,
        )
        db_session.add(opinion)
        await db_session.commit()
        await db_session.refresh(opinion)

        assert opinion.id is not None
        assert opinion.specialty == "medical_oncology"
        assert opinion.participant_id == "dr-smith"
        assert opinion.position == "support"
        assert opinion.confidence == 0.95
        assert opinion.rationale == "Strong evidence from FLAURA trial"
        assert opinion.supporting_evidence == ["PMID: 34567890", "CIViC-123"]
        assert opinion.contraindications == ["Liver impairment"]
        assert opinion.preferred_option == "Osimertinib"
        assert opinion.alternative_option == "Gefitinib"
        assert opinion.requires_more_information is False
        assert opinion.created_at is not None

    async def test_default_values(self, db_session, patient) -> None:
        """Opinion should have sensible defaults."""
        from src.backend.domain.tumor_board import (
            TumorBoardConsensusModel,
            TumorBoardOpinionModel,
        )

        consensus = TumorBoardConsensusModel(
            consensus_id="tb-opinion-default",
            patient_id=patient.id,
        )
        db_session.add(consensus)
        await db_session.flush()

        opinion = TumorBoardOpinionModel(
            consensus_id=consensus.id,
            specialty="pathology",
            position="abstain",
        )
        db_session.add(opinion)
        await db_session.commit()
        await db_session.refresh(opinion)

        assert opinion.confidence == 0.5  # default
        assert opinion.requires_more_information is False
        assert opinion.rationale is None
        assert opinion.participant_id is None

    async def test_back_populates_consensus(self, db_session, patient) -> None:
        """Opinion.back_populates consensus."""
        from src.backend.domain.tumor_board import (
            TumorBoardConsensusModel,
            TumorBoardOpinionModel,
        )

        consensus = TumorBoardConsensusModel(
            consensus_id="tb-opinion-backpop",
            patient_id=patient.id,
        )
        db_session.add(consensus)
        await db_session.flush()

        opinion = TumorBoardOpinionModel(
            consensus_id=consensus.id,
            specialty="surgical_oncology",
            position="oppose",
            confidence=0.80,
        )
        db_session.add(opinion)
        await db_session.commit()

        assert opinion.consensus is not None
        assert opinion.consensus.consensus_id == "tb-opinion-backpop"
        assert opinion.consensus_id == consensus.id

    async def test_json_fields_round_trip(self, db_session, patient) -> None:
        """Supporting_evidence and contraindications JSON survive write-read."""
        from src.backend.domain.tumor_board import (
            TumorBoardConsensusModel,
            TumorBoardOpinionModel,
        )

        consensus = TumorBoardConsensusModel(
            consensus_id="tb-opinion-json",
            patient_id=patient.id,
        )
        db_session.add(consensus)
        await db_session.flush()

        opinion = TumorBoardOpinionModel(
            consensus_id=consensus.id,
            specialty="genomics",
            position="support",
            confidence=0.85,
            supporting_evidence=[
                {"source": "CIViC", "id": "123", "tier": "A"},
                {"source": "PubMed", "pmid": "98765432"},
            ],
            contraindications=[
                {"drug": "Pembrolizumab", "reason": "PD-L1 negative", "severity": "major"},
            ],
        )
        db_session.add(opinion)
        await db_session.commit()
        await db_session.refresh(opinion)

        assert len(opinion.supporting_evidence) == 2
        assert opinion.supporting_evidence[0]["source"] == "CIViC"
        assert len(opinion.contraindications) == 1
        assert opinion.contraindications[0]["drug"] == "Pembrolizumab"


# ═══════════════════════════════════════════════════════════════════════════════
# TumorBoardConsensusTraceModel Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestTumorBoardConsensusTraceModel:
    """Tests for TumorBoardConsensusTraceModel — fields, uniqueness, JSON."""

    async def test_create_all_fields(self, db_session, patient) -> None:
        """Trace model can be created with all fields."""
        from src.backend.domain.tumor_board import (
            TumorBoardConsensusModel,
            TumorBoardConsensusTraceModel,
        )

        consensus = TumorBoardConsensusModel(
            consensus_id="tb-trace-create",
            patient_id=patient.id,
        )
        db_session.add(consensus)
        await db_session.flush()

        trace = TumorBoardConsensusTraceModel(
            trace_id="tbc-trace-001",
            consensus_id=consensus.id,
            step_order=3,
            step_type="calculate_weights",
            input_summary={"opinion_count": 4},
            output_summary={"weighted_count": 3, "skipped_count": 1},
        )
        db_session.add(trace)
        await db_session.commit()
        await db_session.refresh(trace)

        assert trace.id is not None
        assert trace.trace_id == "tbc-trace-001"
        assert trace.step_order == 3
        assert trace.step_type == "calculate_weights"
        assert trace.input_summary == {"opinion_count": 4}
        assert trace.output_summary == {"weighted_count": 3, "skipped_count": 1}
        assert trace.created_at is not None

    async def test_trace_id_step_order_unique(self, db_session, patient) -> None:
        """(trace_id, step_order) must be unique."""
        from sqlalchemy.exc import IntegrityError

        from src.backend.domain.tumor_board import (
            TumorBoardConsensusModel,
            TumorBoardConsensusTraceModel,
        )

        consensus = TumorBoardConsensusModel(
            consensus_id="tb-trace-unique",
            patient_id=patient.id,
        )
        db_session.add(consensus)
        await db_session.flush()

        t1 = TumorBoardConsensusTraceModel(
            trace_id="unique-tbc-trace",
            consensus_id=consensus.id,
            step_order=1,
            step_type="load_context",
        )
        db_session.add(t1)
        await db_session.commit()

        # Same trace_id + step_order → should raise
        t2 = TumorBoardConsensusTraceModel(
            trace_id="unique-tbc-trace",
            consensus_id=consensus.id,
            step_order=1,
            step_type="duplicate",
        )
        db_session.add(t2)
        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_same_trace_id_different_step_order_allowed(
        self,
        db_session,
        patient,
    ) -> None:
        """Same trace_id with different step_order is allowed."""
        from src.backend.domain.tumor_board import (
            TumorBoardConsensusModel,
            TumorBoardConsensusTraceModel,
        )

        consensus = TumorBoardConsensusModel(
            consensus_id="tb-trace-multi",
            patient_id=patient.id,
        )
        db_session.add(consensus)
        await db_session.flush()

        traces = [
            TumorBoardConsensusTraceModel(
                trace_id="multi-tbc-trace",
                consensus_id=consensus.id,
                step_order=i,
                step_type=f"step_{i}",
            )
            for i in range(1, 4)
        ]
        db_session.add_all(traces)
        await db_session.commit()

        assert all(t.id is not None for t in traces)

    async def test_json_fields_round_trip(self, db_session, patient) -> None:
        """Input_summary and output_summary JSON survive write-read."""
        from src.backend.domain.tumor_board import (
            TumorBoardConsensusModel,
            TumorBoardConsensusTraceModel,
        )

        consensus = TumorBoardConsensusModel(
            consensus_id="tb-trace-json",
            patient_id=patient.id,
        )
        db_session.add(consensus)
        await db_session.flush()

        complex_input = {
            "opinions": [
                {"specialty": "medical_oncology", "confidence": 0.95},
                {"specialty": "pathology", "confidence": 0.80},
            ],
            "rules": {"min_opinions": 2},
        }
        complex_output = {
            "status": "completed",
            "weighted_opinions": 2,
            "consensus_ratio": 0.85,
        }

        trace = TumorBoardConsensusTraceModel(
            trace_id="tbc-json-rt",
            consensus_id=consensus.id,
            step_order=1,
            step_type="calculate_consensus",
            input_summary=complex_input,
            output_summary=complex_output,
        )
        db_session.add(trace)
        await db_session.commit()
        await db_session.refresh(trace)

        assert trace.input_summary == complex_input
        assert trace.input_summary["opinions"][0]["specialty"] == "medical_oncology"
        assert trace.output_summary == complex_output
        assert trace.output_summary["consensus_ratio"] == 0.85

    async def test_trace_consensus_relation(self, db_session, patient) -> None:
        """Trace back-populates consensus."""
        from src.backend.domain.tumor_board import (
            TumorBoardConsensusModel,
            TumorBoardConsensusTraceModel,
        )

        consensus = TumorBoardConsensusModel(
            consensus_id="tb-trace-backpop",
            patient_id=patient.id,
        )
        db_session.add(consensus)
        await db_session.flush()

        trace = TumorBoardConsensusTraceModel(
            trace_id="backpop-tbc-trace",
            consensus_id=consensus.id,
            step_order=1,
            step_type="load_context",
        )
        db_session.add(trace)
        await db_session.commit()

        assert trace.consensus is not None
        assert trace.consensus.consensus_id == "tb-trace-backpop"
        assert trace.consensus_id == consensus.id

    async def test_multiple_traces_ordered_by_step(
        self,
        db_session,
        patient,
    ) -> None:
        """Multiple traces for a consensus should be ordered by step_order."""
        from src.backend.domain.tumor_board import (
            TumorBoardConsensusModel,
            TumorBoardConsensusTraceModel,
        )

        consensus = TumorBoardConsensusModel(
            consensus_id="tb-multi-trace-order",
            patient_id=patient.id,
        )
        db_session.add(consensus)
        await db_session.flush()

        traces = [
            TumorBoardConsensusTraceModel(
                trace_id=f"ordered-{i}",
                consensus_id=consensus.id,
                step_order=i,
                step_type=f"step_{i}",
            )
            for i in [3, 1, 2]  # intentionally out of order
        ]
        db_session.add_all(traces)
        await db_session.commit()

        await db_session.refresh(consensus)
        assert len(consensus.traces) == 3
        orders = [t.step_order for t in consensus.traces]
        assert orders == sorted(orders)
