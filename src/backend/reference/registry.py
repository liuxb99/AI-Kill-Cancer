"""
Reference genome registry — manages configured reference genomes and their metadata.

Supports GRCh37 and GRCh38 with FASTA paths, SHA256 checksums, and validation.
"""

from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


@dataclass
class ReferenceGenome:
    """A configured reference genome assembly."""
    build: str  # "GRCh37" or "GRCh38"
    display_name: str = ""
    fasta_path: str | None = None
    fai_path: str | None = None
    sha256: str | None = None
    source: str | None = None
    version: str | None = None
    configured: bool = False
    validated_at: str | None = None


class ReferenceRegistry:
    """Registry of configured reference genomes.

    References are configured via environment variables or direct API.
    Phase 2A: references must be explicitly configured; auto-detection
    only outputs a candidate, never used for canonical normalization.
    """

    def __init__(self):
        self._references: dict[str, ReferenceGenome] = {}

    def register(self, build: str, fasta_path: str | None = None, **kwargs) -> ReferenceGenome:
        """Register a reference genome build."""
        ref = ReferenceGenome(
            build=build,
            display_name=kwargs.get("display_name", build),
            fasta_path=fasta_path,
            fai_path=kwargs.get("fai_path"),
            sha256=kwargs.get("sha256"),
            source=kwargs.get("source"),
            version=kwargs.get("version"),
            configured=fasta_path is not None and os.path.isfile(fasta_path) if fasta_path else False,
        )
        if ref.configured and ref.fasta_path:
            ref.fai_path = ref.fai_path or ref.fasta_path + ".fai"
            if os.path.isfile(ref.fai_path):
                ref.validated_at = datetime.now(UTC).isoformat()
        self._references[build] = ref
        return ref

    def get(self, build: str) -> ReferenceGenome | None:
        """Get a reference by build name."""
        return self._references.get(build)

    def is_configured(self, build: str) -> bool:
        """Check if a reference build is configured and available."""
        ref = self.get(build)
        return ref is not None and ref.configured

    def list_configured(self) -> list[ReferenceGenome]:
        """List all configured references."""
        return [r for r in self._references.values() if r.configured]

    def list_all(self) -> list[ReferenceGenome]:
        """List all registered references."""
        return list(self._references.values())

    def validate_fasta(self, build: str) -> str | None:
        """Validate reference FASTA and return SHA256 (or None if unavailable)."""
        ref = self.get(build)
        if not ref or not ref.fasta_path or not os.path.isfile(ref.fasta_path):
            return None
        try:
            sha256 = hashlib.sha256()
            with open(ref.fasta_path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception as e:
            logger.error(f"Failed to compute SHA256 for {build}: {e}")
            return None

    def get_build_for_genome_build(self, build: str) -> str | None:
        """Normalize genome build string to canonical name."""
        build_lower = build.lower().replace("_", "").replace("-", "")
        mapping = {
            "grch37": "GRCh37", "hg19": "GRCh37", "b37": "GRCh37", "hs37d5": "GRCh37",
            "grch38": "GRCh38", "hg38": "GRCh38",
        }
        return mapping.get(build_lower)


# Global registry
_registry: ReferenceRegistry | None = None


def get_registry() -> ReferenceRegistry:
    """Get or create the global reference registry."""
    global _registry
    if _registry is None:
        _registry = ReferenceRegistry()
        _load_from_env(_registry)
    return _registry


def _load_from_env(registry: ReferenceRegistry) -> None:
    """Load reference configurations from environment variables."""
    env_prefix = "REF_"
    for key, val in os.environ.items():
        if not key.startswith(env_prefix):
            continue
        parts = key[len(env_prefix):].lower().split("_", 1)
        if len(parts) != 2:
            continue
        build, field = parts
        build_upper = build.upper()
        if build_upper not in ("GRCH37", "GRCH38"):
            continue
        canonical = build_upper.replace("G", "G")
        if field == "path":
            registry.register(canonical, fasta_path=val)
        elif field == "sha256":
            ref = registry.get(canonical)
            if ref:
                ref.sha256 = val
        elif field == "version":
            ref = registry.get(canonical)
            if ref:
                ref.version = val
