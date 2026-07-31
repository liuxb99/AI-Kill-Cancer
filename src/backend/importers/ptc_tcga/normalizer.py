"""Normalize compact GDC/TCGA records into the PTC canonical contract."""

from __future__ import annotations

import hashlib
from typing import Any, Mapping

from src.backend.domain.ptc_research import (
    PTCOutcomeInput,
    PTCResearchCaseInput,
    PTCVariantInput,
)


def _text(value: Any) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    if not value or value.lower() in {"not reported", "unknown", "--", "nan"}:
        return None
    return value


def _integer(value: Any) -> int | None:
    text = _text(value)
    if text is None:
        return None
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return None


def _age_range(days_to_birth: Any) -> str | None:
    days = _integer(days_to_birth)
    if days is None:
        return None
    age = abs(days) // 365
    lower = (age // 10) * 10
    return f"{lower}-{lower + 9}"


def deterministic_variant_id(
    source_dataset: str,
    case_id: str,
    gene: str,
    chromosome: str | None,
    position: int | None,
    reference: str | None,
    alternate: str | None,
    protein_change: str | None,
) -> str:
    raw = "|".join(
        str(value or "")
        for value in (
            source_dataset,
            case_id,
            gene.upper(),
            chromosome,
            position,
            reference,
            alternate,
            protein_change,
        )
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:48]


def normalize_case_record(record: Mapping[str, Any]) -> PTCResearchCaseInput:
    """Normalize one flattened case record.

    The function deliberately accepts a small superset of common GDC field
    names so the first end-to-end slice can consume either downloaded JSON or a
    compact fixture without source-specific branching elsewhere.
    """

    case_id = _text(record.get("case_id") or record.get("submitter_id") or record.get("case_submitter_id"))
    if case_id is None:
        raise ValueError("PTC record is missing case_id/submitter_id")

    source_dataset = _text(record.get("source_dataset")) or "TCGA-THCA"
    source_project = _text(record.get("source_project") or record.get("project_id")) or "TCGA-THCA"

    raw_variants = record.get("variants") or []
    variants: list[PTCVariantInput] = []
    for raw in raw_variants:
        gene = _text(raw.get("gene") or raw.get("hugo_symbol"))
        if gene is None:
            continue
        chromosome = _text(raw.get("chromosome") or raw.get("chrom"))
        position = _integer(raw.get("position") or raw.get("start_position"))
        reference = _text(raw.get("reference") or raw.get("reference_allele"))
        alternate = _text(raw.get("alternate") or raw.get("tumor_seq_allele2"))
        protein_change = _text(raw.get("protein_change") or raw.get("hgvsp_short"))
        variant_id = _text(raw.get("variant_id")) or deterministic_variant_id(
            source_dataset,
            case_id,
            gene,
            chromosome,
            position,
            reference,
            alternate,
            protein_change,
        )
        variants.append(
            PTCVariantInput(
                variant_id=variant_id,
                gene=gene.upper(),
                chromosome=chromosome,
                position=position,
                reference=reference,
                alternate=alternate,
                variant_type=_text(raw.get("variant_type")),
                classification=_text(raw.get("classification") or raw.get("variant_classification")),
                protein_change=protein_change,
                source_record_id=_text(raw.get("source_record_id")),
            )
        )

    outcomes: list[PTCOutcomeInput] = []
    vital_status = _text(record.get("vital_status"))
    if vital_status is not None:
        outcomes.append(
            PTCOutcomeInput(
                outcome_id=f"{case_id}:vital_status",
                outcome_type="vital_status",
                outcome_value=vital_status.lower(),
                source_record_id=_text(record.get("source_record_id")),
            )
        )

    return PTCResearchCaseInput(
        case_id=case_id,
        source_dataset=source_dataset,
        source_project=source_project,
        sex=_text(record.get("sex") or record.get("gender")),
        age_range=_text(record.get("age_range")) or _age_range(record.get("days_to_birth")),
        pathologic_stage=_text(record.get("pathologic_stage") or record.get("ajcc_pathologic_stage")),
        t_status=_text(record.get("t_status") or record.get("ajcc_pathologic_t")),
        n_status=_text(record.get("n_status") or record.get("ajcc_pathologic_n")),
        m_status=_text(record.get("m_status") or record.get("ajcc_pathologic_m")),
        vital_status=vital_status,
        days_to_last_follow_up=_integer(record.get("days_to_last_follow_up")),
        days_to_death=_integer(record.get("days_to_death")),
        source_record_id=_text(record.get("source_record_id")),
        variants=variants,
        outcomes=outcomes,
    )


__all__ = ["normalize_case_record", "deterministic_variant_id"]
