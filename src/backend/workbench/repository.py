"""
Workbench repository — Tumor Board workflow persistence.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, String, Text, select

from src.backend.database.models import Base as DBBase
from src.backend.database.models import CompatUUID


class TumorBoardReviewModel(DBBase):
    """Persistent storage for tumor board reviews."""
    __tablename__ = "domain_tumor_board_reviews"

    id = Column(CompatUUID, primary_key=True, default=uuid.uuid4)
    case_id = Column(String(36), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="draft")
    reviewer_id = Column(String(64), nullable=True)
    reviewer_name = Column(String(128), nullable=True)
    decision = Column(String(32), nullable=True)
    comments = Column(JSON, default=list)
    decision_log = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class WorkbenchNoteModel(DBBase):
    """Persistent storage for workbench notes."""
    __tablename__ = "domain_workbench_notes"

    id = Column(CompatUUID, primary_key=True, default=uuid.uuid4)
    case_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(64), nullable=True)
    content = Column(Text, nullable=False)
    note_type = Column(String(32), default="general")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class TumorBoardRepository:
    """Repository for Tumor Board workflow."""

    def __init__(self, db):
        self.db = db

    async def create_review(self, case_id: str, reviewer_id: str = "",
                              reviewer_name: str = "") -> TumorBoardReviewModel:
        review = TumorBoardReviewModel(
            case_id=case_id,
            status="draft",
            reviewer_id=reviewer_id,
            reviewer_name=reviewer_name,
        )
        self.db.add(review)
        await self.db.flush()
        await self.db.refresh(review)
        return review

    async def get_review(self, review_id: uuid.UUID) -> TumorBoardReviewModel | None:
        stmt = select(TumorBoardReviewModel).where(TumorBoardReviewModel.id == review_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_reviews_by_case(self, case_id: str) -> list[TumorBoardReviewModel]:
        stmt = (select(TumorBoardReviewModel)
                .where(TumorBoardReviewModel.case_id == case_id)
                .order_by(TumorBoardReviewModel.created_at.desc()))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_status(self, review_id: uuid.UUID, status: str,
                             decision: str = "") -> TumorBoardReviewModel | None:
        review = await self.get_review(review_id)
        if not review:
            return None
        review.status = status
        if decision:
            review.decision = decision
        log_entry = {"status": status, "decision": decision, "timestamp": datetime.utcnow().isoformat()}
        current_log = list(review.decision_log or [])
        current_log.append(log_entry)
        review.decision_log = current_log
        review.updated_at = datetime.utcnow()
        await self.db.flush()
        await self.db.refresh(review)
        return review

    async def add_comment(self, review_id: uuid.UUID, comment: dict) -> TumorBoardReviewModel | None:
        review = await self.get_review(review_id)
        if not review:
            return None
        current_comments = list(review.comments or [])
        current_comments.append(comment)
        review.comments = current_comments
        await self.db.flush()
        await self.db.refresh(review)
        return review
