"""Content-addressed storage for legally downloadable public research data.

The store keeps the exact response bytes and a small JSON manifest. A request
with the same source and canonical identity reuses the verified local payload
instead of downloading it again. Writes are atomic and corrupted payloads are
never returned.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable

_SAFE = re.compile(r"[^a-zA-Z0-9_.-]+")


@dataclass(frozen=True)
class StoredPayload:
    content: bytes
    cache_hit: bool
    sha256: str
    payload_path: Path
    manifest_path: Path
    metadata: dict[str, Any]


class PublicDataIntegrityError(RuntimeError):
    """Raised when a cached or downloaded payload fails integrity validation."""


class PublicDataStore:
    """Atomic local cache for raw public-source responses and files."""

    def __init__(self, root: str | Path | None = None, *, force_refresh: bool = False):
        configured = root or os.getenv("PUBLIC_DATA_DIR") or "var/public-data"
        self.root = Path(configured).expanduser().resolve()
        self.force_refresh = force_refresh
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def canonical_identity(url: str, params: dict[str, Any] | None = None) -> str:
        normalized = {
            "url": url,
            "params": {
                key: params[key]
                for key in sorted(params or {})
                if params[key] is not None
            },
        }
        return json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    def get_or_fetch(
        self,
        *,
        source: str,
        identity: str,
        fetcher: Callable[[], bytes],
        expected_md5: str | None = None,
        metadata: dict[str, Any] | None = None,
        suffix: str = ".bin",
    ) -> StoredPayload:
        paths = self._paths(source, identity, suffix)
        if not self.force_refresh:
            cached = self._read_verified(*paths)
            if cached is not None:
                return cached

        content = fetcher()
        return self._persist(
            source=source,
            identity=identity,
            content=content,
            expected_md5=expected_md5,
            metadata=metadata or {},
            paths=paths,
        )

    async def aget_or_fetch(
        self,
        *,
        source: str,
        identity: str,
        fetcher: Callable[[], Awaitable[bytes]],
        expected_md5: str | None = None,
        metadata: dict[str, Any] | None = None,
        suffix: str = ".bin",
    ) -> StoredPayload:
        paths = self._paths(source, identity, suffix)
        if not self.force_refresh:
            cached = await asyncio.to_thread(self._read_verified, *paths)
            if cached is not None:
                return cached

        content = await fetcher()
        return await asyncio.to_thread(
            self._persist,
            source=source,
            identity=identity,
            content=content,
            expected_md5=expected_md5,
            metadata=metadata or {},
            paths=paths,
        )

    def stats(self) -> dict[str, Any]:
        manifests = list(self.root.glob("*/*.json"))
        payloads = [path for path in self.root.glob("*/*") if path.suffix != ".json"]
        return {
            "root": str(self.root),
            "manifest_count": len(manifests),
            "payload_count": len(payloads),
            "bytes": sum(path.stat().st_size for path in payloads if path.is_file()),
        }

    def _paths(self, source: str, identity: str, suffix: str) -> tuple[Path, Path]:
        safe_source = _SAFE.sub("_", source.strip().lower()).strip("_") or "unknown"
        key = hashlib.sha256(identity.encode("utf-8")).hexdigest()
        directory = self.root / safe_source
        directory.mkdir(parents=True, exist_ok=True)
        clean_suffix = suffix if suffix.startswith(".") else f".{suffix}"
        return directory / f"{key}{clean_suffix}", directory / f"{key}.json"

    def _read_verified(self, payload_path: Path, manifest_path: Path) -> StoredPayload | None:
        if not payload_path.is_file() or not manifest_path.is_file():
            return None
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            content = payload_path.read_bytes()
        except (OSError, ValueError, json.JSONDecodeError):
            return None
        digest = hashlib.sha256(content).hexdigest()
        if digest != manifest.get("sha256"):
            return None
        expected_md5 = manifest.get("expected_md5")
        if expected_md5 and hashlib.md5(content, usedforsecurity=False).hexdigest() != expected_md5:
            return None
        return StoredPayload(
            content=content,
            cache_hit=True,
            sha256=digest,
            payload_path=payload_path,
            manifest_path=manifest_path,
            metadata=manifest,
        )

    def _persist(
        self,
        *,
        source: str,
        identity: str,
        content: bytes,
        expected_md5: str | None,
        metadata: dict[str, Any],
        paths: tuple[Path, Path],
    ) -> StoredPayload:
        if not isinstance(content, bytes):
            raise TypeError("public data fetcher must return bytes")
        payload_path, manifest_path = paths
        digest = hashlib.sha256(content).hexdigest()
        actual_md5 = hashlib.md5(content, usedforsecurity=False).hexdigest()
        if expected_md5 and actual_md5.lower() != expected_md5.lower():
            raise PublicDataIntegrityError(
                f"MD5 mismatch for {source}: expected {expected_md5}, got {actual_md5}"
            )
        manifest = {
            "source": source,
            "identity": identity,
            "sha256": digest,
            "md5": actual_md5,
            "expected_md5": expected_md5,
            "size_bytes": len(content),
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            **metadata,
        }
        self._atomic_write(payload_path, content)
        self._atomic_write(
            manifest_path,
            (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        )
        return StoredPayload(
            content=content,
            cache_hit=False,
            sha256=digest,
            payload_path=payload_path,
            manifest_path=manifest_path,
            metadata=manifest,
        )

    @staticmethod
    def _atomic_write(path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, path)
        finally:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass


__all__ = [
    "PublicDataIntegrityError",
    "PublicDataStore",
    "StoredPayload",
]
