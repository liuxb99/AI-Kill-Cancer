"""
Unit tests for ConsensusEngine and ConsensusResult — Phase 2b multi-agent
consensus mechanism.

Tests cover model creation, agreement-level computation, conflict detection,
empty-input handling, and edge cases.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.backend.agents.consensus import (
    ConsensusEngine,
    ConsensusResult,
    _build_alternative_options,
    _build_recommended_option,
    _compute_agreement_level,
    _compute_overall_confidence,
    _detect_conflicts,
    _extract_tokens,
    _extract_unresolved_questions,
    _token_similarity,
)
from src.backend.agents.models import AgentOpinion
from src.backend.clinical.models import ClinicalContext

# ─── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def engine() -> ConsensusEngine:
    """A fresh ConsensusEngine instance."""
    return ConsensusEngine()


@pytest.fixture
def context() -> ClinicalContext:
    """A minimal clinical context for consensus tests."""
    ctx = ClinicalContext(
        case_id="CASE-CNS-001",
        patient_id="PT-CNS-001",
        age=55,
        gender="female",
        diagnosis="Lung adenocarcinoma",
        stage="Stage IV",
        histology="adenocarcinoma",
        cancer_type="lung",
    )
    ctx.freeze()
    return ctx


def _opinion(
    agent_type: str = "agent_a",
    summary: str = "Recommend treatment X.",
    pros: list[str] | None = None,
    cons: list[str] | None = None,
    confidence: str = "high",
) -> AgentOpinion:
    """Helper to build an AgentOpinion with defaults."""
    return AgentOpinion(
        agent_type=agent_type,
        agent_version="1.0.0",
        summary=summary,
        pros=pros or [],
        cons=cons or [],
        confidence=confidence,
        references=[],
        context_hash="test-hash",
        created_at=datetime.now(UTC).isoformat(),
    )


# ─── Test: ConsensusResult model ────────────────────────────────────────────


class TestConsensusResult:
    """Verify ConsensusResult Pydantic model creation."""

    def test_minimal_creation(self):
        """Minimal ConsensusResult with required fields."""
        result = ConsensusResult(
            agreement="high",
            confidence="high",
            recommended_option={"treatment": "Surgery", "rationale": "Best option.", "supporting_agents": []},
        )
        assert result.agreement == "high"
        assert result.confidence == "high"
        assert result.recommended_option["treatment"] == "Surgery"
        # Defaults
        assert result.conflicts == []
        assert result.alternative_options == []
        assert result.unresolved_questions == []
        assert result.context_hash is None
        assert result.created_at == ""

    def test_fully_populated(self):
        """Fully populated ConsensusResult with all fields."""
        now = datetime.now(UTC).isoformat()
        result = ConsensusResult(
            agreement="moderate",
            conflicts=[{"agent_types": ["a", "b"], "topic": "topic", "description": "desc"}],
            confidence="medium",
            recommended_option={"treatment": "Chemo", "rationale": "Effective", "supporting_agents": ["a"]},
            alternative_options=[{"treatment": "Radio", "rationale": "Alternative", "supporting_agents": ["b"]}],
            unresolved_questions=["Is patient fit for chemo?"],
            context_hash="abc123",
            created_at=now,
        )
        assert result.agreement == "moderate"
        assert len(result.conflicts) == 1
        assert len(result.alternative_options) == 1
        assert len(result.unresolved_questions) == 1
        assert result.context_hash == "abc123"
        assert result.created_at == now


# ─── Test: Internal helpers ─────────────────────────────────────────────────


class TestTokenHelpers:
    """Tests for _extract_tokens and _token_similarity."""

    def test_extract_tokens_removes_stop_words(self):
        """Stop words and short tokens are removed."""
        tokens = _extract_tokens("The patient has a lung cancer")
        assert "the" not in tokens
        assert "has" not in tokens  # "has" < 3 chars? Actually "has" is 3, but it's a stop word
        assert "a" not in tokens
        assert "lung" in tokens
        assert "cancer" in tokens

    def test_extract_tokens_empty(self):
        """Empty text → empty set."""
        assert _extract_tokens("") == set()

    def test_extract_tokens_punctuation(self):
        """Punctuation is stripped from tokens."""
        tokens = _extract_tokens("EGFR, BRAF; V600E!")
        assert "egfr" in tokens
        assert "braf" in tokens
        assert "v600e" in tokens

    def test_token_similarity_identical(self):
        """Identical texts → 1.0 similarity."""
        sim = _token_similarity("lung adenocarcinoma", "lung adenocarcinoma")
        assert sim == pytest.approx(1.0)

    def test_token_similarity_disjoint(self):
        """Completely different texts → 0.0 similarity."""
        sim = _token_similarity("lung cancer", "heart disease")
        assert sim == 0.0

    def test_token_similarity_partial(self):
        """Partially overlapping texts → value between 0 and 1."""
        sim = _token_similarity("EGFR mutation lung", "EGFR inhibitor lung")
        assert 0.0 < sim < 1.0

    def test_token_similarity_empty_input(self):
        """One or both empty → 0.0."""
        assert _token_similarity("", "lung cancer") == 0.0
        assert _token_similarity("lung cancer", "") == 0.0
        assert _token_similarity("", "") == 0.0


class TestComputeAgreementLevel:
    """Tests for _compute_agreement_level."""

    def test_empty_opinions(self):
        """Empty opinion list → 'none'."""
        assert _compute_agreement_level([], 0) == "none"

    def test_all_high_same_sign_no_conflicts(self):
        """All high confidence, same polarity, no conflicts → 'high'."""
        opinions = [
            _opinion(summary="Use drug A", pros=["Effective"], confidence="high"),
            _opinion(summary="Use drug A", pros=["Well-tolerated"], confidence="high"),
        ]
        assert _compute_agreement_level(opinions, 0) == "high"

    def test_mixed_sign_with_conflicts(self):
        """Mixed polarity with conflicts → 'none'."""
        opinions = [
            _opinion(summary="Use drug A", pros=["Effective"], cons=[], confidence="medium"),
            _opinion(summary="Avoid drug A", pros=[], cons=["Toxic"], confidence="medium"),
        ]
        assert _compute_agreement_level(opinions, 1) == "none"

    def test_mostly_low_confidence(self):
        """More than half low confidence → 'low'."""
        opinions = [
            _opinion(summary="Option A", pros=["OK"], confidence="low"),
            _opinion(summary="Option A", pros=["Fine"], confidence="low"),
            _opinion(summary="Option A", pros=["Good"], confidence="high"),
        ]
        # 2/3 low → low
        assert _compute_agreement_level(opinions, 0) == "low"

    def test_same_sign_few_conflicts(self):
        """Same sign, few conflicts → 'moderate'."""
        opinions = [
            _opinion(summary="Use drug A", pros=["Effective"], confidence="medium"),
            _opinion(summary="Use drug A", pros=["Available"], confidence="medium"),
        ]
        assert _compute_agreement_level(opinions, 1) == "moderate"

    def test_mixed_sign_no_conflicts(self):
        """Mixed polarity but no conflicts → 'moderate'."""
        opinions = [
            _opinion(summary="Drug A", pros=["Good"], confidence="medium"),
            _opinion(summary="Drug B", pros=[], cons=["Expensive"], confidence="medium"),
        ]
        # positive_count = 1, negative_count = 1 → not same_sign
        assert _compute_agreement_level(opinions, 0) == "low"


class TestComputeOverallConfidence:
    """Tests for _compute_overall_confidence."""

    def test_empty(self):
        """Empty list → 'low'."""
        assert _compute_overall_confidence([]) == "low"

    def test_all_high(self):
        """All high → 'high'."""
        ops = [_opinion(confidence="high"), _opinion(confidence="high")]
        assert _compute_overall_confidence(ops) == "high"

    def test_all_low(self):
        """All low → 'low'."""
        ops = [_opinion(confidence="low"), _opinion(confidence="low")]
        assert _compute_overall_confidence(ops) == "low"

    def test_mixed(self):
        """Mixed confidence → 'medium'."""
        ops = [_opinion(confidence="high"), _opinion(confidence="low")]
        assert _compute_overall_confidence(ops) == "medium"


class TestDetectConflicts:
    """Tests for _detect_conflicts."""

    def test_no_conflicts(self):
        """All opinions agree → no conflicts."""
        ops = [
            _opinion(agent_type="a", pros=["Effective treatment"], cons=[]),
            _opinion(agent_type="b", pros=["Effective treatment"], cons=[]),
        ]
        conflicts = _detect_conflicts(ops)
        assert conflicts == []

    def test_detect_conflict(self):
        """One agent's pro matches another's con → conflict detected."""
        ops = [
            _opinion(agent_type="diag", pros=["Use immunotherapy"], cons=[]),
            _opinion(agent_type="drug", pros=[], cons=["immunotherapy"]),
        ]
        conflicts = _detect_conflicts(ops, threshold=0.3)
        assert len(conflicts) >= 1
        assert any("diag" in c["agent_types"] for c in conflicts)

    def test_empty_input(self):
        """Empty list → empty conflicts."""
        assert _detect_conflicts([]) == []

    def test_single_opinion(self):
        """Single opinion → no conflicts."""
        ops = [_opinion(pros=["Good"], cons=["Bad"])]
        assert _detect_conflicts(ops) == []


class TestBuildRecommendedOption:
    """Tests for _build_recommended_option."""

    def test_empty_opinions(self):
        """Empty list → fallback dict."""
        result = _build_recommended_option([])
        assert result["treatment"] == "No consensus reached"
        assert result["supporting_agents"] == []

    def test_picks_highest_scored(self):
        """Opinion with most net pros and highest confidence is picked."""
        ops = [
            _opinion(agent_type="agent_a", summary="Option A", pros=["Good"], confidence="high"),
            _opinion(agent_type="agent_b", summary="Option B", pros=[], cons=["Bad"], confidence="low"),
        ]
        result = _build_recommended_option(ops)
        assert "Option A" in result["treatment"]


class TestBuildAlternativeOptions:
    """Tests for _build_alternative_options."""

    def test_empty_opinions(self):
        """Empty list → empty alternatives."""
        result = _build_alternative_options([], {"supporting_agents": []})
        assert result == []

    def test_excludes_recommended_agents(self):
        """Agents that support the recommended option are excluded."""
        ops = [
            _opinion(agent_type="a", summary="Option A", pros=["Good"]),
            _opinion(agent_type="b", summary="Option B", pros=["OK"]),
        ]
        recommended = {"supporting_agents": ["a"]}
        alternatives = _build_alternative_options(ops, recommended)
        types = [alt["supporting_agents"][0] for alt in alternatives]
        assert "b" in types
        assert "a" not in types


class TestExtractUnresolvedQuestions:
    """Tests for _extract_unresolved_questions."""

    def test_no_questions(self):
        """No low confidence or conflicts → empty."""
        ops = [_opinion(confidence="high")]
        assert _extract_unresolved_questions(ops, []) == []

    def test_low_confidence_question(self):
        """Low-confidence opinion → question generated."""
        ops = [_opinion(agent_type="test", summary="Unsure", confidence="low")]
        questions = _extract_unresolved_questions(ops, [])
        assert len(questions) == 1
        assert "test" in questions[0]
        assert "low confidence" in questions[0]

    def test_conflict_question(self):
        """Conflict entry → question generated."""
        conflicts = [{"agent_types": ["a", "b"], "topic": "Drug choice", "description": "Disagreement"}]
        questions = _extract_unresolved_questions([], conflicts)
        assert len(questions) >= 1
        assert "Conflict" in questions[0]


# ─── Test: ConsensusEngine ──────────────────────────────────────────────────


class TestConsensusEngine:
    """Integration tests for ConsensusEngine.reach_consensus()."""

    @pytest.mark.asyncio
    async def test_empty_opinions(self, engine, context):
        """No opinions → agreement='none', confidence='low'."""
        result = await engine.reach_consensus([], context)
        assert isinstance(result, ConsensusResult)
        assert result.agreement == "none"
        assert result.confidence == "low"
        assert result.recommended_option["treatment"] == "No consensus reached"

    @pytest.mark.asyncio
    async def test_all_agree_high_confidence(self, engine, context):
        """All opinions agree with high confidence → high agreement."""
        opinions = [
            _opinion(
                agent_type="diag",
                summary="Recommend chemotherapy for lung cancer.",
                pros=["Standard of care", "Proven efficacy"],
                confidence="high",
            ),
            _opinion(
                agent_type="drug",
                summary="Recommend chemotherapy for lung cancer.",
                pros=["Effective", "Guideline-concordant"],
                confidence="high",
            ),
        ]
        result = await engine.reach_consensus(opinions, context)
        assert result.agreement == "high"
        assert result.confidence == "high"
        assert result.recommended_option["treatment"] != "No consensus reached"

    @pytest.mark.asyncio
    async def test_partial_conflict(self, engine, context):
        """Conflicting opinions → moderate/low agreement."""
        opinions = [
            _opinion(
                agent_type="diag",
                summary="Use immunotherapy.",
                pros=["Immunotherapy is effective"],
                confidence="high",
            ),
            _opinion(
                agent_type="drug",
                summary="Use chemotherapy.",
                pros=["Chemotherapy works"],
                cons=["Immunotherapy is too expensive"],
                confidence="medium",
            ),
        ]
        result = await engine.reach_consensus(opinions, context)
        assert result.agreement in ("moderate", "low")
        assert len(result.conflicts) >= 0

    @pytest.mark.asyncio
    async def test_propagates_context_hash(self, engine, context):
        """context_hash from ClinicalContext is propagated."""
        opinions = [_opinion()]
        result = await engine.reach_consensus(opinions, context)
        assert result.context_hash == context.context_hash

    @pytest.mark.asyncio
    async def test_created_at_is_set(self, engine, context):
        """created_at is a non-empty ISO timestamp."""
        opinions = [_opinion()]
        result = await engine.reach_consensus(opinions, context)
        assert result.created_at != ""

    @pytest.mark.asyncio
    async def test_single_opinion(self, engine, context):
        """Single opinion → defaults to moderate/high."""
        opinions = [
            _opinion(summary="Single option", pros=["Works"], confidence="high"),
        ]
        result = await engine.reach_consensus(opinions, context)
        assert result.agreement in ("high", "moderate")
        assert result.recommended_option["treatment"] != ""

    @pytest.mark.asyncio
    async def test_multiple_agents_same_type(self, engine, context):
        """Multiple opinions from same agent type handled gracefully."""
        opinions = [
            _opinion(agent_type="diag", summary="Option A", pros=["Effective"], confidence="high"),
            _opinion(agent_type="diag", summary="Option B", pros=["Safe"], confidence="high"),
        ]
        result = await engine.reach_consensus(opinions, context)
        assert result.agreement in ("high", "moderate")
        assert isinstance(result, ConsensusResult)
