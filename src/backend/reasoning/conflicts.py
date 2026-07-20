"""
ConflictAnalyzer — identifies evidence conflicts in reasoning context.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ConflictAnalyzer:
    """
    Analyzes evidence for conflicting results about the same drug-variant pair.
    """

    def analyze(self, evidence_items: list[dict]) -> list[dict]:
        """
        Analyze evidence for conflicts.

        Returns a list of conflict reports, each with:
        - drug_name: the drug involved
        - supporting: list of supporting evidence items
        - conflicting: list of conflicting evidence items
        - severity: high, medium, low
        """
        conflicts = []
        drug_groups: dict[str, dict] = {}

        for item in (evidence_items or []):
            drug_name = (item.get("drug_name", "") or "").strip()
            if not drug_name:
                continue

            if drug_name not in drug_groups:
                drug_groups[drug_name] = {"supporting": [], "conflicting": []}

            direction = (item.get("evidence_direction", "") or "").lower()
            conflict_status = (item.get("_conflict_status", item.get("conflict_status", "")) or "").lower()

            if direction in ("supports", "supporting") or conflict_status == "supporting":
                drug_groups[drug_name]["supporting"].append(item)
            elif direction in ("conflicting", "does not support") or conflict_status == "conflicting":
                drug_groups[drug_name]["conflicting"].append(item)

        for drug_name, groups in drug_groups.items():
            if groups["supporting"] and groups["conflicting"]:
                severity = "high"
                if len(groups["conflicting"]) == 1:
                    severity = "medium"
                conflicts.append({
                    "drug_name": drug_name,
                    "supporting_count": len(groups["supporting"]),
                    "conflicting_count": len(groups["conflicting"]),
                    "severity": severity,
                })

        return conflicts
