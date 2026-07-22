"""
Unit tests for EvidenceBundle, EvidenceItem, and EvidenceCollector.

Tests the evidence aggregation models and the collector that gathers
evidence from multiple knowledge sources with graceful degradation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.backend.clinical.evidence_models import (
    EvidenceBundle,
    EvidenceItem,
    evidence_level_rank,
)
from src.backend.clinical.collector import EvidenceCollector
from src.backend.clinical.models import ClinicalContext


# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_db():
    """Create a mock async SQLAlchemy session."""
    db = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def collector(mock_db):
    """Create an EvidenceCollector with a mock DB session.

    The lazy adapters are not initialised unless _get_* methods are called,
    so we patch them at the class level in tests that need them.
    """
    return EvidenceCollector(mock_db)


@pytest.fixture
def sample_context():
    """Return a minimal ClinicalContext with variants for testing."""
    ctx = ClinicalContext(
        case_id="c1",
        patient_id="p1",
        age=50,
        gender="M",
        diagnosis="PTC",
        stage="II",
        histology="Papillary",
        cancer_type="PTC",
        variants=[
            {
                "gene_symbol": "BRAF",
                "hgvs": "NM_004333.6:c.1799T>A",
                "protein_change": "p.Val600Glu",
                "vaf": 0.35,
                "clinical_significance": "Pathogenic",
            },
        ],
    )
    ctx.freeze()
    return ctx


@pytest.fixture
def sample_evidence_item():
    """Return a fully populated EvidenceItem for testing."""
    return EvidenceItem(
        source="CIViC",
        source_record_id="123",
        gene_symbol="BRAF",
        drug_name="Vemurafenib",
        disease="Melanoma",
        evidence_type="predictive",
        evidence_direction="supporting",
        evidence_level="A",
        source_native_level="A",
        clinical_significance="sensitivity",
        description="BRAF V600E mutation predicts response to Vemurafenib.",
        citation="doi:10.1000/example",
        pmid="12345678",
        url="https://civic.example.org/123",
        confidence="high",
        match_level="exact_variant",
        conflict_status="supporting",
    )


@pytest.fixture
def sample_bundle(sample_evidence_item):
    """Return an EvidenceBundle with sample items."""
    return EvidenceBundle(
        items=[
            sample_evidence_item,
            EvidenceItem(
                source="ClinVar",
                gene_symbol="BRAF",
                evidence_type="prognostic",
                evidence_direction="supporting",
                evidence_level="B",
            ),
            EvidenceItem(
                source="PubMed",
                gene_symbol="EGFR",
                drug_name="Erlotinib",
                evidence_type="predictive",
                evidence_direction="conflicting",
                evidence_level="C",
            ),
        ],
        retrieved_at=datetime.now(timezone.utc).isoformat(),
        context_hash="abc123",
    )


# ─── EvidenceItem ─────────────────────────────────────────────────────────────


class TestEvidenceItem:
    """Tests for the EvidenceItem model."""

    def test_create_full(self, sample_evidence_item):
        """Create an EvidenceItem with all fields."""
        item = sample_evidence_item
        assert item.source == "CIViC"
        assert item.source_record_id == "123"
        assert item.gene_symbol == "BRAF"
        assert item.drug_name == "Vemurafenib"
        assert item.evidence_type == "predictive"
        assert item.evidence_direction == "supporting"
        assert item.evidence_level == "A"
        assert item.confidence == "high"
        assert item.conflict_status == "supporting"

    def test_create_minimal(self):
        """Create an EvidenceItem with only required fields."""
        item = EvidenceItem(source="ClinVar")
        assert item.source == "ClinVar"
        assert item.source_record_id is None
        assert item.gene_symbol is None
        assert item.drug_name is None
        assert item.evidence_type == ""
        assert item.evidence_direction == ""
        assert item.evidence_level == ""
        assert item.source_native_level is None
        assert item.clinical_significance is None
        assert item.citation is None
        assert item.pmid is None
        assert item.url is None
        assert item.confidence is None
        assert item.match_level is None
        assert item.conflict_status is None
        assert item.description is None

    def test_empty_source_allowed(self):
        """EvidenceItem should allow empty source string."""
        item = EvidenceItem(source="")
        assert item.source == ""


# ─── EvidenceBundle ───────────────────────────────────────────────────────────


class TestEvidenceBundle:
    """Tests for the EvidenceBundle model."""

    def test_create_empty(self):
        """Create an empty EvidenceBundle."""
        bundle = EvidenceBundle()
        assert bundle.items == []
        assert bundle.retrieved_at == ""
        assert bundle.context_hash is None

    def test_total_count(self, sample_bundle):
        """total_count should reflect the number of items."""
        assert sample_bundle.total_count == 3

    def test_total_count_empty(self):
        """Empty bundle should have total_count of 0."""
        bundle = EvidenceBundle()
        assert bundle.total_count == 0

    def test_by_source(self, sample_bundle):
        """by_source should group items by source name."""
        by_source = sample_bundle.by_source
        assert "CIViC" in by_source
        assert "ClinVar" in by_source
        assert "PubMed" in by_source
        assert len(by_source["CIViC"]) == 1
        assert len(by_source["ClinVar"]) == 1
        assert len(by_source["PubMed"]) == 1

    def test_by_gene(self, sample_bundle):
        """by_gene should group items by gene symbol."""
        by_gene = sample_bundle.by_gene
        assert "BRAF" in by_gene
        assert "EGFR" in by_gene
        assert len(by_gene["BRAF"]) == 2

    def test_by_gene_missing_symbol(self):
        """Items with no gene_symbol should be grouped under '__missing__'."""
        bundle = EvidenceBundle(
            items=[
                EvidenceItem(source="Internal", gene_symbol=None),
            ],
        )
        by_gene = bundle.by_gene
        assert "__missing__" in by_gene
        assert len(by_gene["__missing__"]) == 1

    def test_by_drug(self, sample_bundle):
        """by_drug should group items by drug name."""
        by_drug = sample_bundle.by_drug
        assert "Vemurafenib" in by_drug
        assert "Erlotinib" in by_drug
        assert "__missing__" in by_drug  # ClinVar item has no drug_name
        assert len(by_drug["Vemurafenib"]) == 1

    def test_highest_level(self, sample_bundle):
        """highest_level should return the best evidence level (A)."""
        assert sample_bundle.highest_level == "A"

    def test_highest_level_empty(self):
        """Empty bundle should have None as highest_level."""
        bundle = EvidenceBundle()
        assert bundle.highest_level is None

    def test_highest_level_single_item(self):
        """Bundle with one item should report its level."""
        bundle = EvidenceBundle(
            items=[EvidenceItem(source="Test", evidence_level="D")],
        )
        assert bundle.highest_level == "D"

    def test_conflicts_summary(self, sample_bundle):
        """conflicts_summary should report status distribution."""
        summary = sample_bundle.conflicts_summary
        statuses = {s["status"] for s in summary}
        assert "supporting" in statuses
        # ClinVar & PubMed items have no conflict_status → "unknown"
        assert "unknown" in statuses

    def test_conflicts_summary_empty(self):
        """Empty bundle should have empty conflicts_summary."""
        bundle = EvidenceBundle()
        assert bundle.conflicts_summary == []

    def test_context_hash(self):
        """context_hash should be preserved from input."""
        bundle = EvidenceBundle(context_hash="sha256hash")
        assert bundle.context_hash == "sha256hash"

    # ── filter() ────────────────────────────────────────────────────────

    def test_filter_by_gene(self, sample_bundle):
        """filter(gene=...) should return only items with that gene."""
        filtered = sample_bundle.filter(gene="BRAF")
        assert filtered.total_count == 2
        assert all(i.gene_symbol == "BRAF" for i in filtered.items)

    def test_filter_by_drug(self, sample_bundle):
        """filter(drug=...) should return only items with that drug."""
        filtered = sample_bundle.filter(drug="Erlotinib")
        assert filtered.total_count == 1
        assert all(i.drug_name == "Erlotinib" for i in filtered.items)

    def test_filter_by_source(self, sample_bundle):
        """filter(source=...) should return only items from that source."""
        filtered = sample_bundle.filter(source="PubMed")
        assert filtered.total_count == 1
        assert all(i.source == "PubMed" for i in filtered.items)

    def test_filter_by_min_level(self, sample_bundle):
        """filter(min_level=...) should keep items at or above the level."""
        # min_level="B" → keeps A and B, removes C (EGFR item)
        filtered = sample_bundle.filter(min_level="B")
        assert filtered.total_count == 2
        for item in filtered.items:
            rank = evidence_level_rank(item.evidence_level)
            assert rank <= evidence_level_rank("B")

    def test_filter_by_min_level_A(self, sample_bundle):
        """filter(min_level="A") should keep only level A items."""
        filtered = sample_bundle.filter(min_level="A")
        assert filtered.total_count == 1
        assert all(item.evidence_level == "A" for item in filtered.items)

    def test_filter_multiple_criteria(self, sample_bundle):
        """filter() with multiple criteria should apply all."""
        filtered = sample_bundle.filter(
            gene="BRAF",
            source="CIViC",
        )
        assert filtered.total_count == 1
        assert filtered.items[0].gene_symbol == "BRAF"
        assert filtered.items[0].source == "CIViC"

    def test_filter_no_match(self, sample_bundle):
        """filter() with non-matching criteria should return empty bundle."""
        filtered = sample_bundle.filter(gene="NONEXISTENT")
        assert filtered.total_count == 0
        assert filtered.items == []

    def test_filter_preserves_metadata(self, sample_bundle):
        """filter() should preserve retrieved_at and context_hash."""
        filtered = sample_bundle.filter(gene="BRAF")
        assert filtered.retrieved_at == sample_bundle.retrieved_at
        assert filtered.context_hash == sample_bundle.context_hash

    def test_filter_returns_new_instance(self, sample_bundle):
        """filter() should return a new EvidenceBundle, not mutate original."""
        filtered = sample_bundle.filter(gene="BRAF")
        assert filtered is not sample_bundle
        assert sample_bundle.total_count == 3  # original unchanged

    def test_filter_empty_bundle(self):
        """filter() on empty bundle should return empty bundle."""
        bundle = EvidenceBundle()
        filtered = bundle.filter(gene="BRAF")
        assert filtered.total_count == 0


# ─── EvidenceCollector ────────────────────────────────────────────────────────


class TestEvidenceCollector:
    """Tests for the EvidenceCollector."""

    async def test_collect_basic_flow(self, collector, sample_context):
        """collect() should return an EvidenceBundle with items when all sources succeed."""
        with (
            patch.object(collector, "_collect_for_gene", AsyncMock(return_value=[
                EvidenceItem(source="CIViC", gene_symbol="BRAF", evidence_type="predictive"),
            ])),
            patch("src.backend.clinical.collector._AUTH_SOURCES", []),
        ):
            bundle = await collector.collect(sample_context)

        assert isinstance(bundle, EvidenceBundle)
        assert bundle.total_count == 1
        assert bundle.items[0].source == "CIViC"
        assert bundle.items[0].gene_symbol == "BRAF"
        assert bundle.context_hash == sample_context.context_hash
        assert bundle.retrieved_at != ""

    async def test_collect_empty_variants(self, collector):
        """collect() should return empty bundle when context has no variants."""
        empty_ctx = ClinicalContext(
            case_id="c1", patient_id="p1", age=30, gender="F",
            diagnosis="PTC", stage="I", histology="Papillary", cancer_type="PTC",
            variants=[],
        )
        empty_ctx.freeze()

        with patch("src.backend.clinical.collector._AUTH_SOURCES", []):
            bundle = await collector.collect(empty_ctx)

        assert isinstance(bundle, EvidenceBundle)
        assert bundle.total_count == 0

    async def test_collect_deduplicates_genes(self, collector, sample_context):
        """collect() should collect evidence per unique gene symbol only."""
        # Add another variant with same gene
        sample_context.variants.append({
            "gene_symbol": "BRAF",
            "hgvs": "NM_004333.6:c.1798_1800del",
            "protein_change": "p.Val600del",
            "vaf": 0.10,
            "clinical_significance": "Pathogenic",
        })

        call_count = 0

        async def collecting(gene, ctx):
            nonlocal call_count
            call_count += 1
            return [EvidenceItem(source="CIViC", gene_symbol=gene)]

        with (
            patch.object(collector, "_collect_for_gene", side_effect=collecting),
            patch("src.backend.clinical.collector._AUTH_SOURCES", []),
        ):
            bundle = await collector.collect(sample_context)

        # Only one unique gene (BRAF) — should call _collect_for_gene once
        assert call_count == 1
        assert bundle.total_count == 1

    async def test_collect_multiple_genes(self, collector):
        """collect() should handle variants with different gene symbols."""
        ctx = ClinicalContext(
            case_id="c1", patient_id="p1", age=45, gender="F",
            diagnosis="PTC", stage="II", histology="Papillary", cancer_type="PTC",
            variants=[
                {"gene_symbol": "BRAF", "hgvs": "", "protein_change": "",
                 "vaf": None, "clinical_significance": ""},
                {"gene_symbol": "EGFR", "hgvs": "", "protein_change": "",
                 "vaf": None, "clinical_significance": ""},
            ],
        )
        ctx.freeze()

        calls: dict[str, int] = {}

        async def collecting(gene, ctx):
            calls[gene] = calls.get(gene, 0) + 1
            return [EvidenceItem(source="Test", gene_symbol=gene)]

        with (
            patch.object(collector, "_collect_for_gene", side_effect=collecting),
            patch("src.backend.clinical.collector._AUTH_SOURCES", []),
        ):
            bundle = await collector.collect(ctx)

        assert bundle.total_count == 2
        assert "BRAF" in calls
        assert "EGFR" in calls
        assert calls["BRAF"] == 1
        assert calls["EGFR"] == 1

    async def test_collect_partial_failure(self, collector, sample_context):
        """collect() should degrade gracefully when some sources fail."""
        with (
            patch.object(
                collector, "_collect_for_gene",
                AsyncMock(return_value=[]),
            ),
            patch("src.backend.clinical.collector._AUTH_SOURCES", []),
        ):
            bundle = await collector.collect(sample_context)
        # Should return empty bundle gracefully, not raise
        assert isinstance(bundle, EvidenceBundle)
        assert bundle.total_count == 0

    async def test_collect_reports_auth_sources_warning(self, collector, sample_context):
        """collect() should log warnings for authorisation-required sources."""
        with (
            patch.object(collector, "_collect_for_gene", AsyncMock(return_value=[])),
            patch("src.backend.clinical.collector._AUTH_SOURCES", ("nccn", "esmo")),
            patch("src.backend.clinical.collector.logger") as mock_logger,
        ):
            await collector.collect(sample_context)

        assert mock_logger.warning.call_count >= 2
        auth_warnings = [
            c for c in mock_logger.warning.call_args_list
            if "requires authorisation" in str(c)
        ]
        assert len(auth_warnings) == 2

    async def test_collect_skips_empty_gene_symbol(self, collector):
        """collect() should skip variant entries with no gene_symbol."""
        ctx = ClinicalContext(
            case_id="c1", patient_id="p1", age=30, gender="M",
            diagnosis="PTC", stage="I", histology="Papillary", cancer_type="PTC",
            variants=[
                {"gene_symbol": "", "hgvs": "", "protein_change": "",
                 "vaf": None, "clinical_significance": ""},
                {"gene_symbol": "  ", "hgvs": "", "protein_change": "",
                 "vaf": None, "clinical_significance": ""},
                {"gene_symbol": "BRAF", "hgvs": "", "protein_change": "",
                 "vaf": None, "clinical_significance": ""},
            ],
        )
        ctx.freeze()

        with (
            patch.object(collector, "_collect_for_gene", AsyncMock(return_value=[
                EvidenceItem(source="Test", gene_symbol="BRAF"),
            ])),
            patch("src.backend.clinical.collector._AUTH_SOURCES", []),
        ):
            bundle = await collector.collect(ctx)

        assert bundle.total_count == 1
        assert bundle.items[0].gene_symbol == "BRAF"

    # ── collect_by_variant ──────────────────────────────────────────────

    async def test_collect_by_variant_basic(self, collector):
        """collect_by_variant() should collect evidence for a variant."""
        with (
            patch.object(collector, "_merger") as mock_merger,
            patch.object(collector, "_get_clinvar") as mock_get_clinvar,
            patch.object(collector, "_get_pubmed") as mock_get_pubmed,
            patch.object(collector, "_get_clinicaltrials") as mock_get_ct,
            patch("src.backend.clinical.collector._AUTH_SOURCES", []),
            patch("src.backend.clinical.collector.variant_cache") as mock_vc,
        ):
            mock_vc.get.return_value = None
            mock_merger.merge_variant_evidence = AsyncMock(return_value={
                "evidence_items": [
                    {"_source": "CIViC", "gene_symbol": "BRAF",
                     "evidence_type": "predictive"},
                ],
            })
            # Other adapters return empty
            mock_clinvar = AsyncMock()
            mock_clinvar.search_variant = AsyncMock(return_value=[])
            mock_get_clinvar.return_value = mock_clinvar

            mock_pubmed = AsyncMock()
            mock_pubmed.search = AsyncMock(return_value=[])
            mock_get_pubmed.return_value = mock_pubmed

            mock_ct = AsyncMock()
            mock_ct.search = AsyncMock(return_value=[])
            mock_get_ct.return_value = mock_ct

            bundle = await collector.collect_by_variant("BRAF", "NM_004333.6:c.1799T>A")

        assert isinstance(bundle, EvidenceBundle)
        assert bundle.total_count == 1
        assert bundle.items[0].source == "CIViC"
        assert bundle.items[0].gene_symbol == "BRAF"
        assert bundle.retrieved_at != ""

    async def test_collect_by_variant_uses_cache(self, collector):
        """collect_by_variant() should return cached results when available."""
        cached_items = [EvidenceItem(source="CIViC", gene_symbol="BRAF")]

        with patch("src.backend.clinical.collector.variant_cache") as mock_vc:
            mock_vc.get.return_value = cached_items

            bundle = await collector.collect_by_variant("BRAF", "NM_004333.6:c.1799T>A")

        assert bundle.total_count == 1
        assert bundle.items[0].source == "CIViC"

    async def test_collect_by_variant_source_failure(self, collector):
        """collect_by_variant() should degrade when a source fails."""
        with (
            patch.object(collector, "_merger") as mock_merger,
            patch.object(collector, "_get_clinvar") as mock_get_clinvar,
            patch.object(collector, "_get_pubmed") as mock_get_pubmed,
            patch.object(collector, "_get_clinicaltrials") as mock_get_ct,
            patch("src.backend.clinical.collector._AUTH_SOURCES", []),
            patch("src.backend.clinical.collector.variant_cache") as mock_vc,
        ):
            mock_vc.get.return_value = None
            # Merger fails
            mock_merger.merge_variant_evidence = AsyncMock(
                side_effect=Exception("Merger API timeout"),
            )
            # ClinVar fails
            mock_clinvar = AsyncMock()
            mock_clinvar.search_variant = AsyncMock(
                side_effect=Exception("ClinVar unavailable"),
            )
            mock_get_clinvar.return_value = mock_clinvar
            # PubMed succeeds
            mock_pubmed = AsyncMock()
            mock_pubmed.search = AsyncMock(return_value=[
                {"_source": "PubMed", "gene_symbol": "BRAF",
                 "evidence_type": "prognostic"},
            ])
            mock_get_pubmed.return_value = mock_pubmed
            # ClinicalTrials fails
            mock_ct = AsyncMock()
            mock_ct.search = AsyncMock(
                side_effect=Exception("ClinicalTrials.gov timeout"),
            )
            mock_get_ct.return_value = mock_ct

            bundle = await collector.collect_by_variant("BRAF", "NM_004333.6:c.1799T>A")

        # Should still have results from PubMed despite other sources failing
        assert bundle.total_count == 1
        assert bundle.items[0].source == "PubMed"

    async def test_collect_by_variant_all_sources_fail(self, collector):
        """collect_by_variant() should return empty bundle when all sources fail."""
        with (
            patch.object(collector, "_merger") as mock_merger,
            patch.object(collector, "_get_clinvar") as mock_get_clinvar,
            patch.object(collector, "_get_pubmed") as mock_get_pubmed,
            patch.object(collector, "_get_clinicaltrials") as mock_get_ct,
            patch("src.backend.clinical.collector._AUTH_SOURCES", []),
            patch("src.backend.clinical.collector.variant_cache") as mock_vc,
        ):
            mock_vc.get.return_value = None
            mock_merger.merge_variant_evidence = AsyncMock(
                side_effect=Exception("Fail"),
            )
            mock_clinvar = AsyncMock()
            mock_clinvar.search_variant = AsyncMock(side_effect=Exception("Fail"))
            mock_get_clinvar.return_value = mock_clinvar
            mock_pubmed = AsyncMock()
            mock_pubmed.search = AsyncMock(side_effect=Exception("Fail"))
            mock_get_pubmed.return_value = mock_pubmed
            mock_ct = AsyncMock()
            mock_ct.search = AsyncMock(side_effect=Exception("Fail"))
            mock_get_ct.return_value = mock_ct

            bundle = await collector.collect_by_variant("BRAF", "NM_004333.6:c.1799T>A")

        assert isinstance(bundle, EvidenceBundle)
        assert bundle.total_count == 0
        assert bundle.retrieved_at != ""

    async def test_collect_by_variant_caches_result(self, collector):
        """collect_by_variant() should cache results via variant_cache.set()."""
        with (
            patch.object(collector, "_merger") as mock_merger,
            patch.object(collector, "_get_clinvar") as mock_get_clinvar,
            patch.object(collector, "_get_pubmed") as mock_get_pubmed,
            patch.object(collector, "_get_clinicaltrials") as mock_get_ct,
            patch("src.backend.clinical.collector._AUTH_SOURCES", []),
            patch("src.backend.clinical.collector.variant_cache") as mock_vc,
        ):
            mock_vc.get.return_value = None
            mock_merger.merge_variant_evidence = AsyncMock(return_value={
                "evidence_items": [],
            })
            mock_clinvar = AsyncMock()
            mock_clinvar.search_variant = AsyncMock(return_value=[])
            mock_get_clinvar.return_value = mock_clinvar
            mock_pubmed = AsyncMock()
            mock_pubmed.search = AsyncMock(return_value=[])
            mock_get_pubmed.return_value = mock_pubmed
            mock_ct = AsyncMock()
            mock_ct.search = AsyncMock(return_value=[])
            mock_get_ct.return_value = mock_ct

            await collector.collect_by_variant("BRAF", "NM_004333.6:c.1799T>A")

            mock_vc.set.assert_called_once()
            args, _ = mock_vc.set.call_args
            assert args[0] == "variant:BRAF:NM_004333.6:c.1799T>A"

    # ── _collect_for_gene ───────────────────────────────────────────────

    async def test_collect_for_gene_uses_cache(self, collector):
        """_collect_for_gene() should return cached results."""
        ctx = MagicMock()
        cached_items = [EvidenceItem(source="Cached", gene_symbol="BRAF")]

        with patch("src.backend.clinical.collector.gene_cache") as mock_gc:
            mock_gc.get.return_value = cached_items

            items = await collector._collect_for_gene("BRAF", ctx)

        assert len(items) == 1
        assert items[0].source == "Cached"

    async def test_collect_for_gene_merger_failure(self, collector):
        """_collect_for_gene() should continue when merger fails."""
        ctx = MagicMock()

        with (
            patch("src.backend.clinical.collector.gene_cache") as mock_gc,
            patch.object(collector, "_merger") as mock_merger,
            patch.object(collector, "_get_clinvar") as mock_get_clinvar,
            patch.object(collector, "_get_pubmed") as mock_get_pubmed,
            patch.object(collector, "_get_clinicaltrials") as mock_get_ct,
        ):
            mock_gc.get.return_value = None
            mock_merger.merge_gene_evidence = AsyncMock(
                side_effect=Exception("Merger fail"),
            )
            mock_clinvar = AsyncMock()
            mock_clinvar.search_variant = AsyncMock(return_value=[])
            mock_get_clinvar.return_value = mock_clinvar
            mock_pubmed = AsyncMock()
            mock_pubmed.search = AsyncMock(return_value=[])
            mock_get_pubmed.return_value = mock_pubmed
            mock_ct = AsyncMock()
            mock_ct.search = AsyncMock(return_value=[])
            mock_get_ct.return_value = mock_ct

            items = await collector._collect_for_gene("BRAF", ctx)

        assert isinstance(items, list)
        assert len(items) == 0

    async def test_collect_for_gene_caches_result(self, collector):
        """_collect_for_gene() should store results in gene_cache."""
        ctx = MagicMock()

        with (
            patch("src.backend.clinical.collector.gene_cache") as mock_gc,
            patch.object(collector, "_merger") as mock_merger,
            patch.object(collector, "_get_clinvar") as mock_get_clinvar,
            patch.object(collector, "_get_pubmed") as mock_get_pubmed,
            patch.object(collector, "_get_clinicaltrials") as mock_get_ct,
        ):
            mock_gc.get.return_value = None
            mock_merger.merge_gene_evidence = AsyncMock(return_value={
                "evidence_items": [],
                "drug_interactions": [],
            })
            mock_clinvar = AsyncMock()
            mock_clinvar.search_variant = AsyncMock(return_value=[])
            mock_get_clinvar.return_value = mock_clinvar
            mock_pubmed = AsyncMock()
            mock_pubmed.search = AsyncMock(return_value=[])
            mock_get_pubmed.return_value = mock_pubmed
            mock_ct = AsyncMock()
            mock_ct.search = AsyncMock(return_value=[])
            mock_get_ct.return_value = mock_ct

            items = await collector._collect_for_gene("BRAF", ctx)

            mock_gc.set.assert_called_once()
            args, _ = mock_gc.set.call_args
            assert args[0] == "gene:BRAF"

    # ── _raw_to_evidence_item ───────────────────────────────────────────

    def test_raw_to_evidence_item_full(self):
        """_raw_to_evidence_item should map all fields from raw dict."""
        raw = {
            "_source": "CIViC",
            "source_record_id": "e123",
            "gene_symbol": "BRAF",
            "drug_name": "Vemurafenib",
            "disease": "Melanoma",
            "evidence_type": "predictive",
            "evidence_direction": "supporting",
            "evidence_level": "A",
            "source_native_level": "A",
            "clinical_significance": "sensitivity",
            "description": "Test description",
            "citation": "Test citation",
            "pmid": "99999",
            "url": "https://example.com",
            "confidence": "high",
            "_match_level": "exact_variant",
            "_conflict_status": "supporting",
        }
        item = EvidenceCollector._raw_to_evidence_item(raw)
        assert item.source == "CIViC"
        assert item.source_record_id == "e123"
        assert item.gene_symbol == "BRAF"
        assert item.drug_name == "Vemurafenib"
        assert item.disease == "Melanoma"
        assert item.evidence_level == "A"
        assert item.confidence == "high"
        assert item.match_level == "exact_variant"
        assert item.conflict_status == "supporting"

    def test_raw_to_evidence_item_minimal(self):
        """_raw_to_evidence_item should handle sparse dict."""
        raw = {"source": "PubMed", "title": "Article title"}
        item = EvidenceCollector._raw_to_evidence_item(raw)
        assert item.source == "PubMed"
        assert item.description == "Article title"
        assert item.source_record_id == ""
        assert item.gene_symbol == ""

    def test_raw_to_evidence_item_alternate_keys(self):
        """_raw_to_evidence_item should try alternate field names."""
        raw = {
            "source": "ClinVar",
            "variant_name": "NM_0001:c.123A>G",
            "journal": "Nature",
            "review_status": "criteria provided",
        }
        item = EvidenceCollector._raw_to_evidence_item(raw)
        assert item.description == "NM_0001:c.123A>G"
        assert item.citation == "Nature"
        assert item.confidence == "criteria provided"

    def test_raw_to_evidence_item_empty(self):
        """_raw_to_evidence_item should handle empty dict."""
        item = EvidenceCollector._raw_to_evidence_item({})
        assert item.source == ""
        assert item.gene_symbol == ""
        assert item.description == ""

    # ── _annotate_conflicts ─────────────────────────────────────────────

    def test_annotate_conflicts_empty(self):
        """_annotate_conflicts should handle empty list."""
        items: list[EvidenceItem] = []
        EvidenceCollector._annotate_conflicts(items)
        assert len(items) == 0

    def test_annotate_conflicts_no_drug(self):
        """Items without drug_name should get not_evaluable status."""
        items = [
            EvidenceItem(source="Test", gene_symbol="BRAF",
                         conflict_status=None),
        ]
        EvidenceCollector._annotate_conflicts(items)
        assert items[0].conflict_status == "not_evaluable"

    def test_annotate_conflicts_supporting(self):
        """Items with supporting direction should get supporting status."""
        items = [
            EvidenceItem(source="CIViC", gene_symbol="BRAF",
                         drug_name="Vemurafenib",
                         evidence_direction="supporting"),
        ]
        EvidenceCollector._annotate_conflicts(items)
        assert items[0].conflict_status == "not_evaluable"

    # ── Lazy adapter initialisation ─────────────────────────────────────

    def test_get_clinvar_lazy_init(self, collector):
        """_get_clinvar should initialise lazily and cache."""
        with patch("src.backend.clinical.collector.ClinVarAdapter") as mock_cls:
            adapter = collector._get_clinvar()
            assert adapter is mock_cls.return_value
            # Second call returns same instance
            assert collector._get_clinvar() is adapter
            mock_cls.assert_called_once()

    def test_get_pubmed_lazy_init(self, collector):
        """_get_pubmed should initialise lazily and cache."""
        with patch("src.backend.clinical.collector.PubMedAdapter") as mock_cls:
            adapter = collector._get_pubmed()
            assert adapter is mock_cls.return_value
            assert collector._get_pubmed() is adapter
            mock_cls.assert_called_once()

    def test_get_clinicaltrials_lazy_init(self, collector):
        """_get_clinicaltrials should initialise lazily and cache."""
        with patch("src.backend.clinical.collector.ClinicalTrialsAdapter") as mock_cls:
            adapter = collector._get_clinicaltrials()
            assert adapter is mock_cls.return_value
            assert collector._get_clinicaltrials() is adapter
            mock_cls.assert_called_once()
