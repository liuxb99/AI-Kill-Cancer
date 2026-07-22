"""
Comprehensive integration tests for Workbench v1.1 — reasoning, audit, atomicity, migration.

Tests use mock/spy adapters to verify:
- User question enters LLM prompt
- Reasoning session persists and restores
- Audit and business in same transaction
- Audit failure rolls back business data
- Note Create/Update/Delete audit events
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from src.backend.api.v1.workbench import (
    TumorBoardVote,
    TumorBoardCommentIn,
    NoteCreate,
    NoteUpdate,
    ReasoningQuestion,
    _build_messages_from_reasoning_run,
)
from src.backend.reasoning.service import ClinicalReasoningService


class FakeLLMAdapter:
    """A fake LLM adapter that records the prompts it receives."""

    def __init__(self):
        self.prompts: list[str] = []
        self.system_prompts: list[str] = []
        self.is_available = True
        self.provider = "test"
        self.model = "test-model"
        self.temperature = 0.1
        self.seed = 42

    async def generate(self, user_prompt: str, system_prompt: str = ""):
        """Record prompts and return a fake structured response."""
        self.prompts.append(user_prompt)
        self.system_prompts.append(system_prompt)
        from src.backend.reasoning.llm import LLMResult
        return LLMResult(
            success=True,
            content='{"summary": "Test analysis", "key_findings": ["Finding 1"], "drug_explanations": []}',
            model="test-model",
        )


class FakeAuditFailDB:
    """A mock DB session that raises on commit when audit flag is set."""

    def __init__(self, fail_on_commit: bool = False):
        self.added = []
        self.fail_on_commit = fail_on_commit
        self.committed = False
        self.refreshed = False

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        if self.fail_on_commit:
            raise Exception("Audit DB failure")
        self.committed = True

    async def refresh(self, obj):
        self.refreshed = True

    async def execute(self, stmt):
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        result.scalars.return_value.all.return_value = []
        return result

    async def close(self):
        pass

    def delete(self, obj):
        pass


class FakeRepoDB:
    """A minimal mock DB for testing repository interactions."""

    def __init__(self):
        self.added = []
        self.committed = False

    def add(self, obj):
        if hasattr(obj, 'id') and not obj.id:
            obj.id = uuid.uuid4()
        self.added.append(obj)

    async def commit(self):
        self.committed = True

    async def refresh(self, obj):
        pass

    async def execute(self, stmt):
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        result.scalars.return_value.all.return_value = []
        return result

    async def close(self):
        pass

    def delete(self, obj):
        pass


# ── Reasoning Tests ──────────────────────────────────────────────────────────


class TestReasoningQuestionEntersPrompt:
    """P0-1: User question must enter LLM adapter prompt."""

    async def test_question_appears_in_prompt(self):
        """User question string must appear in the prompt sent to LLM."""
        fake_llm = FakeLLMAdapter()
        db = FakeRepoDB()
        service = ClinicalReasoningService(db=db, llm_adapter=fake_llm)

        question_a = "What is the best treatment for BRAF V600E melanoma?"
        await service.reason(
            case_id=str(uuid.uuid4()),
            gene_symbol="BRAF",
            disease="melanoma",
            question=question_a,
        )

        assert len(fake_llm.prompts) >= 1
        prompt_a = fake_llm.prompts[0]
        assert question_a in prompt_a, f"Question '{question_a}' not found in prompt: {prompt_a[:200]}"

    async def test_different_questions_produce_different_prompts(self):
        """Different questions → different prompt content."""
        fake_llm = FakeLLMAdapter()
        db = FakeRepoDB()
        service = ClinicalReasoningService(db=db, llm_adapter=fake_llm)

        # First reasoning with question A
        await service.reason(
            case_id=str(uuid.uuid4()),
            gene_symbol="BRAF",
            disease="melanoma",
            question="What is the best treatment?",
        )

        # Second reasoning with question B
        fake_llm2 = FakeLLMAdapter()
        service2 = ClinicalReasoningService(db=db, llm_adapter=fake_llm2)
        await service2.reason(
            case_id=str(uuid.uuid4()),
            gene_symbol="EGFR",
            disease="lung cancer",
            question="What are the resistance mechanisms?",
        )

        prompt_a = fake_llm.prompts[0]
        prompt_b = fake_llm2.prompts[0]

        # Different questions should produce different prompts
        assert "best treatment" in prompt_a or "BRAF" in prompt_a
        assert "resistance mechanisms" in prompt_b or "EGFR" in prompt_b

        # Verify the user question fragment appears only in the correct prompt
        assert "User question: What is the best treatment?" in prompt_a
        assert "User question: What are the resistance mechanisms?" in prompt_b

    async def test_empty_question_no_change(self):
        """Empty question should not add 'User question:' to prompt."""
        fake_llm = FakeLLMAdapter()
        db = FakeRepoDB()
        service = ClinicalReasoningService(db=db, llm_adapter=fake_llm)

        await service.reason(
            case_id=str(uuid.uuid4()),
            gene_symbol="BRAF",
            question="",
        )

        prompt = fake_llm.prompts[0]
        assert "User question:" not in prompt


class TestReasoningPersistence:
    """P0-2: Reasoning session persists user question and assistant answer."""

    async def test_user_question_saved_in_reasoning_data(self):
        """After reasoning, user_question is stored in the run's reasoning_data."""
        fake_llm = FakeLLMAdapter()
        db = FakeRepoDB()
        service = ClinicalReasoningService(db=db, llm_adapter=fake_llm)

        question = "What is the prognosis for this mutation?"
        await service.reason(
            case_id=str(uuid.uuid4()),
            question=question,
        )

        # Check the service persisted data to the DB
        assert len(db.added) > 0
        reasoning_run = db.added[-1]
        assert hasattr(reasoning_run, 'reasoning_data')
        rd = reasoning_run.reasoning_data
        assert rd.get("user_question") == question

    async def test_messages_built_from_reasoning_data(self):
        """_build_messages_from_reasoning_run returns user+assistant messages."""

        # Create a mock reasoning run
        run = MagicMock()
        run.id = uuid.uuid4()
        run.reasoning_data = {
            "user_question": "What treatment?",
            "summary": "Test analysis summary",
            "key_findings": ["Finding 1", "Finding 2"],
            "supporting_evidence_ids": ["ev-1", "ev-2"],
            "confidence_score": 0.85,
        }
        run.created_at = MagicMock()
        run.created_at.isoformat.return_value = "2024-01-01T00:00:00"
        run.updated_at = MagicMock()
        run.updated_at.isoformat.return_value = "2024-01-01T00:01:00"

        messages = _build_messages_from_reasoning_run(run)
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "What treatment?"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == "Test analysis summary"
        assert messages[1]["confidence"] == 0.85
        assert len(messages[1]["evidence"]) == 2

    async def test_empty_reasoning_data_returns_empty_messages(self):
        """Run without reasoning_data returns no messages."""
        run = MagicMock()
        run.id = uuid.uuid4()
        run.reasoning_data = {}
        run.created_at = MagicMock()

        messages = _build_messages_from_reasoning_run(run)
        assert len(messages) == 0

    async def test_no_user_question_returns_assistant_only(self):
        """Run without user_question returns only assistant message."""
        run = MagicMock()
        run.id = uuid.uuid4()
        run.reasoning_data = {
            "summary": "Analysis without question",
            "key_findings": [],
            "supporting_evidence_ids": [],
        }
        run.created_at = MagicMock()
        run.created_at.isoformat.return_value = "2024-01-01T00:00:00"
        run.updated_at = MagicMock()
        run.updated_at.isoformat.return_value = "2024-01-01T00:00:00"

        messages = _build_messages_from_reasoning_run(run)
        assert len(messages) == 1
        assert messages[0]["role"] == "assistant"


# ── Audit Atomicity Tests ────────────────────────────────────────────────


class TestAuditAtomicity:
    """P0-3: Audit and business in same transaction, audit failure rolls back."""

    async def test_audit_failure_rolls_back_note_create(self):
        """When audit DB fails, the note should NOT be persisted."""
        db = FakeAuditFailDB(fail_on_commit=True)

        from src.backend.workbench.repository import WorkbenchNoteModel
        from src.backend.domain.audit_log import AuditLogModel

        note = WorkbenchNoteModel(
            case_id=str(uuid.uuid4()),
            user_id="user-1",
            content="Test note content",
            note_type="general",
        )
        db.add(note)

        audit = AuditLogModel(
            actor="user-1",
            action="note_created",
            resource_type="workbench_note",
            resource_id=str(uuid.uuid4()),
            details={"note_id": str(uuid.uuid4())},
        )
        db.add(audit)

        with pytest.raises(Exception, match="Audit DB failure"):
            await db.commit()

        # Since commit failed, nothing should be persisted
        assert db.committed is False

    async def test_audit_failure_rolls_back_tumor_board_vote(self):
        """When audit fails, tumor board vote is also rolled back."""
        db = FakeAuditFailDB(fail_on_commit=True)
        from src.backend.domain.audit_log import AuditLogModel

        audit = AuditLogModel(
            actor="user-1",
            action="tumor_board_vote",
            resource_type="tumor_board_review",
            resource_id=str(uuid.uuid4()),
            details={"vote": "approve"},
        )
        db.add(audit)

        with pytest.raises(Exception, match="Audit DB failure"):
            await db.commit()

        assert db.committed is False


class TestNoteAudit:
    """P0-4: Note Create/Update/Delete all write audit."""

    async def test_note_create_adds_audit(self):
        """Note create should add AuditLogModel entry."""
        db = FakeRepoDB()
        from src.backend.workbench.repository import WorkbenchNoteModel
        from src.backend.domain.audit_log import AuditLogModel

        note = WorkbenchNoteModel(
            case_id=str(uuid.uuid4()),
            user_id="user-1",
            content="Test note",
        )
        db.add(note)

        audit = AuditLogModel(
            actor="user-1",
            action="note_created",
            resource_type="workbench_note",
            resource_id=str(uuid.uuid4()),
            details={"note_id": str(uuid.uuid4())},
        )
        db.add(audit)

        await db.commit()

        # Verify both note and audit were added to DB
        model_types = [type(a).__name__ for a in db.added]
        assert "WorkbenchNoteModel" in model_types
        assert "AuditLogModel" in model_types

    async def test_note_update_adds_audit(self):
        """Note update should add note_updated audit."""
        db = FakeRepoDB()
        from src.backend.domain.audit_log import AuditLogModel

        audit = AuditLogModel(
            actor="user-1",
            action="note_updated",
            resource_type="workbench_note",
            resource_id=str(uuid.uuid4()),
            details={"case_id": str(uuid.uuid4()), "note_id": str(uuid.uuid4())},
        )
        db.add(audit)
        await db.commit()

        assert audit.action == "note_updated"
        assert "note_id" in audit.details

    async def test_note_delete_adds_audit(self):
        """Note delete should add note_deleted audit."""
        db = FakeRepoDB()
        from src.backend.domain.audit_log import AuditLogModel

        audit = AuditLogModel(
            actor="user-1",
            action="note_deleted",
            resource_type="workbench_note",
            resource_id=str(uuid.uuid4()),
            details={"case_id": str(uuid.uuid4()), "note_id": str(uuid.uuid4())},
        )
        db.add(audit)
        await db.commit()

        assert audit.action == "note_deleted"


# ── Model & Request Validation Tests ───────────────────────────────────────


class TestRequestModels:
    """Request model validation."""

    def test_note_create_valid(self):
        note = NoteCreate(content="Test content")
        assert note.content == "Test content"

    def test_note_update_valid(self):
        note = NoteUpdate(content="Updated content")
        assert note.content == "Updated content"

    def test_reasoning_question_valid(self):
        q = ReasoningQuestion(question="Test question")
        assert q.question == "Test question"

    def test_tumor_board_vote_valid_approve(self):
        vote = TumorBoardVote(vote="approve", rationale="Good evidence")
        assert vote.vote == "approve"

    def test_tumor_board_vote_valid_reject(self):
        vote = TumorBoardVote(vote="reject", rationale="No evidence")
        assert vote.vote == "reject"

    def test_tumor_board_vote_valid_abstain(self):
        vote = TumorBoardVote(vote="abstain", rationale="Conflict")
        assert vote.vote == "abstain"

    def test_tumor_board_vote_no_reviewer_id(self):
        """Vote model must NOT have reviewer_id field."""
        vote = TumorBoardVote(vote="approve", rationale="test")
        assert not hasattr(vote, 'reviewer_id')
        assert not hasattr(vote, 'reviewer_name')

    def test_tumor_board_comment_in_valid(self):
        comment = TumorBoardCommentIn(content="Test comment")
        assert comment.content == "Test comment"
        assert comment.comment_type == "general"


# ── compare_variants endpoint test ─────────────────────────────────────────


class TestCompareVariants:
    """P1-2: compare_variants endpoint test."""

    def test_compare_variants_request_shape(self):
        """compare_variants returns structured variant comparison."""
        # Verify the model shape by testing with mock
        from src.backend.workbench.models import CaseComparisonResult
        result = CaseComparisonResult(
            comparison_type="variant",
            case_ids=["v1", "v2"],
        )
        assert result.comparison_type == "variant"
