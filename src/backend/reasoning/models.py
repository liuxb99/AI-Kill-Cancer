"""
Pydantic models for clinical reasoning results.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict


class ReasoningEvidenceCitation(BaseModel):
    """A citation of evidence in a reasoning result."""
    evidence_id: str = ""
    pmid: str = ""
    citation_text: str = ""
    validated: bool = False


class ReasoningDrugExplanation(BaseModel):
    """Explanation for a drug in the reasoning output."""
    drug_name: str = ""
    explanation: str = ""
    supporting_evidence_ids: list[str] = []
    conflicting_evidence_ids: list[str] = []
    resistance_evidence_ids: list[str] = []
    limitations: list[str] = []


class SafetyNotice(BaseModel):
    """Safety notice for clinical reasoning output."""
    notice: str = "This analysis is for research and evidence organization purposes only. "        "It is NOT a clinical decision support system and must not be used for diagnosis or treatment decisions."
    disclaimer_version: str = "1.0"


class ClinicalReasoningResult(BaseModel):
    """Structured output from a clinical reasoning run."""
    model_config = ConfigDict(from_attributes=True)

    id: str = ""
    case_id: Optional[str] = None
    user_question: str = ""
    summary: str = ""
    key_findings: list[str] = []
    supporting_evidence_ids: list[str] = []
    conflicting_evidence_ids: list[str] = []
    drug_explanations: list[ReasoningDrugExplanation] = []
    uncertainties: list[str] = []
    missing_information: list[str] = []
    limitations: list[str] = []
    safety_notice: SafetyNotice = SafetyNotice()
    citations: list[ReasoningEvidenceCitation] = []


class ReasoningRunResponse(BaseModel):
    """API response for a reasoning run."""
    run_id: str = ""
    status: str = ""  # completed, pending, failed, rejected
    reasoning: Optional[ClinicalReasoningResult] = None
    validation_result: Optional["ReasoningValidationResult"] = None
    message: str = ""


class ReasoningValidationResult(BaseModel):
    """Result of validating a reasoning run."""
    valid: bool = False
    citation_errors: list[str] = []
    drug_errors: list[str] = []
    pmids_not_found: list[str] = []
    evidence_ids_not_found: list[str] = []
    hallucination_warnings: list[str] = []
    overreach_warnings: list[str] = []
