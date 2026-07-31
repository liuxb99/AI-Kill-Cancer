"""
ClinicalPipelineService — Phase 2b 臨床多代理人管線的 transaction 管理。

REVIEW-PHASE3F0-R3-P0-01: ``get_db`` 已移除自動 commit，直接寫入 DB 的
endpoint 必須由 Service 管理 transaction。本 Service 將 clinical API 的
四個流程（run_agents / run_consensus / recommend_treatment / analyze_case）
的「Decision Thread 寫入 + 流程執行」包在單一 transaction 中：成功 commit
一次、失敗 rollback 後 re-raise。若流程中拋出 ``HTTPException``（4xx），
transaction 同樣 rollback 後 re-raise，由 API 層透傳。

Repository（``DecisionThreadRepository.create_node``）已改為 flush-only，
不自行 commit。
"""

from __future__ import annotations

import logging

from src.backend.agents.consensus import ConsensusEngine, ConsensusResult
from src.backend.agents.models import AgentOpinion
from src.backend.agents.orchestrator import AgentOrchestrator
from src.backend.clinical.decision_thread import (
    DecisionThreadInjector,
    DecisionThreadRepository,
)
from src.backend.clinical.evidence_models import EvidenceBundle
from src.backend.clinical.models import ClinicalContext
from src.backend.clinical.recommendation import (
    RecommendationGenerator,
    TreatmentRecommendation,
)
from src.backend.services.base import BaseService

logger = logging.getLogger(__name__)


class AnalysisPipelineResult:
    """``analyze_case`` 流程的完整彙總結果。

    包含管線所有中間與最終產物，供 API 層組裝成 ``AnalyzeResponse``。
    """

    __slots__ = ("context", "evidence", "opinions", "consensus", "recommendation")

    def __init__(
        self,
        context: ClinicalContext,
        evidence: EvidenceBundle,
        opinions: list[AgentOpinion],
        consensus: ConsensusResult,
        recommendation: TreatmentRecommendation,
    ) -> None:
        self.context = context
        self.evidence = evidence
        self.opinions = opinions
        self.consensus = consensus
        self.recommendation = recommendation


class ClinicalPipelineService(BaseService):
    """在單一 transaction 中執行 Phase 2b 臨床決策管線。

    每個公開方法對應一個 API 流程，內部以 ``self._run`` 包裝：
    成功時由 transaction wrapper commit 一次；任何異常（含
    ``HTTPException``）rollback 後 re-raise。

    Parameters
    ----------
    db : AsyncSession
        由 ``get_db`` 注入的 session；transaction 完全由本 Service 管理。
    """

    async def run_agents(
        self,
        case_id: str,
        context: ClinicalContext,
        evidence: EvidenceBundle,
    ) -> list[AgentOpinion]:
        """記錄 context/evidence 節點、執行所有 agents，返回 opinions。"""

        async def _op() -> list[AgentOpinion]:
            _, opinions = await self._run_agents_phase(case_id, context, evidence)
            return opinions

        return await self._run(_op)

    async def run_consensus(
        self,
        case_id: str,
        context: ClinicalContext,
        evidence: EvidenceBundle,
    ) -> ConsensusResult:
        """agents 流程 + 產出並記錄 consensus。"""

        async def _op() -> ConsensusResult:
            injector, opinions = await self._run_agents_phase(case_id, context, evidence)
            engine = ConsensusEngine()
            consensus: ConsensusResult = await engine.reach_consensus(opinions, context)
            await injector.record_consensus_reached(consensus)
            return consensus

        return await self._run(_op)

    async def recommend_treatment(
        self,
        case_id: str,
        context: ClinicalContext,
        evidence: EvidenceBundle,
    ) -> TreatmentRecommendation:
        """agents + consensus + 產出並記錄 treatment recommendation。"""

        async def _op() -> TreatmentRecommendation:
            injector, opinions = await self._run_agents_phase(case_id, context, evidence)
            engine = ConsensusEngine()
            consensus: ConsensusResult = await engine.reach_consensus(opinions, context)
            await injector.record_consensus_reached(consensus)

            generator = RecommendationGenerator()
            recommendation: TreatmentRecommendation = await generator.generate(
                consensus, context, evidence,
            )
            await injector.record_recommendation(recommendation)
            return recommendation

        return await self._run(_op)

    async def analyze_case(
        self,
        case_id: str,
        context: ClinicalContext,
        evidence: EvidenceBundle,
    ) -> AnalysisPipelineResult:
        """完整管線（agents + consensus + recommendation）並彙總全部產物。"""

        async def _op() -> AnalysisPipelineResult:
            injector, opinions = await self._run_agents_phase(case_id, context, evidence)
            engine = ConsensusEngine()
            consensus: ConsensusResult = await engine.reach_consensus(opinions, context)
            await injector.record_consensus_reached(consensus)

            generator = RecommendationGenerator()
            recommendation: TreatmentRecommendation = await generator.generate(
                consensus, context, evidence,
            )
            await injector.record_recommendation(recommendation)

            return AnalysisPipelineResult(
                context=context,
                evidence=evidence,
                opinions=opinions,
                consensus=consensus,
                recommendation=recommendation,
            )

        return await self._run(_op)

    # ── Internal helpers ───────────────────────────────────────────────────

    async def _run_agents_phase(
        self,
        case_id: str,
        context: ClinicalContext,
        evidence: EvidenceBundle,
    ) -> tuple[DecisionThreadInjector, list[AgentOpinion]]:
        """記錄 context_built / evidence_collected 節點並執行所有 agents。

        返回 ``(injector, opinions)``，讓後續流程（consensus、
        recommendation）能沿用相同的 decision thread 鏈（parent_id）。
        """
        repo = DecisionThreadRepository(self.db)
        injector = DecisionThreadInjector(repo, case_id)
        await injector.record_context_built(context)
        await injector.record_evidence_collected(evidence)

        orchestrator = AgentOrchestrator(self.db)
        opinions: list[AgentOpinion] = await orchestrator.run_all(context, evidence)

        for opinion in opinions:
            await injector.record_agent_opinion(opinion)

        return injector, opinions


__all__ = [
    "AnalysisPipelineResult",
    "ClinicalPipelineService",
]
