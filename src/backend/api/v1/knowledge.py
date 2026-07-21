"""
Knowledge API — extended oncology knowledge layer endpoints.

Provides:
- GET  /api/v1/knowledge/variant/{id}
- GET  /api/v1/knowledge/gene/{symbol}
- GET  /api/v1/knowledge/drug/{id}
- GET  /api/v1/knowledge/disease/{id}
- GET  /api/v1/knowledge/publication/{pmid}
- GET  /api/v1/knowledge/trial/{nct_id}
- POST /api/v1/knowledge/refresh
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database.session import get_db
from src.backend.auth.dependencies import require_auth
from src.backend.domain.user import UserModel
from src.backend.knowledge.service import KnowledgeService
from src.backend.knowledge.models import (
    KnowledgeEntityResponse, KnowledgeEntity,
)
from src.backend.knowledge.adapters.pubmed import PubMedAdapter
from src.backend.knowledge.adapters.clinicaltrials import ClinicalTrialsAdapter
from src.backend.repositories.drug_repo import DrugRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/variant/{variant_id}", response_model=KnowledgeEntityResponse)
async def get_variant_knowledge(
    variant_id: str,
    user: UserModel = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Get all knowledge about a variant."""
    service = KnowledgeService(db)
    result = await service.get_variant_knowledge(variant_id)
    if not result.entity:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Variant not found in knowledge base"})
    return result


@router.get("/gene/{gene_symbol}", response_model=KnowledgeEntityResponse)
async def get_gene_knowledge(
    gene_symbol: str,
    user: UserModel = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Get all knowledge about a gene."""
    service = KnowledgeService(db)
    result = await service.get_gene_knowledge(gene_symbol.upper())
    if not result.entity:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Gene not found in knowledge base"})
    return result


@router.get("/drug/{drug_id}", response_model=KnowledgeEntityResponse)
async def get_drug_knowledge(
    drug_id: str,
    user: UserModel = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Get knowledge about a drug from the local knowledge base."""
    service = KnowledgeService(db)
    # First try structured knowledge repository
    result = await service.repo.find_entities(entity_type="drug", name=drug_id)
    if result:
        entity = result[0]
        return KnowledgeEntityResponse(
            entity=KnowledgeEntity(
                id=str(entity.id),
                entity_type="drug",
                source=entity.source,
                source_id=entity.source_id,
                name=entity.name,
                identifiers=entity.identifiers or {},
            ),
        )

    # Fall back to drug repository
    drug_repo = DrugRepository(db)
    try:
        import uuid
        drug_id_uuid = uuid.UUID(drug_id)
        drug = await drug_repo.get(drug_id_uuid)
        if drug:
            return KnowledgeEntityResponse(
                entity=KnowledgeEntity(
                    id=str(drug.id),
                    entity_type="drug",
                    source="local_db",
                    source_id=drug_id,
                    name=drug.name,
                    identifiers={"drugbank_id": drug.drugbank_id} if hasattr(drug, 'drugbank_id') and drug.drugbank_id else {},
                ),
            )
    except (ValueError, Exception):
        pass

    raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Drug not found in knowledge base"})


@router.get("/disease/{disease_id}", response_model=KnowledgeEntityResponse)
async def get_disease_knowledge(
    disease_id: str,
    user: UserModel = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Get knowledge about a disease from the knowledge base."""
    service = KnowledgeService(db)
    result = await service.repo.find_entities(entity_type="disease", name=disease_id)
    if result:
        entity = result[0]
        return KnowledgeEntityResponse(
            entity=KnowledgeEntity(
                id=str(entity.id),
                entity_type="disease",
                source=entity.source,
                source_id=entity.source_id,
                name=entity.name,
                identifiers=entity.identifiers or {},
            ),
        )

    # Try to find by cancer type name
    from src.backend.domain.enums import CancerTypeEnum
    for ct in CancerTypeEnum:
        if disease_id.upper() in (ct.value.upper(), ct.name.upper()):
            return KnowledgeEntityResponse(
                entity=KnowledgeEntity(
                    id=disease_id,
                    entity_type="disease",
                    source="internal",
                    source_id=ct.value,
                    name=ct.value,
                    identifiers={"oncotree_code": ct.value},
                ),
            )

    raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Disease not found in knowledge base"})


@router.get("/publication/{pmid}", response_model=KnowledgeEntityResponse)
async def get_publication(
    pmid: str,
    user: UserModel = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Get publication details from PubMed (public API, no key required)."""
    adapter = PubMedAdapter()
    try:
        results = await adapter.search(f"pmid:{pmid}", max_results=1)
    except Exception as e:
        logger.warning("PubMed lookup failed for %s: %s", pmid, e)
        raise HTTPException(status_code=502, detail={"error": "upstream_error", "message": "Failed to fetch from PubMed"})

    if not results:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Publication not found"})

    pub = results[0]
    return KnowledgeEntityResponse(
        entity=KnowledgeEntity(
            id=pmid,
            entity_type="publication",
            source="pubmed",
            source_id=pmid,
            name=pub.get("title", ""),
            identifiers={"pmid": pmid, "doi": pub.get("doi", "")},
        ),
        relations=[],
    )


@router.get("/trial/{nct_id}", response_model=KnowledgeEntityResponse)
async def get_trial(
    nct_id: str,
    user: UserModel = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Get clinical trial details from ClinicalTrials.gov (public API, no key required)."""
    adapter = ClinicalTrialsAdapter()
    # Normalize NCT ID format
    nct_upper = nct_id.upper().strip()
    if not nct_upper.startswith("NCT"):
        nct_upper = f"NCT{nct_upper}"
    try:
        results = await adapter.search(nct_upper, max_results=1)
    except Exception as e:
        logger.warning("ClinicalTrials.gov lookup failed for %s: %s", nct_id, e)
        raise HTTPException(status_code=502, detail={"error": "upstream_error", "message": "Failed to fetch from ClinicalTrials.gov"})

    if not results:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Clinical trial not found"})

    trial = results[0]
    return KnowledgeEntityResponse(
        entity=KnowledgeEntity(
            id=nct_upper,
            entity_type="clinical_trial",
            source="clinicaltrials.gov",
            source_id=nct_upper,
            name=trial.get("brief_title", trial.get("official_title", "")),
            identifiers={"nct_id": nct_upper},
        ),
        relations=[],
    )


@router.post("/refresh")
async def refresh_knowledge(
    user: UserModel = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Refresh knowledge base from configured public sources."""
    from src.backend.knowledge.adapters import ClinVarAdapter, PubMedAdapter, ClinicalTrialsAdapter

    configured = []
    not_configured = ["COSMIC", "CancerHotspots", "PharmGKB", "OncoKB", "MyCancerGenome"]

    clinvar = ClinVarAdapter()
    pubmed = PubMedAdapter()
    ct_gov = ClinicalTrialsAdapter()

    clinvar_health = await clinvar.health_check()
    pubmed_health = await pubmed.health_check()
    ct_health = await ct_gov.health_check()

    if clinvar_health.get("status") == "ok":
        configured.append("ClinVar")
    else:
        not_configured.append("ClinVar")

    if pubmed_health.get("status") == "ok":
        configured.append("PubMed")
    else:
        not_configured.append("PubMed")

    if ct_health.get("status") == "ok":
        configured.append("ClinicalTrials.gov")
    else:
        not_configured.append("ClinicalTrials.gov")

    return {
        "status": "completed" if configured else "not_configured",
        "message": f"Knowledge sources checked. {len(configured)} configured.",
        "configured_sources": configured,
        "not_configured_sources": not_configured,
        "refreshed_at": datetime.now(timezone.utc).isoformat(),
    }
