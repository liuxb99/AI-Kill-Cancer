"""
Drug Ranking API — evidence-based drug ranking endpoints.

Provides:
- POST /api/v1/ranking/variant/{variant_id}
- POST /api/v1/ranking/case/{case_id}
- GET  /api/v1/ranking/run/{run_id}
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database.session import get_db
from src.backend.auth.dependencies import require_auth, require_case_access, verify_case_access
from src.backend.domain.case_acl import CaseRole
from src.backend.domain.user import UserModel
from src.backend.evidence.merger import EvidenceMerger
from src.backend.ranking.engine import DrugRankingEngine
from src.backend.ranking.models import (
    DrugRankingResult, DrugRankingRunResponse,
)
from src.backend.ranking.repository import RankingRunRepository
from src.backend.repositories.variant_repo import VariantRepository
from src.backend.api.v1.deps import get_variant_repo

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ranking", tags=["ranking"])


@router.post("/variant/{variant_id}", response_model=DrugRankingRunResponse)
async def rank_variant(
    variant_id: str,
    user: UserModel = Depends(require_auth),
    repo: VariantRepository = Depends(get_variant_repo),
    db: AsyncSession = Depends(get_db),
):
    """Rank drugs for a specific variant."""
    try:
        vid = uuid.UUID(variant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"error": "invalid_uuid", "message": "Invalid variant ID"})

    variant = await repo.get(vid)
    if not variant:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Variant not found"})

    # Check case-level access — resolve through sequencing_test → specimen → case
    if variant.sequencing_test_id:
        from src.backend.repositories.sequencing_test_repo import SequencingTestRepository
        from src.backend.repositories.specimen_repo import SpecimenRepository
        st_repo = SequencingTestRepository(db)
        st = await st_repo.get(variant.sequencing_test_id)
        if st and st.specimen_id:
            spec_repo = SpecimenRepository(db)
            spec = await spec_repo.get(st.specimen_id)
            if spec and spec.case_id:
                await verify_case_access(spec.case_id, user, db, CaseRole.EDITOR)

    # Gather evidence
    merger = EvidenceMerger(db=db)
    evidence_result = await merger.merge_variant_evidence(
        gene_symbol=variant.gene_symbol,
        hgvs=variant.hgvs_notation or "",
        chromosome=variant.chromosome,
        position=variant.position,
        reference=variant.reference,
        alternate=variant.alternate,
        request_id=f"rank-variant-{variant_id[:8]}",
    )

    evidence_items = evidence_result.get("evidence_items", [])
    drug_interactions = evidence_result.get("drug_interactions", [])
    match_level = evidence_result.get("match_level", "gene_level_only")

    if not evidence_items and not drug_interactions:
        return DrugRankingRunResponse(
            run_id="",
            status="no_evidence",
            message=f"No evidence found for variant {variant_id}",
        )

    # Run ranking
    engine = DrugRankingEngine()
    ranking_result = await engine.rank(
        gene_symbol=variant.gene_symbol,
        evidence_items=evidence_items,
        drug_interactions=drug_interactions,
        disease="",
        variant_match_level=match_level,
    )

    # Add variant_id to result
    ranking_result.variant_id = variant_id

    # Persist
    ranking_repo = RankingRunRepository(db)
    run_id = uuid.uuid4()
    ranking_result.id = str(run_id)
    try:
        await ranking_repo.create(ranking_result.model_dump())
    except Exception as e:
        logger.warning("Failed to persist ranking: %s", e)

    return DrugRankingRunResponse(
        run_id=str(run_id),
        status="completed",
        ranking=ranking_result,
    )


@router.post("/case/{case_id}", response_model=DrugRankingRunResponse)
async def rank_case(
    case_id: str,
    user: UserModel = Depends(require_case_access(CaseRole.EDITOR)),
    db: AsyncSession = Depends(get_db),
):
    """Rank drugs for a cancer case.

    Loads case variants → gathers evidence per variant → merges drug scores
    → preserves variant-specific evidence → persists ranking run.
    """
    import uuid
    from src.backend.repositories.cancer_case_repo import CancerCaseRepository
    from src.backend.repositories.variant_repo import VariantRepository
    from src.backend.evidence.merger import EvidenceMerger
    from src.backend.ranking.engine import DrugRankingEngine
    from src.backend.ranking.repository import RankingRunRepository

    try:
        cid = uuid.UUID(case_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"error": "invalid_uuid", "message": "Invalid case ID"})

    case_repo = CancerCaseRepository(db)
    variant_repo = VariantRepository(db)
    ranking_repo = RankingRunRepository(db)

    case = await case_repo.get(cid)
    if not case:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Case not found"})

    # Get case variants
    try:
        case_variants = await variant_repo.find_by_case(cid)
    except Exception:
        case_variants = await variant_repo.list(filters=[])

    if not case_variants:
        return DrugRankingRunResponse(
            run_id="",
            status="no_variants",
            message=f"No variants found for case {case_id}",
        )

    # Gather evidence for each variant and merge results
    merger = EvidenceMerger(db=db)
    engine = DrugRankingEngine()

    all_evidence_items = []
    all_drug_interactions = []
    variant_ids = []
    drug_scores: dict[str, dict] = {}  # drug_name -> accumulated data

    for variant in case_variants:
        v_id = str(variant.id) if hasattr(variant, "id") else ""
        variant_ids.append(v_id)

        ev_result = await merger.merge_variant_evidence(
            gene_symbol=variant.gene_symbol if hasattr(variant, "gene_symbol") else "",
            hgvs=getattr(variant, "hgvs_notation", "") or "",
            chromosome=getattr(variant, "chromosome", "") or "",
            position=getattr(variant, "position", 0) or 0,
            reference=getattr(variant, "reference", "") or "",
            alternate=getattr(variant, "alternate", "") or "",
            request_id=f"rank-case-{case_id[:8]}-var-{v_id[:8] if v_id else '?'}",
        )

        evidence_items = ev_result.get("evidence_items", [])
        drug_interactions = ev_result.get("drug_interactions", [])

        all_evidence_items.extend(evidence_items)
        all_drug_interactions.extend(drug_interactions)

        # Track per-variant scores for merge
        for item in evidence_items:
            drug_name = (item.get("drug_name", "") or "").strip()
            if not drug_name:
                continue

            if drug_name not in drug_scores:
                drug_scores[drug_name] = {
                    "variants": [],
                    "evidence_ids": [],
                    "match_levels": [],
                    "has_exact_match": False,
                    "resistance_count": 0,
                    "conflict_count": 0,
                }

            drug_scores[drug_name]["variants"].append(v_id)
            eid = str(item.get("id", ""))
            if eid and eid not in drug_scores[drug_name]["evidence_ids"]:
                drug_scores[drug_name]["evidence_ids"].append(eid)

            ml = item.get("_match_level", "gene_level_only")
            if ml == "exact_variant":
                drug_scores[drug_name]["has_exact_match"] = True
            drug_scores[drug_name]["match_levels"].append(ml)

            direction = (item.get("evidence_direction", "") or "").lower()
            if direction in ("does not support", "resistance"):
                drug_scores[drug_name]["resistance_count"] += 1
            if direction in ("conflicting",):
                drug_scores[drug_name]["conflict_count"] += 1

    # Run ranking engine on merged evidence
    match_level = "exact_variant" if any(d["has_exact_match"] for d in drug_scores.values()) else "gene_level_only"
    ranking_result = await engine.rank(
        gene_symbol=getattr(case, "cancer_type", ""),
        evidence_items=all_evidence_items,
        drug_interactions=all_drug_interactions,
        disease=getattr(case, "cancer_type", ""),
        variant_match_level=match_level,
    )

    # Attach variant contribution metadata to ranking
    ranking_result.case_id = case_id
    ranking_result.variant_ids = variant_ids  # Add this for tracking

    # Persist
    run_id = uuid.uuid4()
    ranking_result.id = str(run_id)
    try:
        await ranking_repo.create(ranking_result.model_dump())
    except Exception as e:
        logger.warning("Failed to persist case ranking: %s", e)

    return DrugRankingRunResponse(
        run_id=str(run_id),
        status="completed",
        ranking=ranking_result,
    )


@router.get("/run/{run_id}", response_model=DrugRankingRunResponse)
async def get_ranking_run(
    run_id: str,
    user: UserModel = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Get a previously computed ranking run."""
    try:
        rid = uuid.UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"error": "invalid_uuid", "message": "Invalid run ID"})

    ranking_repo = RankingRunRepository(db)
    run_model = await ranking_repo.get(rid)

    if not run_model:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Ranking run not found"})

    # Deserialize the stored JSON
    ranking_data = run_model.ranking_data if isinstance(run_model.ranking_data, dict) else {}
    ranking_result = DrugRankingResult(**ranking_data) if ranking_data else None

    return DrugRankingRunResponse(
        run_id=str(run_model.id),
        status=run_model.status,
        ranking=ranking_result,
    )
