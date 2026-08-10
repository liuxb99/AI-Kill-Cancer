"""Local PharmCAT command-line adapter.

PharmCAT consumes GRCh38 VCF input and emits match/phenotype JSON plus an HTML
report. This adapter runs a configured PharmCAT JAR in an isolated temporary
output directory and returns JSON artifacts as research records. It never
interprets PharmCAT output as prescribing or dosing advice.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.backend.adapters.base import AdapterResult, BaseAdapter

_DEFAULT_TIMEOUT = 300


class PharmCATAdapter(BaseAdapter):
    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self._name = "pharmcat"
        self._version = "cli"
        jar = self.config.get("jar") or os.getenv("PHARMCAT_JAR", "")
        self._jar = Path(str(jar)).expanduser() if jar else None
        self._java = str(self.config.get("java") or os.getenv("JAVA_EXECUTABLE") or "java")
        self._timeout = float(self.config.get("timeout", _DEFAULT_TIMEOUT))

    def _resolved_jar(self) -> Path | None:
        if self._jar is None:
            return None
        path = self._jar.resolve()
        return path if path.is_file() else None

    def _resolved_java(self) -> str | None:
        candidate = Path(self._java).expanduser()
        if candidate.is_file():
            return str(candidate.resolve())
        return shutil.which(self._java)

    async def health_check(self) -> dict:
        jar = self._resolved_jar()
        java = self._resolved_java()
        if jar is None:
            return {
                "status": "unavailable",
                "detail": "PharmCAT JAR not configured; set PHARMCAT_JAR",
                "version": self._version,
            }
        if java is None:
            return {
                "status": "unavailable",
                "detail": "Java executable not found",
                "version": self._version,
            }
        try:
            process = await asyncio.create_subprocess_exec(
                java,
                "-jar",
                str(jar),
                "-version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=15)
        except (OSError, asyncio.TimeoutError) as exc:
            return {"status": "degraded", "detail": str(exc), "version": self._version}
        detail = (stdout or stderr).decode("utf-8", errors="replace").strip()
        if process.returncode == 0:
            return {"status": "ok", "detail": detail or "PharmCAT available", "version": self._version}
        # Some PharmCAT releases do not expose -version consistently; a readable
        # JAR plus working Java is still a configured runtime.
        return {
            "status": "degraded",
            "detail": detail or f"PharmCAT version probe exited {process.returncode}",
            "version": self._version,
        }

    def supports(self, query_type: str) -> bool:
        return query_type.lower() in {"pharmcat", "pgx", "pharmacogenomics", "vcf", "annotate"}

    async def validate_input(self, payload: Any) -> list[str]:
        if not isinstance(payload, dict):
            return ["Payload must be an object"]
        vcf_value = str(payload.get("vcf_path", "")).strip()
        if not vcf_value:
            return ["vcf_path is required; PharmCAT requires a prepared GRCh38 VCF"]
        path = Path(vcf_value).expanduser()
        errors: list[str] = []
        if not path.is_file():
            errors.append(f"VCF file does not exist: {path}")
        if path.suffix.lower() not in {".vcf", ".gz", ".bgz"}:
            errors.append("vcf_path must point to a VCF/VCF.GZ-compatible file")
        genome = str(payload.get("genome", "GRCh38")).lower()
        if genome not in {"grch38", "hg38", "b38"}:
            errors.append("PharmCAT input must use GRCh38/hg38")
        outside = str(payload.get("outside_calls", "")).strip()
        if outside and not Path(outside).expanduser().is_file():
            errors.append(f"outside_calls file does not exist: {outside}")
        samples = payload.get("samples")
        if samples is not None and not isinstance(samples, (str, list, tuple)):
            errors.append("samples must be a comma-separated string or list")
        return errors

    @staticmethod
    def _load_json_artifacts(output_dir: Path, base: str) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for kind, suffix in (("match", ".match.json"), ("phenotype", ".phenotype.json")):
            path = output_dir / f"{base}{suffix}"
            if not path.is_file():
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                records.append({"artifact": kind, "parse_error": str(exc), "path": str(path)})
                continue
            records.append({"artifact": kind, "payload": payload})
        report = output_dir / f"{base}.report.html"
        if report.is_file():
            records.append(
                {
                    "artifact": "report",
                    "media_type": "text/html",
                    "size_bytes": report.stat().st_size,
                    "generated": True,
                }
            )
        return records

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
        jar = self._resolved_jar()
        java = self._resolved_java()
        if jar is None or java is None:
            return AdapterResult(
                source=self._name,
                source_version=self._version,
                retrieved_at=retrieved_at,
                request_id=request_id,
                success=False,
                errors=["PharmCAT runtime is not configured (PHARMCAT_JAR and Java are required)"],
            )

        vcf = Path(str(payload["vcf_path"])).expanduser().resolve()
        with tempfile.TemporaryDirectory(prefix="ai-kill-cancer-pharmcat-") as temp_name:
            output_dir = Path(temp_name)
            base = "pharmcat"
            command = [
                java,
                "-jar",
                str(jar),
                "-vcf",
                str(vcf),
                "--output-dir",
                str(output_dir),
                "--base-filename",
                base,
            ]
            outside = str(payload.get("outside_calls", "")).strip()
            if outside:
                command.extend(["--phenotyper-outside-call-file", str(Path(outside).expanduser().resolve())])
            samples = payload.get("samples")
            if samples:
                sample_value = ",".join(str(value) for value in samples) if isinstance(samples, (list, tuple)) else str(samples)
                command.extend(["--samples", sample_value])
            research = payload.get("research")
            if research:
                research_value = ",".join(str(value) for value in research) if isinstance(research, (list, tuple)) else str(research)
                command.extend(["-research", research_value])

            try:
                process = await asyncio.create_subprocess_exec(
                    *command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=self._timeout)
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
                    errors=[f"PharmCAT exceeded timeout of {self._timeout:g} seconds"],
                )
            except OSError as exc:
                return AdapterResult(
                    source=self._name,
                    source_version=self._version,
                    retrieved_at=retrieved_at,
                    request_id=request_id,
                    success=False,
                    errors=[f"Failed to start PharmCAT: {exc}"],
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
                    errors=[f"PharmCAT failed: {detail[:2000]}"],
                )

            records = self._load_json_artifacts(output_dir, base)
            warnings: list[str] = []
            if not records:
                warnings.append("PharmCAT completed but no expected artifacts were found")
            warnings.append(
                "PharmCAT output is research decision-support data and is not a prescription or dosing instruction"
            )
            return AdapterResult(
                source=self._name,
                source_version=self._version,
                retrieved_at=retrieved_at,
                request_id=request_id,
                success=True,
                records=records,
                warnings=warnings,
                license="PharmCAT software/data are subject to their respective upstream terms and source licenses.",
                metadata={
                    "genome": "GRCh38",
                    "stdout": stdout_text[-2000:],
                    "artifact_count": len(records),
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
            errors=[] if records else ["Unsupported or empty PharmCAT response"],
        )


__all__ = ["PharmCATAdapter"]
