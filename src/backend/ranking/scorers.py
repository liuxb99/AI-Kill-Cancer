"""
Scorers for the Drug Ranking Engine.

Each scorer computes a component score for a drug given evidence items.
All scorers produce deterministic scores (0.0 - 1.0 range per item).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Quality weights for evidence sources
SOURCE_QUALITY = {
    "civic": 1.0,
    "dgidb": 0.7,
    "oncotree": 0.6,
    "oncotree_primary": 0.6,
    "knowledge_base": 0.5,
}

# Evidence level weights (CIViC-style)
EVIDENCE_LEVEL_WEIGHT = {
    "Level_1": 1.0,  # FDA-recognized
    "Level_2": 0.9,  # Clinical trial
    "Level_3": 0.7,  # Human case study
    "Level_4": 0.5,  # Preclinical
    "Level_5": 0.3,  # In silico
    "A": 1.0,
    "B": 0.9,
    "C": 0.7,
    "D": 0.5,
    "E": 0.3,
}

# Direction weights
DIRECTION_WEIGHT = {
    "supporting": 1.0,
    "supports": 1.0,
    "sensitive": 1.0,
    "responsiveness": 1.0,
    "conflicting": -0.5,
    "resistance": -1.0,
    "neutral": 0.0,
    "not_evaluable": 0.0,
    "uncertain": 0.0,
}

# Clinical significance weights
SIGNIFICANCE_WEIGHT = {
    "sensitivity": 1.0,
    "resistance": -1.0,
    "reduced_sensitivity": -0.5,
    "improved_response": 1.0,
    "poor_outcome": -0.8,
    "favorable": 0.8,
    "adverse": -0.8,
    "": 0.0,
}

# Match level weights
MATCH_LEVEL_WEIGHT = {
    "exact_variant": 1.0,
    "equivalent_hgvs": 0.95,
    "coordinate_match": 0.9,
    "molecular_profile_match": 0.7,
    "gene_level_only": 0.4,
    "unmatched": 0.0,
}

# Guideline support weights
GUIDELINE_WEIGHT = {
    "nccn": 1.0,
    "asco": 0.9,
    "esmo": 0.9,
    "national_comprehensive_cancer_network": 1.0,
    "american_society_of_clinical_oncology": 0.9,
}

# Regulatory approval weights
REGULATORY_WEIGHT = {
    "fda_approved": 1.0,
    "ema_approved": 0.95,
    "fda_breakthrough": 0.8,
    "fda_orphan": 0.7,
    "investigational": 0.3,
    "not_approved": 0.0,
}


class EvidenceScorer:
    """Scores evidence items by match quality, level, direction, source."""

    def __init__(self, now: Optional[datetime] = None):
        self.now = now or datetime.now(timezone.utc)

    def score(self, drug_name: str, evidence_items: list[dict],
              match_level: str = "gene_level_only") -> tuple[float, int, int, list[str]]:
        """
        Score evidence for a specific drug.
        Returns (total_score, source_count, independent_source_count, evidence_ids).
        """
        if not evidence_items:
            return 0.0, 0, 0, []

        total = 0.0
        seen_sources = set()
        sources_seen_for_drug = set()
        supporting_ids = []

        for item in evidence_items:
            item_drug = (item.get("drug_name", "") or "").strip().lower()
            if item_drug and item_drug != drug_name.strip().lower():
                continue

            # Evidence level weight
            level = item.get("evidence_level", "")
            level_w = EVIDENCE_LEVEL_WEIGHT.get(level, 0.3)

            # Match level weight
            item_match = item.get("_match_level", item.get("match_level", match_level))
            match_w = MATCH_LEVEL_WEIGHT.get(item_match, 0.3)

            # Direction weight
            direction = (item.get("evidence_direction", "") or "").lower()
            dir_w = DIRECTION_WEIGHT.get(direction, 0.0)

            # Source quality
            source = item.get("_source", item.get("source", ""))
            src_w = SOURCE_QUALITY.get(source, 0.5)

            # Evidence type bonus
            ev_type = (item.get("evidence_type", "") or "").lower()
            type_bonus = 0.1 if ev_type in ("predictive", "diagnostic") else 0.0

            # Clinical significance
            significance = (item.get("clinical_significance", "") or "").lower()
            sig_w = SIGNIFICANCE_WEIGHT.get(significance, 0.0)

            # Freshness (items newer than 1 year get 10% bonus)
            freshness = 1.0
            retrieved = item.get("retrieved_at")
            if retrieved and isinstance(retrieved, str):
                try:
                    retrieved_dt = datetime.fromisoformat(retrieved)
                    days_old = (self.now - retrieved_dt).days
                    if days_old < 365:
                        freshness = 1.1
                    elif days_old > 1825:  # 5 years
                        freshness = 0.7
                except (ValueError, TypeError):
                    pass

            # Compound score per item
            item_score = level_w * match_w * abs(dir_w) * src_w * freshness + type_bonus + sig_w

            # Direction flips sign for conflicting/resistance
            if dir_w < 0:
                item_score = -abs(item_score)

            total += item_score

            if item.get("id"):
                item_id = str(item.get("id", ""))
                if item_id and dir_w >= 0:
                    supporting_ids.append(item_id)

            # Track source
            source_record_id = item.get("source_record_id", "")
            if source_record_id:
                seen_sources.add(f"{source}:{source_record_id}")
                if source:
                    sources_seen_for_drug.add(source)

        return total, len(seen_sources), len(sources_seen_for_drug), supporting_ids


class ResistanceScorer:
    """Identifies and scores resistance evidence."""

    def score(self, drug_name: str, evidence_items: list[dict]) -> tuple[float, list[str]]:
        """Score resistance evidence. Returns (penalty, resistance_evidence_ids)."""
        penalty = 0.0
        resistance_ids = []

        for item in evidence_items:
            item_drug = (item.get("drug_name", "") or "").strip().lower()
            if item_drug and item_drug != drug_name.strip().lower():
                continue

            direction = (item.get("evidence_direction", "") or "").lower()
            significance = (item.get("clinical_significance", "") or "").lower()

            is_resistance = (
                "resistance" in direction
                or "resistance" in significance
                or direction == "does not support"
                or significance == "resistance"
                or significance == "reduced_sensitivity"
                or significance == "poor_outcome"
                or significance == "adverse"
            )

            if is_resistance:
                level = item.get("evidence_level", "")
                level_w = EVIDENCE_LEVEL_WEIGHT.get(level, 0.3)
                penalty -= level_w * 0.8  # Significant penalty
                if item.get("id"):
                    resistance_ids.append(str(item.get("id")))

        return penalty, resistance_ids


class SensitivityScorer:
    """Scores sensitivity / responsiveness evidence."""

    def score(self, drug_name: str, evidence_items: list[dict]) -> float:
        """Score sensitivity evidence. Returns bonus score."""
        bonus = 0.0

        for item in evidence_items:
            item_drug = (item.get("drug_name", "") or "").strip().lower()
            if item_drug and item_drug != drug_name.strip().lower():
                continue

            significance = (item.get("clinical_significance", "") or "").lower()
            direction = (item.get("evidence_direction", "") or "").lower()

            is_sensitive = (
                "sensitive" in significance
                or direction == "supports"
                or "response" in significance
                or significance == "favorable"
                or significance == "improved_response"
            )

            if is_sensitive:
                level = item.get("evidence_level", "")
                level_w = EVIDENCE_LEVEL_WEIGHT.get(level, 0.3)
                bonus += level_w * 0.5

        return min(bonus, 5.0)  # Cap sensitivity bonus


class GuidelineScorer:
    """Scores guideline support for drug-disease pairs."""

    # Known guideline-supported drugs per disease
    GUIDELINE_DRUGS: dict[str, list[str]] = {
        "melanoma": ["Vemurafenib", "Dabrafenib", "Trametinib", "Nivolumab", "Pembrolizumab", "Ipilimumab"],
        "nsclc": ["Osimertinib", "Erlotinib", "Gefitinib", "Afatinib", "Crizotinib",
                   "Alectinib", "Ceritinib", "Brigatinib", "Lorlatinib", "Pembrolizumab"],
        "breast": ["Trastuzumab", "Pertuzumab", "Lapatinib", "T-DM1", "Palbociclib",
                    "Ribociclib", "Abemaciclib", "Fulvestrant", "Anastrozole", "Letrozole"],
        "colorectal": ["Cetuximab", "Panitumumab", "Bevacizumab", "Regorafenib"],
        "lung": ["Osimertinib", "Erlotinib", "Gefitinib", "Afatinib", "Crizotinib",
                  "Alectinib", "Ceritinib", "Brigatinib", "Lorlatinib", "Pembrolizumab"],
        "thyroid": ["Lenvatinib", "Sorafenib", "Cabozantinib", "Vandetanib"],
        "gist": ["Imatinib", "Sunitinib", "Regorafenib"],
        "cml": ["Imatinib", "Dasatinib", "Nilotinib", "Bosutinib", "Ponatinib"],
        "her2": ["Trastuzumab", "Pertuzumab", "T-DM1", "Lapatinib", "Neratinib"],
        "braft": ["Vemurafenib", "Dabrafenib", "Encorafenib"],
        "egfr": ["Osimertinib", "Erlotinib", "Gefitinib", "Afatinib", "Dacomitinib"],
        "alk": ["Crizotinib", "Alectinib", "Ceritinib", "Brigatinib", "Lorlatinib"],
        "ros1": ["Crizotinib", "Entrectinib", "Lorlatinib"],
        "ntrk": ["Larotrectinib", "Entrectinib"],
        "kras": ["Sotorasib", "Adagrasib"],
    }

    def score(self, drug_name: str, disease: str = "") -> tuple[float, bool]:
        """Score guideline support. Returns (bonus, has_guideline)."""
        if not disease and not drug_name:
            return 0.0, False

        drug_lower = drug_name.strip().lower()
        disease_lower = disease.strip().lower()

        for key, drugs in self.GUIDELINE_DRUGS.items():
            if disease_lower and disease_lower in key:
                for d in drugs:
                    if d.lower() == drug_lower:
                        return 2.0, True

        # Check across all diseases if no disease context
        if not disease:
            for drugs in self.GUIDELINE_DRUGS.values():
                for d in drugs:
                    if d.lower() == drug_lower:
                        return 1.0, True

        return 0.0, False


class RegulatoryScorer:
    """Scores regulatory approval status."""

    # Known FDA-approved precision oncology drugs
    FDA_APPROVED = [
        "Vemurafenib", "Dabrafenib", "Trametinib", "Cobimetinib",
        "Osimertinib", "Erlotinib", "Gefitinib", "Afatinib", "Dacomitinib",
        "Crizotinib", "Alectinib", "Ceritinib", "Brigatinib", "Lorlatinib",
        "Entrectinib", "Larotrectinib",
        "Trastuzumab", "Pertuzumab", "T-DM1", "Lapatinib", "Neratinib",
        "Palbociclib", "Ribociclib", "Abemaciclib",
        "Imatinib", "Dasatinib", "Nilotinib", "Bosutinib", "Ponatinib",
        "Sunitinib", "Sorafenib", "Regorafenib", "Lenvatinib",
        "Nivolumab", "Pembrolizumab", "Ipilimumab", "Atezolizumab",
        "Cetuximab", "Panitumumab", "Bevacizumab",
        "Sotorasib", "Adagrasib",
        "Olaparib", "Niraparib", "Rucaparib", "Talazoparib",
        "Ibrutinib", "Idelalisib", "Venetoclax",
    ]

    def score(self, drug_name: str) -> tuple[float, bool]:
        """Score regulatory approval. Returns (bonus, is_approved)."""
        drug_lower = drug_name.strip().lower()
        for approved in self.FDA_APPROVED:
            if approved.lower() == drug_lower:
                return 2.0, True
        return 0.0, False


class ClinicalTrialScorer:
    """Scores clinical trial evidence."""

    def score(self, drug_name: str, evidence_items: list[dict]) -> float:
        """Score clinical trial evidence for a drug. Returns bonus."""
        bonus = 0.0
        for item in evidence_items:
            item_drug = (item.get("drug_name", "") or "").strip().lower()
            if item_drug and item_drug != drug_name.strip().lower():
                continue

            evidence_type = (item.get("evidence_type", "") or "").lower()
            if "trial" in evidence_type or "clinical" in evidence_type:
                level = item.get("evidence_level", "")
                level_w = EVIDENCE_LEVEL_WEIGHT.get(level, 0.3)
                bonus += level_w * 0.8

        return min(bonus, 3.0)
