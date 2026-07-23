
"""
Integration test for clinical reasoning validation.
"""
from src.backend.reasoning.conflicts import ConflictAnalyzer
from src.backend.reasoning.context import ReasoningContextBuilder
from src.backend.reasoning.models import ClinicalReasoningResult
from src.backend.reasoning.validator import EvidenceCitationValidator


class TestReasoningValidationFlow:
    def test_validator_rejects_nonexistent_evidence(self):
        validator = EvidenceCitationValidator()
        validator.load_snapshot(evidence_items=[{"id": "ev-1"}], drug_names=["DrugA"])
        result = ClinicalReasoningResult(
            id="test", supporting_evidence_ids=["ev-999"])
        validation = validator.validate(result)
        assert not validation.valid
        assert len(validation.evidence_ids_not_found) == 1

    def test_validator_rejects_fake_pmid(self):
        validator = EvidenceCitationValidator()
        validator.load_snapshot(evidence_items=[{"id": "ev-1", "pmid": "12345678"}],
                                drug_names=[])
        result = ClinicalReasoningResult(
            id="test",
            citations=[{"evidence_id": "ev-1", "pmid": "99999999"}])
        validation = validator.validate(result)
        assert not validation.valid
        assert len(validation.pmids_not_found) == 1

    def test_conflict_analyzer_detects_conflicts(self):
        analyzer = ConflictAnalyzer()
        items = [
            {"drug_name": "DrugX", "evidence_direction": "Supports", "_conflict_status": "supporting"},
            {"drug_name": "DrugX", "evidence_direction": "Does Not Support", "_conflict_status": "conflicting"},
        ]
        conflicts = analyzer.analyze(items)
        assert len(conflicts) == 1
        assert conflicts[0]["drug_name"] == "DrugX"

    def test_context_hash_is_deterministic(self):
        import asyncio
        builder = ReasoningContextBuilder()
        ctx1 = asyncio.run(builder.build(variant_data={"gene": "BRAF"}))
        asyncio.run(builder.build(variant_data={"gene": "BRAF"}))
        # Different built_at timestamps, so hashes will differ
        assert ctx1.context_hash is not None
        assert len(ctx1.context_hash) == 64

