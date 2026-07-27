"""Clinical Graph Event Schema — Versioned DTO for Outbox Events."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class GraphAggregateType(str, Enum):
    PATIENT = "patient"
    VARIANT = "variant"
    EVIDENCE = "evidence"
    RECOMMENDATION = "recommendation"
    CLINICAL_DECISION = "clinical_decision"
    TUMOR_BOARD_CONSENSUS = "tumor_board_consensus"
    SPECIALIST_OPINION = "specialist_opinion"
    DRUG = "drug"


class GraphEventType(str, Enum):
    PATIENT_CREATED = "patient.created"
    PATIENT_UPDATED = "patient.updated"
    RECOMMENDATION_CREATED = "recommendation.created"
    RECOMMENDATION_UPDATED = "recommendation.updated"
    CLINICAL_DECISION_CREATED = "clinical_decision.created"
    CLINICAL_DECISION_UPDATED = "clinical_decision.updated"
    TUMOR_BOARD_CONSENSUS_CREATED = "tumor_board_consensus.created"
    TUMOR_BOARD_CONSENSUS_UPDATED = "tumor_board_consensus.updated"


# 敏感字段列表（不得出现在 payload 中）
SENSITIVE_FIELDS = frozenset({
    "password_hash", "password", "refresh_token", "access_token",
    "private_key", "database_url", "db_url", "token",
})


class ClinicalGraphEvent(BaseModel):
    """版本化事件 DTO — 用于 Outbox 与 Graph Adapter 之间交换。"""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: GraphEventType
    schema_version: int = Field(default=1, ge=1)
    aggregate_type: GraphAggregateType
    aggregate_id: str
    occurred_at: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    actor_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)

    def validate_payload_sensitive_fields(self) -> bool:
        """检查 payload 中是否包含敏感字段。"""
        return not bool(SENSITIVE_FIELDS & set(self.payload.keys()))


__all__ = [
    "ClinicalGraphEvent",
    "GraphAggregateType",
    "GraphEventType",
    "SENSITIVE_FIELDS",
]
