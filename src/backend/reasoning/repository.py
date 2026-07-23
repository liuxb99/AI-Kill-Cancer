"""
ReasoningRunRepository — persists reasoning runs with full metadata.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Float, Integer, String, select

from src.backend.database.models import Base as DBBase
from src.backend.database.models import CompatUUID


class ReasoningRunModel(DBBase):
    """Persistent storage for a clinical reasoning run."""
    __tablename__ = "domain_reasoning_runs"

    id = Column(CompatUUID, primary_key=True, default=uuid.uuid4)
    case_id = Column(String(36), nullable=True, index=True)
    variant_id = Column(String(36), nullable=True, index=True)
    status = Column(String(32), nullable=False, default="pending")

    # LLM metadata
    provider = Column(String(64), nullable=True)
    model = Column(String(128), nullable=True)
    model_version = Column(String(64), nullable=True)
    prompt_template_version = Column(String(32), nullable=True)
    temperature = Column(Float, nullable=True)
    seed = Column(Integer, nullable=True)

    # Hashing for reproducibility
    input_hash = Column(String(64), nullable=True)
    output_hash = Column(String(64), nullable=True)
    context_hash = Column(String(64), nullable=True)

    # Performance
    token_usage = Column(JSON, default=dict)
    latency_ms = Column(Float, nullable=True)

    # Versioning
    git_commit = Column(String(64), nullable=True)

    # Results
    reasoning_data = Column(JSON, nullable=True)
    validation_result = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ReasoningRunRepository:
    """Repository for ReasoningRunModel."""

    def __init__(self, db):
        self.db = db

    async def create(self, **kwargs) -> ReasoningRunModel:
        instance = ReasoningRunModel(**kwargs)
        self.db.add(instance)
        await self.db.commit()
        await self.db.refresh(instance)
        return instance

    async def get(self, run_id: uuid.UUID) -> ReasoningRunModel | None:
        stmt = select(ReasoningRunModel).where(ReasoningRunModel.id == run_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, run_id: uuid.UUID, **kwargs) -> ReasoningRunModel | None:
        instance = await self.get(run_id)
        if not instance:
            return None
        for field, value in kwargs.items():
            if hasattr(instance, field) and value is not None:
                setattr(instance, field, value)
        instance.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(instance)
        return instance
