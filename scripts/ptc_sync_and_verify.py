#!/usr/bin/env python3
"""Run the complete PTC data pipeline and objectively verify readiness.

Examples:
    python scripts/ptc_sync_and_verify.py --no-sync
    python scripts/ptc_sync_and_verify.py --gdc-size 100 --mutation-files 1

Exit codes:
    0: demo readiness gate passed
    2: command completed, but demo readiness gate did not pass
    1: unexpected execution/configuration failure

This command is for research and decision-support operations only. It does not
approve the system for autonomous clinical use.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.backend.services.ptc_completion_service import DEFAULT_PTC_DRUGS, PTCCompletionService  # noqa: E402
from src.backend.services.ptc_readiness_service import PTCReadinessService  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Synchronize and verify the complete PTC research product")
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL"),
        help="SQLAlchemy async URL; defaults to DATABASE_URL",
    )
    parser.add_argument("--no-sync", action="store_true", help="only evaluate persisted data")
    parser.add_argument("--gdc-size", type=int, default=100)
    parser.add_argument("--mutation-files", type=int, default=1)
    parser.add_argument("--trial-size", type=int, default=100)
    parser.add_argument("--pubmed-size", type=int, default=100)
    parser.add_argument("--drug", action="append", dest="drugs", help="repeat to override the default PTC drug list")
    parser.add_argument("--include-civic", action="store_true")
    parser.add_argument("--output", type=Path, help="optionally save the complete JSON result")
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if not args.database_url:
        raise ValueError("DATABASE_URL or --database-url is required")
    if not (1 <= args.gdc_size <= 10_000):
        raise ValueError("--gdc-size must be between 1 and 10000")
    if not (0 <= args.mutation_files <= 20):
        raise ValueError("--mutation-files must be between 0 and 20")
    if not (1 <= args.trial_size <= 1_000):
        raise ValueError("--trial-size must be between 1 and 1000")
    if not (1 <= args.pubmed_size <= 500):
        raise ValueError("--pubmed-size must be between 1 and 500")


async def execute(args: argparse.Namespace) -> dict[str, Any]:
    validate_args(args)
    engine = create_async_engine(args.database_url, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as db:
            sync_result: dict[str, Any] | None = None
            if not args.no_sync:
                sync_result = await PTCCompletionService(db).sync_all(
                    gdc_size=args.gdc_size,
                    gdc_mutation_files=args.mutation_files,
                    trial_size=args.trial_size,
                    pubmed_size=args.pubmed_size,
                    drug_names=args.drugs or DEFAULT_PTC_DRUGS,
                    include_civic=args.include_civic,
                )
            readiness = await PTCReadinessService(db).evaluate()
            return {
                "status": "PASS" if readiness["demo_ready"] else "NOT_READY",
                "sync": sync_result,
                "readiness": readiness,
            }
    finally:
        await engine.dispose()


def write_result(result: dict[str, Any], output: Path | None) -> None:
    text = json.dumps(result, ensure_ascii=False, indent=2, default=str)
    print(text)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")


def main() -> int:
    try:
        args = parse_args()
        result = asyncio.run(execute(args))
        write_result(result, args.output)
        return 0 if result["readiness"]["demo_ready"] else 2
    except Exception as exc:
        print(
            json.dumps(
                {"status": "ERROR", "error": f"{type(exc).__name__}: {exc}"},
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
