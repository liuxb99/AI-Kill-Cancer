"""
VCF parsing module — extracts variants from VCF lines.

Supports VCF v4.x format. Uses standard library only.
VCF.GZ files must be decompressed before parsing.
"""

from __future__ import annotations

import re
import gzip
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class VCFRecord:
    """A single VCF record (data line)."""
    chromosome: str
    position: int
    id: str  # rs ID or "."
    reference: str
    alternate: str
    quality: Optional[float] = None
    filter_status: Optional[str] = None
    info: dict = field(default_factory=dict)
    format_fields: Optional[list[str]] = None
    sample_values: Optional[list[list[str]]] = None
    raw_line: Optional[str] = None


@dataclass
class VCFHeader:
    """VCF header metadata."""
    fileformat: str = "VCFv4.2"
    contigs: list[str] = field(default_factory=list)
    info_fields: dict = field(default_factory=dict)
    format_fields: dict = field(default_factory=dict)
    sample_ids: list[str] = field(default_factory=list)
    genome_build: Optional[str] = None  # Detected from reference or assembly
    reference: Optional[str] = None  # ##reference=


@dataclass
class VCFParseResult:
    """Result of parsing a VCF file."""
    header: Optional[VCFHeader] = None
    records: list[VCFRecord] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    record_count: int = 0


# ─── Parsing ──────────────────────────────────────────────────────────────────

_SECTION_RE = re.compile(r"##(\w+)=<?(.+?)>?")
_INFO_RE = re.compile(r"##INFO=<(.+?)>")
_FORMAT_RE = re.compile(r"##FORMAT=<(.+?)>")
_CONTIG_RE = re.compile(r"##contig=<(.+?)>")

# Reference genome mapping
_REFERENCE_BUILD_MAP = {
    "GRCh37": "GRCh37",
    "GRCh38": "GRCh38",
    "hg19": "GRCh37",
    "hg38": "GRCh38",
    "hs37d5": "GRCh37",
    "b37": "GRCh37",
}


def detect_genome_build(header: VCFHeader) -> Optional[str]:
    """Detect genome build from VCF header metadata."""
    # Check ##reference= for known patterns
    if header.reference:
        ref_lower = header.reference.lower()
        for key, build in _REFERENCE_BUILD_MAP.items():
            if key.lower() in ref_lower:
                return build

    # Check contig names for clues (GRCh38 has "chr" prefix often)
    if header.contigs:
        first = header.contigs[0]
        if first.startswith("chr"):
            return "GRCh38"
        else:
            return "GRCh37"

    return None


def _parse_info_field(info_str: str) -> dict:
    """Parse INFO field string into key=value pairs."""
    result = {}
    if not info_str or info_str == ".":
        return result
    for part in info_str.split(";"):
        if "=" in part:
            key, val = part.split("=", 1)
            result[key] = val
        else:
            result[part] = True
    return result


def _parse_header_line(line: str, header: VCFHeader) -> None:
    """Parse a single VCF header line (##)."""
    line = line.strip()
    if line.startswith("##fileformat="):
        header.fileformat = line.split("=", 1)[1].strip()
    elif line.startswith("##reference="):
        header.reference = line.split("=", 1)[1].strip().strip("<>")
    elif line.startswith("##INFO="):
        m = _INFO_RE.match(line)
        if m:
            raw = m.group(1)
            info = _parse_meta_entry(raw)
            if info and "ID" in info:
                header.info_fields[info["ID"]] = info
    elif line.startswith("##FORMAT="):
        m = _FORMAT_RE.match(line)
        if m:
            raw = m.group(1)
            fmt = _parse_meta_entry(raw)
            if fmt and "ID" in fmt:
                header.format_fields[fmt["ID"]] = fmt
    elif line.startswith("##contig="):
        m = _CONTIG_RE.match(line)
        if m:
            raw = m.group(1)
            contig = _parse_meta_entry(raw)
            if contig and "ID" in contig:
                header.contigs.append(contig["ID"])


def _parse_meta_entry(raw: str) -> dict:
    """Parse a structured meta entry like ID=foo,Type=String,..."""
    result = {}
    for part in raw.split(","):
        if "=" in part:
            key, val = part.split("=", 1)
            result[key.strip()] = val.strip()
    return result


def _parse_data_line(line: str, sample_ids: list[str]) -> Optional[VCFRecord]:
    """Parse a non-header VCF data line."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    parts = line.split("\t")
    if len(parts) < 8:
        return None

    try:
        chrom = parts[0]
        pos = int(parts[1])
        vid = parts[2]
        ref = parts[3]
        alt = parts[4]
        qual = float(parts[5]) if parts[5] != "." else None
        filt = parts[6] if parts[6] != "." else None

        info = _parse_info_field(parts[7])

        fmt_fields = None
        sample_vals = None
        if len(parts) > 8 and parts[8] != ".":
            fmt_fields = parts[8].split(":")
            sample_vals = []
            for sp in parts[9:]:
                sample_vals.append(sp.split(":") if sp != "." else [])

        return VCFRecord(
            chromosome=chrom,
            position=pos,
            id=vid,
            reference=ref,
            alternate=alt,
            quality=qual,
            filter_status=filt,
            info=info,
            format_fields=fmt_fields,
            sample_values=sample_vals,
            raw_line=line,
        )
    except (ValueError, IndexError):
        return None


def parse_vcf(content: str) -> VCFParseResult:
    """Parse VCF content string into structured result."""
    result = VCFParseResult()
    header = VCFHeader()
    lines = content.split("\n")

    in_header = True
    for line in lines:
        line = line.strip()
        if not line:
            continue

        if in_header:
            if line.startswith("##"):
                _parse_header_line(line, header)
            elif line.startswith("#CHROM"):
                # Column header line
                parts = line.split("\t")
                if len(parts) > 9:
                    header.sample_ids = parts[9:]
                in_header = False
            else:
                # Non-header before #CHROM — error
                result.errors.append(f"Unexpected non-header line: {line[:80]}")
                in_header = False
        else:
            record = _parse_data_line(line, header.sample_ids)
            if record:
                result.records.append(record)
                result.record_count += 1

    # Detect genome build
    header.genome_build = detect_genome_build(header)
    result.header = header

    return result


def parse_vcf_file(filepath: str) -> VCFParseResult:
    """Parse a VCF file from path (supports .vcf and .vcf.gz)."""
    content: str
    if filepath.endswith(".gz"):
        with gzip.open(filepath, "rt") as f:
            content = f.read()
    else:
        with open(filepath, "r") as f:
            content = f.read()
    return parse_vcf(content)
