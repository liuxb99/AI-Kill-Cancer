"""
ConsensusEngine — aggregates agent opinions, computes agreement level,
identifies conflicts, and produces a structured ConsensusResult.

The engine operates entirely with rule-based heuristics — no LLM calls
are made.  It analyses the pros/cons and confidence levels of each
:class:`AgentOpinion`, detects cross-agent conflicts via token-level
Jaccard similarity, and builds a consensus result that includes a
recommended option, alternatives, and unresolved questions.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from src.backend.clinical.models import ClinicalContext

from .models import AgentOpinion


# ─── Public models ─────────────────────────────────────────────────────────────


class ConsensusResult(BaseModel):
    """Aggregated consensus result from multiple agent opinions.

    Encapsulates the agreement level, detected conflicts, recommended
    and alternative options, and unresolved questions.

    Parameters
    ----------
    agreement : str
        Level of agreement among agents — ``"high"``, ``"moderate"``,
        ``"low"``, or ``"none"``.
    conflicts : list[dict]
        Detected conflicts between agent opinions.  Each entry is a dict
        with keys ``agent_types`` (list[str]), ``topic`` (str), and
        ``description`` (str).
    confidence : str
        Overall confidence of the consensus — ``"high"``, ``"medium"``,
        or ``"low"``.
    recommended_option : dict
        Recommended clinical option.  Contains keys ``treatment`` (str),
        ``rationale`` (str), and ``supporting_agents`` (list[str]).
    alternative_options : list[dict]
        Alternative options considered.  Each entry is a dict with keys
        ``treatment`` (str), ``rationale`` (str), and
        ``supporting_agents`` (list[str]).
    unresolved_questions : list[str]
        Questions that remain unanswered after the consensus process.
    context_hash : str | None
        SHA256 hash of the :class:`ClinicalContext` snapshot that the
        opinions were based on, for full traceability.
    created_at : str
        ISO-8601 timestamp of when this consensus result was created.
    """

    agreement: str
    conflicts: list[dict] = Field(default_factory=list)
    confidence: str
    recommended_option: dict
    alternative_options: list[dict] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    context_hash: str | None = None
    created_at: str = ""


# ─── Internal helpers ──────────────────────────────────────────────────────────

_STOP_WORDS: frozenset[str] = frozenset({
    "a", "about", "above", "after", "again", "against", "all", "also",
    "an", "and", "are", "as", "at", "be", "been", "being", "below",
    "between", "both", "but", "by", "can", "could", "did", "do",
    "does", "down", "during", "each", "few", "for", "from", "further",
    "had", "has", "have", "he", "her", "here", "herself", "him",
    "himself", "his", "how", "i", "if", "in", "into", "is", "it",
    "its", "itself", "just", "may", "me", "might", "more", "most",
    "my", "myself", "no", "nor", "not", "now", "of", "off", "on",
    "once", "only", "or", "other", "our", "ours", "ourselves", "out",
    "over", "own", "same", "she", "should", "so", "some", "such",
    "than", "that", "the", "their", "theirs", "them", "themselves",
    "then", "there", "these", "they", "this", "those", "through",
    "to", "too", "under", "until", "up", "very", "was", "we",
    "were", "what", "when", "where", "which", "while", "who",
    "whom", "why", "will", "with", "would", "you", "your", "yours",
    "yourself", "yourselves",
})


def _extract_tokens(text: str) -> set[str]:
    """Extract meaningful lowercase tokens from a text string.

    Strips punctuation, splits on whitespace, and removes stop words
    as well as tokens shorter than 3 characters.

    Parameters
    ----------
    text : str
        The input text.

    Returns
    -------
    set[str]
        A set of cleaned, meaningful tokens.
    """
    tokens: set[str] = set()
    for word in text.split():
        cleaned = word.strip(
            ".,;:!?\"'()[]{}<>/-_=+|\\@#$%^&*~`"
        ).lower()
        if cleaned and cleaned not in _STOP_WORDS and len(cleaned) > 2:
            tokens.add(cleaned)
    return tokens


def _token_similarity(a: str, b: str) -> float:
    """Compute Jaccard similarity between two text strings.

    Parameters
    ----------
    a : str
        First text.
    b : str
        Second text.

    Returns
    -------
    float
        A similarity score between 0.0 and 1.0 inclusive.
    """
    ta = _extract_tokens(a)
    tb = _extract_tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _compute_agreement_level(
    opinions: list[AgentOpinion],
    conflict_count: int,
) -> str:
    """Determine the agreement level based on confidence distribution
    and opinion polarity.

    Parameters
    ----------
    opinions : list[AgentOpinion]
        The agent opinions to evaluate.
    conflict_count : int
        Number of detected cross-agent conflicts.

    Returns
    -------
    str
        One of ``"high"``, ``"moderate"``, ``"low"``, ``"none"``.
    """
    if not opinions:
        return "none"

    # Polarity score per opinion: positive = more pros than cons
    polarities: list[int] = []
    conf_high = 0
    conf_low = 0

    for op in opinions:
        score = len(op.pros) - len(op.cons)
        polarities.append(score)
        if op.confidence == "high":
            conf_high += 1
        elif op.confidence == "low":
            conf_low += 1

    n = len(opinions)
    positive_count = sum(1 for p in polarities if p > 0)
    negative_count = sum(1 for p in polarities if p < 0)

    # All opinions share the same sign (or are neutral)
    same_sign = positive_count == 0 or negative_count == 0

    if not same_sign and conflict_count > 0:
        return "none"

    if conf_high == n and same_sign and conflict_count == 0:
        return "high"

    if conf_low > n // 2:
        return "low"

    if same_sign and conflict_count <= n // 2:
        return "moderate"

    return "low"


def _compute_overall_confidence(
    opinions: list[AgentOpinion],
) -> str:
    """Aggregate individual agent confidences into an overall level.

    Parameters
    ----------
    opinions : list[AgentOpinion]
        The agent opinions to evaluate.

    Returns
    -------
    str
        One of ``"high"``, ``"medium"``, ``"low"``.
    """
    if not opinions:
        return "low"

    high = sum(1 for op in opinions if op.confidence == "high")
    low = sum(1 for op in opinions if op.confidence == "low")
    n = len(opinions)

    if high == n:
        return "high"
    if low == n:
        return "low"
    return "medium"


def _detect_conflicts(
    opinions: list[AgentOpinion],
    threshold: float = 0.3,
) -> list[dict]:
    """Identify conflicting opinions by comparing pros and cons across
    agents using token-level Jaccard similarity.

    Parameters
    ----------
    opinions : list[AgentOpinion]
        The agent opinions to analyse.
    threshold : float
        Jaccard similarity threshold above which two texts are
        considered to refer to the same topic (default 0.3).

    Returns
    -------
    list[dict]
        Each dict contains ``agent_types``, ``topic``, and
        ``description`` keys.
    """
    conflicts: list[dict] = []

    for i, op_i in enumerate(opinions):
        for j in range(i + 1, len(opinions)):
            op_j = opinions[j]

            # Compare i's pros with j's cons
            for pro in op_i.pros:
                for con in op_j.cons:
                    sim = _token_similarity(pro, con)
                    if sim >= threshold:
                        _record_conflict(
                            conflicts,
                            op_i.agent_type,
                            op_j.agent_type,
                            pro,
                            con,
                        )

            # Compare j's pros with i's cons
            for pro in op_j.pros:
                for con in op_i.cons:
                    sim = _token_similarity(pro, con)
                    if sim >= threshold:
                        _record_conflict(
                            conflicts,
                            op_j.agent_type,
                            op_i.agent_type,
                            pro,
                            con,
                        )

    return conflicts


def _record_conflict(
    conflicts: list[dict],
    supporter: str,
    opposer: str,
    pro_text: str,
    con_text: str,
) -> None:
    """Add a single conflict entry to the list.

    Parameters
    ----------
    conflicts : list[dict]
        The conflict list being built.
    supporter : str
        Agent type that supports the topic.
    opposer : str
        Agent type that opposes the topic.
    pro_text : str
        The supporting argument text.
    con_text : str
        The opposing argument text.
    """
    topic = (
        pro_text[:80] + ("…" if len(pro_text) > 80 else "")
    )
    description = (
        f"{supporter} supports: {pro_text[:120]}"
        f" — {opposer} opposes: {con_text[:120]}"
    )
    conflicts.append({
        "agent_types": [supporter, opposer],
        "topic": topic,
        "description": description,
    })


def _build_recommended_option(
    opinions: list[AgentOpinion],
) -> dict:
    """Build the recommended option from the best-supported opinion.

    The opinion with the highest net support (pros minus cons, weighted
    by confidence) is chosen as the recommended option.  Other opinions
    whose summary shares meaningful token overlap with the chosen one
    are listed as supporting agents.

    Parameters
    ----------
    opinions : list[AgentOpinion]
        The agent opinions to evaluate.

    Returns
    -------
    dict
        A dict with keys ``treatment``, ``rationale``, and
        ``supporting_agents``.
    """
    if not opinions:
        return {
            "treatment": "No consensus reached",
            "rationale": "No agent opinions were provided for analysis.",
            "supporting_agents": [],
        }

    def _score(op: AgentOpinion) -> int:
        """Score an opinion: higher is more favourable."""
        base = len(op.pros) - len(op.cons)
        confidence_bonus = (
            3 if op.confidence == "high"
            else 2 if op.confidence == "medium"
            else 1
        )
        return base + confidence_bonus

    best = max(opinions, key=_score)

    # Collect supporting agents (those whose summary aligns with the best)
    supporting_agents: list[str] = [best.agent_type]
    for op in opinions:
        if op.agent_type == best.agent_type:
            continue
        if _token_similarity(best.summary, op.summary) > 0.3:
            supporting_agents.append(op.agent_type)

    rationale: str
    if best.pros:
        rationale = (
            "Based on supporting arguments: "
            + "; ".join(best.pros[:3])
        )[:500]
    else:
        rationale = best.summary[:500]

    return {
        "treatment": best.summary[:200],
        "rationale": rationale,
        "supporting_agents": supporting_agents,
    }


def _build_alternative_options(
    opinions: list[AgentOpinion],
    recommended: dict,
) -> list[dict]:
    """Build alternative options from opinions that differ from the
    recommended one.

    Parameters
    ----------
    opinions : list[AgentOpinion]
        The agent opinions to evaluate.
    recommended : dict
        The recommended option dict (used to exclude its supporting
        agents).

    Returns
    -------
    list[dict]
        Each entry is a dict with keys ``treatment``, ``rationale``,
        and ``supporting_agents``.
    """
    alternatives: list[dict] = []
    recommended_agents = set(recommended.get("supporting_agents", []))

    for op in opinions:
        if op.agent_type in recommended_agents:
            continue
        if not op.pros and not op.cons:
            continue

        args_parts: list[str] = []
        args_parts.extend(op.pros[:2])
        args_parts.extend(op.cons[:2])
        rationale = (
            "Arguments considered: " + "; ".join(args_parts)
        )[:500] if args_parts else op.summary[:500]

        alternatives.append({
            "treatment": op.summary[:200],
            "rationale": rationale,
            "supporting_agents": [op.agent_type],
        })

    return alternatives


def _extract_unresolved_questions(
    opinions: list[AgentOpinion],
    conflicts: list[dict],
) -> list[str]:
    """Extract unresolved questions from low-confidence opinions and
    detected conflicts.

    Parameters
    ----------
    opinions : list[AgentOpinion]
        The agent opinions to evaluate.
    conflicts : list[dict]
        Detected conflicts (as produced by :func:`_detect_conflicts`).

    Returns
    -------
    list[str]
        Unresolved questions.
    """
    questions: list[str] = []

    for op in opinions:
        if op.confidence == "low":
            questions.append(
                f"{op.agent_type} has low confidence: {op.summary[:150]}"
            )

    for conflict in conflicts:
        topic = conflict.get("topic", "Unknown")
        types = conflict.get("agent_types", [])
        if topic:
            questions.append(
                f"Conflict between {' and '.join(types)} "
                f"regarding: {topic}"
            )

    return questions


# ─── Public API ────────────────────────────────────────────────────────────────


class ConsensusEngine:
    """Rule-based consensus engine for aggregating agent opinions.

    Analyses a collection of :class:`AgentOpinion` instances produced
    by the multi-agent system, computes agreement levels, identifies
    conflicts, and produces a structured :class:`ConsensusResult`.

    The engine operates entirely with rule-based heuristics — no LLM
    calls are made.
    """

    def __init__(self) -> None:
        pass

    async def reach_consensus(
        self,
        opinions: list[AgentOpinion],
        context: ClinicalContext,
    ) -> ConsensusResult:
        """Analyse agent opinions and reach a consensus result.

        The algorithm performs the following steps:

        1. Compute individual opinion polarity (pros vs cons count).
        2. Detect cross-agent conflicts via token-level Jaccard
           similarity between pros and cons.
        3. Determine the overall agreement level based on confidence
           distribution and polarity alignment.
        4. Build the recommended option and alternative options.
        5. Extract unresolved questions from low-confidence opinions
           and detected conflicts.
        6. Return a fully populated :class:`ConsensusResult`.

        Parameters
        ----------
        opinions : list[AgentOpinion]
            The structured opinions produced by one or more clinical
            decision-support agents.
        context : ClinicalContext
            The clinical context snapshot that the opinions are based
            on.  Its ``context_hash`` is propagated into the result for
            traceability.

        Returns
        -------
        ConsensusResult
            The aggregated consensus result.
        """
        if not opinions:
            return ConsensusResult(
                agreement="none",
                conflicts=[],
                confidence="low",
                recommended_option={
                    "treatment": "No consensus reached",
                    "rationale": "No agent opinions were provided.",
                    "supporting_agents": [],
                },
                alternative_options=[],
                unresolved_questions=[],
                context_hash=context.context_hash or None,
                created_at=datetime.now(timezone.utc).isoformat(),
            )

        # 1. Detect cross-agent conflicts
        conflicts = _detect_conflicts(opinions)

        # 2. Compute agreement level
        agreement = _compute_agreement_level(opinions, len(conflicts))

        # 3. Compute overall confidence
        confidence = _compute_overall_confidence(opinions)

        # 4. Build recommended option
        recommended = _build_recommended_option(opinions)

        # 5. Build alternative options
        alternatives = _build_alternative_options(opinions, recommended)

        # 6. Extract unresolved questions
        questions = _extract_unresolved_questions(opinions, conflicts)

        return ConsensusResult(
            agreement=agreement,
            conflicts=conflicts,
            confidence=confidence,
            recommended_option=recommended,
            alternative_options=alternatives,
            unresolved_questions=questions,
            context_hash=context.context_hash or None,
            created_at=datetime.now(timezone.utc).isoformat(),
        )


__all__ = [
    "ConsensusEngine",
    "ConsensusResult",
]
