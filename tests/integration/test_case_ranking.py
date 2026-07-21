
"""
Integration test for case-based drug ranking (was 501).
Tests the full flow: variant evidence → merge → rank → persist.
"""
from src.backend.ranking.engine import DrugRankingEngine

class TestCaseRankingFlow:
    async def test_rank_case_no_variants(self):
        engine = DrugRankingEngine()
        result = await engine.rank(
            gene_symbol="",
            evidence_items=[],
            drug_interactions=[],
        )
        assert result.ranking_count == 0
        assert result.status == "completed"

    async def test_rank_case_with_variants(self):
        engine = DrugRankingEngine()
        evidence = [
            {"id": "ev-1", "drug_name": "DrugA", "evidence_level": "A",
             "evidence_direction": "Supports", "_match_level": "exact_variant",
             "source": "civic", "source_record_id": "1", "retrieved_at": "2024-01-01T00:00:00",
             "clinical_significance": "sensitivity"},
            {"id": "ev-2", "drug_name": "DrugB", "evidence_level": "B",
             "evidence_direction": "Supports", "_match_level": "gene_level_only",
             "source": "civic", "source_record_id": "2", "retrieved_at": "2024-01-01T00:00:00",
             "clinical_significance": ""},
        ]
        result = await engine.rank(
            gene_symbol="BRAF",
            evidence_items=evidence,
            drug_interactions=[],
            disease="melanoma",
            variant_match_level="exact_variant",
        )
        assert result.ranking_count == 2
        assert result.rankings[0].total_score >= result.rankings[1].total_score

    async def test_rank_case_persists_variant_info(self):
        engine = DrugRankingEngine()
        result = await engine.rank(
            gene_symbol="BRAF",
            evidence_items=[{"id": "ev-1", "drug_name": "DrugX", "evidence_level": "A",
                            "evidence_direction": "Supports", "_match_level": "exact_variant",
                            "source": "civic", "source_record_id": "1",
                            "retrieved_at": "2024-01-01T00:00:00"}],
            drug_interactions=[],
            evidence_snapshot_id="snap-001",
            git_commit="abc123",
        )
        assert result.evidence_snapshot_id == "snap-001"
        assert result.git_commit == "abc123"
        assert result.ranking_algorithm_version == "0.5.0"

