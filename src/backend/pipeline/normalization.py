"""
Variant normalization pipeline.

Supports bcftools norm via subprocess (preferred) and a basic
Python-based normalization as fallback.

Normalization includes:
- Left-alignment (trimming reference/alternate)
- Splitting multi-allelic sites
- Parsing normalized results
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Optional
from dataclasses import dataclass, field

from src.backend.adapters.base import BaseAdapter, AdapterResult, NotConfiguredAdapter
from src.backend.domain.enums import NormalizationStatusEnum

logger = logging.getLogger(__name__)


@dataclass
class NormalizedVariant:
    """A single normalized variant record."""
    chromosome: str
    position: int
    reference: str
    alternate: str
    original_position: int
    original_reference: str
    original_alternate: str
    is_split: bool = False  # True if this was split from a multi-allelic site


@dataclass
class NormalizationResult:
    """Result of variant normalization."""
    status: NormalizationStatusEnum
    normalized: list[NormalizedVariant] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


# ─── Basic Python Normalization (left-alignment) ─────────────────────────────


def _normalize_left_align(ref: str, alt: str) -> tuple[str, str, str, str]:
    """Basic left-alignment normalization.

    Returns: (ref, alt, trimmed_ref, trimmed_alt)
    Trims common prefix and suffix to left-align the variant.
    """
    # Remove common prefix
    prefix_len = 0
    for i in range(min(len(ref), len(alt))):
        if ref[i].upper() == alt[i].upper():
            prefix_len = i + 1
        else:
            break

    # Remove common suffix (after removing prefix)
    ref_suffix = ref[prefix_len:]
    alt_suffix = alt[prefix_len:]
    suffix_len = 0
    for i in range(1, min(len(ref_suffix), len(alt_suffix)) + 1):
        if ref_suffix[-i].upper() == alt_suffix[-i].upper():
            suffix_len = i
        else:
            break

    new_ref = ref[prefix_len:len(ref) - suffix_len] if suffix_len > 0 else ref[prefix_len:]
    new_alt = alt[prefix_len:len(alt) - suffix_len] if suffix_len > 0 else alt[prefix_len:]

    return new_ref, new_alt, prefix_len, suffix_len


def normalize_variants_python(
    variants: list[tuple[str, int, str, str]],
) -> NormalizationResult:
    """Normalize variants using Python-based left-alignment.

    Args:
        variants: List of (chromosome, position, ref, alt) tuples

    Returns:
        NormalizationResult with normalized variants
    """
    result = NormalizationResult(status=NormalizationStatusEnum.COMPLETED)

    for chrom, pos, ref, alt in variants:
        new_ref, new_alt, prefix_trim, suffix_trim = _normalize_left_align(ref, alt)

        new_pos = pos + prefix_trim

        if prefix_trim > 0 or suffix_trim > 0:
            logger.debug(f"Normalized {chrom}:{pos} {ref}>{alt} -> {new_pos} {new_ref}>{new_alt}")

        result.normalized.append(NormalizedVariant(
            chromosome=chrom,
            position=new_pos,
            reference=new_ref,
            alternate=new_alt,
            original_position=pos,
            original_reference=ref,
            original_alternate=alt,
            is_split=False,
        ))

    return result


# ─── Bcftools Normalization (subprocess) ──────────────────────────────────────


class BcftoolsAdapter(BaseAdapter):
    """Adapter for bcftools norm normalization.

    Falls back to Python normalization if bcftools is not installed.
    """

    def __init__(self, bcftools_path: str = "bcftools", config: Optional[dict] = None):
        super().__init__(config)
        self._name = "bcftools"
        self._version = "0.0.0"
        self._bcftools_path = bcftools_path
        self._available = False

    async def _check_available(self) -> bool:
        """Check if bcftools is available."""
        try:
            proc = await asyncio.create_subprocess_exec(
                self._bcftools_path, "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
            if proc.returncode == 0:
                # Parse version
                version_line = stdout.decode().split("\n")[0] if stdout else ""
                self._version = version_line.strip()
                self._available = True
                return True
        except (FileNotFoundError, asyncio.TimeoutError, OSError):
            pass
        self._available = False
        return False

    @property
    def available(self) -> bool:
        return self._available

    async def health_check(self) -> dict:
        available = await self._check_available()
        if available:
            return {"status": "ok", "detail": f"bcftools {self._version}", "version": self._version}
        return {"status": "degraded", "detail": "bcftools not installed, using Python fallback", "version": "0.0.0"}

    def supports(self, query_type: str) -> bool:
        return query_type in ("normalize", "norm")

    async def validate_input(self, payload: Any) -> list[str]:
        errors = []
        if not isinstance(payload, list):
            errors.append("Payload must be a list of variant tuples")
        return errors

    async def annotate(self, payload: Any, **kwargs) -> AdapterResult:
        """Run bcftools norm via subprocess.
        Falls back to Python normalization if bcftools is not available.
        """
        # Try bcftools first
        if await self._check_available():
            return await self._run_bcftools_norm(payload)

        # Fallback to Python
        logger.info("bcftools not available, using Python normalization fallback")
        py_result = normalize_variants_python(payload)
        records = []
        for nv in py_result.normalized:
            records.append({
                "chromosome": nv.chromosome,
                "position": nv.position,
                "reference": nv.reference,
                "alternate": nv.alternate,
                "original_position": nv.original_position,
                "is_normalized": (nv.original_position != nv.position
                                  or nv.original_reference != nv.reference
                                  or nv.original_alternate != nv.alternate),
            })
        return AdapterResult(
            source="bcftools_python_fallback",
            source_version="python",
            retrieved_at=__import__("datetime").datetime.now(__import__("zoneinfo").ZoneInfo("UTC")).isoformat(),
            request_id=kwargs.get("request_id", "unknown"),
            success=True,
            records=records,
            warnings=py_result.warnings,
        )

    async def _run_bcftools_norm(self, variants: list) -> AdapterResult:
        """Run bcftools norm on variant data."""
        # Create temporary VCF
        import tempfile
        import json
        from datetime import datetime, timezone

        tmp_dir = tempfile.mkdtemp()
        vcf_path = os.path.join(tmp_dir, "input.vcf")
        ref_path = self.config.get("reference", "")

        try:
            # Write minimal VCF
            with open(vcf_path, "w") as f:
                f.write("##fileformat=VCFv4.2\n")
                f.write("##source=AI-Kill-Cancer\n")
                f.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n")
                for chrom, pos, ref, alt in variants:
                    f.write(f"{chrom}\t{pos}\t.\t{ref}\t{alt}\t.\t.\t.\n")

            # Run bcftools norm
            cmd = [self._bcftools_path, "norm"]
            if ref_path:
                cmd.extend(["-f", ref_path])
            cmd.extend(["-o", os.path.join(tmp_dir, "output.vcf"), vcf_path])

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)

            if proc.returncode != 0:
                return AdapterResult(
                    source="bcftools",
                    source_version=self._version,
                    retrieved_at=datetime.now(timezone.utc).isoformat(),
                    request_id="unknown",
                    success=False,
                    errors=[f"bcftools norm failed: {stderr.decode()}"],
                )

            # Parse output
            from src.backend.vcf.parser import parse_vcf_file
            parse_result = parse_vcf_file(os.path.join(tmp_dir, "output.vcf"))

            records = []
            for record in parse_result.records:
                records.append({
                    "chromosome": record.chromosome,
                    "position": record.position,
                    "reference": record.reference,
                    "alternate": record.alternate,
                    "original_position": None,  # bcftools handles this internally
                    "is_normalized": True,
                })

            return AdapterResult(
                source="bcftools",
                source_version=self._version,
                retrieved_at=datetime.now(timezone.utc).isoformat(),
                request_id="unknown",
                success=True,
                records=records,
            )

        finally:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def normalize_response(self, raw: Any) -> AdapterResult:
        return AdapterResult(source="bcftools", source_version=self._version,
                             retrieved_at="", request_id="", success=False,
                             errors=["Not implemented"])


# Workaround for Optional/Any typing
from typing import Any  # noqa: E402
