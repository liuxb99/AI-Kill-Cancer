"""
Ensembl VEP adapter — real REST API integration.

Uses the Ensembl REST API (https://rest.ensembl.org/vep/human/region)
for variant annotation when local VEP is not installed.

Phase 2A: REST API integration. Local VEP support deferred.
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import UTC, datetime
from typing import Any

from src.backend.adapters.base import AdapterResult, BaseAdapter

logger = logging.getLogger(__name__)


# ─── REST API configuration ───────────────────────────────────────────────────

ENSEMBL_REST_URL = "https://rest.ensembl.org"
VEP_ENDPOINT = "/vep/human/region"
DEFAULT_TIMEOUT = 30  # seconds
MAX_RETRIES = 2

# HGVS pattern for VEP region format
_HGVS_G_RE = re.compile(r"^(\d+|X|Y|MT|chr\d+|chrX|chrY|chrMT):g\.(\d+)([ACGTN]+)>([ACGTN]+)$")


def _build_region_string(chromosome: str, position: int, ref: str, alt: str) -> str:
    """Build region string for VEP REST API: {chrom}:{start}-{end}:{allele}"""
    # Strip "chr" prefix if present
    chrom = chromosome.replace("chr", "")
    start = position
    end = position + len(ref) - 1
    return f"{chrom}:{start}-{end}:{alt}"


def _parse_vep_consequence(consequence: str) -> str:
    """Map VEP consequence term to standard SO term."""
    # VEP returns terms like "missense_variant", "stop_gained", etc.
    # Normalize to lowercase and return as-is (already SO format)
    return consequence.lower().replace(" ", "_")


def _extract_vep_results(data: dict, region: str) -> list[dict]:
    """Extract relevant annotation fields from VEP response.

    Transcript selection policy (priority order):
    1. MANE Select transcript
    2. Canonical transcript
    3. protein_coding biotype
    4. Highest-impact consequence
    5. Any other transcript

    All transcript consequences are preserved in the response;
    the "selected" transcript is marked separately.
    """
    results = []
    for item in data if isinstance(data, list) else [data]:
        most_severe = item.get("most_severe_consequence", "")
        allele_str = item.get("allele_string", "")
        transcript_consequences = item.get("transcript_consequences", [])

        # Define selection priority
        def _transcript_priority(tc: dict) -> tuple:
            """Return sort key for transcript selection."""
            is_mane = 0 if tc.get("mane_select") or tc.get("mane_plus_clinical") else 1
            is_canonical = 0 if tc.get("canonical") == 1 else 1
            is_protein_coding = 0 if tc.get("biotype") == "protein_coding" else 1
            impact_order = {"HIGH": 0, "MODERATE": 1, "LOW": 2, "MODIFIER": 3}
            impact = impact_order.get(tc.get("impact", ""), 4)
            return (is_mane, is_canonical, is_protein_coding, impact)

        # Sort transcripts by priority
        sorted_tcs = sorted(transcript_consequences, key=_transcript_priority)

        # Build result entries for ALL transcripts
        for i, tc in enumerate(sorted_tcs):
            result = {
                "region": region,
                "allele_string": allele_str,
                "gene_symbol": tc.get("gene_symbol", ""),
                "gene_id": tc.get("gene_id", ""),
                "transcript_id": tc.get("transcript_id", ""),
                "protein_id": tc.get("protein_id", ""),
                "consequence": _parse_vep_consequence(
                    tc.get("consequence_terms", [""])[0]
                ) if tc.get("consequence_terms") else most_severe.lower(),
                "all_consequences": [c.lower() for c in tc.get("consequence_terms", [])],
                "hgvs_c": tc.get("hgvs_transcript", ""),
                "hgvs_p": tc.get("hgvs_short", ""),
                "protein_change": tc.get("hgvs_short", ""),
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
                "is_selected": i == 0,  # First = highest priority
                "selection_reason": _selection_reason(i, tc),
            }
            results.append(result)

        # If no transcript consequences, still add an entry
        if not transcript_consequences:
            result = {
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
            results.append(result)

    return results


def _selection_reason(index: int, tc: dict) -> str:
    """Return human-readable reason for transcript selection priority."""
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


class VEPAdapter(BaseAdapter):
    """VEP adapter using Ensembl REST API.

    When local VEP is installed, it can also run VEP via subprocess.
    Phase 2A uses REST API only.
    """

    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self._name = "ensembl_vep"
        self._version = "rest_api_2.0"
        self._rest_url = config.get("rest_url", ENSEMBL_REST_URL) if config else ENSEMBL_REST_URL
        self._timeout = config.get("timeout", DEFAULT_TIMEOUT) if config else DEFAULT_TIMEOUT

    async def health_check(self) -> dict:
        """Check if Ensembl REST API is reachable."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self._rest_url}/info/data/")
                if resp.status_code == 200:
                    return {"status": "ok", "detail": "Ensembl REST API reachable", "version": self._version}
                return {"status": "degraded", "detail": f"Ensembl API returned {resp.status_code}", "version": self._version}
        except Exception as e:
            return {"status": "degraded", "detail": f"Ensembl API unreachable: {e}", "version": self._version}

    def supports(self, query_type: str) -> bool:
        return query_type in ("annotate", "vep", "variant")

    async def validate_input(self, payload: Any) -> list[str]:
        errors = []
        if not isinstance(payload, dict):
            errors.append("Payload must be a dict with 'variants' key")
            return errors
        variants = payload.get("variants", [])
        if not variants:
            errors.append("No variants provided")
        for i, v in enumerate(variants):
            if not all(k in v for k in ("chromosome", "position", "reference", "alternate")):
                errors.append(f"Variant {i}: missing required fields")
        return errors

    async def annotate(self, payload: Any, **kwargs) -> AdapterResult:
        """Annotate variants using Ensembl VEP REST API.

        Payload format:
            {"variants": [{"chromosome": "7", "position": 140753336,
                           "reference": "A", "alternate": "T", ...}]}
        """
        import httpx
        variants = payload.get("variants", []) if isinstance(payload, dict) else payload
        request_id = kwargs.get("request_id", "unknown")

        # Convert to list if single variant dict
        if isinstance(variants, dict):
            variants = [variants]

        all_results = []
        warnings = []
        errors = []

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for v in variants:
                chrom = str(v.get("chromosome", ""))
                pos = int(v.get("position", 0))
                ref = str(v.get("reference", ""))
                alt = str(v.get("alternate", ""))

                # Skip if required fields missing
                if not chrom or not pos or not ref or not alt:
                    errors.append(f"Missing fields for variant: {v}")
                    continue

                # Build region string
                region = _build_region_string(chrom, pos, ref, alt)

                # Build API request
                headers = {"Content-Type": "application/json", "Accept": "application/json"}
                url = f"{self._rest_url}{VEP_ENDPOINT}/{region}"
                params = {
                    "hgvs": 0,
                    "numbers": 1,
                    "canonical": 1,
                    "mane": 1,
                    "protein": 1,
                    "xref_refseq": 1,
                }

                for attempt in range(MAX_RETRIES + 1):
                    try:
                        resp = await client.get(url, headers=headers, params=params)
                        if resp.status_code == 200:
                            data = resp.json()
                            vep_results = _extract_vep_results(data, region)
                            for r in vep_results:
                                r["chromosome"] = chrom
                                r["position"] = pos
                                r["reference"] = ref
                                r["alternate"] = alt
                            all_results.extend(vep_results)
                            break
                        elif resp.status_code == 429 and attempt < MAX_RETRIES:
                            wait = 2 ** attempt
                            logger.warning(f"Rate limited, retrying in {wait}s")
                            await asyncio.sleep(wait)
                        else:
                            errors.append(f"VEP API returned {resp.status_code} for {region}")
                            break
                    except httpx.TimeoutException:
                        if attempt < MAX_RETRIES:
                            await asyncio.sleep(1)
                        else:
                            errors.append(f"Timeout annotating {region}")
                    except Exception as e:
                        errors.append(f"Error annotating {region}: {e}")
                        break

        return AdapterResult(
            source="ensembl_vep",
            source_version=self._version,
            retrieved_at=datetime.now(UTC).isoformat(),
            request_id=request_id,
            success=len(errors) == 0,
            records=all_results,
            warnings=warnings,
            errors=errors,
            license="Ensembl REST API — http://rest.ensembl.org/",
        )

    def normalize_response(self, raw: Any) -> AdapterResult:
        return AdapterResult(source=self._name, source_version=self._version,
                             retrieved_at="", request_id="", success=False,
                             errors=["Not implemented"])
