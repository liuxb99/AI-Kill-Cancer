"""
ReasoningContextBuilder — builds frozen context from evidence, ranking, and knowledge snapshots.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ReasoningContext:
    """A frozen context snapshot for reasoning."""
    def __init__(self):
        self.case_snapshot: dict = {}
        self.variant_snapshot: dict = {}
        self.evidence_snapshot: list[dict] = []
        self.ranking_snapshot: dict | None = None
        self.knowledge_snapshot: dict = {}
        self.built_at: str = ""
        self.context_hash: str = ""

    def freeze(self) -> str:
        """Freeze the context and compute its hash."""
        self.built_at = datetime.utcnow().isoformat()
        payload = {
            "case": self.case_snapshot,
            "variant": self.variant_snapshot,
            "evidence": self.evidence_snapshot,
            "ranking": self.ranking_snapshot,
            "knowledge": self.knowledge_snapshot,
            "built_at": self.built_at,
        }
        self.context_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode()
        ).hexdigest()
        return self.context_hash


class ReasoningContextBuilder:
    """
    Builds frozen context for a reasoning run from evidence, ranking, and knowledge.
    """

    async def build(self, variant_data: dict | None = None,
                     evidence_items: list[dict] | None = None,
                     ranking_result: dict | None = None,
                     knowledge_data: dict | None = None,
                     case_data: dict | None = None) -> ReasoningContext:
        """Build a frozen context from provided snapshots."""
        context = ReasoningContext()
        context.variant_snapshot = variant_data or {}
        context.evidence_snapshot = evidence_items or []
        context.ranking_snapshot = ranking_result
        context.knowledge_snapshot = knowledge_data or {}
        context.case_snapshot = case_data or {}
        context.freeze()
        return context
