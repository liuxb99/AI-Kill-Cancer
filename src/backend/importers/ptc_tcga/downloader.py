"""GDC API client for public TCGA-THCA clinical and mutation data."""

from __future__ import annotations

import inspect
import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from src.backend.importers.ptc_tcga.maf_parser import merge_variants_into_cases, parse_maf_bytes
from src.backend.sync.public_data_store import PublicDataStore

GDC_API = "https://api.gdc.cancer.gov"


@dataclass(frozen=True)
class GDCDownloadResult:
    records: list[dict[str, Any]]
    total: int
    source_version: str | None
    mutation_files: int = 0
    mutation_variants: int = 0


class GDCClient:
    def __init__(
        self,
        base_url: str = GDC_API,
        timeout: int = 60,
        store: PublicDataStore | None = None,
        *,
        force_refresh: bool = False,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.store = store or PublicDataStore(force_refresh=force_refresh)

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

    def fetch_ptc_cases_with_mutations(
        self,
        *,
        size: int = 100,
        offset: int = 0,
        mutation_files: int = 1,
    ) -> GDCDownloadResult:
        """Download clinical cases and merge public masked somatic mutations.

        GDC mutation files are project-level MAFs. One current open file is
        normally sufficient for the MVP; callers may request more files when
        validating multiple workflows. Duplicate variants are removed by their
        normalized content before persistence.
        """
        clinical = self.fetch_ptc_cases(size=size, offset=offset)
        if mutation_files <= 0:
            return clinical
        manifest = self.fetch_somatic_mutation_manifest(size=min(mutation_files, 20))
        merged_by_case: dict[str, list[dict[str, Any]]] = {}
        seen: dict[str, set[tuple[Any, ...]]] = {}
        downloaded = 0
        for item in manifest[:mutation_files]:
            file_id = item.get("file_id")
            if not file_id:
                continue
            downloader = self.download_public_file
            if "expected_md5" in inspect.signature(downloader).parameters:
                raw_payload = downloader(str(file_id), expected_md5=item.get("md5sum"))
            else:  # Backward-compatible adapter/test-double contract.
                raw_payload = downloader(str(file_id))
            grouped = parse_maf_bytes(raw_payload)
            downloaded += 1
            for case_id, variants in grouped.items():
                target = merged_by_case.setdefault(case_id, [])
                keys = seen.setdefault(case_id, set())
                for variant in variants:
                    key = (
                        variant.get("gene"),
                        variant.get("chromosome"),
                        variant.get("position"),
                        variant.get("reference"),
                        variant.get("alternate"),
                        variant.get("classification"),
                        variant.get("protein_change"),
                    )
                    if key not in keys:
                        keys.add(key)
                        target.append(variant)
        records = merge_variants_into_cases(clinical.records, merged_by_case)
        return GDCDownloadResult(
            records=records,
            total=clinical.total,
            source_version=clinical.source_version,
            mutation_files=downloaded,
            mutation_variants=sum(len(item.get("variants", [])) for item in records),
        )

    def fetch_somatic_mutation_manifest(self, *, size: int = 1000) -> list[dict[str, Any]]:
        """Return metadata for public masked somatic mutation MAF files."""
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

    def download_public_file(
        self, file_id: str, *, expected_md5: str | None = None
    ) -> bytes:
        if not file_id or "/" in file_id or ".." in file_id:
            raise ValueError("invalid GDC file id")
        url = f"{self.base_url}/data/{file_id}"

        def fetch() -> bytes:
            request = Request(
                url,
                headers={"Accept": "application/octet-stream", "User-Agent": "AI-Kill-Cancer/ptc-importer"},
            )
            with urlopen(request, timeout=self.timeout) as response:  # nosec B310 - fixed HTTPS GDC endpoint
                return response.read()

        stored = self.store.get_or_fetch(
            source="gdc",
            identity=self.store.canonical_identity(url),
            fetcher=fetch,
            expected_md5=expected_md5,
            metadata={"url": url, "file_id": file_id},
            suffix=".maf",
        )
        return stored.content

    def _get_json(self, path: str) -> dict[str, Any]:
        url = f"{self.base_url}{path}"

        def fetch() -> bytes:
            request = Request(
                url,
                headers={"Accept": "application/json", "User-Agent": "AI-Kill-Cancer/ptc-importer"},
            )
            with urlopen(request, timeout=self.timeout) as response:  # nosec B310 - configured trusted GDC endpoint
                return response.read()

        stored = self.store.get_or_fetch(
            source="gdc",
            identity=self.store.canonical_identity(url),
            fetcher=fetch,
            metadata={"url": url, "media_type": "application/json"},
            suffix=".json",
        )
        return json.loads(stored.content.decode("utf-8"))

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
