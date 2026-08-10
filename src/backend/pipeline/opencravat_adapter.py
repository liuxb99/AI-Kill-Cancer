"""OpenCRAVAT adapter backed by the local ``oc`` command line tool.

The adapter never installs modules or mutates global OpenCRAVAT configuration.
It accepts either a local VCF path or structured variants, executes an isolated
job in a temporary output directory, and normalizes generated TSV reports into
the common :class:`AdapterResult` envelope.
"""

from __future__ import annotations

import asyncio
import csv
import os
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.backend.adapters.base import AdapterResult, BaseAdapter

_SUPPORTED_GENOMES = {"hg38", "hg19", "hg18"}
_DEFAULT_TIMEOUT = 300


def _variant_fields(item: dict[str, Any]) -> tuple[str, int, str, str] | None:
    chromosome = str(item.get("chromosome", "")).strip()
    position = item.get("position")
    reference = str(item.get("reference", "")).strip().upper()
    alternate = str(item.get("alternate", "")).strip().upper()
    if chromosome.lower().startswith("chr"):
        chromosome = chromosome[3:]
    if not chromosome or not position or not reference or not alternate:
        return None
    try:
        pos = int(position)
    except (TypeError, ValueError):
        return None
    if pos <= 0:
        return None
    return chromosome, pos, reference, alternate


def _write_vcf(path: Path, variants: list[dict[str, Any]], genome: str) -> None:
    """Write the minimal single-sample VCF required by OpenCRAVAT."""
    lines = [
        "##fileformat=VCFv4.2",
        f"##reference={genome}",
        '##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">',
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE",
    ]
    for index, item in enumerate(variants, start=1):
        fields = _variant_fields(item)
        if fields is None:
            raise ValueError(f"Variant {index - 1} is missing chromosome/position/reference/alternate")
        chrom, pos, ref, alt = fields
        identifier = str(item.get("id") or item.get("variant_id") or f"variant-{index}")
        lines.append(f"{chrom}\t{pos}\t{identifier}\t{ref}\t{alt}\t.\tPASS\t.\tGT\t0/1")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _parse_tsv_reports(output_dir: Path, max_records: int = 10000) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for report_path in sorted(output_dir.glob("*.tsv")):
        report_name = report_path.stem
        with report_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            for row in reader:
                normalized = {str(key): value for key, value in row.items() if key is not None}
                normalized["_opencravat_report"] = report_name
                records.append(normalized)
                if len(records) >= max_records:
                    return records
    return records


class OpenCRAVATAdapter(BaseAdapter):
    """Run an installed OpenCRAVAT CLI without hiding configuration failures."""

    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self._name = "opencravat"
        self._version = "cli"
        self._executable = str(
            self.config.get("executable")
            or os.getenv("OPENCRAVAT_EXECUTABLE")
            or "oc"
        )
        self._genome = str(self.config.get("genome", "hg38"))
        self._timeout = float(self.config.get("timeout", _DEFAULT_TIMEOUT))
        self._annotators = [str(value) for value in self.config.get("annotators", [])]
        self._max_records = int(self.config.get("max_records", 10000))

    def _resolved_executable(self) -> str | None:
        candidate = Path(self._executable).expanduser()
        if candidate.is_file():
            return str(candidate.resolve())
        return shutil.which(self._executable)

    async def health_check(self) -> dict:
        executable = self._resolved_executable()
        if executable is None:
            return {
                "status": "unavailable",
                "detail": "OpenCRAVAT CLI not found; install open-cravat or configure OPENCRAVAT_EXECUTABLE",
                "version": self._version,
            }
        try:
            process = await asyncio.create_subprocess_exec(
                executable,
                "version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=10)
        except (OSError, asyncio.TimeoutError) as exc:
            return {"status": "degraded", "detail": str(exc), "version": self._version}
        detail = (stdout or stderr).decode("utf-8", errors="replace").strip()
        if process.returncode == 0:
            return {"status": "ok", "detail": detail or "OpenCRAVAT available", "version": self._version}
        return {
            "status": "degraded",
            "detail": detail or f"OpenCRAVAT exited with code {process.returncode}",
            "version": self._version,
        }

    def supports(self, query_type: str) -> bool:
        return query_type.lower() in {"annotate", "variant", "gene", "vcf"}

    async def validate_input(self, payload: Any) -> list[str]:
        if not isinstance(payload, dict):
            return ["Payload must be an object"]
        genome = str(payload.get("genome", self._genome))
        errors: list[str] = []
        if genome not in _SUPPORTED_GENOMES:
            errors.append(f"Unsupported genome build: {genome}")
        vcf_path = payload.get("vcf_path")
        variants = payload.get("variants")
        if vcf_path:
            path = Path(str(vcf_path)).expanduser()
            if not path.is_file():
                errors.append(f"VCF file does not exist: {path}")
            elif path.suffix.lower() not in {".vcf", ".gz", ".bgz"}:
                errors.append("vcf_path must point to a VCF/VCF.GZ-compatible file")
        elif isinstance(variants, list) and variants:
            for index, item in enumerate(variants):
                if not isinstance(item, dict) or _variant_fields(item) is None:
                    errors.append(
                        f"Variant {index} requires chromosome, positive position, reference, and alternate"
                    )
        else:
            errors.append("Provide vcf_path or a non-empty variants list")
        return errors

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

        executable = self._resolved_executable()
        if executable is None:
            return AdapterResult(
                source=self._name,
                source_version=self._version,
                retrieved_at=retrieved_at,
                request_id=request_id,
                success=False,
                errors=["OpenCRAVAT CLI is not installed or configured"],
            )

        genome = str(payload.get("genome", self._genome))
        with tempfile.TemporaryDirectory(prefix="ai-kill-cancer-oc-") as temp_name:
            temp_dir = Path(temp_name)
            source_vcf: Path
            if payload.get("vcf_path"):
                source_vcf = Path(str(payload["vcf_path"])).expanduser().resolve()
            else:
                source_vcf = temp_dir / "input.vcf"
                _write_vcf(source_vcf, payload["variants"], genome)

            output_dir = temp_dir / "output"
            output_dir.mkdir(parents=True, exist_ok=True)
            command = [
                executable,
                "run",
                str(source_vcf),
                "-l",
                genome,
                "-t",
                "tsv",
                "-d",
                str(output_dir),
                "-n",
                "ai-kill-cancer",
            ]
            annotators = payload.get("annotators", self._annotators)
            if annotators:
                command.extend(["-a", *[str(item) for item in annotators]])

            try:
                process = await asyncio.create_subprocess_exec(
                    *command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=self._timeout
                )
            except asyncio.TimeoutError:
                if "process" in locals():
                    process.kill()
                    await process.communicate()
                return AdapterResult(
                    source=self._name,
                    source_version=self._version,
                    retrieved_at=retrieved_at,
                    request_id=request_id,
                    success=False,
                    errors=[f"OpenCRAVAT exceeded timeout of {self._timeout:g} seconds"],
                )
            except OSError as exc:
                return AdapterResult(
                    source=self._name,
                    source_version=self._version,
                    retrieved_at=retrieved_at,
                    request_id=request_id,
                    success=False,
                    errors=[f"Failed to start OpenCRAVAT: {exc}"],
                )

            stdout_text = stdout.decode("utf-8", errors="replace").strip()
            stderr_text = stderr.decode("utf-8", errors="replace").strip()
            if process.returncode != 0:
                detail = stderr_text or stdout_text or f"exit code {process.returncode}"
                return AdapterResult(
                    source=self._name,
                    source_version=self._version,
                    retrieved_at=retrieved_at,
                    request_id=request_id,
                    success=False,
                    errors=[f"OpenCRAVAT failed: {detail[:2000]}"],
                )

            records = _parse_tsv_reports(output_dir, self._max_records)
            warnings: list[str] = []
            if not records:
                warnings.append("OpenCRAVAT completed but produced no TSV records")
            return AdapterResult(
                source=self._name,
                source_version=self._version,
                retrieved_at=retrieved_at,
                request_id=request_id,
                success=True,
                records=records,
                warnings=warnings,
                license="OpenCRAVAT framework; individual annotator data retain their own licenses",
                metadata={
                    "genome": genome,
                    "annotators": [str(item) for item in annotators],
                    "stdout": stdout_text[-2000:],
                    "records_truncated": len(records) >= self._max_records,
                },
            )

    def normalize_response(self, raw: Any) -> AdapterResult:
        if isinstance(raw, list):
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
            errors=[] if records else ["Unsupported or empty OpenCRAVAT response"],
        )


__all__ = ["OpenCRAVATAdapter", "_parse_tsv_reports", "_write_vcf"]
