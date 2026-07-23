"""
CaseContextBuilder — assembles a frozen ClinicalContext from database records.

Loads a cancer case, its patient, and associated variants from the database
and populates a ClinicalContext instance that can be used for reasoning,
ranking, and reporting.
"""

from __future__ import annotations

import logging
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.clinical.models import ClinicalContext
from src.backend.domain.cancer_case import CancerCaseModel
from src.backend.domain.enums import SexEnum
from src.backend.domain.patient import PatientModel
from src.backend.domain.sequencing import SequencingTestModel
from src.backend.domain.specimen import SpecimenModel
from src.backend.domain.variant import VariantModel
from src.backend.repositories.cancer_case_repo import CancerCaseRepository
from src.backend.repositories.patient_repo import PatientRepository

logger = logging.getLogger(__name__)


class CaseContextBuilder:
    """Builds a ClinicalContext by loading real data from the database.

    Attributes:
        db: The async SQLAlchemy session used for all queries.
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialise the builder with a database session.

        Args:
            db: An active async SQLAlchemy session.
        """
        self.db = db

    async def build(self, case_id: str) -> ClinicalContext:
        """Assemble a ClinicalContext from database records.

        Loads the cancer case, its patient, and all associated variants,
        then constructs and freezes a ClinicalContext snapshot.

        If the *case_id* is invalid (not a UUID or not found) an empty
        ``ClinicalContext`` is returned — no exception is raised.
        Fields that are ``NULL`` in the database are safely
        mapped to ``None`` or an empty list.

        Args:
            case_id: The UUID string of the cancer case to load.

        Returns:
            A frozen ``ClinicalContext`` instance with a computed
            ``context_hash``.
        """
        # ── Validate case_id ──────────────────────────────────────────────
        if not case_id:
            logger.warning("Empty or None case_id provided")
            return self._empty_context()

        try:
            cid = uuid.UUID(case_id) if isinstance(case_id, str) else case_id
        except (ValueError, AttributeError):
            logger.warning("Invalid case_id provided: %s", case_id)
            return self._empty_context()

        # ── Load cancer case ──────────────────────────────────────────────
        case_repo = CancerCaseRepository(self.db)
        case = await case_repo.get(cid)
        if case is None:
            logger.info("Cancer case not found: %s", case_id)
            return self._empty_context()

        # ── Load patient ──────────────────────────────────────────────────
        patient: PatientModel | None = None
        try:
            pid = (
                uuid.UUID(str(case.patient_id))
                if not isinstance(case.patient_id, uuid.UUID)
                else case.patient_id
            )
            patient_repo = PatientRepository(self.db)
            patient = await patient_repo.get(pid)
        except Exception as exc:
            logger.warning("Could not load patient for case %s: %s", case_id, exc)

        # ── Load variants ─────────────────────────────────────────────────
        variants: list[VariantModel] = await self._load_variants(cid)

        # ── Assemble ClinicalContext ──────────────────────────────────────
        context = self._assemble(case, patient, variants, case_id)
        context.freeze()
        return context

    # ── Internal helpers ─────────────────────────────────────────────────

    async def _load_variants(self, case_id: uuid.UUID) -> list[VariantModel]:
        """Fetch all variants belonging to a cancer case.

        Traverses the relationship chain:  Case → Specimen → SequencingTest
        → Variant.

        Args:
            case_id: The UUID of the cancer case.

        Returns:
            A list of ``VariantModel`` instances (may be empty).
        """
        try:
            stmt = (
                select(VariantModel)
                .join(
                    SequencingTestModel,
                    VariantModel.sequencing_test_id == SequencingTestModel.id,
                )
                .join(
                    SpecimenModel,
                    SequencingTestModel.specimen_id == SpecimenModel.id,
                )
                .where(SpecimenModel.case_id == case_id)
            )
            result = await self.db.execute(stmt)
            return list(result.scalars().all())
        except Exception as exc:
            logger.warning("Failed to load variants for case %s: %s", case_id, exc)
            return []

    def _assemble(
        self,
        case: CancerCaseModel,
        patient: PatientModel | None,
        variants: list[VariantModel],
        case_id: str,
    ) -> ClinicalContext:
        """Map database models to a ``ClinicalContext``.

        Args:
            case: The loaded cancer case.
            patient: The loaded patient (may be None).
            variants: The list of associated variants.
            case_id: The original case ID string.

        Returns:
            A populated (but not yet frozen) ``ClinicalContext``.
        """
        # ── Patient-derived fields ────────────────────────────────────────
        age = self._resolve_age(patient)
        gender = self._resolve_gender(patient)

        # ── Case-derived fields ───────────────────────────────────────────
        cancer_type = self._safe_str(case.cancer_type)
        histology = case.histology or ""
        stage = case.stage or ""
        diagnosis = (
            f"{cancer_type} ({histology})" if histology else cancer_type
        )
        oncotree_code = case.oncotree_code

        treatment_history = (
            case.treatment_history
            if isinstance(case.treatment_history, list)
            else []
        )
        current_medications = (
            case.current_medications
            if isinstance(case.current_medications, list)
            else []
        )
        metastatic_sites = (
            case.metastatic_sites
            if isinstance(case.metastatic_sites, list)
            else []
        )
        recurrence_status = case.recurrence_status
        clinical_notes = case.clinical_notes

        # ── Variant-derived fields ────────────────────────────────────────
        biomarkers: list[dict] = []
        variant_dicts: list[dict] = []

        for v in variants:
            v_item = {
                "gene_symbol": v.gene_symbol or "",
                "hgvs": v.hgvs_p or v.hgvs_c or "",
                "protein_change": v.protein_change or "",
                "vaf": float(v.vaf) if v.vaf is not None else None,
                "clinical_significance": v.clinical_significance or "",
            }
            variant_dicts.append(v_item)

            # A biomarker is a simplified view of the same data
            if v.gene_symbol:
                biomarkers.append(
                    {
                        "gene": v.gene_symbol,
                        "value": v.protein_change or v.hgvs_p or "",
                    }
                )

        return ClinicalContext(
            case_id=str(case.id),
            patient_id=str(case.patient_id),
            age=age,
            gender=gender,
            diagnosis=diagnosis,
            stage=stage,
            histology=histology,
            cancer_type=cancer_type,
            oncotree_code=oncotree_code,
            biomarkers=biomarkers,
            variants=variant_dicts,
            treatment_history=treatment_history,
            current_medications=current_medications,
            allergies=[],
            metastatic_sites=metastatic_sites,
            recurrence_status=recurrence_status,
            clinical_notes=clinical_notes,
        )

    # ── Field-level helpers ──────────────────────────────────────────────

    @staticmethod
    def _resolve_age(patient: PatientModel | None) -> int:
        """Calculate age from the patient's birth year, or return 0."""
        if patient is None:
            return 0
        if patient.birth_year is not None:
            try:
                return date.today().year - patient.birth_year
            except (ValueError, OverflowError):
                pass
        return 0

    @staticmethod
    def _resolve_gender(patient: PatientModel | None) -> str:
        """Return the patient's sex as a string, or empty string."""
        if patient is None or patient.sex is None:
            return ""
        if isinstance(patient.sex, SexEnum):
            return patient.sex.value
        return str(patient.sex)

    @staticmethod
    def _safe_str(value) -> str:
        """Convert an enum or string value to a plain string."""
        if value is None:
            return ""
        if hasattr(value, "value"):
            return str(value.value)
        return str(value)

    @staticmethod
    def _empty_context() -> ClinicalContext:
        """Return a ClinicalContext with all empty/default values."""
        return ClinicalContext(
            case_id="",
            patient_id="",
            age=0,
            gender="",
            diagnosis="",
            stage="",
            histology="",
            cancer_type="",
            oncotree_code=None,
            biomarkers=[],
            variants=[],
            treatment_history=[],
            current_medications=[],
            allergies=[],
            metastatic_sites=[],
            recurrence_status=None,
            clinical_notes=None,
        )
