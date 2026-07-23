"""
Real SQLAlchemy transaction atomicity tests.

Uses direct SQLAlchemy AsyncSession (in-memory SQLite) to verify that
business data + audit are committed atomically.

- Success path: normal insert flow.
- Rollback path: an event listener on the session raises before any
  AuditLogModel insert, simulating a database constraint violation.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import String, event, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.backend.database.models import Base
from src.backend.domain.audit_log import AuditLogModel
from src.backend.workbench.repository import TumorBoardRepository, TumorBoardReviewModel, WorkbenchNoteModel

# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
async def ses_engine():
    """Normal session + engine — allows all audit inserts."""
    AuditLogModel.__table__.columns["action"].type = String(64)
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session, engine, maker
    await engine.dispose()


@pytest.fixture
async def fail_ses_engine():
    """
    Session with an event listener that rejects any AuditLogModel insert.
    Simulates a database constraint violation during flush/commit.
    """
    AuditLogModel.__table__.columns["action"].type = String(64)
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        def reject_audit(session, ctx, instances):
            for obj in session.new:
                if isinstance(obj, AuditLogModel):
                    raise ValueError("Simulated audit constraint violation")
        event.listen(session.sync_session, "before_flush", reject_audit)
        yield session, engine, maker
    await engine.dispose()


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_note(case_id: str, content: str = "Test note") -> WorkbenchNoteModel:
    return WorkbenchNoteModel(
        case_id=case_id,
        user_id="test-user",
        content=content,
        note_type="general",
    )


def _make_audit(action: str, **details) -> AuditLogModel:
    return AuditLogModel(
        patient_id=None,
        actor="test-user",
        action=action,
        resource_type="workbench_note",
        resource_id=str(uuid.uuid4()),
        details=details,
    )


async def _fresh_count(engine, maker, model_cls) -> int:
    """Count rows in a fresh session."""
    async with maker() as fresh:
        result = await fresh.execute(select(model_cls))
        return len(result.scalars().all())


# ═══════════════════════════════════════════════════════════════════════════════
# P0-1: Note Create single commit
# ═══════════════════════════════════════════════════════════════════════════════


class TestNoteCreateSingleCommit:
    """P0-1: flush → get real ID → single commit."""

    async def test_flush_gets_real_note_id(self, ses_engine):
        """After flush, note.id should be assigned."""
        session, _, _ = ses_engine
        note = _make_note(case_id=str(uuid.uuid4()))
        session.add(note)
        await session.flush()
        assert note.id is not None, "flush did not assign note.id"
        assert isinstance(note.id, uuid.UUID)

    async def test_audit_contains_real_note_id(self, ses_engine):
        """After single commit, audit details should contain the real note_id."""
        session, _, _ = ses_engine
        case_id = str(uuid.uuid4())
        note = _make_note(case_id=case_id)
        session.add(note)
        await session.flush()

        real_note_id = str(note.id)
        audit = _make_audit("note_created", note_id=real_note_id, case_id=case_id)
        session.add(audit)
        await session.commit()

        result = await session.execute(
            select(AuditLogModel).where(AuditLogModel.action == "note_created")
        )
        persisted_audit = result.scalar_one_or_none()
        assert persisted_audit is not None
        assert persisted_audit.details.get("note_id") == real_note_id

    async def test_only_one_commit_call(self, ses_engine):
        """The entire operation should call commit exactly once."""
        session, _, _ = ses_engine
        case_id = str(uuid.uuid4())
        note = _make_note(case_id=case_id)
        session.add(note)
        await session.flush()
        audit = _make_audit("note_created", note_id=str(note.id), case_id=case_id)
        session.add(audit)
        await session.commit()

        notes = (await session.execute(select(WorkbenchNoteModel))).scalars().all()
        assert len(notes) == 1
        audits = (await session.execute(select(AuditLogModel))).scalars().all()
        assert len(audits) == 1

    async def test_audit_failure_prevents_note_persist(self, fail_ses_engine):
        """When audit insert fails, note should NOT exist in DB."""
        session, engine, maker = fail_ses_engine
        case_id = str(uuid.uuid4())
        note = _make_note(case_id=case_id)
        session.add(note)
        await session.flush()

        audit = _make_audit("note_created", note_id=str(note.id), case_id=case_id)
        session.add(audit)

        with pytest.raises(ValueError, match="Simulated audit constraint violation"):
            await session.commit()

        await session.rollback()

        # Verify note does NOT exist in a fresh session
        count = await _fresh_count(engine, maker, WorkbenchNoteModel)
        assert count == 0, f"Expected 0 notes after rollback, got {count}"

    async def test_commit_failure_removes_note_and_audit(self, fail_ses_engine):
        """If commit fails, neither note nor audit persist."""
        session, engine, maker = fail_ses_engine
        case_id = str(uuid.uuid4())
        note = _make_note(case_id=case_id)
        session.add(note)
        await session.flush()

        audit = _make_audit("note_created", note_id=str(note.id), case_id=case_id)
        session.add(audit)

        with pytest.raises(ValueError):
            await session.commit()
        await session.rollback()

        assert await _fresh_count(engine, maker, WorkbenchNoteModel) == 0
        assert await _fresh_count(engine, maker, AuditLogModel) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# P0-1: Note Update & Delete rollback
# ═══════════════════════════════════════════════════════════════════════════════


class TestNoteUpdateDeleteRollback:
    """Note update/delete rollback on audit failure."""

    async def _create_note(self, session, case_id: str, content: str = "Original"):
        note = _make_note(case_id=case_id, content=content)
        session.add(note)
        audit = _make_audit("note_create", note_id=str(uuid.uuid4()), case_id=case_id)
        session.add(audit)
        await session.commit()
        return note.id

    async def test_note_update_rolls_back_on_audit_failure(self, ses_engine):
        """Failed update audit should not change the existing note."""
        session, _, _ = ses_engine
        case_id = str(uuid.uuid4())
        note_id = await self._create_note(session, case_id)

        # Attach reject listener
        def reject_audit(s, ctx, instances):
            for obj in s.new:
                if isinstance(obj, AuditLogModel):
                    raise ValueError("Simulated audit constraint violation")
        event.listen(session.sync_session, "before_flush", reject_audit)

        session.expire_all()
        result = await session.execute(
            select(WorkbenchNoteModel).where(WorkbenchNoteModel.id == note_id)
        )
        note = result.scalar_one()
        note.content = "Modified content"

        update_audit = _make_audit("note_updated", note_id=str(note_id), case_id=case_id)
        session.add(update_audit)

        with pytest.raises(ValueError):
            await session.commit()
        await session.rollback()

        session.expire_all()
        result = await session.execute(
            select(WorkbenchNoteModel).where(WorkbenchNoteModel.id == note_id)
        )
        reloaded = result.scalar_one()
        assert reloaded.content == "Original", f"Expected 'Original' but got '{reloaded.content}'"

    async def test_note_delete_rolls_back_on_audit_failure(self, ses_engine):
        """Failed delete audit should leave the note intact."""
        session, _, _ = ses_engine
        case_id = str(uuid.uuid4())
        note_id = await self._create_note(session, case_id)

        def reject_audit(s, ctx, instances):
            for obj in s.new:
                if isinstance(obj, AuditLogModel):
                    raise ValueError("Simulated audit constraint violation")
        event.listen(session.sync_session, "before_flush", reject_audit)

        session.expire_all()
        result = await session.execute(
            select(WorkbenchNoteModel).where(WorkbenchNoteModel.id == note_id)
        )
        await session.delete(result.scalar_one())

        del_audit = _make_audit("note_deleted", note_id=str(note_id), case_id=case_id)
        session.add(del_audit)

        with pytest.raises(ValueError):
            await session.commit()
        await session.rollback()

        session.expire_all()
        result = await session.execute(
            select(WorkbenchNoteModel).where(WorkbenchNoteModel.id == note_id)
        )
        assert result.scalar_one_or_none() is not None, "Note was deleted despite rollback"


# ═══════════════════════════════════════════════════════════════════════════════
# P0-2: Tumor Board transaction boundary
# ═══════════════════════════════════════════════════════════════════════════════


class TestTumorBoardTransaction:
    """Repository only flushes — caller controls commit."""

    async def test_create_review_requires_external_commit(self, ses_engine):
        """Caller must commit — without it, nothing persists."""
        session, engine, maker = ses_engine
        repo = TumorBoardRepository(session)
        review = await repo.create_review(
            case_id=str(uuid.uuid4()),
            reviewer_id="dr-x",
            reviewer_name="Dr. X",
        )
        assert review.id is not None

        await session.rollback()

        count = await _fresh_count(engine, maker, TumorBoardReviewModel)
        assert count == 0, "Review survived without commit"

    async def test_review_vote_audit_all_committed(self, ses_engine):
        """create_review + vote + audit: one commit persists all."""
        session, _, _ = ses_engine
        repo = TumorBoardRepository(session)
        case_id = str(uuid.uuid4())

        review = await repo.create_review(case_id=case_id, reviewer_id="dr-y")
        review_id = review.id

        vote_data = {"vote": "approve", "rationale": "Good evidence", "reviewer_id": "dr-y"}
        await repo.add_comment(review_id, vote_data)

        audit = _make_audit("tumor_board_vote", case_id=case_id, vote="approve")
        session.add(audit)
        await session.commit()

        # Verify review
        result = await session.execute(
            select(TumorBoardReviewModel).where(TumorBoardReviewModel.id == review_id)
        )
        assert result.scalar_one_or_none() is not None

        # Verify audit
        result = await session.execute(
            select(AuditLogModel).where(AuditLogModel.action == "tumor_board_vote")
        )
        assert result.scalar_one_or_none() is not None

    async def test_vote_failure_rolls_back_review(self, fail_ses_engine):
        """When audit fails, review + vote should not exist."""
        session, engine, maker = fail_ses_engine
        repo = TumorBoardRepository(session)
        case_id = str(uuid.uuid4())

        review = await repo.create_review(case_id=case_id, reviewer_id="dr-z")
        review_id = review.id
        vote_data = {"vote": "approve", "rationale": "Test", "reviewer_id": "dr-z"}
        await repo.add_comment(review_id, vote_data)

        audit = _make_audit("tumor_board_vote", case_id=case_id, vote="approve")
        session.add(audit)

        with pytest.raises(ValueError):
            await session.commit()
        await session.rollback()

        count = await _fresh_count(engine, maker, TumorBoardReviewModel)
        assert count == 0, f"Expected 0 reviews, got {count}"

    async def test_comment_failure_rolls_back_review(self, fail_ses_engine):
        """When audit fails, comment + review should not exist."""
        session, engine, maker = fail_ses_engine
        repo = TumorBoardRepository(session)
        case_id = str(uuid.uuid4())

        review = await repo.create_review(case_id=case_id, reviewer_id="dr-w")
        review_id = review.id
        comment_data = {"content": "Test comment", "user_id": "dr-w"}
        await repo.add_comment(review_id, comment_data)

        audit = _make_audit("tumor_board_comment", case_id=case_id)
        session.add(audit)

        with pytest.raises(ValueError):
            await session.commit()
        await session.rollback()

        count = await _fresh_count(engine, maker, TumorBoardReviewModel)
        assert count == 0
