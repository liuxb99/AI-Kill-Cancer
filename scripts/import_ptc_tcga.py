#!/usr/bin/env python3
"""Download public TCGA-THCA data and import it into AI-Kill-Cancer.

Examples:

    python scripts/import_ptc_tcga.py --database-url "$DATABASE_URL" --cases 100
    python scripts/import_ptc_tcga.py --database-url "$DATABASE_URL" --cases 100 --mutation-files 1

The command downloads only public GDC records.  It does not request controlled
BAM/FASTQ data or require a GDC access token.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.backend.importers.ptc_tcga.downloader import GDCClient  # noqa: E402
from src.backend.importers.ptc_tcga.maf_parser import (  # noqa: E402
    merge_variants_into_cases,
    parse_maf_bytes,
)
from src.backend.importers.ptc_tcga.service import PTCTCGAImportService  # noqa: E402


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import public TCGA-THCA research data")
    parser.add_argument("--database-url", required=True, help="SQLAlchemy async database URL")
    parser.add_argument("--cases", type=int, default=100, help="number of clinical cases to download")
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument(
        "--mutation-files",
        type=int,
        default=0,
        help="number of public masked somatic mutation files to download (0 = clinical only)",
    )
    parser.add_argument("--source-version", default=None)
    parser.add_argument("--batch-id", default=None)
    parser.add_argument("--manifest-output", type=Path, default=None)
    return parser.parse_args()


async def execute(args: argparse.Namespace) -> dict:
    client = GDCClient()
    clinical = await asyncio.to_thread(
        client.fetch_ptc_cases,
        size=args.cases,
        offset=args.offset,
    )
    records = clinical.records

    manifest: list[dict] = []
    if args.mutation_files > 0:
        manifest = await asyncio.to_thread(
            client.fetch_somatic_mutation_manifest,
            size=max(args.mutation_files, 1),
        )
        variants_by_case: dict[str, list[dict]] = {}
        for item in manifest[: args.mutation_files]:
            file_id = item.get("file_id")
            if not file_id:
                continue
            payload = await asyncio.to_thread(client.download_public_file, file_id)
            parsed = parse_maf_bytes(payload)
            for case_id, variants in parsed.items():
                variants_by_case.setdefault(case_id, []).extend(variants)
        records = merge_variants_into_cases(records, variants_by_case)

    if args.manifest_output:
        args.manifest_output.parent.mkdir(parents=True, exist_ok=True)
        args.manifest_output.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    engine = create_async_engine(args.database_url, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            result = await PTCTCGAImportService(session).import_records(
                records,
                source_version=args.source_version or clinical.source_version,
                batch_id=args.batch_id,
            )
    finally:
        await engine.dispose()

    return {
        **result.__dict__,
        "gdc_total_cases": clinical.total,
        "downloaded_cases": len(clinical.records),
        "downloaded_mutation_files": min(len(manifest), args.mutation_files),
    }


def main() -> int:
    try:
        result = asyncio.run(execute(arguments()))
    except Exception as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps({"status": "completed", **result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
