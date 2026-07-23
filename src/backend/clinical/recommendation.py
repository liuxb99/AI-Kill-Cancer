"""
RecommendationGenerator — rule-based treatment recommendation generator.

Transforms a :class:`ConsensusResult` together with the original
:class:`ClinicalContext` and :class:`EvidenceBundle` into a structured
:class:`TreatmentRecommendation` that includes both a machine-readable
``structured_json`` field and a clinician-friendly Markdown report.

All logic is rule-based — no LLM calls are made.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from src.backend.agents.consensus import ConsensusResult
from src.backend.clinical.evidence_models import EvidenceBundle
from src.backend.clinical.models import ClinicalContext

# ─── TreatmentRecommendation Model ──────────────────────────────────────────


class TreatmentRecommendation(BaseModel):
    """Structured treatment recommendation generated from a consensus result.

    Encapsulates the final output of the clinical decision-support pipeline:
    recommended first-line and second-line therapies, clinical trial options,
    supporting evidence, benefit/risk analysis, monitoring plan, and both
    a structured JSON representation and a human-readable Markdown report.

    Parameters
    ----------
    first_line : dict
        First-line treatment recommendation. Contains keys ``treatment``
        (str), ``rationale`` (str), ``drugs`` (list[dict]), and
        ``supporting_agents`` (list[str]).
    second_line : dict
        Second-line / alternative treatment recommendation. Same structure
        as *first_line*.
    clinical_trial : dict
        Clinical trial options. Contains keys ``trials`` (list[dict]),
        ``recommendation`` (str), and ``reasoning`` (str).
    supporting_evidence : list[dict]
        Evidence items supporting the recommendation. Each entry contains
        ``source``, ``evidence_level``, ``description``, and optional
        ``citation`` / ``url``.
    expected_benefit : dict
        Expected clinical benefit analysis. Contains keys ``summary``
        (str), ``benefits`` (list[str]), ``magnitude`` (str), and
        ``confidence`` (str).
    potential_risk : dict
        Potential risks and adverse effects analysis. Contains keys
        ``summary`` (str), ``risks`` (list[dict]), ``severity`` (str),
        and ``confidence`` (str).
    monitoring_plan : dict
        Proposed monitoring plan. Contains keys ``summary`` (str),
        ``actions`` (list[dict]), ``frequency`` (str), and
        ``duration`` (str).
    structured_json : dict
        Complete structured data representation of the recommendation,
        suitable for downstream API consumption or storage.
    markdown : str
        Human-readable Markdown report designed for clinician review.
    context_hash : str | None
        SHA256 hash of the :class:`ClinicalContext` snapshot used to
        generate this recommendation, for full traceability.
    created_at : str
        ISO-8601 timestamp of when this recommendation was created.
    """

    first_line: dict
    second_line: dict
    clinical_trial: dict
    supporting_evidence: list[dict] = Field(default_factory=list)
    expected_benefit: dict
    potential_risk: dict
    monitoring_plan: dict
    structured_json: dict
    markdown: str
    context_hash: str | None = None
    created_at: str = ""


# ─── Internal helpers ───────────────────────────────────────────────────────


def _build_first_line(consensus: ConsensusResult) -> dict:
    """Build a structured first-line recommendation from the consensus.

    Parameters
    ----------
    consensus : ConsensusResult
        The aggregated consensus result.

    Returns
    -------
    dict
        First-line treatment dict with ``treatment``, ``rationale``,
        ``drugs``, and ``supporting_agents`` keys.
    """
    recommended = consensus.recommended_option
    treatment_text = recommended.get("treatment", "No recommendation")
    rationale = recommended.get("rationale", "")
    supporting = recommended.get("supporting_agents", [])

    # Attempt to parse drug names from the treatment summary
    drugs: list[dict] = [
        {"name": treatment_text, "dose": None, "frequency": None}
    ]

    return {
        "treatment": treatment_text,
        "rationale": rationale,
        "drugs": drugs,
        "supporting_agents": supporting,
        "evidence_level": _derive_evidence_level(consensus),
    }


def _build_second_line(consensus: ConsensusResult) -> dict:
    """Build a second-line / alternative recommendation.

    Parameters
    ----------
    consensus : ConsensusResult
        The aggregated consensus result.

    Returns
    -------
    dict
        Second-line treatment dict. Returns a "No alternative options"
        placeholder when none are available.
    """
    alternatives = consensus.alternative_options
    if not alternatives:
        return {
            "treatment": "No alternative options identified",
            "rationale": (
                "All agents converged on the first-line recommendation "
                "without proposing distinct alternatives."
            ),
            "drugs": [],
            "supporting_agents": [],
            "evidence_level": consensus.confidence,
        }

    # Pick the highest-ranked alternative (first entry)
    best_alt = alternatives[0]
    drugs: list[dict] = [
        {"name": best_alt.get("treatment", ""), "dose": None, "frequency": None}
    ]

    return {
        "treatment": best_alt.get("treatment", ""),
        "rationale": best_alt.get("rationale", ""),
        "drugs": drugs,
        "supporting_agents": best_alt.get("supporting_agents", []),
        "evidence_level": consensus.confidence,
    }


def _build_clinical_trial(
    consensus: ConsensusResult,
    evidence: EvidenceBundle,
) -> dict:
    """Build clinical trial options from evidence and consensus.

    Parameters
    ----------
    consensus : ConsensusResult
        The aggregated consensus result.
    evidence : EvidenceBundle
        The evidence bundle, used to extract trial-related items.

    Returns
    -------
    dict
        Clinical trial options dict with ``trials``, ``recommendation``,
        and ``reasoning`` keys.
    """
    # Extract items that mention "trial" in their source or description
    trial_items: list[dict] = []
    for item in evidence.items:
        source_lower = item.source.lower()
        desc_lower = (item.description or "").lower()
        if "trial" in source_lower or "trial" in desc_lower:
            trial_items.append({
                "source": item.source,
                "nct_id": item.source_record_id,
                "disease": item.disease,
                "drug": item.drug_name,
                "evidence_level": item.evidence_level,
                "description": item.description,
                "url": item.url,
            })

    # If no trial-specific evidence is found, note this
    if not trial_items:
        trial_items = [
            {
                "source": "N/A",
                "nct_id": None,
                "disease": None,
                "drug": None,
                "evidence_level": None,
                "description": (
                    "No clinical trial evidence was identified in the "
                    "available evidence bundle."
                ),
                "url": None,
            }
        ]

    recommendation = (
        "Consider enrolling the patient in one of the listed clinical "
        "trials after verifying eligibility criteria."
    )

    reasoning_parts: list[str] = []
    if consensus.unresolved_questions:
        reasoning_parts.append(
            "Clinical trials may address unresolved questions: "
            + "; ".join(consensus.unresolved_questions[:3])
        )
    if not reasoning_parts:
        reasoning_parts.append(
            "Trial options are based on evidence available in the "
            "knowledge base."
        )

    return {
        "trials": trial_items,
        "recommendation": recommendation,
        "reasoning": " ".join(reasoning_parts),
    }


def _build_supporting_evidence(
    consensus: ConsensusResult,
    evidence: EvidenceBundle,
) -> list[dict]:
    """Extract and rank supporting evidence from the evidence bundle.

    Parameters
    ----------
    consensus : ConsensusResult
        The aggregated consensus result.
    evidence : EvidenceBundle
        The evidence bundle.

    Returns
    -------
    list[dict]
        Sorted list of evidence items (highest level first), each
        containing ``source``, ``evidence_level``, ``description``,
        ``citation``, and ``url``.
    """
    # Identify the recommended drug name from consensus
    recommended_treatment = (
        consensus.recommended_option.get("treatment", "") or ""
    ).lower()

    # Score and collect relevant evidence
    scored: list[tuple[int, dict]] = []
    for item in evidence.items:
        score = 0
        # Boost items matching the recommended treatment
        if item.drug_name and item.drug_name.lower() in recommended_treatment:
            score += 10
        if item.gene_symbol:
            score += 5
        if item.evidence_level:
            rank = _evidence_level_rank(item.evidence_level)
            score += max(0, 20 - rank)  # higher rank → lower score

        scored.append((
            score,
            {
                "source": item.source,
                "evidence_level": item.evidence_level,
                "description": item.description or "No description available",
                "citation": item.citation,
                "url": item.url,
            },
        ))

    # Sort descending by score, take top items
    scored.sort(key=lambda x: x[0], reverse=True)
    return [entry for _, entry in scored[:10]]


def _build_benefit(consensus: ConsensusResult) -> dict:
    """Build an expected-benefit analysis from the consensus.

    Parameters
    ----------
    consensus : ConsensusResult
        The aggregated consensus result.

    Returns
    -------
    dict
        Benefit analysis with ``summary``, ``benefits``, ``magnitude``,
        and ``confidence`` keys.
    """
    recommended = consensus.recommended_option
    benefits: list[str] = []

    for agent in recommended.get("supporting_agents", []):
        benefits.append(f"Endorsed by {agent}")

    # Add generic expected benefits if none extracted
    if not benefits:
        benefits.append(
            "Targeted therapy aligned with molecular profiling results."
        )

    # Determine magnitude from agreement level
    magnitude_map: dict[str, str] = {
        "high": "significant improvement expected",
        "moderate": "moderate improvement expected",
        "low": "limited improvement expected",
        "none": "uncertain benefit",
    }
    magnitude = magnitude_map.get(consensus.agreement, "uncertain benefit")

    return {
        "summary": (
            "The recommended treatment is expected to provide "
            f"{magnitude} based on the current evidence."
        ),
        "benefits": benefits,
        "magnitude": magnitude,
        "confidence": consensus.confidence,
    }


def _build_risk(consensus: ConsensusResult) -> dict:
    """Build a potential-risk analysis from the consensus.

    Parameters
    ----------
    consensus : ConsensusResult
        The aggregated consensus result.

    Returns
    -------
    dict
        Risk analysis with ``summary``, ``risks``, ``severity``, and
        ``confidence`` keys.
    """
    risks: list[dict] = []

    # Convert conflicts into risk items
    for conflict in consensus.conflicts:
        risks.append({
            "topic": conflict.get("topic", "Unknown"),
            "description": conflict.get("description", ""),
            "severity": "moderate",
        })

    # If no conflicts, add a generic risk note
    if not risks:
        risks.append({
            "topic": "General treatment-related toxicity",
            "description": (
                "Standard adverse effects associated with the "
                "recommended therapy should be considered."
            ),
            "severity": "variable",
        })

    severity_map: dict[str, str] = {
        "high": "low",
        "moderate": "moderate",
        "low": "moderate",
        "none": "high",
    }
    severity = severity_map.get(consensus.agreement, "moderate")

    return {
        "summary": (
            f"Potential risks are assessed as {severity} severity "
            "based on the current evidence and agent consensus."
        ),
        "risks": risks,
        "severity": severity,
        "confidence": consensus.confidence,
    }


def _build_monitoring_plan() -> dict:
    """Build a standard monitoring plan for the recommended therapy.

    Returns
    -------
    dict
        Monitoring plan with ``summary``, ``actions``, ``frequency``,
        and ``duration`` keys.
    """
    actions: list[dict] = [
        {
            "action": "Complete blood count (CBC) with differential",
            "frequency": "Every 2 weeks during initial treatment",
            "rationale": "Monitor for haematologic toxicity",
        },
        {
            "action": "Comprehensive metabolic panel (CMP)",
            "frequency": "Every 2 weeks during initial treatment",
            "rationale": "Monitor hepatic and renal function",
        },
        {
            "action": "ECG",
            "frequency": "Baseline and as clinically indicated",
            "rationale": "Monitor for cardiac effects",
        },
        {
            "action": "Imaging (CT or PET-CT)",
            "frequency": "Every 8-12 weeks",
            "rationale": "Assess treatment response per RECIST criteria",
        },
        {
            "action": "Performance status assessment (ECOG)",
            "frequency": "At each cycle",
            "rationale": "Evaluate functional status and tolerability",
        },
        {
            "action": "Symptom and adverse event review",
            "frequency": "At each visit",
            "rationale": "Early detection of treatment-related toxicities",
        },
    ]

    return {
        "summary": (
            "Regular monitoring is essential to evaluate treatment "
            "response, manage adverse effects, and adjust therapy as "
            "needed. The schedule below should be tailored to the "
            "specific agents used and the patient's clinical status."
        ),
        "actions": actions,
        "frequency": "Every 2-4 weeks during active treatment",
        "duration": "Throughout treatment course and follow-up",
    }


def _build_structured_json(
    first_line: dict,
    second_line: dict,
    clinical_trial: dict,
    supporting_evidence: list[dict],
    expected_benefit: dict,
    potential_risk: dict,
    monitoring_plan: dict,
    consensus: ConsensusResult,
    context: ClinicalContext,
) -> dict:
    """Assemble the complete structured JSON representation.

    Parameters
    ----------
    first_line : dict
        First-line treatment.
    second_line : dict
        Second-line treatment.
    clinical_trial : dict
        Clinical trial options.
    supporting_evidence : list[dict]
        Supporting evidence items.
    expected_benefit : dict
        Benefit analysis.
    potential_risk : dict
        Risk analysis.
    monitoring_plan : dict
        Monitoring plan.
    consensus : ConsensusResult
        The source consensus result.
    context : ClinicalContext
        The clinical context.

    Returns
    -------
    dict
        Complete structured JSON payload.
    """
    return {
        "patient": {
            "case_id": context.case_id,
            "patient_id": context.patient_id,
            "diagnosis": context.diagnosis,
            "cancer_type": context.cancer_type,
            "stage": context.stage,
        },
        "consensus": {
            "agreement": consensus.agreement,
            "confidence": consensus.confidence,
            "conflicts_count": len(consensus.conflicts),
            "unresolved_questions": consensus.unresolved_questions,
        },
        "recommendation": {
            "first_line": first_line,
            "second_line": second_line,
            "clinical_trial": clinical_trial,
        },
        "evidence_summary": {
            "total_items": len(supporting_evidence),
            "top_level": (
                max(
                    (e["evidence_level"] for e in supporting_evidence
                     if e.get("evidence_level")),
                    default="not_assessed",
                )
            ),
        },
        "benefit_risk": {
            "expected_benefit": expected_benefit,
            "potential_risk": potential_risk,
        },
        "monitoring_plan": monitoring_plan,
    }


def _build_markdown(
    first_line: dict,
    second_line: dict,
    clinical_trial: dict,
    supporting_evidence: list[dict],
    expected_benefit: dict,
    potential_risk: dict,
    monitoring_plan: dict,
    consensus: ConsensusResult,
    context: ClinicalContext,
) -> str:
    """Generate a clinician-friendly Markdown report.

    Parameters
    ----------
    first_line : dict
        First-line treatment.
    second_line : dict
        Second-line treatment.
    clinical_trial : dict
        Clinical trial options.
    supporting_evidence : list[dict]
        Supporting evidence items.
    expected_benefit : dict
        Benefit analysis.
    potential_risk : dict
        Risk analysis.
    monitoring_plan : dict
        Monitoring plan.
    consensus : ConsensusResult
        The source consensus result.
    context : ClinicalContext
        The clinical context.

    Returns
    -------
    str
        A formatted Markdown report string.
    """
    lines: list[str] = [
        "# Treatment Recommendation Report",
        "",
        f"**Case ID:** {context.case_id}  ",
        f"**Patient ID:** {context.patient_id}  ",
        f"**Diagnosis:** {context.diagnosis}  ",
        f"**Cancer Type:** {context.cancer_type}  ",
        f"**Stage:** {context.stage}  ",
        f"**Generated:** {datetime.now(UTC).isoformat()}  ",
        "",
        "---",
        "",
        "## Consensus Summary",
        "",
        f"- **Agreement Level:** {consensus.agreement}",
        f"- **Confidence:** {consensus.confidence}",
        f"- **Conflicts Detected:** {len(consensus.conflicts)}",
        f"- **Unresolved Questions:** "
        f"{len(consensus.unresolved_questions)}",
        "",
    ]

    # Conflicts
    if consensus.conflicts:
        lines.append("### Detected Conflicts")
        lines.append("")
        for conflict in consensus.conflicts:
            topic = conflict.get("topic", "Unknown")
            desc = conflict.get("description", "")
            lines.append(f"- **{topic}**: {desc}")
        lines.append("")

    # Unresolved questions
    if consensus.unresolved_questions:
        lines.append("### Unresolved Questions")
        lines.append("")
        for q in consensus.unresolved_questions:
            lines.append(f"- {q}")
        lines.append("")

    lines.extend([
        "---",
        "",
        "## Treatment Recommendation",
        "",
        "### First-Line Therapy",
        "",
        f"**Treatment:** {first_line.get('treatment', 'N/A')}",
        "",
        f"**Rationale:** {first_line.get('rationale', 'N/A')}",
        "",
    ])

    drugs = first_line.get("drugs", [])
    if drugs:
        lines.append("**Drugs:**")
        for drug in drugs:
            name = drug.get("name", "Unknown")
            lines.append(f"- {name}")
        lines.append("")

    supporting = first_line.get("supporting_agents", [])
    if supporting:
        lines.append(
            "**Supporting Agents:** " + ", ".join(supporting)
        )
        lines.append("")

    lines.extend([
        "### Second-Line / Alternative Therapy",
        "",
        f"**Treatment:** {second_line.get('treatment', 'N/A')}",
        "",
        f"**Rationale:** {second_line.get('rationale', 'N/A')}",
        "",
    ])

    alt_drugs = second_line.get("drugs", [])
    if alt_drugs:
        lines.append("**Drugs:**")
        for drug in alt_drugs:
            name = drug.get("name", "Unknown")
            lines.append(f"- {name}")
        lines.append("")

    lines.extend([
        "### Clinical Trial Options",
        "",
        f"**Recommendation:** "
        f"{clinical_trial.get('recommendation', 'N/A')}",
        "",
        f"**Reasoning:** "
        f"{clinical_trial.get('reasoning', 'N/A')}",
        "",
    ])

    trials = clinical_trial.get("trials", [])
    if trials:
        lines.append("**Available Trials:**")
        lines.append("")
        for trial in trials:
            source = trial.get("source", "N/A")
            nct = trial.get("nct_id") or "N/A"
            desc = trial.get("description") or "No description"
            lines.append(f"- **Source:** {source}  ")
            lines.append(f"  **NCT ID:** {nct}  ")
            lines.append(f"  **Description:** {desc}")
            if trial.get("url"):
                lines.append(f"  **URL:** {trial['url']}")
            lines.append("")

    lines.extend([
        "---",
        "",
        "## Supporting Evidence",
        "",
    ])

    if supporting_evidence:
        for i, ev in enumerate(supporting_evidence, 1):
            level = ev.get("evidence_level") or "not_assessed"
            source = ev.get("source", "Unknown")
            desc = ev.get("description", "No description")
            lines.append(f"### Evidence Item #{i}")
            lines.append("")
            lines.append(f"**Source:** {source}  ")
            lines.append(f"**Level:** {level}  ")
            lines.append(f"**Description:** {desc}")
            if ev.get("citation"):
                lines.append(f"**Citation:** {ev['citation']}")
            if ev.get("url"):
                lines.append(f"**URL:** {ev['url']}")
            lines.append("")
    else:
        lines.append(
            "No supporting evidence items were available in the "
            "evidence bundle."
        )
        lines.append("")

    lines.extend([
        "---",
        "",
        "## Benefit-Risk Assessment",
        "",
        "### Expected Benefit",
        "",
        f"{expected_benefit.get('summary', 'N/A')}",
        "",
    ])

    benefits = expected_benefit.get("benefits", [])
    if benefits:
        lines.append("**Specific Benefits:**")
        for b in benefits:
            lines.append(f"- {b}")
        lines.append("")
    lines.append(
        f"**Magnitude:** "
        f"{expected_benefit.get('magnitude', 'N/A')}  "
    )
    lines.append(
        f"**Confidence:** "
        f"{expected_benefit.get('confidence', 'N/A')}"
    )
    lines.append("")

    lines.extend([
        "### Potential Risks",
        "",
        f"{potential_risk.get('summary', 'N/A')}",
        "",
    ])

    risks = potential_risk.get("risks", [])
    if risks:
        lines.append("**Specific Risks:**")
        for risk in risks:
            topic = risk.get("topic", "Unknown")
            desc = risk.get("description", "")
            severity = risk.get("severity", "unknown")
            lines.append(f"- **{topic}** (severity: {severity})")
            if desc:
                lines.append(f"  - {desc}")
        lines.append("")
    lines.append(
        f"**Overall Severity:** "
        f"{potential_risk.get('severity', 'N/A')}  "
    )
    lines.append(
        f"**Confidence:** "
        f"{potential_risk.get('confidence', 'N/A')}"
    )
    lines.append("")

    lines.extend([
        "---",
        "",
        "## Monitoring Plan",
        "",
        f"{monitoring_plan.get('summary', 'N/A')}",
        "",
        f"**Frequency:** "
        f"{monitoring_plan.get('frequency', 'N/A')}  ",
        f"**Duration:** "
        f"{monitoring_plan.get('duration', 'N/A')}",
        "",
        "### Recommended Actions",
        "",
    ])

    actions = monitoring_plan.get("actions", [])
    if actions:
        for action in actions:
            act = action.get("action", "")
            freq = action.get("frequency", "")
            rationale = action.get("rationale", "")
            lines.append(f"- **{act}**")
            lines.append(f"  - **Frequency:** {freq}")
            lines.append(f"  - **Rationale:** {rationale}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(
        "*This recommendation was generated by an AI-assisted clinical "
        "decision-support system. All outputs should be reviewed by a "
        "qualified clinician before clinical action.*"
    )

    return "\n".join(lines)


def _derive_evidence_level(consensus: ConsensusResult) -> str:
    """Derive an overall evidence-level label from the consensus state.

    Parameters
    ----------
    consensus : ConsensusResult
        The consensus result.

    Returns
    -------
    str
        An evidence-level string (A–E or Level_1–5).
    """
    mapping: dict[str, str] = {
        "high": "B",
        "moderate": "C",
        "low": "D",
        "none": "E",
    }
    return mapping.get(consensus.agreement, "not_assessed")


def _evidence_level_rank(level: str) -> int:
    """Return a numeric rank for an evidence level (lower is better).

    Parameters
    ----------
    level : str
        Evidence level string (e.g. ``"A"``, ``"Level_1"``).

    Returns
    -------
    int
        Numeric rank where 0 is best.
    """
    precedence: list[str] = [
        "A", "B", "C", "D", "E",
        "Level_1", "Level_2", "Level_3", "Level_4", "Level_5",
        "not_assessed",
    ]
    try:
        return precedence.index(level)
    except ValueError:
        return len(precedence)


# ─── Public API ─────────────────────────────────────────────────────────────


class RecommendationGenerator:
    """Rule-based generator for structured treatment recommendations.

    Transforms the output of the consensus engine (a :class:`ConsensusResult`)
    together with the original clinical context and evidence bundle into a
    comprehensive :class:`TreatmentRecommendation` that includes both a
    machine-readable structured JSON payload and a clinician-friendly
    Markdown report.

    All logic is rule-based — no LLM calls are made.  The generator
    extracts recommended and alternative treatments, gathers supporting
    evidence, performs benefit/risk analysis, and suggests a monitoring
    plan.
    """

    def __init__(self) -> None:
        pass

    async def generate(
        self,
        consensus: ConsensusResult,
        context: ClinicalContext,
        evidence: EvidenceBundle,
    ) -> TreatmentRecommendation:
        r"""Generate a structured treatment recommendation.

        The method performs the following steps:

        1. Extract the first-line recommendation from
           *consensus*.\ ``recommended_option``.
        2. Build second-line / alternative options from
           *consensus*.\ ``alternative_options``.
        3. Extract clinical trial options from *evidence*.
        4. Gather and rank supporting evidence items.
        5. Generate benefit analysis based on agent pros and agreement.
        6. Generate risk analysis based on conflicts and disagreement.
        7. Build a standard monitoring plan.
        8. Assemble the complete structured JSON payload.
        9. Generate a clinician-friendly Markdown report.
        10. Return a fully populated :class:`TreatmentRecommendation`.

        Parameters
        ----------
        consensus : ConsensusResult
            The aggregated consensus result produced by the
            :class:`ConsensusEngine`.
        context : ClinicalContext
            The original clinical context snapshot used for reasoning.
        evidence : EvidenceBundle
            The aggregated evidence bundle from the Evidence Collector.

        Returns
        -------
        TreatmentRecommendation
            A fully populated treatment recommendation with both
            structured JSON and Markdown representations.
        """
        # Step 1-2: Build treatment lines
        first_line = _build_first_line(consensus)
        second_line = _build_second_line(consensus)

        # Step 3: Clinical trial options
        clinical_trial = _build_clinical_trial(consensus, evidence)

        # Step 4: Supporting evidence
        supporting_evidence = _build_supporting_evidence(consensus, evidence)

        # Step 5-6: Benefit / risk analysis
        expected_benefit = _build_benefit(consensus)
        potential_risk = _build_risk(consensus)

        # Step 7: Monitoring plan
        monitoring_plan = _build_monitoring_plan()

        # Step 8: Structured JSON
        structured_json = _build_structured_json(
            first_line,
            second_line,
            clinical_trial,
            supporting_evidence,
            expected_benefit,
            potential_risk,
            monitoring_plan,
            consensus,
            context,
        )

        # Step 9: Markdown report
        markdown = _build_markdown(
            first_line,
            second_line,
            clinical_trial,
            supporting_evidence,
            expected_benefit,
            potential_risk,
            monitoring_plan,
            consensus,
            context,
        )

        # Step 10: Assemble result
        return TreatmentRecommendation(
            first_line=first_line,
            second_line=second_line,
            clinical_trial=clinical_trial,
            supporting_evidence=supporting_evidence,
            expected_benefit=expected_benefit,
            potential_risk=potential_risk,
            monitoring_plan=monitoring_plan,
            structured_json=structured_json,
            markdown=markdown,
            context_hash=consensus.context_hash or context.context_hash or None,
            created_at=datetime.now(UTC).isoformat(),
        )


__all__ = [
    "RecommendationGenerator",
    "TreatmentRecommendation",
]
