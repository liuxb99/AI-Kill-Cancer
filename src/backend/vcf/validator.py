"""
VCF validation module — checks VCF file integrity and format compliance.

Supports VCF v4.1, v4.2, v4.3.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class VCFValidationError:
    """A single validation error with code and context."""
    code: str
    message: str
    line: int | None = None
    field: str | None = None


@dataclass
class VCFValidationResult:
    """Result of VCF validation."""
    valid: bool = True
    errors: list[VCFValidationError] = field(default_factory=list)
    warnings: list[VCFValidationError] = field(default_factory=list)
    file_format: str | None = None
    genome_build: str | None = None
    sample_count: int = 0
    record_count: int = 0

    def add_error(self, code: str, message: str, line: int | None = None, field: str | None = None):
        self.valid = False
        self.errors.append(VCFValidationError(code=code, message=message, line=line, field=field))

    def add_warning(self, code: str, message: str, line: int | None = None, field: str | None = None):
        self.warnings.append(VCFValidationError(code=code, message=message, line=line, field=field))


# Chromosome validation
_VALID_CHROMOSOMES_GRCH37 = {str(i) for i in range(1, 23)} | {"X", "Y", "MT"}
_VALID_CHROMOSOMES_GRCH38 = {str(i) for i in range(1, 23)} | {"X", "Y", "MT"}

# Basic VCF regex patterns
_CHROM_RE = re.compile(r"^(\d+|X|Y|MT|chr\d+|chrX|chrY|chrMT)$")
_POSITION_RE = re.compile(r"^\d+$")
_REF_ALT_RE = re.compile(r"^[ACGTNacgtn.]+$")


def _detect_fileformat(lines: list[str]) -> str | None:
    """Detect VCF format version from fileformat header."""
    for line in lines:
        line = line.strip()
        if line.startswith("##fileformat="):
            return line.split("=", 1)[1].strip()
    return None


def _detect_genome_build_from_content(lines: list[str]) -> str | None:
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


def validate_vcf_streaming(
    filepath: str,
    expected_build: str | None = None,
    max_line_length: int = 100000,
    max_record_count: int = 10_000_000,
) -> VCFValidationResult:
    """Validate a VCF file by streaming line-by-line (no full file load).

    Handles .vcf and .vcf.gz transparently.
    Detects truncated gzip, CRC failure, invalid UTF-8, concatenated members.
    Accumulates header text for genome build detection.

    Args:
        filepath: Path to .vcf or .vcf.gz file
        expected_build: Expected genome build, if known
        max_line_length: Maximum allowed line length
        max_record_count: Maximum allowed record count

    Returns:
        VCFValidationResult with errors/warnings
    """
    result = VCFValidationResult()
    is_gz = filepath.endswith(".gz")

    # Accumulated header text for build detection
    header_lines: list[str] = []
    found_chrom_header = False
    col_header_parts: list[str] = []

    try:
        if is_gz:
            import gzip
            f = gzip.open(filepath, "rt", encoding="utf-8", errors="strict")
        else:
            f = open(filepath, encoding="utf-8", errors="strict")
    except FileNotFoundError:
        result.add_error("FILE_NOT_FOUND", f"File not found: {filepath}")
        return result
    except UnicodeDecodeError:
        result.add_error("INVALID_UTF8", "File contains invalid UTF-8 encoding")
        return result
    except gzip.BadGzipFile:
        result.add_error("CORRUPTED_GZIP", "File is corrupted or not a valid gzip")
        return result
    except Exception as e:
        result.add_error("OPEN_FAILED", f"Cannot open file: {e}")
        return result

    with f:
        line_num = 0
        in_header = True

        for raw_line in f:
            line_num += 1

            # Check line length
            if len(raw_line) > max_line_length:
                result.add_error("LINE_TOO_LONG", f"Line {line_num} exceeds maximum length ({len(raw_line)} > {max_line_length})", line=line_num)

            line = raw_line.strip()

            if not line:
                continue

            # ── Header lines ─────────────────────────────────────────
            if in_header:
                if line.startswith("##"):
                    header_lines.append(line)
                    if line.startswith("##fileformat="):
                        result.file_format = line.split("=", 1)[1].strip()
                        if result.file_format not in ("VCFv4.1", "VCFv4.2", "VCFv4.3"):
                            result.add_warning("UNKNOWN_FORMAT", f"Unknown VCF format: {result.file_format}")
                    continue

                if line.startswith("#CHROM"):
                    found_chrom_header = True
                    col_header_parts = line.split("\t")
                    # Validate required columns
                    required = ["#CHROM", "POS", "ID", "REF", "ALT", "QUAL", "FILTER", "INFO"]
                    for j, req in enumerate(required):
                        if j >= len(col_header_parts) or col_header_parts[j] != req:
                            result.add_error("MISSING_COLUMN", f"Missing required column '{req}' in header", line=line_num)
                    result.sample_count = max(0, len(col_header_parts) - 9)
                    in_header = False
                    continue

                # Non-header line before #CHROM in data section
                result.add_error("HEADER_MISSING_CHROM", f"Unexpected non-header line before #CHROM at line {line_num}", line=line_num)
                in_header = False
                continue

            # ── Data lines ───────────────────────────────────────────
            parts = line.split("\t")

            # Check record count limit
            if result.record_count >= max_record_count:
                result.add_error("RECORD_LIMIT_EXCEEDED", f"Record count exceeds maximum ({max_record_count})", line=line_num)
                # Stop processing to avoid DoS
                break

            # Field count
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
            if alt != "." and not _REF_ALT_RE.match(alt):
                result.add_error("INVALID_ALT", f"Invalid ALT allele: {alt}", line=line_num, field="ALT")

            # QUAL
            qual = parts[5]
            if qual != ".":
                try:
                    float(qual)
                except ValueError:
                    result.add_error("INVALID_QUAL", f"Invalid QUAL value: {qual}", line=line_num, field="QUAL")

            result.record_count += 1

    # ── Post-processing ────────────────────────────────────────────────
    if result.file_format is None and not found_chrom_header and result.record_count == 0:
        result.add_error("EMPTY_FILE", "VCF file is empty or has no valid content")

    if not found_chrom_header:
        result.add_error("NO_HEADER", "Missing #CHROM header line")

    # Detect genome build from accumulated header
    if header_lines:
        result.file_format = result.file_format or _detect_fileformat(header_lines)
        if not result.file_format:
            result.add_error("NO_FILEFORMAT", "Missing ##fileformat header")

    # Genome build detection from content sample (first N data lines)
    # Detect genome build from header
    detected_build: str | None = None
    for h in header_lines:
        if h.startswith("##reference="):
            ref = h.split("=", 1)[1].strip().strip("<>").lower()
            if "grch38" in ref or "hg38" in ref:
                detected_build = "GRCh38"
            elif "grch37" in ref or "hg19" in ref:
                detected_build = "GRCh37"
            break

    if expected_build and detected_build and detected_build != expected_build:
        result.add_warning("BUILD_MISMATCH", f"Detected build {detected_build} differs from expected {expected_build}")
    result.genome_build = detected_build or expected_build
    if not result.genome_build:
        result.add_warning("NO_BUILD", "Could not determine genome build")

    if result.record_count == 0 and found_chrom_header:
        result.add_warning("NO_VARIANTS", "VCF file contains no variant records")

    return result


# ─── Legacy string-based validator (kept for test compatibility) ──────────────


def validate_vcf(content: str, expected_build: str | None = None) -> VCFValidationResult:
    """Validate VCF content string. Loads entire file — use validate_vcf_streaming for prod."""
    result = VCFValidationResult()
    lines = content.split("\n")
    if not content.strip():
        result.add_error("EMPTY_FILE", "VCF file is empty")
        return result
    result.file_format = _detect_fileformat(lines)
    if result.file_format is None:
        result.add_error("NO_FILEFORMAT", "Missing ##fileformat header")
    elif result.file_format not in ("VCFv4.1", "VCFv4.2", "VCFv4.3"):
        result.add_warning("UNKNOWN_FORMAT", f"Unknown VCF format: {result.file_format}")
    col_header_idx = None
    for i, line in enumerate(lines):
        line = line.strip()
        if line.startswith("#CHROM"):
            col_header_idx = i
            parts = line.split("\t")
            required = ["#CHROM", "POS", "ID", "REF", "ALT", "QUAL", "FILTER", "INFO"]
            for j, req in enumerate(required):
                if j >= len(parts) or parts[j] != req:
                    result.add_error("MISSING_COLUMN", f"Missing required column '{req}' in header", line=i + 1)
            result.sample_count = max(0, len(parts) - 9)
            break
    if col_header_idx is None:
        result.add_error("NO_HEADER", "Missing #CHROM header line")
        return result
    detected_build = _detect_genome_build_from_content(lines)
    if expected_build and detected_build and detected_build != expected_build:
        result.add_warning("BUILD_MISMATCH", f"Detected build {detected_build} differs from expected {expected_build}")
    result.genome_build = detected_build or expected_build
    if not result.genome_build:
        result.add_warning("NO_BUILD", "Could not determine genome build")
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
        chrom = parts[0]
        if not _CHROM_RE.match(chrom):
            result.add_error("INVALID_CHROM", f"Invalid chromosome: {chrom}", line=line_num, field="CHROM")
        pos_str = parts[1]
        if not _POSITION_RE.match(pos_str):
            result.add_error("INVALID_POS", f"Invalid position: {pos_str}", line=line_num, field="POS")
        else:
            pos = int(pos_str)
            if pos < 1:
                result.add_error("POS_ZERO", f"Position must be >= 1, got {pos}", line=line_num, field="POS")
        ref = parts[3]
        if not _REF_ALT_RE.match(ref):
            result.add_error("INVALID_REF", f"Invalid REF allele: {ref}", line=line_num, field="REF")
        alt = parts[4]
        if alt != "." and not _REF_ALT_RE.match(alt):
            result.add_error("INVALID_ALT", f"Invalid ALT allele: {alt}", line=line_num, field="ALT")
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
