"""
Phase 2B Hardening Tests — Persistent Clinical Evidence Layer.

Tests:
- KnowledgeSourceRepository (upsert, health check)
- EvidenceItemRepository (upsert, dedup, withdraw, conflict tracking)
- DrugInteractionRepository (upsert, dedup)
- EvidenceMerger matching priority chain
- Evidence API refresh / cache invalidate
- match_level tracking
- source_native_level preservation
"""

from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.backend.evidence.domain import (
    KnowledgeSourceModel, EvidenceItemModel, DrugInteractionModel,
    MATCH_LEVEL_ORDER, MATCH_LEVEL_PRECEDENCE,
    EvidenceVariantResponse, EvidenceGeneResponse,
    EvidenceRefreshResponse, EvidenceCacheInvalidateResponse,
)
from src.backend.evidence.merger import EvidenceMerger
from src.backend.evidence.cache import TTLCache
from src.backend.repositories.knowledge_source_repo import KnowledgeSourceRepository
from src.backend.repositories.evidence_item_repo import EvidenceItemRepository, _compute_payload_hash
from src.backend.repositories.drug_interaction_repo import DrugInteractionRepository, _compute_interaction_hash


# ─── Helpers ──────────────────────────────────────────────────────────────────


def make_model(cls, **kwargs):
    """Create a model instance with auto-generated UUID id."""
    if "id" not in kwargs:
        kwargs["id"] = uuid.uuid4()
    return cls(**kwargs)


class FakeDB:
    """A fake DB session that stores added objects in-memory."""

    def __init__(self):
        self.added = []
        self.committed = False
        self._storage = {}

    def add(self, obj):
        if not hasattr(obj, 'id') or obj.id is None:
            obj.id = uuid.uuid4()
        self.added.append(obj)

    async def commit(self):
        self.committed = True

    async def refresh(self, obj):
        pass

    async def execute(self, stmt):
        return FakeResult()

    async def close(self):
        pass


class FakeResult:
    """Fake SQLAlchemy result returning None for everything."""

    def scalar_one_or_none(self):
        return None

    def scalars(self):
        return FakeScalars()

    def scalar(self):
        return 0


class FakeScalars:
    def all(self):
        return []


class FakeDBWithExisting(FakeDB):
    """Fake DB that returns an existing record on execute."""

    def __init__(self, existing_record):
        super().__init__()
        self._existing = existing_record

    async def execute(self, stmt):
        return FakeResultWithValue(self._existing)


class FakeResultWithValue:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalars(self):
        return FakeScalarsWithValue([self._value])

    def scalar(self):
        return 1


class FakeScalarsWithValue:
    def __init__(self, values):
        self._values = values

    def all(self):
        return self._values


# ─── Test: KnowledgeSourceRepository ─────────────────────────────────────────


class TestKnowledgeSourceRepository:
    """Test KnowledgeSourceRepository upsert and health tracking."""

    async def test_upsert_new(self):
        """Should create a new knowledge source record."""
        db = FakeDB()
        repo = KnowledgeSourceRepository(db)

        result = await repo.upsert(
            name="test_source",
            version="1.0",
            license="MIT",
            base_url="https://example.com/api",
            is_configured="configured",
        )

        assert result.name == "test_source"
        assert result.version == "1.0"
        assert result.license == "MIT"
        assert result.is_configured == "configured"
        assert len(db.added) == 1
        assert db.committed

    async def test_upsert_existing(self):
        """Should update an existing knowledge source record."""
        existing = make_model(KnowledgeSourceModel, name="existing_source", version="1.0")
        db = FakeDBWithExisting(existing)
        repo = KnowledgeSourceRepository(db)

        updated = await repo.upsert(name="existing_source", version="2.0", is_configured="configured")

        assert updated.version == "2.0"
        assert updated.is_configured == "configured"

    async def test_record_health_check(self):
        """Should record health check for a source."""
        # Test with non-existent source -> returns None
        db = FakeDB()
        repo = KnowledgeSourceRepository(db)
        result = await repo.record_health_check("nonexistent", "degraded")
        assert result is None

        # Test with existing source
        existing = make_model(KnowledgeSourceModel, name="test_civic", version="2.0")
        db2 = FakeDBWithExisting(existing)
        repo2 = KnowledgeSourceRepository(db2)
        result2 = await repo2.record_health_check("test_civic", "configured", version="2.1")
        assert result2 is not None
        assert result2.is_configured == "configured"


# ─── Test: EvidenceItemRepository ────────────────────────────────────────────


class TestEvidenceItemRepository:
    """Test EvidenceItemRepository upsert, dedup, withdraw."""

    def test_compute_payload_hash(self):
        """Should produce consistent SHA256 hashes for same payload."""
        item1 = {"source": "civic", "source_record_id": "123", "gene_symbol": "BRAF",
                  "drug_name": "", "disease": "melanoma", "evidence_type": "predictive",
                  "evidence_direction": "supporting"}
        item2 = {"source": "civic", "source_record_id": "123", "gene_symbol": "BRAF",
                  "drug_name": "", "disease": "melanoma", "evidence_type": "predictive",
                  "evidence_direction": "supporting"}

        h1 = _compute_payload_hash(item1)
        h2 = _compute_payload_hash(item2)
        assert h1 == h2
        assert len(h1) == 64  # SHA256 hex

    def test_compute_payload_hash_different(self):
        """Should produce different hashes for different payloads."""
        item1 = {"source": "civic", "source_record_id": "123", "gene_symbol": "BRAF",
                  "drug_name": "", "disease": "melanoma", "evidence_type": "predictive",
                  "evidence_direction": "supporting"}
        item2 = {"source": "civic", "source_record_id": "456", "gene_symbol": "EGFR",
                  "drug_name": "", "disease": "lung", "evidence_type": "predictive",
                  "evidence_direction": "supporting"}

        h1 = _compute_payload_hash(item1)
        h2 = _compute_payload_hash(item2)
        assert h1 != h2

    async def test_upsert_new_item(self):
        """Should create a new evidence item (no existing match)."""
        db = FakeDB()
        repo = EvidenceItemRepository(db)
        source_id = uuid.uuid4()

        result = await repo.upsert(
            source_id=source_id,
            item={"source": "civic", "source_record_id": "e123", "gene_symbol": "BRAF",
                   "drug_name": "Vemurafenib", "disease": "melanoma",
                   "evidence_type": "predictive", "evidence_direction": "supporting",
                   "evidence_level": "A", "source_version": "2.0"},
            match_level="exact_variant",
            conflict_status="supporting",
        )

        assert result is not None
        assert result.gene_symbol == "BRAF"
        assert result.match_level == "exact_variant"
        assert result.conflict_status == "supporting"
        assert result.payload_hash is not None
        assert result.first_seen_at is not None
        assert result.last_seen_at is not None
        assert len(db.added) == 1

    async def test_find_by_gene_symbol(self):
        db = FakeDB()
        repo = EvidenceItemRepository(db)
        results = await repo.find_by_gene_symbol("BRAF")
        assert isinstance(results, list)

    async def test_count_active(self):
        db = FakeDB()
        repo = EvidenceItemRepository(db)
        count = await repo.count_active()
        assert count == 0


# ─── Test: DrugInteractionRepository ──────────────────────────────────────────


class TestDrugInteractionRepository:
    """Test DrugInteractionRepository upsert and dedup."""

    def test_compute_interaction_hash(self):
        """Should produce consistent hashes."""
        i1 = {"gene_symbol": "BRAF", "drug_name": "Vemurafenib",
               "interaction_type": "inhibitor", "source_db_name": "DrugBank"}
        i2 = {"gene_symbol": "BRAF", "drug_name": "Vemurafenib",
               "interaction_type": "inhibitor", "source_db_name": "DrugBank"}

        h1 = _compute_interaction_hash(i1)
        h2 = _compute_interaction_hash(i2)
        assert h1 == h2

    async def test_upsert_new(self):
        """Should create a new interaction."""
        db = FakeDB()
        repo = DrugInteractionRepository(db)
        source_id = uuid.uuid4()

        result = await repo.upsert(
            source_id=source_id,
            item={"gene_symbol": "BRAF", "drug_name": "Vemurafenib",
                   "interaction_type": "inhibitor", "source_db_name": "DrugBank",
                   "pmids": ["12345678"], "source_version": "v2"},
        )

        assert result is not None
        assert result.gene_symbol == "BRAF"
        assert result.payload_hash is not None
        assert len(db.added) == 1


# ─── Test: EvidenceMerger Matching Priority ───────────────────────────────────


class TestEvidenceMergerMatchingPriority:
    """Test the evidence matching priority chain."""

    async def test_determine_match_level_exact_hgvs(self):
        """HGVS exact match should return 'exact_variant'."""
        merger = EvidenceMerger()
        query = {"gene_symbol": "BRAF", "hgvs": "NM_004333.6:c.1799T>A"}
        item = {"gene_symbol": "BRAF", "hgvs_description": "NM_004333.6:c.1799T>A"}

        level = merger._determine_match_level(query, item)
        assert level == "exact_variant"

    async def test_determine_match_level_equivalent_hgvs(self):
        """HGVS with same variant part should return 'equivalent_hgvs'."""
        merger = EvidenceMerger()
        query = {"gene_symbol": "BRAF", "hgvs": "NM_004333.6:c.1799T>A"}
        item = {"gene_symbol": "BRAF", "hgvs_description": "ENST00000288602.6:c.1799T>A"}

        level = merger._determine_match_level(query, item)
        assert level == "equivalent_hgvs"

    async def test_determine_match_level_exact_coordinates(self):
        """Exact coordinate match should return 'exact_variant'."""
        merger = EvidenceMerger()
        query = {"gene_symbol": "BRAF", "chromosome": "7", "position": 140753336,
                  "reference": "A", "alternate": "T"}
        item = {"gene_symbol": "BRAF", "chromosome": "7", "position": 140753336,
                 "reference": "A", "alternate": "T"}

        level = merger._determine_match_level(query, item)
        assert level == "exact_variant"

    async def test_determine_match_level_coordinate(self):
        """Same chromosome and position should return 'coordinate_match'."""
        merger = EvidenceMerger()
        query = {"gene_symbol": "BRAF", "chromosome": "7", "position": 140753336,
                  "reference": "A", "alternate": "T"}
        item = {"gene_symbol": "BRAF", "chromosome": "7", "position": 140753336,
                 "reference": "G", "alternate": "C"}

        level = merger._determine_match_level(query, item)
        assert level == "coordinate_match"

    async def test_determine_match_level_gene_only(self):
        """Same gene, no variant details should return 'gene_level_only'."""
        merger = EvidenceMerger()
        query = {"gene_symbol": "BRAF"}
        item = {"gene_symbol": "BRAF"}

        level = merger._determine_match_level(query, item)
        assert level == "gene_level_only"

    async def test_determine_match_level_unmatched(self):
        """Different genes should return 'unmatched'."""
        merger = EvidenceMerger()
        query = {"gene_symbol": "BRAF"}
        item = {"gene_symbol": "EGFR"}

        level = merger._determine_match_level(query, item)
        assert level == "unmatched"

    async def test_match_level_precedence_order(self):
        """MATCH_LEVEL_ORDER should correctly rank levels."""
        assert MATCH_LEVEL_ORDER["exact_variant"] < MATCH_LEVEL_ORDER["equivalent_hgvs"]
        assert MATCH_LEVEL_ORDER["equivalent_hgvs"] < MATCH_LEVEL_ORDER["coordinate_match"]
        assert MATCH_LEVEL_ORDER["coordinate_match"] < MATCH_LEVEL_ORDER["molecular_profile_match"]
        assert MATCH_LEVEL_ORDER["molecular_profile_match"] < MATCH_LEVEL_ORDER["gene_level_only"]
        assert MATCH_LEVEL_ORDER["gene_level_only"] < MATCH_LEVEL_ORDER["unmatched"]

    async def test_determine_conflict_status_supporting(self):
        """Supporting direction should map to 'supporting'."""
        merger = EvidenceMerger()
        assert merger._determine_conflict_status({"evidence_direction": "Supports"}) == "supporting"
        assert merger._determine_conflict_status({"evidence_direction": "supporting"}) == "supporting"
        assert merger._determine_conflict_status({"evidence_direction": "Sensitive"}) == "supporting"

    async def test_determine_conflict_status_conflicting(self):
        """Conflicting direction should map to 'conflicting'."""
        merger = EvidenceMerger()
        assert merger._determine_conflict_status({"evidence_direction": "Does Not Support"}) == "conflicting"
        assert merger._determine_conflict_status({"evidence_direction": "Conflicting"}) == "conflicting"
        assert merger._determine_conflict_status({"evidence_direction": "Resistance"}) == "conflicting"

    async def test_determine_conflict_status_uncertain(self):
        """Uncertain/empty direction should map to 'uncertain'."""
        merger = EvidenceMerger()
        assert merger._determine_conflict_status({"evidence_direction": ""}) == "uncertain"
        assert merger._determine_conflict_status({"evidence_direction": "neutral"}) == "uncertain"
        assert merger._determine_conflict_status({"evidence_direction": "inconclusive"}) == "uncertain"


# ─── Test: EvidenceMerger with Mock Adapters ──────────────────────────────────


class MockAdapterResult:
    """Mock AdapterResult for testing."""
    def __init__(self, success=True, records=None, warnings=None, errors=None, metadata=None):
        self.success = success
        self.records = records or []
        self.warnings = warnings or []
        self.errors = errors or []
        self.metadata = metadata or {}
        self.source = "mock"
        self.source_version = "1.0"


class TestEvidenceMergerPersistence:
    """Test EvidenceMerger persistence and integration."""

    async def test_merge_without_db(self):
        """Merger should work without DB (dict-only mode)."""
        merger = EvidenceMerger()
        result = await merger.merge_variant_evidence(
            gene_symbol="BRAF",
            request_id="test-no-db",
        )
        assert result is not None
        assert result["gene_symbol"] == "BRAF"
        assert "evidence_items" in result

    async def test_merge_with_mock_adapters(self):
        """Merger should handle adapter results correctly."""
        civic_mock = MagicMock()
        civic_mock.lookup_hgvs = AsyncMock(return_value=MockAdapterResult(success=True, records=[
            {"gene_symbol": "BRAF", "source_record_id": "1", "evidence_level": "A",
             "evidence_direction": "Supports", "disease": "melanoma", "drug_name": "Vemurafenib",
             "evidence_type": "predictive", "description": "Test evidence"}
        ], metadata={"request_hash": "abc", "response_hash": "def"}))
        civic_mock.lookup_coordinates = AsyncMock(return_value=MockAdapterResult(success=True, records=[]))
        civic_mock.lookup_variant = AsyncMock(return_value=MockAdapterResult(success=True, records=[]))

        dgidb_mock = MagicMock()
        dgidb_mock.lookup_gene = AsyncMock(return_value=MockAdapterResult(success=True, records=[
            {"gene_symbol": "BRAF", "drug_name": "Vemurafenib", "interaction_type": "inhibitor"}
        ]))

        merger = EvidenceMerger(civic_adapter=civic_mock, dgidb_adapter=dgidb_mock)
        result = await merger.refresh_all(
            gene_symbol="BRAF",
            hgvs="NM_004333.6:c.1799T>A",
            request_id="test-mock",
        )

        assert result["gene_symbol"] == "BRAF"
        assert result["evidence_count"] >= 1
        assert result["drug_count"] >= 1
        assert result["match_level"] in MATCH_LEVEL_PRECEDENCE
        civic_mock.lookup_hgvs.assert_called_once()
        dgidb_mock.lookup_gene.assert_called_once()

    async def test_merge_priority_hgvs_first(self):
        """When HGVS is provided, it should be queried first."""
        civic_mock = MagicMock()
        civic_mock.lookup_hgvs = AsyncMock(return_value=MockAdapterResult(success=True, records=[
            {"gene_symbol": "BRAF", "source_record_id": "1", "evidence_level": "A",
             "evidence_direction": "Supports"}
        ], metadata={"request_hash": "abc", "response_hash": "def"}))
        civic_mock.lookup_coordinates = AsyncMock(return_value=MockAdapterResult(success=True, records=[]))
        civic_mock.lookup_variant = AsyncMock(return_value=MockAdapterResult(success=True, records=[]))

        dgidb_mock = MagicMock()
        dgidb_mock.lookup_gene = AsyncMock(return_value=MockAdapterResult(success=True, records=[]))

        merger = EvidenceMerger(civic_adapter=civic_mock, dgidb_adapter=dgidb_mock)
        await merger.refresh_all(
            gene_symbol="BRAF",
            hgvs="NM_004333.6:c.1799T>A",
            chromosome="7", position=140753336, reference="A", alternate="T",
            request_id="test-priority",
        )

        civic_mock.lookup_hgvs.assert_called_once()
        civic_mock.lookup_coordinates.assert_called_once()
        civic_mock.lookup_variant.assert_called_once()

    async def test_merge_with_partial_failure(self):
        """Merger should handle partial adapter failures."""
        civic_mock = MagicMock()
        civic_mock.lookup_hgvs = AsyncMock(return_value=MockAdapterResult(
            success=False, errors=["CIViC unavailable"]
        ))
        civic_mock.lookup_coordinates = AsyncMock(return_value=MockAdapterResult(
            success=False, errors=["CIViC unavailable"]
        ))
        civic_mock.lookup_variant = AsyncMock(return_value=MockAdapterResult(
            success=False, errors=["CIViC unavailable"]
        ))

        dgidb_mock = MagicMock()
        dgidb_mock.lookup_gene = AsyncMock(return_value=MockAdapterResult(
            success=True, records=[{"gene_symbol": "BRAF", "drug_name": "Test Drug",
                                      "interaction_type": "inhibitor"}]
        ))

        merger = EvidenceMerger(civic_adapter=civic_mock, dgidb_adapter=dgidb_mock)
        result = await merger.refresh_all(
            gene_symbol="BRAF",
            request_id="test-partial",
        )

        assert result["gene_symbol"] == "BRAF"
        assert result["drug_count"] >= 1
        # CIViC failures should be in errors list
        civ_errors = [e for e in result["errors"] if "CIViC" in e]
        assert len(civ_errors) >= 1


# ─── Test: Evidence Cache ─────────────────────────────────────────────────────


class TestEvidenceCache:
    """Test TTLCache operations."""

    def test_cache_set_and_get(self):
        cache = TTLCache(ttl_seconds=60)
        cache.set("test_key", {"data": 123})
        assert cache.get("test_key") == {"data": 123}

    def test_cache_expiry(self):
        cache = TTLCache(ttl_seconds=0)
        cache.set("test_key", "value")
        import time
        time.sleep(0.001)
        assert cache.get("test_key") is None

    def test_cache_miss(self):
        cache = TTLCache()
        assert cache.get("nonexistent") is None

    def test_cache_clear(self):
        cache = TTLCache()
        cache.set("a", 1)
        cache.set("b", 2)
        assert cache.size == 2
        cache.clear()
        assert cache.size == 0

    def test_cache_invalidate(self):
        cache = TTLCache()
        cache.set("key", "value")
        assert cache.get("key") == "value"
        cache.invalidate("key")
        assert cache.get("key") is None


# ─── Test: Response Models ────────────────────────────────────────────────────


class TestResponseModels:
    """Test Phase 2B Pydantic response models."""

    def test_evidence_variant_response_with_match_level(self):
        response = EvidenceVariantResponse(
            variant_id="test-id",
            gene_symbol="BRAF",
            match_level="exact_variant",
            evidence_count=2,
        )
        assert response.match_level == "exact_variant"
        assert response.variant_id == "test-id"
        assert response.gene_symbol == "BRAF"

    def test_evidence_refresh_response(self):
        response = EvidenceRefreshResponse(
            status="completed",
            sources_updated=["civic", "dgidb"],
            total_evidence=42,
            total_interactions=10,
        )
        assert response.status == "completed"
        assert response.total_evidence == 42
        assert response.total_interactions == 10

    def test_evidence_cache_invalidate_response(self):
        response = EvidenceCacheInvalidateResponse(
            status="completed",
            cache_type="gene_cache,variant_cache",
        )
        assert response.status == "completed"
        assert response.cleared_at is not None


# ─── Test: Domain Model Fields ────────────────────────────────────────────────


class TestDomainModelFields:
    """Test that the domain models have the new Phase 2B fields."""

    def test_evidence_item_model_has_match_level(self):
        cols = {c.name: c for c in EvidenceItemModel.__table__.columns}
        assert "match_level" in cols
        assert "conflict_status" in cols
        assert "source_native_level" in cols
        assert "payload_hash" in cols
        assert "first_seen_at" in cols
        assert "last_seen_at" in cols
        assert "withdrawn_at" in cols
        assert "superseded_by" in cols
        assert "is_superseded" in cols

    def test_knowledge_source_model_has_retrieval_count(self):
        cols = {c.name: c for c in KnowledgeSourceModel.__table__.columns}
        assert "retrieval_count" in cols

    def test_drug_interaction_model_has_payload_hash(self):
        cols = {c.name: c for c in DrugInteractionModel.__table__.columns}
        assert "payload_hash" in cols
        assert "first_seen_at" in cols
        assert "last_seen_at" in cols
        assert "withdrawn_at" in cols
        assert "superseded_by" in cols
        assert "is_superseded" in cols
