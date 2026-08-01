"""PTC multi-scale 3D visualization data API.

The cell view is a scientific illustration assembled from persisted case data.
Protein structures are loaded from public AlphaFold DB predictions or selected
experimental PDB entries. Neither representation is a patient-specific atomic
reconstruction of a cancer cell.
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.backend.database.session import get_db
from src.backend.domain.ptc_research import PTCResearchCaseModel

router = APIRouter(prefix="/ptc-visualization", tags=["ptc-visualization"])

PROTEIN_CATALOG: dict[str, dict[str, Any]] = {
    "BRAF": {"uniprot": "P15056", "pdb_ids": ["1UWH", "4MNE"], "name": "B-Raf proto-oncogene kinase"},
    "RET": {"uniprot": "P07949", "pdb_ids": ["2IVU", "6NEC"], "name": "Proto-oncogene tyrosine-protein kinase receptor Ret"},
    "NTRK1": {"uniprot": "P04629", "pdb_ids": ["4AOJ"], "name": "High affinity nerve growth factor receptor"},
    "NTRK2": {"uniprot": "Q16620", "pdb_ids": ["4AT3"], "name": "BDNF/NT-3 growth factors receptor"},
    "NTRK3": {"uniprot": "Q16288", "pdb_ids": ["6KZC"], "name": "NT-3 growth factor receptor"},
    "TERT": {"uniprot": "O14746", "pdb_ids": ["7BG9"], "name": "Telomerase reverse transcriptase"},
    "NRAS": {"uniprot": "P01111", "pdb_ids": ["5UHV"], "name": "GTPase NRas"},
    "HRAS": {"uniprot": "P01112", "pdb_ids": ["5P21"], "name": "GTPase HRas"},
    "KRAS": {"uniprot": "P01116", "pdb_ids": ["6GJ8", "7RPZ"], "name": "GTPase KRas"},
    "TP53": {"uniprot": "P04637", "pdb_ids": ["2OCJ", "8DC4"], "name": "Cellular tumor antigen p53"},
    "AKT1": {"uniprot": "P31749", "pdb_ids": ["4EJN"], "name": "RAC-alpha serine/threonine-protein kinase"},
    "PIK3CA": {"uniprot": "P42336", "pdb_ids": ["4OVU", "7K6M"], "name": "PI3-kinase catalytic subunit alpha"},
    "EGFR": {"uniprot": "P00533", "pdb_ids": ["1M17", "5UG9"], "name": "Epidermal growth factor receptor"},
}

_ALPHAFOLD_CACHE: dict[str, tuple[float, dict[str, Any] | None]] = {}
_ALPHAFOLD_SUCCESS_TTL_SECONDS = 6 * 60 * 60
_ALPHAFOLD_FAILURE_TTL_SECONDS = 5 * 60


def _case_payload(model: PTCResearchCaseModel) -> dict[str, Any]:
    return {
        "case_id": model.case_id,
        "source_dataset": model.source_dataset,
        "source_project": model.source_project,
        "disease": model.disease,
        "sex": model.sex,
        "age_range": model.age_range,
        "pathologic_stage": model.pathologic_stage,
        "t_status": model.t_status,
        "n_status": model.n_status,
        "m_status": model.m_status,
        "vital_status": model.vital_status,
        "days_to_last_follow_up": model.days_to_last_follow_up,
        "days_to_death": model.days_to_death,
        "created_at": model.created_at.isoformat() if model.created_at else None,
        "updated_at": model.updated_at.isoformat() if model.updated_at else None,
        "variants": [
            {
                "variant_id": item.variant_id,
                "gene": item.gene,
                "chromosome": item.chromosome,
                "position": item.position,
                "reference": item.reference,
                "alternate": item.alternate,
                "variant_type": item.variant_type,
                "classification": item.classification,
                "protein_change": item.protein_change,
                "source_record_id": item.source_record_id,
            }
            for item in model.variants
        ],
        "outcomes": [
            {
                "outcome_id": item.outcome_id,
                "outcome_type": item.outcome_type,
                "outcome_value": item.outcome_value,
                "observed_at": item.observed_at.isoformat() if item.observed_at else None,
                "source_record_id": item.source_record_id,
            }
            for item in model.outcomes
        ],
    }


@router.get("/cases/latest")
async def latest_cases(
    limit: int = Query(default=100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await db.execute(
        select(PTCResearchCaseModel)
        .options(selectinload(PTCResearchCaseModel.variants), selectinload(PTCResearchCaseModel.outcomes))
        .order_by(PTCResearchCaseModel.updated_at.desc(), PTCResearchCaseModel.case_id.desc())
        .limit(limit)
    )
    rows = list(result.scalars().unique())
    return {"count": len(rows), "limit": limit, "cases": [_case_payload(row) for row in rows]}


def _fetch_alphafold_metadata(uniprot: str) -> dict[str, Any] | None:
    now = time.monotonic()
    cached = _ALPHAFOLD_CACHE.get(uniprot)
    if cached:
        cached_at, cached_value = cached
        ttl = _ALPHAFOLD_SUCCESS_TTL_SECONDS if cached_value is not None else _ALPHAFOLD_FAILURE_TTL_SECONDS
        if now - cached_at < ttl:
            return cached_value

    request = Request(
        f"https://alphafold.ebi.ac.uk/api/prediction/{uniprot}",
        headers={"Accept": "application/json", "User-Agent": "AI-Kill-Cancer/PTC-3D"},
    )
    value: dict[str, Any] | None = None
    try:
        with urlopen(request, timeout=8) as response:  # nosec B310 - fixed official HTTPS endpoint
            payload = json.loads(response.read().decode("utf-8"))
        if isinstance(payload, list) and payload and isinstance(payload[0], dict):
            value = payload[0]
        elif isinstance(payload, dict):
            value = payload
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        value = None

    _ALPHAFOLD_CACHE[uniprot] = (now, value)
    return value


@router.get("/proteins/{gene}")
async def protein_structure(gene: str) -> dict[str, Any]:
    symbol = gene.strip().upper()
    entry = PROTEIN_CATALOG.get(symbol)
    if entry is None:
        raise HTTPException(status_code=404, detail="No curated PTC protein structure mapping for this gene")

    metadata = await asyncio.to_thread(_fetch_alphafold_metadata, entry["uniprot"])
    cif_url = None
    pdb_url = None
    confidence_url = None
    entry_id = None
    if metadata:
        cif_url = metadata.get("cifUrl") or metadata.get("cif_url") or metadata.get("bcifUrl")
        pdb_url = metadata.get("pdbUrl") or metadata.get("pdb_url")
        confidence_url = metadata.get("paeDocUrl") or metadata.get("pae_doc_url")
        entry_id = metadata.get("entryId") or metadata.get("entry_id")

    if not cif_url:
        cif_url = f"https://alphafold.ebi.ac.uk/files/AF-{entry['uniprot']}-F1-model_v4.cif"

    return {
        "gene": symbol,
        "name": entry["name"],
        "uniprot": entry["uniprot"],
        "alphafold_entry_id": entry_id or f"AF-{entry['uniprot']}-F1",
        "alphafold_entry_url": f"https://alphafold.ebi.ac.uk/entry/{entry['uniprot']}",
        "cif_url": cif_url,
        "pdb_url": pdb_url,
        "confidence_url": confidence_url,
        "experimental_pdb_ids": entry["pdb_ids"],
        "default_pdb_id": entry["pdb_ids"][0] if entry["pdb_ids"] else None,
        "source": "AlphaFold DB prediction with representative experimental PDB structures",
        "disclaimer": "Predicted and experimental reference structures are not patient-specific molecular reconstructions.",
    }


@router.get("/proteins")
async def protein_catalog() -> dict[str, Any]:
    return {
        "count": len(PROTEIN_CATALOG),
        "proteins": [{"gene": gene, **entry} for gene, entry in sorted(PROTEIN_CATALOG.items())],
    }


__all__ = ["router", "PROTEIN_CATALOG"]
