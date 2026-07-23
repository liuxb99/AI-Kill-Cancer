"""
Unit tests for DecisionNode, DecisionThreadRepository, and DecisionThreadInjector.

Tests cover:
- DecisionNode Pydantic model creation and serialisation
- DecisionThreadRepository CRUD and query methods
- DecisionThreadInjector record_*() methods and node chaining
- Edge cases: invalid IDs, empty data, None values
- Session reload and persistence round-trip with real SQLite
"""

from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.backend.clinical.decision_thread import (
    DecisionNode,
    DecisionNodeModel,
    DecisionThreadInjector,
    DecisionThreadRepository,
)
from src.backend.clinical.models import ClinicalContext
from src.backend.database.models import Base

# ─── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_db():
    """Create a mock async SQLAlchemy session."""
    db = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def repo(mock_db):
    """Create a DecisionThreadRepository with a mock DB session."""
    return DecisionThreadRepository(mock_db)


@pytest.fixture
def sample_node_dict():
    """Return a minimal valid DecisionNode dictionary."""
    return {
        "id": str(uuid.uuid4()),
        "case_id": str(uuid.uuid4()),
        "node_type": "context_built",
        "input_snapshot": {"genome": "GRCh38"},
        "context_hash": "abc123",
        "timestamp": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def injector(repo):
    """Create a DecisionThreadInjector with a mock repo and fixed case_id."""
    return DecisionThreadInjector(repo, case_id=str(uuid.uuid4()))


# ─── Test DecisionNode model ───────────────────────────────────────────────────


class TestDecisionNodeModel:
    """DecisionNode Pydantic model creation and serialisation."""

    async def test_create_minimal_node(self):
        """Create a DecisionNode with only required fields."""
        case_id = str(uuid.uuid4())
        node = DecisionNode(
            id="",
            case_id=case_id,
            node_type="context_built",
        )
        assert node.id == ""
        assert node.case_id == case_id
        assert node.node_type == "context_built"
        assert node.input_snapshot == {}
        assert node.evidence_snapshot == {}
        assert node.agent_id == ""
        assert node.agent_type == ""
        assert node.reasoning == ""
        assert node.confidence == ""
        assert node.decision_label == ""
        assert node.timestamp == ""
        assert node.context_hash is None
        assert node.parent_id is None

    async def test_create_full_node(self):
        """Create a DecisionNode with all fields populated."""
        node_id = str(uuid.uuid4())
        case_id = str(uuid.uuid4())
        parent_id = str(uuid.uuid4())
        ts = datetime.utcnow().isoformat()
        node = DecisionNode(
            id=node_id,
            case_id=case_id,
            parent_id=parent_id,
            node_type="consensus_reached",
            input_snapshot={"key": "value"},
            evidence_snapshot={"count": 5},
            agent_id="agent-1",
            agent_type="hematologist",
            reasoning="All agents agree",
            confidence="high",
            decision_label="Start treatment A",
            timestamp=ts,
            context_hash="def456",
        )
        assert node.id == node_id
        assert node.parent_id == parent_id
        assert node.node_type == "consensus_reached"
        assert node.input_snapshot == {"key": "value"}
        assert node.agent_id == "agent-1"
        assert node.timestamp == ts
        assert node.context_hash == "def456"

    async def test_serialise_to_dict(self):
        """DecisionNode.model_dump() returns a serialisable dict."""
        case_id = str(uuid.uuid4())
        node = DecisionNode(
            id="",
            case_id=case_id,
            node_type="evidence_collected",
            evidence_snapshot={"items": ["a"]},
        )
        dumped = node.model_dump()
        assert dumped["case_id"] == case_id
        assert dumped["node_type"] == "evidence_collected"
        assert dumped["evidence_snapshot"] == {"items": ["a"]}
        assert dumped["parent_id"] is None
        assert isinstance(dumped["id"], str)

    async def test_deserialise_from_dict(self):
        """DecisionNode.model_validate() reconstructs from a dict."""
        data = {
            "id": str(uuid.uuid4()),
            "case_id": str(uuid.uuid4()),
            "node_type": "agent_opinion",
            "agent_id": "dr-ai",
            "reasoning": "BRAF V600E is actionable",
        }
        node = DecisionNode.model_validate(data)
        assert node.case_id == data["case_id"]
        assert node.node_type == "agent_opinion"
        assert node.agent_id == "dr-ai"
        assert node.reasoning == "BRAF V600E is actionable"

    async def test_from_orm_converts_uuids(self):
        """DecisionNode.model_validate() converts ORM UUID/datetime to strings."""
        orm_id = uuid.uuid4()
        case_id = uuid.uuid4()
        parent_id = uuid.uuid4()
        now = datetime.utcnow()

        orm_model = MagicMock(spec=DecisionNodeModel)
        orm_model.id = orm_id
        orm_model.case_id = str(case_id)
        orm_model.parent_id = parent_id
        orm_model.node_type = "recommendation_generated"
        orm_model.input_snapshot = {"treatment": "A"}
        orm_model.evidence_snapshot = None
        orm_model.agent_id = None
        orm_model.agent_type = None
        orm_model.reasoning = None
        orm_model.confidence = "high"
        orm_model.decision_label = None
        orm_model.timestamp = now
        orm_model.context_hash = "xyz"

        node = DecisionNode.model_validate(orm_model)
        assert node.id == str(orm_id)
        assert node.parent_id == str(parent_id)
        assert node.timestamp == now.isoformat()
        # NULL fields should map to defaults
        assert node.input_snapshot == {"treatment": "A"}  # kept as-is
        assert node.evidence_snapshot == {}  # None -> {}
        assert node.agent_id == ""  # None -> ""
        assert node.reasoning == ""  # None -> ""
        assert node.decision_label == ""  # None -> ""

    async def test_from_orm_with_none_parent_id(self):
        """Root node with parent_id=None stays None after conversion."""
        orm_model = MagicMock(spec=DecisionNodeModel)
        orm_model.id = uuid.uuid4()
        orm_model.case_id = str(uuid.uuid4())
        orm_model.parent_id = None
        orm_model.node_type = "context_built"
        orm_model.input_snapshot = None
        orm_model.evidence_snapshot = None
        orm_model.agent_id = None
        orm_model.agent_type = None
        orm_model.reasoning = None
        orm_model.confidence = None
        orm_model.decision_label = None
        orm_model.timestamp = datetime.utcnow()
        orm_model.context_hash = None

        node = DecisionNode.model_validate(orm_model)
        assert node.parent_id is None
        assert node.context_hash is None
        assert node.input_snapshot == {}

    async def test_invalid_node_type_raises(self):
        """An invalid node_type literal raises a validation error."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            DecisionNode(
                id="",
                case_id=str(uuid.uuid4()),
                node_type="invalid_type",  # type: ignore[arg-type]
            )

    async def test_model_copy_and_update(self):
        """DecisionNode supports copy/update for immutable modifications."""
        node = DecisionNode(
            id=str(uuid.uuid4()),
            case_id=str(uuid.uuid4()),
            node_type="agent_opinion",
            agent_id="dr-a",
        )
        updated = node.model_copy(update={"agent_id": "dr-b"})
        assert updated.agent_id == "dr-b"
        assert node.agent_id == "dr-a"  # original unchanged


# ─── Test DecisionThreadRepository ────────────────────────────────────────────


class TestDecisionThreadRepository:
    """DecisionThreadRepository CRUD and query methods."""

    async def test_create_node_persists_and_returns_node(self, repo, sample_node_dict):
        """create_node persists a DecisionNodeModel and returns a DecisionNode."""
        node = DecisionNode(**sample_node_dict)
        result = await repo.create_node(node)

        assert isinstance(result, DecisionNode)
        assert result.case_id == sample_node_dict["case_id"]
        assert result.node_type == sample_node_dict["node_type"]
        # A new ID should be assigned
        assert result.id != ""
        assert result.id != sample_node_dict["id"]
        # Timestamp should be populated
        assert result.timestamp != ""
        # Verify DB session interactions
        repo.db.add.assert_called_once()
        repo.db.commit.assert_awaited_once()
        repo.db.refresh.assert_awaited_once()

    async def test_create_node_with_timestamp(self, repo):
        """create_node respects a valid provided timestamp."""
        ts = datetime.utcnow().isoformat()
        node = DecisionNode(
            id="",
            case_id=str(uuid.uuid4()),
            node_type="context_built",
            timestamp=ts,
        )
        result = await repo.create_node(node)
        assert result.timestamp != ""

    async def test_create_node_with_parent(self, repo):
        """create_node correctly stores parent_id linkage."""
        parent_id = str(uuid.uuid4())
        node = DecisionNode(
            id="",
            case_id=str(uuid.uuid4()),
            parent_id=parent_id,
            node_type="agent_opinion",
        )
        result = await repo.create_node(node)
        assert result.parent_id == parent_id

    async def test_get_case_thread_returns_ordered_nodes(self, repo):
        """get_case_thread returns all nodes for a case, ordered by timestamp."""
        case_id = str(uuid.uuid4())
        mock_model_1 = MagicMock(spec=DecisionNodeModel)
        mock_model_1.id = uuid.uuid4()
        mock_model_1.case_id = case_id
        mock_model_1.parent_id = None
        mock_model_1.node_type = "context_built"
        mock_model_1.input_snapshot = {}
        mock_model_1.evidence_snapshot = {}
        mock_model_1.agent_id = ""
        mock_model_1.agent_type = ""
        mock_model_1.reasoning = ""
        mock_model_1.confidence = ""
        mock_model_1.decision_label = ""
        mock_model_1.timestamp = datetime.utcnow()
        mock_model_1.context_hash = ""

        mock_model_2 = MagicMock(spec=DecisionNodeModel)
        mock_model_2.id = uuid.uuid4()
        mock_model_2.case_id = case_id
        mock_model_2.parent_id = mock_model_1.id
        mock_model_2.node_type = "agent_opinion"
        mock_model_2.input_snapshot = {}
        mock_model_2.evidence_snapshot = {}
        mock_model_2.agent_id = "agent-1"
        mock_model_2.agent_type = "oncologist"
        mock_model_2.reasoning = "test"
        mock_model_2.confidence = "medium"
        mock_model_2.decision_label = ""
        mock_model_2.timestamp = datetime.utcnow()
        mock_model_2.context_hash = ""

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_model_1, mock_model_2]
        repo.db.execute = AsyncMock(return_value=mock_result)

        nodes = await repo.get_case_thread(case_id)
        assert len(nodes) == 2
        assert isinstance(nodes[0], DecisionNode)
        assert nodes[0].case_id == case_id
        assert nodes[0].node_type == "context_built"
        assert nodes[1].node_type == "agent_opinion"
        assert nodes[1].parent_id == str(mock_model_1.id)

    async def test_get_case_thread_empty(self, repo):
        """get_case_thread returns empty list when no nodes exist."""
        case_id = str(uuid.uuid4())
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        repo.db.execute = AsyncMock(return_value=mock_result)

        nodes = await repo.get_case_thread(case_id)
        assert nodes == []

    async def test_get_decision_tree_returns_same_as_thread(self, repo):
        """get_decision_tree currently returns the same ordered list as get_case_thread."""
        case_id = str(uuid.uuid4())
        # The implementation delegates to get_case_thread, so mock that
        # We verify the method returns the same type and calls through
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        repo.db.execute = AsyncMock(return_value=mock_result)

        nodes = await repo.get_decision_tree(case_id)
        assert isinstance(nodes, list)
        assert len(nodes) == 0

    async def test_get_node_returns_node_for_valid_id(self, repo):
        """get_node returns a DecisionNode when a valid UUID string is given."""
        node_id = str(uuid.uuid4())
        mock_model = MagicMock(spec=DecisionNodeModel)
        mock_model.id = uuid.UUID(node_id)
        mock_model.case_id = str(uuid.uuid4())
        mock_model.parent_id = None
        mock_model.node_type = "context_built"
        mock_model.input_snapshot = {}
        mock_model.evidence_snapshot = {}
        mock_model.agent_id = ""
        mock_model.agent_type = ""
        mock_model.reasoning = ""
        mock_model.confidence = ""
        mock_model.decision_label = ""
        mock_model.timestamp = datetime.utcnow()
        mock_model.context_hash = ""

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        repo.db.execute = AsyncMock(return_value=mock_result)

        node = await repo.get_node(node_id)
        assert node is not None
        assert node.id == node_id
        assert node.node_type == "context_built"

    async def test_get_node_returns_none_for_invalid_id(self, repo):
        """get_node returns None when node_id is not a valid UUID."""
        node = await repo.get_node("not-a-uuid")
        assert node is None
        repo.db.execute.assert_not_called()

    async def test_get_node_returns_none_for_missing_id(self, repo):
        """get_node returns None when no node matches the given UUID."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        repo.db.execute = AsyncMock(return_value=mock_result)

        node = await repo.get_node(str(uuid.uuid4()))
        assert node is None

    async def test_get_node_returns_none_for_empty_string(self, repo):
        """get_node returns None for empty string node_id."""
        node = await repo.get_node("")
        assert node is None
        repo.db.execute.assert_not_called()

    async def test_create_node_with_none_context_hash(self, repo):
        """create_node handles None context_hash gracefully."""
        node = DecisionNode(
            id="",
            case_id=str(uuid.uuid4()),
            node_type="context_built",
            context_hash=None,
        )
        result = await repo.create_node(node)
        assert isinstance(result, DecisionNode)

    async def test_create_node_with_invalid_timestamp_falls_back(self, repo):
        """create_node falls back to utcnow when timestamp is unparseable."""
        node = DecisionNode(
            id="",
            case_id=str(uuid.uuid4()),
            node_type="context_built",
            timestamp="not-a-valid-timestamp",
        )
        result = await repo.create_node(node)
        assert result.timestamp != "not-a-valid-timestamp"
        assert result.timestamp != ""


# ─── Test DecisionThreadInjector ──────────────────────────────────────────────


class TestDecisionThreadInjector:
    """DecisionThreadInjector record_*() methods and node chaining."""

    async def test_record_context_built_creates_node(self, injector):
        """record_context_built creates a context_built node and returns its ID."""
        mock_context = MagicMock()
        mock_context.model_dump.return_value = {"case_id": injector.case_id}
        mock_context.case_id = injector.case_id
        mock_context.context_hash = "hash001"

        # Mock repo.create_node to return a predictable node
        saved_node = DecisionNode(
            id=str(uuid.uuid4()),
            case_id=injector.case_id,
            node_type="context_built",
            input_snapshot={"case_id": injector.case_id},
            context_hash="hash001",
            decision_label=f"Context built for case {injector.case_id}",
        )
        injector.repo.create_node = AsyncMock(return_value=saved_node)

        result_id = await injector.record_context_built(mock_context)
        assert result_id == saved_node.id
        assert injector._last_node_id == saved_node.id

    async def test_record_context_built_links_to_parent(self, injector):
        """record_context_built sets parent_id from _last_node_id."""
        parent_id = str(uuid.uuid4())
        injector._last_node_id = parent_id

        mock_context = MagicMock()
        mock_context.model_dump.return_value = {}
        mock_context.case_id = injector.case_id
        mock_context.context_hash = None

        def create_node_side_effect(node: DecisionNode) -> DecisionNode:
            assert node.parent_id == parent_id
            return DecisionNode(
                id=str(uuid.uuid4()),
                case_id=node.case_id,
                parent_id=node.parent_id,
                node_type=node.node_type,
                input_snapshot=node.input_snapshot,
                context_hash=node.context_hash,
                decision_label=node.decision_label,
            )

        injector.repo.create_node = AsyncMock(side_effect=create_node_side_effect)
        await injector.record_context_built(mock_context)

    async def test_record_evidence_collected_creates_node(self, injector):
        """record_evidence_collected creates an evidence_collected node."""
        mock_evidence = MagicMock()
        mock_evidence.model_dump.return_value = {
            "total_count": 5,
            "by_source": {"pubmed": 3, "guideline": 2},
            "items": ["a", "b", "c", "d", "e"],
        }
        mock_evidence.context_hash = "hash002"

        saved_node = DecisionNode(
            id=str(uuid.uuid4()),
            case_id=injector.case_id,
            node_type="evidence_collected",
            evidence_snapshot={"total_count": 5, "by_source": {"pubmed": 3, "guideline": 2}},
            context_hash="hash002",
            decision_label="Evidence collected: 5 items",
        )
        injector.repo.create_node = AsyncMock(return_value=saved_node)

        result_id = await injector.record_evidence_collected(mock_evidence)
        assert result_id == saved_node.id
        assert injector._last_node_id == saved_node.id

    async def test_record_evidence_collected_no_model_dump(self, injector):
        """record_evidence_collected handles objects without model_dump."""
        mock_evidence = MagicMock()
        del mock_evidence.model_dump
        mock_evidence.context_hash = None

        saved_node = DecisionNode(
            id=str(uuid.uuid4()),
            case_id=injector.case_id,
            node_type="evidence_collected",
            evidence_snapshot={"total_count": 0, "by_source": {}},
            decision_label="Evidence collected: 0 items",
        )
        injector.repo.create_node = AsyncMock(return_value=saved_node)

        result_id = await injector.record_evidence_collected(mock_evidence)
        assert result_id == saved_node.id

    async def test_record_agent_opinion_creates_node(self, injector):
        """record_agent_opinion creates an agent_opinion node."""
        mock_opinion = MagicMock()
        mock_opinion.agent_type = "oncologist"
        mock_opinion.summary = "BRAF V600E detected"
        mock_opinion.confidence = "high"
        mock_opinion.context_hash = "hash003"

        saved_node = DecisionNode(
            id=str(uuid.uuid4()),
            case_id=injector.case_id,
            node_type="agent_opinion",
            agent_id="oncologist",
            agent_type="oncologist",
            reasoning="BRAF V600E detected",
            confidence="high",
            context_hash="hash003",
            decision_label="Agent opinion: oncologist",
        )
        injector.repo.create_node = AsyncMock(return_value=saved_node)

        result_id = await injector.record_agent_opinion(mock_opinion)
        assert result_id == saved_node.id
        assert injector._last_node_id == saved_node.id

    async def test_record_consensus_reached_creates_node(self, injector):
        """record_consensus_reached creates a consensus_reached node."""
        mock_consensus = MagicMock()
        mock_consensus.recommended_option = {"treatment": "Surgery"}
        mock_consensus.agreement = "unanimous"
        mock_consensus.confidence = "high"
        mock_consensus.context_hash = "hash004"

        saved_node = DecisionNode(
            id=str(uuid.uuid4()),
            case_id=injector.case_id,
            node_type="consensus_reached",
            reasoning="Agreement: unanimous | Confidence: high",
            confidence="high",
            decision_label="Surgery",
            context_hash="hash004",
        )
        injector.repo.create_node = AsyncMock(return_value=saved_node)

        result_id = await injector.record_consensus_reached(mock_consensus)
        assert result_id == saved_node.id
        assert injector._last_node_id == saved_node.id

    async def test_record_consensus_reached_no_recommended_option(self, injector):
        """record_consensus_reached handles missing recommended_option."""
        mock_consensus = MagicMock()
        mock_consensus.recommended_option = {}
        mock_consensus.agreement = "majority"
        mock_consensus.confidence = "medium"
        mock_consensus.context_hash = None

        saved_node = DecisionNode(
            id=str(uuid.uuid4()),
            case_id=injector.case_id,
            node_type="consensus_reached",
            reasoning="Agreement: majority | Confidence: medium",
            confidence="medium",
            decision_label="Consensus reached: majority agreement",
            context_hash=None,
        )
        injector.repo.create_node = AsyncMock(return_value=saved_node)

        result_id = await injector.record_consensus_reached(mock_consensus)
        assert result_id == saved_node.id

    async def test_record_recommendation_creates_node(self, injector):
        """record_recommendation creates a recommendation_generated node."""
        mock_recommendation = MagicMock()
        mock_recommendation.first_line = {"treatment": "Targeted Therapy"}
        mock_recommendation.second_line = {"treatment": "Immunotherapy"}
        mock_recommendation.clinical_trial = {"name": "NCT000000"}
        mock_recommendation.context_hash = "hash005"

        saved_node = DecisionNode(
            id=str(uuid.uuid4()),
            case_id=injector.case_id,
            node_type="recommendation_generated",
            input_snapshot={
                "first_line": "Targeted Therapy",
                "has_second_line": True,
                "has_clinical_trial": True,
            },
            decision_label="Targeted Therapy",
            context_hash="hash005",
        )
        injector.repo.create_node = AsyncMock(return_value=saved_node)

        result_id = await injector.record_recommendation(mock_recommendation)
        assert result_id == saved_node.id
        assert injector._last_node_id == saved_node.id

    async def test_record_recommendation_no_first_line(self, injector):
        """record_recommendation handles empty first_line gracefully."""
        mock_recommendation = MagicMock()
        mock_recommendation.first_line = {}
        mock_recommendation.second_line = None
        mock_recommendation.clinical_trial = None
        mock_recommendation.context_hash = None

        saved_node = DecisionNode(
            id=str(uuid.uuid4()),
            case_id=injector.case_id,
            node_type="recommendation_generated",
            input_snapshot={
                "first_line": "",
                "has_second_line": False,
                "has_clinical_trial": False,
            },
            decision_label="Recommendation generated",
            context_hash=None,
        )
        injector.repo.create_node = AsyncMock(return_value=saved_node)

        result_id = await injector.record_recommendation(mock_recommendation)
        assert result_id == saved_node.id

    async def test_record_chain_forms_parent_links(self, injector):
        """Multiple record_* calls form a correct parent_id chain."""
        case_id = injector.case_id

        # Setup — simulate creating nodes in sequence
        ctx = MagicMock()
        ctx.model_dump.return_value = {}
        ctx.case_id = case_id
        ctx.context_hash = None

        ev = MagicMock()
        ev.model_dump.return_value = {"total_count": 2, "by_source": {}, "items": ["x", "y"]}
        ev.context_hash = None

        op = MagicMock()
        op.agent_type = "oncologist"
        op.summary = "summary"
        op.confidence = "medium"
        op.context_hash = None

        cs = MagicMock()
        cs.recommended_option = {}
        cs.agreement = "consensus"
        cs.confidence = "low"
        cs.context_hash = None

        rc = MagicMock()
        rc.first_line = {}
        rc.second_line = None
        rc.clinical_trial = None
        rc.context_hash = None

        # Mock repo.create_node to track parent_id chaining
        created_nodes: list[DecisionNode] = []

        async def chain_create(node: DecisionNode) -> DecisionNode:
            saved = DecisionNode(
                id=str(uuid.uuid4()),
                case_id=node.case_id,
                parent_id=node.parent_id,
                node_type=node.node_type,
                input_snapshot=node.input_snapshot,
                evidence_snapshot=node.evidence_snapshot,
                agent_id=node.agent_id,
                agent_type=node.agent_type,
                reasoning=node.reasoning,
                confidence=node.confidence,
                decision_label=node.decision_label,
                context_hash=node.context_hash,
            )
            created_nodes.append(saved)
            return saved

        injector.repo.create_node = AsyncMock(side_effect=chain_create)

        id1 = await injector.record_context_built(ctx)
        id2 = await injector.record_evidence_collected(ev)
        id3 = await injector.record_agent_opinion(op)
        id4 = await injector.record_consensus_reached(cs)
        id5 = await injector.record_recommendation(rc)

        # All IDs should be distinct
        ids = {id1, id2, id3, id4, id5}
        assert len(ids) == 5

        # Verify chain: each node's parent_id equals the previous node's id
        assert created_nodes[0].parent_id is None
        assert created_nodes[1].parent_id == created_nodes[0].id
        assert created_nodes[2].parent_id == created_nodes[1].id
        assert created_nodes[3].parent_id == created_nodes[2].id
        assert created_nodes[4].parent_id == created_nodes[3].id

        # Verify node types
        assert created_nodes[0].node_type == "context_built"
        assert created_nodes[1].node_type == "evidence_collected"
        assert created_nodes[2].node_type == "agent_opinion"
        assert created_nodes[3].node_type == "consensus_reached"
        assert created_nodes[4].node_type == "recommendation_generated"


# ─── Persistence / Session Reload Tests ──────────────────────────────────────


class TestDecisionNodePersistence:
    """Verify persistence and session reload of DecisionNode data.

    Uses a real in-memory SQLite database to ensure data written in one
    session can be read back correctly in a new session.
    """

    @pytest.fixture
    async def db_engine(self):
        """Create an in-memory SQLite engine with all tables."""
        engine = create_async_engine("sqlite+aiosqlite://", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        yield engine
        await engine.dispose()

    @pytest.fixture
    async def session(self, db_engine):
        """Provide a single-use async session.

        The session is closed after each test so the next call creates a
        genuinely new session (session reload simulation).
        """
        session_factory = async_sessionmaker(
            db_engine, class_=AsyncSession, expire_on_commit=False
        )
        async with session_factory() as s:
            yield s

    # ── Helper ───────────────────────────────────────────────────────────
    async def _count_nodes(self, db_engine) -> int:
        """Return the total number of rows in clinical_decision_nodes."""
        from sqlalchemy import func, select

        session_factory = async_sessionmaker(
            db_engine, class_=AsyncSession, expire_on_commit=False
        )
        async with session_factory() as s:
            result = await s.execute(
                select(func.count()).select_from(DecisionNodeModel)
            )
            return result.scalar() or 0

    # ── Tests ─────────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_create_and_reload_decision_node(self, db_engine, session):
        """Write a DecisionNode → commit → new session → read back.

        Every field that was written must be identical after reload.
        """
        # ── Arrange: create node in first session ────────────────────────
        repo = DecisionThreadRepository(session)
        case_id = str(uuid.uuid4())
        original = DecisionNode(
            id="",
            case_id=case_id,
            parent_id=None,
            node_type="context_built",
            input_snapshot={"genome": "GRCh38", "tumor_type": "PTC"},
            evidence_snapshot={},
            agent_id="",
            agent_type="",
            reasoning="Initial context built",
            confidence="high",
            decision_label="Context for PTC",
            context_hash="abc123def456",
        )
        saved = await repo.create_node(original)
        saved_id = saved.id
        saved_timestamp = saved.timestamp

        # Session closes automatically after this test (fixture scope)

        # ── Act: open brand-new session and read back ────────────────────
        session_factory = async_sessionmaker(
            db_engine, class_=AsyncSession, expire_on_commit=False
        )
        async with session_factory() as new_session:
            new_repo = DecisionThreadRepository(new_session)
            reloaded = await new_repo.get_node(saved_id)

        # ── Assert: all fields match original ──────────────────────────
        assert reloaded is not None, "Node should exist after reload"
        assert reloaded.id == saved_id
        assert reloaded.case_id == case_id
        assert reloaded.parent_id is None
        assert reloaded.node_type == "context_built"
        assert reloaded.input_snapshot == {"genome": "GRCh38", "tumor_type": "PTC"}
        assert reloaded.evidence_snapshot == {}
        assert reloaded.reasoning == "Initial context built"
        assert reloaded.confidence == "high"
        assert reloaded.decision_label == "Context for PTC"
        assert reloaded.context_hash == "abc123def456"
        assert reloaded.timestamp == saved_timestamp

        # Also verify persistence via get_case_thread
        async with session_factory() as new_session:
            new_repo = DecisionThreadRepository(new_session)
            thread = await new_repo.get_case_thread(case_id)
        assert len(thread) == 1
        assert thread[0].id == saved_id

    @pytest.mark.asyncio
    async def test_get_case_thread_after_reload(self, db_engine, session):
        """Multiple nodes survive session reload and are returned ordered."""
        # ── Arrange: create 3 nodes in one session ─────────────────────
        repo = DecisionThreadRepository(session)
        case_id = str(uuid.uuid4())
        n1 = await repo.create_node(DecisionNode(
            id="", case_id=case_id, node_type="context_built",
            input_snapshot={"step": 1}, context_hash="h1",
        ))
        n2 = await repo.create_node(DecisionNode(
            id="", case_id=case_id, node_type="evidence_collected",
            parent_id=n1.id, input_snapshot={"step": 2}, context_hash="h2",
        ))
        await repo.create_node(DecisionNode(
            id="", case_id=case_id, node_type="agent_opinion",
            parent_id=n2.id, input_snapshot={"step": 3}, context_hash="h3",
        ))

        # ── Act: reload in new session ──────────────────────────────────
        session_factory = async_sessionmaker(
            db_engine, class_=AsyncSession, expire_on_commit=False
        )
        async with session_factory() as new_session:
            new_repo = DecisionThreadRepository(new_session)
            thread = await new_repo.get_case_thread(case_id)

        # ── Assert ──────────────────────────────────────────────────────
        assert len(thread) == 3
        # Order must be chronological (context_built → evidence_collected → agent_opinion)
        assert [t.node_type for t in thread] == [
            "context_built", "evidence_collected", "agent_opinion",
        ]
        # Parent chain
        assert thread[0].parent_id is None
        assert thread[1].parent_id == thread[0].id
        assert thread[2].parent_id == thread[1].id
        # Context hashes
        assert thread[0].context_hash == "h1"
        assert thread[1].context_hash == "h2"
        assert thread[2].context_hash == "h3"

    @pytest.mark.asyncio
    async def test_clinical_context_roundtrip_via_injector(
        self, db_engine, session
    ):
        """ClinicalContext data survives persistence and reload.

        Create a ClinicalContext → pass through DecisionThreadInjector
        → persist → reload → verify ClinicalContext fields are intact.
        """
        # ── Arrange ──────────────────────────────────────────────────────
        case_id = str(uuid.uuid4())
        ctx = ClinicalContext(
            case_id=case_id,
            patient_id=str(uuid.uuid4()),
            age=45,
            gender="F",
            diagnosis="Papillary thyroid carcinoma",
            stage="II",
            histology="Classic variant",
            cancer_type="PTC",
            oncotree_code="PTC",
            biomarkers=[{"gene": "BRAF", "status": "V600E"}],
            variants=[{"gene_symbol": "BRAF", "hgvs": "c.1799T>A"}],
            ecog_score=1,
            metastatic_sites=["Lymph nodes"],
            recurrence_status="new_diagnosis",
            clinical_notes="Suspicious nodule found during routine checkup",
        )
        ctx.freeze()  # computes context_hash
        assert ctx.context_hash, "context_hash must be set after freeze"

        repo = DecisionThreadRepository(session)
        injector = DecisionThreadInjector(repo, case_id=case_id)

        # ── Act: record context_built ────────────────────────────────────
        node_id = await injector.record_context_built(ctx)

        # ── Reload in new session ────────────────────────────────────────
        session_factory = async_sessionmaker(
            db_engine, class_=AsyncSession, expire_on_commit=False
        )
        async with session_factory() as new_session:
            new_repo = DecisionThreadRepository(new_session)
            reloaded = await new_repo.get_node(node_id)

        # ── Assert ────────────────────────────────────────────────────────
        assert reloaded is not None
        assert reloaded.node_type == "context_built"
        assert reloaded.case_id == case_id
        assert reloaded.context_hash == ctx.context_hash
        assert reloaded.parent_id is None
        # The input_snapshot should contain the ClinicalContext fields
        assert reloaded.input_snapshot["case_id"] == case_id
        assert reloaded.input_snapshot["patient_id"] == ctx.patient_id
        assert reloaded.input_snapshot["age"] == 45
        assert reloaded.input_snapshot["gender"] == "F"
        assert reloaded.input_snapshot["diagnosis"] == "Papillary thyroid carcinoma"
        assert reloaded.input_snapshot["cancer_type"] == "PTC"
        assert reloaded.decision_label == f"Context built for case {case_id}"

    @pytest.mark.asyncio
    async def test_injector_chain_survives_reload(self, db_engine, session):
        """A full injector chain is correctly rebuilt after session reload."""
        # ── Arrange: create a full chain via injector ──────────────────
        case_id = str(uuid.uuid4())

        # Mock pipeline objects
        class FakeContext:
            def __init__(self, cid):
                self.case_id = cid
            context_hash = "ch-ctx"
            def model_dump(self):
                return {"case_id": self.case_id, "patient_id": "p1"}

        class FakeEvidence:
            context_hash = "ch-ev"
            def model_dump(self):
                return {"total_count": 3, "by_source": {"pubmed": 2, "guideline": 1}, "items": ["a", "b", "c"]}

        class FakeOpinion:
            agent_type = "oncologist"
            summary = "BRAF V600E is actionable"
            confidence = "high"
            context_hash = "ch-op"

        class FakeConsensus:
            recommended_option = {"treatment": "Surgery"}
            agreement = "unanimous"
            confidence = "high"
            context_hash = "ch-cs"

        class FakeRecommendation:
            first_line = {"treatment": "Targeted Therapy"}
            second_line = None
            clinical_trial = None
            context_hash = "ch-rec"

        repo = DecisionThreadRepository(session)
        injector = DecisionThreadInjector(repo, case_id=case_id)

        await injector.record_context_built(FakeContext(case_id))
        await injector.record_evidence_collected(FakeEvidence())
        await injector.record_agent_opinion(FakeOpinion())
        await injector.record_consensus_reached(FakeConsensus())
        await injector.record_recommendation(FakeRecommendation())

        # ── Act: reload in new session ─────────────────────────────────
        session_factory = async_sessionmaker(
            db_engine, class_=AsyncSession, expire_on_commit=False
        )
        async with session_factory() as new_session:
            new_repo = DecisionThreadRepository(new_session)
            thread = await new_repo.get_case_thread(case_id)

        # ── Assert ─────────────────────────────────────────────────────
        assert len(thread) == 5

        # Verify chronological order
        node_types = [n.node_type for n in thread]
        assert node_types == [
            "context_built",
            "evidence_collected",
            "agent_opinion",
            "consensus_reached",
            "recommendation_generated",
        ]

        # Verify parent chain
        assert thread[0].parent_id is None
        assert thread[1].parent_id == thread[0].id
        assert thread[2].parent_id == thread[1].id
        assert thread[3].parent_id == thread[2].id
        assert thread[4].parent_id == thread[3].id

        # Verify context_hash chain
        assert thread[0].context_hash == "ch-ctx"
        assert thread[1].context_hash == "ch-ev"
        assert thread[2].context_hash == "ch-op"
        assert thread[3].context_hash == "ch-cs"
        assert thread[4].context_hash == "ch-rec"

        # Verify individual node contents
        assert thread[0].input_snapshot["case_id"] == case_id
        assert thread[1].evidence_snapshot["total_count"] == 3
        assert thread[2].agent_type == "oncologist"
        assert thread[2].reasoning == "BRAF V600E is actionable"
        assert thread[3].decision_label == "Surgery"
        assert thread[4].input_snapshot["first_line"] == "Targeted Therapy"

    @pytest.mark.asyncio
    async def test_persist_node_with_all_nullable_fields(self, db_engine, session):
        """Nodes with NULL values persist correctly and return defaults."""
        repo = DecisionThreadRepository(session)
        case_id = str(uuid.uuid4())

        # Create node with mostly None fields
        node = await repo.create_node(DecisionNode(
            id="",
            case_id=case_id,
            node_type="recommendation_generated",
            parent_id=None,
            input_snapshot={},
            evidence_snapshot={},
            agent_id="",
            agent_type="",
            reasoning="",
            confidence="",
            decision_label="",
            context_hash=None,
        ))

        session_factory = async_sessionmaker(
            db_engine, class_=AsyncSession, expire_on_commit=False
        )
        async with session_factory() as new_session:
            new_repo = DecisionThreadRepository(new_session)
            reloaded = await new_repo.get_node(node.id)

        assert reloaded is not None
        assert reloaded.node_type == "recommendation_generated"
        assert reloaded.parent_id is None
        assert reloaded.context_hash is None or reloaded.context_hash == ""
        assert reloaded.input_snapshot == {}
        assert reloaded.evidence_snapshot == {}
        assert reloaded.agent_id == ""
        assert reloaded.reasoning == ""
        assert reloaded.confidence == ""

    @pytest.mark.asyncio
    async def test_count_across_sessions(self, db_engine, session):
        """Verify row count is consistent across session boundaries."""
        repo = DecisionThreadRepository(session)
        case_id = str(uuid.uuid4())

        # Create 2 nodes
        await repo.create_node(DecisionNode(
            id="", case_id=case_id, node_type="context_built",
        ))
        await repo.create_node(DecisionNode(
            id="", case_id=case_id, node_type="evidence_collected",
        ))

        # Count in a new session
        count = await self._count_nodes(db_engine)
        assert count == 2

        # Add a third in a new session
        session_factory = async_sessionmaker(
            db_engine, class_=AsyncSession, expire_on_commit=False
        )
        async with session_factory() as s2:
            r2 = DecisionThreadRepository(s2)
            await r2.create_node(DecisionNode(
                id="", case_id=case_id, node_type="agent_opinion",
            ))

        count = await self._count_nodes(db_engine)
        assert count == 3
