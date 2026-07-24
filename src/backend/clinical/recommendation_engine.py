"""
Recommendation Engine — rule-based engine for evidence aggregation, drug ranking,
and clinical recommendation generation.

Provides the core pipeline that:
1. Collects evidence via ``EvidenceCollector``
2. Aggregates and weights evidence via ``EvidenceAggregator`` (backed by
   ``WeightRegistry`` from ``evidence_weight``)
3. Ranks drugs via ``DrugRanker``
4. Applies configurable rules (``RecommendationRule``) to produce a structured
   recommendation result.

All scoring logic is rule-based and data-driven — no hardcoded thresholds or
placeholder values are used.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from src.backend.clinical.evidence_models import (
    EvidenceBundle,
    EvidenceItem,
)
from src.backend.clinical.evidence_weight import WeightRegistry
from src.backend.clinical.calculation_trace import (
    TraceManager,
    TraceStep,
)
from src.backend.clinical.explainable_recommendation import (
    ExplainableEngine,
    ExplanationFormatter,
    RecommendationReason,
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# RecommendationRule
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class RecommendationRule:
    """A single rule in the recommendation rule engine.

    Each rule encapsulates a condition (a callable that receives the full
    engine context and returns ``True`` when the rule should fire) and an
    action (a callable that receives the context and may mutate it or return
    a value).

    Rules are evaluated in descending ``priority`` order.  When multiple
    rules have the same priority, they are evaluated in registration order.

    Attributes
    ----------
    rule_id : str
        Unique identifier for this rule (e.g. ``"contraindication_01"``).
    name : str
        Human-readable short name.
    description : str
        Longer description explaining the rule's intent.
    condition : Callable[[dict], bool] | None
        A callable that takes the engine context (a dict) and returns
        ``True`` if the rule's action should fire.  If ``None`` the rule
        always fires.
    action : Callable[[dict], Any] | None
        A callable that takes the engine context and performs the rule's
        side-effect or returns a value.  If ``None`` the rule acts as a
        no-op marker.
    priority : int
        Higher-priority rules fire first (default ``0``).
    source : str
        Origin / owner of the rule (e.g. ``"internal"``, ``"nccn_guidelines"``).
    """

    rule_id: str
    name: str
    description: str = ""
    condition: Callable[[dict], bool] | None = None
    action: Callable[[dict], Any] | None = None
    priority: int = 0
    source: str = "internal"

    def evaluate(self, context: dict) -> Optional[Any]:
        """Evaluate the rule against the given context.

        If the rule has no condition, or the condition returns ``True``,
        the action is invoked (if present) and its result is returned.
        Otherwise ``None`` is returned.

        Parameters
        ----------
        context : dict
            The full engine context dictionary at evaluation time.

        Returns
        -------
        Any or None
            The result of the action callable, or ``None`` if the rule did
            not fire.
        """
        if self.condition is not None:
            try:
                should_fire = self.condition(context)
            except Exception:
                logger.exception(
                    "Rule %s (%s) condition raised an exception — skipping.",
                    self.rule_id,
                    self.name,
                )
                return None
            if not should_fire:
                return None

        if self.action is not None:
            try:
                return self.action(context)
            except Exception:
                logger.exception(
                    "Rule %s (%s) action raised an exception — skipping.",
                    self.rule_id,
                    self.name,
                )
                return None

        return None


# ═══════════════════════════════════════════════════════════════════════════════
# EvidenceAggregator
# ═══════════════════════════════════════════════════════════════════════════════


class EvidenceAggregator:
    """Aggregate evidence from an ``EvidenceBundle`` using source-tier weights.

    The aggregator consults ``WeightRegistry`` to resolve each evidence item's
    numeric weight (by source + native tier), then groups and sums results by
    drug name.

    This class is fully rule-driven — the weight mappings live in
    ``EvidenceWeightConfig`` instances registered with ``WeightRegistry``,
    not in hardcoded tables.
    """

    def __init__(self, weight_registry: type[WeightRegistry] = WeightRegistry) -> None:
        """Initialise the aggregator.

        Parameters
        ----------
        weight_registry : type[WeightRegistry], optional
            The weight registry class to consult for weight lookups.
            Defaults to ``WeightRegistry``.
        """
        self._registry = weight_registry

    # ── Public API ─────────────────────────────────────────────────────────

    def aggregate(
        self,
        evidence_bundle: EvidenceBundle,
        context: dict | None = None,
    ) -> dict[str, dict]:
        """Aggregate evidence items by drug, applying source-tier weights.

        For each evidence item that has a ``drug_name``, the method:
        1. Looks up the numeric weight via ``WeightRegistry.get_weight(source, native_level)``
        2. Records the evidence score, source name, tier, and direction
        3. Groups by drug name and computes:
           - ``evidence_scores``: list of per-item weighted scores
           - ``total_weight``: sum of all weighted scores for the drug
           - ``source_count``: number of distinct sources contributing evidence
           - ``item_count``: total number of evidence items
           - ``highest_weight``: maximum individual weight among items

        Parameters
        ----------
        evidence_bundle : EvidenceBundle
            The bundle of evidence items to aggregate.
        context : dict, optional
            Optional engine context (reserved for future rule-driven
            aggregation overrides).

        Returns
        -------
        dict[str, dict]
            Mapping of ``drug_name → aggregated result``.  Each value
            contains:

            .. code-block:: python

                {
                    "evidence_scores": [{"weight": float, "source": str, "tier": str, "direction": str}, ...],
                    "total_weight": float,
                    "source_count": int,
                    "item_count": int,
                    "highest_weight": float,
                    "sources": set[str],
                    "directions": set[str],
                }
        """
        _ = context  # reserved for future rule-driven overrides
        grouped: dict[str, list[EvidenceItem]] = {}
        for item in evidence_bundle.items:
            drug = item.drug_name
            if not drug:
                continue
            grouped.setdefault(drug, []).append(item)

        result: dict[str, dict] = {}
        for drug, items in grouped.items():
            scores: list[dict[str, Any]] = []
            total_weight = 0.0
            sources: set[str] = set()
            directions: set[str] = set()
            highest_weight = 0.0

            for item in items:
                # Resolve weight via registry
                try:
                    weight = self._registry.get_weight(
                        source=item.source,
                        native_tier=item.evidence_level or "not_assessed",
                    )
                except KeyError:
                    # Source not registered — fall back to a safe default
                    logger.debug(
                        "Source %r not registered in WeightRegistry; "
                        "using weight 0.0 for item %s.",
                        item.source,
                        item.source_record_id,
                    )
                    weight = 0.0

                score_entry: dict[str, Any] = {
                    "weight": weight,
                    "source": item.source,
                    "tier": item.evidence_level or "not_assessed",
                    "direction": item.evidence_direction or "unknown",
                    "clinical_significance": item.clinical_significance or "",
                    "conflict_status": item.conflict_status or "",
                }
                scores.append(score_entry)

                total_weight += weight
                sources.add(item.source)
                if item.evidence_direction:
                    directions.add(item.evidence_direction)
                if weight > highest_weight:
                    highest_weight = weight

            result[drug] = {
                "evidence_scores": scores,
                "total_weight": round(total_weight, 6),
                "source_count": len(sources),
                "item_count": len(items),
                "highest_weight": round(highest_weight, 6),
                "sources": sources,
                "directions": directions,
            }

        return result


# ═══════════════════════════════════════════════════════════════════════════════
# DrugRanker (P3A-03 compatible)
# ═══════════════════════════════════════════════════════════════════════════════


class DrugRanker:
    """Rank drugs by aggregated evidence weight.

    Sorting criteria (configurable via ``sort_keys``):
    - Primary: ``total_weight`` (descending)
    - Secondary: ``source_count`` (descending)
    - Tertiary: ``highest_weight`` (descending)

    This ranker produces a flat list of dictionaries that serve as input to
    the ``DrugRankingEngine`` in ``drug_ranking``.
    """

    def __init__(
        self,
        sort_keys: list[str] | None = None,
    ) -> None:
        """Initialise the ranker.

        Parameters
        ----------
        sort_keys : list[str], optional
            Ordered list of aggregate keys to sort by (prepend ``-`` for
            descending).  Defaults to ``["-total_weight", "-source_count",
            "-highest_weight"]``.
        """
        self._sort_keys = sort_keys or [
            "-total_weight",
            "-source_count",
            "-highest_weight",
        ]

    # ── Public API ─────────────────────────────────────────────────────────

    def rank(
        self,
        aggregated: dict[str, dict],
    ) -> list[dict]:
        """Rank drugs based on aggregated evidence data.

        Parameters
        ----------
        aggregated : dict[str, dict]
            Output from ``EvidenceAggregator.aggregate()``.  Mapping of
            ``drug_name → {total_weight, source_count, ...}``.

        Returns
        -------
        list[dict]
            Drugs sorted by the configured keys.  Each entry contains:

            .. code-block:: python

                {
                    "drug_name": str,
                    "total_weight": float,
                    "source_count": int,
                    "item_count": int,
                    "highest_weight": float,
                    "rank": int,           # 1-based position
                    "sources": list[str],
                }
        """
        entries: list[dict] = []
        for drug_name, agg in aggregated.items():
            entries.append({
                "drug_name": drug_name,
                "total_weight": agg["total_weight"],
                "source_count": agg["source_count"],
                "item_count": agg["item_count"],
                "highest_weight": agg["highest_weight"],
                "sources": sorted(agg["sources"]),
            })

        # Sort by configured keys
        def _sort_key(entry: dict) -> tuple:
            values: list = []
            for key in self._sort_keys:
                desc = key.startswith("-")
                actual_key = key.lstrip("-")
                val = entry.get(actual_key, 0)
                # Negate for descending sort
                if desc:
                    if isinstance(val, (int, float)):
                        val = -val
                    else:
                        val = self._negate_collection(val)
                values.append(val if val is not None else 0)
            return tuple(values)

        entries.sort(key=_sort_key)

        # Assign 1-based rank
        for idx, entry in enumerate(entries, 1):
            entry["rank"] = idx

        return entries

    @staticmethod
    def _negate_collection(val: Any) -> Any:
        """Return a negated version of a collection or value.

        For strings, returns the string as-is (strings are not negatable).
        """
        if isinstance(val, (int, float)):
            return -val
        return val


# ═══════════════════════════════════════════════════════════════════════════════
# RecommendationEngine
# ═══════════════════════════════════════════════════════════════════════════════


class RecommendationEngine:
    """Main recommendation engine that orchestrates the full pipeline.

    Pipeline steps
    --------------
    1. **Collect** — use ``EvidenceCollector`` to gather evidence for the
       given variants and patient context.
    2. **Aggregate** — use ``EvidenceAggregator`` to weight-summarise
       evidence by drug.
    3. **Rank** — use ``DrugRanker`` to sort drugs by evidence strength.
    4. **Apply rules** — evaluate all registered ``RecommendationRule``
       instances against the pipeline context.
    5. **Return** — a structured dictionary with the ranked drugs,
       aggregated data, and rule results.

    The engine is fully composable: every component (collector, aggregator,
    ranker, rules) can be swapped or extended.
    """

    def __init__(
        self,
        collector: Any,
        aggregator: EvidenceAggregator | None = None,
        ranker: DrugRanker | None = None,
        rules: list[RecommendationRule] | None = None,
        trace_manager: TraceManager | None = None,
    ) -> None:
        """Initialise the recommendation engine.

        Parameters
        ----------
        collector : EvidenceCollector
            An instance of ``EvidenceCollector`` (or a duck-typed compatible
            object with an async ``collect(context)`` method returning
            ``EvidenceBundle``).
        aggregator : EvidenceAggregator, optional
            Defaults to a fresh ``EvidenceAggregator``.
        ranker : DrugRanker, optional
            Defaults to a fresh ``DrugRanker``.
        rules : list[RecommendationRule], optional
            Optional list of rules to evaluate in step 4.  Rules are sorted
            by descending priority before evaluation.
        trace_manager : TraceManager, optional
            An optional ``TraceManager`` instance for recording calculation
            traces.  When provided, every pipeline step is traced.
        """
        self._collector = collector
        self._aggregator = aggregator or EvidenceAggregator()
        self._ranker = ranker or DrugRanker()
        self._rules = sorted(
            rules or [],
            key=lambda r: r.priority,
            reverse=True,
        )
        self._trace_manager = trace_manager

    # ── Public API ─────────────────────────────────────────────────────────

    async def run(
        self,
        patient_context: Any,
        variants: list[dict] | None = None,
    ) -> dict:
        """Execute the full recommendation pipeline.

        Parameters
        ----------
        patient_context : ClinicalContext
            A frozen ``ClinicalContext`` snapshot describing the patient,
            case, and variants.
        variants : list[dict], optional
            Optional explicit variant list.  When provided this list is
            passed through the pipeline; otherwise variants are read from
            ``patient_context.variants``.

        Returns
        -------
        dict
            Structured result containing:

            .. code-block:: python

                {
                    "drugs_ranked": [...],       # output of DrugRanker.rank()
                    "aggregated": {...},          # output of EvidenceAggregator.aggregate()
                    "evidence_count": int,
                    "rules_evaluated": int,
                    "rules_fired": int,
                    "rule_results": [...],
                    "pipeline_status": str,
                    "trace_id": str | None,      # present when trace_manager is configured
                }
        """
        resolved_variants = variants or getattr(patient_context, "variants", [])
        patient_id = getattr(patient_context, "patient_id", "unknown")

        # ── Initialise trace ──────────────────────────────────────────────
        trace_id: str | None = None
        if self._trace_manager is not None:
            try:
                trace = self._trace_manager.start_trace(
                    patient_id=patient_id,
                )
                trace_id = trace.trace_id
            except Exception:
                logger.exception("Failed to start calculation trace — continuing without tracing.")

        context = {
            "patient_context": patient_context,
            "variants": resolved_variants,
            "evidence_bundle": None,
            "aggregated": None,
            "ranked": None,
            "rule_results": [],
        }

        # ── Step 1: Collect ───────────────────────────────────────────────
        try:
            _record_trace_step(
                self._trace_manager,
                trace_id,
                "collect_evidence",
                "input",
                input_data={
                    "patient_id": patient_id,
                    "variants_count": len(resolved_variants),
                },
            )

            evidence_bundle: EvidenceBundle = await self._collector.collect(
                patient_context,
            )
            context["evidence_bundle"] = evidence_bundle

            _record_trace_step(
                self._trace_manager,
                trace_id,
                "collect_evidence",
                "input",
                output_data={
                    "evidence_count": len(evidence_bundle.items),
                    "sources": list(
                        getattr(evidence_bundle, "by_source", {}).keys()
                    ) if hasattr(evidence_bundle, "by_source") else [],
                },
            )
        except Exception:
            logger.exception("Evidence collection failed — aborting pipeline.")
            _fail_trace(self._trace_manager, trace_id)
            return self._empty_result(
                error="evidence_collection_failed",
            )

        # ── Step 2: Aggregate ─────────────────────────────────────────────
        try:
            _record_trace_step(
                self._trace_manager,
                trace_id,
                "aggregate_evidence",
                "evidence",
                input_data={
                    "evidence_count": len(evidence_bundle.items),
                },
            )

            aggregated = self._aggregator.aggregate(
                evidence_bundle=evidence_bundle,
                context=context,
            )
            context["aggregated"] = aggregated

            _record_trace_step(
                self._trace_manager,
                trace_id,
                "aggregate_evidence",
                "evidence",
                output_data={
                    "drug_count": len(aggregated),
                    "drugs": list(aggregated.keys()),
                    "total_weight_by_drug": {
                        drug: data["total_weight"]
                        for drug, data in aggregated.items()
                    },
                },
            )
        except Exception:
            logger.exception("Evidence aggregation failed — aborting pipeline.")
            _fail_trace(self._trace_manager, trace_id)
            return self._empty_result(
                error="evidence_aggregation_failed",
            )

        # ── Step 3: Rank ──────────────────────────────────────────────────
        try:
            _record_trace_step(
                self._trace_manager,
                trace_id,
                "rank_drugs",
                "score",
                input_data={
                    "drug_count": len(aggregated),
                    "drugs": list(aggregated.keys()),
                },
            )

            ranked = self._ranker.rank(aggregated)
            context["ranked"] = ranked

            _record_trace_step(
                self._trace_manager,
                trace_id,
                "rank_drugs",
                "score",
                output_data={
                    "ranking": [
                        {
                            "drug_name": r["drug_name"],
                            "rank": r["rank"],
                            "total_weight": r["total_weight"],
                        }
                        for r in ranked
                    ],
                },
            )
        except Exception:
            logger.exception("Drug ranking failed — aborting pipeline.")
            _fail_trace(self._trace_manager, trace_id)
            return self._empty_result(
                error="drug_ranking_failed",
            )

        # ── Step 4: Apply rules ───────────────────────────────────────────
        rules_evaluated = 0
        rules_fired = 0
        rule_results: list[dict] = []

        rule_input = {
            "rules_count": len(self._rules),
            "rule_ids": [r.rule_id for r in self._rules],
        }
        _record_trace_step(
            self._trace_manager,
            trace_id,
            "apply_rules",
            "recommendation",
            input_data=rule_input,
        )

        for rule in self._rules:
            rules_evaluated += 1
            result = rule.evaluate(context)
            rule_results.append({
                "rule_id": rule.rule_id,
                "name": rule.name,
                "fired": result is not None,
                "result": result,
            })
            if result is not None:
                rules_fired += 1

        context["rule_results"] = rule_results

        _record_trace_step(
            self._trace_manager,
            trace_id,
            "apply_rules",
            "recommendation",
            output_data={
                "rules_evaluated": rules_evaluated,
                "rules_fired": rules_fired,
                "fired_rule_ids": [
                    rr["rule_id"] for rr in rule_results if rr["fired"]
                ],
            },
        )

        # ── Step 5: Assemble result ───────────────────────────────────────
        result = {
            "drugs_ranked": ranked,
            "aggregated": {
                drug: {
                    "total_weight": data["total_weight"],
                    "source_count": data["source_count"],
                    "item_count": data["item_count"],
                    "highest_weight": data["highest_weight"],
                    "sources": sorted(data["sources"]),
                }
                for drug, data in aggregated.items()
            },
            "evidence_count": len(evidence_bundle.items),
            "rules_evaluated": rules_evaluated,
            "rules_fired": rules_fired,
            "rule_results": rule_results,
            "pipeline_status": "completed",
        }

        _record_trace_step(
            self._trace_manager,
            trace_id,
            "assemble_output",
            "output",
            input_data={
                "drugs_ranked_count": len(ranked),
                "evidence_count": len(evidence_bundle.items),
            },
            output_data={
                "pipeline_status": "completed",
            },
        )

        # ── Complete trace ────────────────────────────────────────────────
        if self._trace_manager is not None and trace_id is not None:
            try:
                self._trace_manager.complete_trace(trace_id, status="completed")
                result["trace_id"] = trace_id
            except Exception:
                logger.exception("Failed to complete calculation trace.")

        return result

    # ── Internal helpers ─────────────────────────────────────────────────

    @staticmethod
    def _empty_result(error: str = "unknown") -> dict:
        """Return a safe empty result when the pipeline fails."""
        result = {
            "drugs_ranked": [],
            "aggregated": {},
            "evidence_count": 0,
            "rules_evaluated": 0,
            "rules_fired": 0,
            "rule_results": [],
            "pipeline_status": f"error: {error}",
        }
        return result


# ═══════════════════════════════════════════════════════════════════════════════
# Module-level helpers (used by RecommendationEngine.run)
# ═══════════════════════════════════════════════════════════════════════════════


def _record_trace_step(
    trace_manager: TraceManager | None,
    trace_id: str | None,
    step_name: str,
    step_type: str,
    *,
    input_data: dict | None = None,
    output_data: dict | None = None,
) -> None:
    """Record a single trace step if a trace manager and trace ID are available.

    This is a no-op when either *trace_manager* or *trace_id* is ``None``,
    making it safe to call unconditionally.

    Parameters
    ----------
    trace_manager : TraceManager | None
        The trace manager instance (may be ``None``).
    trace_id : str | None
        The active trace ID (may be ``None``).
    step_name : str
        Short name for the step.
    step_type : str
        Category of step (``"input"``, ``"evidence"``, ``"score"``,
        ``"recommendation"``, ``"output"``).
    input_data : dict | None
        Optional snapshot of data entering the step.
    output_data : dict | None
        Optional snapshot of data produced by the step.
    """
    if trace_manager is None or trace_id is None:
        return
    try:
        step = TraceStep(
            step_name=step_name,
            step_type=step_type,
            input_data=input_data or {},
            output_data=output_data or {},
        )
        trace_manager.add_step(trace_id, step)
    except Exception:
        logger.debug(
            "Failed to record trace step %r for trace %s.",
            step_name,
            trace_id,
            exc_info=True,
        )


def _fail_trace(
    trace_manager: TraceManager | None,
    trace_id: str | None,
) -> None:
    """Mark a trace as failed if a trace manager and trace ID are available.

    Parameters
    ----------
    trace_manager : TraceManager | None
        The trace manager instance (may be ``None``).
    trace_id : str | None
        The active trace ID (may be ``None``).
    """
    if trace_manager is None or trace_id is None:
        return
    try:
        trace_manager.complete_trace(trace_id, status="failed")
    except Exception:
        logger.debug(
            "Failed to mark trace %s as failed.",
            trace_id,
            exc_info=True,
        )


__all__ = [
    "DrugRanker",
    "EvidenceAggregator",
    "RecommendationEngine",
    "RecommendationRule",
]
