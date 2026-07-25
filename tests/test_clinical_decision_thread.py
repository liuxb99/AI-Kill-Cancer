"""
Digital Thread tests for Evidence → Recommendation → Clinical Decision (Phase 3B — Batch H Part 2).

Covers:
- Evidence → Recommendation → Clinical Decision full traceability
- Clinical Decision Trace can be traced back to the Recommendation
- Recommendation Trace can be traced back to the Evidence
- trace_id associations are correct across models
"""

from __future__ import annotations

import uuid
from datetime import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.backend.database.models import Base
from src.backend.domain.clinical_decision import (
    ClinicalDecisionModel,
    ClinicalDecisionTraceModel,
)
from src.backend.domain.evidence import EvidenceModel
from src.backend.domain.patient import PatientModel
from src.backend.domain.recommendation import (
    RecommendationModel,
    RecommendationTraceModel,
    RecommendationTraceStepModel,
)
from src.backend.domain.enums import (
    EvidenceDirectionEnum,
    EvidenceLevelEnum,
    EvidenceTypeEnum,
)
from src.backend.domain.enums import ConsentStatusEnum, SexEnum

# ─── Fixtures ─────────────────────────────────────────────────────────────


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
        display_name="THREAD-TEST-PATIENT",
        sex=SexEnum.F,
        consent_status=ConsentStatusEnum.GRANTED,
    )
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p


@pytest.fixture
async def evidence(db_session, patient):
    """Create an Evidence record that the recommendation will reference."""
    ev = EvidenceModel(
        evidence_type=EvidenceTypeEnum.PREDICTIVE,
        source_name="CIViC",
        source_record_id="CIViC-12345",
        gene_symbol="EGFR",
        cancer_type="NSCLC",
        evidence_direction=EvidenceDirectionEnum.SUPPORTING,
        evidence_level=EvidenceLevelEnum.LEVEL_1,
        summary="Osimertinib is effective for EGFR L858R mutated NSCLC.",
        retrieved_at=datetime.utcnow(),
    )
    db_session.add(ev)
    await db_session.commit()
    await db_session.refresh(ev)
    return ev


@pytest.fixture
async def recommendation_with_trace(db_session, patient, evidence):
    """Create a RecommendationModel + RecommendationTraceModel + Step.

    The recommendation's result_payload references the evidence,
    and the trace step records evidence_references for auditability.
    """
    rec = RecommendationModel(
        recommendation_id="rec-digital-thread-001",
        patient_id=patient.id,
        engine_version="1.0.0",
        status="completed",
        trace_id="trace-rec-digital-001",
        request_payload={"variants": ["EGFR L858R"]},
        result_payload={
            "recommendations": [
                {
                    "drug_name": "Osimertinib",
                    "rank": 1,
                    "overall_score": 0.95,
                    "evidence_score": 0.90,
                    "sensitivity_score": 0.85,
                    "resistance_score": 0.10,
                    "conflict_score": 0.05,
                },
            ],
            "evidence": [
                {
                    "drug_name": "Osimertinib",
                    "evidence_level": "Tier_1",
                    "evidence_direction": "supporting",
                    "source": "CIViC",
                    "source_record_id": "CIViC-12345",
                },
            ],
        },
    )
    db_session.add(rec)
    await db_session.flush()  # get rec.id assigned

    # Recommendation Trace
    rec_trace = RecommendationTraceModel(
        trace_id="trace-rec-digital-001",
        recommendation_id=rec.id,
    )
    db_session.add(rec_trace)
    await db_session.flush()  # get rec_trace.id assigned

    # Trace Step that explicitly references the evidence
    step = RecommendationTraceStepModel(
        trace_id=rec_trace.id,
        step_order=0,
        step_type="evidence_collection",
        input_summary={"variants": ["EGFR L858R"]},
        output_summary={
            "evidence_count": 1,
            "sources": ["CIViC"],
        },
        evidence_references=[str(evidence.id)],
        status="completed",
    )
    db_session.add(step)

    await db_session.commit()
    await db_session.refresh(rec)
    return rec


@pytest.fixture
async def clinical_decision_with_trace(
    db_session,
    patient,
    recommendation_with_trace,
):
    """Create a ClinicalDecisionModel + ClinicalDecisionTraceModel.

    The trace records the recommendation_id to preserve the digital thread.
    """
    rec = recommendation_with_trace

    dec = ClinicalDecisionModel(
        decision_id="dec-digital-thread-001",
        patient_id=patient.id,
        recommendation_id=rec.id,
        decision_type="approved",
        reason=(
            "Osimertinib is approved for NSCLC with EGFR L858R "
            "based on Tier 1 evidence from CIViC."
        ),
        evidence_summary={
            "total_evidence_count": 1,
            "best_evidence_tier": "Tier_1",
            "sources": ["CIViC"],
            "direction_breakdown": {
                "supporting": 1,
                "resistance": 0,
                "conflicting": 0,
                "neutral": 0,
            },
        },
        confidence="high",
        alternatives=[
            {
                "drug_name": "Afatinib",
                "rank": 2,
                "overall_score": 0.85,
                "rationale": "Alternative EGFR-TKI",
            },
        ],
        contraindications=[
            {
                "drug": "Osimertinib",
                "type": "resistance",
                "detail": "T790M mutation",
                "severity": "moderate",
            },
        ],
        status="active",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(dec)
    await db_session.flush()  # get dec.id assigned

    # Clinical Decision Trace — links back to the recommendation
    dec_trace = ClinicalDecisionTraceModel(
        trace_id="trace-dec-digital-001",
        clinical_decision_id=dec.id,
        recommendation_id=rec.id,
        step_order=0,
        step_type="clinical_decision_evaluate",
        input_summary={
            "patient_id": str(patient.id),
            "recommendation_id": rec.recommendation_id,
            "variants": [{"gene_symbol": "EGFR", "protein_change": "L858R"}],
            "evidence_count": 1,
        },
        output_summary={
            "decision_type": "approved",
            "confidence": "high",
        },
        created_at=datetime.utcnow(),
    )
    db_session.add(dec_trace)

    await db_session.commit()
    await db_session.refresh(dec)
    return dec


# ─── Tests: Digital Thread ────────────────────────────────────────────────


class TestEvidenceToRecommendationToDecision:
    """Evidence → Recommendation → Clinical Decision full traceability."""

    async def test_clinical_decision_trace_points_to_recommendation(
        self,
        db_session,
        clinical_decision_with_trace,
        recommendation_with_trace,
    ):
        """The ClinicalDecisionTraceModel.recommendation_id must reference
        the original RecommendationModel."""
        dec = clinical_decision_with_trace
        rec = recommendation_with_trace

        # Load the clinical decision trace from DB
        stmt = select(ClinicalDecisionTraceModel).where(
            ClinicalDecisionTraceModel.clinical_decision_id == dec.id,
        )
        result = await db_session.execute(stmt)
        dec_traces = result.scalars().all()

        assert len(dec_traces) >= 1
        dec_trace = dec_traces[0]

        # The trace's recommendation_id must point back to the recommendation
        assert dec_trace.recommendation_id == rec.id
        assert dec_trace.step_type == "clinical_decision_evaluate"

        # Verify the recommendation is reachable via the trace
        rec_from_trace = await db_session.get(
            RecommendationModel,
            dec_trace.recommendation_id,
        )
        assert rec_from_trace is not None
        assert rec_from_trace.recommendation_id == rec.recommendation_id
        assert rec_from_trace.trace_id == "trace-rec-digital-001"

    async def test_recommendation_trace_points_to_evidence(
        self,
        db_session,
        recommendation_with_trace,
        evidence,
    ):
        """The RecommendationTraceStepModel.evidence_references must
        contain the EvidenceModel ID."""
        rec = recommendation_with_trace

        # Load the recommendation trace and its steps
        trace_stmt = select(RecommendationTraceModel).where(
            RecommendationTraceModel.recommendation_id == rec.id,
        )
        trace_result = await db_session.execute(trace_stmt)
        rec_trace = trace_result.scalar_one_or_none()
        assert rec_trace is not None
        assert rec_trace.trace_id == "trace-rec-digital-001"

        # Load steps
        step_stmt = select(RecommendationTraceStepModel).where(
            RecommendationTraceStepModel.trace_id == rec_trace.id,
        )
        step_result = await db_session.execute(step_stmt)
        steps = step_result.scalars().all()

        assert len(steps) >= 1
        step = steps[0]

        # The step must reference the evidence
        assert step.evidence_references is not None
        evidence_ids = [
            uuid.UUID(ref) if isinstance(ref, str) else ref
            for ref in step.evidence_references
        ]
        assert evidence.id in evidence_ids

        # Verify the evidence is reachable
        ev_from_ref = await db_session.get(EvidenceModel, evidence.id)
        assert ev_from_ref is not None
        assert ev_from_ref.gene_symbol == "EGFR"
        assert ev_from_ref.source_name == "CIViC"

    async def test_recommendation_result_payload_contains_evidence_data(
        self,
        db_session,
        recommendation_with_trace,
        evidence,
    ):
        """The recommendation's result_payload should contain evidence
        that matches the linked EvidenceModel."""
        rec = recommendation_with_trace

        payload = rec.result_payload or {}
        ev_list = payload.get("evidence", [])
        assert len(ev_list) >= 1

        ev_item = ev_list[0]
        assert ev_item["source"] == "CIViC"
        assert ev_item["source_record_id"] == "CIViC-12345"
        assert ev_item["evidence_level"] == "Tier_1"
        # This matches the evidence fixture's source_record_id
        assert ev_item["source_record_id"] == evidence.source_record_id

    async def test_full_traceability_chain(
        self,
        db_session,
        clinical_decision_with_trace,
        recommendation_with_trace,
        evidence,
        patient,
    ):
        """End-to-end verification: Clinical Decision → Recommendation → Evidence.

        Walk the chain:
        1. Start from ClinicalDecisionModel
        2. Follow recommendation_id FK → RecommendationModel
        3. From RecommendationModel follow traces → RecommendationTraceModel
        4. From trace steps follow evidence_references → EvidenceModel
        """
        dec = clinical_decision_with_trace

        # ── Step 1: ClinicalDecisionModel → recommendation_id ────────────
        dec_from_db = await db_session.get(ClinicalDecisionModel, dec.id)
        assert dec_from_db is not None
        assert dec_from_db.recommendation_id is not None

        # ── Step 2: Follow FK → RecommendationModel ──────────────────────
        rec_from_db = await db_session.get(
            RecommendationModel,
            dec_from_db.recommendation_id,
        )
        assert rec_from_db is not None
        assert rec_from_db.recommendation_id == "rec-digital-thread-001"
        assert rec_from_db.patient_id == patient.id

        # ── Step 3: RecommendationModel → trace → TraceModel ─────────────
        # Via the relationship 'traces'
        # Explicitly refresh to avoid MissingGreenlet in async context
        await db_session.refresh(rec_from_db, ['traces'])
        rec_traces = rec_from_db.traces
        assert len(rec_traces) >= 1
        rec_trace = rec_traces[0]
        assert rec_trace.trace_id == "trace-rec-digital-001"
        assert rec_trace.recommendation_id == rec_from_db.id

        # ── Step 4: Trace steps → evidence_references → EvidenceModel ────
        # Explicitly refresh to avoid MissingGreenlet in async context
        await db_session.refresh(rec_trace, ['steps'])
        rec_steps = rec_trace.steps
        assert len(rec_steps) >= 1
        step = rec_steps[0]

        assert step.evidence_references is not None
        evidence_ids = [
            uuid.UUID(ref) if isinstance(ref, str) else ref
            for ref in step.evidence_references
        ]

        # Verify the evidence exists and matches
        ev_from_chain = await db_session.get(EvidenceModel, evidence.id)
        assert ev_from_chain is not None
        assert ev_from_chain.id in evidence_ids
        assert ev_from_chain.gene_symbol == "EGFR"
        assert ev_from_chain.cancer_type == "NSCLC"

        # ── Step 5: Verify ClinicalDecisionTrace also links to Recommendation ──
        dec_trace_stmt = select(ClinicalDecisionTraceModel).where(
            ClinicalDecisionTraceModel.clinical_decision_id == dec.id,
        )
        dec_trace_result = await db_session.execute(dec_trace_stmt)
        dec_traces = dec_trace_result.scalars().all()
        assert len(dec_traces) >= 1
        dec_trace = dec_traces[0]

        # The clinical decision trace must reference the recommendation
        assert dec_trace.recommendation_id == rec_from_db.id
        assert dec_trace.step_type == "clinical_decision_evaluate"

    async def test_trace_id_associations(
        self,
        db_session,
        clinical_decision_with_trace,
        recommendation_with_trace,
    ):
        """Verify trace_id values are correctly associated across models."""
        dec = clinical_decision_with_trace
        rec = recommendation_with_trace

        # RecommendationModel.trace_id should match its trace
        assert rec.trace_id == "trace-rec-digital-001"

        # ClinicalDecisionTraceModel.trace_id should be unique and set
        dec_trace_stmt = select(ClinicalDecisionTraceModel).where(
            ClinicalDecisionTraceModel.clinical_decision_id == dec.id,
        )
        dec_trace_result = await db_session.execute(dec_trace_stmt)
        dec_trace = dec_trace_result.scalar_one()
        assert dec_trace.trace_id == "trace-dec-digital-001"
        assert dec_trace.trace_id != rec.trace_id  # Different traces

        # Both traces should reference the same recommendation
        assert dec_trace.recommendation_id == rec.id

    async def test_multiple_decisions_from_one_recommendation(
        self,
        db_session,
        patient,
        recommendation_with_trace,
    ):
        """Multiple clinical decisions can be created from one recommendation,
        and all should trace back correctly."""
        rec = recommendation_with_trace

        # Create two clinical decisions from the same recommendation
        for i in range(2):
            dec = ClinicalDecisionModel(
                decision_id=f"dec-multi-{i:03d}",
                patient_id=patient.id,
                recommendation_id=rec.id,
                decision_type="approved",
                reason="Approved based on evidence.",
                evidence_summary={},
                confidence="high",
                status="active",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db_session.add(dec)
            await db_session.flush()

            dec_trace = ClinicalDecisionTraceModel(
                trace_id=f"trace-dec-multi-{i:03d}",
                clinical_decision_id=dec.id,
                recommendation_id=rec.id,
                step_order=0,
                step_type="clinical_decision_evaluate",
                input_summary={},
                output_summary={},
                created_at=datetime.utcnow(),
            )
            db_session.add(dec_trace)

        await db_session.commit()

        # Verify all decisions trace back to the same recommendation
        stmt_dec = select(ClinicalDecisionModel).where(
            ClinicalDecisionModel.recommendation_id == rec.id,
        )
        dec_result = await db_session.execute(stmt_dec)
        decisions = dec_result.scalars().all()
        assert len(decisions) >= 2

        for d in decisions:
            assert d.recommendation_id == rec.id

        # Verify all traces point back
        stmt_trace = select(ClinicalDecisionTraceModel).where(
            ClinicalDecisionTraceModel.recommendation_id == rec.id,
        )
        trace_result = await db_session.execute(stmt_trace)
        traces = trace_result.scalars().all()
        assert len(traces) >= 2

        for t in traces:
            assert t.recommendation_id == rec.id
