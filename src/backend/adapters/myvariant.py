"""MyVariant.info REST adapter.

Provides a stable BaseAdapter implementation for public variant annotation and
query lookups.  The service is read-only and all returned records retain their
source payload so downstream evidence code can decide which fields to trust.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

from src.backend.adapters.base import AdapterResult, BaseAdapter

DEFAULT_BASE_URL = "https://myvariant.info/v1"
DEFAULT_TIMEOUT = 30


class MyVariantAdapter(BaseAdapter):
    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self._name = "myvariant"
        self._version = "v1"
        self._base_url = self.config.get("base_url", DEFAULT_BASE_URL).rstrip("/")
        self._timeout = float(self.config.get("timeout", DEFAULT_TIMEOUT))
        self._fields = self.config.get("fields", "all")

    async def health_check(self) -> dict:
        import httpx

        try:
            async with httpx.AsyncClient(timeout=min(self._timeout, 10)) as client:
                response = await client.get(
                    f"{self._base_url}/query",
                    params={"q": "rs58991260", "size": 0},
                )
            if response.status_code == 200:
                return {"status": "ok", "detail": "MyVariant.info reachable", "version": self._version}
            return {
                "status": "degraded",
                "detail": f"MyVariant.info returned HTTP {response.status_code}",
                "version": self._version,
            }
        except Exception as exc:
            return {"status": "degraded", "detail": str(exc), "version": self._version}

    def supports(self, query_type: str) -> bool:
        return query_type.lower() in {"variant", "annotate", "hgvs", "query", "rsid"}

    async def validate_input(self, payload: Any) -> list[str]:
        if not isinstance(payload, dict):
            return ["Payload must be an object"]
        if any(payload.get(key) for key in ("variant_id", "hgvs", "query", "rsid")):
            return []
        variants = payload.get("variants")
        if isinstance(variants, list) and variants:
            missing = [str(index) for index, item in enumerate(variants) if not self._variant_identifier(item)]
            return [f"Variants missing identifier at indexes: {', '.join(missing)}"] if missing else []
        return ["Provide variant_id, hgvs, rsid, query, or a non-empty variants list"]

    @staticmethod
    def _variant_identifier(item: Any) -> str | None:
        if isinstance(item, str):
            return item.strip() or None
        if not isinstance(item, dict):
            return None
        for key in ("variant_id", "hgvs", "rsid"):
            value = str(item.get(key, "")).strip()
            if value:
                return value
        chromosome = str(item.get("chromosome", "")).removeprefix("chr").strip()
        position = item.get("position")
        reference = str(item.get("reference", "")).strip()
        alternate = str(item.get("alternate", "")).strip()
        if chromosome and position and reference and alternate:
            return f"chr{chromosome}:g.{int(position)}{reference}>{alternate}"
        return None

    async def _fetch_variant(self, client, identifier: str) -> tuple[dict | None, str | None]:
        encoded = quote(identifier, safe="")
        response = await client.get(
            f"{self._base_url}/variant/{encoded}",
            params={"fields": self._fields},
        )
        if response.status_code == 200:
            data = response.json()
            return data if isinstance(data, dict) else {"value": data}, None
        if response.status_code == 404:
            return None, f"Variant not found: {identifier}"
        return None, f"MyVariant.info returned HTTP {response.status_code} for {identifier}"

    async def annotate(self, payload: Any, **kwargs) -> AdapterResult:
        import httpx

        errors = await self.validate_input(payload)
        request_id = kwargs.get("request_id", "unknown")
        if errors:
            return AdapterResult(
                source=self._name,
                source_version=self._version,
                retrieved_at=datetime.now(UTC).isoformat(),
                request_id=request_id,
                success=False,
                errors=errors,
            )

        records: list[dict] = []
        warnings: list[str] = []
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            query = str(payload.get("query", "")).strip()
            if query:
                response = await client.get(
                    f"{self._base_url}/query",
                    params={
                        "q": query,
                        "fields": self._fields,
                        "size": int(payload.get("size", 10)),
                        "from": int(payload.get("from", 0)),
                    },
                )
                if response.status_code != 200:
                    errors.append(f"MyVariant.info query returned HTTP {response.status_code}")
                else:
                    body = response.json()
                    hits = body.get("hits", []) if isinstance(body, dict) else []
                    records.extend(hit for hit in hits if isinstance(hit, dict))
            else:
                identifiers: list[str] = []
                direct = payload.get("variant_id") or payload.get("hgvs") or payload.get("rsid")
                if direct:
                    identifiers.append(str(direct).strip())
                for item in payload.get("variants", []) or []:
                    identifier = self._variant_identifier(item)
                    if identifier:
                        identifiers.append(identifier)
                for identifier in dict.fromkeys(identifiers):
                    record, error = await self._fetch_variant(client, identifier)
                    if record is not None:
                        record.setdefault("query_identifier", identifier)
                        records.append(record)
                    elif error:
                        warnings.append(error)

        return AdapterResult(
            source=self._name,
            source_version=self._version,
            retrieved_at=datetime.now(UTC).isoformat(),
            request_id=request_id,
            success=not errors,
            records=records,
            warnings=warnings,
            errors=errors,
            license="MyVariant.info data sources retain their original licenses; inspect source fields before reuse.",
            metadata={"base_url": self._base_url},
        )

    def normalize_response(self, raw: Any) -> AdapterResult:
        if isinstance(raw, dict) and isinstance(raw.get("hits"), list):
            records = [item for item in raw["hits"] if isinstance(item, dict)]
        elif isinstance(raw, list):
            records = [item for item in raw if isinstance(item, dict)]
        elif isinstance(raw, dict):
            records = [raw]
        else:
            records = []
        return AdapterResult(
            source=self._name,
            source_version=self._version,
            retrieved_at=datetime.now(UTC).isoformat(),
            request_id="normalize_response",
            success=bool(records),
            records=records,
            errors=[] if records else ["Unsupported or empty MyVariant.info response"],
        )


__all__ = ["MyVariantAdapter"]
