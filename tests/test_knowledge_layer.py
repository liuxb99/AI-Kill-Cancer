"""
Tests for Extended Knowledge Layer (v0.6.0).
"""

from __future__ import annotations

import uuid
import pytest

from src.backend.knowledge.models import (
    KnowledgeEntity, KnowledgeRelation, Publication, ClinicalTrial,
    GuidelineItem, RegulatoryApproval, KnowledgeEntityResponse,
)
from src.backend.knowledge.identifiers import IdentifierMapper, normalize_hgvs, normalize_gene_symbol


class TestIdentifierMapper:
    def setup_method(self):
        self.mapper = IdentifierMapper()

    def test_map_gene_to_ncbi(self):
        assert self.mapper.map_gene_to_ncbi("BRAF") == "673"
        assert self.mapper.map_gene_to_ncbi("EGFR") == "1956"
        assert self.mapper.map_gene_to_ncbi("UNKNOWN") is None

    def test_map_ncbi_to_gene(self):
        assert self.mapper.map_ncbi_to_gene("673") == "BRAF"
        assert self.mapper.map_ncbi_to_gene("999999") is None

    def test_detect_pmid(self):
        assert self.mapper.detect_identifier_type("12345678") == "pmid"

    def test_detect_nct(self):
        assert self.mapper.detect_identifier_type("NCT04267848") == "nct"

    def test_detect_doi(self):
        assert self.mapper.detect_identifier_type("10.1038/s41586-020-2649-2") == "doi"

    def test_detect_dbsnp(self):
        assert self.mapper.detect_identifier_type("rs113488022") == "dbsnp"

    def test_detect_hgvs(self):
        assert self.mapper.detect_identifier_type("NM_004333.6:c.1799T>A") == "hgvs"

    def test_detect_oncotree(self):
        assert self.mapper.detect_identifier_type("MEL") == "oncotree"

    def test_detect_doid(self):
        assert self.mapper.detect_identifier_type("DOID:1909") == "doid"

    def test_detect_drugbank(self):
        assert self.mapper.detect_identifier_type("DB01267") == "drugbank"

    def test_map_oncotree_to_disease(self):
        assert self.mapper.map_oncotree_to_disease("MEL") == "Melanoma"
        assert self.mapper.map_oncotree_to_disease("LUAD") == "Lung Adenocarcinoma"
        assert self.mapper.map_oncotree_to_disease("INVALID") is None

    def test_map_doid_to_disease(self):
        assert self.mapper.map_doid_to_disease("DOID:1909") == "Melanoma"
        assert self.mapper.map_doid_to_disease("DOID:999999") is None

    def test_get_all_identifiers(self):
        ids = self.mapper.get_all_identifiers("BRAF")
        assert ids["hgnc"] == "BRAF"
        assert ids["ncbi_gene"] == "673"

    def test_normalize_hgvs(self):
        assert normalize_hgvs(" NM_004333.6:c.1799T>A ") == "NM_004333.6:C.1799T>A"
        assert normalize_hgvs("nM_004333.6:c.1799T>A") == "NM_004333.6:C.1799T>A"


class TestKnowledgeModels:
    def test_knowledge_entity(self):
        entity = KnowledgeEntity(
            entity_type="gene",
            source="HGNC",
            source_id="1097",
            name="BRAF",
            identifiers={"ncbi_gene": "673"},
        )
        assert entity.entity_type == "gene"
        assert entity.name == "BRAF"
        assert entity.identifiers["ncbi_gene"] == "673"

    def test_knowledge_relation(self):
        rel = KnowledgeRelation(
            source_entity_id="id-1",
            target_entity_id="id-2",
            relation_type="associated_with",
            source="CIViC",
        )
        assert rel.relation_type == "associated_with"

    def test_publication(self):
        pub = Publication(
            pmid="12345678",
            title="Test Publication",
            authors=["Author A", "Author B"],
            journal="Nature",
            year=2024,
        )
        assert pub.pmid == "12345678"
        assert len(pub.authors) == 2

    def test_clinical_trial(self):
        trial = ClinicalTrial(
            nct_id="NCT04267848",
            title="Test Trial",
            status="Recruiting",
            phase="Phase 2",
            conditions=["Melanoma"],
        )
        assert trial.nct_id == "NCT04267848"
        assert trial.phase == "Phase 2"

    def test_guideline_item(self):
        guideline = GuidelineItem(
            source="NCCN",
            title="NCCN Melanoma Guidelines",
            disease="Melanoma",
            drug="Vemurafenib",
            biomarker="BRAF V600E",
        )
        assert guideline.source == "NCCN"
        assert guideline.drug == "Vemurafenib"

    def test_regulatory_approval(self):
        approval = RegulatoryApproval(
            drug_name="Vemurafenib",
            indication="BRAF V600E melanoma",
            agency="FDA",
            approval_type="full",
        )
        assert approval.drug_name == "Vemurafenib"
        assert approval.agency == "FDA"

    def test_knowledge_entity_response(self):
        response = KnowledgeEntityResponse(
            entity=KnowledgeEntity(entity_type="gene", source="HGNC", source_id="1097", name="BRAF"),
        )
        assert response.entity is not None
        assert response.entity.name == "BRAF"


class FakeKnowledgeDB:
    '''Minimal mock DB for knowledge repository tests.'''
    def __init__(self):
        self.added = []

    def add(self, obj):
        obj.id = uuid.uuid4()
        self.added.append(obj)

    async def commit(self):
        pass

    async def refresh(self, obj):
        pass

    async def execute(self, stmt):
        return FakeKnowledgeResult()

    async def close(self):
        pass


class FakeKnowledgeResult:
    def scalar_one_or_none(self):
        return None
    def scalars(self):
        return FakeKnowledgeScalars()
    def scalar(self):
        return 0


class FakeKnowledgeScalars:
    def all(self):
        return []


class TestKnowledgeRepository:
    """Test KnowledgeRepository using mock DB."""

    async def test_upsert_and_find(self):
        db = FakeKnowledgeDB()
        from src.backend.knowledge.repository import KnowledgeRepository

        repo = KnowledgeRepository(db)
        # Mock session doesn't actually store data, but method shouldn't crash
        result = await repo.upsert_entity(
            entity_type="gene",
            source="HGNC",
            source_id="1097",
            name="BRAF",
            identifiers={"ncbi_gene": "673"},
        )
        assert result is not None

    async def test_count_entities(self):
        db = FakeKnowledgeDB()
        from src.backend.knowledge.repository import KnowledgeRepository

        repo = KnowledgeRepository(db)
        count = await repo.count_entities()
        assert count == 0


class TestKnowledgeService:
    async def test_get_variant_knowledge_empty(self):
        db = FakeKnowledgeDB()
        from src.backend.knowledge.service import KnowledgeService

        service = KnowledgeService(db)
        # Invalid UUID
        result = await service.get_variant_knowledge("not-a-uuid")
        assert result.entity is None
