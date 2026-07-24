"""
Restart Recovery Test (Phase 3A Hardening — Batch E5).

Verifies that recommendation data survives a full database engine restart:
1. Create a real Engine + Session
2. Create required Patient record (satisfying FK constraints)
3. Persist a Recommendation + Trace + Steps via repositories
4. Record the recommendation_id
5. Dispose the first Engine
6. Create a *new* Engine + Session (no in-memory state carried over)
7. Retrieve the recommendation by ID
8. Confirm the full data chain (Recommendation → Trace → Steps) is intact

**Prohibited** (enforced by code structure):
- Shared module-level dicts
- Shared service / repository / session instances
- mock / monkeypatch restart
"""

from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.backend.database.models import Base
from src.backend.domain.patient import PatientModel
from src.backend.repositories.recommendation_repo import (
    RecommendationRepository,
    TraceRepository,
)
from src.backend.domain.recommendation import (
    RecommendationModel,
    RecommendationTraceModel,
    RecommendationTraceStepModel,
)

_DB_FILE = "test_e5_restart_recovery.db"


@pytest.fixture(autouse=True)
def _cleanup_db():
    """Remove the test DB file before and after each test."""
    if os.path.exists(_DB_FILE):
        os.remove(_DB_FILE)
    yield
    if os.path.exists(_DB_FILE):
        os.remove(_DB_FILE)


@pytest.fixture
async def db_engine():
    """Create a file-based SQLite engine with all tables."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{_DB_FILE}", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine


@pytest.fixture
async def db_session(db_engine):
    """Provide an async session bound to the file-based engine."""
    async_session = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False,
    )
    async with async_session() as session:
        yield session


async def _persist_chain_sync(session, patient, rec_id_hex=None, trace_id_hex=None):
    """Persist Recommendation + Trace + Steps, return ID dict."""
    rec_id = rec_id_hex or uuid.uuid4().hex
    trace_id = trace_id_hex or uuid.uuid4().hex

    # Recommendation
    rec = RecommendationModel(
        recommendation_id=rec_id,
        patient_id=patient.id,
        trace_id=trace_id,
        engine_version="1.0.0",
        status="completed",
        request_payload={"patient_id": str(patient.id), "variants": ["EGFR L858R"]},
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
        },
        report_html="<html>E5 Test Report</html>",
    )
    session.add(rec)
    # Flush to ensure rec.id is assigned
    await session.flush()

    # Trace
    trace = RecommendationTraceModel(
        trace_id=trace_id,
        recommendation_id=rec.id,
    )
    session.add(trace)
    # Flush to ensure trace.id is assigned
    await session.flush()

    # Steps
    steps_data = [
        (0, "evidence", {"variants": ["EGFR L858R"]}, {"count": 5}, 0.8, 0.75, None),
        (1, "score", {"top_n": 5}, {"ranked": 3}, 1.0, 0.92, 1),
        (2, "recommendation", {"aggregated": True}, {"final": True}, None, None, None),
    ]
    for order, stype, inp, out, w, s, r in steps_data:
        step = RecommendationTraceStepModel(
            trace_id=trace.id,
            step_order=order,
            step_type=stype,
            input_summary=inp,
            output_summary=out,
            weight=w,
            score=s,
            rank=r,
            status="completed",
        )
        session.add(step)

    return {
        "recommendation_id": rec_id,
        "trace_id": trace_id,
        "recommendation_uuid": str(rec.id),
        "trace_uuid": str(trace.id),
    }


class TestRestartRecovery:
    """E5: real restart with a new Engine + Session."""

    async def test_restart_recovery_data_intact(self, db_engine, _cleanup_db):
        """Full chain survives a complete engine restart."""
        # ── Phase 1: Write via first Engine+Session ──────────────────────
        async_session1 = async_sessionmaker(
            db_engine, class_=AsyncSession, expire_on_commit=False,
        )
        async with async_session1() as session:
            # Patient
            pid = uuid.uuid4()
            pat = PatientModel(id=pid, display_name="RESTART-PATIENT-1")
            session.add(pat)
            await session.commit()
            await session.refresh(pat)

            ids = await _persist_chain_sync(session, pat)
            await session.commit()

        # ── Phase 2: Dispose engine ──────────────────────────────────────
        await db_engine.dispose()

        # ── Phase 3: New engine (same file) — simulate restart ────────────
        engine2 = create_async_engine(f"sqlite+aiosqlite:///{_DB_FILE}", echo=False)
        async_session2 = async_sessionmaker(
            engine2, class_=AsyncSession, expire_on_commit=False,
        )

        async with async_session2() as session:
            # Read back
            rec_repo = RecommendationRepository(session)
            trace_repo = TraceRepository(session)

            rec = await rec_repo.get_by_id(ids["recommendation_id"])
            assert rec is not None, "Recommendation NOT FOUND after restart"
            assert rec.recommendation_id == ids["recommendation_id"]
            assert rec.engine_version == "1.0.0"
            assert rec.status == "completed"
            assert rec.report_html == "<html>E5 Test Report</html>"
            assert rec.result_payload is not None
            drugs = rec.result_payload.get("recommendations", [])
            assert len(drugs) == 1
            assert drugs[0]["drug_name"] == "Osimertinib"

            trace = await trace_repo.get_trace_by_trace_id(ids["trace_id"])
            assert trace is not None, "Trace NOT FOUND after restart"
            assert trace.trace_id == ids["trace_id"]

            steps = await trace_repo.get_steps_by_trace_id(ids["trace_uuid"])
            assert len(steps) == 3
            assert steps[0].step_order == 0
            assert steps[0].step_type == "evidence"
            assert steps[0].weight == 0.8
            assert steps[0].score == 0.75
            assert steps[1].step_order == 1
            assert steps[1].step_type == "score"
            assert steps[2].step_order == 2
            assert steps[2].step_type == "recommendation"

        await engine2.dispose()

    async def test_restart_recovery_trace_references(self, db_engine, _cleanup_db):
        """After restart, FK references between trace and recommendation hold."""
        async_session1 = async_sessionmaker(
            db_engine, class_=AsyncSession, expire_on_commit=False,
        )
        async with async_session1() as session:
            pid = uuid.uuid4()
            pat = PatientModel(id=pid, display_name="RESTART-PATIENT-2")
            session.add(pat)
            await session.commit()
            await session.refresh(pat)

            ids = await _persist_chain_sync(session, pat)
            await session.commit()

        await db_engine.dispose()

        # Restart
        engine2 = create_async_engine(f"sqlite+aiosqlite:///{_DB_FILE}", echo=False)
        async_session2 = async_sessionmaker(
            engine2, class_=AsyncSession, expire_on_commit=False,
        )
        async with async_session2() as session:
            trace_repo = TraceRepository(session)
            trace = await trace_repo.get_trace_by_trace_id(ids["trace_id"])
            assert trace is not None
            # Trace -> Recommendation FK
            assert trace.recommendation_id is not None
            assert str(trace.recommendation_id) == ids["recommendation_uuid"]

            # Steps -> Trace FK
            steps = await trace_repo.get_steps_by_trace_id(ids["trace_uuid"])
            assert len(steps) == 3
            for step in steps:
                assert str(step.trace_id) == ids["trace_uuid"]

        await engine2.dispose()

    async def test_restart_recovery_multiple_records(self, db_engine, _cleanup_db):
        """Multiple recommendations all survive restart."""
        async_session1 = async_sessionmaker(
            db_engine, class_=AsyncSession, expire_on_commit=False,
        )
        async with async_session1() as session:
            pid = uuid.uuid4()
            pat = PatientModel(id=pid, display_name="RESTART-PATIENT-3")
            session.add(pat)
            await session.commit()
            await session.refresh(pat)

            ids1 = await _persist_chain_sync(session, pat, rec_id_hex=uuid.uuid4().hex, trace_id_hex=uuid.uuid4().hex)
            ids2 = await _persist_chain_sync(session, pat, rec_id_hex=uuid.uuid4().hex, trace_id_hex=uuid.uuid4().hex)
            await session.commit()

        await db_engine.dispose()

        engine2 = create_async_engine(f"sqlite+aiosqlite:///{_DB_FILE}", echo=False)
        async_session2 = async_sessionmaker(
            engine2, class_=AsyncSession, expire_on_commit=False,
        )
        async with async_session2() as session:
            repo = RecommendationRepository(session)
            r1 = await repo.get_by_id(ids1["recommendation_id"])
            r2 = await repo.get_by_id(ids2["recommendation_id"])
            assert r1 is not None
            assert r2 is not None
            assert r1.recommendation_id != r2.recommendation_id

        await engine2.dispose()
