"""Local DRKG dataset adapter.

DRKG is distributed as a TSV of ``(head, relation, tail)`` triplets.  This
adapter intentionally does not auto-download the multi-million-edge dataset;
point ``DRKG_PATH`` (or ``config['path']``) at a local ``drkg.tsv`` file.
Queries stream the file and return bounded exact/substring matches so the
integration works on ordinary local research workstations without loading the
whole graph into RAM.
"""

from __future__ import annotations

import csv
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.backend.adapters.base import AdapterResult, BaseAdapter

_DEFAULT_LIMIT = 100
_MAX_LIMIT = 5000


class DRKGAdapter(BaseAdapter):
    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self._name = "drkg"
        self._version = "drkg.tsv"
        configured = self.config.get("path") or os.getenv("DRKG_PATH", "")
        self._path = Path(str(configured)).expanduser() if configured else None
        self._default_limit = int(self.config.get("limit", _DEFAULT_LIMIT))

    def _resolved_path(self) -> Path | None:
        if self._path is None:
            return None
        path = self._path.resolve()
        return path if path.is_file() else None

    async def health_check(self) -> dict:
        path = self._resolved_path()
        if path is None:
            return {
                "status": "unavailable",
                "detail": "DRKG dataset not configured; set DRKG_PATH to drkg.tsv",
                "version": self._version,
            }
        try:
            with path.open("r", encoding="utf-8", newline="") as handle:
                first = handle.readline().rstrip("\n\r")
            fields = first.split("\t") if first else []
            if len(fields) < 3:
                return {
                    "status": "degraded",
                    "detail": "DRKG file does not look like head/relation/tail TSV",
                    "version": self._version,
                }
            return {
                "status": "ok",
                "detail": f"DRKG dataset ready: {path}",
                "version": self._version,
                "size_bytes": path.stat().st_size,
            }
        except OSError as exc:
            return {"status": "degraded", "detail": str(exc), "version": self._version}

    def supports(self, query_type: str) -> bool:
        return query_type.lower() in {"query", "entity", "gene", "drug", "relation", "neighbors"}

    async def validate_input(self, payload: Any) -> list[str]:
        if not isinstance(payload, dict):
            return ["Payload must be an object"]
        query = str(payload.get("query") or payload.get("entity") or "").strip()
        relation = str(payload.get("relation") or "").strip()
        if not query and not relation:
            return ["Provide query/entity and/or relation"]
        try:
            limit = int(payload.get("limit", self._default_limit))
        except (TypeError, ValueError):
            return ["limit must be an integer"]
        if not 1 <= limit <= _MAX_LIMIT:
            return [f"limit must be between 1 and {_MAX_LIMIT}"]
        mode = str(payload.get("match", "contains")).lower()
        if mode not in {"exact", "contains"}:
            return ["match must be 'exact' or 'contains'"]
        return []

    @staticmethod
    def _matches(value: str, query: str, mode: str) -> bool:
        if not query:
            return True
        if mode == "exact":
            return value.casefold() == query.casefold()
        return query.casefold() in value.casefold()

    async def annotate(self, payload: Any, **kwargs) -> AdapterResult:
        request_id = kwargs.get("request_id", "unknown")
        retrieved_at = datetime.now(UTC).isoformat()
        errors = await self.validate_input(payload)
        if errors:
            return AdapterResult(
                source=self._name,
                source_version=self._version,
                retrieved_at=retrieved_at,
                request_id=request_id,
                success=False,
                errors=errors,
            )
        path = self._resolved_path()
        if path is None:
            return AdapterResult(
                source=self._name,
                source_version=self._version,
                retrieved_at=retrieved_at,
                request_id=request_id,
                success=False,
                errors=["DRKG dataset is not configured; set DRKG_PATH"],
            )

        query = str(payload.get("query") or payload.get("entity") or "").strip()
        relation_query = str(payload.get("relation") or "").strip()
        mode = str(payload.get("match", "contains")).lower()
        limit = min(int(payload.get("limit", self._default_limit)), _MAX_LIMIT)
        records: list[dict[str, str]] = []
        scanned = 0
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle, delimiter="\t")
            for row in reader:
                if len(row) < 3:
                    continue
                scanned += 1
                head, relation, tail = row[0], row[1], row[2]
                entity_match = self._matches(head, query, mode) or self._matches(tail, query, mode)
                relation_match = self._matches(relation, relation_query, mode)
                if entity_match and relation_match:
                    records.append({"head": head, "relation": relation, "tail": tail})
                    if len(records) >= limit:
                        break

        return AdapterResult(
            source=self._name,
            source_version=self._version,
            retrieved_at=retrieved_at,
            request_id=request_id,
            success=True,
            records=records,
            warnings=[] if records else ["No DRKG triplets matched the query"],
            license="DRKG aggregates multiple sources; downstream use must respect source-specific licenses.",
            metadata={
                "path": str(path),
                "scanned_rows": scanned,
                "limit": limit,
                "match": mode,
            },
        )

    def normalize_response(self, raw: Any) -> AdapterResult:
        records: list[dict] = []
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    records.append(item)
                elif isinstance(item, (list, tuple)) and len(item) >= 3:
                    records.append({"head": item[0], "relation": item[1], "tail": item[2]})
        elif isinstance(raw, dict):
            records = [raw]
        return AdapterResult(
            source=self._name,
            source_version=self._version,
            retrieved_at=datetime.now(UTC).isoformat(),
            request_id="normalize_response",
            success=bool(records),
            records=records,
            errors=[] if records else ["Unsupported or empty DRKG response"],
        )


__all__ = ["DRKGAdapter"]
