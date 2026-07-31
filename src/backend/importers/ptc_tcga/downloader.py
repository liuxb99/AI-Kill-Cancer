"""Minimal GDC API client for public TCGA-THCA data.

The first slice intentionally downloads compact clinical metadata through the
GDC cases endpoint.  Large molecular files remain optional and are represented
by manifest metadata so the pipeline can grow without changing its contract.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


GDC_API = "https://api.gdc.cancer.gov"


@dataclass(frozen=True)
class GDCDownloadResult:
    records: list[dict[str, Any]]
    total: int
    source_version: str | None


class GDCClient:
    def __init__(self, base_url: str = GDC_API, timeout: int = 60):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def fetch_ptc_cases(self, *, size: int = 100, offset: int = 0) -> GDCDownloadResult:
        if size < 1 or size > 10_000:
            raise ValueError("size must be between 1 and 10000")
        if offset < 0:
            raise ValueError("offset must be non-negative")

        filters = {
            "op": "and",
            "content": [
                {
                    "op": "in",
                    "content": {
                        "field": "cases.project.project_id",
                        "value": ["TCGA-THCA"],
                    },
                }
            ],
        }
        fields = ",".join(
            [
                "case_id",
                "submitter_id",
                "project.project_id",
                "demographic.gender",
                "demographic.sex_at_birth",
                "demographic.vital_status",
                "demographic.days_to_birth",
                "demographic.days_to_death",
                "diagnoses.ajcc_pathologic_stage",
                "diagnoses.ajcc_pathologic_t",
                "diagnoses.ajcc_pathologic_n",
                "diagnoses.ajcc_pathologic_m",
                "diagnoses.days_to_last_follow_up",
                "diagnoses.primary_diagnosis",
                "diagnoses.morphology",
            ]
        )
        params = {
            "filters": json.dumps(filters, separators=(",", ":")),
            "fields": fields,
            "expand": "demographic,diagnoses",
            "format": "JSON",
            "size": str(size),
            "from": str(offset),
        }
        payload = self._get_json(f"/cases?{urlencode(params)}")
        hits = payload.get("data", {}).get("hits", [])
        records = [self._flatten_case(hit) for hit in hits]
        pagination = payload.get("data", {}).get("pagination", {})
        return GDCDownloadResult(
            records=records,
            total=int(pagination.get("total", len(records))),
            source_version=payload.get("data", {}).get("release"),
        )

    def fetch_somatic_mutation_manifest(self, *, size: int = 1000) -> list[dict[str, Any]]:
        """Return metadata for public masked somatic mutation MAF files.

        The caller can subsequently download selected public file UUIDs through
        the GDC ``/data/{file_id}`` endpoint or the official gdc-client.
        """
        filters = {
            "op": "and",
            "content": [
                {
                    "op": "in",
                    "content": {
                        "field": "cases.project.project_id",
                        "value": ["TCGA-THCA"],
                    },
                },
                {
                    "op": "in",
                    "content": {
                        "field": "files.data_type",
                        "value": ["Masked Somatic Mutation"],
                    },
                },
                {
                    "op": "in",
                    "content": {
                        "field": "files.access",
                        "value": ["open"],
                    },
                },
            ],
        }
        params = {
            "filters": json.dumps(filters, separators=(",", ":")),
            "fields": "file_id,file_name,md5sum,file_size,data_format,cases.submitter_id",
            "format": "JSON",
            "size": str(size),
        }
        payload = self._get_json(f"/files?{urlencode(params)}")
        return list(payload.get("data", {}).get("hits", []))

    def download_public_file(self, file_id: str) -> bytes:
        if not file_id or "/" in file_id or ".." in file_id:
            raise ValueError("invalid GDC file id")
        request = Request(
            f"{self.base_url}/data/{file_id}",
            headers={"Accept": "application/octet-stream", "User-Agent": "AI-Kill-Cancer/ptc-importer"},
        )
        with urlopen(request, timeout=self.timeout) as response:  # nosec B310 - fixed HTTPS GDC endpoint
            return response.read()

    def _get_json(self, path: str) -> dict[str, Any]:
        request = Request(
            f"{self.base_url}{path}",
            headers={"Accept": "application/json", "User-Agent": "AI-Kill-Cancer/ptc-importer"},
        )
        with urlopen(request, timeout=self.timeout) as response:  # nosec B310 - configured trusted GDC endpoint
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def _flatten_case(hit: dict[str, Any]) -> dict[str, Any]:
        demographic = hit.get("demographic") or {}
        diagnoses = hit.get("diagnoses") or []
        diagnosis = diagnoses[0] if diagnoses else {}
        project = hit.get("project") or {}
        return {
            "case_id": hit.get("submitter_id") or hit.get("case_id"),
            "source_record_id": hit.get("case_id"),
            "source_dataset": "TCGA-THCA",
            "source_project": project.get("project_id") or "TCGA-THCA",
            "sex": demographic.get("sex_at_birth") or demographic.get("gender"),
            "days_to_birth": demographic.get("days_to_birth"),
            "vital_status": demographic.get("vital_status"),
            "days_to_death": demographic.get("days_to_death"),
            "pathologic_stage": diagnosis.get("ajcc_pathologic_stage"),
            "t_status": diagnosis.get("ajcc_pathologic_t"),
            "n_status": diagnosis.get("ajcc_pathologic_n"),
            "m_status": diagnosis.get("ajcc_pathologic_m"),
            "days_to_last_follow_up": diagnosis.get("days_to_last_follow_up"),
            "primary_diagnosis": diagnosis.get("primary_diagnosis"),
            "morphology": diagnosis.get("morphology"),
            "variants": [],
        }


__all__ = ["GDCClient", "GDCDownloadResult", "GDC_API"]
