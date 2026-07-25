"""
Tests for Clinical Decision SQLAlchemy ORM models.

Covers ``ClinicalDecisionModel`` and ``ClinicalDecisionTraceModel``.
"""
from __future__ import annotations

import pytest
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

    p = PatientModel(display_name="CD-TEST-PATIENT")
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p


@pytest.fixture
async def recommendation(db_session, patient):
    """Create a minimal Recommendation for FK references."""
    from src.backend.domain.recommendation import RecommendationModel

    rec = RecommendationModel(
        recommendation_id="cd-rec-001",
        patient_id=patient.id,
    )
    db_session.add(rec)
    await db_session.commit()
    await db_session.refresh(rec)
    return rec


class TestClinicalDecisionModel:
    """Tests for ClinicalDecisionModel — core fields, JSON, indexes, relations."""

    async def test_create_all_fields(self, db_session, patient, recommendation):
        """ClinicalDecisionModel can be created with all fields populated."""
        from src.backend.domain.clinical_decision import ClinicalDecisionModel

        decision = ClinicalDecisionModel(
            decision_id="dec-001",
            patient_id=patient.id,
            recommendation_id=recommendation.id,
            decision_type="treatment_selection",
            reason="Patient shows EGFR L858R mutation",
            evidence_summary={"sources": ["CIViC"], "evidence_count": 3},
            confidence="high",
            alternatives=[{"drug": "Osimertinib", "rank": 1}],
            contraindications=[{"drug": "Pembrolizumab", "reason": "PD-L1 negative"}],
            status="active",
            created_by=None,
        )
        db_session.add(decision)
        await db_session.commit()
        await db_session.refresh(decision)

        assert decision.id is not None
        assert decision.decision_id == "dec-001"
        assert decision.decision_type == "treatment_selection"
        assert decision.reason == "Patient shows EGFR L858R mutation"
        assert decision.confidence == "high"
        assert decision.status == "active"
        assert decision.created_at is not None
        assert decision.updated_at is not None

    async def test_default_values(self, db_session, patient):
        """ClinicalDecisionModel should have sensible defaults."""
        from src.backend.domain.clinical_decision import ClinicalDecisionModel

        decision = ClinicalDecisionModel(
            decision_id="dec-default",
            patient_id=patient.id,
            decision_type="test",
            reason="Test reason",
            confidence="medium",
        )
        db_session.add(decision)
        await db_session.commit()
        await db_session.refresh(decision)

        assert decision.status == "active"  # default
        assert decision.created_at is not None  # auto-set
        assert decision.updated_at is not None  # auto-set
        assert decision.evidence_summary is None  # nullable
        assert decision.alternatives is None  # nullable
        assert decision.contraindications is None  # nullable
        assert decision.recommendation_id is None  # nullable
        assert decision.created_by is None  # nullable

    async def test_decision_id_unique(self, db_session, patient):
        """decision_id must be unique."""
        from sqlalchemy.exc import IntegrityError

        from src.backend.domain.clinical_decision import ClinicalDecisionModel

        d1 = ClinicalDecisionModel(
            decision_id="unique-dec-001",
            patient_id=patient.id,
            decision_type="test",
            reason="First",
            confidence="high",
        )
        db_session.add(d1)
        await db_session.commit()

        d2 = ClinicalDecisionModel(
            decision_id="unique-dec-001",
            patient_id=patient.id,
            decision_type="test",
            reason="Second",
            confidence="low",
        )
        db_session.add(d2)
        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_json_fields_round_trip(self, db_session, patient):
        """JSON fields (evidence_summary, alternatives, contraindications) survive write-read."""
        from src.backend.domain.clinical_decision import ClinicalDecisionModel

        complex_evidence = {
            "sources": [
                {"name": "CIViC", "id": "123", "level": "A"},
                {"name": "PubMed", "pmid": "34567890"},
            ],
            "evidence_count": 2,
            "nested": {"gene": "EGFR", "variant": "L858R", "scores": [0.95, 0.87]},
        }
        alternatives_data = [
            {"drug": "Osimertinib", "rank": 1, "score": 0.92},
            {"drug": "Gefitinib", "rank": 2, "score": 0.75},
        ]
        contraindications_data = [
            {"drug": "Pembrolizumab", "reason": "PD-L1 negative", "severity": "major"},
        ]

        decision = ClinicalDecisionModel(
            decision_id="json-roundtrip",
            patient_id=patient.id,
            decision_type="treatment_selection",
            reason="RT test",
            confidence="high",
            evidence_summary=complex_evidence,
            alternatives=alternatives_data,
            contraindications=contraindications_data,
        )
        db_session.add(decision)
        await db_session.commit()
        await db_session.refresh(decision)

        assert decision.evidence_summary == complex_evidence
        assert decision.evidence_summary["sources"][0]["name"] == "CIViC"
        assert decision.alternatives == alternatives_data
        assert decision.alternatives[0]["drug"] == "Osimertinib"
        assert decision.contraindications == contraindications_data
        assert decision.contraindications[0]["severity"] == "major"

    async def test_trace_relation(self, db_session, patient):
        """ClinicalDecisionModel can be linked to ClinicalDecisionTraceModel."""
        from src.backend.domain.clinical_decision import (
            ClinicalDecisionModel,
            ClinicalDecisionTraceModel,
        )

        decision = ClinicalDecisionModel(
            decision_id="trace-rel-test",
            patient_id=patient.id,
            decision_type="test",
            reason="Trace relation test",
            confidence="high",
        )
        db_session.add(decision)
        await db_session.flush()

        trace = ClinicalDecisionTraceModel(
            trace_id="cd-trace-001",
            clinical_decision_id=decision.id,
            step_order=1,
            step_type="evidence_collection",
            input_summary={"variants": ["EGFR L858R"]},
            output_summary={"evidence_count": 5},
        )
        db_session.add(trace)
        await db_session.commit()

        # Reload and check relationship
        await db_session.refresh(decision)
        assert len(decision.traces) == 1
        assert decision.traces[0].trace_id == "cd-trace-001"

    async def test_cascade_delete_decision_deletes_traces(self, db_session, patient):
        """Deleting a ClinicalDecisionModel should cascade-delete its traces."""
        from src.backend.domain.clinical_decision import (
            ClinicalDecisionModel,
            ClinicalDecisionTraceModel,
        )
        from sqlalchemy import select

        decision = ClinicalDecisionModel(
            decision_id="cascade-del",
            patient_id=patient.id,
            decision_type="test",
            reason="Cascade test",
            confidence="high",
        )
        db_session.add(decision)
        await db_session.flush()

        trace = ClinicalDecisionTraceModel(
            trace_id="trace-cascade-cd",
            clinical_decision_id=decision.id,
            step_order=1,
            step_type="test",
        )
        db_session.add(trace)
        await db_session.commit()

        # Delete the decision
        await db_session.delete(decision)
        await db_session.commit()

        # Verify trace is gone
        stmt = select(ClinicalDecisionTraceModel).where(
            ClinicalDecisionTraceModel.trace_id == "trace-cascade-cd",
        )
        result = await db_session.execute(stmt)
        assert result.scalar_one_or_none() is None

    async def test_traces_empty_by_default(self, db_session, patient):
        """New decision should have no traces."""
        from src.backend.domain.clinical_decision import ClinicalDecisionModel

        decision = ClinicalDecisionModel(
            decision_id="no-trace",
            patient_id=patient.id,
            decision_type="test",
            reason="No traces",
            confidence="low",
        )
        db_session.add(decision)
        await db_session.commit()
        await db_session.refresh(decision)

        assert decision.traces == []


class TestClinicalDecisionTraceModel:
    """Tests for ClinicalDecisionTraceModel — fields, uniqueness, JSON, ordering."""

    async def test_create_all_fields(self, db_session, patient):
        """ClinicalDecisionTraceModel can be created with all fields populated."""
        from src.backend.domain.clinical_decision import (
            ClinicalDecisionModel,
            ClinicalDecisionTraceModel,
        )

        decision = ClinicalDecisionModel(
            decision_id="trace-create",
            patient_id=patient.id,
            decision_type="test",
            reason="Trace create parent",
            confidence="high",
        )
        db_session.add(decision)
        await db_session.flush()

        trace = ClinicalDecisionTraceModel(
            trace_id="trace-full-001",
            clinical_decision_id=decision.id,
            step_order=3,
            step_type="drug_ranking",
            input_summary={"drugs": ["Osimertinib", "Gefitinib"]},
            output_summary={"rank": 1, "score": 0.92},
        )
        db_session.add(trace)
        await db_session.commit()
        await db_session.refresh(trace)

        assert trace.id is not None
        assert trace.trace_id == "trace-full-001"
        assert trace.step_order == 3
        assert trace.step_type == "drug_ranking"
        assert trace.input_summary == {"drugs": ["Osimertinib", "Gefitinib"]}
        assert trace.output_summary == {"rank": 1, "score": 0.92}
        assert trace.created_at is not None

    async def test_trace_id_unique(self, db_session, patient):
        """trace_id must be unique."""
        from sqlalchemy.exc import IntegrityError

        from src.backend.domain.clinical_decision import (
            ClinicalDecisionModel,
            ClinicalDecisionTraceModel,
        )

        decision = ClinicalDecisionModel(
            decision_id="trace-unique",
            patient_id=patient.id,
            decision_type="test",
            reason="Unique trace test",
            confidence="high",
        )
        db_session.add(decision)
        await db_session.flush()

        t1 = ClinicalDecisionTraceModel(
            trace_id="unique-trace", clinical_decision_id=decision.id, step_order=1, step_type="a"
        )
        db_session.add(t1)
        await db_session.commit()

        t2 = ClinicalDecisionTraceModel(
            trace_id="unique-trace", clinical_decision_id=decision.id, step_order=2, step_type="b"
        )
        db_session.add(t2)
        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_json_fields_round_trip(self, db_session, patient):
        """JSON fields (input_summary, output_summary) survive write-read."""
        from src.backend.domain.clinical_decision import (
            ClinicalDecisionModel,
            ClinicalDecisionTraceModel,
        )

        decision = ClinicalDecisionModel(
            decision_id="trace-json-rt",
            patient_id=patient.id,
            decision_type="test",
            reason="JSON round-trip for trace",
            confidence="medium",
        )
        db_session.add(decision)
        await db_session.flush()

        complex_input = {
            "variants": ["EGFR L858R", "KRAS G12C"],
            "patient_info": {"age": 65, "cancer_type": "NSCLC"},
            "gene_panel": ["EGFR", "KRAS", "BRAF"],
        }
        complex_output = {
            "recommendations": [
                {"drug": "Osimertinib", "score": 0.95, "evidence": ["CIViC"]},
            ],
            "warnings": ["Check liver function"],
        }

        trace = ClinicalDecisionTraceModel(
            trace_id="trace-json-test",
            clinical_decision_id=decision.id,
            step_order=2,
            step_type="analysis",
            input_summary=complex_input,
            output_summary=complex_output,
        )
        db_session.add(trace)
        await db_session.commit()
        await db_session.refresh(trace)

        assert trace.input_summary == complex_input
        assert trace.input_summary["patient_info"]["cancer_type"] == "NSCLC"
        assert trace.output_summary == complex_output
        assert trace.output_summary["recommendations"][0]["drug"] == "Osimertinib"

    async def test_trace_clinical_decision_relation(self, db_session, patient):
        """ClinicalDecisionTraceModel back-populates clinical_decision."""
        from src.backend.domain.clinical_decision import (
            ClinicalDecisionModel,
            ClinicalDecisionTraceModel,
        )

        decision = ClinicalDecisionModel(
            decision_id="trace-backpop",
            patient_id=patient.id,
            decision_type="test",
            reason="Back-populate test",
            confidence="high",
        )
        db_session.add(decision)
        await db_session.flush()

        trace = ClinicalDecisionTraceModel(
            trace_id="backpop-trace",
            clinical_decision_id=decision.id,
            step_order=1,
            step_type="collect",
        )
        db_session.add(trace)
        await db_session.commit()

        assert trace.clinical_decision is not None
        assert trace.clinical_decision.decision_id == "trace-backpop"
        assert trace.clinical_decision_id == decision.id

    async def test_trace_without_decision_allowed(self, db_session):
        """ClinicalDecisionTraceModel.clinical_decision_id is nullable."""
        from src.backend.domain.clinical_decision import ClinicalDecisionTraceModel

        trace = ClinicalDecisionTraceModel(
            trace_id="orphan-trace-cd",
            step_order=1,
            step_type="orphan",
        )
        db_session.add(trace)
        await db_session.commit()
        await db_session.refresh(trace)

        assert trace.id is not None
        assert trace.clinical_decision_id is None

    async def test_trace_without_recommendation_allowed(self, db_session, patient):
        """ClinicalDecisionTraceModel.recommendation_id is nullable."""
        from src.backend.domain.clinical_decision import (
            ClinicalDecisionModel,
            ClinicalDecisionTraceModel,
        )

        decision = ClinicalDecisionModel(
            decision_id="trace-no-rec",
            patient_id=patient.id,
            decision_type="test",
            reason="No recommendation link",
            confidence="low",
        )
        db_session.add(decision)
        await db_session.flush()

        trace = ClinicalDecisionTraceModel(
            trace_id="no-rec-trace",
            clinical_decision_id=decision.id,
            step_order=1,
            step_type="test",
        )
        db_session.add(trace)
        await db_session.commit()
        await db_session.refresh(trace)

        assert trace.recommendation_id is None

    async def test_multiple_traces_ordered_by_step(self, db_session, patient):
        """Multiple traces for a decision should be retrievable in order."""
        from src.backend.domain.clinical_decision import (
            ClinicalDecisionModel,
            ClinicalDecisionTraceModel,
        )

        decision = ClinicalDecisionModel(
            decision_id="multi-trace",
            patient_id=patient.id,
            decision_type="test",
            reason="Multiple traces",
            confidence="high",
        )
        db_session.add(decision)
        await db_session.flush()

        traces = [
            ClinicalDecisionTraceModel(
                trace_id=f"multi-{i}", clinical_decision_id=decision.id,
                step_order=i, step_type=f"step_{i}",
            )
            for i in range(1, 4)
        ]
        db_session.add_all(traces)
        await db_session.commit()

        await db_session.refresh(decision)
        assert len(decision.traces) == 3
        orders = [t.step_order for t in decision.traces]
        assert orders == sorted(orders)  # should be in ascending order
