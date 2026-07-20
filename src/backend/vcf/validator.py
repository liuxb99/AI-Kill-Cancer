"""
VCF validation module — checks VCF file integrity and format compliance.

Supports VCF v4.1, v4.2, v4.3.
"""

from __future__ import annotations

import re
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class VCFValidationError:
    """A single validation error with code and context."""
    code: str
    message: str
    line: Optional[int] = None
    field: Optional[str] = None


@dataclass
class VCFValidationResult:
    """Result of VCF validation."""
    valid: bool = True
    errors: list[VCFValidationError] = field(default_factory=list)
    warnings: list[VCFValidationError] = field(default_factory=list)
    file_format: Optional[str] = None
    genome_build: Optional[str] = None
    sample_count: int = 0
    record_count: int = 0

    def add_error(self, code: str, message: str, line: Optional[int] = None, field: Optional[str] = None):
        self.valid = False
        self.errors.append(VCFValidationError(code=code, message=message, line=line, field=field))

    def add_warning(self, code: str, message: str, line: Optional[int] = None, field: Optional[str] = None):
        self.warnings.append(VCFValidationError(code=code, message=message, line=line, field=field))


# Chromosome validation
_VALID_CHROMOSOMES_GRCH37 = {str(i) for i in range(1, 23)} | {"X", "Y", "MT"}
_VALID_CHROMOSOMES_GRCH38 = {str(i) for i in range(1, 23)} | {"X", "Y", "MT"}

# Basic VCF regex patterns
_CHROM_RE = re.compile(r"^(\d+|X|Y|MT|chr\d+|chrX|chrY|chrMT)$")
_POSITION_RE = re.compile(r"^\d+$")
_REF_ALT_RE = re.compile(r"^[ACGTNacgtn.]+$")


def _detect_fileformat(lines: list[str]) -> Optional[str]:
    """Detect VCF format version from fileformat header."""
    for line in lines:
        line = line.strip()
        if line.startswith("##fileformat="):
            return line.split("=", 1)[1].strip()
    return None


def _detect_genome_build_from_content(lines: list[str]) -> Optional[str]:
    """Detect genome build from VCF content."""
    has_chr_prefix = False
    no_chr_prefix = False

    for line in lines:
        line = line.strip()
        if line.startswith("#"):
            continue
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 5:
            continue
        chrom = parts[0]
        if chrom.startswith("chr"):
            has_chr_prefix = True
        elif chrom in _VALID_CHROMOSOMES_GRCH37:
            no_chr_prefix = True

    if has_chr_prefix and not no_chr_prefix:
        return "GRCh38"
    elif no_chr_prefix and not has_chr_prefix:
        return "GRCh37"
    return None


def validate_vcf(content: str, expected_build: Optional[str] = None) -> VCFValidationResult:
    """Validate VCF content string.

    Args:
        content: Raw VCF file content as string
        expected_build: Expected genome build, if known

    Returns:
        VCFValidationResult with errors/warnings
    """
    result = VCFValidationResult()
    lines = content.split("\n")

    # Check file exists
    if not content.strip():
        result.add_error("EMPTY_FILE", "VCF file is empty")
        return result

    # Detect format
    result.file_format = _detect_fileformat(lines)
    if result.file_format is None:
        result.add_error("NO_FILEFORMAT", "Missing ##fileformat header")
    elif result.file_format not in ("VCFv4.1", "VCFv4.2", "VCFv4.3"):
        result.add_warning("UNKNOWN_FORMAT", f"Unknown VCF format: {result.file_format}")

    # Find column header
    col_header_idx = None
    for i, line in enumerate(lines):
        line = line.strip()
        if line.startswith("#CHROM"):
            col_header_idx = i
            parts = line.split("\t")
            # Validate required columns
            required = ["#CHROM", "POS", "ID", "REF", "ALT", "QUAL", "FILTER", "INFO"]
            for j, req in enumerate(required):
                if j >= len(parts) or parts[j] != req:
                    result.add_error("MISSING_COLUMN", f"Missing required column '{req}' in header", line=i + 1)
            result.sample_count = max(0, len(parts) - 9)
            break

    if col_header_idx is None:
        result.add_error("NO_HEADER", "Missing #CHROM header line")
        return result

    # Detect genome build
    detected_build = _detect_genome_build_from_content(lines)
    if expected_build and detected_build and detected_build != expected_build:
        result.add_warning("BUILD_MISMATCH", f"Detected build {detected_build} differs from expected {expected_build}")
    result.genome_build = detected_build or expected_build
    if not result.genome_build:
        result.add_warning("NO_BUILD", "Could not determine genome build")

    # Validate data lines
    data_start = col_header_idx + 1
    for i in range(data_start, len(lines)):
        line = lines[i].strip()
        if not line:
            continue
        line_num = i + 1

        parts = line.split("\t")
        if len(parts) < 8:
            result.add_error("TOO_FEW_FIELDS", f"Expected 8+ fields, got {len(parts)}", line=line_num)
            continue

        # CHROM
        chrom = parts[0]
        if not _CHROM_RE.match(chrom):
            result.add_error("INVALID_CHROM", f"Invalid chromosome: {chrom}", line=line_num, field="CHROM")

        # POS
        pos_str = parts[1]
        if not _POSITION_RE.match(pos_str):
            result.add_error("INVALID_POS", f"Invalid position: {pos_str}", line=line_num, field="POS")
        else:
            pos = int(pos_str)
            if pos < 1:
                result.add_error("POS_ZERO", f"Position must be >= 1, got {pos}", line=line_num, field="POS")

        # REF
        ref = parts[3]
        if not _REF_ALT_RE.match(ref):
            result.add_error("INVALID_REF", f"Invalid REF allele: {ref}", line=line_num, field="REF")

        # ALT
        alt = parts[4]
        if alt == ".":
            # No alternate allele — this is a reference call
            pass
        elif not _REF_ALT_RE.match(alt):
            result.add_error("INVALID_ALT", f"Invalid ALT allele: {alt}", line=line_num, field="ALT")

        # QUAL
        qual = parts[5]
        if qual != ".":
            try:
                float(qual)
            except ValueError:
                result.add_error("INVALID_QUAL", f"Invalid QUAL value: {qual}", line=line_num, field="QUAL")

        result.record_count += 1

    if result.record_count == 0:
        result.add_warning("NO_VARIANTS", "VCF file contains no variant records")

    return result


def validate_vcf_file(filepath: str, expected_build: Optional[str] = None) -> VCFValidationResult:
    """Validate a VCF file from path."""
    import gzip
    if filepath.endswith(".gz"):
        import gzip
        with gzip.open(filepath, "rt") as f:
            content = f.read()
    else:
        with open(filepath, "r") as f:
            content = f.read()
    return validate_vcf(content, expected_build)
