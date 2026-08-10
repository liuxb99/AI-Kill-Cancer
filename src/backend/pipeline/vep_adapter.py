"""
Ensembl VEP adapter — real REST API integration.

Uses the Ensembl REST API (https://rest.ensembl.org/vep/human/region)
for variant annotation when local VEP is not installed.
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import UTC, datetime
from typing import Any

from src.backend.adapters.base import AdapterResult, BaseAdapter

logger = logging.getLogger(__name__)

ENSEMBL_REST_URL = "https://rest.ensembl.org"
VEP_ENDPOINT = "/vep/human/region"
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 2
_HGVS_G_RE = re.compile(r"^(\d+|X|Y|MT|chr\d+|chrX|chrY|chrMT):g\.(\d+)([ACGTN]+)>([ACGTN]+)$")


def _build_region_string(chromosome: str, position: int, ref: str, alt: str) -> str:
    chrom = chromosome.removeprefix("chr")
    start = position
    end = position + len(ref) - 1
    return f"{chrom}:{start}-{end}:{alt}"


def _parse_vep_consequence(consequence: str) -> str:
    return consequence.lower().replace(" ", "_")


def _selection_reason(index: int, tc: dict) -> str:
    if index == 0:
        if tc.get("mane_select"):
            return "MANE Select transcript"
        if tc.get("mane_plus_clinical"):
            return "MANE Plus Clinical transcript"
        if tc.get("canonical") == 1:
            return "Canonical transcript"
        if tc.get("biotype") == "protein_coding":
            return "protein_coding transcript (highest impact)"
        return "Highest priority transcript"
    return f"Additional transcript (priority {index + 1})"


def _extract_vep_results(data: Any, region: str) -> list[dict]:
    results: list[dict] = []
    items = data if isinstance(data, list) else [data]
    for item in items:
        if not isinstance(item, dict):
            continue
        most_severe = str(item.get("most_severe_consequence", ""))
        allele_str = item.get("allele_string", "")
        transcript_consequences = item.get("transcript_consequences", []) or []

        def _transcript_priority(tc: dict) -> tuple:
            is_mane = 0 if tc.get("mane_select") or tc.get("mane_plus_clinical") else 1
            is_canonical = 0 if tc.get("canonical") == 1 else 1
            is_protein_coding = 0 if tc.get("biotype") == "protein_coding" else 1
            impact_order = {"HIGH": 0, "MODERATE": 1, "LOW": 2, "MODIFIER": 3}
            impact = impact_order.get(tc.get("impact", ""), 4)
            return is_mane, is_canonical, is_protein_coding, impact

        sorted_tcs = sorted(
            [tc for tc in transcript_consequences if isinstance(tc, dict)],
            key=_transcript_priority,
        )
        for index, tc in enumerate(sorted_tcs):
            terms = tc.get("consequence_terms", []) or []
            result = {
                "region": region,
                "allele_string": allele_str,
                "gene_symbol": tc.get("gene_symbol", ""),
                "gene_id": tc.get("gene_id", ""),
                "transcript_id": tc.get("transcript_id", ""),
                "protein_id": tc.get("protein_id", ""),
                "consequence": (
                    _parse_vep_consequence(str(terms[0]))
                    if terms
                    else most_severe.lower()
                ),
                "all_consequences": [str(value).lower() for value in terms],
                "hgvs_c": tc.get("hgvsc") or tc.get("hgvs_transcript", ""),
                "hgvs_p": tc.get("hgvsp") or tc.get("hgvs_short", ""),
                "protein_change": tc.get("hgvsp") or tc.get("hgvs_short", ""),
                "codons": tc.get("codons", ""),
                "amino_acids": tc.get("amino_acids", ""),
                "strand": tc.get("strand", 0),
                "biotype": tc.get("biotype", ""),
                "impact": tc.get("impact", ""),
                "exon": tc.get("exon", ""),
                "intron": tc.get("intron", ""),
                "domains": tc.get("domains", []),
                "sift_prediction": tc.get("sift_prediction", ""),
                "polyphen_prediction": tc.get("polyphen_prediction", ""),
                "is_mane_select": bool(tc.get("mane_select")),
                "is_canonical": tc.get("canonical") == 1,
                "is_selected": index == 0,
                "selection_reason": _selection_reason(index, tc),
            }
            results.append(result)

        if not sorted_tcs:
            results.append(
                {
                    "region": region,
                    "allele_string": allele_str,
                    "gene_symbol": item.get("gene_symbol", ""),
                    "colocated_variants": item.get("colocated_variants", []),
                    "consequence": most_severe.lower() if most_severe else "intergenic_variant",
                    "all_consequences": [most_severe.lower()] if most_severe else ["intergenic_variant"],
                    "hgvs_c": "",
                    "hgvs_p": "",
                    "protein_change": "",
                    "is_selected": True,
                    "selection_reason": "no_transcript_consequences",
                }
            )
    return results


def _infer_region(item: dict[str, Any]) -> str:
    region = str(item.get("region", "")).strip()
    if region:
        return region
    chromosome = str(item.get("seq_region_name") or item.get("chromosome") or "").strip()
    start = item.get("start") or item.get("position")
    allele_string = str(item.get("allele_string", ""))
    alternate = ""
    if "/" in allele_string:
        alternate = allele_string.split("/")[-1]
    elif item.get("alternate"):
        alternate = str(item["alternate"])
    if chromosome and start and alternate:
        return _build_region_string(chromosome, int(start), str(item.get("reference", "N")), alternate)
    return str(item.get("input", "normalize_response"))


class VEPAdapter(BaseAdapter):
    """VEP adapter using the Ensembl REST API."""

    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self._name = "ensembl_vep"
        self._version = "rest_api_2.0"
        self._rest_url = self.config.get("rest_url", ENSEMBL_REST_URL)
        self._timeout = self.config.get("timeout", DEFAULT_TIMEOUT)

    async def health_check(self) -> dict:
        try:
            import httpx

            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self._rest_url}/info/data/")
            if response.status_code == 200:
                return {"status": "ok", "detail": "Ensembl REST API reachable", "version": self._version}
            return {
                "status": "degraded",
                "detail": f"Ensembl API returned {response.status_code}",
                "version": self._version,
            }
        except Exception as exc:
            return {
                "status": "degraded",
                "detail": f"Ensembl API unreachable: {exc}",
                "version": self._version,
            }

    def supports(self, query_type: str) -> bool:
        return query_type.lower() in {"annotate", "vep", "variant"}

    async def validate_input(self, payload: Any) -> list[str]:
        if not isinstance(payload, dict):
            return ["Payload must be a dict with 'variants' key"]
        variants = payload.get("variants", [])
        if isinstance(variants, dict):
            variants = [variants]
        if not isinstance(variants, list) or not variants:
            return ["No variants provided"]
        errors: list[str] = []
        for index, variant in enumerate(variants):
            if not isinstance(variant, dict) or not all(
                key in variant for key in ("chromosome", "position", "reference", "alternate")
            ):
                errors.append(f"Variant {index}: missing required fields")
        return errors

    async def annotate(self, payload: Any, **kwargs) -> AdapterResult:
        import httpx

        validation_errors = await self.validate_input(payload)
        request_id = kwargs.get("request_id", "unknown")
        if validation_errors:
            return AdapterResult(
                source=self._name,
                source_version=self._version,
                retrieved_at=datetime.now(UTC).isoformat(),
                request_id=request_id,
                success=False,
                errors=validation_errors,
            )

        variants = payload["variants"]
        if isinstance(variants, dict):
            variants = [variants]
        records: list[dict] = []
        warnings: list[str] = []
        errors: list[str] = []

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for variant in variants:
                chrom = str(variant["chromosome"])
                pos = int(variant["position"])
                ref = str(variant["reference"])
                alt = str(variant["alternate"])
                region = _build_region_string(chrom, pos, ref, alt)
                url = f"{self._rest_url}{VEP_ENDPOINT}/{region}"
                params = {
                    "hgvs": 1,
                    "numbers": 1,
                    "canonical": 1,
                    "mane": 1,
                    "protein": 1,
                    "xref_refseq": 1,
                }
                for attempt in range(MAX_RETRIES + 1):
                    try:
                        response = await client.get(
                            url,
                            headers={"Accept": "application/json"},
                            params=params,
                        )
                        if response.status_code == 200:
                            normalized = _extract_vep_results(response.json(), region)
                            for record in normalized:
                                record.update(
                                    chromosome=chrom,
                                    position=pos,
                                    reference=ref,
                                    alternate=alt,
                                )
                            records.extend(normalized)
                            break
                        if response.status_code == 429 and attempt < MAX_RETRIES:
                            wait = 2**attempt
                            logger.warning("VEP rate limited; retrying in %ss", wait)
                            await asyncio.sleep(wait)
                            continue
                        errors.append(f"VEP API returned {response.status_code} for {region}")
                        break
                    except httpx.TimeoutException:
                        if attempt < MAX_RETRIES:
                            await asyncio.sleep(1)
                        else:
                            errors.append(f"Timeout annotating {region}")
                    except Exception as exc:
                        errors.append(f"Error annotating {region}: {exc}")
                        break

        return AdapterResult(
            source=self._name,
            source_version=self._version,
            retrieved_at=datetime.now(UTC).isoformat(),
            request_id=request_id,
            success=not errors,
            records=records,
            warnings=warnings,
            errors=errors,
            license="Ensembl REST API data; see Ensembl terms and source attribution requirements.",
        )

    def normalize_response(self, raw: Any) -> AdapterResult:
        records: list[dict] = []
        if isinstance(raw, AdapterResult):
            return raw
        if isinstance(raw, dict) and isinstance(raw.get("records"), list):
            records = [item for item in raw["records"] if isinstance(item, dict)]
        else:
            items = raw if isinstance(raw, list) else [raw]
            raw_items = [item for item in items if isinstance(item, dict)]
            if raw_items and all(
                "transcript_consequences" not in item and "most_severe_consequence" not in item
                for item in raw_items
            ):
                records = raw_items
            else:
                for item in raw_items:
                    records.extend(_extract_vep_results(item, _infer_region(item)))

        return AdapterResult(
            source=self._name,
            source_version=self._version,
            retrieved_at=datetime.now(UTC).isoformat(),
            request_id="normalize_response",
            success=bool(records),
            records=records,
            errors=[] if records else ["Unsupported or empty Ensembl VEP response"],
            license="Ensembl REST API data; see Ensembl terms and source attribution requirements.",
        )


__all__ = [
    "VEPAdapter",
    "_build_region_string",
    "_extract_vep_results",
    "_parse_vep_consequence",
]
