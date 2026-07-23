"""
DecisionNode model and DecisionThreadRepository for clinical decision traceability.

Each important decision during Phase 2 clinical reasoning produces a
``DecisionNode``, forming a digital thread (decision tree) that can be
audited, traced, and replayed.

The module also provides ``DecisionThreadInjector``, an API-layer helper
that automatically creates decision nodes after each pipeline step,
linking them via ``parent_id`` into a coherent decision chain.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator
from sqlalchemy import JSON, Column, DateTime, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database.models import Base as DBBase
from src.backend.database.models import CompatUUID

# ─── Node type literal ─────────────────────────────────────────────────────────

NodeType = Literal[
    "context_built",
    "evidence_collected",
    "agent_opinion",
    "consensus_reached",
    "recommendation_generated",
]

# ─── SQLAlchemy model ─────────────────────────────────────────────────────────


class DecisionNodeModel(DBBase):
    """Persistent storage for clinical decision nodes.

    Maps to the ``clinical_decision_nodes`` table created by migration 016.
    Each row represents one atomic decision or state transition in the
    clinical reasoning pipeline.
    """

    __tablename__ = "clinical_decision_nodes"

    id = Column(CompatUUID, primary_key=True, default=uuid.uuid4)
    case_id = Column(
        String(36),
        nullable=False,
        index=True,
    )
    parent_id = Column(CompatUUID, nullable=True)
    node_type = Column(String(64), nullable=False)
    input_snapshot = Column(JSON, nullable=True)
    evidence_snapshot = Column(JSON, nullable=True)
    agent_id = Column(String(128), nullable=True)
    agent_type = Column(String(64), nullable=True)
    reasoning = Column(Text, nullable=True)
    confidence = Column(String(32), nullable=True)
    decision_label = Column(String(256), nullable=True)
    timestamp = Column(DateTime, nullable=False)
    context_hash = Column(String(64), nullable=False, index=True)

    def __repr__(self) -> str:
        return (
            f"<DecisionNodeModel(id={self.id}, node_type={self.node_type!r}, "
            f"case_id={self.case_id!r})>"
        )


# ─── Pydantic model ───────────────────────────────────────────────────────────


class DecisionNode(BaseModel):
    """A single decision node in the clinical decision thread.

    This model is used for API serialisation and represents one atomic
    decision or state transition (context built, evidence collected,
    agent opinion, consensus reached, recommendation generated).
    """

    model_config = {"from_attributes": True}

    id: str
    case_id: str
    parent_id: str | None = None
    node_type: NodeType
    input_snapshot: dict[str, Any] = Field(default_factory=dict)
    evidence_snapshot: dict[str, Any] = Field(default_factory=dict)
    agent_id: str = ""
    agent_type: str = ""
    reasoning: str = ""
    confidence: str = ""
    decision_label: str = ""
    timestamp: str = ""
    """ISO-8601 formatted timestamp."""
    context_hash: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _convert_orm_fields(cls, data: Any) -> Any:
        """Convert ORM-specific types (UUID, datetime) to serialisable forms.

        When ``data`` is an ORM model instance (e.g. ``DecisionNodeModel``),
        UUID fields are converted to strings and ``datetime`` fields to
        ISO-8601 strings before Pydantic validation proceeds.
        """
        if not hasattr(data, "id"):
            return data  # already a dict or unknown type
        # Build a clean dict from the ORM instance, converting types
        converted: dict[str, Any] = {}
        for field_name in (
            "id", "case_id", "parent_id", "node_type",
            "input_snapshot", "evidence_snapshot", "agent_id",
            "agent_type", "reasoning", "confidence", "decision_label",
            "timestamp", "context_hash",
        ):
            raw = getattr(data, field_name, None)
            if isinstance(raw, uuid.UUID):
                converted[field_name] = str(raw)
            elif isinstance(raw, datetime):
                converted[field_name] = raw.isoformat()
            elif raw is None:
                # Map NULL from DB to the Pydantic field default
                if field_name in ("input_snapshot", "evidence_snapshot"):
                    converted[field_name] = {}
                elif field_name in ("agent_id", "agent_type", "reasoning", "confidence", "decision_label"):
                    converted[field_name] = ""
                elif field_name in ("timestamp",):
                    converted[field_name] = ""
                elif field_name in ("context_hash", "parent_id"):
                    converted[field_name] = None
                elif field_name in ("id", "case_id", "node_type"):
                    converted[field_name] = raw  # should not be None, but pass through
                else:
                    converted[field_name] = raw
            else:
                converted[field_name] = raw
        return converted


# ─── Repository ───────────────────────────────────────────────────────────────


class DecisionThreadRepository:
    """Repository for managing ``DecisionNode`` persistence.

    Handles CRUD operations on the ``clinical_decision_nodes`` table and
    provides thread / tree queries for clinical decision traceability.

    Attributes:
        db: The async SQLAlchemy session used for all database operations.
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialise the repository with a database session.

        Args:
            db: An active async SQLAlchemy session.
        """
        self.db = db

    async def create_node(self, node: DecisionNode) -> DecisionNode:
        """Persist a new decision node.

        Args:
            node: The ``DecisionNode`` instance to persist.  Its ``id``
                field is ignored — a new UUID is assigned by the model.

        Returns:
            The saved ``DecisionNode`` with the server-assigned ``id``
            and normalised ``timestamp``.
        """
        timestamp: datetime
        if node.timestamp:
            try:
                timestamp = datetime.fromisoformat(node.timestamp)
            except (ValueError, TypeError):
                timestamp = datetime.utcnow()
        else:
            timestamp = datetime.utcnow()

        model = DecisionNodeModel(
            id=uuid.uuid4(),
            case_id=node.case_id,
            parent_id=uuid.UUID(node.parent_id) if node.parent_id else None,
            node_type=node.node_type,
            input_snapshot=node.input_snapshot,
            evidence_snapshot=node.evidence_snapshot,
            agent_id=node.agent_id,
            agent_type=node.agent_type,
            reasoning=node.reasoning,
            confidence=node.confidence,
            decision_label=node.decision_label,
            timestamp=timestamp,
            context_hash=node.context_hash or "",
        )
        self.db.add(model)
        await self.db.commit()
        await self.db.refresh(model)
        return DecisionNode.model_validate(model)

    async def get_case_thread(self, case_id: str) -> list[DecisionNode]:
        """Retrieve all decision nodes for a given case, ordered by timestamp.

        Args:
            case_id: The case identifier.

        Returns:
            A list of ``DecisionNode`` instances, sorted chronologically.
        """
        stmt = (
            select(DecisionNodeModel)
            .where(DecisionNodeModel.case_id == case_id)
            .order_by(DecisionNodeModel.timestamp.asc())
        )
        result = await self.db.execute(stmt)
        models = result.scalars().all()
        return [DecisionNode.model_validate(m) for m in models]

    async def get_decision_tree(self, case_id: str) -> list[DecisionNode]:
        """Retrieve the full decision tree for a case (including parent-child relationships).

        This method returns all nodes for the case, ordered by timestamp.
        The caller can reconstruct the tree by linking nodes via
        ``parent_id`` — a node with ``parent_id=None`` is a root node.

        Args:
            case_id: The case identifier.

        Returns:
            A list of ``DecisionNode`` instances, sorted chronologically.
        """
        # Currently returns the same ordered list as get_case_thread;
        # the parent-child linking is left to the caller. This preserves
        # the flat storage model while enabling tree reconstruction.
        return await self.get_case_thread(case_id)

    async def get_node(self, node_id: str) -> DecisionNode | None:
        """Retrieve a single decision node by its ID.

        Args:
            node_id: The node UUID string.

        Returns:
            The ``DecisionNode`` if found, otherwise ``None``.
        """
        try:
            uid = uuid.UUID(node_id)
        except (ValueError, AttributeError):
            return None
        stmt = select(DecisionNodeModel).where(DecisionNodeModel.id == uid)
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return DecisionNode.model_validate(model)


class DecisionThreadInjector:
    """API-layer helper that injects decision nodes into the digital thread.

    Creates a ``DecisionNode`` after each pipeline step (context built,
    evidence collected, agent opinion, consensus reached, recommendation
    generated) and chains them together via ``parent_id``.

    One instance should be created per API call — it is not reused across
    requests.

    Attributes:
        repo: The ``DecisionThreadRepository`` used to persist nodes.
        _last_node_id: The ID of the most recently created node, used
            as ``parent_id`` for the next node in the chain.
    """

    def __init__(self, repo: DecisionThreadRepository, case_id: str) -> None:
        """Initialise the injector with a repository and case identifier.

        Args:
            repo: A ``DecisionThreadRepository`` bound to the current
                database session.
            case_id: The case UUID string that all nodes in this chain
                belong to.
        """
        self.repo = repo
        self.case_id = case_id
        self._last_node_id: str | None = None

    async def record_context_built(self, context: Any) -> str:
        """Create a decision node after the ClinicalContext has been built.

        Args:
            context: The ``ClinicalContext`` instance produced by
                ``CaseContextBuilder.build()``.

        Returns:
            The UUID string of the newly created node.
        """
        node = DecisionNode(
            id="",
            case_id=self.case_id,
            parent_id=self._last_node_id,
            node_type="context_built",
            input_snapshot=context.model_dump() if hasattr(context, "model_dump") else {},
            context_hash=getattr(context, "context_hash", None),
            decision_label=f"Context built for case {context.case_id}",
        )
        saved = await self.repo.create_node(node)
        self._last_node_id = saved.id
        return saved.id

    async def record_evidence_collected(self, evidence: Any) -> str:
        """Create a decision node after evidence has been collected.

        Args:
            evidence: The ``EvidenceBundle`` instance produced by
                ``EvidenceCollector.collect()``.

        Returns:
            The UUID string of the newly created node.
        """
        bundle_dict: dict[str, Any] = {}
        if hasattr(evidence, "model_dump"):
            bundle_dict = evidence.model_dump()

        node = DecisionNode(
            id="",
            case_id=self.case_id,
            parent_id=self._last_node_id,
            node_type="evidence_collected",
            evidence_snapshot={
                "total_count": bundle_dict.get("total_count", len(bundle_dict.get("items", []))),
                "by_source": bundle_dict.get("by_source", {}),
            },
            context_hash=getattr(evidence, "context_hash", None),
            decision_label=(
                f"Evidence collected: {bundle_dict.get('total_count', 0)} items"
            ),
        )
        saved = await self.repo.create_node(node)
        self._last_node_id = saved.id
        return saved.id

    async def record_agent_opinion(self, opinion: Any) -> str:
        """Create a decision node after an agent has produced an opinion.

        Args:
            opinion: The ``AgentOpinion`` instance produced by one agent.

        Returns:
            The UUID string of the newly created node.
        """
        node = DecisionNode(
            id="",
            case_id=self.case_id,
            parent_id=self._last_node_id,
            node_type="agent_opinion",
            agent_id=getattr(opinion, "agent_type", ""),
            agent_type=getattr(opinion, "agent_type", ""),
            reasoning=getattr(opinion, "summary", ""),
            confidence=getattr(opinion, "confidence", "medium"),
            context_hash=getattr(opinion, "context_hash", None),
            decision_label=f"Agent opinion: {getattr(opinion, 'agent_type', 'unknown')}",
        )
        saved = await self.repo.create_node(node)
        self._last_node_id = saved.id
        return saved.id

    async def record_consensus_reached(self, consensus: Any) -> str:
        """Create a decision node after consensus has been reached.

        Args:
            consensus: The ``ConsensusResult`` instance produced by
                ``ConsensusEngine.reach_consensus()``.

        Returns:
            The UUID string of the newly created node.
        """
        recommended = getattr(consensus, "recommended_option", {})
        treatment = recommended.get("treatment", "") if isinstance(recommended, dict) else ""

        node = DecisionNode(
            id="",
            case_id=self.case_id,
            parent_id=self._last_node_id,
            node_type="consensus_reached",
            reasoning=(
                f"Agreement: {getattr(consensus, 'agreement', 'unknown')} | "
                f"Confidence: {getattr(consensus, 'confidence', 'unknown')}"
            ),
            confidence=getattr(consensus, "confidence", "medium"),
            decision_label=treatment or f"Consensus reached: {getattr(consensus, 'agreement', 'unknown')} agreement",
            context_hash=getattr(consensus, "context_hash", None),
        )
        saved = await self.repo.create_node(node)
        self._last_node_id = saved.id
        return saved.id

    async def record_recommendation(self, recommendation: Any) -> str:
        """Create a decision node after a treatment recommendation has been generated.

        Args:
            recommendation: The ``TreatmentRecommendation`` instance
                produced by ``RecommendationGenerator.generate()``.

        Returns:
            The UUID string of the newly created node.
        """
        first_line = getattr(recommendation, "first_line", {})
        treatment = first_line.get("treatment", "") if isinstance(first_line, dict) else ""

        node = DecisionNode(
            id="",
            case_id=self.case_id,
            parent_id=self._last_node_id,
            node_type="recommendation_generated",
            input_snapshot={
                "first_line": treatment,
                "has_second_line": bool(getattr(recommendation, "second_line", None)),
                "has_clinical_trial": bool(getattr(recommendation, "clinical_trial", None)),
            },
            decision_label=treatment or "Recommendation generated",
            context_hash=getattr(recommendation, "context_hash", None),
        )
        saved = await self.repo.create_node(node)
        self._last_node_id = saved.id
        return saved.id


__all__ = [
    "DecisionNode",
    "DecisionNodeModel",
    "DecisionThreadInjector",
    "DecisionThreadRepository",
    "NodeType",
]
