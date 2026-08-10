from datetime import datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

import src.backend.database.session as session_module
from src.backend.config import settings
from src.backend.domain.enums import (
    EvidenceDirectionEnum,
    EvidenceLevelEnum,
    EvidenceTypeEnum,
)
from src.backend.domain.evidence import EvidenceModel
from src.backend.domain.ptc_research import (
    PTCOutcomeModel,
    PTCResearchCaseModel,
    PTCVariantModel,
)
from src.backend.domain.research_depth import (
    ResearchEventModel,
    ResearchHypothesisModel,
    ResearchRunModel,
)
from src.backend.research_depth.orchestrator import execute_research_loop


def _research_case(case_id: str, *, braf: bool, outcome: str) -> PTCResearchCaseModel:
    case = PTCResearchCaseModel(
        case_id=case_id,
        source_dataset="DEPTH-TEST",
        source_project="DEPTH-TEST",
        disease="papillary_thyroid_carcinoma",
        pathologic_stage="Stage III",
    )
    if braf:
        case.variants.append(
            PTCVariantModel(
                variant_id=f"{case_id}-BRAF-V600E",
                case_id=case_id,
                source_dataset="DEPTH-TEST",
                gene="BRAF",
                protein_change="p.V600E",
                classification="missense_variant",
            )
        )
    case.outcomes.append(
        PTCOutcomeModel(
            outcome_id=f"{case_id}-RECURRENCE",
            case_id=case_id,
            source_dataset="DEPTH-TEST",
            outcome_type="recurrence",
            outcome_value=outcome,
            observed_at=datetime.utcnow(),
        )
    )
    return case


async def _load_inputs(factory):
    async with factory() as db:
        cases = list(
            (
                await db.execute(
                    select(PTCResearchCaseModel)
                    .options(
                        selectinload(PTCResearchCaseModel.variants),
                        selectinload(PTCResearchCaseModel.outcomes),
                    )
                    .where(PTCResearchCaseModel.source_dataset == "DEPTH-TEST")
                    .order_by(PTCResearchCaseModel.case_id)
                )
            ).scalars().unique()
        )
        evidence = list(
            (
                await db.execute(
                    select(EvidenceModel)
                    .where(EvidenceModel.gene_symbol == "BRAF")
                    .order_by(EvidenceModel.source_record_id)
                )
            ).scalars()
        )
        return cases, evidence


@pytest.mark.asyncio
async def test_research_loop_persists_reuses_and_survives_restart(tmp_path, monkeypatch):
    db_path = tmp_path / "research-depth.db"
    db_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    monkeypatch.setattr(settings, "APP_MODE", "research")
    monkeypatch.setattr(settings, "DEMO_AUTO_BOOTSTRAP", False)

    await session_module.init_db(db_url)
    factory = session_module.async_session_factory
    assert factory is not None

    async with factory() as db:
        db.add_all(
            [
                _research_case("DEPTH-A", braf=True, outcome="recurrence"),
                _research_case("DEPTH-B", braf=True, outcome="recurrence"),
                _research_case("DEPTH-C", braf=False, outcome="no recurrence"),
                _research_case("DEPTH-D", braf=False, outcome="no recurrence"),
                EvidenceModel(
                    evidence_type=EvidenceTypeEnum.PREDICTIVE,
                    source_name="DepthSourceA",
                    source_record_id="DEPTH-SUPPORT",
                    gene_symbol="BRAF",
                    cancer_type="PTC",
                    evidence_direction=EvidenceDirectionEnum.SUPPORTING,
                    evidence_level=EvidenceLevelEnum.LEVEL_2,
                    summary="Research supporting evidence",
                    retrieved_at=datetime.utcnow(),
                ),
                EvidenceModel(
                    evidence_type=EvidenceTypeEnum.PREDICTIVE,
                    source_name="DepthSourceB",
                    source_record_id="DEPTH-CONFLICT",
                    gene_symbol="BRAF",
                    cancer_type="PTC",
                    evidence_direction=EvidenceDirectionEnum.CONFLICTING,
                    evidence_level=EvidenceLevelEnum.LEVEL_2,
                    summary="Research counter-evidence",
                    retrieved_at=datetime.utcnow(),
                ),
            ]
        )
        await db.commit()

    cases, evidence = await _load_inputs(factory)
    async with factory() as db:
        first = await execute_research_loop(
            db,
            gene="BRAF",
            protein_change="p.V600E",
            cases=cases,
            evidence=evidence,
        )
        await db.commit()
    assert first["reused"] is False
    assert first["research_only"] is True
    assert first["clinical_use"] is False
    assert len(first["hypotheses"]) >= 2
    assert all(item["falsification_criteria"] for item in first["hypotheses"])

    cases, evidence = await _load_inputs(factory)
    async with factory() as db:
        second = await execute_research_loop(
            db,
            gene="BRAF",
            protein_change="p.V600E",
            cases=cases,
            evidence=evidence,
        )
        await db.commit()
    assert second["reused"] is True
    assert second["run_id"] == first["run_id"]
    assert second["input_fingerprint"] == first["input_fingerprint"]

    await session_module.close_db()
    await session_module.init_db(db_url)
    restarted = session_module.async_session_factory
    assert restarted is not None

    async with restarted() as db:
        run_count = (
            await db.execute(select(func.count()).select_from(ResearchRunModel))
        ).scalar_one()
        hypothesis_count = (
            await db.execute(select(func.count()).select_from(ResearchHypothesisModel))
        ).scalar_one()
        event_count = (
            await db.execute(select(func.count()).select_from(ResearchEventModel))
        ).scalar_one()
        events = list(
            (
                await db.execute(
                    select(ResearchEventModel).order_by(ResearchEventModel.event_type)
                )
            ).scalars()
        )

    assert run_count == 1
    assert hypothesis_count >= 2
    assert event_count >= 4
    assert {item.event_type for item in events} >= {
        "cohort_stratified",
        "evidence_conflict_assessed",
        "hypothesis_generated",
    }
    assert all(item.provenance.get("input_fingerprint") for item in events)

    await session_module.close_db()
