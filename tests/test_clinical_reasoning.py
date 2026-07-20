"""
Tests for Clinical Reasoning Layer (v0.7.0).
"""

from __future__ import annotations

import pytest

from src.backend.reasoning.models import (
    ClinicalReasoningResult, ReasoningRunResponse,
    ReasoningEvidenceCitation, ReasoningDrugExplanation,
    ReasoningValidationResult, SafetyNotice,
)
from src.backend.reasoning.validator import EvidenceCitationValidator, HallucinationGuard
from src.backend.reasoning.conflicts import ConflictAnalyzer
from src.backend.reasoning.context import ReasoningContextBuilder
from src.backend.reasoning.llm import (
    LLMAdapter, DisabledLLMAdapter, OpenAILikeAdapter, LocalLLMAdapter,
    get_llm_adapter, LLMResult,
)


class TestReasoningModels:
    def test_clinical_reasoning_result_defaults(self):
        result = ClinicalReasoningResult(id="test-1")
        assert result.id == "test-1"
        assert result.summary == ""
        assert len(result.key_findings) == 0
        assert result.safety_notice is not None
        assert "NOT" in result.safety_notice.notice

    def test_reasoning_drug_explanation(self):
        de = ReasoningDrugExplanation(
            drug_name="Vemurafenib",
            explanation="Test explanation",
            supporting_evidence_ids=["ev-1", "ev-2"],
        )
        assert de.drug_name == "Vemurafenib"
        assert len(de.supporting_evidence_ids) == 2

    def test_reasoning_evidence_citation(self):
        cit = ReasoningEvidenceCitation(
            evidence_id="ev-1",
            pmid="12345678",
            validated=True,
        )
        assert cit.validated

    def test_safety_notice(self):
        notice = SafetyNotice()
        assert notice.disclaimer_version == "1.0"
        assert "research" in notice.notice.lower()

    def test_reasoning_run_response(self):
        resp = ReasoningRunResponse(
            run_id="run-1",
            status="completed",
            message="Done",
        )
        assert resp.run_id == "run-1"
        assert resp.status == "completed"

    def test_reasoning_validation_result(self):
        result = ReasoningValidationResult(
            valid=True,
            citation_errors=[],
        )
        assert result.valid
        assert len(result.citation_errors) == 0


class TestEvidenceCitationValidator:
    def test_valid_citations(self):
        validator = EvidenceCitationValidator()
        validator.load_snapshot(
            evidence_items=[
                {"id": "ev-1", "pmid": "12345678", "drug_name": "Vemurafenib"},
                {"id": "ev-2", "pmid": "87654321", "drug_name": "Dabrafenib"},
            ],
            drug_names=["Vemurafenib", "Dabrafenib"],
        )

        result = ClinicalReasoningResult(
            id="test",
            supporting_evidence_ids=["ev-1", "ev-2"],
            drug_explanations=[
                ReasoningDrugExplanation(
                    drug_name="Vemurafenib",
                    supporting_evidence_ids=["ev-1"],
                ),
            ],
        )

        validation = validator.validate(result)
        assert validation.valid

    def test_invalid_evidence_id(self):
        validator = EvidenceCitationValidator()
        validator.load_snapshot(evidence_items=[{"id": "ev-1"}], drug_names=[])

        result = ClinicalReasoningResult(
            id="test",
            supporting_evidence_ids=["ev-999"],  # Non-existent
        )

        validation = validator.validate(result)
        assert not validation.valid
        assert len(validation.evidence_ids_not_found) == 1

    def test_invalid_drug_name(self):
        validator = EvidenceCitationValidator()
        validator.load_snapshot(
            evidence_items=[{"id": "ev-1", "drug_name": "Vemurafenib"}],
            drug_names=["Vemurafenib"],
        )

        result = ClinicalReasoningResult(
            id="test",
            drug_explanations=[
                ReasoningDrugExplanation(
                    drug_name="FakeDrug",  # Not in snapshot
                    supporting_evidence_ids=["ev-1"],
                ),
            ],
        )

        validation = validator.validate(result)
        assert not validation.valid
        assert len(validation.drug_errors) > 0

    def test_invalid_pmid(self):
        validator = EvidenceCitationValidator()
        validator.load_snapshot(
            evidence_items=[{"id": "ev-1", "pmid": "12345678"}],
            drug_names=[],
        )

        result = ClinicalReasoningResult(
            id="test",
            citations=[
                ReasoningEvidenceCitation(
                    evidence_id="ev-1",
                    pmid="99999999",  # Not in snapshot
                ),
            ],
        )

        validation = validator.validate(result)
        assert not validation.valid
        assert len(validation.pmids_not_found) == 1


class TestHallucinationGuard:
    def test_known_drug_passes(self):
        guard = HallucinationGuard()
        guard.load_snapshot([{"drug_name": "Vemurafenib", "pmid": "12345678"}])
        assert guard.check_drug_name("Vemurafenib")

    def test_unknown_drug_fails(self):
        guard = HallucinationGuard()
        guard.load_snapshot([{"drug_name": "Vemurafenib"}])
        assert not guard.check_drug_name("FakeDrug")

    def test_known_pmid(self):
        guard = HallucinationGuard()
        guard.load_snapshot([{"pmid": "12345678"}])
        assert guard.check_pmid("12345678")

    def test_unknown_pmid(self):
        guard = HallucinationGuard()
        guard.load_snapshot([])
        assert not guard.check_pmid("99999999")


class TestConflictAnalyzer:
    def test_no_conflicts(self):
        analyzer = ConflictAnalyzer()
        items = [
            {"drug_name": "Vemurafenib", "evidence_direction": "Supports", "_conflict_status": "supporting"},
            {"drug_name": "Vemurafenib", "evidence_direction": "Supports", "_conflict_status": "supporting"},
        ]
        conflicts = analyzer.analyze(items)
        assert len(conflicts) == 0

    def test_detects_conflicts(self):
        analyzer = ConflictAnalyzer()
        items = [
            {"drug_name": "DrugX", "evidence_direction": "Supports", "_conflict_status": "supporting"},
            {"drug_name": "DrugX", "evidence_direction": "Does Not Support", "_conflict_status": "conflicting"},
        ]
        conflicts = analyzer.analyze(items)
        assert len(conflicts) == 1
        assert conflicts[0]["drug_name"] == "DrugX"
        assert conflicts[0]["supporting_count"] == 1
        assert conflicts[0]["conflicting_count"] == 1


class TestReasoningContext:
    def test_build_context(self):
        builder = ReasoningContextBuilder()
        import asyncio
        context = asyncio.run(builder.build(
            variant_data={"gene": "BRAF", "hgvs": "c.1799T>A"},
            evidence_items=[{"id": "ev-1", "drug_name": "Vemurafenib"}],
        ))
        assert context.variant_snapshot["gene"] == "BRAF"
        assert len(context.evidence_snapshot) == 1
        assert context.context_hash is not None
        assert len(context.context_hash) == 64  # SHA256

    def test_context_hash_format(self):
        builder = ReasoningContextBuilder()
        import asyncio
        ctx = asyncio.run(builder.build(
            variant_data={"gene": "BRAF"},
            evidence_items=[{"id": "ev-1"}],
        ))
        assert ctx.context_hash is not None
        assert len(ctx.context_hash) == 64  # SHA256 hex

    def test_context_different_inputs_different_hashes(self):
        builder = ReasoningContextBuilder()
        import asyncio
        ctx1 = asyncio.run(builder.build(
            variant_data={"gene": "BRAF"},
            evidence_items=[{"id": "ev-1"}],
        ))
        ctx2 = asyncio.run(builder.build(
            variant_data={"gene": "EGFR"},
            evidence_items=[{"id": "ev-2"}],
        ))
        # Different inputs should produce different hashes
        assert ctx1.context_hash != ctx2.context_hash


class TestLLMAdapters:
    def test_disabled_adapter(self):
        adapter = DisabledLLMAdapter()
        assert not adapter.is_available
        import asyncio
        result = asyncio.run(adapter.generate("test"))
        assert not result.success
        assert "not configured" in result.error.lower()

    def test_get_disabled_adapter(self):
        adapter = get_llm_adapter({"provider": "disabled"})
        assert isinstance(adapter, DisabledLLMAdapter)
        assert not adapter.is_available

    def test_get_openai_adapter_without_key(self):
        adapter = get_llm_adapter({"provider": "openai"})
        assert isinstance(adapter, OpenAILikeAdapter)
        # Without API key, should not be available
        import os
        if not os.getenv("OPENAI_API_KEY"):
            assert not adapter.is_available


class TestClinicalReasoningService:
    """Test the reasoning service with mock DB."""

    async def test_reasoning_without_llm(self):
        from tests.test_knowledge_layer import FakeKnowledgeDB
        db = FakeKnowledgeDB()
        adapter = DisabledLLMAdapter()

        from src.backend.reasoning.service import ClinicalReasoningService
        service = ClinicalReasoningService(db=db, llm_adapter=adapter)

        result = await service.reason(
            case_id="test-case",
            gene_symbol="BRAF",
            disease="melanoma",
            evidence_items=[{"id": "ev-1", "drug_name": "Vemurafenib"}],
        )

        assert result.status == "no_llm"
        assert result.reasoning is not None
        assert "LLM not configured" in result.message
        assert "BRAF" in result.reasoning.summary
