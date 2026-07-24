"""
Evidence Weight / Tier / Confidence / Evidence Level models.

Provides an extensible, registry-based system for mapping knowledge-source
evidence tiers to numeric weights and confidence levels.  Supports FDA,
NCCN, OncoKB, CIViC, DGIdb, and OpenCRAVAT out of the box; new sources
can be added dynamically via ``WeightRegistry.register_source()``.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


# ─── Evidence Tier Enum ────────────────────────────────────────────────────────


class EvidenceTier(str, Enum):
    """Normalised evidence tier across all knowledge sources.

    Tiers are ordered from highest (TIER_0) to lowest (TIER_4); each source
    maps its native categories to one of these five tiers.
    """

    TIER_0 = "Tier_0"
    """Highest evidence — FDA approved / NCCN Category 1 / OncoKB Level 1."""
    TIER_1 = "Tier_1"
    """Strong clinical evidence — NCCN 2A / CIViC A / OncoKB Level 2."""
    TIER_2 = "Tier_2"
    """Moderate clinical evidence — NCCN 2B / CIViC B / OncoKB Level 3."""
    TIER_3 = "Tier_3"
    """Emerging / preclinical evidence — CIViC C / OncoKB Level 4."""
    TIER_4 = "Tier_4"
    """Lowest evidence — in silico prediction / inferred / case report."""


# ─── Confidence Level Enum ──────────────────────────────────────────────────────


class ConfidenceLevel(str, Enum):
    """Confidence assigned to a piece of evidence based on its weight score."""

    HIGH = "HIGH"
    """Weight >= 0.80 — well-validated, regulatory-approved, or large-trial data."""
    MODERATE = "MODERATE"
    """Weight >= 0.50 and < 0.80 — clinical evidence with some limitations."""
    LOW = "LOW"
    """Weight >= 0.20 and < 0.50 — preclinical, small studies, or inferred."""
    UNKNOWN = "UNKNOWN"
    """Weight < 0.20 — insufficient or no supporting data."""


# ─── Evidence Level (Composite) ─────────────────────────────────────────────────


class EvidenceLevel(BaseModel):
    """Fully resolved evidence level for a single evidence item.

    Combines the source identifier, the normalised tier, the source-native
    tier string, the computed numeric weight, and the derived confidence
    level into one composite value.
    """

    source: str
    """Knowledge source identifier, e.g. ``"nccn"``, ``"oncokb"``."""

    tier: EvidenceTier
    """Normalised tier (TIER_0 … TIER_4)."""

    native_tier: str
    """Original tier string from the source, e.g. ``"Category 1"``, ``"Level_3B"``."""

    weight: float = Field(ge=0.0, le=1.0)
    """Numeric weight in [0.0, 1.0] — higher = stronger evidence."""

    confidence: ConfidenceLevel = ConfidenceLevel.UNKNOWN
    """Confidence level derived from the weight value."""


# ─── EvidenceWeightConfig ────────────────────────────────────────────────────────


class EvidenceWeightConfig(BaseModel):
    """Per-source configuration for evidence weight mappings.

    Each knowledge source registers an instance of this config so that
    ``WeightRegistry`` can resolve a native tier string to a numeric weight
    and a ``ConfidenceLevel``.
    """

    source_name: str
    """Unique identifier for the knowledge source, e.g. ``"fda"``."""

    tier_mapping: Dict[str, float]
    """Maps source-native tier strings to weights in [0.0, 1.0].

    Example for NCCN::

        {
            "Category 1": 1.0,
            "Category 2A": 0.85,
            "Category 2B": 0.70,
            "Category 3":  0.50,
            "not_assessed": 0.20,
        }
    """

    base_weight: float = Field(default=1.0, ge=0.0, le=1.0)
    """Source-level multiplier applied on top of the tier mapping.

    Can be used to discount an entire source (e.g. DGIdb = 0.85) relative
    to the tier weight.
    """

    confidence_thresholds: Dict[ConfidenceLevel, float] = Field(
        default_factory=lambda: {
            ConfidenceLevel.HIGH: 0.80,
            ConfidenceLevel.MODERATE: 0.50,
            ConfidenceLevel.LOW: 0.20,
            ConfidenceLevel.UNKNOWN: 0.0,
        }
    )
    """Minimum weight required for each confidence level.

    The highest level whose threshold is met (or exceeded) is assigned.
    Default thresholds: HIGH >= 0.80, MODERATE >= 0.50, LOW >= 0.20.
    """

    weight_version: str = Field(default="1.0.0", pattern=r"^\d+\.\d+\.\d+$")
    """Semantic version of this weight mapping definition."""

    @field_validator("tier_mapping")
    @classmethod
    def _validate_tier_weights(cls, v: Dict[str, float]) -> Dict[str, float]:
        """Ensure all tier weights fall in [0.0, 1.0]."""
        for key, val in v.items():
            if not 0.0 <= val <= 1.0:
                raise ValueError(
                    f"Weight for tier {key!r} ({val}) is outside [0.0, 1.0]"
                )
        return v

    def resolve_weight(self, native_tier: str) -> float:
        """Look up the native tier and apply the source-level base weight.

        Returns ``0.0`` when the tier string is not present in the mapping.
        """
        tier_weight = self.tier_mapping.get(native_tier, 0.0)
        return round(tier_weight * self.base_weight, 6)

    def resolve_confidence(self, weight: float) -> ConfidenceLevel:
        """Derive a ``ConfidenceLevel`` from a numeric weight.

        Iterates thresholds in descending order and returns the highest
        matching level.
        """
        # Sort thresholds descending by value (highest threshold first)
        sorted_levels = sorted(
            self.confidence_thresholds.items(),
            key=lambda kv: kv[1],
            reverse=True,
        )
        for level, threshold in sorted_levels:
            if weight >= threshold:
                return level
        return ConfidenceLevel.UNKNOWN


# ─── WeightRegistry ──────────────────────────────────────────────────────────────


class WeightRegistry:
    """Registry of evidence-weight configurations (singleton pattern).

    Sources are registered once (typically at import time) and can be
    looked up by name thereafter.  The registry is pre-populated with
    default configurations for six major knowledge sources.
    """

    _sources: Dict[str, EvidenceWeightConfig] = {}

    # ── Registration ───────────────────────────────────────────────────────

    @classmethod
    def register_source(
        cls,
        config: EvidenceWeightConfig,
        *,
        overwrite: bool = False,
    ) -> None:
        """Register (or update) a source weight configuration.

        Parameters
        ----------
        config : EvidenceWeightConfig
            Fully populated per-source configuration.
        overwrite : bool
            If ``False`` (default), raises ``KeyError`` when the source
            already exists.  Pass ``True`` to silently replace an existing
            entry.
        """
        name = config.source_name
        if not overwrite and name in cls._sources:
            raise KeyError(
                f"Source {name!r} is already registered. "
                "Use overwrite=True to replace it."
            )
        cls._sources[name] = config

    @classmethod
    def unregister_source(cls, name: str) -> None:
        """Remove a previously registered source.

        Raises ``KeyError`` if the source does not exist.
        """
        cls._sources.pop(name)

    @classmethod
    def registered_sources(cls) -> frozenset[str]:
        """Return an immutable set of all registered source names."""
        return frozenset(cls._sources)

    @classmethod
    def get_config(cls, source: str) -> EvidenceWeightConfig:
        """Retrieve the config for a source.

        Raises ``KeyError`` when the source has not been registered.
        """
        if source not in cls._sources:
            raise KeyError(
                f"Source {source!r} is not registered. "
                f"Available sources: {sorted(cls._sources)}"
            )
        return cls._sources[source]

    @classmethod
    def get_weight(
        cls,
        source: str,
        native_tier: str,
    ) -> float:
        """Resolve the numeric weight for a source + native tier string.

        Shorthand for ``get_config(source).resolve_weight(native_tier)``.
        """
        return cls.get_config(source).resolve_weight(native_tier)

    @classmethod
    def get_evidence_level(
        cls,
        source: str,
        native_tier: str,
    ) -> EvidenceLevel:
        """Build a full ``EvidenceLevel`` from source + native tier string.

        The normalised ``EvidenceTier`` is inferred from the native tier
        via the source's own mapping heuristic (override
        ``_map_to_evidence_tier`` per source for custom logic).  For most
        sources the native tier name already encodes the tier level.
        """
        config = cls.get_config(source)
        weight = config.resolve_weight(native_tier)
        confidence = config.resolve_confidence(weight)
        tier = cls._infer_tier(source, native_tier, weight)

        return EvidenceLevel(
            source=source,
            tier=tier,
            native_tier=native_tier,
            weight=weight,
            confidence=confidence,
        )

    # ── Tier inference ─────────────────────────────────────────────────────

    @classmethod
    def _infer_tier(
        cls,
        source: str,
        native_tier: str,
        weight: float,
    ) -> EvidenceTier:
        """Infer a normalised ``EvidenceTier`` for a given source + tier.

        The default implementation uses weight thresholds:
            >= 0.90 → TIER_0
            >= 0.75 → TIER_1
            >= 0.55 → TIER_2
            >= 0.30 → TIER_3
            <  0.30 → TIER_4

        Sources with non-standard mappings can override this method
        by subclassing ``WeightRegistry`` and providing a custom
        ``_infer_tier``.
        """
        if weight >= 0.90:
            return EvidenceTier.TIER_0
        if weight >= 0.75:
            return EvidenceTier.TIER_1
        if weight >= 0.55:
            return EvidenceTier.TIER_2
        if weight >= 0.30:
            return EvidenceTier.TIER_3
        return EvidenceTier.TIER_4


# ═══════════════════════════════════════════════════════════════════════════════
# Default source registrations
# ═══════════════════════════════════════════════════════════════════════════════

# ─── FDA ────────────────────────────────────────────────────────────────────────

WeightRegistry.register_source(
    EvidenceWeightConfig(
        source_name="fda",
        base_weight=1.0,
        tier_mapping={
            "Approved": 1.0,
            "Breakthrough Therapy": 0.90,
            "Fast Track": 0.75,
            "Orphan Drug": 0.60,
            "Investigational": 0.40,
            "not_assessed": 0.10,
        },
        weight_version="1.0.0",
    )
)

# ─── NCCN ───────────────────────────────────────────────────────────────────────

WeightRegistry.register_source(
    EvidenceWeightConfig(
        source_name="nccn",
        base_weight=1.0,
        tier_mapping={
            "Category 1": 1.0,
            "Category 2A": 0.85,
            "Category 2B": 0.70,
            "Category 3": 0.50,
            "not_assessed": 0.20,
        },
        weight_version="1.0.0",
    )
)

# ─── OncoKB ─────────────────────────────────────────────────────────────────────

WeightRegistry.register_source(
    EvidenceWeightConfig(
        source_name="oncokb",
        base_weight=1.0,
        tier_mapping={
            "Level 1": 1.0,
            "Level 2": 0.85,
            "Level 3A": 0.70,
            "Level 3B": 0.60,
            "Level 4": 0.45,
            "Level R1": 0.80,
            "Level R2": 0.65,
            "not_assessed": 0.15,
        },
        weight_version="1.0.0",
    )
)

# ─── CIViC ──────────────────────────────────────────────────────────────────────

WeightRegistry.register_source(
    EvidenceWeightConfig(
        source_name="civic",
        base_weight=1.0,
        tier_mapping={
            "A": 1.0,
            "B": 0.85,
            "C": 0.65,
            "D": 0.45,
            "E": 0.25,
            "not_assessed": 0.10,
        },
        weight_version="1.0.0",
    )
)

# ─── DGIdb ──────────────────────────────────────────────────────────────────────

WeightRegistry.register_source(
    EvidenceWeightConfig(
        source_name="dgidb",
        base_weight=0.85,
        tier_mapping={
            "FDA-approved": 0.90,
            "Clinical trial": 0.70,
            "Preclinical": 0.50,
            "Literature-supported": 0.30,
            "Inferred": 0.15,
            "not_assessed": 0.05,
        },
        weight_version="1.0.0",
    )
)

# ─── OpenCRAVAT ─────────────────────────────────────────────────────────────────

WeightRegistry.register_source(
    EvidenceWeightConfig(
        source_name="opencravat",
        base_weight=1.0,
        tier_mapping={
            "Pathogenic + FDA-approved therapy": 0.95,
            "Pathogenic + Clinical trial": 0.80,
            "Pathogenic + Standard of care": 0.85,
            "Likely pathogenic": 0.60,
            "VUS with functional data": 0.40,
            "VUS": 0.20,
            "Benign": 0.05,
            "not_assessed": 0.05,
        },
        weight_version="1.0.0",
    )
)


__all__ = [
    "ConfidenceLevel",
    "EvidenceLevel",
    "EvidenceTier",
    "EvidenceWeightConfig",
    "WeightRegistry",
]
