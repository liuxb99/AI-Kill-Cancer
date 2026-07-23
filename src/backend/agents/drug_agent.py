"""DrugAgent — drug recommendation and analysis agent.

Identifies potentially effective drugs based on the patient's molecular
variants and available evidence, while taking into account prior treatment
history, current medications, and known allergies / contraindications.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from src.backend.agents.base import BaseAgent
from src.backend.agents.models import AgentOpinion
from src.backend.clinical.evidence_models import EvidenceBundle
from src.backend.clinical.models import ClinicalContext

# ─── Helper constants ──────────────────────────────────────────────────────────

_SUPPORTING_DIRECTIONS = {"supporting", "positive", "sensitive"}


def _gene_symbols(variants: list[dict]) -> set[str]:
    """Return the set of gene symbols present in *variants*."""
    return {v.get("gene_symbol", "") for v in variants if v.get("gene_symbol")}


def _used_drugs(treatment_history: list[dict]) -> set[str]:
    """Collect all drug names the patient has previously received."""
    drugs: set[str] = set()
    for tx in treatment_history:
        regimen = tx.get("regimen") or tx.get("treatment") or ""
        if regimen:
            # regimen may be a single drug or a combination; add as-is
            drugs.add(regimen.lower().strip())
        # Some records list individual drugs
        for key in ("drugs", "medications", "agents"):
            entries = tx.get(key)
            if isinstance(entries, list):
                for entry in entries:
                    if isinstance(entry, str):
                        drugs.add(entry.lower().strip())
    return drugs


class DrugAgent(BaseAgent):
    """Agent that analyses drug options for a clinical context.

    Evaluates up to three dimensions:

    1. **Evidence-matched drugs** — drugs referenced in the evidence bundle
       that target genes for which the patient carries variants.
    2. **Prior treatment** — drugs the patient has already received, which
       may inform resistance or re-challenge considerations.
    3. **Contraindications** — allergies, current medications, and
       comorbidities that may preclude certain drugs.

    The agent returns a structured :class:`AgentOpinion` listing recommended
    drugs along with supporting and opposing arguments and traceable
    references.
    """

    agent_type: str = "drug"
    agent_version: str = "1.0.0"

    async def analyze(
        self,
        context: ClinicalContext,
        evidence: EvidenceBundle,
    ) -> AgentOpinion:
        """Analyse drug options for the given clinical context.

        Parameters
        ----------
        context : ClinicalContext
            Frozen patient / case snapshot containing *variants*,
            *treatment_history*, *current_medications*, and *allergies*.
        evidence : EvidenceBundle
            Aggregated evidence items from knowledge sources. Items
            with a ``drug_name`` are candidates for recommendation.

        Returns
        -------
        AgentOpinion
            Structured opinion with a plain-text summary of drug
            recommendations, supporting (pros) and opposing (cons)
            arguments, and a confidence rating.
        """
        # ── 1. Gather patient-level data ──────────────────────────────────
        patient_genes = _gene_symbols(context.variants)
        previously_used = _used_drugs(context.treatment_history)
        allergies_lower = {a.lower().strip() for a in context.allergies}
        current_rx_names: set[str] = set()
        for med in context.current_medications:
            name = med.get("name") or med.get("drug_name") or ""
            if name:
                current_rx_names.add(name.lower().strip())

        # ── 2. Organise evidence by drug ──────────────────────────────────
        # Map drug_name → list of evidence items (as plain dicts)
        drug_evidence: dict[str, list[dict[str, Any]]] = {}
        for item in evidence.items:
            drug = item.drug_name
            if not drug:
                continue
            drug_evidence.setdefault(drug.lower().strip(), []).append(
                item.model_dump()
            )

        # ── 3. Build candidate-drug analysis ──────────────────────────────
        pros: list[str] = []
        cons: list[str] = []
        references: list[dict[str, Any]] = []

        recommended_drugs: list[str] = []
        excluded_drugs: list[str] = []

        for drug_name_lower, ev_items in drug_evidence.items():
            # Determine which genes this drug is associated with
            associated_genes: set[str] = set()
            for ev in ev_items:
                gene = ev.get("gene_symbol")
                if gene:
                    associated_genes.add(gene)

            # Check if the drug targets any of the patient's genes
            matched_genes = associated_genes & patient_genes
            if not matched_genes:
                continue

            # ── Contraindication checks ───────────────────────────────────
            contraindicated_reasons: list[str] = []

            # Allergy check
            for allergy in allergies_lower:
                if allergy in drug_name_lower or drug_name_lower in allergy:
                    contraindicated_reasons.append(
                        f"allergy to {allergy}"
                    )

            # Current medication conflict check (simple name overlap)
            for curr_rx in current_rx_names:
                if curr_rx == drug_name_lower:
                    contraindicated_reasons.append(
                        "already listed in current medications"
                    )

            # Check comorbidities that may contraindicate
            # (basic keyword match against clinical_notes and diagnosis)
            if context.clinical_notes:
                notes_lower = context.clinical_notes.lower()
                # Common contraindication keywords
                if "liver" in notes_lower or "hepatic" in notes_lower:
                    contraindicated_reasons.append(
                        "possible hepatic impairment noted in clinical notes"
                    )
                if "kidney" in notes_lower or "renal" in notes_lower:
                    contraindicated_reasons.append(
                        "possible renal impairment noted in clinical notes"
                    )

            if contraindicated_reasons:
                excluded_drugs.append(drug_name_lower)
                reasons = "; ".join(contraindicated_reasons)
                cons.append(
                    f"{drug_name_lower.title()} excluded: {reasons}."
                )
                continue

            # ── Prior treatment assessment ────────────────────────────────
            prior_use = drug_name_lower in previously_used
            if prior_use:
                # Check if prior response was positive (from treatment_history)
                prior_response = self._find_prior_response(
                    drug_name_lower, context.treatment_history
                )
                if prior_response == "progressive":
                    cons.append(
                        f"{drug_name_lower.title()} previously used with "
                        f"progressive disease — likely ineffective."
                    )
                    continue
                if prior_response == "stable":
                    cons.append(
                        f"{drug_name_lower.title()} previously used with "
                        f"stable disease — may still be viable."
                    )

            # ── Build recommendation ──────────────────────────────────────
            recommended_drugs.append(drug_name_lower)
            gene_list = ", ".join(sorted(matched_genes))
            total_ev = len(ev_items)
            supporting_count = sum(
                1 for ev in ev_items
                if (ev.get("evidence_direction") or "").lower()
                in _SUPPORTING_DIRECTIONS
            )

            if prior_use:
                pros.append(
                    f"{drug_name_lower.title()} previously received — "
                    f"re-challenge may be considered (targets {gene_list})."
                )
            else:
                pros.append(
                    f"{drug_name_lower.title()} targets patient variant(s) "
                    f"in {gene_list} ({supporting_count}/{total_ev} evidence "
                    f"items supporting)."
                )

            # Add references for this drug
            for ev in ev_items:
                ref: dict[str, Any] = {
                    "source": ev["source"],
                    "citation": (
                        ev.get("citation")
                        or ev.get("description", "")
                        or f"{ev['source']} evidence for {drug_name_lower}"
                    ),
                }
                if ev.get("url"):
                    ref["url"] = ev["url"]
                # Avoid duplicate references
                if ref not in references:
                    references.append(ref)

        # ── 4. Summary ────────────────────────────────────────────────────
        summary_parts: list[str] = []

        if recommended_drugs:
            summary_parts.append(
                f"Recommended {len(recommended_drugs)} drug(s) based on "
                f"variant-evidence match: "
                f"{', '.join(d.title() for d in recommended_drugs)}."
            )
        else:
            summary_parts.append(
                "No drug matched the patient's variants with sufficient "
                "evidence in the current bundle."
            )

        if excluded_drugs:
            summary_parts.append(
                f"{len(excluded_drugs)} drug(s) excluded due to "
                f"contraindications: "
                f"{', '.join(d.title() for d in excluded_drugs)}."
            )

        if not context.variants:
            summary_parts.append(
                "No variants recorded in clinical context — "
                "drug matching relies solely on evidence-level data."
            )

        summary = " ".join(summary_parts)

        # ── 5. Confidence ─────────────────────────────────────────────────
        if recommended_drugs and any(
            (ev.get("evidence_level") or "") in ("A", "B", "Level_1")
            for ev_list in drug_evidence.values()
            for ev in ev_list
        ):
            confidence = "high"
        elif recommended_drugs:
            confidence = "medium"
        else:
            confidence = "low"

        # ── 6. Build opinion ───────────────────────────────────────────────
        opinion = AgentOpinion(
            agent_type=self.agent_type,
            agent_version=self.agent_version,
            summary=summary,
            pros=pros,
            cons=cons,
            confidence=confidence,
            references=references,
            context_hash=context.context_hash or None,
            created_at=datetime.now(UTC).isoformat(),
        )

        # ── 7. Validate before returning ───────────────────────────────────
        errors = self.validate_opinion(opinion)
        if errors:
            msg = "; ".join(errors)
            raise ValueError(f"DrugAgent generated invalid opinion: {msg}")

        return opinion

    # ── Private helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _find_prior_response(
        drug_name: str,
        treatment_history: list[dict],
    ) -> str | None:
        """Check the best recorded response to *drug_name* in treatment history.

        Returns ``"progressive"``, ``"stable"``, ``"responsive"``, or
        ``None`` if the drug was not found.
        """
        for tx in treatment_history:
            regimen = (tx.get("regimen") or tx.get("treatment") or "").lower()
            if drug_name not in regimen:
                continue
            response = (tx.get("response") or tx.get("best_response") or "").lower()
            if response in ("progressive disease", "progression", "pd"):
                return "progressive"
            if response in ("stable disease", "sd"):
                return "stable"
            if response in (
                "complete response",
                "partial response",
                "cr",
                "pr",
                "responsive",
            ):
                return "responsive"
        return None


__all__ = [
    "DrugAgent",
]
