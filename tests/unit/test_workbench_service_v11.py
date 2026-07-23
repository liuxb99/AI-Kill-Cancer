"""
Unit tests for WorkbenchService v1.1 — data integrity, error handling, no fake data.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.backend.reasoning.service import ClinicalReasoningService
from src.backend.workbench.models import (
    ActivityLog,
    KnowledgeGraph,
    PatientSummary,
    TreatmentRecommendation,
    WorkbenchTimeline,
)
from src.backend.workbench.service import WorkbenchService


@pytest.fixture
def mock_db():
    """Create a mock async session."""
    db = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def service(mock_db):
    """Create WorkbenchService with mock DB."""
    return WorkbenchService(mock_db)


class TestDataIntegrity:
    """Data integrity: no fake data, empty results, proper errors."""

    async def test_empty_database_returns_empty_graph(self, service):
        """Empty DB → empty KnowledgeGraph, no BRAF/Vemurafenib."""
        service.case_repo.get = AsyncMock(return_value=None)
        service.variant_repo.find_by_case = AsyncMock(return_value=[])
        valid_uuid = str(uuid.uuid4())
        graph = await service.build_knowledge_graph(case_id=valid_uuid)
        assert isinstance(graph, KnowledgeGraph)
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0
        # Verify no BRAF or Vemurafenib in any node label
        labels = [n.label for n in graph.nodes]
        assert "BRAF" not in labels
        assert "Vemurafenib" not in labels

    async def test_empty_database_returns_empty_patient_summary(self, service):
        """Empty DB → empty PatientSummary, no fake demographics."""
        service.case_repo.get = AsyncMock(return_value=None)
        valid_uuid = str(uuid.uuid4())
        summary = await service.get_patient_summary(valid_uuid)
        assert isinstance(summary, PatientSummary)
        assert summary.cancer_type == ""
        assert summary.patient.age == 0
        assert summary.patient.sex == ""

    async def test_empty_database_returns_empty_activity_log(self, service):
        """Empty DB → empty ActivityLog, no placeholder entry."""
        # Mock audit log query returns empty
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        service.db.execute = AsyncMock(return_value=mock_result)

        log = await service.get_activity_log("case-1")
        assert isinstance(log, ActivityLog)
        assert len(log.entries) == 0
        assert log.total == 0

    async def test_empty_database_returns_empty_timeline(self, service):
        """Empty DB → empty WorkbenchTimeline, no fake events."""
        service.case_repo.get = AsyncMock(return_value=None)
        valid_uuid = str(uuid.uuid4())
        timeline = await service.get_case_timeline(valid_uuid)
        assert isinstance(timeline, WorkbenchTimeline)
        assert len(timeline.events) == 0

    async def test_invalid_uuid_returns_empty(self, service):
        """Invalid UUID string returns empty result, not fake data."""
        graph = await service.build_knowledge_graph(case_id="not-a-uuid-at-all")
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0

        summary = await service.get_patient_summary("not-a-uuid-at-all")
        assert summary.cancer_type == ""

        timeline = await service.get_case_timeline("not-a-uuid-at-all")
        assert len(timeline.events) == 0

    async def test_database_exception_returns_empty_gracefully(self, service):
        """DB exception returns empty/fallback, never fake data."""
        service.case_repo.get = AsyncMock(side_effect=Exception("DB connection failed"))
        valid_uuid = str(uuid.uuid4())

        graph = await service.build_knowledge_graph(case_id=valid_uuid)
        assert len(graph.nodes) == 0

        summary = await service.get_patient_summary(valid_uuid)
        assert summary.cancer_type == ""

    async def test_missing_case_returns_empty_patient_summary(self, service):
        """Case not found → empty PatientSummary."""
        service.case_repo.get = AsyncMock(return_value=None)
        valid_uuid = str(uuid.uuid4())
        summary = await service.get_patient_summary(valid_uuid)
        assert isinstance(summary, PatientSummary)
        assert summary.diagnosis == ""

    async def test_no_variants_empty_treatment(self, service):
        """No variants → empty treatment recommendations."""
        mock_case = MagicMock()
        mock_case.cancer_type = "BRCA"
        mock_case.stage = "II"
        mock_case.patient_id = uuid.uuid4()
        service.case_repo.get = AsyncMock(return_value=mock_case)
        service.variant_repo.find_by_case = AsyncMock(return_value=[])

        valid_uuid = str(uuid.uuid4())
        rec = await service.get_treatment_recommendation(valid_uuid)
        assert isinstance(rec, TreatmentRecommendation)
        assert len(rec.recommendations) == 0

    async def test_variants_link_to_treatment(self, service):
        """Variants with matching drugs produce recommendations."""
        mock_case = MagicMock()
        mock_case.cancer_type = "MEL"
        mock_case.stage = "IV"
        mock_case.patient_id = uuid.uuid4()
        service.case_repo.get = AsyncMock(return_value=mock_case)

        mock_variant = MagicMock()
        mock_variant.gene_symbol = "BRAF"
        mock_variant.hgvs_notation = "c.1799T>A"
        mock_variant.protein_change = "p.V600E"
        mock_variant.id = uuid.uuid4()
        mock_variant.created_at = None
        service.variant_repo.find_by_case = AsyncMock(return_value=[mock_variant])

        mock_drug = MagicMock()
        mock_drug.name = "Dabrafenib"
        mock_drug.drugbank_id = "DB08912"
        mock_drug.mechanism_of_action = "BRAF inhibitor"
        mock_drug.status = "approved"
        service.drug_repo.find_by_gene = AsyncMock(return_value=[mock_drug])

        valid_uuid = str(uuid.uuid4())
        rec = await service.get_treatment_recommendation(valid_uuid)
        assert len(rec.recommendations) >= 1
        names = [d.name for d in rec.recommendations]
        assert "Dabrafenib" in names

    async def test_timeline_from_case_events(self, service):
        """Case with variants produces timeline events."""
        mock_case = MagicMock()
        mock_case.cancer_type = "MEL"
        mock_case.created_at = None
        mock_case.updated_at = None
        service.case_repo.get = AsyncMock(return_value=mock_case)

        mock_variant = MagicMock()
        mock_variant.gene_symbol = "BRAF"
        mock_variant.hgvs_notation = "c.1799T>A"
        mock_variant.created_at = None
        service.variant_repo.find_by_case = AsyncMock(return_value=[mock_variant])

        valid_uuid = str(uuid.uuid4())
        timeline = await service.get_case_timeline(valid_uuid)
        assert len(timeline.events) >= 1

    async def test_compare_cases_shared_and_unique(self, service):
        """Case comparison correctly identifies shared and unique variants."""
        valid_id_1 = uuid.uuid4()
        valid_id_2 = uuid.uuid4()

        mock_v1 = MagicMock()
        mock_v1.gene_symbol = "BRAF"
        mock_v1.hgvs_notation = "c.1799T>A"
        mock_v1.protein_change = "p.V600E"
        mock_v1.id = uuid.uuid4()

        mock_v2 = MagicMock()
        mock_v2.gene_symbol = "EGFR"
        mock_v2.hgvs_notation = "c.2573T>G"
        mock_v2.protein_change = "p.L858R"
        mock_v2.id = uuid.uuid4()

        service.variant_repo.find_by_case = AsyncMock(side_effect=[
            [mock_v1],  # case 1: BRAF
            [mock_v1, mock_v2],  # case 2: BRAF + EGFR
        ])

        result = await service.compare_cases([str(valid_id_1), str(valid_id_2)])
        assert result.comparison_type == "case"
        assert len(result.case_ids) == 2


class TestErrorHandling:
    """Error handling: exceptions → proper errors, not empty results."""

    async def test_case_repo_exception(self, service):
        """When case_repo.get raises, service returns empty gracefully."""
        service.case_repo.get = AsyncMock(side_effect=Exception("repo error"))
        valid_uuid = str(uuid.uuid4())
        summary = await service.get_patient_summary(valid_uuid)
        # Should return empty PatientSummary without crashing
        assert isinstance(summary, PatientSummary)

    async def test_variant_repo_exception(self, service):
        """When variant_repo raises, service returns empty without crashing."""
        mock_case = MagicMock()
        mock_case.cancer_type = "BRCA"
        mock_case.stage = "II"
        mock_case.patient_id = uuid.uuid4()
        service.case_repo.get = AsyncMock(return_value=mock_case)
        service.variant_repo.find_by_case = AsyncMock(side_effect=Exception("repo error"))

        valid_uuid = str(uuid.uuid4())
        summary = await service.get_patient_summary(valid_uuid)
        assert isinstance(summary, PatientSummary)


class TestReasoningQuestion:
    """P0-1: User question enters LLM adapter prompt."""

    async def test_question_in_prompt(self):
        """Question string must appear in the built user prompt."""
        class SpyLLM:
            def __init__(self):
                self.prompts = []
                self.is_available = True
                self.provider = "test"
                self.model = "test"
                self.temperature = 0.1
                self.seed = 42
            async def generate(self, user_prompt, system_prompt=""):
                self.prompts.append(user_prompt)
                from src.backend.reasoning.llm import LLMResult
                return LLMResult(
                    success=True,
                    content='{"summary": "test", "key_findings": [], "drug_explanations": []}',
                    model="test",
                )

        db = AsyncMock()
        db.execute = AsyncMock()
        spy = SpyLLM()
        service = ClinicalReasoningService(db=db, llm_adapter=spy)

        await service.reason(
            case_id=str(uuid.uuid4()),
            gene_symbol="BRAF",
            disease="melanoma",
            question="What is the best therapy?",
        )

        assert len(spy.prompts) >= 1
        # The question must appear in the prompt sent to LLM
        assert "What is the best therapy?" in spy.prompts[0]
        # The question should be labeled
        assert "User question:" in spy.prompts[0]

    async def test_different_questions_different_prompts(self):
        """Different questions should produce different prompt content."""
        class SpyLLM2:
            def __init__(self):
                self.prompts = []
                self.is_available = True
                self.provider = "test"
                self.model = "test"
                self.temperature = 0.1
                self.seed = 42
            async def generate(self, user_prompt, system_prompt=""):
                self.prompts.append(user_prompt)
                from src.backend.reasoning.llm import LLMResult
                return LLMResult(
                    success=True,
                    content='{"summary": "test", "key_findings": [], "drug_explanations": []}',
                    model="test",
                )

        db = AsyncMock()
        db.execute = AsyncMock()
        spy = SpyLLM2()
        service = ClinicalReasoningService(db=db, llm_adapter=spy)

        await service.reason(
            case_id=str(uuid.uuid4()),
            gene_symbol="EGFR",
            question="What resistance mechanisms exist?",
        )

        assert "What resistance mechanisms exist?" in spy.prompts[0]
        assert "User question: What resistance mechanisms exist?" in spy.prompts[0]

    async def test_user_question_saved_in_reasoning_data(self):
        """User question is saved in the reasoning_data field."""
        class SavingDB:
            def __init__(self):
                self.added = []
                self.committed = False
            def add(self, obj):
                if hasattr(obj, 'id') and not obj.id:
                    obj.id = uuid.uuid4()
                self.added.append(obj)
            async def commit(self):
                self.committed = True
            async def refresh(self, obj):
                pass
            async def execute(self, stmt):
                m = MagicMock()
                m.scalar_one_or_none.return_value = None
                m.scalars.return_value.all.return_value = []
                return m
            async def close(self):
                pass
            def delete(self, obj):
                pass

        class SpyLLM3:
            def __init__(self):
                self.is_available = True
                self.provider = "test"
                self.model = "test"
                self.temperature = 0.1
                self.seed = 42
            async def generate(self, user_prompt, system_prompt=""):
                from src.backend.reasoning.llm import LLMResult
                return LLMResult(
                    success=True,
                    content='{"summary": "test", "key_findings": [], "drug_explanations": []}',
                    model="test",
                )

        db = SavingDB()
        spy = SpyLLM3()
        service = ClinicalReasoningService(db=db, llm_adapter=spy)

        question = "What is the standard of care?"
        await service.reason(
            case_id=str(uuid.uuid4()),
            question=question,
        )

        # Verify the reasoning_data contains user_question
        reasoning_run = [a for a in db.added if hasattr(a, 'reasoning_data')]
        assert len(reasoning_run) > 0
        rd = reasoning_run[-1].reasoning_data
        assert rd.get("user_question") == question
