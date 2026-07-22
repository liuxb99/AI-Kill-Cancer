"""ResistanceAgent — resistance / drug-resistance analysis agent.

Analyses the risk of drug resistance based on known resistance mutations,
acquired resistance from prior treatments, and cross-referenced evidence.
"""

from __future__ import annotations

from datetime import datetime, timezone

from src.backend.agents.base import BaseAgent
from src.backend.agents.models import AgentOpinion
from src.backend.clinical.evidence_models import EvidenceBundle
from src.backend.clinical.models import ClinicalContext

_RESISTANCE_SIGNIFICANCES = {"resistance", "resistant"}


class ResistanceAgent(BaseAgent):
    """Agent that analyses drug-resistance risk for a clinical context.

    Evaluates three dimensions of resistance:

    1. **Variant-level resistance** — known resistance mutations identified
       from the patient's variant list (e.g. EGFR T790M, KRAS G12C).
    2. **Acquired resistance** — prior treatments in the patient's history
       that may have selected for resistant clones.
    3. **Evidence-based resistance** — external evidence items that report
       resistance associations for the patient's variants or drugs.

    The agent returns a structured :class:`AgentOpinion` with a resistance
    risk summary, supporting/opposing arguments, and traceable references.
    """

    agent_type: str = "resistance"
    agent_version: str = "1.0.0"

    async def analyze(
        self,
        context: ClinicalContext,
        evidence: EvidenceBundle,
    ) -> AgentOpinion:
        """Analyse drug-resistance risk for the given clinical context.

        Parameters
        ----------
        context : ClinicalContext
            Frozen patient / case snapshot containing *variants* and
            *treatment_history* to evaluate.
        evidence : EvidenceBundle
            Aggregated evidence items from knowledge sources; items with
            ``clinical_significance`` of ``"resistance"`` are considered.

        Returns
        -------
        AgentOpinion
            Structured opinion with a plain-text summary of resistance
            risk, supporting (pros) and opposing (cons) arguments, and
            a confidence rating.
        """
        # ── 1. Variant-level resistance ────────────────────────────────────
        resistance_variants: list[dict] = []
        for var in context.variants:
            sig = (var.get("clinical_significance") or "").lower()
            if sig in _RESISTANCE_SIGNIFICANCES:
                resistance_variants.append(var)

        # ── 2. Acquired resistance from treatment history ──────────────────
        prior_treatments: list[str] = []
        for tx in context.treatment_history:
            regimen = tx.get("regimen") or tx.get("treatment") or ""
            if regimen:
                prior_treatments.append(regimen)

        # ── 3. Evidence-based resistance cross-reference ───────────────────
        resistance_evidence: list[dict] = []
        for item in evidence.items:
            sig = (item.clinical_significance or "").lower()
            if sig in _RESISTANCE_SIGNIFICANCES:
                resistance_evidence.append(item.model_dump())

        # ── 4. Build reasoning ─────────────────────────────────────────────
        pros: list[str] = []
        cons: list[str] = []
        references: list[dict] = []

        if resistance_variants:
            genes = sorted(
                {v.get("gene_symbol", "?") for v in resistance_variants}
            )
            pros.append(
                f"Detected known resistance mutations: {', '.join(genes)}."
            )
            for var in resistance_variants:
                protein = var.get("protein_change") or var.get("hgvs", "")
                gene = var.get("gene_symbol", "?")
                ref: dict = {
                    "source": "variant_list",
                    "citation": (
                        f"Variant {gene} {protein} flagged as resistance "
                        f"in clinical context"
                    ),
                }
                references.append(ref)

        if prior_treatments:
            pros.append(
                f"Patient has prior treatment history "
                f"({len(prior_treatments)} regimen(s)), which may indicate "
                f"acquired resistance."
            )

        if resistance_evidence:
            sources = sorted(
                {e["source"] for e in resistance_evidence}
            )
            pros.append(
                f"Found {len(resistance_evidence)} evidence item(s) "
                f"reporting resistance from sources: "
                f"{', '.join(sorted(sources))}."
            )
            for ev in resistance_evidence:
                ref = {
                    "source": ev["source"],
                    "citation": ev.get("citation") or ev.get("description", ""),
                }
                if ev.get("url"):
                    ref["url"] = ev["url"]
                references.append(ref)

        # Cons — only include if there is meaningful risk to note
        if not resistance_variants and not resistance_evidence:
            cons.append(
                "No known resistance mutations or resistance-reporting "
                "evidence identified."
            )

        # ── 5. Determine confidence ────────────────────────────────────────
        if resistance_variants or resistance_evidence:
            confidence = "high"
        elif prior_treatments:
            confidence = "medium"
        else:
            confidence = "low"

        # ── 6. Build summary ────────────────────────────────────────────────
        summary_parts: list[str] = []
        if resistance_variants:
            genes_str = ", ".join(
                sorted(
                    f"{v.get('gene_symbol', '?')}"
                    f"({v.get('protein_change', v.get('hgvs', ''))})"
                    for v in resistance_variants
                )
            )
            summary_parts.append(
                f"Resistance mutations detected in {genes_str}."
            )
        if prior_treatments:
            summary_parts.append(
                f"Prior treatment exposes patient to acquired resistance "
                f"risk ({len(prior_treatments)} prior regimen(s))."
            )
        if resistance_evidence:
            summary_parts.append(
                f"{len(resistance_evidence)} evidence source(s) corroborate "
                f"resistance concern."
            )
        if not summary_parts:
            summary_parts.append(
                "No resistance signals detected from variants, treatment "
                "history, or evidence."
            )

        summary = " ".join(summary_parts)

        opinion = AgentOpinion(
            agent_type=self.agent_type,
            agent_version=self.agent_version,
            summary=summary,
            pros=pros,
            cons=cons,
            confidence=confidence,
            references=references,
            context_hash=context.context_hash or None,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # ── 7. Validate before returning ───────────────────────────────────
        errors = self.validate_opinion(opinion)
        if errors:
            msg = "; ".join(errors)
            raise ValueError(f"ResistanceAgent generated invalid opinion: {msg}")

        return opinion


__all__ = [
    "ResistanceAgent",
]
