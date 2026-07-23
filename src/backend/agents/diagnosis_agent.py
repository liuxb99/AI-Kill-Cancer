"""
DiagnosisAgent — diagnostic consistency and correctness analysis for the
Phase 2b multi-agent system.

Evaluates the consistency of diagnosis-related fields in a
:class:`ClinicalContext` snapshot, cross-references biomarkers against
diagnostic evidence in the :class:`EvidenceBundle`, and returns an
:class:`AgentOpinion` with the agent's assessment.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from src.backend.agents.base import BaseAgent
from src.backend.agents.models import AgentOpinion
from src.backend.clinical.evidence_models import EvidenceBundle
from src.backend.clinical.models import ClinicalContext

# ─── Helper constants ──────────────────────────────────────────────────────────

_STAGE_PATTERN_HELP = (
    "Expected format example: 'Stage IIB', 'IV', 'III', 'I', 'IA', 'IIIA'"
)

_COMMON_HISTOLOGY_MAP: dict[str, list[str]] = {
    "lung": [
        "adenocarcinoma",
        "squamous cell carcinoma",
        "large cell carcinoma",
        "small cell carcinoma",
        "non-small cell lung cancer",
        "NSCLC",
        "SCLC",
        "carcinoid",
    ],
    "breast": [
        "invasive ductal carcinoma",
        "invasive lobular carcinoma",
        "ductal carcinoma in situ",
        "lobular carcinoma in situ",
        "triple-negative",
        "HER2-positive",
        "HR-positive",
        "inflammatory",
    ],
    "colorectal": [
        "adenocarcinoma",
        "mucinous adenocarcinoma",
        "signet ring cell",
        "neuroendocrine",
        "squamous cell",
    ],
    "prostate": [
        "adenocarcinoma",
        "small cell carcinoma",
        "neuroendocrine",
        "squamous",
        "sarcomatoid",
    ],
    "melanoma": [
        "superficial spreading",
        "nodular",
        "lentigo maligna",
        "acral lentiginous",
        "desmoplastic",
        "mucosal",
    ],
    "liver": [
        "hepatocellular carcinoma",
        "cholangiocarcinoma",
        "fibrolamellar",
        "hepatoblastoma",
    ],
    "pancreas": [
        "ductal adenocarcinoma",
        "neuroendocrine",
        "acinar cell carcinoma",
        "pancreatoblastoma",
    ],
    "ovary": [
        "serous carcinoma",
        "mucinous carcinoma",
        "endometrioid carcinoma",
        "clear cell carcinoma",
        "granulosa cell",
        "germ cell",
    ],
    "kidney": [
        "clear cell RCC",
        "papillary RCC",
        "chromophobe RCC",
        "oncocytoma",
        "collecting duct",
    ],
    "stomach": [
        "adenocarcinoma",
        "diffuse-type",
        "intestinal-type",
        "signet ring cell",
        "gastrointestinal stromal tumor",
        "GIST",
        "MALT",
        "neuroendocrine",
    ],
    "bladder": [
        "urothelial carcinoma",
        "squamous cell carcinoma",
        "adenocarcinoma",
        "small cell carcinoma",
        "sarcomatoid",
    ],
    "cervix": [
        "squamous cell carcinoma",
        "adenocarcinoma",
        "adenosquamous",
        "small cell",
        "neuroendocrine",
    ],
    "head and neck": [
        "squamous cell carcinoma",
        "HNSCC",
        "adenocarcinoma",
        "mucoepidermoid",
        "adenoid cystic",
        "lymphoma",
    ],
    "brain": [
        "glioblastoma",
        "astrocytoma",
        "oligodendroglioma",
        "ependymoma",
        "medulloblastoma",
        "meningioma",
        "GBM",
        "glioma",
    ],
}

_DIAGNOSTIC_EVIDENCE_TYPES = {"diagnostic", "prognostic"}

_KNOWN_STAGE_PREFIXES = {
    "I", "II", "III", "IV",
    "IA", "IB", "IC",
    "IIA", "IIB", "IIC",
    "IIIA", "IIIB", "IIIC",
    "IVA", "IVB", "IVC",
}


# ─── Agent implementation ──────────────────────────────────────────────────────


class DiagnosisAgent(BaseAgent):
    """Analyse the consistency and correctness of diagnosis information.

    This agent evaluates the diagnostic fields in a frozen
    :class:`ClinicalContext` snapshot (*diagnosis*, *cancer_type*,
    *histology*, *stage*) for internal consistency, cross-references
    patient biomarkers against diagnostic evidence from the
    :class:`EvidenceBundle`, and produces a structured
    :class:`AgentOpinion` summarising its findings.

    Parameters
    ----------
    db : AsyncSession
        SQLAlchemy asynchronous database session.

    Attributes
    ----------
    agent_type : str
        Unique identifier ``"diagnosis"``.
    agent_version : str
        Semantic version ``"1.0.0"``.
    """

    agent_type: str = "diagnosis"
    agent_version: str = "1.0.0"

    async def analyze(
        self,
        context: ClinicalContext,
        evidence: EvidenceBundle,
    ) -> AgentOpinion:
        """Analyse diagnosis information and return a structured opinion.

        The analysis performs the following steps:

        1. **Field presence check** — ensures that *diagnosis*,
           *cancer_type*, *histology*, and *stage* are all populated.
        2. **Consistency evaluation** — checks *cancer_type* against
           *diagnosis* and *histology* for commonly expected patterns;
           validates the *stage* format.
        3. **Biomarker cross-reference** — matches each biomarker in
           *context.biomarkers* against diagnostic/prognostic evidence
           items in the bundle.
        4. **Evidence-based assessment** — filters the evidence bundle
           for items of type ``"diagnostic"`` or ``"prognostic"`` and
           evaluates whether the evidence supports or conflicts with the
           recorded diagnosis.

        Parameters
        ----------
        context : ClinicalContext
            Frozen clinical snapshot containing ``diagnosis``,
            ``cancer_type``, ``histology``, ``stage``, and
            ``biomarkers``.
        evidence : EvidenceBundle
            Aggregated evidence items from all configured knowledge
            sources.

        Returns
        -------
        AgentOpinion
            A structured opinion with a summary of consistency findings,
            biomarker matches, supporting/opposing arguments, and
            references.
        """
        created_at = datetime.now(UTC).isoformat()

        # ── Step 1: Field presence ────────────────────────────────────────
        missing_fields = self._check_missing_fields(context)

        # ── Step 2: Consistency checks ────────────────────────────────────
        consistency_issues: list[str] = []
        if not missing_fields:
            consistency_issues = self._check_consistency(context)

        # ── Step 3: Biomarker cross-reference ─────────────────────────────
        biomarker_findings = self._cross_reference_biomarkers(
            context=context,
            evidence=evidence,
        )

        # ── Step 4: Evidence-based diagnostic assessment ──────────────────
        diagnostic_evidence_assessment = self._assess_diagnostic_evidence(
            context=context,
            evidence=evidence,
        )

        # ── Build summary ─────────────────────────────────────────────────
        summary_parts: list[str] = [
            f"Diagnosis assessment for {context.cancer_type} "
            f"({context.diagnosis})."
        ]

        if missing_fields:
            summary_parts.append(
                f"Missing field(s): {', '.join(sorted(missing_fields))}."
            )

        if consistency_issues:
            summary_parts.append(
                f"Consistency issue(s) detected: "
                f"{'; '.join(consistency_issues[:3])}."
                f"{' (and more)' if len(consistency_issues) > 3 else ''}"
            )
        elif not missing_fields:
            summary_parts.append("Diagnosis fields appear internally consistent.")

        matched_biomarkers = [
            bf for bf in biomarker_findings if bf.get("evidence_matched")
        ]
        if matched_biomarkers:
            summary_parts.append(
                f"{len(matched_biomarkers)} biomarker(s) matched to "
                f"diagnostic evidence."
            )

        diagnostic_refs = diagnostic_evidence_assessment.get("references", [])
        if diagnostic_refs:
            summary_parts.append(
                f"Found {len(diagnostic_refs)} diagnostic evidence item(s) "
                f"in the bundle."
            )

        summary = " ".join(summary_parts)

        # ── Build pros / cons ─────────────────────────────────────────────
        pros: list[str] = []
        cons: list[str] = []

        if not missing_fields and not consistency_issues:
            pros.append(
                "Diagnosis, cancer_type, histology, and stage are all "
                "populated and internally consistent."
            )
        elif missing_fields:
            cons.append(
                f"Required diagnostic field(s) missing: "
                f"{', '.join(sorted(missing_fields))}."
            )

        if consistency_issues:
            for issue in consistency_issues:
                cons.append(issue)

        if matched_biomarkers:
            matched_names = [
                bf["biomarker"]
                for bf in matched_biomarkers
            ]
            pros.append(
                f"Biomarker(s) {', '.join(sorted(set(matched_names)))} "
                f"have corresponding diagnostic evidence, supporting the "
                f"recorded diagnosis."
            )

        unmatched_biomarkers = [
            bf for bf in biomarker_findings if not bf.get("evidence_matched")
        ]
        if unmatched_biomarkers:
            unmatched_names = [
                bf["biomarker"]
                for bf in unmatched_biomarkers
            ]
            cons.append(
                f"Biomarker(s) {', '.join(sorted(set(unmatched_names)))} "
                f"lack matching diagnostic evidence — consider further "
                f"investigation."
            )

        supporting = diagnostic_evidence_assessment.get("supporting", 0)
        conflicting = diagnostic_evidence_assessment.get("conflicting", 0)
        if supporting > 0:
            pros.append(
                f"{supporting} diagnostic evidence item(s) support the "
                f"recorded diagnosis."
            )
        if conflicting > 0:
            cons.append(
                f"{conflicting} diagnostic evidence item(s) conflict with "
                f"or raise questions about the recorded diagnosis."
            )

        if not diagnostic_refs and not biomarker_findings:
            cons.append(
                "No diagnostic or prognostic evidence available in the "
                "evidence bundle to corroborate the diagnosis."
            )

        # ── Confidence ────────────────────────────────────────────────────
        confidence = self._derive_confidence(
            missing_fields=missing_fields,
            consistency_issues=consistency_issues,
            diagnostic_evidence_assessment=diagnostic_evidence_assessment,
            biomarker_findings=biomarker_findings,
        )

        # ── Collect references ────────────────────────────────────────────
        references: list[dict[str, str]] = list(diagnostic_refs)
        for bf in biomarker_findings:
            for ref in bf.get("references", []):
                if ref not in references:
                    references.append(ref)

        return AgentOpinion(
            agent_type=self.agent_type,
            agent_version=self.agent_version,
            summary=summary,
            pros=pros,
            cons=cons,
            confidence=confidence,
            references=references,
            context_hash=context.context_hash or None,
            created_at=created_at,
        )

    # ── Private helpers ───────────────────────────────────────────────────

    @staticmethod
    def _check_missing_fields(context: ClinicalContext) -> list[str]:
        """Identify which diagnostic fields are missing or empty.

        Parameters
        ----------
        context : ClinicalContext
            The clinical context to inspect.

        Returns
        -------
        list[str]
            A list of field names that are empty or whitespace-only.
        """
        missing: list[str] = []
        for field in ("diagnosis", "cancer_type", "histology", "stage"):
            value = getattr(context, field, None)
            if not value or (isinstance(value, str) and not value.strip()):
                missing.append(field)
        return missing

    @staticmethod
    def _check_consistency(context: ClinicalContext) -> list[str]:
        """Evaluate internal consistency of diagnosis fields.

        Checks performed:

        - Whether *cancer_type* appears within the *diagnosis* string
          (case-insensitive).
        - Whether *histology* is a recognised subtype for the given
          *cancer_type* (based on a built-in map of common associations).
        - Whether *stage* matches one of the known clinical stage
          formats.

        Parameters
        ----------
        context : ClinicalContext
            The clinical context (must have non-empty *diagnosis*,
            *cancer_type*, *histology*, and *stage*).

        Returns
        -------
        list[str]
            A list of human-readable consistency issue descriptions.
        """
        issues: list[str] = []
        diag_lower = context.diagnosis.lower()
        cancer_lower = context.cancer_type.lower()

        # ── cancer_type in diagnosis ──────────────────────────────────────
        if cancer_lower not in diag_lower:
            # Check partial match: individual words of cancer_type
            cancer_words = cancer_lower.replace("-", " ").split()
            if not any(word in diag_lower for word in cancer_words if len(word) > 2):
                issues.append(
                    f"cancer_type '{context.cancer_type}' is not explicitly "
                    f"mentioned in the diagnosis field "
                    f"'{context.diagnosis}'."
                )

        # ── histology vs. cancer_type ─────────────────────────────────────
        histology_lower = context.histology.lower().strip()
        expected_histologies = _COMMON_HISTOLOGY_MAP.get(cancer_lower)

        if expected_histologies is not None:
            if not any(
                expected.lower() in histology_lower
                or histology_lower in expected.lower()
                for expected in expected_histologies
            ):
                issues.append(
                    f"histology '{context.histology}' is not among the "
                    f"commonly expected subtypes for "
                    f"{context.cancer_type}."
                )

        # ── Stage format ──────────────────────────────────────────────────
        stage_upper = context.stage.upper().strip()
        # Remove leading "STAGE " prefix for comparison
        stage_core = stage_upper
        if stage_core.startswith("STAGE "):
            stage_core = stage_core[6:].strip()

        if stage_core not in _KNOWN_STAGE_PREFIXES:
            issues.append(
                f"stage '{context.stage}' does not match a recognised "
                f"clinical stage format. {_STAGE_PATTERN_HELP}"
            )

        return issues

    @staticmethod
    def _cross_reference_biomarkers(
        context: ClinicalContext,
        evidence: EvidenceBundle,
    ) -> list[dict[str, Any]]:
        """Cross-reference patient biomarkers against diagnostic evidence.

        For each biomarker in *context.biomarkers*, the method looks up
        the biomarker name (or associated gene) in the evidence bundle
        and records whether matching diagnostic/prognostic evidence
        exists.

        Parameters
        ----------
        context : ClinicalContext
            The clinical context containing ``biomarkers``.
        evidence : EvidenceBundle
            The aggregated evidence bundle.

        Returns
        -------
        list[dict]
            A list of findings, each with keys:
            - ``biomarker`` — the biomarker identifier.
            - ``evidence_matched`` — ``True`` if relevant evidence found.
            - ``references`` — list of reference dicts from matched items.
        """
        findings: list[dict[str, Any]] = []

        if not context.biomarkers:
            return findings

        # Collect all diagnostic/prognostic evidence items keyed by gene
        diagnostic_items = [
            item
            for item in evidence.items
            if item.evidence_type.lower() in _DIAGNOSTIC_EVIDENCE_TYPES
        ]

        for bio in context.biomarkers:
            if not isinstance(bio, dict):
                continue

            biomarker_name = (
                bio.get("name")
                or bio.get("gene_symbol")
                or bio.get("biomarker")
                or ""
            )
            if not biomarker_name:
                continue

            biomarker_lower = biomarker_name.lower()

            # Find matching evidence items
            matched_items = [
                item
                for item in diagnostic_items
                if item.gene_symbol
                and item.gene_symbol.lower() == biomarker_lower
            ]

            refs: list[dict[str, str]] = []
            for item in matched_items:
                ref: dict[str, str] = {
                    "source": item.source,
                    "citation": item.citation or f"{item.source} record",
                }
                if item.url:
                    ref["url"] = item.url
                refs.append(ref)

            findings.append({
                "biomarker": biomarker_name,
                "evidence_matched": bool(matched_items),
                "references": refs,
            })

        return findings

    @staticmethod
    def _assess_diagnostic_evidence(
        context: ClinicalContext,
        evidence: EvidenceBundle,
    ) -> dict[str, Any]:
        """Assess the evidence bundle for diagnostic support.

        Filters the evidence bundle to items classified as ``"diagnostic"``
        or ``"prognostic"`` and evaluates whether the evidence supports
        or conflicts with the recorded diagnosis.

        Parameters
        ----------
        context : ClinicalContext
            The clinical context (used for the diagnosis text).
        evidence : EvidenceBundle
            The aggregated evidence bundle.

        Returns
        -------
        dict
            A dictionary with:
            - ``supporting`` — count of supporting items.
            - ``conflicting`` — count of conflicting items.
            - ``references`` — list of reference dicts for all relevant
              diagnostic items.
        """
        supporting = 0
        conflicting = 0
        references: list[dict[str, str]] = []

        diagnostic_items = [
            item
            for item in evidence.items
            if item.evidence_type.lower() in _DIAGNOSTIC_EVIDENCE_TYPES
        ]

        for item in diagnostic_items:
            ref: dict[str, str] = {
                "source": item.source,
                "citation": item.citation or f"{item.source} record",
            }
            if item.url:
                ref["url"] = item.url
            references.append(ref)

            # Determine support/conflict based on evidence_direction
            direction = (item.evidence_direction or "").lower()
            disease = (item.disease or "").lower()

            if direction == "supporting":
                supporting += 1
            elif direction == "conflicting":
                conflicting += 1
            elif direction == "" or direction == "neutral":
                # If direction is empty but the disease matches the
                # patient's cancer type, treat as supporting
                if disease and context.cancer_type.lower() in disease:
                    supporting += 1

        return {
            "supporting": supporting,
            "conflicting": conflicting,
            "references": references,
        }

    @staticmethod
    def _derive_confidence(
        missing_fields: list[str],
        consistency_issues: list[str],
        diagnostic_evidence_assessment: dict[str, Any],
        biomarker_findings: list[dict[str, Any]],
    ) -> str:
        """Derive an overall confidence level for the agent's opinion.

        Returns ``"high"`` when all fields are present, no consistency
        issues found, and there is diagnostic evidence supporting the
        diagnosis; ``"low"`` when critical fields are missing or there
        are significant consistency conflicts with no corroborating
        evidence; otherwise ``"medium"``.

        Parameters
        ----------
        missing_fields : list[str]
            List of missing field names.
        consistency_issues : list[str]
            List of consistency issue descriptions.
        diagnostic_evidence_assessment : dict
            Output of ``_assess_diagnostic_evidence``.
        biomarker_findings : list[dict]
            Output of ``_cross_reference_biomarkers``.

        Returns
        -------
        str
            ``"high"``, ``"medium"``, or ``"low"``.
        """
        if missing_fields:
            return "low"

        has_supporting_evidence = (
            diagnostic_evidence_assessment.get("supporting", 0) > 0
        )
        any_biomarker_matched = any(
            bf.get("evidence_matched") for bf in biomarker_findings
        )

        if not consistency_issues and (has_supporting_evidence or any_biomarker_matched):
            return "high"

        if consistency_issues and not has_supporting_evidence:
            return "low"

        return "medium"


__all__ = [
    "DiagnosisAgent",
]
