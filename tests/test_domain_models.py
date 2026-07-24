"""
Tests for domain models — Pydantic schema validation.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.backend.domain.analysis_run import AnalysisRunCreate
from src.backend.domain.cancer_case import CancerCaseCreate
from src.backend.domain.consent import ConsentCreate, ConsentTypeEnum
from src.backend.domain.drug import DrugCreate
from src.backend.domain.enums import (
    CancerTypeEnum,
    ConsentStatusEnum,
    EvidenceDirectionEnum,
    EvidenceLevelEnum,
    FileTypeEnum,
    SexEnum,
    VariantOriginEnum,
    VariantTypeEnum,
)
from src.backend.domain.evidence import EvidenceCreate
from src.backend.domain.patient import PatientCreate, PatientUpdate
from src.backend.domain.sequencing import SequencingTestCreate
from src.backend.domain.specimen import SpecimenCreate, SpecimenTypeEnum
from src.backend.domain.uploaded_file import FileTypeEnum as UploadFileType
from src.backend.domain.uploaded_file import UploadedFileCreate
from src.backend.domain.variant import VariantImport
from src.backend.domain.visualization_graph import GraphEdge, GraphNode, VisualizationGraph


class TestPatientSchema:
    def test_patient_create_valid(self):
        p = PatientCreate(sex=SexEnum.M, consent_status=ConsentStatusEnum.GRANTED)
        assert p.sex == "M"
        assert p.consent_status == "granted"

    def test_patient_create_minimal(self):
        p = PatientCreate()
        assert p.consent_status == "pending"

    def test_patient_create_invalid_birth_year(self):
        with pytest.raises(ValidationError):
            PatientCreate(birth_year=1899)

    def test_patient_update_allows_partial(self):
        u = PatientUpdate(display_name="ANON-001")
        assert u.display_name == "ANON-001"


class TestCancerCaseSchema:
    def test_case_create_valid(self):
        c = CancerCaseCreate(
            patient_id="550e8400-e29b-41d4-a716-446655440000",
            cancer_type=CancerTypeEnum.PTC,
        )
        assert c.cancer_type == "PTC"

    def test_case_create_invalid_type(self):
        with pytest.raises(ValidationError):
            CancerCaseCreate(
                patient_id="550e8400-e29b-41d4-a716-446655440000",
                cancer_type="INVALID",
            )

    def test_case_create_all_fields(self):
        c = CancerCaseCreate(
            patient_id="550e8400-e29b-41d4-a716-446655440000",
            cancer_type=CancerTypeEnum.ATC,
            stage="IVB",
            oncotree_code="THPA",
        )
        assert c.stage == "IVB"
        assert c.oncotree_code == "THPA"


class TestSpecimenSchema:
    def test_specimen_create_valid(self):
        s = SpecimenCreate(
            case_id="550e8400-e29b-41d4-a716-446655440000",
            specimen_type=SpecimenTypeEnum.FFPE,
        )
        assert s.specimen_type == "FFPE"

    def test_specimen_create_with_tumor_purity(self):
        s = SpecimenCreate(
            case_id="id", specimen_type=SpecimenTypeEnum.FRESH_FROZEN,
            tumor_purity=0.75,
        )
        assert s.tumor_purity == 0.75

    def test_specimen_create_invalid_purity(self):
        with pytest.raises(ValidationError):
            SpecimenCreate(
                case_id="id", specimen_type=SpecimenTypeEnum.BLOOD,
                tumor_purity=1.5,
            )


class TestSequencingTestSchema:
    def test_sequencing_test_create_valid(self):
        t = SequencingTestCreate(
            specimen_id="550e8400-e29b-41d4-a716-446655440000",
            assay_name="ThyroSeq v3",
        )
        assert t.assay_name == "ThyroSeq v3"
        assert t.result_type == "somatic"


class TestUploadedFileSchema:
    def test_upload_create_valid(self):
        u = UploadedFileCreate(
            sequencing_test_id="550e8400-e29b-41d4-a716-446655440000",
            original_filename="sample.vcf",
            file_type=UploadFileType.VCF,
        )
        assert u.file_type == "VCF"

    def test_upload_create_json(self):
        u = UploadedFileCreate(
            sequencing_test_id="id",
            original_filename="report.json",
            file_type=FileTypeEnum.JSON,
        )
        assert u.file_type == "JSON"


class TestVariantSchema:
    def test_variant_import_valid(self):
        v = VariantImport(
            sequencing_test_id="550e8400-e29b-41d4-a716-446655440000",
            gene_symbol="BRAF",
            chromosome="7",
            position=140753336,
            reference="A",
            alternate="T",
            genome_build="GRCh38",
            variant_type=VariantTypeEnum.SNV,
            origin=VariantOriginEnum.SOMATIC,
        )
        assert v.gene_symbol == "BRAF"
        assert v.hgvs_p is None  # optional

    def test_variant_import_full(self):
        v = VariantImport(
            sequencing_test_id="id",
            gene_symbol="TERT",
            chromosome="5",
            position=1295228,
            reference="G",
            alternate="A",
            genome_build="GRCh38",
            variant_type=VariantTypeEnum.TERT_PROMOTER,
            origin=VariantOriginEnum.SOMATIC,
            hgvs_g="g.1295228G>A",
            vaf=0.45,
        )
        assert v.variant_type == "TERT_promoter"
        assert v.vaf == 0.45


class TestDrugSchema:
    def test_drug_create_valid(self):
        d = DrugCreate(
            name="Lenvatinib",
            drugbank_id="DB09078",
        )
        assert d.name == "Lenvatinib"
        assert d.approval_status is None


class TestEvidenceSchema:
    def test_evidence_create_valid(self):
        e = EvidenceCreate(
            evidence_type="predictive",
            source_name="CIViC",
            evidence_direction=EvidenceDirectionEnum.SUPPORTING,
            evidence_level=EvidenceLevelEnum.LEVEL_2,
        )
        assert e.evidence_direction == "supporting"

    def test_evidence_direction_enum_values(self):
        for direction in ["supporting", "conflicting", "neutral", "insufficient"]:
            e = EvidenceCreate(
                evidence_type="prognostic",
                source_name="Test",
                evidence_direction=direction,
                evidence_level=EvidenceLevelEnum.LEVEL_4,
            )
            assert e.evidence_direction == direction


class TestAnalysisRunSchema:
    def test_analysis_run_create_valid(self):
        a = AnalysisRunCreate(
            case_id="550e8400-e29b-41d4-a716-446655440000",
            pipeline_version="0.2.0",
        )
        assert a.pipeline_version == "0.2.0"

    def test_analysis_run_default_status(self):
        """AnalysisRuns created in Phase 1 start as pending."""
        # AnalysisRunCreate doesn't have status field — it's set server-side
        a = AnalysisRunCreate(
            case_id="550e8400-e29b-41d4-a716-446655440000",
        )
        assert a.case_id is not None


class TestConsentSchema:
    def test_consent_create_valid(self):
        c = ConsentCreate(
            patient_id="550e8400-e29b-41d4-a716-446655440000",
            consent_type=ConsentTypeEnum.RESEARCH,
        )
        assert c.consent_type == "research"


class TestGraphSchema:
    def test_graph_node(self):
        n = GraphNode(id="BRAF", type="gene", label="BRAF")
        assert n.id == "BRAF"
        assert n.status == "active"

    def test_graph_edge(self):
        e = GraphEdge(
            id="e1", source="BRAF", target="MAPK",
            relation="activates",
        )
        assert e.direction == "directed"
        assert e.weight == 1.0

    def test_visualization_graph(self):
        g = VisualizationGraph(
            nodes=[GraphNode(id="n1", type="gene", label="BRAF")],
            edges=[GraphEdge(id="e1", source="n1", target="n2", relation="affects")],
        )
        assert len(g.nodes) == 1
        assert len(g.edges) == 1

    def test_node_types_are_valid(self):
        from src.backend.domain.visualization_graph import NODE_TYPES
        assert "gene" in NODE_TYPES
        assert "variant" in NODE_TYPES
        assert "drug" in NODE_TYPES
        assert "cancer_case" in NODE_TYPES
        assert len(NODE_TYPES) == 10

    def test_edge_types_are_valid(self):
        from src.backend.domain.visualization_graph import EDGE_TYPES
        assert "activates" in EDGE_TYPES
        assert "inhibits" in EDGE_TYPES
        assert "targets" in EDGE_TYPES
        assert len(EDGE_TYPES) == 12


# ═══════════════════════════════════════════════════════════════════════════════
# Recommendation Model Tests (SQLAlchemy ORM models)
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
async def db_session():
    """Create an in-memory SQLite database for testing SQLAlchemy models."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from src.backend.database.models import Base

    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def sample_recommendation_data():
    """Provide a base set of fields for creating a RecommendationModel."""
    return {
        "recommendation_id": "abc123def456",
        "engine_version": "1.0.0",
        "status": "pending",
        "request_payload": {"variants": ["EGFR L858R"]},
        "result_payload": {"recommendations": [{"drug_name": "Osimertinib", "rank": 1}]},
        "report_html": "<html><body>Report</body></html>",
    }


@pytest.fixture
async def patient(db_session):
    """Create a minimal Patient for FK references."""
    from src.backend.domain.patient import PatientModel

    p = PatientModel(display_name="TEST-PATIENT")
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p


class TestRecommendationModels:
    """Test SQLAlchemy models for recommendation domain."""

    async def test_create_recommendation_all_fields(self, db_session, sample_recommendation_data, patient):
        """RecommendationModel can be created with all fields populated."""
        from src.backend.domain.recommendation import RecommendationModel

        data = dict(sample_recommendation_data)
        data["patient_id"] = patient.id
        rec = RecommendationModel(**data)
        db_session.add(rec)
        await db_session.commit()
        await db_session.refresh(rec)

        assert rec.id is not None
        assert rec.recommendation_id == "abc123def456"
        assert rec.engine_version == "1.0.0"
        assert rec.status == "pending"
        assert rec.request_payload == {"variants": ["EGFR L858R"]}
        assert rec.result_payload == {"recommendations": [{"drug_name": "Osimertinib", "rank": 1}]}
        assert rec.report_html == "<html><body>Report</body></html>"
        assert rec.created_at is not None
        assert rec.updated_at is not None

    async def test_default_values(self, db_session, patient):
        """RecommendationModel should have sensible defaults."""
        from src.backend.domain.recommendation import RecommendationModel

        rec = RecommendationModel(
            recommendation_id="default-test",
            patient_id=patient.id,
        )
        db_session.add(rec)
        await db_session.commit()
        await db_session.refresh(rec)

        assert rec.engine_version == "1.0.0"  # default
        assert rec.status == "pending"  # default
        assert rec.created_at is not None  # auto-set
        assert rec.updated_at is not None  # auto-set
        assert rec.request_payload is None  # nullable
        assert rec.result_payload is None  # nullable
        assert rec.report_html is None  # nullable

    async def test_recommendation_id_unique(self, db_session, patient):
        """recommendation_id must be unique."""
        from sqlalchemy.exc import IntegrityError

        from src.backend.domain.recommendation import RecommendationModel

        rec1 = RecommendationModel(recommendation_id="unique-id-001", patient_id=patient.id)
        db_session.add(rec1)
        await db_session.commit()

        rec2 = RecommendationModel(recommendation_id="unique-id-001", patient_id=patient.id)
        db_session.add(rec2)
        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_json_fields_round_trip(self, db_session, patient):
        """JSON fields (request_payload, result_payload) should survive a write-read cycle."""
        from src.backend.domain.recommendation import RecommendationModel

        complex_payload = {
            "variants": ["EGFR L858R", "KRAS G12C"],
            "patient_context": {"age": 65, "cancer_type": "NSCLC"},
            "top_n": 5,
            "nested": {"list": [1, 2, 3], "flag": True},
        }
        rec = RecommendationModel(
            recommendation_id="json-roundtrip",
            patient_id=patient.id,
            request_payload=complex_payload,
            result_payload={"rankings": [{"drug": "Test", "score": 0.95}]},
        )
        db_session.add(rec)
        await db_session.commit()
        await db_session.refresh(rec)

        assert rec.request_payload == complex_payload
        assert rec.result_payload["rankings"][0]["drug"] == "Test"

    async def test_trace_relation(self, db_session, patient):
        """RecommendationModel can be linked to a RecommendationTraceModel."""
        from src.backend.domain.recommendation import (
            RecommendationModel,
            RecommendationTraceModel,
        )

        rec = RecommendationModel(recommendation_id="trace-rel-test", patient_id=patient.id)
        db_session.add(rec)
        await db_session.flush()

        trace = RecommendationTraceModel(
            trace_id="trace-001",
            recommendation_id=rec.id,
        )
        db_session.add(trace)
        await db_session.commit()

        # Reload and check relationship
        await db_session.refresh(rec)
        assert len(rec.traces) == 1
        assert rec.traces[0].trace_id == "trace-001"

    async def test_trace_steps_relation(self, db_session, patient):
        """RecommendationTraceModel can have multiple trace steps."""
        from src.backend.domain.recommendation import (
            RecommendationModel,
            RecommendationTraceModel,
            RecommendationTraceStepModel,
        )

        rec = RecommendationModel(recommendation_id="steps-rel-test", patient_id=patient.id)
        db_session.add(rec)
        await db_session.flush()

        trace = RecommendationTraceModel(
            trace_id="trace-steps-001",
            recommendation_id=rec.id,
        )
        db_session.add(trace)
        await db_session.flush()

        step1 = RecommendationTraceStepModel(
            trace_id=trace.id,
            step_order=1,
            step_type="evidence_collection",
            input_summary={"variants": ["EGFR"]},
            output_summary={"evidence_count": 5},
            status="completed",
        )
        step2 = RecommendationTraceStepModel(
            trace_id=trace.id,
            step_order=2,
            step_type="drug_ranking",
            input_summary={"drugs": ["Osimertinib"]},
            output_summary={"rank": 1},
            status="completed",
        )
        db_session.add_all([step1, step2])
        await db_session.commit()

        await db_session.refresh(trace)
        assert len(trace.steps) == 2
        assert trace.steps[0].step_order == 1
        assert trace.steps[1].step_order == 2

    async def test_cascade_delete_recommendation_deletes_traces(self, db_session, patient):
        """Deleting a RecommendationModel should cascade-delete its traces."""
        from src.backend.domain.recommendation import (
            RecommendationModel,
            RecommendationTraceModel,
        )

        rec = RecommendationModel(recommendation_id="cascade-del", patient_id=patient.id)
        db_session.add(rec)
        await db_session.flush()

        trace = RecommendationTraceModel(
            trace_id="trace-cascade",
            recommendation_id=rec.id,
        )
        db_session.add(trace)
        await db_session.commit()

        # Delete the recommendation
        await db_session.delete(rec)
        await db_session.commit()

        # Verify trace is gone
        from sqlalchemy import select

        stmt = select(RecommendationTraceModel).where(
            RecommendationTraceModel.trace_id == "trace-cascade",
        )
        result = await db_session.execute(stmt)
        assert result.scalar_one_or_none() is None

    async def test_cascade_delete_trace_deletes_steps(self, db_session, patient):
        """Deleting a RecommendationTraceModel should cascade-delete its steps."""
        from src.backend.domain.recommendation import (
            RecommendationModel,
            RecommendationTraceModel,
            RecommendationTraceStepModel,
        )

        rec = RecommendationModel(recommendation_id="cascade-step-del", patient_id=patient.id)
        db_session.add(rec)
        await db_session.flush()

        trace = RecommendationTraceModel(
            trace_id="trace-step-cascade",
            recommendation_id=rec.id,
        )
        db_session.add(trace)
        await db_session.flush()

        step = RecommendationTraceStepModel(
            trace_id=trace.id,
            step_order=1,
            step_type="test",
            status="completed",
        )
        db_session.add(step)
        await db_session.commit()

        # Delete the trace
        await db_session.delete(trace)
        await db_session.commit()

        # Verify step is gone
        from sqlalchemy import select

        stmt = select(RecommendationTraceStepModel).where(
            RecommendationTraceStepModel.step_order == 1,
        )
        result = await db_session.execute(stmt)
        assert result.scalar_one_or_none() is None

    async def test_trace_step_default_status(self, db_session, patient):
        """RecommendationTraceStepModel should default status to 'pending'."""
        from src.backend.domain.recommendation import (
            RecommendationModel,
            RecommendationTraceModel,
            RecommendationTraceStepModel,
        )

        rec = RecommendationModel(recommendation_id="step-default", patient_id=patient.id)
        db_session.add(rec)
        await db_session.flush()

        trace = RecommendationTraceModel(
            trace_id="step-default-trace",
            recommendation_id=rec.id,
        )
        db_session.add(trace)
        await db_session.flush()

        step = RecommendationTraceStepModel(
            trace_id=trace.id,
            step_order=1,
            step_type="test",
        )
        db_session.add(step)
        await db_session.commit()

        assert step.status == "pending"  # default

    async def test_trace_without_recommendation_allowed(self, db_session):
        """RecommendationTraceModel.recommendation_id is nullable."""
        from src.backend.domain.recommendation import RecommendationTraceModel

        trace = RecommendationTraceModel(trace_id="orphan-trace")
        db_session.add(trace)
        await db_session.commit()
        await db_session.refresh(trace)

        assert trace.id is not None
        assert trace.recommendation_id is None
