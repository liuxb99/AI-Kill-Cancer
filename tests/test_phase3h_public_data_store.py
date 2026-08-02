"""Phase 3H content-addressed public data download tests."""

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path

import pytest

from src.backend.sync.public_data_store import PublicDataIntegrityError, PublicDataStore


def test_existing_payload_is_not_downloaded_again(tmp_path: Path):
    store = PublicDataStore(tmp_path)
    calls = 0

    def fetch() -> bytes:
        nonlocal calls
        calls += 1
        return b"public research payload"

    first = store.get_or_fetch(source="gdc", identity="same-request", fetcher=fetch)
    second = store.get_or_fetch(source="gdc", identity="same-request", fetcher=fetch)

    assert calls == 1
    assert first.cache_hit is False
    assert second.cache_hit is True
    assert second.content == first.content
    assert second.sha256 == hashlib.sha256(first.content).hexdigest()


def test_different_request_identity_creates_distinct_payload(tmp_path: Path):
    store = PublicDataStore(tmp_path)
    first = store.get_or_fetch(source="pubmed", identity="query-a", fetcher=lambda: b"a")
    second = store.get_or_fetch(source="pubmed", identity="query-b", fetcher=lambda: b"b")

    assert first.payload_path != second.payload_path
    assert store.stats()["payload_count"] == 2


def test_corrupted_cached_payload_is_downloaded_again(tmp_path: Path):
    store = PublicDataStore(tmp_path)
    calls = 0

    def fetch() -> bytes:
        nonlocal calls
        calls += 1
        return f"payload-{calls}".encode()

    first = store.get_or_fetch(source="openfda", identity="label", fetcher=fetch)
    first.payload_path.write_bytes(b"corrupted")
    second = store.get_or_fetch(source="openfda", identity="label", fetcher=fetch)

    assert calls == 2
    assert second.cache_hit is False
    assert second.content == b"payload-2"


def test_expected_md5_is_verified_before_persistence(tmp_path: Path):
    store = PublicDataStore(tmp_path)
    with pytest.raises(PublicDataIntegrityError, match="MD5 mismatch"):
        store.get_or_fetch(
            source="gdc",
            identity="maf-file",
            fetcher=lambda: b"wrong",
            expected_md5="00000000000000000000000000000000",
        )
    assert store.stats()["payload_count"] == 0


def test_force_refresh_replaces_existing_payload(tmp_path: Path):
    base = PublicDataStore(tmp_path)
    base.get_or_fetch(source="civic", identity="genes", fetcher=lambda: b"v1")

    refreshed = PublicDataStore(tmp_path, force_refresh=True).get_or_fetch(
        source="civic", identity="genes", fetcher=lambda: b"v2"
    )

    assert refreshed.cache_hit is False
    assert refreshed.content == b"v2"


def test_async_existing_payload_is_not_downloaded_again(tmp_path: Path):
    async def scenario() -> None:
        store = PublicDataStore(tmp_path)
        calls = 0

        async def fetch() -> bytes:
            nonlocal calls
            calls += 1
            return b"async-public-data"

        first = await store.aget_or_fetch(source="clinicaltrials", identity="ptc", fetcher=fetch)
        second = await store.aget_or_fetch(source="clinicaltrials", identity="ptc", fetcher=fetch)
        assert first.cache_hit is False
        assert second.cache_hit is True
        assert calls == 1

    asyncio.run(scenario())


def test_canonical_identity_is_order_independent(tmp_path: Path):
    store = PublicDataStore(tmp_path)
    left = store.canonical_identity("https://example.test", {"b": 2, "a": 1})
    right = store.canonical_identity("https://example.test", {"a": 1, "b": 2})
    assert left == right
