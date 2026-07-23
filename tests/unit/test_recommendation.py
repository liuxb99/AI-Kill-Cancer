"""
Unit tests for RecommendationGenerator and TreatmentRecommendation —
Phase 2b clinical recommendation generation.

Tests cover model creation, the generate() method with consensus input,
edge cases (empty consensus, missing data), and output format validation
(JSON structure, Markdown content).
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.backend.agents.consensus import ConsensusResult
from src.backend.clinical.evidence_models import EvidenceBundle, EvidenceItem
from src.backend.clinical.models import ClinicalContext
from src.backend.clinical.recommendation import (
    RecommendationGenerator,
    TreatmentRecommendation,
)

# ─── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def generator() -> RecommendationGenerator:
    """A fresh RecommendationGenerator instance."""
    return RecommendationGenerator()


@pytest.fixture
def context() -> ClinicalContext:
    """A minimal clinical context for recommendation tests."""
    ctx = ClinicalContext(
        case_id="CASE-REC-001",
        patient_id="PT-REC-001",
        age=60,
        gender="male",
        diagnosis="Lung adenocarcinoma",
        stage="Stage IV",
        histology="adenocarcinoma",
        cancer_type="lung",
    )
    ctx.freeze()
    return ctx


@pytest.fixture
def evidence_bundle() -> EvidenceBundle:
    """An empty evidence bundle."""
    return EvidenceBundle()


@pytest.fixture
def sample_evidence() -> EvidenceBundle:
    """A sample evidence bundle with a trial-related item."""
    return EvidenceBundle(items=[
        EvidenceItem(
            source="ClinicalTrials.gov",
            source_record_id="NCT04244447",
            gene_symbol="EGFR",
            drug_name="Osimertinib",
            disease="Non-small cell lung cancer",
            evidence_type="predictive",
            evidence_level="B",
            description="Phase 3 trial of osimertinib in EGFR-mutated NSCLC",
            citation="NCT04244447",
            url="https://clinicaltrials.gov/ct2/show/NCT04244447",
        ),
        EvidenceItem(
            source="NCCN",
            gene_symbol="EGFR",
            drug_name="Osimertinib",
            evidence_type="predictive",
            evidence_direction="supporting",
            evidence_level="A",
            description="NCCN guideline recommends osimertinib for EGFR-mutated NSCLC",
            citation="NCCN NSCLC v5.2024",
        ),
    ])


def _consensus_result(
    agreement: str = "high",
    confidence: str = "high",
    treatment: str = "Osimertinib",
    rationale: str = "Effective targeted therapy for EGFR mutation.",
    supporting_agents: list[str] | None = None,
    conflicts: list[dict] | None = None,
    alternatives: list[dict] | None = None,
    questions: list[str] | None = None,
) -> ConsensusResult:
    """Helper to build a ConsensusResult with defaults."""
    return ConsensusResult(
        agreement=agreement,
        conflicts=conflicts or [],
        confidence=confidence,
        recommended_option={
            "treatment": treatment,
            "rationale": rationale,
            "supporting_agents": supporting_agents or ["drug"],
        },
        alternative_options=alternatives or [],
        unresolved_questions=questions or [],
        context_hash="test-hash-rec",
        created_at=datetime.now(UTC).isoformat(),
    )


# ─── Test: TreatmentRecommendation model ────────────────────────────────────


class TestTreatmentRecommendation:
    """Verify TreatmentRecommendation Pydantic model creation."""

    def test_minimal_creation(self):
        """Minimal TreatmentRecommendation with required fields."""
        rec = TreatmentRecommendation(
            first_line={"treatment": "Drug A", "rationale": "Effective", "drugs": [], "supporting_agents": []},
            second_line={"treatment": "Drug B", "rationale": "Alternative", "drugs": [], "supporting_agents": []},
            clinical_trial={"trials": [], "recommendation": "None", "reasoning": "N/A"},
            expected_benefit={"summary": "Good", "benefits": [], "magnitude": "high", "confidence": "high"},
            potential_risk={"summary": "Low", "risks": [], "severity": "low", "confidence": "high"},
            monitoring_plan={"summary": "Standard", "actions": [], "frequency": "weekly", "duration": "3 months"},
            structured_json={},
            markdown="# Report",
        )
        assert rec.first_line["treatment"] == "Drug A"
        assert rec.markdown == "# Report"
        assert rec.context_hash is None
        assert rec.created_at == ""

    def test_fully_populated(self):
        """Fully populated TreatmentRecommendation with all fields."""
        now = datetime.now(UTC).isoformat()
        rec = TreatmentRecommendation(
            first_line={"treatment": "Osimertinib", "rationale": "EGFR targeted", "drugs": [{"name": "Osimertinib"}], "supporting_agents": ["drug"]},
            second_line={"treatment": "Chemotherapy", "rationale": "Alternative", "drugs": [{"name": "Cisplatin"}], "supporting_agents": ["diag"]},
            clinical_trial={"trials": [{"nct_id": "NCT04244447"}], "recommendation": "Consider trial", "reasoning": "Eligibility"},
            supporting_evidence=[{"source": "NCCN", "evidence_level": "A", "description": "Guideline"}],
            expected_benefit={"summary": "Significant", "benefits": ["PFS benefit"], "magnitude": "significant", "confidence": "high"},
            potential_risk={"summary": "Manageable", "risks": [{"topic": "Rash", "severity": "mild"}], "severity": "moderate", "confidence": "medium"},
            monitoring_plan={"summary": "Monthly follow-up", "actions": [{"action": "CBC", "frequency": "monthly"}], "frequency": "monthly", "duration": "6 months"},
            structured_json={"key": "value"},
            markdown="# Full Report\n\nDetail.",
            context_hash="abc123",
            created_at=now,
        )
        assert rec.structured_json["key"] == "value"
        assert "Full Report" in rec.markdown
        assert rec.context_hash == "abc123"


# ─── Test: RecommendationGenerator.generate() ───────────────────────────────


class TestRecommendationGenerator:
    """Tests for RecommendationGenerator.generate()."""

    @pytest.mark.asyncio
    async def test_basic_generate(self, generator, context, sample_evidence):
        """Basic generate with valid consensus and evidence → valid TreatmentRecommendation."""
        consensus = _consensus_result()
        rec = await generator.generate(consensus, context, sample_evidence)

        assert isinstance(rec, TreatmentRecommendation)
        assert rec.first_line["treatment"] == "Osimertinib"
        assert rec.created_at != ""

    @pytest.mark.asyncio
    async def test_generate_with_empty_consensus(self, generator, context, evidence_bundle):
        """Empty consensus (no agreement) → fallback values in output."""
        consensus = _consensus_result(
            agreement="none",
            confidence="low",
            treatment="No consensus reached",
            rationale="No agent opinions were provided.",
        )
        rec = await generator.generate(consensus, context, evidence_bundle)

        assert isinstance(rec, TreatmentRecommendation)
        assert rec.first_line["treatment"] == "No consensus reached"
        assert rec.structured_json is not None
        assert len(rec.markdown) > 0

    @pytest.mark.asyncio
    async def test_generate_with_conflicts(self, generator, context, evidence_bundle):
        """Consensus with conflicts → risks section populated from conflicts."""
        consensus = _consensus_result(
            agreement="low",
            confidence="medium",
            conflicts=[
                {
                    "agent_types": ["diag", "drug"],
                    "topic": "Immunotherapy vs chemotherapy",
                    "description": "Diagnosis supports immunotherapy but drug agent prefers chemotherapy.",
                },
            ],
        )
        rec = await generator.generate(consensus, context, evidence_bundle)

        assert isinstance(rec, TreatmentRecommendation)
        assert len(rec.potential_risk.get("risks", [])) >= 1
        assert rec.structured_json is not None

    @pytest.mark.asyncio
    async def test_generate_with_alternatives(self, generator, context, evidence_bundle):
        """Consensus with alternative options → second_line populated."""
        consensus = _consensus_result(
            alternatives=[
                {
                    "treatment": "Chemotherapy",
                    "rationale": "Alternative for unfit patients",
                    "supporting_agents": ["diag"],
                },
            ],
        )
        rec = await generator.generate(consensus, context, evidence_bundle)

        assert rec.second_line["treatment"] == "Chemotherapy"
        assert rec.second_line["supporting_agents"] == ["diag"]

    @pytest.mark.asyncio
    async def test_generate_with_trial_evidence(self, generator, context, sample_evidence):
        """Evidence with clinical trial items → trials populated."""
        consensus = _consensus_result()
        rec = await generator.generate(consensus, context, sample_evidence)

        trials = rec.clinical_trial.get("trials", [])
        assert len(trials) >= 1
        assert any(t.get("nct_id") == "NCT04244447" for t in trials)

    @pytest.mark.asyncio
    async def test_generate_propagates_context_hash(self, generator, context, sample_evidence):
        """context_hash from consensus is propagated to recommendation."""
        consensus = _consensus_result()
        rec = await generator.generate(consensus, context, sample_evidence)
        assert rec.context_hash == consensus.context_hash

    @pytest.mark.asyncio
    async def test_generate_created_at_is_set(self, generator, context, evidence_bundle):
        """created_at is a non-empty ISO timestamp."""
        consensus = _consensus_result()
        rec = await generator.generate(consensus, context, evidence_bundle)
        assert rec.created_at != ""

    @pytest.mark.asyncio
    async def test_generate_with_unresolved_questions(self, generator, context, evidence_bundle):
        """Unresolved questions in consensus → reflected in clinical trial reasoning."""
        consensus = _consensus_result(
            questions=["Is the patient fit for surgery?"],
        )
        rec = await generator.generate(consensus, context, evidence_bundle)
        reasoning = rec.clinical_trial.get("reasoning", "")
        assert len(reasoning) > 0


# ─── Test: Output format validation ─────────────────────────────────────────


class TestOutputFormat:
    """Verify JSON and Markdown output formats from generate()."""

    @pytest.mark.asyncio
    async def test_structured_json_has_required_keys(self, generator, context, sample_evidence):
        """Structured JSON contains all expected top-level keys."""
        consensus = _consensus_result()
        rec = await generator.generate(consensus, context, sample_evidence)

        json_data = rec.structured_json
        assert isinstance(json_data, dict)
        assert "patient" in json_data
        assert "consensus" in json_data
        assert "recommendation" in json_data
        assert "evidence_summary" in json_data
        assert "benefit_risk" in json_data
        assert "monitoring_plan" in json_data

        # Verify nested structure within recommendation
        rec_block = json_data["recommendation"]
        assert "first_line" in rec_block
        assert "second_line" in rec_block
        assert "clinical_trial" in rec_block

        # Verify evidence_summary has expected sub-keys
        ev_summary = json_data["evidence_summary"]
        assert "total_items" in ev_summary
        assert "top_level" in ev_summary

    @pytest.mark.asyncio
    async def test_markdown_contains_expected_sections(self, generator, context, sample_evidence):
        """Markdown report contains all expected section headers."""
        consensus = _consensus_result()
        rec = await generator.generate(consensus, context, sample_evidence)

        md = rec.markdown
        assert "# Treatment Recommendation Report" in md
        assert "## Consensus Summary" in md
        assert "## Treatment Recommendation" in md
        assert "### First-Line Therapy" in md
        assert "### Second-Line / Alternative Therapy" in md
        assert "### Clinical Trial Options" in md
        assert "## Supporting Evidence" in md
        assert "## Benefit-Risk Assessment" in md
        assert "## Monitoring Plan" in md
        # Case context should be present
        assert context.case_id in md
        assert context.patient_id in md

    @pytest.mark.asyncio
    async def test_markdown_contains_consensus_details(self, generator, context, evidence_bundle):
        """Markdown includes agreement level and confidence."""
        consensus = _consensus_result(agreement="high", confidence="high")
        rec = await generator.generate(consensus, context, evidence_bundle)

        md = rec.markdown
        assert "high" in md.lower()
        assert "Agreement Level" in md
        assert "Confidence" in md

    @pytest.mark.asyncio
    async def test_markdown_with_conflicts(self, generator, context, evidence_bundle):
        """Conflicts in consensus → Detected Conflicts section in markdown."""
        consensus = _consensus_result(
            conflicts=[
                {
                    "agent_types": ["diag", "drug"],
                    "topic": "Treatment choice",
                    "description": "Agents disagree on first-line therapy.",
                },
            ],
        )
        rec = await generator.generate(consensus, context, evidence_bundle)

        md = rec.markdown
        assert "Detected Conflicts" in md
        assert "Treatment choice" in md

    @pytest.mark.asyncio
    async def test_markdown_with_unresolved_questions(self, generator, context, evidence_bundle):
        """Unresolved questions → Unresolved Questions section in markdown."""
        consensus = _consensus_result(
            questions=["What is the patient's PD-L1 status?"],
        )
        rec = await generator.generate(consensus, context, evidence_bundle)

        md = rec.markdown
        assert "Unresolved Questions" in md
        assert "PD-L1" in md

    @pytest.mark.asyncio
    async def test_structured_json_empty_consensus(self, generator, context, evidence_bundle):
        """Empty consensus → JSON still has required keys with fallback values."""
        consensus = _consensus_result(
            agreement="none",
            confidence="low",
            treatment="No consensus reached",
        )
        rec = await generator.generate(consensus, context, evidence_bundle)

        json_data = rec.structured_json
        assert json_data["recommendation"]["first_line"]["treatment"] == "No consensus reached"

    @pytest.mark.asyncio
    async def test_markdown_no_evidence(self, generator, context, evidence_bundle):
        """No evidence items → markdown notes missing evidence."""
        consensus = _consensus_result()
        rec = await generator.generate(consensus, context, evidence_bundle)

        assert "No supporting evidence" in rec.markdown or "Supporting Evidence" in rec.markdown
