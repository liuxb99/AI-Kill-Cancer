"""
Tests for ExplainableEngine, CalculationTrace, and ReportGenerator (P3A-10).

Covers:
- ExplainableEngine.generate_explanations() for various scenarios
- ExplanationFormatter text/HTML output
- TraceManager CRUD operations
- ReportGenerator HTML generation
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest

from src.backend.clinical.calculation_trace import (
    CalculationTrace,
    TraceManager,
    TraceStep,
)
from src.backend.clinical.drug_ranking import (
    ConflictScore,
    DrugRankingEngine,
    DrugRankingResult,
    EvidenceScore,
    OverallScore,
    Resistance,
    Sensitivity,
)
from src.backend.clinical.explainable_recommendation import (
    ExplainableEngine,
    ExplanationFormatter,
    ReasonItem,
    RecommendationReason,
)
from src.backend.clinical.report_generator import ReportGenerator


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def drug_ranking_result_top() -> DrugRankingResult:
    """A DrugRankingResult simulating the #1 ranked drug."""
    return DrugRankingResult(
        drug_name="Osimertinib",
        overall_score=OverallScore(
            raw_score=0.7834,
            evidence_score_value=0.82,
            sensitivity_value=0.85,
            resistance_value=0.12,
            conflict_value=0.05,
        ),
        evidence_score=EvidenceScore(
            total_weighted_score=8.25,
            source_diversity=0.75,
            highest_tier="Tier_0",
            confidence_score=0.82,
        ),
        sensitivity=Sensitivity(
            score=0.85,
            supporting_item_count=8,
            total_item_count=12,
            details="Sensitivity for Osimertinib: 8/12 items supporting, weighted score = 0.8500.",
        ),
        resistance=Resistance(
            score=0.12,
            resistance_item_count=2,
            total_item_count=12,
            details="Resistance for Osimertinib: 2/12 items indicating resistance, weighted score = 0.1200.",
        ),
        conflict_score=ConflictScore(
            score=0.05,
            conflicting_pairs=1,
            total_items=12,
            details="Conflict analysis: 1 conflicting pair(s) among 12 items, score = 0.0500.",
        ),
        rank=1,
        details={
            "item_count": 12,
            "source_count": 4,
            "highest_weight": 3.5,
            "sources": ["COSMIC", "CIViC", "OncoKB", "ClinicalTrials.gov"],
        },
    )


@pytest.fixture
def drug_ranking_result_second() -> DrugRankingResult:
    """A DrugRankingResult simulating the #2 ranked drug."""
    return DrugRankingResult(
        drug_name="Pembrolizumab",
        overall_score=OverallScore(
            raw_score=0.5210,
            evidence_score_value=0.55,
            sensitivity_value=0.60,
            resistance_value=0.30,
            conflict_value=0.15,
        ),
        evidence_score=EvidenceScore(
            total_weighted_score=4.5,
            source_diversity=0.50,
            highest_tier="Tier_1",
            confidence_score=0.55,
        ),
        sensitivity=Sensitivity(
            score=0.60,
            supporting_item_count=4,
            total_item_count=6,
            details="Sensitivity for Pembrolizumab: 4/6 items supporting, weighted score = 0.6000.",
        ),
        resistance=Resistance(
            score=0.30,
            resistance_item_count=2,
            total_item_count=6,
            details="Resistance for Pembrolizumab: 2/6 items indicating resistance, weighted score = 0.3000.",
        ),
        conflict_score=ConflictScore(
            score=0.15,
            conflicting_pairs=1,
            total_items=6,
            details="Conflict analysis: 1 conflicting pair(s) among 6 items, score = 0.1500.",
        ),
        rank=2,
        details={
            "item_count": 6,
            "source_count": 3,
            "highest_weight": 2.0,
            "sources": ["CIViC", "OncoKB", "PubMed"],
        },
    )


@pytest.fixture
def ranking_results(
    drug_ranking_result_top,
    drug_ranking_result_second,
) -> list[DrugRankingResult]:
    """Two ranked drugs for explainable engine testing."""
    return [drug_ranking_result_top, drug_ranking_result_second]


@pytest.fixture
def aggregated_data() -> dict[str, Any]:
    """Simulated aggregated evidence data for two drugs."""
    return {
        "Osimertinib": {
            "evidence_scores": [
                {"weight": 1.0, "source": "OncoKB", "tier": "Level 1", "direction": "supporting",
                 "clinical_significance": "sensitivity", "conflict_status": "", "source_record_id": "onc-001"},
                {"weight": 0.85, "source": "CIViC", "tier": "A", "direction": "supporting",
                 "clinical_significance": "sensitivity", "conflict_status": "", "source_record_id": "civ-001"},
                {"weight": 0.80, "source": "COSMIC", "tier": "Level R1", "direction": "supporting",
                 "clinical_significance": "sensitivity", "conflict_status": "", "source_record_id": "cos-001"},
            ],
            "total_weight": 2.65,
            "source_count": 3,
            "item_count": 3,
            "highest_weight": 1.0,
            "sources": {"OncoKB", "CIViC", "COSMIC"},
            "directions": {"supporting"},
        },
        "Pembrolizumab": {
            "evidence_scores": [
                {"weight": 0.85, "source": "NCCN", "tier": "Category 2A", "direction": "supporting",
                 "clinical_significance": "sensitivity", "conflict_status": ""},
                {"weight": 0.65, "source": "CIViC", "tier": "C", "direction": "resistance",
                 "clinical_significance": "resistance", "conflict_status": "conflicting"},
            ],
            "total_weight": 1.50,
            "source_count": 2,
            "item_count": 2,
            "highest_weight": 0.85,
            "sources": {"NCCN", "CIViC"},
            "directions": {"supporting", "resistance"},
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ExplainableEngine Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestExplainableEngine:
    """Test the explainable recommendation engine."""

    def test_generate_explanations(self, ranking_results, aggregated_data):
        """generate_explanations produces one RecommendationReason per drug."""
        engine = ExplainableEngine(aggregated_data=aggregated_data)
        explanations = engine.generate_explanations(ranking_results)
        assert len(explanations) == 2
        assert all(isinstance(e, RecommendationReason) for e in explanations)

    def test_first_drug_explanation(self, ranking_results, aggregated_data):
        """Top-ranked drug should have rank-specific reasons."""
        engine = ExplainableEngine(aggregated_data=aggregated_data)
        explanations = engine.generate_explanations(ranking_results)
        top = explanations[0]
        assert top.drug_name == "Osimertinib"
        assert top.rank == 1
        assert top.overall_score == 0.7834
        assert len(top.reasons) > 0

        # Should contain rank context about leading #2
        rank_reasons = [r for r in top.reasons if r.category == "rule"]
        rank_texts = " ".join(r.detail for r in rank_reasons)
        assert "leads" in rank_texts or "#1" in rank_texts

    def test_second_drug_explanation(self, ranking_results, aggregated_data):
        """Second-ranked drug should mention trailing the top."""
        engine = ExplainableEngine(aggregated_data=aggregated_data)
        explanations = engine.generate_explanations(ranking_results)
        second = explanations[1]
        assert second.drug_name == "Pembrolizumab"
        assert second.rank == 2
        rank_reasons = [r for r in second.reasons if r.category == "rule"]
        rank_texts = " ".join(r.detail for r in rank_reasons)
        assert "trails" in rank_texts or "#2" in rank_texts

    def test_explanations_include_evidence_support(self, ranking_results, aggregated_data):
        """Explanations should include evidence_support reasons."""
        engine = ExplainableEngine(aggregated_data=aggregated_data)
        explanations = engine.generate_explanations(ranking_results)
        for expl in explanations:
            cats = {r.category for r in expl.reasons}
            assert "evidence_support" in cats

    def test_explanations_include_sensitivity(self, ranking_results, aggregated_data):
        """Explanations should include sensitivity reasons."""
        engine = ExplainableEngine(aggregated_data=aggregated_data)
        explanations = engine.generate_explanations(ranking_results)
        for expl in explanations:
            cats = {r.category for r in expl.reasons}
            assert "sensitivity" in cats

    def test_explanations_include_resistance(self, ranking_results, aggregated_data):
        """Explanations should include resistance reasons."""
        engine = ExplainableEngine(aggregated_data=aggregated_data)
        explanations = engine.generate_explanations(ranking_results)
        for expl in explanations:
            cats = {r.category for r in expl.reasons}
            assert "resistance" in cats

    def test_explanations_include_conflict(self, ranking_results, aggregated_data):
        """Explanations should include conflict reasons."""
        engine = ExplainableEngine(aggregated_data=aggregated_data)
        explanations = engine.generate_explanations(ranking_results)
        for expl in explanations:
            cats = {r.category for r in expl.reasons}
            assert "conflict" in cats

    def test_explanations_with_resistance_evidence(self, drug_ranking_result_second, aggregated_data):
        """Drug with resistance evidence should have penalty reasons."""
        engine = ExplainableEngine(aggregated_data=aggregated_data)
        explanations = engine.generate_explanations([drug_ranking_result_second])
        expl = explanations[0]
        resistance_reasons = [r for r in expl.reasons if r.category == "resistance"]
        # Resistance score > 0 so resistance reasons should have negative impact
        negative_impacts = [r for r in resistance_reasons if r.score_impact < 0]
        assert len(negative_impacts) >= 1

    def test_explanations_no_resistance(self, drug_ranking_result_top, aggregated_data):
        """Drug without resistance should have 'No resistance' reason."""
        # Modify resistance score to 0
        top = drug_ranking_result_top
        top.resistance.score = 0.0
        top.resistance.resistance_item_count = 0
        engine = ExplainableEngine(aggregated_data=aggregated_data)
        explanations = engine.generate_explanations([top])
        expl = explanations[0]
        resistance_texts = " ".join(r.detail for r in expl.reasons if r.category == "resistance")
        assert "No resistance" in resistance_texts

    def test_explanations_with_conflict_evidence(self, drug_ranking_result_second, aggregated_data):
        """Drug with conflict evidence should have conflict reasons."""
        engine = ExplainableEngine(aggregated_data=aggregated_data)
        explanations = engine.generate_explanations([drug_ranking_result_second])
        expl = explanations[0]
        conflict_reasons = [r for r in expl.reasons if r.category == "conflict"]
        assert len(conflict_reasons) > 0

    def test_explanations_reasons_sorted_by_impact(self, ranking_results, aggregated_data):
        """Reasons should be sorted by absolute score_impact descending."""
        engine = ExplainableEngine(aggregated_data=aggregated_data)
        explanations = engine.generate_explanations(ranking_results)
        for expl in explanations:
            impacts = [abs(r.score_impact) for r in expl.reasons]
            assert impacts == sorted(impacts, reverse=True)

    def test_explanations_with_ranking_engine(self, ranking_results, aggregated_data):
        """Providing a ranking engine should pass its config weights."""
        ranking_engine = DrugRankingEngine(
            evidence_weight=0.5,
            sensitivity_weight=0.3,
            resistance_penalty=0.1,
            conflict_penalty=0.1,
        )
        engine = ExplainableEngine(
            ranking_engine=ranking_engine,
            aggregated_data=aggregated_data,
        )
        explanations = engine.generate_explanations(ranking_results)
        expl = explanations[0]
        # Check that custom weights appear in the breakdown
        rule_reasons = [r for r in expl.reasons if r.category == "rule"]
        breakdown_text = " ".join(r.detail for r in rule_reasons)
        assert "×0.5" in breakdown_text or "×0.3" in breakdown_text or "×-0.1" in breakdown_text

    def test_top_drug_has_rank_context_comparison(self, ranking_results, aggregated_data):
        """Top-ranked drug should compare with the second place."""
        engine = ExplainableEngine(aggregated_data=aggregated_data)
        explanations = engine.generate_explanations(ranking_results)
        top = explanations[0]
        rank_reasons = [r for r in top.reasons if r.category == "rule"]
        diff_text = " ".join(r.detail for r in rank_reasons)
        assert "leads" in diff_text
        assert "Pembrolizumab" in diff_text

    def test_reason_item_creation(self):
        """ReasonItem should be created with correct fields."""
        item = ReasonItem(
            category="evidence_support",
            detail="Test reason detail.",
            source="TestSource",
            score_impact=0.5,
            trace_id="trace-001",
        )
        assert item.category == "evidence_support"
        assert item.detail == "Test reason detail."
        assert item.source == "TestSource"
        assert item.score_impact == 0.5
        assert item.trace_id == "trace-001"

    def test_recommendation_reason_creation(self):
        """RecommendationReason should aggregate reasons."""
        reason = RecommendationReason(
            drug_name="TestDrug",
            rank=1,
            overall_score=0.75,
            reasons=[
                ReasonItem(category="evidence_support", detail="Good evidence.", source="Src", score_impact=0.3),
            ],
        )
        assert reason.drug_name == "TestDrug"
        assert len(reason.reasons) == 1
        assert reason.overall_score == 0.75


# ═══════════════════════════════════════════════════════════════════════════════
# ExplanationFormatter Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestExplanationFormatter:
    """Test the ExplanationFormatter output."""

    def test_format_text(self, ranking_results, aggregated_data):
        """format_text should produce multi-line plain text."""
        engine = ExplainableEngine(aggregated_data=aggregated_data)
        explanations = engine.generate_explanations(ranking_results)
        formatter = ExplanationFormatter()
        text = formatter.format_text(explanations[0])
        assert isinstance(text, str)
        assert len(text) > 50
        assert "Drug:" in text
        assert "Rank:" in text
        assert "Overall Score:" in text
        assert "Explanation:" in text

    def test_format_text_contains_reasons(self, ranking_results, aggregated_data):
        """format_text should include reason details."""
        engine = ExplainableEngine(aggregated_data=aggregated_data)
        explanations = engine.generate_explanations(ranking_results)
        formatter = ExplanationFormatter()
        text = formatter.format_text(explanations[0])
        assert "evidence_support" in text or "sensitivity" in text

    def test_format_html(self, ranking_results, aggregated_data):
        """format_html should produce an HTML fragment."""
        engine = ExplainableEngine(aggregated_data=aggregated_data)
        explanations = engine.generate_explanations(ranking_results)
        formatter = ExplanationFormatter()
        html = formatter.format_html(explanations[0])
        assert isinstance(html, str)
        assert "<div" in html
        assert "recommendation-reason" in html
        assert "Osimertinib" in html

    def test_format_html_structure(self, ranking_results, aggregated_data):
        """HTML output should contain structural elements."""
        engine = ExplainableEngine(aggregated_data=aggregated_data)
        explanations = engine.generate_explanations(ranking_results)
        formatter = ExplanationFormatter()
        html = formatter.format_html(explanations[0])
        assert '<h3 class="drug-name">' in html
        assert 'class="rank-info"' in html
        assert 'class="reasons-list"' in html

    def test_format_text_with_trace_id(self):
        """format_text should include trace_id when present."""
        reason = RecommendationReason(
            drug_name="TestDrug",
            rank=1,
            overall_score=0.5,
            reasons=[
                ReasonItem(
                    category="evidence_support",
                    detail="Item with trace.",
                    source="Src",
                    score_impact=0.2,
                    trace_id="trc-123",
                ),
            ],
        )
        formatter = ExplanationFormatter()
        text = formatter.format_text(reason)
        assert "[trace: trc-123]" in text

    def test_format_html_with_trace_id(self):
        """format_html should include trace_id span when present."""
        reason = RecommendationReason(
            drug_name="TestDrug",
            rank=1,
            overall_score=0.5,
            reasons=[
                ReasonItem(
                    category="evidence_support",
                    detail="Item with trace.",
                    source="Src",
                    score_impact=0.2,
                    trace_id="trc-456",
                ),
            ],
        )
        formatter = ExplanationFormatter()
        html = formatter.format_html(reason)
        assert "trace-id" in html
        assert "trc-456" in html


# ═══════════════════════════════════════════════════════════════════════════════
# CalculationTrace / TraceManager Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestTraceManager:
    """Test TraceManager CRUD operations."""

    def setup_method(self):
        self.manager = TraceManager()

    def test_start_trace(self):
        """start_trace should create a new trace with status 'running'."""
        trace = self.manager.start_trace(patient_id="P-001")
        assert trace is not None
        assert trace.trace_id is not None
        assert trace.patient_id == "P-001"
        assert trace.status == "running"
        assert trace.started_at is not None
        assert trace.completed_at is None
        assert trace.steps == []

    def test_start_trace_with_custom_id(self):
        """start_trace should accept a custom trace_id."""
        trace = self.manager.start_trace(patient_id="P-002", trace_id="my-custom-id")
        assert trace.trace_id == "my-custom-id"

    def test_add_step(self):
        """add_step should append a step to the trace."""
        trace = self.manager.start_trace(patient_id="P-001")
        step = TraceStep(
            step_name="collect_evidence",
            step_type="input",
            input_data={"variant_count": 5},
            output_data={},
        )
        self.manager.add_step(trace.trace_id, step)
        updated = self.manager.get_trace(trace.trace_id)
        assert updated is not None
        assert len(updated.steps) == 1
        assert updated.steps[0].step_name == "collect_evidence"
        assert updated.steps[0].input_data == {"variant_count": 5}

    def test_add_step_to_completed_trace_raises(self):
        """Adding a step to a completed trace should raise ValueError."""
        trace = self.manager.start_trace(patient_id="P-001")
        self.manager.complete_trace(trace.trace_id)
        step = TraceStep(step_name="late_step", step_type="output")
        with pytest.raises(ValueError, match="must be 'running'"):
            self.manager.add_step(trace.trace_id, step)

    def test_add_step_to_nonexistent_trace_raises(self):
        """Adding a step to a non-existent trace should raise KeyError."""
        step = TraceStep(step_name="ghost", step_type="output")
        with pytest.raises(KeyError, match="not found"):
            self.manager.add_step("nonexistent", step)

    def test_complete_trace(self):
        """complete_trace should mark the trace as completed."""
        trace = self.manager.start_trace(patient_id="P-001")
        completed = self.manager.complete_trace(trace.trace_id)
        assert completed.status == "completed"
        assert completed.completed_at is not None
        assert completed.completed_at >= completed.started_at

    def test_complete_trace_failed(self):
        """complete_trace with status='failed' should work."""
        trace = self.manager.start_trace(patient_id="P-001")
        completed = self.manager.complete_trace(trace.trace_id, status="failed")
        assert completed.status == "failed"
        assert completed.completed_at is not None

    def test_complete_trace_nonexistent_raises(self):
        """Completing a non-existent trace should raise KeyError."""
        with pytest.raises(KeyError):
            self.manager.complete_trace("nonexistent")

    def test_complete_trace_already_completed_raises(self):
        """Completing an already-completed trace should raise ValueError."""
        trace = self.manager.start_trace(patient_id="P-001")
        self.manager.complete_trace(trace.trace_id)
        with pytest.raises(ValueError, match="must be 'running'"):
            self.manager.complete_trace(trace.trace_id)

    def test_complete_trace_invalid_status_raises(self):
        """Using an invalid final status should raise ValueError."""
        trace = self.manager.start_trace(patient_id="P-001")
        with pytest.raises(ValueError, match="Invalid final status"):
            self.manager.complete_trace(trace.trace_id, status="invalid_status")

    def test_get_trace(self):
        """get_trace should return the trace object."""
        trace = self.manager.start_trace(patient_id="P-001")
        retrieved = self.manager.get_trace(trace.trace_id)
        assert retrieved is trace

    def test_get_trace_nonexistent(self):
        """get_trace for non-existent ID should return None."""
        assert self.manager.get_trace("nonexistent") is None

    def test_list_traces_empty(self):
        """list_traces on empty manager returns empty list."""
        assert self.manager.list_traces() == []

    def test_list_traces_all(self):
        """list_traces should return all traces, newest first."""
        self.manager.start_trace(patient_id="P-001")
        self.manager.start_trace(patient_id="P-002")
        traces = self.manager.list_traces()
        assert len(traces) == 2

    def test_list_traces_filter_by_patient(self):
        """list_traces should filter by patient_id."""
        self.manager.start_trace(patient_id="P-001")
        self.manager.start_trace(patient_id="P-002")
        traces = self.manager.list_traces(patient_id="P-001")
        assert len(traces) == 1
        assert traces[0].patient_id == "P-001"

    def test_list_traces_filter_by_status(self):
        """list_traces should filter by status."""
        t1 = self.manager.start_trace(patient_id="P-001")
        self.manager.complete_trace(t1.trace_id)
        self.manager.start_trace(patient_id="P-002")
        completed = self.manager.list_traces(status="completed")
        running = self.manager.list_traces(status="running")
        assert len(completed) == 1
        assert len(running) == 1

    def test_clear(self):
        """clear should remove all traces."""
        self.manager.start_trace(patient_id="P-001")
        self.manager.clear()
        assert self.manager.list_traces() == []

    def test_multiple_steps(self):
        """Multiple steps should be recorded in order."""
        trace = self.manager.start_trace(patient_id="P-001")
        steps_data = [
            ("collect", "input", {"vars": 3}),
            ("aggregate", "evidence", {"drugs": 2}),
            ("rank", "score", {"ranked": 2}),
        ]
        for name, stype, inp in steps_data:
            self.manager.add_step(
                trace.trace_id,
                TraceStep(step_name=name, step_type=stype, input_data=inp),
            )
        updated = self.manager.get_trace(trace.trace_id)
        assert len(updated.steps) == 3
        for i, (name, stype, inp) in enumerate(steps_data):
            assert updated.steps[i].step_name == name
            assert updated.steps[i].step_type == stype
            assert updated.steps[i].input_data == inp

    def test_trace_step_timestamp(self):
        """TraceStep should have an auto-generated timestamp."""
        step = TraceStep(step_name="test", step_type="output")
        assert step.timestamp is not None
        assert isinstance(step.timestamp, datetime)

    def test_trace_total_duration_ms(self):
        """total_duration_ms should reflect completed duration."""
        trace = self.manager.start_trace(patient_id="P-001")
        assert trace.total_duration_ms == 0.0
        self.manager.complete_trace(trace.trace_id)
        completed = self.manager.get_trace(trace.trace_id)
        assert completed.total_duration_ms >= 0.0

    def test_trace_step_count(self):
        """step_count should return the number of steps."""
        trace = self.manager.start_trace(patient_id="P-001")
        assert trace.step_count == 0
        self.manager.add_step(trace.trace_id, TraceStep(step_name="s1", step_type="input"))
        assert trace.step_count == 1

    def test_trace_step_with_parent_trace_id(self):
        """TraceStep should accept an optional parent_trace_id."""
        step = TraceStep(
            step_name="child_step",
            step_type="score",
            parent_trace_id="parent-001",
        )
        assert step.parent_trace_id == "parent-001"
        assert step.step_name == "child_step"

    def test_trace_step_with_duration_ms(self):
        """TraceStep should accept an optional duration_ms."""
        step = TraceStep(
            step_name="timed_step",
            step_type="evidence",
            duration_ms=150.5,
        )
        assert step.duration_ms == 150.5


# ═══════════════════════════════════════════════════════════════════════════════
# ReportGenerator Tests
# ═══════════════════════════════════════════════════════════════════════════════


# We need a minimal mock of RecommendationResponse and RecommendationDrugItem
# to avoid requiring the full API import chain


@pytest.fixture
def mock_recommendation_response():
    """Create a minimal mock of RecommendationResponse for report testing."""
    from pydantic import BaseModel, Field

    class MockDrugItem(BaseModel):
        drug_name: str
        rank: int
        overall_score: float
        evidence_score: float = 0.0
        sensitivity_score: float = 0.0
        resistance_score: float = 0.0
        conflict_score: float = 0.0
        explanations: list[dict] = []

    class MockResponse(BaseModel):
        recommendation_id: str = "rec-001"
        patient_id: str = "P-001"
        recommendations: list[MockDrugItem] = []
        trace_id: str = "trace-001"
        engine_version: str = "1.0.0"
        created_at: str = "2025-06-18T14:30:00Z"
        report_html: str | None = None

    return MockResponse(
        recommendations=[
            MockDrugItem(
                drug_name="Osimertinib",
                rank=1,
                overall_score=0.7834,
                evidence_score=0.82,
                sensitivity_score=0.85,
                resistance_score=0.12,
                conflict_score=0.05,
                explanations=[
                    {"category": "evidence_support", "detail": "Strong evidence from multiple sources.",
                     "source": "EvidenceAggregator", "score_impact": 0.328},
                    {"category": "sensitivity", "detail": "High sensitivity score.",
                     "source": "DrugRankingEngine", "score_impact": 0.2975},
                    {"category": "resistance", "detail": "Low resistance detected.",
                     "source": "DrugRankingEngine", "score_impact": -0.018},
                    {"category": "conflict", "detail": "No conflicting evidence.",
                     "source": "DrugRankingEngine", "score_impact": 0.0},
                ],
            ),
            MockDrugItem(
                drug_name="Pembrolizumab",
                rank=2,
                overall_score=0.5210,
                evidence_score=0.55,
                sensitivity_score=0.60,
                resistance_score=0.30,
                conflict_score=0.15,
                explanations=[
                    {"category": "evidence_support", "detail": "Moderate evidence.",
                     "source": "EvidenceAggregator", "score_impact": 0.22},
                ],
            ),
        ],
    )


class TestReportGenerator:
    """Test the HTML ReportGenerator."""

    def test_generate_returns_html(self, mock_recommendation_response):
        """generate should return a non-empty HTML string."""
        generator = ReportGenerator()
        html = generator.generate(
            mock_recommendation_response,
            variants=["EGFR L858R"],
            evidence_count=8,
            rules_evaluated=5,
            rules_fired=3,
            trace_steps=[
                {"step_name": "collect", "step_type": "input",
                 "input_data": {"variants": 1}, "output_data": {"items": 8}},
            ],
        )
        assert isinstance(html, str)
        assert len(html) > 100

    def test_generate_contains_required_sections(self, mock_recommendation_response):
        """HTML should contain all required sections."""
        generator = ReportGenerator()
        html = generator.generate(
            mock_recommendation_response,
            variants=["EGFR L858R"],
            evidence_count=8,
            rules_evaluated=5,
            rules_fired=3,
        )
        assert "Patient Info" in html or "patient-info" in html
        assert "Evidence Summary" in html or "evidence-summary" in html
        assert "Top Drug Rankings" in html or "ranking-table" in html
        assert "Reason Breakdown" in html or "reason-breakdown" in html
        assert "Calculation Trace" in html or "trace-details" in html
        assert "Disclaimer" in html or "disclaimer" in html

    def test_generate_with_warnings(self, mock_recommendation_response):
        """HTML with high resistance should include warnings section."""
        mock_recommendation_response.recommendations[0].resistance_score = 0.6
        generator = ReportGenerator()
        html = generator.generate(
            mock_recommendation_response,
            variants=["EGFR L858R"],
            evidence_count=8,
        )
        assert "Warnings" in html or "warning" in html

    def test_generate_without_warnings(self, mock_recommendation_response):
        """HTML with no warnings should omit the warnings section."""
        mock_recommendation_response.recommendations[0].resistance_score = 0.0
        mock_recommendation_response.recommendations[0].conflict_score = 0.0
        mock_recommendation_response.recommendations[0].explanations = []
        mock_recommendation_response.recommendations[1].resistance_score = 0.0
        mock_recommendation_response.recommendations[1].conflict_score = 0.0
        mock_recommendation_response.recommendations[1].explanations = []
        generator = ReportGenerator()
        html = generator.generate(
            mock_recommendation_response,
            variants=["EGFR L858R"],
            evidence_count=8,
        )
        # Warnings section should be empty or absent when no warnings
        assert 'class="warning-list"' not in html

    def test_generate_without_variants(self, mock_recommendation_response):
        """generate should handle empty variants list."""
        generator = ReportGenerator()
        html = generator.generate(
            mock_recommendation_response,
            variants=[],
            evidence_count=0,
        )
        assert isinstance(html, str)
        assert len(html) > 100

    def test_generate_without_trace_steps(self, mock_recommendation_response):
        """generate should handle missing trace steps."""
        generator = ReportGenerator()
        html = generator.generate(
            mock_recommendation_response,
            variants=["EGFR L858R"],
            evidence_count=5,
        )
        assert isinstance(html, str)
        assert "Calculation Trace" in html

    def test_generate_contains_drug_names(self, mock_recommendation_response):
        """HTML should contain the drug names."""
        generator = ReportGenerator()
        html = generator.generate(
            mock_recommendation_response,
            variants=["EGFR L858R"],
            evidence_count=5,
        )
        assert "Osimertinib" in html
        assert "Pembrolizumab" in html

    def test_generate_contains_scores(self, mock_recommendation_response):
        """HTML should contain the numeric scores."""
        generator = ReportGenerator()
        html = generator.generate(
            mock_recommendation_response,
            variants=["EGFR L858R"],
            evidence_count=5,
        )
        assert "0.7834" in html or "0.78" in html

    def test_generate_contains_engine_version(self, mock_recommendation_response):
        """HTML should include the engine version."""
        generator = ReportGenerator()
        html = generator.generate(
            mock_recommendation_response,
            variants=["EGFR L858R"],
            evidence_count=5,
        )
        assert "1.0.0" in html

    def test_generate_rank1_highlight(self, mock_recommendation_response):
        """Rank 1 drug should have a special CSS class."""
        generator = ReportGenerator()
        html = generator.generate(
            mock_recommendation_response,
            variants=["EGFR L858R"],
            evidence_count=5,
        )
        assert "rank-1" in html

    def test_generate_reason_breakdown(self, mock_recommendation_response):
        """HTML should include reason breakdown groups."""
        generator = ReportGenerator()
        html = generator.generate(
            mock_recommendation_response,
            variants=["EGFR L858R"],
            evidence_count=5,
        )
        assert "reason-group" in html

    def test_format_trace_data(self):
        """_format_trace_data should format dicts compactly."""
        data = {"variants": 3, "status": "ok", "drugs": ["A", "B"]}
        result = ReportGenerator._format_trace_data(data)
        assert "variants: 3" in result
        assert "status: ok" in result

    def test_format_trace_data_empty(self):
        """_format_trace_data should return empty string for empty dict."""
        assert ReportGenerator._format_trace_data({}) == ""

    def test_score_class(self):
        """_score_class should return correct CSS class."""
        assert ReportGenerator._score_class(0.1) == "score-positive"
        assert ReportGenerator._score_class(-0.1) == "score-negative"
        assert ReportGenerator._score_class(0.0) == "score-neutral"
        assert ReportGenerator._score_class(0.05) == "score-neutral"  # boundary
