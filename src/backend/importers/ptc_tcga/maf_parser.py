"""Parser for GDC public Masked Somatic Mutation MAF files."""

from __future__ import annotations

import csv
import gzip
import io
from collections import defaultdict
from typing import Iterable, TextIO


def tcga_case_id(sample_barcode: str) -> str:
    """Return the TCGA participant barcode from a sample barcode."""
    parts = sample_barcode.strip().split("-")
    if len(parts) < 3:
        raise ValueError(f"invalid TCGA sample barcode: {sample_barcode!r}")
    return "-".join(parts[:3])


def parse_maf_text(stream: TextIO) -> dict[str, list[dict]]:
    """Parse a MAF stream and group normalized variants by TCGA case ID."""
    data_lines = (line for line in stream if line.strip() and not line.startswith("#"))
    reader = csv.DictReader(data_lines, delimiter="\t")
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in reader:
        sample = row.get("Tumor_Sample_Barcode") or row.get("Matched_Norm_Sample_Barcode")
        gene = row.get("Hugo_Symbol")
        if not sample or not gene or gene in {"Unknown", ""}:
            continue
        case_id = tcga_case_id(sample)
        grouped[case_id].append(
            {
                "gene": gene,
                "chromosome": row.get("Chromosome"),
                "position": row.get("Start_Position"),
                "reference": row.get("Reference_Allele"),
                "alternate": row.get("Tumor_Seq_Allele2"),
                "variant_type": row.get("Variant_Type"),
                "classification": row.get("Variant_Classification"),
                "protein_change": row.get("HGVSp_Short") or row.get("HGVSp"),
                "source_record_id": row.get("dbSNP_RS") or row.get("Tumor_Sample_Barcode"),
            }
        )
    return dict(grouped)


def parse_maf_bytes(data: bytes, *, compressed: bool | None = None) -> dict[str, list[dict]]:
    if compressed is None:
        compressed = data[:2] == b"\x1f\x8b"
    payload = gzip.decompress(data) if compressed else data
    return parse_maf_text(io.StringIO(payload.decode("utf-8", errors="replace")))


def merge_variants_into_cases(cases: Iterable[dict], variants_by_case: dict[str, list[dict]]) -> list[dict]:
    merged: list[dict] = []
    for case in cases:
        item = dict(case)
        case_id = str(item.get("case_id") or item.get("submitter_id") or "")
        item["variants"] = list(variants_by_case.get(case_id, []))
        merged.append(item)
    return merged


__all__ = ["parse_maf_text", "parse_maf_bytes", "merge_variants_into_cases", "tcga_case_id"]
