"""PTC multi-scale 3D visualization data API.

The cell view is a scientific illustration assembled from persisted case data.
Protein coordinates are loaded from deterministic public structure files and
rendered by the project's built-in Three.js viewer. No AlphaFold metadata API
or remote viewer runtime is required.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.backend.database.session import get_db
from src.backend.domain.ptc_research import PTCResearchCaseModel

router = APIRouter(prefix="/ptc-visualization", tags=["ptc-visualization"])

# Curated human UniProt accessions and representative experimental PDB entries.
# Structure URLs are generated locally from these identifiers. The backend never
# calls the AlphaFold API.
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


def _alphafold_pdb_url(uniprot: str) -> str:
    return f"https://alphafold.ebi.ac.uk/files/AF-{uniprot}-F1-model_v4.pdb"


def _alphafold_cif_url(uniprot: str) -> str:
    return f"https://alphafold.ebi.ac.uk/files/AF-{uniprot}-F1-model_v4.cif"


def _experimental_structure(pdb_id: str) -> dict[str, str]:
    normalized = pdb_id.upper()
    return {
        "pdb_id": normalized,
        "pdb_url": f"https://files.rcsb.org/download/{normalized}.pdb",
        "entry_url": f"https://www.ebi.ac.uk/pdbe/entry/pdb/{normalized.lower()}",
    }


@router.get("/proteins/{gene}")
async def protein_structure(gene: str) -> dict[str, Any]:
    symbol = gene.strip().upper()
    entry = PROTEIN_CATALOG.get(symbol)
    if entry is None:
        raise HTTPException(status_code=404, detail="No curated PTC protein structure mapping for this gene")

    uniprot = entry["uniprot"]
    structures = [_experimental_structure(pdb_id) for pdb_id in entry["pdb_ids"]]
    return {
        "gene": symbol,
        "name": entry["name"],
        "uniprot": uniprot,
        "alphafold_entry_id": f"AF-{uniprot}-F1",
        "alphafold_entry_url": f"https://alphafold.ebi.ac.uk/entry/{uniprot}",
        "pdb_url": _alphafold_pdb_url(uniprot),
        "cif_url": _alphafold_cif_url(uniprot),
        "experimental_structures": structures,
        "experimental_pdb_ids": entry["pdb_ids"],
        "default_pdb_id": entry["pdb_ids"][0] if entry["pdb_ids"] else None,
        "renderer": "builtin-threejs-pdb",
        "uses_alphafold_api": False,
        "source": "Static AlphaFold DB and RCSB PDB coordinate files rendered by built-in project code",
        "disclaimer": "Predicted and experimental reference structures are not patient-specific molecular reconstructions.",
    }


@router.get("/proteins")
async def protein_catalog() -> dict[str, Any]:
    return {
        "count": len(PROTEIN_CATALOG),
        "proteins": [{"gene": gene, **entry} for gene, entry in sorted(PROTEIN_CATALOG.items())],
    }


__all__ = ["router", "PROTEIN_CATALOG"]
