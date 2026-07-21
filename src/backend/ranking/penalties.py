"""
Penalty functions for the Drug Ranking Engine.
"""

from __future__ import annotations



class ConflictPenalty:
    """Penalizes drugs with conflicting evidence."""

    def apply(self, evidence_items: list[dict], drug_name: str) -> float:
        """
        Compute penalty for conflicting evidence about a drug.
        For each conflicting item, apply a penalty proportional to evidence level.
        """
        penalty = 0.0
        conflict_count = 0

        for item in evidence_items:
            item_drug = (item.get("drug_name", "") or "").strip().lower()
            if item_drug and item_drug != drug_name.strip().lower():
                continue

            direction = (item.get("evidence_direction", "") or "").lower()
            conflict_status = (item.get("_conflict_status", item.get("conflict_status", "")) or "").lower()

            is_conflicting = (
                direction in ("conflicting", "does not support")
                or conflict_status == "conflicting"
            )

            if is_conflicting:
                level = item.get("evidence_level", "")
                level_weights = {"Level_1": 1.0, "Level_2": 0.9, "Level_3": 0.7,
                                 "Level_4": 0.5, "Level_5": 0.3, "A": 1.0, "B": 0.9,
                                 "C": 0.7, "D": 0.5, "E": 0.3}
                weight = level_weights.get(level, 0.3)
                penalty -= weight * 1.0
                conflict_count += 1

        # Additional penalty for multiple conflicts
        if conflict_count > 1:
            penalty -= 0.5 * (conflict_count - 1)

        return penalty


class UncertaintyPenalty:
    """Penalizes drugs with high uncertainty evidence."""

    def apply(self, evidence_items: list[dict], drug_name: str) -> float:
        """
        Compute penalty for uncertain evidence about a drug.
        """
        penalty = 0.0
        uncertain_count = 0

        for item in evidence_items:
            item_drug = (item.get("drug_name", "") or "").strip().lower()
            if item_drug and item_drug != drug_name.strip().lower():
                continue

            direction = (item.get("evidence_direction", "") or "").lower()
            conflict_status = (item.get("_conflict_status", item.get("conflict_status", "")) or "").lower()

            is_uncertain = (
                direction in ("neutral", "inconclusive", "")
                or conflict_status in ("uncertain", "not_evaluable")
            )

            if is_uncertain:
                penalty -= 0.3
                uncertain_count += 1

        if uncertain_count > 3:
            penalty -= 0.5

        return penalty
