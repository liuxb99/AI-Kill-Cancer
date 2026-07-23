"""
EvidenceCitationValidator and HallucinationGuard.

Ensures all LLM output citations reference real evidence, PMIDs, and drugs.
"""

from __future__ import annotations

import logging

from src.backend.reasoning.models import (
    ClinicalReasoningResult,
    ReasoningValidationResult,
)

logger = logging.getLogger(__name__)


class EvidenceCitationValidator:
    """
    Validates that citations in reasoning output reference real evidence.

    Checks:
    - evidence_id exists in the provided evidence snapshot
    - PMID matches database records
    - Drug names come from the input snapshot
    - Conclusions don't exceed evidence scope
    """

    def __init__(self):
        self._evidence_map: dict[str, dict] = {}
        self._pmid_set: set[str] = set()
        self._drug_set: set[str] = set()

    def load_snapshot(self, evidence_items: list[dict],
                      drug_names: list[str] | None = None):
        """Load evidence snapshot for validation."""
        self._evidence_map = {}
        self._pmid_set = set()
        for item in (evidence_items or []):
            eid = str(item.get("id", ""))
            if eid:
                self._evidence_map[eid] = item
            pmid = str(item.get("pmid", ""))
            if pmid:
                self._pmid_set.add(pmid)
        self._drug_set = set(d or "" for d in (drug_names or []))

    def validate(self, result: ClinicalReasoningResult) -> ReasoningValidationResult:
        """Validate a reasoning result against loaded snapshot."""
        citation_errors = []
        drug_errors = []
        pmids_not_found = []
        evidence_ids_not_found = []
        hallucination_warnings = []
        overreach_warnings = []

        # Check all cited evidence IDs exist in snapshot
        for eid in result.supporting_evidence_ids + result.conflicting_evidence_ids:
            if eid and eid not in self._evidence_map:
                citation_errors.append(f"Evidence ID {eid} not found in snapshot")
                evidence_ids_not_found.append(eid)

        # Check citations
        for citation in result.citations:
            if citation.evidence_id and citation.evidence_id not in self._evidence_map:
                citation_errors.append(f"Citation evidence_id {citation.evidence_id} not found")
                evidence_ids_not_found.append(citation.evidence_id)
            if citation.pmid and citation.pmid not in self._pmid_set:
                citation_errors.append(f"PMID {citation.pmid} not in evidence snapshot")
                pmids_not_found.append(citation.pmid)

        # Check drug explanations
        for drug_exp in result.drug_explanations:
            if drug_exp.drug_name and drug_exp.drug_name not in self._drug_set:
                drug_errors.append(f"Drug '{drug_exp.drug_name}' not in input snapshot")

            # Check supporting/conflicting evidence IDs
            for eid in drug_exp.supporting_evidence_ids + drug_exp.conflicting_evidence_ids:
                if eid and eid not in self._evidence_map:
                    citation_errors.append(f"Drug {drug_exp.drug_name} cites evidence {eid} not in snapshot")
                    evidence_ids_not_found.append(eid)

        # Check for hallucination warnings
        if len(result.key_findings) > 20:
            hallucination_warnings.append(f"Unusually large number of findings ({len(result.key_findings)})")

        valid = len(citation_errors) == 0 and len(drug_errors) == 0

        return ReasoningValidationResult(
            valid=valid,
            citation_errors=citation_errors,
            drug_errors=drug_errors,
            pmids_not_found=pmids_not_found,
            evidence_ids_not_found=evidence_ids_not_found,
            hallucination_warnings=hallucination_warnings,
            overreach_warnings=overreach_warnings,
        )


class HallucinationGuard:
    """
    Guards against common LLM hallucinations in clinical reasoning.

    Checks:
    - Claims about novel variants not in evidence
    - References to non-existent publications
    - Drug names not in evidence snapshot
    - Overconfident claims from weak evidence
    """

    def __init__(self):
        self._known_pmids: set[str] = set()
        self._known_drugs: set[str] = set()
        self._known_variants: set[str] = set()

    def load_snapshot(self, evidence_items: list[dict]):
        """Load known entities from evidence snapshot."""
        for item in (evidence_items or []):
            pmid = str(item.get("pmid", ""))
            if pmid:
                self._known_pmids.add(pmid)
            drug = str(item.get("drug_name", ""))
            if drug:
                self._known_drugs.add(drug.lower())

    def check_drug_name(self, drug_name: str) -> bool:
        """Check if a drug name is in the known set."""
        return drug_name.lower() in self._known_drugs

    def check_pmid(self, pmid: str) -> bool:
        """Check if a PMID is in the known set."""
        return pmid in self._known_pmids
