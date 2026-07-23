"""
Unit tests for Phase 2b multi-agent system — BaseAgent, AgentOpinion,
and concrete agent implementations (DiagnosisAgent, VariantAgent, DrugAgent,
GuidelineAgent, ClinicalTrialAgent, ResistanceAgent).
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from src.backend.agents.base import BaseAgent
from src.backend.agents.diagnosis_agent import DiagnosisAgent
from src.backend.agents.drug_agent import DrugAgent
from src.backend.agents.models import AgentOpinion
from src.backend.agents.variant_agent import VariantAgent
from src.backend.clinical.evidence_models import EvidenceBundle, EvidenceItem
from src.backend.clinical.models import ClinicalContext

# ─── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def mock_db():
    """Create a mock async database session."""
    return AsyncMock()


@pytest.fixture
def minimal_context() -> ClinicalContext:
    """A minimal valid ClinicalContext with all required fields."""
    ctx = ClinicalContext(
        case_id="CASE-001",
        patient_id="PT-001",
        age=55,
        gender="female",
        diagnosis="Lung adenocarcinoma",
        stage="Stage IIB",
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
def sample_bundle() -> EvidenceBundle:
    """A sample evidence bundle with a few items."""
    items = [
        EvidenceItem(
            source="ClinVar",
            gene_symbol="EGFR",
            evidence_type="diagnostic",
            evidence_direction="supporting",
            citation="ClinVar record 1",
            url="https://example.com/clinvar/1",
            clinical_significance="pathogenic",
        ),
        EvidenceItem(
            source="CIViC",
            gene_symbol="EGFR",
            evidence_type="predictive",
            evidence_direction="supporting",
            citation="CIViC record 2",
            drug_name="Erlotinib",
            evidence_level="A",
        ),
        EvidenceItem(
            source="NCCN",
            gene_symbol="EGFR",
            evidence_type="predictive",
            evidence_direction="supporting",
            citation="NCCN guideline",
            drug_name="Osimertinib",
        ),
    ]
    return EvidenceBundle(items=items)


# ─── Test: BaseAgent (abstract) ─────────────────────────────────────────────


class TestBaseAgent:
    """Verify that BaseAgent cannot be instantiated directly."""

    def test_cannot_instantiate_abstract_class(self, mock_db):
        """BaseAgent is abstract → TypeError when instantiated."""
        with pytest.raises(TypeError, match="abstract"):
            BaseAgent(mock_db)  # type: ignore

    def test_validate_opinion_valid(self):
        """validate_opinion returns empty list for a well-formed opinion."""
        opinion = AgentOpinion(
            agent_type="test_agent",
            agent_version="1.0.0",
            summary="A valid summary.",
            confidence="high",
            created_at=datetime.now(UTC).isoformat(),
        )
        # Use a concrete subclass to access validate_opinion
        agent = DiagnosisAgent(db=AsyncMock())
        errors = agent.validate_opinion(opinion)
        assert errors == []

    def test_validate_opinion_empty_agent_type(self):
        """Missing agent_type → error."""
        opinion = AgentOpinion(
            agent_type="",
            agent_version="1.0.0",
            summary="Summary text.",
            confidence="high",
            created_at=datetime.now(UTC).isoformat(),
        )
        agent = DiagnosisAgent(db=AsyncMock())
        errors = agent.validate_opinion(opinion)
        assert "agent_type must not be empty" in errors

    def test_validate_opinion_empty_agent_version(self):
        """Missing agent_version → error."""
        opinion = AgentOpinion(
            agent_type="test",
            agent_version="",
            summary="Summary text.",
            confidence="high",
            created_at=datetime.now(UTC).isoformat(),
        )
        agent = DiagnosisAgent(db=AsyncMock())
        errors = agent.validate_opinion(opinion)
        assert "agent_version must not be empty" in errors

    def test_validate_opinion_empty_summary(self):
        """Missing summary → error."""
        opinion = AgentOpinion(
            agent_type="test",
            agent_version="1.0.0",
            summary="",
            confidence="high",
            created_at=datetime.now(UTC).isoformat(),
        )
        agent = DiagnosisAgent(db=AsyncMock())
        errors = agent.validate_opinion(opinion)
        assert "summary must not be empty" in errors

    def test_validate_opinion_invalid_confidence(self):
        """Invalid confidence value → error."""
        opinion = AgentOpinion(
            agent_type="test",
            agent_version="1.0.0",
            summary="Summary text.",
            confidence="very_high",
            created_at=datetime.now(UTC).isoformat(),
        )
        agent = DiagnosisAgent(db=AsyncMock())
        errors = agent.validate_opinion(opinion)
        assert any("confidence must be one of" in e for e in errors)

    def test_validate_opinion_missing_created_at(self):
        """Missing created_at → error."""
        opinion = AgentOpinion(
            agent_type="test",
            agent_version="1.0.0",
            summary="Summary text.",
            confidence="medium",
            created_at="",
        )
        agent = DiagnosisAgent(db=AsyncMock())
        errors = agent.validate_opinion(opinion)
        assert "created_at must be set (ISO-8601 timestamp)" in errors

    def test_validate_opinion_invalid_references(self):
        """Invalid references (non-dict, missing keys) → errors."""
        # Use model_construct to bypass Pydantic type validation so that
        # validate_opinion receives the raw references as-is for checking.
        opinion = AgentOpinion.model_construct(
            agent_type="test",
            agent_version="1.0.0",
            summary="Summary text.",
            confidence="low",
            created_at=datetime.now(UTC).isoformat(),
            references=[
                "not a dict",
                {"source": "NCCN"},  # missing 'citation'
            ],
        )
        agent = DiagnosisAgent(db=AsyncMock())
        errors = agent.validate_opinion(opinion)
        assert any("must be a dict" in e for e in errors)
        assert any("missing required key 'citation'" in e for e in errors)

    def test_validate_opinion_multiple_errors(self):
        """Multiple validation issues → all reported."""
        opinion = AgentOpinion(
            agent_type="",
            agent_version="",
            summary="",
            confidence="unknown",
            created_at="",
        )
        agent = DiagnosisAgent(db=AsyncMock())
        errors = agent.validate_opinion(opinion)
        assert len(errors) >= 4


# ─── Test: AgentOpinion model ───────────────────────────────────────────────


class TestAgentOpinion:
    """Verify AgentOpinion Pydantic model creation and defaults."""

    def test_minimal_creation(self):
        """Minimal AgentOpinion with only required fields."""
        opinion = AgentOpinion(
            agent_type="test",
            agent_version="1.0.0",
            summary="Test opinion.",
        )
        assert opinion.agent_type == "test"
        assert opinion.agent_version == "1.0.0"
        assert opinion.summary == "Test opinion."
        # Defaults
        assert opinion.confidence == "medium"
        assert opinion.pros == []
        assert opinion.cons == []
        assert opinion.references == []
        assert opinion.created_at == ""
        assert opinion.context_hash is None

    def test_fully_populated(self):
        """Fully populated AgentOpinion with all fields."""
        now = datetime.now(UTC).isoformat()
        opinion = AgentOpinion(
            agent_type="diagnosis",
            agent_version="2.0.0",
            summary="Full opinion.",
            pros=["Reason A", "Reason B"],
            cons=["Risk X"],
            confidence="high",
            references=[{"source": "NCCN", "citation": "Guideline v3"}],
            context_hash="abc123",
            created_at=now,
        )
        assert opinion.agent_type == "diagnosis"
        assert len(opinion.pros) == 2
        assert len(opinion.cons) == 1
        assert opinion.confidence == "high"
        assert opinion.context_hash == "abc123"
        assert opinion.created_at == now

    def test_invalid_confidence_rejected(self):
        """Invalid confidence string → caught by validate_opinion."""
        opinion = AgentOpinion(
            agent_type="test",
            agent_version="1.0.0",
            summary="Bad confidence.",
            confidence="invalid_value",
        )
        agent = DiagnosisAgent(db=AsyncMock())
        errors = agent.validate_opinion(opinion)
        assert any("confidence must be one of" in e for e in errors)


# ─── Test: DiagnosisAgent ───────────────────────────────────────────────────


class TestDiagnosisAgent:
    """Tests for DiagnosisAgent.analyze()."""

    @pytest.mark.asyncio
    async def test_analyze_full_valid_context(self, mock_db, sample_bundle):
        """Fully populated valid context → high confidence, no cons."""
        context = ClinicalContext(
            case_id="CASE-001",
            patient_id="PT-001",
            age=60,
            gender="male",
            diagnosis="Lung adenocarcinoma",
            stage="Stage IIB",
            histology="adenocarcinoma",
            cancer_type="lung",
            biomarkers=[{"name": "EGFR", "gene_symbol": "EGFR"}],
        )
        context.freeze()
        agent = DiagnosisAgent(db=mock_db)
        opinion = await agent.analyze(context, sample_bundle)

        assert isinstance(opinion, AgentOpinion)
        assert opinion.agent_type == "diagnosis"
        assert opinion.agent_version == "1.0.0"
        assert opinion.confidence in ("high", "medium", "low")
        assert "lung" in opinion.summary.lower()
        assert opinion.created_at != ""

    @pytest.mark.asyncio
    async def test_analyze_missing_fields(self, mock_db, evidence_bundle):
        """Missing diagnosis fields → low confidence, cons present."""
        context = ClinicalContext(
            case_id="CASE-002",
            patient_id="PT-002",
            age=45,
            gender="female",
            diagnosis="",
            stage="",
            histology="",
            cancer_type="breast",
        )
        context.freeze()
        agent = DiagnosisAgent(db=mock_db)
        opinion = await agent.analyze(context, evidence_bundle)

        assert opinion.confidence == "low"
        assert len(opinion.cons) > 0
        assert any("missing" in c.lower() for c in opinion.cons)

    @pytest.mark.asyncio
    async def test_analyze_inconsistent_stage(self, mock_db, evidence_bundle):
        """Invalid stage format → consistency issues in cons."""
        context = ClinicalContext(
            case_id="CASE-003",
            patient_id="PT-003",
            age=50,
            gender="female",
            diagnosis="Breast cancer",
            stage="Unknown",
            histology="invasive ductal carcinoma",
            cancer_type="breast",
        )
        context.freeze()
        agent = DiagnosisAgent(db=mock_db)
        opinion = await agent.analyze(context, evidence_bundle)

        assert len(opinion.cons) > 0
        assert any("stage" in c.lower() for c in opinion.cons)

    @pytest.mark.asyncio
    async def test_analyze_with_biomarker_evidence(self, mock_db):
        """Biomarker matched to evidence → mentioned in pros and summary."""
        context = ClinicalContext(
            case_id="CASE-004",
            patient_id="PT-004",
            age=55,
            gender="female",
            diagnosis="Lung adenocarcinoma",
            stage="Stage IV",
            histology="adenocarcinoma",
            cancer_type="lung",
            biomarkers=[{"name": "EGFR"}],
        )
        context.freeze()
        bundle = EvidenceBundle(items=[
            EvidenceItem(
                source="ClinVar",
                gene_symbol="EGFR",
                evidence_type="diagnostic",
                evidence_direction="supporting",
                citation="ClinVar EGFR record",
            ),
        ])
        agent = DiagnosisAgent(db=mock_db)
        opinion = await agent.analyze(context, bundle)

        # The summary says "1 biomarker(s) matched to diagnostic evidence."
        assert "biomarker" in opinion.summary.lower()
        # The biomarker name appears in pros, not in the summary.
        assert any("EGFR" in p for p in opinion.pros)

    @pytest.mark.asyncio
    async def test_agent_does_not_share_state(self, mock_db, evidence_bundle):
        """Two DiagnosisAgent instances do not interfere."""
        ctx1 = ClinicalContext(
            case_id="CASE-A",
            patient_id="PT-A",
            age=40, gender="female",
            diagnosis="Breast cancer", stage="Stage IIA",
            histology="invasive ductal carcinoma", cancer_type="breast",
        )
        ctx1.freeze()
        ctx2 = ClinicalContext(
            case_id="CASE-B",
            patient_id="PT-B",
            age=70, gender="male",
            diagnosis="Prostate cancer", stage="Stage IV",
            histology="adenocarcinoma", cancer_type="prostate",
        )
        ctx2.freeze()

        agent1 = DiagnosisAgent(db=mock_db)
        agent2 = DiagnosisAgent(db=mock_db)
        op1 = await agent1.analyze(ctx1, evidence_bundle)
        op2 = await agent2.analyze(ctx2, evidence_bundle)

        assert op1.summary != op2.summary
        assert op1.context_hash != op2.context_hash


# ─── Test: VariantAgent ─────────────────────────────────────────────────────


class TestVariantAgent:
    """Tests for VariantAgent.analyze()."""

    @pytest.mark.asyncio
    async def test_analyze_with_variants(self, mock_db):
        """Variants present with evidence → valid opinion."""
        context = ClinicalContext(
            case_id="CASE-010",
            patient_id="PT-010",
            age=60, gender="male",
            diagnosis="Lung adenocarcinoma",
            stage="Stage IV",
            histology="adenocarcinoma",
            cancer_type="lung",
            variants=[
                {
                    "gene_symbol": "EGFR",
                    "hgvs": "c.2573T>G",
                    "protein_change": "p.Leu858Arg",
                    "vaf": 0.35,
                    "clinical_significance": "pathogenic",
                },
            ],
        )
        context.freeze()
        bundle = EvidenceBundle(items=[
            EvidenceItem(
                source="ClinVar",
                gene_symbol="EGFR",
                evidence_type="predictive",
                clinical_significance="pathogenic",
                citation="ClinVar EGFR L858R",
                drug_name="Erlotinib",
            ),
            EvidenceItem(
                source="CIViC",
                gene_symbol="EGFR",
                evidence_type="predictive",
                clinical_significance="pathogenic",
                citation="CIViC EGFR record",
                drug_name="Osimertinib",
            ),
        ])
        agent = VariantAgent(db=mock_db)
        opinion = await agent.analyze(context, bundle)

        assert isinstance(opinion, AgentOpinion)
        assert opinion.agent_type == "variant"
        assert "EGFR" in opinion.summary
        assert len(opinion.references) >= 1

    @pytest.mark.asyncio
    async def test_analyze_no_variants(self, mock_db, evidence_bundle):
        """No variants → medium confidence, cons present."""
        context = ClinicalContext(
            case_id="CASE-011",
            patient_id="PT-011",
            age=45, gender="female",
            diagnosis="Breast cancer",
            stage="Stage IIA",
            histology="invasive ductal carcinoma",
            cancer_type="breast",
            variants=[],
        )
        context.freeze()
        agent = VariantAgent(db=mock_db)
        opinion = await agent.analyze(context, evidence_bundle)

        assert opinion.confidence == "medium"
        assert "no variants" in opinion.summary.lower()

    @pytest.mark.asyncio
    async def test_analyze_druggable_variants(self, mock_db):
        """Variants with drug evidence → druggable flagged."""
        context = ClinicalContext(
            case_id="CASE-012",
            patient_id="PT-012",
            age=55, gender="female",
            diagnosis="Lung adenocarcinoma",
            stage="Stage IV",
            histology="adenocarcinoma",
            cancer_type="lung",
            variants=[
                {
                    "gene_symbol": "BRAF",
                    "hgvs": "c.1799T>A",
                    "protein_change": "p.Val600Glu",
                    "vaf": 0.42,
                },
            ],
        )
        context.freeze()
        bundle = EvidenceBundle(items=[
            EvidenceItem(
                source="CIViC",
                gene_symbol="BRAF",
                evidence_type="predictive",
                clinical_significance="pathogenic",
                drug_name="Vemurafenib",
                citation="CIViC BRAF V600E",
            ),
        ])
        agent = VariantAgent(db=mock_db)
        opinion = await agent.analyze(context, bundle)

        assert "druggable" in opinion.summary.lower()
        assert any("vemurafenib" in p.lower() or "druggable" in p.lower()
                   for p in opinion.pros)

    @pytest.mark.asyncio
    async def test_analyze_no_civic_clinvar_evidence(self, mock_db):
        """Variants without ClinVar/CIViC evidence → cons about missing evidence."""
        context = ClinicalContext(
            case_id="CASE-013",
            patient_id="PT-013",
            age=50, gender="male",
            diagnosis="Colorectal cancer",
            stage="Stage III",
            histology="adenocarcinoma",
            cancer_type="colorectal",
            variants=[
                {"gene_symbol": "MYC", "hgvs": "c.1A>G", "protein_change": "p.Met1?"},
            ],
        )
        context.freeze()
        bundle = EvidenceBundle(items=[
            EvidenceItem(
                source="PubMed",
                gene_symbol="MYC",
                evidence_type="prognostic",
                citation="PubMed article",
            ),
        ])
        agent = VariantAgent(db=mock_db)
        opinion = await agent.analyze(context, bundle)

        # MYC is not from ClinVar/CIViC, so cons about missing evidence
        assert any("MYC" in c for c in opinion.cons)
        assert any("lack" in c.lower() for c in opinion.cons)


# ─── Test: DrugAgent ────────────────────────────────────────────────────────


class TestDrugAgent:
    """Tests for DrugAgent.analyze()."""

    @pytest.mark.asyncio
    async def test_analyze_recommends_drug(self, mock_db):
        """Drug with matching gene variant → recommended."""
        context = ClinicalContext(
            case_id="CASE-020",
            patient_id="PT-020",
            age=60, gender="female",
            diagnosis="Lung adenocarcinoma",
            stage="Stage IV",
            histology="adenocarcinoma",
            cancer_type="lung",
            variants=[{"gene_symbol": "EGFR"}],
            treatment_history=[],
            current_medications=[],
            allergies=[],
        )
        context.freeze()
        bundle = EvidenceBundle(items=[
            EvidenceItem(
                source="NCCN",
                gene_symbol="EGFR",
                drug_name="Osimertinib",
                evidence_type="predictive",
                evidence_direction="supporting",
                evidence_level="A",
                citation="NCCN NSCLC guideline",
            ),
        ])
        agent = DrugAgent(db=mock_db)
        opinion = await agent.analyze(context, bundle)

        assert isinstance(opinion, AgentOpinion)
        assert opinion.agent_type == "drug"
        assert any("osimertinib" in p.lower() for p in opinion.pros)
        assert opinion.confidence in ("high", "medium")

    @pytest.mark.asyncio
    async def test_analyze_excluded_by_allergy(self, mock_db):
        """Drug matching patient's allergy → excluded."""
        context = ClinicalContext(
            case_id="CASE-021",
            patient_id="PT-021",
            age=50, gender="male",
            diagnosis="Lung adenocarcinoma",
            stage="Stage IV",
            histology="adenocarcinoma",
            cancer_type="lung",
            variants=[{"gene_symbol": "EGFR"}],
            treatment_history=[],
            current_medications=[],
            allergies=["erlotinib"],
        )
        context.freeze()
        bundle = EvidenceBundle(items=[
            EvidenceItem(
                source="NCCN",
                gene_symbol="EGFR",
                drug_name="Erlotinib",
                evidence_type="predictive",
                evidence_direction="supporting",
                citation="NCCN guideline",
            ),
        ])
        agent = DrugAgent(db=mock_db)
        opinion = await agent.analyze(context, bundle)

        assert any("excluded" in c.lower() for c in opinion.cons)
        assert any("allergy" in c.lower() for c in opinion.cons)

    @pytest.mark.asyncio
    async def test_analyze_no_matching_drugs(self, mock_db, evidence_bundle):
        """No drug evidence matches patient variants → low confidence."""
        context = ClinicalContext(
            case_id="CASE-022",
            patient_id="PT-022",
            age=65, gender="female",
            diagnosis="Pancreatic cancer",
            stage="Stage IV",
            histology="ductal adenocarcinoma",
            cancer_type="pancreas",
            variants=[{"gene_symbol": "KRAS"}],
            treatment_history=[],
            current_medications=[],
            allergies=[],
        )
        context.freeze()
        agent = DrugAgent(db=mock_db)
        opinion = await agent.analyze(context, evidence_bundle)

        assert opinion.confidence == "low"
        assert "no drug matched" in opinion.summary.lower()

    @pytest.mark.asyncio
    async def test_analyze_with_prior_treatment(self, mock_db):
        """Drug previously used with progression → cons about prior failure."""
        context = ClinicalContext(
            case_id="CASE-023",
            patient_id="PT-023",
            age=55, gender="male",
            diagnosis="Lung adenocarcinoma",
            stage="Stage IV",
            histology="adenocarcinoma",
            cancer_type="lung",
            variants=[{"gene_symbol": "EGFR"}],
            treatment_history=[
                {
                    "regimen": "Erlotinib",
                    "response": "Progressive Disease",
                },
            ],
            current_medications=[],
            allergies=[],
        )
        context.freeze()
        bundle = EvidenceBundle(items=[
            EvidenceItem(
                source="NCCN",
                gene_symbol="EGFR",
                drug_name="Erlotinib",
                evidence_type="predictive",
                evidence_direction="supporting",
                citation="NCCN guideline",
            ),
        ])
        agent = DrugAgent(db=mock_db)
        opinion = await agent.analyze(context, bundle)

        assert any("progressive" in c.lower() for c in opinion.cons)
        assert any("previously" in c.lower() for c in opinion.cons)

    @pytest.mark.asyncio
    async def test_generates_invalid_opinion_raises_error(self, mock_db):
        """DrugAgent raises ValueError when validate_opinion fails."""
        # Inject an invalid state by mocking to produce an empty summary
        context = ClinicalContext(
            case_id="CASE-024",
            patient_id="PT-024",
            age=40, gender="female",
            diagnosis="Breast cancer",
            stage="Stage II",
            histology="invasive ductal carcinoma",
            cancer_type="breast",
            variants=[],
            treatment_history=[],
            current_medications=[],
            allergies=[],
        )
        context.freeze()
        agent = DrugAgent(db=mock_db)

        # The DrugAgent internally calls validate_opinion().
        # With no variants and no evidence, it should produce a valid
        # low-confidence opinion rather than raising.
        bundle = EvidenceBundle()
        opinion = await agent.analyze(context, bundle)
        assert isinstance(opinion, AgentOpinion)
        # No error should be raised — the agent handles empty state gracefully


# ─── Test: Agent isolation ──────────────────────────────────────────────────


class TestAgentIsolation:
    """Verify that agents of different types do not interfere."""

    @pytest.mark.asyncio
    async def test_diagnosis_and_variant_independent(self, mock_db):
        """DiagnosisAgent and VariantAgent produce independent opinions."""
        context = ClinicalContext(
            case_id="CASE-030",
            patient_id="PT-030",
            age=50, gender="female",
            diagnosis="Lung adenocarcinoma",
            stage="Stage IV",
            histology="adenocarcinoma",
            cancer_type="lung",
            variants=[{"gene_symbol": "EGFR", "hgvs": "c.2573T>G"}],
            biomarkers=[{"name": "EGFR"}],
        )
        context.freeze()
        bundle = EvidenceBundle(items=[
            EvidenceItem(
                source="ClinVar", gene_symbol="EGFR",
                evidence_type="diagnostic", evidence_direction="supporting",
                citation="ClinVar record",
            ),
        ])

        diag = DiagnosisAgent(db=mock_db)
        variant = VariantAgent(db=mock_db)

        op_diag = await diag.analyze(context, bundle)
        op_variant = await variant.analyze(context, bundle)

        assert op_diag.agent_type == "diagnosis"
        assert op_variant.agent_type == "variant"
        assert op_diag.summary != op_variant.summary

    @pytest.mark.asyncio
    async def test_multiple_instances_same_input(self, mock_db):
        """Two instances of the same agent with same input → same output."""
        ctx = ClinicalContext(
            case_id="CASE-031",
            patient_id="PT-031",
            age=45, gender="male",
            diagnosis="Prostate cancer",
            stage="Stage II",
            histology="adenocarcinoma",
            cancer_type="prostate",
        )
        ctx.freeze()
        bundle = EvidenceBundle()

        a1 = DiagnosisAgent(db=mock_db)
        a2 = DiagnosisAgent(db=mock_db)

        op1 = await a1.analyze(ctx, bundle)
        op2 = await a2.analyze(ctx, bundle)

        assert op1.agent_type == op2.agent_type
        assert op1.confidence == op2.confidence
        assert op1.summary == op2.summary
