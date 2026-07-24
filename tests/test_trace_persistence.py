"""
Trace Persistence Test (Phase 3A Hardening — Batch E6).

Verifies that the full calculation chain stored in the database can be
faithfully restored:

- Recommendation → Trace → Steps
- Step-level: Evidence → Weight → Score → Rank → Explanation
- Step ordering is preserved
- All scalar values (float, int, JSON) survive round-trip
"""

from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.backend.database.models import Base
from src.backend.domain.patient import PatientModel
from src.backend.domain.recommendation import (
    RecommendationModel,
    RecommendationTraceModel,
    RecommendationTraceStepModel,
)
from src.backend.repositories.recommendation_repo import (
    RecommendationRepository,
    TraceRepository,
)

_DB_FILE = "test_e6_trace_persistence.db"


@pytest.fixture(autouse=True)
def _cleanup_db():
    if os.path.exists(_DB_FILE):
        os.remove(_DB_FILE)
    yield
    if os.path.exists(_DB_FILE):
        os.remove(_DB_FILE)


@pytest.fixture
async def db_engine():
    engine = create_async_engine(f"sqlite+aiosqlite:///{_DB_FILE}", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine


@pytest.fixture
async def db_session(db_engine):
    async_session = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False,
    )
    async with async_session() as session:
        yield session


async def _build_full_chain(session, patient):
    """Create a realistic recommendation with complete trace steps."""
    rec_id = uuid.uuid4().hex
    trace_id = uuid.uuid4().hex

    # ── Recommendation ────────────────────────────────────────────────────
    rec = RecommendationModel(
        recommendation_id=rec_id,
        patient_id=patient.id,
        trace_id=trace_id,
        engine_version="1.0.0",
        status="completed",
        request_payload={
            "patient_id": str(patient.id),
            "variants": ["BRAF V600E", "EGFR L858R"],
            "patient_context": {"age": 58, "cancer_type": "Melanoma"},
            "top_n": 3,
        },
        result_payload={
            "recommendations": [
                {
                    "drug_name": "Vemurafenib",
                    "rank": 1,
                    "overall_score": 0.92,
                    "evidence_score": 0.88,
                    "sensitivity_score": 0.85,
                    "resistance_score": 0.12,
                    "conflict_score": 0.03,
                    "explanations": [
                        {
                            "category": "efficacy",
                            "detail": "BRAF V600E is a strong driver mutation",
                            "source": "NCCN Guidelines",
                            "score_impact": 0.45,
                        },
                    ],
                },
                {
                    "drug_name": "Dabrafenib + Trametinib",
                    "rank": 2,
                    "overall_score": 0.87,
                    "evidence_score": 0.82,
                    "sensitivity_score": 0.80,
                    "resistance_score": 0.08,
                    "conflict_score": 0.02,
                    "explanations": [
                        {
                            "category": "synergy",
                            "detail": "Dual MAPK pathway inhibition improves outcomes",
                            "source": "COMBI-d trial",
                            "score_impact": 0.38,
                        },
                    ],
                },
            ],
        },
        report_html="<h1>E6 Report</h1><p>BRAF V600E analysis</p>",
    )
    session.add(rec)
    await session.flush()  # ensure rec.id is assigned before creating trace

    # ── Trace ─────────────────────────────────────────────────────────────
    trace = RecommendationTraceModel(
        trace_id=trace_id,
        recommendation_id=rec.id,
    )
    session.add(trace)
    await session.flush()  # ensure trace.id is assigned before creating steps

    # ── Steps with full Evidence → Weight → Score → Rank chain ────────────
    steps_data = [
        # Step 0: Evidence collection
        RecommendationTraceStepModel(
            trace_id=trace.id,
            step_order=0,
            step_type="evidence",
            input_summary={
                "variants": ["BRAF V600E", "EGFR L858R"],
                "patient_context": {"age": 58, "cancer_type": "Melanoma"},
            },
            output_summary={
                "evidence_found": 15,
                "sources": ["FDA", "NCCN", "COSMIC", "cBioPortal"],
                "matched_variants": ["BRAF V600E"],
            },
            weight=0.8,
            score=0.75,
            rank=None,
            status="completed",
        ),
        # Step 1: Weight assignment
        RecommendationTraceStepModel(
            trace_id=trace.id,
            step_order=1,
            step_type="weight",
            input_summary={"evidence_id": "ev-001", "evidence_level": "Level_2"},
            output_summary={
                "assigned_weight": 0.85,
                "weight_components": {
                    "evidence_level": 0.6,
                    "trial_quality": 0.15,
                    "consistency": 0.1,
                },
            },
            weight=0.85,
            score=None,
            rank=None,
            status="completed",
        ),
        # Step 2: Scoring
        RecommendationTraceStepModel(
            trace_id=trace.id,
            step_order=2,
            step_type="score",
            input_summary={
                "drug_candidates": ["Vemurafenib", "Dabrafenib + Trametinib", "Imatinib"],
            },
            output_summary={
                "scores": {
                    "Vemurafenib": {"overall": 0.92, "evidence": 0.88, "sensitivity": 0.85, "resistance": 0.12},
                    "Dabrafenib + Trametinib": {"overall": 0.87, "evidence": 0.82, "sensitivity": 0.80, "resistance": 0.08},
                    "Imatinib": {"overall": 0.15, "evidence": 0.10, "sensitivity": 0.20, "resistance": 0.60},
                },
            },
            weight=1.0,
            score=0.92,
            rank=None,
            status="completed",
        ),
        # Step 3: Ranking
        RecommendationTraceStepModel(
            trace_id=trace.id,
            step_order=3,
            step_type="ranking",
            input_summary={"top_n": 3, "scored_drugs": 3},
            output_summary={
                "ranked_drugs": [
                    {"drug_name": "Vemurafenib", "rank": 1, "overall_score": 0.92},
                    {"drug_name": "Dabrafenib + Trametinib", "rank": 2, "overall_score": 0.87},
                    {"drug_name": "Imatinib", "rank": 3, "overall_score": 0.15},
                ],
            },
            weight=None,
            score=None,
            rank=1,
            status="completed",
        ),
        # Step 4: Explanation generation
        RecommendationTraceStepModel(
            trace_id=trace.id,
            step_order=4,
            step_type="explanation",
            input_summary={"ranked_list": True},
            output_summary={
                "explanations": [
                    {
                        "drug": "Vemurafenib",
                        "reasons": [
                            "BRAF V600E is a validated drug target",
                            "FDA-approved for BRAF-mutant melanoma",
                            "High evidence confidence (Level_2)",
                        ],
                    },
                ],
            },
            weight=None,
            score=0.95,
            rank=None,
            status="completed",
        ),
    ]
    for step in steps_data:
        session.add(step)

    return {
        "recommendation_id": rec_id,
        "trace_id": trace_id,
        "recommendation_uuid": str(rec.id),
        "trace_uuid": str(trace.id),
    }


class TestTracePersistence:
    """E6: Full calculation chain restoration from database."""

    async def test_evidence_weight_score_rank_chain(self, db_session):
        """Evidence → Weight → Score → Rank → Explanation restores correctly."""
        pid = uuid.uuid4()
        pat = PatientModel(id=pid, display_name="E6-PATIENT")
        db_session.add(pat)
        await db_session.commit()
        await db_session.refresh(pat)

        ids = await _build_full_chain(db_session, pat)
        await db_session.commit()

        # Read back
        trace_repo = TraceRepository(db_session)
        rec_repo = RecommendationRepository(db_session)

        rec = await rec_repo.get_by_id(ids["recommendation_id"])
        assert rec is not None
        assert rec.status == "completed"
        assert rec.engine_version == "1.0.0"

        # Verify result_payload contains full explanation chain
        payload = rec.result_payload
        assert payload is not None
        drugs = payload["recommendations"]
        assert len(drugs) == 2
        assert drugs[0]["drug_name"] == "Vemurafenib"
        assert drugs[0]["rank"] == 1
        assert drugs[0]["overall_score"] == 0.92
        assert len(drugs[0]["explanations"]) == 1
        assert drugs[0]["explanations"][0]["category"] == "efficacy"
        assert drugs[0]["explanations"][0]["score_impact"] == 0.45

        # Verify weight in second drug
        assert drugs[1]["drug_name"] == "Dabrafenib + Trametinib"
        assert drugs[1]["rank"] == 2

        # Trace
        trace = await trace_repo.get_trace_by_trace_id(ids["trace_id"])
        assert trace is not None
        assert trace.recommendation_id is not None

    async def test_step_order_preserved(self, db_session):
        """Steps are stored and retrieved in the correct order."""
        pid = uuid.uuid4()
        pat = PatientModel(id=pid, display_name="E6-ORDER")
        db_session.add(pat)
        await db_session.commit()
        await db_session.refresh(pat)

        ids = await _build_full_chain(db_session, pat)
        await db_session.commit()

        trace_repo = TraceRepository(db_session)
        steps = await trace_repo.get_steps_by_trace_id(ids["trace_uuid"])

        assert len(steps) == 5
        # Verify correct type sequence
        expected_types = ["evidence", "weight", "score", "ranking", "explanation"]
        for i, step in enumerate(steps):
            assert step.step_order == i, f"Step {i} has wrong order: {step.step_order}"
            assert step.step_type == expected_types[i], (
                f"Step {i} expected {expected_types[i]!r}, got {step.step_type!r}"
            )

    async def test_numeric_values_survive_round_trip(self, db_session):
        """Float, int, and None values are preserved exactly."""
        pid = uuid.uuid4()
        pat = PatientModel(id=pid, display_name="E6-NUMERIC")
        db_session.add(pat)
        await db_session.commit()
        await db_session.refresh(pat)

        ids = await _build_full_chain(db_session, pat)
        await db_session.commit()

        trace_repo = TraceRepository(db_session)
        steps = await trace_repo.get_steps_by_trace_id(ids["trace_uuid"])

        # Step 0: evidence
        s0 = steps[0]
        assert s0.weight == 0.8
        assert s0.score == 0.75
        assert s0.rank is None

        # Step 1: weight
        s1 = steps[1]
        assert s1.weight == 0.85
        assert s1.score is None
        assert s1.rank is None

        # Step 2: score
        s2 = steps[2]
        assert s2.weight == 1.0
        assert s2.score == 0.92
        assert s2.rank is None

        # Step 3: ranking
        s3 = steps[3]
        assert s3.weight is None
        assert s3.score is None
        assert s3.rank == 1

        # Step 4: explanation
        s4 = steps[4]
        assert s4.weight is None
        assert s4.score == 0.95
        assert s4.rank is None

    async def test_json_fields_round_trip(self, db_session):
        """JSON fields (input_summary, output_summary, evidence_references) survive."""
        pid = uuid.uuid4()
        pat = PatientModel(id=pid, display_name="E6-JSON")
        db_session.add(pat)
        await db_session.commit()
        await db_session.refresh(pat)

        ids = await _build_full_chain(db_session, pat)
        await db_session.commit()

        trace_repo = TraceRepository(db_session)
        steps = await trace_repo.get_steps_by_trace_id(ids["trace_uuid"])

        # Step 0: evidence has rich input/output
        s0 = steps[0]
        assert s0.input_summary is not None
        assert "variants" in s0.input_summary
        assert s0.input_summary["variants"] == ["BRAF V600E", "EGFR L858R"]
        assert s0.output_summary["evidence_found"] == 15
        assert "FDA" in s0.output_summary["sources"]

        # Step 1: weight components
        s1 = steps[1]
        assert s1.output_summary["weight_components"]["evidence_level"] == 0.6

        # Step 2: drug scores
        s2 = steps[2]
        assert s2.input_summary["drug_candidates"] == [
            "Vemurafenib", "Dabrafenib + Trametinib", "Imatinib",
        ]
        assert s2.output_summary["scores"]["Vemurafenib"]["overall"] == 0.92

        # Step 3: ranking
        s3 = steps[3]
        assert s3.output_summary["ranked_drugs"][0]["rank"] == 1

        # Step 4: explanations
        s4 = steps[4]
        assert "explanations" in s4.output_summary
        assert "BRAF V600E is a validated drug target" in s4.output_summary["explanations"][0]["reasons"]

    async def test_full_chain_from_database(self, db_session, _cleanup_db):
        """End-to-end: write full chain, dispose engine, read back from new engine."""
        pid = uuid.uuid4()
        pat = PatientModel(id=pid, display_name="E6-FULL")
        db_session.add(pat)
        await db_session.commit()
        await db_session.refresh(pat)

        ids = await _build_full_chain(db_session, pat)
        await db_session.commit()

        # Dispose current session — use new engine
        await db_session.close()

        engine2 = create_async_engine(f"sqlite+aiosqlite:///{_DB_FILE}", echo=False)
        async_session2 = async_sessionmaker(
            engine2, class_=AsyncSession, expire_on_commit=False,
        )
        async with async_session2() as session:
            rec_repo = RecommendationRepository(session)
            trace_repo = TraceRepository(session)

            rec = await rec_repo.get_by_id(ids["recommendation_id"])
            assert rec is not None
            assert rec.status == "completed"
            assert rec.request_payload["patient_context"]["cancer_type"] == "Melanoma"

            trace = await trace_repo.get_trace_by_trace_id(ids["trace_id"])
            assert trace is not None

            steps = await trace_repo.get_steps_by_trace_id(ids["trace_uuid"])
            assert len(steps) == 5

            # Verify the Explanation step
            last_step = steps[-1]
            assert last_step.step_type == "explanation"
            assert last_step.step_order == 4
            assert last_step.score == 0.95
            assert "BRAF V600E" in str(last_step.output_summary)

        await engine2.dispose()
