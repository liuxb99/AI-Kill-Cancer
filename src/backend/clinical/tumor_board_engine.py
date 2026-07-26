"""
Tumor Board Consensus Engine

Calculates multi-specialty consensus from specialist opinions
and produces a structured consensus result with traceability.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from src.backend.domain.enums import ConsensusStatus, Position
from src.backend.clinical.consensus_rules import DEFAULT_RULES, ConsensusRuleSet


# ═══════════════════════════════════════════════════════════════════════════════
# DTOs
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class SpecialistOpinionInput:
    """P0 data — a single specialist's opinion on a clinical option.

    Attributes
    ----------
    specialty : str
        The specialty identifier (e.g. ``"medical_oncology"``).
    participant_id : str, optional
        Optional identifier for the individual participant.
    position : str
        One of ``"support"``, ``"oppose"``, ``"abstain"``.
    confidence : float
        Raw confidence score in ``[0.0, 1.0]``.
    rationale : str, optional
        Free-text justification for the position.
    supporting_evidence : list[str], optional
        References supporting the position (e.g. literature PMIDs).
    contraindications : list[str], optional
        Contraindication signals considered.
    preferred_option : str, optional
        The option the specialist prefers.
    alternative_option : str, optional
        An alternative the specialist would accept.
    requires_more_information : bool
        Whether the specialist needs more data before deciding.
    """

    specialty: str
    participant_id: Optional[str] = None
    position: str = "abstain"
    confidence: float = 0.5
    rationale: Optional[str] = None
    supporting_evidence: Optional[List[str]] = None
    contraindications: Optional[List[str]] = None
    preferred_option: Optional[str] = None
    alternative_option: Optional[str] = None
    requires_more_information: bool = False


@dataclass
class TumorBoardConsensusInput:
    """Input payload for the consensus engine.

    Attributes
    ----------
    patient_id : str
        Identifier linking to the patient record.
    recommendation_id : str
        Identifier linking to the recommendation being reviewed.
    clinical_decision_id : str
        Identifier linking to the associated clinical decision.
    specialist_opinions : list[SpecialistOpinionInput]
        Collection of specialist opinions to evaluate.
    meeting_context : str, optional
        Free-text description of the tumor board meeting context.
    """

    patient_id: str
    recommendation_id: str
    clinical_decision_id: str
    specialist_opinions: List[SpecialistOpinionInput]
    meeting_context: Optional[str] = None


@dataclass
class WeightedOpinion:
    """Internal weighted representation of a specialist opinion.

    Attributes
    ----------
    specialty : str
        The specialty identifier.
    position : str
        One of ``"support"``, ``"oppose"``, ``"abstain"``.
    raw_confidence : float
        The original confidence score from the input.
    weight : float
        The computed effective weight after applying all modifiers.
    evidence_score : float
        Optional evidence contribution multiplier (default ``1.0``).
    """

    specialty: str
    position: str
    raw_confidence: float
    weight: float
    evidence_score: float = 1.0


@dataclass
class ConsensusResult:
    """Structured output of the Tumor Board Consensus Engine.

    Attributes
    ----------
    consensus_id : str
        Unique identifier for this consensus run.
    consensus_status : ConsensusStatus
        The final consensus classification.
    consensus_score : float
        Overall consensus score (same as ``consensus_ratio``).
    support_score : float
        Sum of weighted support opinions.
    oppose_score : float
        Sum of weighted oppose opinions.
    abstain_score : float
        Sum of weighted abstain opinions.
    consensus_ratio : float
        Proportion of weighted support over total weighted
        (support + oppose).  ``0.0`` when no weighted opinions exist.
    confidence_score : float
        Mean raw confidence across all valid opinions.
    final_recommendation : str, optional
        The agreed-upon recommendation, if any.
    supporting_rationale : str, optional
        Human-readable explanation of how the consensus was reached.
    dissenting_opinions : list[dict]
        Serialised list of dissenting (oppose) opinions.
    unresolved_questions : list[str]
        Questions raised by specialists that remain unresolved.
    required_follow_up : list[str]
        Actions required before a final decision can be made.
    participating_specialties : list[str]
        Distinct specialties that contributed opinions.
    trace_steps : list[dict]
        Ordered trace of every calculation step.
    """

    consensus_id: str
    consensus_status: ConsensusStatus
    consensus_score: float
    support_score: float
    oppose_score: float
    abstain_score: float
    consensus_ratio: float
    confidence_score: float
    final_recommendation: Optional[str] = None
    supporting_rationale: Optional[str] = None
    dissenting_opinions: List[Dict] = field(default_factory=list)
    unresolved_questions: List[str] = field(default_factory=list)
    required_follow_up: List[str] = field(default_factory=list)
    participating_specialties: List[str] = field(default_factory=list)
    trace_steps: List[Dict] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════════

TRACE_STEP_TYPES: List[str] = [
    "load_context",
    "validate_links",
    "normalize_opinions",
    "calculate_weights",
    "calculate_consensus",
    "resolve_dissent",
    "finalize_consensus",
    "prepare_persistence",
]


# ═══════════════════════════════════════════════════════════════════════════════
# ConsensusEngine
# ═══════════════════════════════════════════════════════════════════════════════


class ConsensusEngine:
    """Rule-based engine that calculates multi-specialty consensus.

    The engine consumes specialist opinions and applies consensus rules
    to produce a structured ``ConsensusResult`` with full traceability.

    Each step of the pipeline is recorded in the ``trace_steps`` list
    on the result, providing an audit trail for clinical review.

    Parameters
    ----------
    rules : ConsensusRuleSet
        The rule set to use for consensus calculation.  Defaults to
        ``DEFAULT_RULES``.
    """

    def __init__(self, rules: ConsensusRuleSet = DEFAULT_RULES) -> None:
        """Initialise the consensus engine.

        Parameters
        ----------
        rules : ConsensusRuleSet, optional
            Custom rule set instance.  Defaults to ``DEFAULT_RULES``.
        """
        self._rules = rules

    # ── Public API ─────────────────────────────────────────────────────────

    def calculate(self, input_data: TumorBoardConsensusInput) -> ConsensusResult:
        """Calculate consensus from specialist opinions.

        Parameters
        ----------
        input_data : TumorBoardConsensusInput
            The input payload containing patient context and specialist
            opinions.

        Returns
        -------
        ConsensusResult
            The structured consensus result with full traceability.

        Raises
        ------
        ValueError
            If required link fields (patient_id, recommendation_id,
            clinical_decision_id) are empty.
        """
        trace_steps: List[Dict] = []

        # Use a deterministic short ID for readability while keeping
        # sufficient uniqueness.
        consensus_id = f"TBC-{uuid.uuid4().hex[:12].upper()}"

        # ── Step 0: Load context ──────────────────────────────────────
        self._step_load_context(input_data, trace_steps)

        # ── Step 1: Validate links ────────────────────────────────────
        self._step_validate_links(input_data, trace_steps)

        # ── Step 2: Normalise opinions ────────────────────────────────
        weighted = self._step_normalize_opinions(input_data, trace_steps)

        # ── Step 3: Calculate weights ─────────────────────────────────
        weighted = self._step_calculate_weights(weighted, trace_steps)

        # ── Step 4: Calculate consensus ──────────────────────────────
        scores = self._step_calculate_consensus(weighted, trace_steps)

        # ── Step 5: Resolve dissent ─────────────────────────────────
        dissenting = self._step_resolve_dissent(weighted, trace_steps)

        # ── Step 6: Finalise consensus ──────────────────────────────
        status = self._step_finalize_consensus(
            weighted, scores["consensus_ratio"], input_data, trace_steps
        )

        # ── Step 7: Prepare persistence ─────────────────────────────
        result = self._step_prepare_persistence(
            consensus_id=consensus_id,
            consensus_status=status,
            support_score=scores["support_score"],
            oppose_score=scores["oppose_score"],
            abstain_score=scores["abstain_score"],
            consensus_ratio=scores["consensus_ratio"],
            confidence_score=scores["confidence_score"],
            dissenting_opinions=dissenting,
            weighted_opinions=weighted,
            input_data=input_data,
            trace_steps=trace_steps,
        )

        return result

    # ── Step implementations ────────────────────────────────────────────

    @staticmethod
    def _step_load_context(
        input_data: TumorBoardConsensusInput,
        trace_steps: List[Dict],
    ) -> None:
        """Record input context summary as the first trace step."""
        step: Dict = {
            "step_type": "load_context",
            "input_summary": {
                "patient_id": input_data.patient_id,
                "recommendation_id": input_data.recommendation_id,
                "clinical_decision_id": input_data.clinical_decision_id,
                "opinion_count": len(input_data.specialist_opinions),
                "has_meeting_context": input_data.meeting_context is not None,
            },
            "output_summary": {
                "status": "context_loaded",
            },
        }
        trace_steps.append(step)

    @staticmethod
    def _step_validate_links(
        input_data: TumorBoardConsensusInput,
        trace_steps: List[Dict],
    ) -> None:
        """Validate that required link fields are not empty.

        Raises
        ------
        ValueError
            If any of patient_id, recommendation_id, or
            clinical_decision_id is empty / falsy.
        """
        errors: List[str] = []
        if not input_data.patient_id:
            errors.append("patient_id is required")
        if not input_data.recommendation_id:
            errors.append("recommendation_id is required")
        if not input_data.clinical_decision_id:
            errors.append("clinical_decision_id is required")

        step: Dict = {
            "step_type": "validate_links",
            "input_summary": {
                "patient_id": input_data.patient_id,
                "recommendation_id": input_data.recommendation_id,
                "clinical_decision_id": input_data.clinical_decision_id,
            },
            "output_summary": {
                "valid": len(errors) == 0,
                "errors": errors,
            },
        }
        trace_steps.append(step)

        if errors:
            raise ValueError(
                f"Consensus link validation failed: {'; '.join(errors)}"
            )

    @staticmethod
    def _step_normalize_opinions(
        input_data: TumorBoardConsensusInput,
        trace_steps: List[Dict],
    ) -> List[WeightedOpinion]:
        """Convert raw ``SpecialistOpinionInput`` items to ``WeightedOpinion``.

        The ``weight`` field is left as ``0.0`` at this stage; it will be
        computed in ``_step_calculate_weights``.
        """
        weighted: List[WeightedOpinion] = []
        for opinion in input_data.specialist_opinions:
            weighted.append(
                WeightedOpinion(
                    specialty=opinion.specialty,
                    position=opinion.position,
                    raw_confidence=opinion.confidence,
                    weight=0.0,  # computed in the next step
                    evidence_score=1.0,
                )
            )

        step: Dict = {
            "step_type": "normalize_opinions",
            "input_summary": {
                "raw_opinion_count": len(input_data.specialist_opinions),
            },
            "output_summary": {
                "normalized_count": len(weighted),
                "specialties": sorted({w.specialty for w in weighted}),
            },
        }
        trace_steps.append(step)
        return weighted

    def _step_calculate_weights(
        self,
        opinions: List[WeightedOpinion],
        trace_steps: List[Dict],
    ) -> List[WeightedOpinion]:
        """Apply specialty weight and confidence weight to each opinion.

        Opinions whose ``raw_confidence`` falls below
        ``rules.min_confidence`` are dropped.  Abstentions receive the
        configured ``abstain_weight`` (typically ``0.0``).
        """
        updated: List[WeightedOpinion] = []
        skipped: List[Dict] = []

        for opinion in opinions:
            # Determine effective weight
            if opinion.position == "abstain":
                weight = self._rules.abstain_weight
            else:
                sw = self.get_specialty_weight(opinion.specialty)
                cw = self.get_confidence_weight(opinion.raw_confidence)
                weight = sw * cw

            # Filter out opinions with negligible confidence
            if opinion.raw_confidence < self._rules.min_confidence:
                skipped.append(
                    {
                        "specialty": opinion.specialty,
                        "position": opinion.position,
                        "raw_confidence": opinion.raw_confidence,
                        "reason": "below_min_confidence",
                    }
                )
                continue

            updated.append(
                WeightedOpinion(
                    specialty=opinion.specialty,
                    position=opinion.position,
                    raw_confidence=opinion.raw_confidence,
                    weight=weight,
                    evidence_score=opinion.evidence_score,
                )
            )

        step: Dict = {
            "step_type": "calculate_weights",
            "input_summary": {
                "opinion_count": len(opinions),
            },
            "output_summary": {
                "weighted_count": len(updated),
                "skipped_count": len(skipped),
                "skipped": skipped,
                "weights": {w.specialty: w.weight for w in updated},
            },
        }
        trace_steps.append(step)
        return updated

    @staticmethod
    def _step_calculate_consensus(
        opinions: List[WeightedOpinion],
        trace_steps: List[Dict],
    ) -> Dict[str, float]:
        """Calculate support, oppose, abstain scores and consensus ratio.

        Returns a dict with keys:
            support_score, oppose_score, abstain_score,
            consensus_ratio, confidence_score.
        """
        support_score = 0.0
        oppose_score = 0.0
        abstain_score = 0.0
        confidence_values: List[float] = []

        for o in opinions:
            if o.position == "support":
                support_score += o.weight
            elif o.position == "oppose":
                oppose_score += o.weight
            elif o.position == "abstain":
                abstain_score += o.weight
            confidence_values.append(o.raw_confidence)

        total_weighted = support_score + oppose_score
        consensus_ratio = (
            support_score / total_weighted if total_weighted > 0 else 0.0
        )
        confidence_score = (
            sum(confidence_values) / len(confidence_values)
            if confidence_values
            else 0.0
        )

        step: Dict = {
            "step_type": "calculate_consensus",
            "input_summary": {
                "opinion_count": len(opinions),
            },
            "output_summary": {
                "support_score": support_score,
                "oppose_score": oppose_score,
                "abstain_score": abstain_score,
                "total_weighted": total_weighted,
                "consensus_ratio": consensus_ratio,
                "confidence_score": confidence_score,
            },
        }
        trace_steps.append(step)

        return {
            "support_score": support_score,
            "oppose_score": oppose_score,
            "abstain_score": abstain_score,
            "consensus_ratio": consensus_ratio,
            "confidence_score": confidence_score,
        }

    def _step_resolve_dissent(
        self,
        opinions: List[WeightedOpinion],
        trace_steps: List[Dict],
    ) -> List[Dict]:
        """Extract dissenting (oppose) opinions as serialisable dicts."""
        dissenting = self.extract_dissenting_opinions(opinions)

        step: Dict = {
            "step_type": "resolve_dissent",
            "input_summary": {
                "total_opinions": len(opinions),
            },
            "output_summary": {
                "dissenting_count": len(dissenting),
                "dissenting_opinions": dissenting,
            },
        }
        trace_steps.append(step)
        return dissenting

    def _step_finalize_consensus(
        self,
        opinions: List[WeightedOpinion],
        consensus_ratio: float,
        input_data: TumorBoardConsensusInput,
        trace_steps: List[Dict],
    ) -> ConsensusStatus:
        """Determine the consensus status from ratio, rules, and context.

        Priority (first match wins):
        1. Any opinion with ``requires_more_information`` → DEFERRED
        2. Fewer valid opinions than ``rules.min_opinions`` → INSUFFICIENT_INFORMATION
        3. ``consensus_ratio == 1.0`` → UNANIMOUS
        4. ``consensus_ratio >= strong_consensus_threshold`` → STRONG_CONSENSUS
        5. ``consensus_ratio >= majority_consensus_threshold`` → MAJORITY_CONSENSUS
        6. ``consensus_ratio > split_decision_upper`` → SPLIT_DECISION
        7. Otherwise → SPLIT_DECISION
        """
        # 1. Check deferred
        has_deferred = any(
            o.requires_more_information
            for o in input_data.specialist_opinions
        )
        if has_deferred:
            status = ConsensusStatus.DEFERRED
        # 2. Check insufficient information
        elif len(opinions) < self._rules.min_opinions:
            status = ConsensusStatus.INSUFFICIENT_INFORMATION
        # 3. Unanimous
        elif consensus_ratio >= self._rules.unanimous_threshold:
            status = ConsensusStatus.UNANIMOUS
        # 4. Strong consensus
        elif consensus_ratio >= self._rules.strong_consensus_threshold:
            status = ConsensusStatus.STRONG_CONSENSUS
        # 5. Majority consensus
        elif consensus_ratio >= self._rules.majority_consensus_threshold:
            status = ConsensusStatus.MAJORITY_CONSENSUS
        # 6 / 7. Split decision
        else:
            status = ConsensusStatus.SPLIT_DECISION

        step: Dict = {
            "step_type": "finalize_consensus",
            "input_summary": {
                "effective_opinion_count": len(opinions),
                "consensus_ratio": consensus_ratio,
                "min_opinions": self._rules.min_opinions,
                "has_deferred_opinions": has_deferred,
            },
            "output_summary": {
                "consensus_status": status.value,
            },
        }
        trace_steps.append(step)
        return status

    @staticmethod
    def _step_prepare_persistence(
        consensus_id: str,
        consensus_status: ConsensusStatus,
        support_score: float,
        oppose_score: float,
        abstain_score: float,
        consensus_ratio: float,
        confidence_score: float,
        dissenting_opinions: List[Dict],
        weighted_opinions: List[WeightedOpinion],
        input_data: TumorBoardConsensusInput,
        trace_steps: List[Dict],
    ) -> ConsensusResult:
        """Assemble the final ``ConsensusResult`` with all derived fields."""
        participating_specialties = sorted(
            {o.specialty for o in weighted_opinions}
        )

        # Collect unresolved questions and required follow-up from input
        unresolved_questions: List[str] = []
        required_follow_up: List[str] = []
        for opinion in input_data.specialist_opinions:
            if opinion.requires_more_information:
                if opinion.rationale:
                    unresolved_questions.append(opinion.rationale)
            if opinion.position == "abstain" and opinion.rationale:
                required_follow_up.append(
                    f"Review {opinion.specialty} concerns: {opinion.rationale}"
                )

        supporting_rationale = ConsensusEngine._build_supporting_rationale(
            status=consensus_status,
            ratio=consensus_ratio,
            support_score=support_score,
            oppose_score=oppose_score,
        )

        result = ConsensusResult(
            consensus_id=consensus_id,
            consensus_status=consensus_status,
            consensus_score=consensus_ratio,
            support_score=support_score,
            oppose_score=oppose_score,
            abstain_score=abstain_score,
            consensus_ratio=consensus_ratio,
            confidence_score=confidence_score,
            final_recommendation=None,
            supporting_rationale=supporting_rationale,
            dissenting_opinions=dissenting_opinions,
            unresolved_questions=unresolved_questions,
            required_follow_up=required_follow_up,
            participating_specialties=participating_specialties,
            trace_steps=trace_steps,
        )

        # Append the final trace step (note: result already holds trace_steps,
        # but we add the step after constructing the result so the trace on
        # the returned object is complete).
        step: Dict = {
            "step_type": "prepare_persistence",
            "input_summary": {
                "consensus_id": consensus_id,
                "consensus_status": consensus_status.value,
            },
            "output_summary": {
                "consensus_id": result.consensus_id,
                "consensus_status": result.consensus_status.value,
                "consensus_score": result.consensus_score,
                "participating_specialties": result.participating_specialties,
            },
        }
        trace_steps.append(step)

        return result

    # ── Helper methods ────────────────────────────────────────────────────

    def get_specialty_weight(self, specialty: str) -> float:
        """Look up the weight for a given specialty.

        Parameters
        ----------
        specialty : str
            The specialty identifier (e.g. ``"medical_oncology"``).

        Returns
        -------
        float
            The specialty weight from the rules, or ``0.5`` if the
            specialty is not in the configured weights table.
        """
        return self._rules.specialty_weights.get(specialty, 0.5)

    def get_confidence_weight(self, confidence: float) -> float:
        """Map a raw confidence value to a confidence weight multiplier.

        The mapping follows these thresholds:

        - ``confidence >= 0.8`` → ``rules.confidence_high`` (default ``1.0``)
        - ``confidence >= 0.5`` → ``rules.confidence_medium`` (default ``0.7``)
        - ``confidence < 0.5``  → ``rules.confidence_low`` (default ``0.4``)

        Parameters
        ----------
        confidence : float
            Raw confidence score in ``[0.0, 1.0]``.

        Returns
        -------
        float
            The mapped confidence weight.
        """
        if confidence >= 0.8:
            return self._rules.confidence_high
        if confidence >= 0.5:
            return self._rules.confidence_medium
        return self._rules.confidence_low

    def extract_dissenting_opinions(
        self, opinions: List[WeightedOpinion]
    ) -> List[Dict]:
        """Extract dissenting (oppose) opinions as serialisable dicts.

        Parameters
        ----------
        opinions : list[WeightedOpinion]
            The (possibly filtered) weighted opinions to scan.

        Returns
        -------
        list[dict]
            Each dict contains ``specialty``, ``position``, ``weight``,
            and ``raw_confidence`` for every opinion whose position is
            ``"oppose"``.
        """
        dissenting: List[Dict] = []
        for opinion in opinions:
            if opinion.position == "oppose":
                dissenting.append(
                    {
                        "specialty": opinion.specialty,
                        "position": opinion.position,
                        "weight": opinion.weight,
                        "raw_confidence": opinion.raw_confidence,
                    }
                )
        return dissenting

    # ── Static helpers ───────────────────────────────────────────────────

    @staticmethod
    def _build_supporting_rationale(
        status: ConsensusStatus,
        ratio: float,
        support_score: float,
        oppose_score: float,
    ) -> str:
        """Generate a human-readable rationale for the consensus result."""
        if status == ConsensusStatus.UNANIMOUS:
            return (
                f"All participating specialties unanimously support the "
                f"recommendation (ratio={ratio:.2f})."
            )
        if status == ConsensusStatus.STRONG_CONSENSUS:
            return (
                f"Strong consensus reached with {ratio:.0%} of weighted "
                f"opinions in support "
                f"(support={support_score:.2f}, oppose={oppose_score:.2f})."
            )
        if status == ConsensusStatus.MAJORITY_CONSENSUS:
            return (
                f"Majority consensus: {ratio:.0%} of weighted opinions "
                f"support the recommendation "
                f"(support={support_score:.2f}, oppose={oppose_score:.2f})."
            )
        if status == ConsensusStatus.SPLIT_DECISION:
            return (
                f"Split decision: weighted opinions are divided "
                f"(support={support_score:.2f}, oppose={oppose_score:.2f}, "
                f"ratio={ratio:.2f}). Further discussion required."
            )
        if status == ConsensusStatus.INSUFFICIENT_INFORMATION:
            return (
                f"Insufficient specialist opinions to form a consensus "
                f"(minimum required: 2)."
            )
        if status == ConsensusStatus.DEFERRED:
            return (
                f"Decision deferred: one or more specialists require "
                f"additional information before voting."
            )
        return (
            f"Consensus status: {status.value} "
            f"(ratio={ratio:.2f}, support={support_score:.2f})."
        )


__all__ = [
    "ConsensusEngine",
    "ConsensusResult",
    "SpecialistOpinionInput",
    "TumorBoardConsensusInput",
    "WeightedOpinion",
    "TRACE_STEP_TYPES",
]
