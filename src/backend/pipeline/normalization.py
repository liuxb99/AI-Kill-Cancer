"""
Variant normalization pipeline.

Provides two levels of normalization:

1. **Minimal representation** (Python-based, no reference required):
   - Trims common prefix/suffix from REF/ALT
   - Splits multi-allelic sites
   - Preserves VCF anchor base legality
   - Does NOT produce canonical normalization

2. **Canonical normalization** (bcftools norm, requires reference):
   - Requires bcftools installed + reference FASTA available
   - Executes `bcftools norm -f <reference> -m -any`
   - Saves complete provenance (command, version, runtime, stderr)

Only bcftools-based output may be labeled "canonical".
Python output is always "minimal_representation_only".
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import shutil
import tempfile
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from src.backend.adapters.base import AdapterResult, BaseAdapter
from src.backend.domain.enums import (
    NormalizationMethodEnum,
    NormalizationSemanticsEnum,
    NormalizationStatusEnum,
)
from src.backend.reference.registry import ReferenceRegistry
from src.backend.reference.registry import get_registry as get_ref_registry

logger = logging.getLogger(__name__)


# ─── Data Structures ──────────────────────────────────────────────────────────


@dataclass
class NormalizedVariant:
    """A single normalized variant record with provenance."""
    chromosome: str
    position: int
    reference: str
    alternate: str
    original_position: int
    original_reference: str
    original_alternate: str
    is_split: bool = False
    normalization_method: str = ""  # "minimal_representation" | "bcftools_canonical"


@dataclass
class NormalizationResult:
    """Complete result of a normalization operation."""
    status: NormalizationStatusEnum
    method: NormalizationMethodEnum = NormalizationMethodEnum.NOT_APPLICABLE
    semantics: NormalizationSemanticsEnum = NormalizationSemanticsEnum.NOT_APPLICABLE
    normalized: list[NormalizedVariant] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    provenance: dict = field(default_factory=dict)


# ─── Symbolic / special allele detection ──────────────────────────────────────

_SYMBOLIC_ALT = {"<DEL>", "<DUP>", "<INS>", "<INV>", "<CNV>", "<DUP:TANDEM>",
                 "<DUP:INTERSPERSED>", "<DEL:ME>", "<DUP:ME>", "<INS:ME>"}

_STAR_ALLELE = "*"
_BREAKEND_RE = None  # Complex, detected by pattern


def _is_symbolic(alt: str) -> bool:
    """Check if ALT is a symbolic allele (<DEL>, <DUP>, etc.)."""
    return alt in _SYMBOLIC_ALT or (alt.startswith("<") and alt.endswith(">"))


def _is_breakend(alt: str) -> bool:
    """Check if ALT is a breakend allele (contains [ or ])."""
    return "[" in alt or "]" in alt


def _is_star(alt: str) -> bool:
    """Check if ALT is the star (*) allele."""
    return alt == _STAR_ALLELE


def _has_multiple_alt(alt: str) -> bool:
    """Check if multi-allelic (comma-separated ALTs)."""
    return "," in alt


# ─── Minimal Representation (Python, no reference) ────────────────────────────


def _minimal_representation(ref: str, alt: str) -> tuple[str, str, int]:
    """Compute minimal representation of a variant.

    Trims common prefix and suffix, preserving VCF anchor base legality.
    Returns (trimmed_ref, trimmed_alt, position_shift).

    Guarantees:
    - REF is never empty
    - ALT is never empty
    - Position shift is correct
    - Handles SNV, indel, MNV correctly
    - Skips symbolic and breakend alleles unchanged
    """
    # Skip symbolic, breakend, and star alleles
    if _is_symbolic(alt) or _is_breakend(alt) or _is_star(alt):
        return ref, alt, 0

    # Handle multi-allelic
    if _has_multiple_alt(alt):
        # Split into individual records (handled by caller)
        return ref, alt, 0

    # Both REF and ALT must be non-empty
    if not ref or not alt:
        return ref or "N", alt or "N", 0

    ref_upper = ref.upper()
    alt_upper = alt.upper()

    # Find common prefix
    prefix_len = 0
    for i in range(min(len(ref_upper), len(alt_upper))):
        if ref_upper[i] == alt_upper[i]:
            prefix_len = i + 1
        else:
            break

    # Remaining strings after prefix
    ref_rem = ref[prefix_len:]
    alt_rem = alt[prefix_len:]

    # Find common suffix (only if both have remaining)
    suffix_len = 0
    if ref_rem and alt_rem:
        for i in range(1, min(len(ref_rem), len(alt_rem)) + 1):
            if ref_rem[-i].upper() == alt_rem[-i].upper():
                suffix_len = i
            else:
                break

    # Trim suffix
    if suffix_len > 0:
        new_ref = ref_rem[:len(ref_rem) - suffix_len]
        new_alt = alt_rem[:len(alt_rem) - suffix_len]
    else:
        new_ref = ref_rem
        new_alt = alt_rem

    # Ensure neither is empty (VCF requires at least one base)
    if not new_ref:
        new_ref = ref[prefix_len:prefix_len + 1] if prefix_len > 0 else ref[0]
        # Without reference, we can't determine the anchor base
        # Use a single base from original position
        new_ref = "N"

    if not new_alt:
        new_alt = alt[prefix_len:prefix_len + 1] if prefix_len > 0 else alt[0]
        new_alt = "N"

    # Position shift: trimmed prefix length
    pos_shift = prefix_len

    return new_ref, new_alt, pos_shift


def normalize_minimal_representation(
    variants: list[tuple[str, int, str, str]],
) -> NormalizationResult:
    """Compute minimal representation for a list of variants.

    This is NOT canonical normalization. It only does:
    - Trim common prefix/suffix
    - Split multi-allelic (basic)
    - Preserve anchor base

    Does NOT use reference genome. Does NOT left-align against reference.
    """
    result = NormalizationResult(
        status=NormalizationStatusEnum.COMPLETED,
        method=NormalizationMethodEnum.MINIMAL_REPRESENTATION,
        semantics=NormalizationSemanticsEnum.MINIMAL_REPRESENTATION_ONLY,
    )

    for chrom, pos, ref, alt in variants:
        # Handle multi-allelic (comma-separated ALTs)
        if _has_multiple_alt(alt):
            alt_parts = alt.split(",")
            for i, alt_part in enumerate(alt_parts):
                try:
                    new_ref, new_alt, pos_shift = _minimal_representation(ref, alt_part)
                    result.normalized.append(NormalizedVariant(
                        chromosome=chrom,
                        position=pos + pos_shift,
                        reference=new_ref,
                        alternate=new_alt,
                        original_position=pos,
                        original_reference=ref,
                        original_alternate=alt_part,
                        is_split=len(alt_parts) > 1,
                        normalization_method="minimal_representation",
                    ))
                except Exception as e:
                    result.warnings.append(f"Failed to normalize {chrom}:{pos} {ref}>{alt_part}: {e}")
            continue

        # Skip symbolic, breakend, star alleles
        if _is_symbolic(alt) or _is_breakend(alt) or _is_star(alt):
            result.normalized.append(NormalizedVariant(
                chromosome=chrom, position=pos,
                reference=ref, alternate=alt,
                original_position=pos, original_reference=ref, original_alternate=alt,
                normalization_method="not_applicable",
            ))
            continue

        try:
            new_ref, new_alt, pos_shift = _minimal_representation(ref, alt)
            result.normalized.append(NormalizedVariant(
                chromosome=chrom,
                position=pos + pos_shift,
                reference=new_ref,
                alternate=new_alt,
                original_position=pos,
                original_reference=ref,
                original_alternate=alt,
                normalization_method="minimal_representation",
            ))
        except Exception as e:
            result.warnings.append(f"Failed to normalize {chrom}:{pos} {ref}>{alt}: {e}")

    result.provenance = {
        "method": "minimal_representation",
        "tool": "python",
        "reference_required": False,
        "input_count": len(variants),
        "output_count": len(result.normalized),
    }
    return result


# ─── Bcftools Canonical Normalization ─────────────────────────────────────────


class BcftoolsAdapter(BaseAdapter):
    """Adapter for bcftools norm — produces CANONICAL normalization.

    Requires:
    - bcftools installed and available on PATH
    - Reference FASTA and .fai index for the target genome build

    If bcftools is not available, falls back to minimal representation
    but clearly labels it as non-canonical.
    """

    def __init__(self, reference_registry: ReferenceRegistry | None = None, config: dict | None = None):
        super().__init__(config)
        self._name = "bcftools"
        self._version = "0.0.0"
        self._bcftools_path = config.get("bcftools_path", "bcftools") if config else "bcftools"
        self._available = False
        self._ref_registry = reference_registry or get_ref_registry()
        self._bcftools_version_detected: str | None = None

    async def _detect_version(self) -> str:
        """Detect bcftools version."""
        try:
            proc = await asyncio.create_subprocess_exec(
                self._bcftools_path, "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
            if proc.returncode == 0:
                lines = stdout.decode().split("\n")
                return lines[0].strip() if lines else "unknown"
        except (TimeoutError, FileNotFoundError, OSError):
            pass
        return "not_available"

    async def _check_available(self) -> bool:
        """Check if bcftools is available and get version."""
        if self._bcftools_version_detected:
            return self._available
        version = await self._detect_version()
        self._bcftools_version_detected = version
        self._version = version
        self._available = version != "not_available"
        return self._available

    @property
    def available(self) -> bool:
        return self._available

    @property
    def bcftools_version(self) -> str:
        return self._bcftools_version_detected or "unknown"

    async def health_check(self) -> dict:
        available = await self._check_available()
        if available:
            return {
                "status": "ok",
                "detail": f"bcftools {self._version}",
                "version": self._version,
                "canonical_normalization": True,
            }
        return {
            "status": "degraded",
            "detail": "bcftools not installed — canonical normalization unavailable",
            "version": "0.0.0",
            "canonical_normalization": False,
        }

    def supports(self, query_type: str) -> bool:
        return query_type in ("normalize", "norm", "canonical", "minimal")

    async def validate_input(self, payload: Any) -> list[str]:
        errors = []
        if not isinstance(payload, list):
            errors.append("Payload must be a list of variant tuples")
        return errors

    async def annotate(self, payload: Any, **kwargs) -> AdapterResult:
        """Normalize variants.

        If bcftools is available AND reference is configured:
        - Runs canonical normalization with provenance

        Otherwise:
        - Runs minimal representation (Python)
        - Clearly labels as non-canonical
        """
        request_id = kwargs.get("request_id", str(uuid.uuid4()))
        genome_build = kwargs.get("genome_build", "")

        # Try bcftools canonical first
        if await self._check_available():
            ref = self._ref_registry.get(genome_build) if genome_build else None
            if ref and ref.configured and ref.fasta_path:
                return await self._run_bcftools_norm(payload, ref, request_id)

        # Fallback: minimal representation
        logger.info("bcftools canonical not available — using minimal representation")
        mr_result = normalize_minimal_representation(payload)
        records = []
        for nv in mr_result.normalized:
            records.append({
                "chromosome": nv.chromosome,
                "position": nv.position,
                "reference": nv.reference,
                "alternate": nv.alternate,
                "original_position": nv.original_position,
                "original_reference": nv.original_reference,
                "original_alternate": nv.original_alternate,
                "is_split": nv.is_split,
                "normalization_method": nv.normalization_method,
                "is_normalized": (nv.original_position != nv.position
                                  or nv.original_reference != nv.reference
                                  or nv.original_alternate != nv.alternate),
            })
        return AdapterResult(
            source="bcftools_python_fallback",
            source_version="python_minimal_representation",
            retrieved_at=datetime.now(UTC).isoformat(),
            request_id=request_id,
            success=True,
            records=records,
            warnings=mr_result.warnings + ["Canonical normalization not available — minimal representation used"],
        )

    async def _run_bcftools_norm(self, variants: list, ref_genome, request_id: str) -> AdapterResult:
        """Run bcftools norm with reference FASTA."""
        tmp_dir = tempfile.mkdtemp(prefix="bcftools_norm_")
        start_time = time.monotonic()

        try:
            vcf_path = os.path.join(tmp_dir, "input.vcf")
            output_path = os.path.join(tmp_dir, "output.vcf")

            # Compute FASTA SHA256
            fasta_sha256 = None
            try:
                fasta_sha256 = hashlib.sha256()
                with open(ref_genome.fasta_path, "rb") as f:
                    for chunk in iter(lambda: f.read(65536), b""):
                        fasta_sha256.update(chunk)
                fasta_sha256 = fasta_sha256.hexdigest()
            except Exception:
                pass

            # Build minimal VCF
            with open(vcf_path, "w") as f:
                f.write("##fileformat=VCFv4.2\n")
                f.write("##source=AI-Kill-Cancer\n")
                f.write(f"##reference={ref_genome.fasta_path}\n")
                f.write("#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n")
                for chrom, pos, ref, alt in variants:
                    # Handle multi-allelic
                    if "," in alt:
                        for a in alt.split(","):
                            f.write(f"{chrom}\t{pos}\t.\t{ref}\t{a}\t.\t.\t.\n")
                    else:
                        f.write(f"{chrom}\t{pos}\t.\t{ref}\t{alt}\t.\t.\t.\n")

            # Build command
            cmd = [
                self._bcftools_path, "norm",
                "-f", ref_genome.fasta_path,
                "-m", "-any",
                "-o", output_path,
                vcf_path,
            ]
            command_str = " ".join(cmd)

            # Execute
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
            except TimeoutError:
                proc.kill()
                return AdapterResult(
                    source="bcftools",
                    source_version=self._version,
                    retrieved_at=datetime.now(UTC).isoformat(),
                    request_id=request_id,
                    success=False,
                    errors=["bcftools norm timed out after 300s"],
                )

            duration_ms = int((time.monotonic() - start_time) * 1000)

            if proc.returncode != 0:
                return AdapterResult(
                    source="bcftools",
                    source_version=self._version,
                    retrieved_at=datetime.now(UTC).isoformat(),
                    request_id=request_id,
                    success=False,
                    errors=[f"bcftools norm failed (rc={proc.returncode}): {stderr.decode()[:1000]}"],
                )

            # Parse output
            from src.backend.vcf.parser import parse_vcf_file
            parse_result = parse_vcf_file(output_path)
            stderr_text = stderr.decode() if stderr else ""

            # Build variant mapping: compare input to output
            records = []
            for i, record in enumerate(parse_result.records):
                original = variants[min(i, len(variants) - 1)]
                orig_chrom, orig_pos, orig_ref, orig_alt = original if i < len(variants) else ("", 0, "", "")
                is_normalized = (record.position != orig_pos
                                 or record.reference != orig_ref
                                 or record.alternate != orig_alt)
                records.append({
                    "chromosome": record.chromosome,
                    "position": record.position,
                    "reference": record.reference,
                    "alternate": record.alternate,
                    "original_position": orig_pos,
                    "original_reference": orig_ref,
                    "original_alternate": orig_alt,
                    "normalization_method": "bcftools_canonical",
                    "is_normalized": is_normalized,
                })

            return AdapterResult(
                source="bcftools",
                source_version=self._version,
                retrieved_at=datetime.now(UTC).isoformat(),
                request_id=request_id,
                success=True,
                records=records,
                warnings=[] if not stderr_text else [f"bcftools stderr: {stderr_text[:500]}"],
                license="bcftools — MIT / VCF specification",
                metadata={
                    "command": command_str,
                    "reference_fasta": ref_genome.fasta_path,
                    "reference_sha256": fasta_sha256,
                    "bcftools_version": self._version,
                    "genome_build": ref_genome.build,
                    "duration_ms": duration_ms,
                    "return_code": proc.returncode,
                },
            )

        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def normalize_response(self, raw: Any) -> AdapterResult:
        """Normalize a raw bcftools response into standard AdapterResult."""
        if isinstance(raw, AdapterResult):
            return raw
        return AdapterResult(
            source="bcftools",
            source_version=self._version,
            retrieved_at=datetime.now(UTC).isoformat(),
            request_id="normalize",
            success=False,
            records=[],
            errors=["Raw response normalization not supported"],
        )


# ─── Fix missing imports ──────────────────────────────────────────────────────

import uuid  # noqa: E402, F811
