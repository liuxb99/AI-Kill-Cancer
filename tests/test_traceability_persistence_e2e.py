from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import select

from src.backend.config import settings
from src.backend.database import session as db_session
from src.backend.demo.bootstrap import _demo_uuid, bootstrap_demo_dataset
from src.backend.domain.cancer_case import CancerCaseModel
from src.backend.domain.clinical_decision import ClinicalDecisionModel, ClinicalDecisionTraceModel
from src.backend.domain.enums import EvidenceDirectionEnum, EvidenceLevelEnum, EvidenceTypeEnum
from src.backend.domain.evidence import EvidenceModel
from src.backend.domain.patient import PatientModel
from src.backend.domain.recommendation import (
    RecommendationModel,
    RecommendationTraceModel,
    RecommendationTraceStepModel,
)
from src.backend.domain.sequencing import SequencingTestModel
from src.backend.domain.specimen import SpecimenModel
from src.backend.domain.variant import VariantModel


@pytest.mark.asyncio
async def test_traceability_chain_survives_sqlite_restart(tmp_path, monkeypatch):
    database = tmp_path / "traceability.db"
    db_url = f"sqlite+aiosqlite:///{database.as_posix()}"

    monkeypatch.setattr(settings, "APP_MODE", "research")
    monkeypatch.setattr(settings, "DB_BACKEND", "sqlite")
    monkeypatch.setattr(settings, "DATABASE_URL", db_url)
    monkeypatch.setattr(settings, "SQLITE_PATH", str(database))
    monkeypatch.setattr(settings, "DEMO_AUTO_BOOTSTRAP", False)

    await db_session.init_db(db_url)
    assert db_session.async_session_factory is not None
    await bootstrap_demo_dataset(db_session.async_session_factory, "data/demo")

    patient_id = _demo_uuid("patient", "PTC-DEMO-001")
    case_id = _demo_uuid("case", "CASE-DEMO-001")
    specimen_id = _demo_uuid("specimen", "SPEC-DEMO-001")
    sequencing_id = _demo_uuid("sequencing", "SEQ-DEMO-001")
    variant_id = _demo_uuid("variant", "VAR-DEMO-001")

    async with db_session.async_session_factory() as session:
        evidence = EvidenceModel(
            evidence_type=EvidenceTypeEnum.PREDICTIVE,
            source_name="traceability-e2e",
            source_record_id="TRACE-EV-001",
            gene_symbol="BRAF",
            variant_id=variant_id,
            cancer_type="PTC",
            study_type="restart-persistence",
            evidence_direction=EvidenceDirectionEnum.SUPPORTING,
            evidence_level=EvidenceLevelEnum.LEVEL_2,
            quality="test",
            summary="Persistent evidence link for restart E2E",
            retrieved_at=datetime.utcnow(),
        )
        recommendation = RecommendationModel(
            recommendation_id="TRACE-REC-001",
            patient_id=patient_id,
            case_id=case_id,
            trace_id="TRACE-RUN-001",
            engine_version="e2e",
            status="completed",
            request_payload={"variant_id": str(variant_id)},
            result_payload={"evidence_source": "TRACE-EV-001"},
        )
        session.add_all([evidence, recommendation])
        await session.flush()

        rec_trace = RecommendationTraceModel(
            trace_id="TRACE-RUN-001",
            recommendation_id=recommendation.id,
        )
        session.add(rec_trace)
        await session.flush()
        session.add(
            RecommendationTraceStepModel(
                trace_id=rec_trace.id,
                step_order=1,
                step_type="evidence_link",
                input_summary={"case_id": str(case_id), "variant_id": str(variant_id)},
                output_summary={"recommendation_id": "TRACE-REC-001"},
                evidence_references=[str(evidence.id)],
                status="completed",
            )
        )

        decision = ClinicalDecisionModel(
            decision_id="TRACE-DEC-001",
            patient_id=patient_id,
            recommendation_id=recommendation.id,
            decision_type="research_review",
            reason="Restart persistence verification only",
            evidence_summary={"evidence_ids": [str(evidence.id)]},
            confidence="test-only",
            alternatives=[],
            contraindications=[],
            status="active",
        )
        session.add(decision)
        await session.flush()
        session.add(
            ClinicalDecisionTraceModel(
                trace_id="TRACE-DECISION-RUN-001",
                clinical_decision_id=decision.id,
                recommendation_id=recommendation.id,
                step_order=1,
                step_type="recommendation_link",
                input_summary={"recommendation_id": "TRACE-REC-001"},
                output_summary={"decision_id": "TRACE-DEC-001"},
            )
        )
        await session.commit()
        evidence_id = evidence.id
        recommendation_pk = recommendation.id
        decision_pk = decision.id

    await db_session.close_db()
    assert db_session.async_session_factory is None
    await db_session.init_db(db_url)
    assert db_session.async_session_factory is not None

    async with db_session.async_session_factory() as restarted:
        assert (await restarted.get(PatientModel, patient_id)) is not None
        case = await restarted.get(CancerCaseModel, case_id)
        specimen = await restarted.get(SpecimenModel, specimen_id)
        sequencing = await restarted.get(SequencingTestModel, sequencing_id)
        variant = await restarted.get(VariantModel, variant_id)
        evidence = await restarted.get(EvidenceModel, evidence_id)
        recommendation = await restarted.get(RecommendationModel, recommendation_pk)
        decision = await restarted.get(ClinicalDecisionModel, decision_pk)

        assert case is not None and case.patient_id == patient_id
        assert specimen is not None and specimen.case_id == case_id
        assert sequencing is not None and sequencing.specimen_id == specimen_id
        assert variant is not None and variant.sequencing_test_id == sequencing_id
        assert evidence is not None and evidence.variant_id == variant_id
        assert recommendation is not None and recommendation.case_id == case_id
        assert decision is not None and decision.recommendation_id == recommendation_pk

        rec_step = (
            await restarted.execute(
                select(RecommendationTraceStepModel).where(
                    RecommendationTraceStepModel.trace_id
                    == select(RecommendationTraceModel.id)
                    .where(RecommendationTraceModel.recommendation_id == recommendation_pk)
                    .scalar_subquery()
                )
            )
        ).scalar_one()
        assert rec_step.evidence_references == [str(evidence_id)]

        decision_trace = (
            await restarted.execute(
                select(ClinicalDecisionTraceModel).where(
                    ClinicalDecisionTraceModel.clinical_decision_id == decision_pk
                )
            )
        ).scalar_one()
        assert decision_trace.recommendation_id == recommendation_pk
        assert decision.evidence_summary == {"evidence_ids": [str(evidence_id)]}

    await db_session.close_db()
