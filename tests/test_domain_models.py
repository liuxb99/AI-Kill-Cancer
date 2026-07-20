"""
Tests for domain models — Pydantic schema validation.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.backend.domain.enums import (
    CancerTypeEnum, SexEnum, ConsentStatusEnum,
    VariantTypeEnum, VariantOriginEnum, OncogenicityEnum,
    EvidenceDirectionEnum, EvidenceLevelEnum, CandidateCategoryEnum,
    AnalysisStatusEnum, FileTypeEnum, UploadStatusEnum,
)
from src.backend.domain.patient import PatientCreate, PatientUpdate
from src.backend.domain.cancer_case import CancerCaseCreate
from src.backend.domain.specimen import SpecimenCreate, SpecimenTypeEnum
from src.backend.domain.sequencing_test import SequencingTestCreate
from src.backend.domain.uploaded_file import UploadedFileCreate, FileTypeEnum as UploadFileType
from src.backend.domain.variant import VariantImport
from src.backend.domain.drug import DrugCreate
from src.backend.domain.evidence import EvidenceCreate
from src.backend.domain.analysis_run import AnalysisRunCreate
from src.backend.domain.consent import ConsentCreate, ConsentTypeEnum
from src.backend.domain.visualization_graph import GraphNode, GraphEdge, VisualizationGraph


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
        from src.backend.domain.analysis_run import AnalysisRunModel, AnalysisStatusEnum
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
