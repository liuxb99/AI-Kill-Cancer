#!/usr/bin/env python3
"""Cross-repository E2E for the complete PTC GraphData projection.

Creates a representative PTC dataset, exports deterministic KnowGraphGo
GraphData, imports it twice, and verifies replay does not create duplicates.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from src.backend.database.models import Base  # noqa: E402
from src.backend.domain.ptc_knowledge import (  # noqa: E402
    PTCEvidenceRecordModel,
    PTCTherapyModel,
    PTCTherapyTargetModel,
)
from src.backend.domain.ptc_research import (  # noqa: E402
    PTCOutcomeModel,
    PTCResearchCaseModel,
    PTCVariantModel,
)
from src.backend.services.ptc_integrated_service import PTCIntegratedService  # noqa: E402
from src.backend.services.ptc_knowgraph_export import PTCKnowGraphExportService  # noqa: E402


async def build_graph_data() -> dict:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        case = PTCResearchCaseModel(
            case_id="TCGA-E2E-0001",
            source_dataset="TCGA-THCA",
            pathologic_stage="Stage II",
            vital_status="Alive",
        )
        db.add(case)
        await db.flush()
        db.add(
            PTCVariantModel(
                variant_id="TCGA-E2E-0001:BRAF:V600E",
                research_case_id=case.id,
                case_id=case.case_id,
                source_dataset="TCGA-THCA",
                gene="BRAF",
                protein_change="p.V600E",
                classification="Missense_Mutation",
            )
        )
        db.add(
            PTCOutcomeModel(
                outcome_id="TCGA-E2E-0001:vital_status",
                research_case_id=case.id,
                case_id=case.case_id,
                source_dataset="TCGA-THCA",
                outcome_type="vital_status",
                outcome_value="Alive",
            )
        )
        therapy = PTCTherapyModel(
            therapy_key="openfda:dabrafenib-e2e",
            name="Dabrafenib",
            generic_name="dabrafenib",
            source_name="openFDA",
            source_record_id="dabrafenib-e2e",
            approval_status="FDA label available",
        )
        db.add(therapy)
        await db.flush()
        db.add(
            PTCTherapyTargetModel(
                therapy_id=therapy.id,
                gene_symbol="BRAF",
                variant="V600E",
                target_type="molecular_target",
                evidence_level="label_or_curated_mapping",
            )
        )
        db.add(
            PTCEvidenceRecordModel(
                evidence_key="pubmed:e2e:braf",
                source_name="PubMed",
                source_record_id="PMID-E2E",
                evidence_type="publication",
                evidence_level="published_literature",
                gene_symbol="BRAF",
                therapy_id=therapy.id,
                title="BRAF evidence in papillary thyroid carcinoma",
            )
        )
        await db.commit()
        await PTCIntegratedService(db).bootstrap_herbal_research()
        graph_data = await PTCKnowGraphExportService(db).export()
    await engine.dispose()
    return graph_data


def run_json(command: list[str], *, repo: Path, payload: bytes | None = None) -> dict:
    process = subprocess.run(
        command,
        cwd=repo,
        input=payload,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if process.returncode != 0:
        raise RuntimeError(
            f"command failed ({process.returncode}): {' '.join(command)}\n"
            f"stdout={process.stdout.decode('utf-8', errors='replace')}\n"
            f"stderr={process.stderr.decode('utf-8', errors='replace')}"
        )
    return json.loads(process.stdout)


def run_import(repo: Path, dsn: Path, payload: bytes) -> dict:
    return run_json(
        ["go", "run", "./cmd/ptcgraphdata", "-dsn", str(dsn)],
        repo=repo,
        payload=payload,
    )


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--knowgraph-repo", required=True, type=Path)
    args = parser.parse_args()
    repo = args.knowgraph_repo.resolve()
    if not (repo / "go.mod").exists():
        raise SystemExit(f"KnowGraphGo repository not found: {repo}")

    graph_data = await build_graph_data()
    payload = json.dumps(graph_data, sort_keys=True).encode("utf-8")
    with tempfile.TemporaryDirectory(prefix="ptc-full-graph-") as tmp:
        dsn = Path(tmp) / "ptc-full.db"
        first = run_import(repo, dsn, payload)
        second = run_import(repo, dsn, payload)
        nodes = run_json(
            ["go", "run", "./cmd/knowgraph", "--dsn", str(dsn), "--json", "node", "list", "--ns", "ptc", "--limit", "10000"],
            repo=repo,
        )
        relations = run_json(
            ["go", "run", "./cmd/knowgraph", "--dsn", str(dsn), "--json", "edge", "list", "--ns", "ptc", "--limit", "10000"],
            repo=repo,
        )

    expected_entities = graph_data["metadata"]["entity_count"]
    expected_relations = graph_data["metadata"]["relation_count"]
    node_count = int(nodes.get("count", len(nodes.get("nodes", []))))
    relation_count = int(relations.get("count", len(relations.get("edges", []))))
    assert first["entities_created"] == expected_entities, first
    assert first["relations_created"] == expected_relations, first
    assert second["entities_created"] == 0, second
    assert second["relations_created"] == 0, second
    assert node_count == expected_entities, (node_count, expected_entities)
    assert relation_count == expected_relations, (relation_count, expected_relations)
    print(
        json.dumps(
            {
                "status": "PASS",
                "entities": node_count,
                "relations": relation_count,
                "first_import": first,
                "replay": second,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
