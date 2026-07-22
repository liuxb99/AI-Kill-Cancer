"""
Clinical module API — Clinical Context Builder, Evidence Collector,
and Phase 2b multi-agent endpoints.

Provides:
- GET  /api/v1/clinical/context/{case_id}            — ClinicalContext JSON
- GET  /api/v1/clinical/evidence/{case_id}           — EvidenceBundle JSON
- GET  /api/v1/clinical/evidence/gene/{gene_symbol}  — EvidenceBundle by gene
- POST /api/v1/clinical/agents/{case_id}             — Agent opinions
- POST /api/v1/clinical/consensus/{case_id}          — Agent opinions + consensus
- POST /api/v1/clinical/recommend/{case_id}          — Full pipeline → recommendation
- POST /api/v1/clinical/analyze/{case_id}             — Full pipeline → all products
- GET  /api/v1/clinical/thread/{case_id}             — Decision thread (chronological)
- GET  /api/v1/clinical/thread/{case_id}/tree        — Decision tree (parent-child)
- GET  /api/v1/clinical/thread/node/{node_id}        — Single decision node
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.agents.consensus import ConsensusEngine, ConsensusResult
from src.backend.agents.models import AgentOpinion
from src.backend.agents.orchestrator import AgentOrchestrator
from src.backend.auth.dependencies import (
    require_auth,
    require_case_access,
    verify_case_access,
)
from src.backend.clinical.builder import CaseContextBuilder
from src.backend.clinical.collector import EvidenceCollector
from src.backend.clinical.decision_thread import (
    DecisionNode,
    DecisionThreadInjector,
    DecisionThreadRepository,
)
from src.backend.clinical.evidence_models import EvidenceBundle
from src.backend.clinical.models import ClinicalContext
from src.backend.clinical.recommendation import (
    RecommendationGenerator,
    TreatmentRecommendation,
)
from src.backend.database.session import get_db
from src.backend.domain.case_acl import CaseRole
from src.backend.domain.user import UserModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/clinical", tags=["clinical"])


# ─── Response models ────────────────────────────────────────────────────────────


class AnalyzeResponse(BaseModel):
    """Response model for the full analysis pipeline.

    Contains every intermediate and final product of the multi-agent
    clinical decision-support pipeline so that callers can inspect
    context, evidence, agent opinions, consensus, and the final
    treatment recommendation in a single response.
    """

    context: ClinicalContext
    evidence: EvidenceBundle
    opinions: list[AgentOpinion]
    consensus: ConsensusResult
    recommendation: TreatmentRecommendation


# ─── Helper ─────────────────────────────────────────────────────────────────────


async def _build_context_and_evidence(
    db: AsyncSession,
    case_id: str,
) -> tuple[ClinicalContext, EvidenceBundle]:
    """Build ClinicalContext and collect evidence for a case.

    Parameters
    ----------
    db : AsyncSession
        Database session.
    case_id : str
        Case UUID string.

    Returns
    -------
    tuple[ClinicalContext, EvidenceBundle]
        The built context and collected evidence.

    Raises
    ------
    HTTPException
        If the case_id is invalid or the case is not found.
    """
    try:
        uuid.UUID(case_id)
    except ValueError:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": f"Invalid case ID: {case_id}"},
        )

    builder = CaseContextBuilder(db)
    context = await builder.build(case_id)

    if not context.case_id:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": f"Case not found: {case_id}"},
        )

    collector = EvidenceCollector(db)
    evidence = await collector.collect(context)
    return context, evidence


# ─── Existing endpoints ─────────────────────────────────────────────────────────


@router.get("/context/{case_id}", response_model=ClinicalContext)
async def get_clinical_context(
    case_id: str,
    user: UserModel = Depends(require_case_access(CaseRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
) -> ClinicalContext:
    """Build and return a ClinicalContext snapshot for the given case.

    Uses CaseContextBuilder to assemble patient, case, and variant data
    from the database into a frozen ClinicalContext.
    """
    # Validate case_id format
    try:
        uuid.UUID(case_id)
    except ValueError:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": f"Invalid case ID: {case_id}"},
        )

    builder = CaseContextBuilder(db)
    context = await builder.build(case_id)

    if not context.case_id:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": f"Case not found: {case_id}"},
        )

    return context


@router.get("/evidence/gene/{gene_symbol}", response_model=EvidenceBundle)
async def get_evidence_by_gene(
    gene_symbol: str,
    user: UserModel = Depends(require_case_access(CaseRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
) -> EvidenceBundle:
    """Collect evidence for a gene symbol (shorthand).

    Uses EvidenceCollector.collect_by_variant(gene, "") to query all
    knowledge sources for evidence related to the given gene.
    """
    collector = EvidenceCollector(db)
    bundle = await collector.collect_by_variant(gene_symbol, "")
    return bundle


@router.get("/evidence/{case_id}", response_model=EvidenceBundle)
async def get_clinical_evidence(
    case_id: str,
    user: UserModel = Depends(require_case_access(CaseRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
) -> EvidenceBundle:
    """Collect evidence for a case by building context and querying all sources.

    First builds a ClinicalContext via CaseContextBuilder, then feeds it
    to EvidenceCollector.collect() to produce a comprehensive EvidenceBundle.
    """
    # Validate case_id format
    try:
        uuid.UUID(case_id)
    except ValueError:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": f"Invalid case ID: {case_id}"},
        )

    builder = CaseContextBuilder(db)
    context = await builder.build(case_id)

    if not context.case_id:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": f"Case not found: {case_id}"},
        )

    collector = EvidenceCollector(db)
    bundle = await collector.collect(context)
    return bundle


# ─── Phase 2b endpoints ─────────────────────────────────────────────────────────


@router.post(
    "/agents/{case_id}",
    response_model=list[AgentOpinion],
)
async def run_agents(
    case_id: str,
    user: UserModel = Depends(require_case_access(CaseRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
) -> list[AgentOpinion]:
    """Run all clinical decision-support agents for a case and return
    their structured opinions.

    Pipeline:
        1. Build ClinicalContext via CaseContextBuilder
        2. Collect evidence via EvidenceCollector
        3. Run all agents via AgentOrchestrator.run_all()

    Each step has independent error handling so that partial failures
    are reported gracefully.
    """
    # Step 1 & 2: context + evidence
    context, evidence = await _build_context_and_evidence(db, case_id)

    # ── Decision thread: record context_built and evidence_collected ──
    repo = DecisionThreadRepository(db)
    injector = DecisionThreadInjector(repo, case_id)
    await injector.record_context_built(context)
    await injector.record_evidence_collected(evidence)

    # Step 3: run agents
    orchestrator = AgentOrchestrator(db)
    opinions: list[AgentOpinion] = await orchestrator.run_all(context, evidence)

    # ── Decision thread: record each agent opinion ──
    for opinion in opinions:
        await injector.record_agent_opinion(opinion)

    return opinions


@router.post(
    "/consensus/{case_id}",
    response_model=ConsensusResult,
)
async def run_consensus(
    case_id: str,
    user: UserModel = Depends(require_case_access(CaseRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
) -> ConsensusResult:
    """Run agents and reach consensus for a case.

    Pipeline:
        1. Build ClinicalContext via CaseContextBuilder
        2. Collect evidence via EvidenceCollector
        3. Run all agents via AgentOrchestrator.run_all()
        4. Reach consensus via ConsensusEngine.reach_consensus()

    Each step has independent error handling so that partial failures
    are reported gracefully.
    """
    # Step 1 & 2: context + evidence
    context, evidence = await _build_context_and_evidence(db, case_id)

    # ── Decision thread: record context_built and evidence_collected ──
    repo = DecisionThreadRepository(db)
    injector = DecisionThreadInjector(repo, case_id)
    await injector.record_context_built(context)
    await injector.record_evidence_collected(evidence)

    # Step 3: run agents
    orchestrator = AgentOrchestrator(db)
    opinions: list[AgentOpinion] = await orchestrator.run_all(context, evidence)

    # ── Decision thread: record each agent opinion ──
    for opinion in opinions:
        await injector.record_agent_opinion(opinion)

    # Step 4: consensus
    engine = ConsensusEngine()
    consensus: ConsensusResult = await engine.reach_consensus(opinions, context)

    # ── Decision thread: record consensus_reached ──
    await injector.record_consensus_reached(consensus)

    return consensus


@router.post(
    "/recommend/{case_id}",
    response_model=TreatmentRecommendation,
)
async def recommend_treatment(
    case_id: str,
    user: UserModel = Depends(require_case_access(CaseRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
) -> TreatmentRecommendation:
    """Run the full analysis pipeline and return a treatment recommendation.

    Pipeline:
        1. Build ClinicalContext via CaseContextBuilder
        2. Collect evidence via EvidenceCollector
        3. Run all agents via AgentOrchestrator.run_all()
        4. Reach consensus via ConsensusEngine.reach_consensus()
        5. Generate recommendation via RecommendationGenerator.generate()

    Each step has independent error handling so that partial failures
    are reported gracefully.
    """
    # Step 1 & 2: context + evidence
    context, evidence = await _build_context_and_evidence(db, case_id)

    # ── Decision thread: record context_built and evidence_collected ──
    repo = DecisionThreadRepository(db)
    injector = DecisionThreadInjector(repo, case_id)
    await injector.record_context_built(context)
    await injector.record_evidence_collected(evidence)

    # Step 3: run agents
    orchestrator = AgentOrchestrator(db)
    opinions: list[AgentOpinion] = await orchestrator.run_all(context, evidence)

    # ── Decision thread: record each agent opinion ──
    for opinion in opinions:
        await injector.record_agent_opinion(opinion)

    # Step 4: consensus
    engine = ConsensusEngine()
    consensus: ConsensusResult = await engine.reach_consensus(opinions, context)

    # ── Decision thread: record consensus_reached ──
    await injector.record_consensus_reached(consensus)

    # Step 5: generate recommendation
    generator = RecommendationGenerator()
    recommendation: TreatmentRecommendation = await generator.generate(
        consensus, context, evidence,
    )

    # ── Decision thread: record recommendation_generated ──
    await injector.record_recommendation(recommendation)

    return recommendation


@router.post(
    "/analyze/{case_id}",
    response_model=AnalyzeResponse,
)
async def analyze_case(
    case_id: str,
    user: UserModel = Depends(require_case_access(CaseRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
) -> AnalyzeResponse:
    """Run the complete multi-agent analysis pipeline for a case.

    This is the primary endpoint for Phase 2b.  It executes every step
    of the clinical decision-support pipeline and returns all
    intermediate and final products:

    - **context**      — ClinicalContext snapshot of the case
    - **evidence**     — Aggregated EvidenceBundle from all sources
    - **opinions**     — Structured AgentOpinion list from all agents
    - **consensus**    — ConsensusResult with agreement level, conflicts
    - **recommendation** — Final TreatmentRecommendation

    Each step has independent error handling so that partial failures
    (e.g. an individual agent error) do not block the rest of the
    pipeline.
    """
    # Step 1 & 2: context + evidence
    context, evidence = await _build_context_and_evidence(db, case_id)

    # ── Decision thread: record context_built and evidence_collected ──
    repo = DecisionThreadRepository(db)
    injector = DecisionThreadInjector(repo, case_id)
    await injector.record_context_built(context)
    await injector.record_evidence_collected(evidence)

    # Step 3: run agents
    orchestrator = AgentOrchestrator(db)
    opinions: list[AgentOpinion] = await orchestrator.run_all(context, evidence)

    # ── Decision thread: record each agent opinion ──
    for opinion in opinions:
        await injector.record_agent_opinion(opinion)

    # Step 4: consensus
    engine = ConsensusEngine()
    consensus: ConsensusResult = await engine.reach_consensus(opinions, context)

    # ── Decision thread: record consensus_reached ──
    await injector.record_consensus_reached(consensus)

    # Step 5: generate recommendation
    generator = RecommendationGenerator()
    recommendation: TreatmentRecommendation = await generator.generate(
        consensus, context, evidence,
    )

    # ── Decision thread: record recommendation_generated ──
    await injector.record_recommendation(recommendation)

    return AnalyzeResponse(
        context=context,
        evidence=evidence,
        opinions=opinions,
        consensus=consensus,
        recommendation=recommendation,
    )


# ─── Digital Thread endpoints ─────────────────────────────────────────────────


@router.get("/thread/node/{node_id}", response_model=DecisionNode)
async def get_decision_node(
    node_id: str,
    user: UserModel = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> DecisionNode:
    """Retrieve a single decision node by its ID.

    Args:
        node_id: The decision node UUID string.

    Returns:
        The DecisionNode if found.

    Raises:
        HTTPException 404 if the node does not exist.
        HTTPException 403 if the user lacks access to the associated case.
    """
    repo = DecisionThreadRepository(db)
    node = await repo.get_node(node_id)

    if node is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "message": f"Decision node not found: {node_id}",
            },
        )

    # Verify the user has VIEWER access to the case this node belongs to
    await verify_case_access(
        case_id=uuid.UUID(node.case_id),
        user=user,
        db=db,
        required_role=CaseRole.VIEWER,
    )

    return node


@router.get("/thread/{case_id}", response_model=list[DecisionNode])
async def get_case_thread(
    case_id: str,
    user: UserModel = Depends(require_case_access(CaseRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
) -> list[DecisionNode]:
    """Retrieve the full decision thread for a case, ordered chronologically.

    Args:
        case_id: The case UUID string.

    Returns:
        A list of DecisionNode instances sorted by timestamp.

    Raises:
        HTTPException 404 if the case_id format is invalid.
    """
    # Validate case_id format
    try:
        uuid.UUID(case_id)
    except ValueError:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "message": f"Invalid case ID: {case_id}",
            },
        )

    repo = DecisionThreadRepository(db)
    nodes = await repo.get_case_thread(case_id)

    return nodes


@router.get("/thread/{case_id}/tree", response_model=list[DecisionNode])
async def get_decision_tree(
    case_id: str,
    user: UserModel = Depends(require_case_access(CaseRole.VIEWER)),
    db: AsyncSession = Depends(get_db),
) -> list[DecisionNode]:
    """Retrieve the full decision tree for a case, including parent-child
    relationship information encoded in ``parent_id`` fields.

    Args:
        case_id: The case UUID string.

    Returns:
        A list of DecisionNode instances sorted chronologically.  Nodes
        with ``parent_id = None`` are root nodes; the caller can
        reconstruct the tree by linking nodes via ``parent_id``.

    Raises:
        HTTPException 404 if the case_id format is invalid.
    """
    # Validate case_id format
    try:
        uuid.UUID(case_id)
    except ValueError:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "message": f"Invalid case ID: {case_id}",
            },
        )

    repo = DecisionThreadRepository(db)
    nodes = await repo.get_decision_tree(case_id)

    return nodes
