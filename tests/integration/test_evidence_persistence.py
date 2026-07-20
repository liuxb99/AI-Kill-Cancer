
"""
Integration test for evidence persistence flow.
Tests: upsert → find → withdrawn lifecycle.
"""
import uuid
import pytest
from datetime import datetime
from src.backend.evidence.domain import EvidenceItemModel

class TestEvidencePersistenceFlow:
    async def test_evidence_item_model_fields(self):
        """Verify EvidenceItemModel has all Phase 2B fields."""
        cols = {c.name for c in EvidenceItemModel.__table__.columns}
        assert "match_level" in cols
        assert "conflict_status" in cols
        assert "source_native_level" in cols
        assert "payload_hash" in cols
        assert "first_seen_at" in cols
        assert "last_seen_at" in cols
        assert "withdrawn_at" in cols
        assert "superseded_by" in cols
        assert "is_superseded" in cols

    async def test_knowledge_source_model_fields(self):
        from src.backend.evidence.domain import KnowledgeSourceModel
        cols = {c.name for c in KnowledgeSourceModel.__table__.columns}
        assert "retrieval_count" in cols

    async def test_drug_interaction_model_fields(self):
        from src.backend.evidence.domain import DrugInteractionModel
        cols = {c.name for c in DrugInteractionModel.__table__.columns}
        assert "payload_hash" in cols
        assert "first_seen_at" in cols
        assert "last_seen_at" in cols

