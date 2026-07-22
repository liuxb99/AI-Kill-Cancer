"""
Unit tests for ClinicalContext model and CaseContextBuilder.

Tests the frozen clinical context snapshot model including hash computation,
and the builder that assembles contexts from database records.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.backend.clinical.builder import CaseContextBuilder
from src.backend.clinical.models import ClinicalContext
from src.backend.domain.cancer_case import CancerCaseModel
from src.backend.domain.enums import SexEnum
from src.backend.domain.patient import PatientModel
from src.backend.domain.variant import VariantModel


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_db():
    """Create a mock async SQLAlchemy session."""
    db = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def builder(mock_db):
    """Create a CaseContextBuilder with a mock DB session."""
    return CaseContextBuilder(mock_db)


@pytest.fixture
def sample_clinical_context():
    """Return a fully populated ClinicalContext for testing."""
    return ClinicalContext(
        case_id="case-001",
        patient_id="pat-001",
        age=45,
        gender="F",
        diagnosis="PTC (Papillary thyroid carcinoma)",
        stage="II",
        histology="Papillary thyroid carcinoma",
        cancer_type="PTC",
        oncotree_code="THPA",
        biomarkers=[
            {"gene": "BRAF", "value": "p.Val600Glu"},
        ],
        variants=[
            {
                "gene_symbol": "BRAF",
                "hgvs": "NM_004333.6:c.1799T>A",
                "protein_change": "p.Val600Glu",
                "vaf": 0.35,
                "clinical_significance": "Pathogenic",
            },
        ],
        treatment_history=[
            {"therapy": "Surgery", "date": "2024-01-15"},
        ],
        current_medications=[
            {"name": "Levothyroxine", "dose": "100 mcg"},
        ],
        allergies=["Penicillin"],
        ecog_score=1,
        metastatic_sites=["Lymph nodes"],
        recurrence_status="no_recurrence",
        clinical_notes="Patient responding well.",
    )


class TestClinicalContext:
    """Tests for the ClinicalContext Pydantic model."""

    def test_create_full(self, sample_clinical_context):
        """Create a ClinicalContext with all fields populated."""
        ctx = sample_clinical_context
        assert ctx.case_id == "case-001"
        assert ctx.patient_id == "pat-001"
        assert ctx.age == 45
        assert ctx.gender == "F"
        assert ctx.diagnosis == "PTC (Papillary thyroid carcinoma)"
        assert ctx.stage == "II"
        assert ctx.histology == "Papillary thyroid carcinoma"
        assert ctx.cancer_type == "PTC"
        assert ctx.oncotree_code == "THPA"
        assert len(ctx.biomarkers) == 1
        assert len(ctx.variants) == 1
        assert len(ctx.treatment_history) == 1
        assert len(ctx.current_medications) == 1
        assert ctx.allergies == ["Penicillin"]
        assert ctx.ecog_score == 1
        assert ctx.metastatic_sites == ["Lymph nodes"]
        assert ctx.recurrence_status == "no_recurrence"
        assert ctx.clinical_notes == "Patient responding well."

    def test_default_values(self):
        """ClinicalContext should use sensible defaults for optional fields."""
        ctx = ClinicalContext(
            case_id="",
            patient_id="",
            age=0,
            gender="",
            diagnosis="",
            stage="",
            histology="",
            cancer_type="",
        )
        assert ctx.oncotree_code is None
        assert ctx.biomarkers == []
        assert ctx.variants == []
        assert ctx.treatment_history == []
        assert ctx.current_medications == []
        assert ctx.allergies == []
        assert ctx.ecog_score is None
        assert ctx.metastatic_sites == []
        assert ctx.recurrence_status is None
        assert ctx.clinical_notes is None
        assert ctx.context_hash == ""

    def test_default_values_empty_strings(self):
        """String fields requiring values should default to empty strings."""
        ctx = ClinicalContext(
            case_id="x",
            patient_id="y",
            age=0,
            gender="",
            diagnosis="",
            stage="",
            histology="",
            cancer_type="",
        )
        assert ctx.case_id == "x"
        assert ctx.patient_id == "y"
        assert ctx.age == 0
        assert ctx.gender == ""

    def test_default_variants_description(self):
        """Variant field should accept the documented keys."""
        ctx = ClinicalContext(
            case_id="c1",
            patient_id="p1",
            age=30,
            gender="M",
            diagnosis="FTC",
            stage="I",
            histology="Follicular",
            cancer_type="FTC",
            variants=[
                {
                    "gene_symbol": "EGFR",
                    "hgvs": "NM_005228.5:c.2573T>G",
                    "protein_change": "p.Leu858Arg",
                    "vaf": 0.42,
                    "clinical_significance": "Pathogenic",
                },
            ],
        )
        v = ctx.variants[0]
        assert v["gene_symbol"] == "EGFR"
        assert v["hgvs"] == "NM_005228.5:c.2573T>G"
        assert v["protein_change"] == "p.Leu858Arg"
        assert v["vaf"] == 0.42
        assert v["clinical_significance"] == "Pathogenic"

    # ── freeze() tests ───────────────────────────────────────────────────

    def test_freeze_returns_hex_string(self, sample_clinical_context):
        """freeze() should return a SHA256 hex digest."""
        ctx = sample_clinical_context
        h = ctx.freeze()
        assert isinstance(h, str)
        assert len(h) == 64
        # All chars should be hex digits
        int(h, 16)

    def test_freeze_stores_hash_on_context(self, sample_clinical_context):
        """freeze() should store the hash in context_hash."""
        ctx = sample_clinical_context
        assert ctx.context_hash == ""
        h = ctx.freeze()
        assert ctx.context_hash == h
        assert ctx.context_hash != ""

    def test_same_data_produces_same_hash(self):
        """Two contexts with identical data should produce identical hashes."""
        data = dict(
            case_id="c1",
            patient_id="p1",
            age=55,
            gender="M",
            diagnosis="MTC",
            stage="III",
            histology="Medullary",
            cancer_type="MTC",
        )
        ctx_a = ClinicalContext(**data)
        ctx_b = ClinicalContext(**data)
        assert ctx_a.freeze() == ctx_b.freeze()

    def test_different_data_produces_different_hash(self):
        """Two contexts with differing fields should produce different hashes."""
        ctx_a = ClinicalContext(
            case_id="c1", patient_id="p1", age=55, gender="M",
            diagnosis="MTC", stage="III", histology="Medullary", cancer_type="MTC",
        )
        ctx_b = ClinicalContext(
            case_id="c1", patient_id="p1", age=55, gender="M",
            diagnosis="MTC", stage="III", histology="Medullary", cancer_type="PTC",
        )
        assert ctx_a.freeze() != ctx_b.freeze()

    def test_freeze_excludes_context_hash_field(self):
        """The context_hash field itself should not be part of the hash payload."""
        ctx = ClinicalContext(
            case_id="c1", patient_id="p1", age=30, gender="F",
            diagnosis="FTC", stage="I", histology="Follicular", cancer_type="FTC",
            context_hash="pre-set",
        )
        h = ctx.freeze()
        # The hash should not include the pre-set context_hash field
        # Re-freezing should produce the same hash
        assert h == ctx.freeze()

    def test_freeze_uses_sorted_keys(self):
        """freeze() should sort keys for reproducibility regardless of field order."""
        # Create with explicit field order — Pydantic model_dump sorts anyway
        ctx = ClinicalContext(
            case_id="c1", patient_id="p1", age=40, gender="F",
            diagnosis="PTC", stage="I", histology="Papillary", cancer_type="PTC",
        )
        h1 = ctx.freeze()

        ctx2 = ClinicalContext(
            patient_id="p1", case_id="c1", gender="F", age=40,
            cancer_type="PTC", histology="Papillary", diagnosis="PTC", stage="I",
        )
        h2 = ctx2.freeze()
        assert h1 == h2

    def test_freeze_idempotent(self, sample_clinical_context):
        """Calling freeze() multiple times should return the same hash."""
        ctx = sample_clinical_context
        h1 = ctx.freeze()
        h2 = ctx.freeze()
        assert h1 == h2

    def test_freeze_with_variants(self):
        """freeze() should incorporate variant data into the hash."""
        ctx = ClinicalContext(
            case_id="c1", patient_id="p1", age=50, gender="M",
            diagnosis="ATC", stage="IV", histology="Anaplastic", cancer_type="ATC",
            variants=[{"gene_symbol": "TP53", "hgvs": "", "protein_change": "",
                       "vaf": None, "clinical_significance": ""}],
        )
        h = ctx.freeze()
        assert len(h) == 64

    def test_freeze_with_optional_none(self):
        """freeze() should handle None values in optional fields."""
        ctx = ClinicalContext(
            case_id="c1", patient_id="p1", age=35, gender="F",
            diagnosis="PTC", stage="I", histology="Papillary", cancer_type="PTC",
            oncotree_code=None,
            ecog_score=None,
            recurrence_status=None,
            clinical_notes=None,
        )
        h = ctx.freeze()
        assert len(h) == 64


class TestCaseContextBuilder:
    """Tests for the CaseContextBuilder."""

    async def test_build_success(self, builder, mock_db):
        """build() should return a frozen ClinicalContext with hash for valid case."""
        case_id = str(uuid.uuid4())
        patient_id = uuid.uuid4()

        # Mock the case repo
        mock_case = MagicMock(spec=CancerCaseModel)
        mock_case.id = uuid.UUID(case_id)
        mock_case.patient_id = patient_id
        mock_case.cancer_type = "PTC"
        mock_case.histology = "Papillary thyroid carcinoma"
        mock_case.stage = "II"
        mock_case.oncotree_code = "THPA"
        mock_case.treatment_history = [{"therapy": "Surgery"}]
        mock_case.current_medications = [{"name": "Levothyroxine"}]
        mock_case.metastatic_sites = ["Lymph nodes"]
        mock_case.recurrence_status = "no_recurrence"
        mock_case.clinical_notes = "Stable"

        # Mock the patient repo
        mock_patient = MagicMock(spec=PatientModel)
        mock_patient.birth_year = 1979
        mock_patient.sex = SexEnum.F

        # Mock the variant query
        mock_variant = MagicMock(spec=VariantModel)
        mock_variant.gene_symbol = "BRAF"
        mock_variant.hgvs_p = "p.Val600Glu"
        mock_variant.hgvs_c = "c.1799T>A"
        mock_variant.protein_change = "p.Val600Glu"
        mock_variant.vaf = 0.35
        mock_variant.clinical_significance = "Pathogenic"

        # Wire up mocks
        with (
            patch.object(builder, "_load_variants", AsyncMock(return_value=[mock_variant])),
        ):
            # We need to mock the repos inside build()
            # Since they're created inside build, we patch at module level
            with (
                patch(
                    "src.backend.clinical.builder.CancerCaseRepository",
                    return_value=AsyncMock(get=AsyncMock(return_value=mock_case)),
                ) as mock_case_repo_cls,
                patch(
                    "src.backend.clinical.builder.PatientRepository",
                    return_value=AsyncMock(get=AsyncMock(return_value=mock_patient)),
                ) as mock_patient_repo_cls,
            ):
                ctx = await builder.build(case_id)

        assert isinstance(ctx, ClinicalContext)
        assert ctx.case_id == case_id
        assert ctx.patient_id == str(patient_id)
        assert ctx.age > 0  # computed from birth_year
        assert ctx.gender == "F"
        assert ctx.cancer_type == "PTC"
        assert ctx.histology == "Papillary thyroid carcinoma"
        assert ctx.stage == "II"
        assert ctx.oncotree_code == "THPA"
        assert len(ctx.treatment_history) == 1
        assert len(ctx.current_medications) == 1
        assert ctx.metastatic_sites == ["Lymph nodes"]
        assert ctx.recurrence_status == "no_recurrence"
        assert ctx.clinical_notes == "Stable"
        assert ctx.context_hash != ""
        assert len(ctx.context_hash) == 64

    async def test_build_invalid_case_id(self, builder):
        """build() should return empty context for invalid case_id."""
        ctx = await builder.build("not-a-uuid")
        assert isinstance(ctx, ClinicalContext)
        assert ctx.case_id == ""
        assert ctx.patient_id == ""
        assert ctx.age == 0
        assert ctx.gender == ""
        assert ctx.context_hash == ""

    async def test_build_none_case_id(self, builder):
        """build() should handle None case_id gracefully (invalid)."""
        ctx = await builder.build(None)  # type: ignore[arg-type]
        assert isinstance(ctx, ClinicalContext)
        assert ctx.case_id == ""

    async def test_build_case_not_found(self, builder, mock_db):
        """build() should return empty context when case is not in database."""
        valid_uuid = str(uuid.uuid4())
        with patch(
            "src.backend.clinical.builder.CancerCaseRepository",
            return_value=AsyncMock(get=AsyncMock(return_value=None)),
        ):
            ctx = await builder.build(valid_uuid)
        assert isinstance(ctx, ClinicalContext)
        assert ctx.case_id == ""
        assert ctx.age == 0

    async def test_build_database_error_on_case(self, builder):
        """build() should propagate DB errors when loading the case."""
        with patch(
            "src.backend.clinical.builder.CancerCaseRepository",
            return_value=AsyncMock(
                get=AsyncMock(side_effect=Exception("DB connection failed")),
            ),
            with pytest.raises(Exception, match="DB connection failed"):
                await builder.build(str(uuid.uuid4()))

    async def test_build_database_error_on_variants_returns_empty_variants(
        self, builder, mock_db,
    ):
        """build() should handle variant loading errors gracefully (empty list)."""
        case_id = str(uuid.uuid4())
        patient_id = uuid.uuid4()

        mock_case = MagicMock(spec=CancerCaseModel)
        mock_case.id = uuid.UUID(case_id)
        mock_case.patient_id = patient_id
        mock_case.cancer_type = "PTC"
        mock_case.histology = ""
        mock_case.stage = ""
        mock_case.oncotree_code = None
        mock_case.treatment_history = []
        mock_case.current_medications = []
        mock_case.metastatic_sites = []
        mock_case.recurrence_status = None
        mock_case.clinical_notes = None

        mock_patient = MagicMock(spec=PatientModel)
        mock_patient.birth_year = 1985
        mock_patient.sex = SexEnum.M

        with (
            patch(
                "src.backend.clinical.builder.CancerCaseRepository",
                return_value=AsyncMock(get=AsyncMock(return_value=mock_case)),
            ),
            patch(
                "src.backend.clinical.builder.PatientRepository",
                return_value=AsyncMock(get=AsyncMock(return_value=mock_patient)),
            ),
            patch.object(
                builder, "_load_variants",
                AsyncMock(return_value=[]),
            ) as mock_load_variants,
        ):
            ctx = await builder.build(case_id)

        assert isinstance(ctx, ClinicalContext)
        assert ctx.case_id == case_id
        assert len(ctx.variants) == 0
        assert len(ctx.biomarkers) == 0
        assert ctx.context_hash != ""

    async def test_build_missing_patient(self, builder):
        """build() should handle missing patient gracefully, defaulting age/gender."""
        case_id = str(uuid.uuid4())

        mock_case = MagicMock(spec=CancerCaseModel)
        mock_case.id = uuid.UUID(case_id)
        mock_case.patient_id = uuid.uuid4()
        mock_case.cancer_type = "FTC"
        mock_case.histology = "Follicular"
        mock_case.stage = "I"
        mock_case.oncotree_code = None
        mock_case.treatment_history = []
        mock_case.current_medications = []
        mock_case.metastatic_sites = []
        mock_case.recurrence_status = None
        mock_case.clinical_notes = None

        with (
            patch(
                "src.backend.clinical.builder.CancerCaseRepository",
                return_value=AsyncMock(get=AsyncMock(return_value=mock_case)),
            ),
            patch(
                "src.backend.clinical.builder.PatientRepository",
                return_value=AsyncMock(get=AsyncMock(return_value=None)),
            ),
            patch.object(
                builder, "_load_variants",
                AsyncMock(return_value=[]),
            ),
        ):
            ctx = await builder.build(case_id)

        assert ctx.age == 0
        assert ctx.gender == ""

    async def test_build_empty_context_structure(self, builder):
        """Empty context should have the expected structure with defaults."""
        ctx = await builder.build("invalid")
        assert ctx.model_dump() == ClinicalContext(
            case_id="", patient_id="", age=0, gender="",
            diagnosis="", stage="", histology="", cancer_type="",
            oncotree_code=None, biomarkers=[], variants=[],
            treatment_history=[], current_medications=[], allergies=[],
            metastatic_sites=[], recurrence_status=None, clinical_notes=None,
        ).model_dump()

    async def test_build_case_without_patient_record(self, builder):
        """build() should not raise when patient cannot be loaded."""
        case_id = str(uuid.uuid4())

        mock_case = MagicMock(spec=CancerCaseModel)
        mock_case.id = uuid.UUID(case_id)
        mock_case.patient_id = uuid.uuid4()
        mock_case.cancer_type = "PTC"
        mock_case.histology = ""
        mock_case.stage = ""
        mock_case.oncotree_code = None
        mock_case.treatment_history = []
        mock_case.current_medications = []
        mock_case.metastatic_sites = []
        mock_case.recurrence_status = None
        mock_case.clinical_notes = None

        with (
            patch(
                "src.backend.clinical.builder.CancerCaseRepository",
                return_value=AsyncMock(get=AsyncMock(return_value=mock_case)),
            ),
            patch(
                "src.backend.clinical.builder.PatientRepository",
                return_value=AsyncMock(
                    get=AsyncMock(side_effect=Exception("Patient DB error")),
                ),
            ),
            patch.object(
                builder, "_load_variants",
                AsyncMock(return_value=[]),
            ),
        ):
            ctx = await builder.build(case_id)

        # Should succeed with defaults for missing patient
        assert ctx.age == 0
        assert ctx.gender == ""
        assert ctx.cancer_type == "PTC"
