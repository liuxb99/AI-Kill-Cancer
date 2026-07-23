"""
ClinicalContext model — a frozen snapshot of patient, case, variant, and
treatment data used for reasoning, ranking, and reporting.

This model carries a context_hash (SHA256) for full traceability of the
exact data state that was fed into any clinical decision support step.
"""

from __future__ import annotations

import hashlib
import json

from pydantic import BaseModel, Field


class ClinicalContext(BaseModel):
    """A frozen clinical context snapshot for reasoning and reporting.

    Collects all relevant patient, case, variant, and treatment information
    into one immutable data structure that can be hashed for auditability.
    """

    case_id: str
    patient_id: str

    age: int
    gender: str

    diagnosis: str
    stage: str
    histology: str
    cancer_type: str
    oncotree_code: str | None = None

    biomarkers: list[dict] = Field(default_factory=list)
    variants: list[dict] = Field(
        default_factory=list,
        description=(
            "Each item contains gene_symbol, hgvs, protein_change, vaf, "
            "and clinical_significance."
        ),
    )
    treatment_history: list[dict] = Field(default_factory=list)
    current_medications: list[dict] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)

    ecog_score: int | None = None
    metastatic_sites: list[str] = Field(default_factory=list)
    recurrence_status: str | None = None
    clinical_notes: str | None = None

    context_hash: str = ""

    def freeze(self) -> str:
        """Compute and return the SHA256 of the serialised context.

        The hash is computed from all fields except *context_hash* itself,
        serialised as a JSON string with sorted keys for reproducibility.
        The result is stored in ``self.context_hash`` and also returned.
        """
        payload = self.model_dump(exclude={"context_hash"})
        self.context_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode()
        ).hexdigest()
        return self.context_hash
