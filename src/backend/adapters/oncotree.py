"""OncoTree REST adapter.

Uses the public OncoTree API for cancer-type lookup and search.  Results are
returned as source records without converting ontology codes into clinical
recommendations.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

from src.backend.adapters.base import AdapterResult, BaseAdapter

_DEFAULT_BASE_URL = "https://oncotree.info/api"
_DEFAULT_VERSION = "oncotree_latest_stable"
_DEFAULT_TIMEOUT = 30


class OncoTreeAdapter(BaseAdapter):
    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self._name = "oncotree"
        self._version = str(self.config.get("version", _DEFAULT_VERSION))
        self._base_url = str(self.config.get("base_url", _DEFAULT_BASE_URL)).rstrip("/")
        self._timeout = float(self.config.get("timeout", _DEFAULT_TIMEOUT))

    async def health_check(self) -> dict:
        import httpx

        try:
            async with httpx.AsyncClient(timeout=min(self._timeout, 10)) as client:
                response = await client.get(f"{self._base_url}/versions")
            if response.status_code == 200:
                return {"status": "ok", "detail": "OncoTree API reachable", "version": self._version}
            return {
                "status": "degraded",
                "detail": f"OncoTree API returned HTTP {response.status_code}",
                "version": self._version,
            }
        except Exception as exc:
            return {"status": "degraded", "detail": str(exc), "version": self._version}

    def supports(self, query_type: str) -> bool:
        return query_type.lower() in {"tumor_type", "cancer_type", "oncotree", "code", "search", "main_type"}

    async def validate_input(self, payload: Any) -> list[str]:
        if not isinstance(payload, dict):
            return ["Payload must be an object"]
        if any(str(payload.get(key, "")).strip() for key in ("code", "name", "search", "main_type")):
            return []
        if payload.get("all") is True:
            return []
        return ["Provide code, name/search, main_type, or all=true"]

    @staticmethod
    def _records(raw: Any) -> list[dict]:
        if isinstance(raw, list):
            return [item for item in raw if isinstance(item, dict)]
        if isinstance(raw, dict):
            for key in ("items", "results", "data"):
                value = raw.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
            return [raw]
        return []

    async def annotate(self, payload: Any, **kwargs) -> AdapterResult:
        import httpx

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

        params = {"version": str(payload.get("version", self._version))}
        if payload.get("all") is True:
            path = "/tumorTypes"
        elif payload.get("code"):
            path = f"/tumorTypes/search/code/{quote(str(payload['code']).strip(), safe='')}"
            params.update({"exactMatch": "true"})
        elif payload.get("main_type"):
            path = f"/tumorTypes/search/mainType/{quote(str(payload['main_type']).strip(), safe='')}"
            params.update({"exactMatch": str(bool(payload.get('exact_match', True))).lower()})
        else:
            value = str(payload.get("name") or payload.get("search") or "").strip()
            search_type = str(payload.get("search_type", "name"))
            if search_type not in {"name", "code", "mainType", "nci", "umls"}:
                return AdapterResult(
                    source=self._name,
                    source_version=self._version,
                    retrieved_at=retrieved_at,
                    request_id=request_id,
                    success=False,
                    errors=["Unsupported OncoTree search_type"],
                )
            path = f"/tumorTypes/search/{search_type}/{quote(value, safe='')}"
            params.update({
                "exactMatch": str(bool(payload.get("exact_match", False))).lower(),
                "level": str(payload.get("level", "1,2,3,4,5,6,7")),
            })

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(f"{self._base_url}{path}", params=params)
        except Exception as exc:
            return AdapterResult(
                source=self._name,
                source_version=self._version,
                retrieved_at=retrieved_at,
                request_id=request_id,
                success=False,
                errors=[f"OncoTree request failed: {exc}"],
            )

        if response.status_code != 200:
            return AdapterResult(
                source=self._name,
                source_version=self._version,
                retrieved_at=retrieved_at,
                request_id=request_id,
                success=False,
                errors=[f"OncoTree API returned HTTP {response.status_code}"],
            )
        try:
            raw = response.json()
        except ValueError:
            return AdapterResult(
                source=self._name,
                source_version=self._version,
                retrieved_at=retrieved_at,
                request_id=request_id,
                success=False,
                errors=["OncoTree API returned non-JSON content"],
            )
        records = self._records(raw)
        return AdapterResult(
            source=self._name,
            source_version=params["version"],
            retrieved_at=retrieved_at,
            request_id=request_id,
            success=True,
            records=records,
            warnings=[] if records else ["OncoTree returned no matching tumor types"],
            license="OncoTree is licensed CC BY 4.0; preserve attribution.",
            metadata={"endpoint": path, "version": params["version"]},
        )

    def normalize_response(self, raw: Any) -> AdapterResult:
        records = self._records(raw)
        return AdapterResult(
            source=self._name,
            source_version=self._version,
            retrieved_at=datetime.now(UTC).isoformat(),
            request_id="normalize_response",
            success=bool(records),
            records=records,
            errors=[] if records else ["Unsupported or empty OncoTree response"],
            license="OncoTree is licensed CC BY 4.0; preserve attribution.",
        )


__all__ = ["OncoTreeAdapter"]
