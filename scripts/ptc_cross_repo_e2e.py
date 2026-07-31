#!/usr/bin/env python3
"""End-to-end PTC projection test across AI-Kill-Cancer and KnowGraphGo."""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.backend.database.models import Base  # noqa: E402
from src.backend.domain.clinical_graph_outbox import ClinicalGraphOutboxModel  # noqa: E402
from src.backend.importers.ptc_tcga.service import PTCTCGAImportService  # noqa: E402

PTC_NAMESPACE = uuid.UUID("4e893c63-d0a2-4eef-949d-d4fdd7e65e09")


def fixture_records() -> list[dict]:
    return [
        {
            "case_id": "TCGA-PTC-0001",
            "gender": "female",
            "ajcc_pathologic_stage": "Stage I",
            "vital_status": "Alive",
            "variants": [
                {
                    "hugo_symbol": "BRAF",
                    "chromosome": "7",
                    "start_position": 140453136,
                    "reference_allele": "A",
                    "tumor_seq_allele2": "T",
                    "hgvsp_short": "p.V600E",
                    "variant_classification": "Missense_Mutation",
                }
            ],
        },
        {
            "case_id": "TCGA-PTC-0002",
            "gender": "male",
            "ajcc_pathologic_stage": "Stage II",
            "vital_status": "Alive",
            "variants": [
                {
                    "hugo_symbol": "NRAS",
                    "chromosome": "1",
                    "start_position": 115256529,
                    "reference_allele": "T",
                    "tumor_seq_allele2": "C",
                    "hgvsp_short": "p.Q61R",
                }
            ],
        },
        {
            "case_id": "TCGA-PTC-0003",
            "gender": "female",
            "ajcc_pathologic_stage": "Stage I",
            "vital_status": "Alive",
            "variants": [
                {
                    "hugo_symbol": "RET",
                    "chromosome": "10",
                    "start_position": 43612032,
                    "reference_allele": "G",
                    "tumor_seq_allele2": "A",
                    "hgvsp_short": "fusion-proxy",
                }
            ],
        },
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--knowgraph-repo", type=Path, required=True)
    parser.add_argument("--keep", action="store_true", help="keep temporary databases")
    return parser.parse_args()


def run(command: list[str], *, cwd: Path, stdin: bytes | None = None) -> dict:
    completed = subprocess.run(
        command,
        cwd=cwd,
        input=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"command failed ({completed.returncode}): {' '.join(command)}\n"
            f"stdout={completed.stdout.decode(errors='replace')}\n"
            f"stderr={completed.stderr.decode(errors='replace')}"
        )
    text = completed.stdout.decode("utf-8")
    return json.loads(text) if text.strip() else {}


def graph_id(prefix: str, *parts: str) -> str:
    canonical = ":".join(["ptc", prefix, *(part.strip().lower() for part in parts)])
    return str(uuid.uuid5(PTC_NAMESPACE, canonical))


async def create_events(database: Path) -> list[dict]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{database}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            result = await PTCTCGAImportService(session).import_records(
                fixture_records(), batch_id="ptc-cross-repo-e2e"
            )
            if result.imported_cases != 3 or result.outbox_events != 9:
                raise AssertionError(f"unexpected import result: {result}")
            rows = list(
                (
                    await session.execute(
                        select(ClinicalGraphOutboxModel).order_by(ClinicalGraphOutboxModel.created_at)
                    )
                ).scalars()
            )
    finally:
        await engine.dispose()

    return [
        {
            "event_id": row.event_id,
            "event_type": row.event_type,
            "schema_version": row.schema_version,
            "aggregate_type": row.aggregate_type,
            "aggregate_id": row.aggregate_id,
            "occurred_at": row.occurred_at.isoformat() + "Z",
            "correlation_id": row.correlation_id,
            "causation_id": row.causation_id,
            "payload": row.payload,
        }
        for row in rows
    ]


async def execute(args: argparse.Namespace) -> dict:
    if not (args.knowgraph_repo / "go.mod").exists():
        raise FileNotFoundError(f"KnowGraphGo repository not found: {args.knowgraph_repo}")

    temporary = tempfile.TemporaryDirectory(prefix="ptc-e2e-")
    workdir = Path(temporary.name)
    clinical_db = workdir / "clinical.db"
    graph_db = workdir / "ptcgraph.db"
    events = await create_events(clinical_db)
    payload = json.dumps(events, ensure_ascii=False).encode("utf-8")

    first = run(
        ["go", "run", "./cmd/ptcgraph", "--dsn", str(graph_db), "--batch"],
        cwd=args.knowgraph_repo,
        stdin=payload,
    )
    nodes_first = run(
        ["go", "run", "./cmd/knowgraph", "--dsn", str(graph_db), "--json", "node", "list", "--ns", "ptc", "--limit", "1000"],
        cwd=args.knowgraph_repo,
    )
    edges_first = run(
        ["go", "run", "./cmd/knowgraph", "--dsn", str(graph_db), "--json", "edge", "list", "--ns", "ptc", "--limit", "1000"],
        cwd=args.knowgraph_repo,
    )

    replay = run(
        ["go", "run", "./cmd/ptcgraph", "--dsn", str(graph_db), "--batch"],
        cwd=args.knowgraph_repo,
        stdin=payload,
    )
    nodes_replay = run(
        ["go", "run", "./cmd/knowgraph", "--dsn", str(graph_db), "--json", "node", "list", "--ns", "ptc", "--limit", "1000"],
        cwd=args.knowgraph_repo,
    )
    edges_replay = run(
        ["go", "run", "./cmd/knowgraph", "--dsn", str(graph_db), "--json", "edge", "list", "--ns", "ptc", "--limit", "1000"],
        cwd=args.knowgraph_repo,
    )

    node_count_first = int(nodes_first.get("count", len(nodes_first.get("nodes", []))))
    edge_count_first = int(edges_first.get("count", len(edges_first.get("edges", []))))
    node_count_replay = int(nodes_replay.get("count", len(nodes_replay.get("nodes", []))))
    edge_count_replay = int(edges_replay.get("count", len(edges_replay.get("edges", []))))
    if (node_count_first, edge_count_first) != (node_count_replay, edge_count_replay):
        raise AssertionError("idempotent replay changed graph counts")

    # Verify a real path from TCGA-PTC-0001 to BRAF.
    from_id = graph_id("case", "TCGA-THCA", "TCGA-PTC-0001")
    to_id = graph_id("gene", "BRAF")
    path = run(
        ["go", "run", "./cmd/knowgraph", "--dsn", str(graph_db), "--json", "query", "path", from_id, to_id],
        cwd=args.knowgraph_repo,
    )

    result = {
        "status": "passed",
        "events": len(events),
        "first_apply": first,
        "replay": replay,
        "node_count": node_count_replay,
        "relation_count": edge_count_replay,
        "path": path,
        "workdir": str(workdir) if args.keep else None,
    }
    if args.keep:
        temporary.cleanup = lambda: None  # type: ignore[method-assign]
    else:
        temporary.cleanup()
    return result


def main() -> int:
    try:
        result = asyncio.run(execute(parse_args()))
    except Exception as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
