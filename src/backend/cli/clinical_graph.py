"""Clinical Graph CLI — 手动管理知识图谱投影。"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from src.backend.domain.clinical_graph_outbox import ClinicalGraphOutboxModel
from src.backend.domain.recommendation import RecommendationModel
from src.backend.domain.clinical_decision import ClinicalDecisionModel
from src.backend.domain.tumor_board import TumorBoardConsensusModel
from src.backend.schemas.clinical_graph_event import (
    ClinicalGraphEvent,
    GraphAggregateType,
    GraphEventType,
)
from src.backend.clinical_graph.client import ClinicalGraphClient

logger = logging.getLogger(__name__)


async def rebuild(
    db_url: str,
    patient_id: str = None,
    from_date: str = None,
    dry_run: bool = False,
):
    """重建知识图谱投影。"""
    engine = create_async_engine(db_url)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        events: List[ClinicalGraphEvent] = []

        # 1. Query recommendations
        from sqlalchemy import select, or_

        query = select(RecommendationModel)
        if patient_id:
            query = query.filter(RecommendationModel.patient_id == patient_id)
        if from_date:
            from datetime import datetime
            dt = datetime.fromisoformat(from_date)
            query = query.filter(RecommendationModel.created_at >= dt)

        result = await session.execute(query)
        recommendations = result.scalars().all()

        for rec in recommendations[:100]:  # 限制批量大小
            events.append(ClinicalGraphEvent(
                event_type=GraphEventType.RECOMMENDATION_CREATED,
                aggregate_type=GraphAggregateType.RECOMMENDATION,
                aggregate_id=str(rec.recommendation_id),
                payload={
                    "recommendation_id": str(rec.recommendation_id),
                    "patient_id": str(rec.patient_id) if rec.patient_id else "",
                },
            ))

        # 2. Query clinical decisions
        query2 = select(ClinicalDecisionModel)
        if patient_id:
            query2 = query2.filter(ClinicalDecisionModel.patient_id == patient_id)
        result2 = await session.execute(query2)
        decisions = result2.scalars().all()
        for dec in decisions[:100]:
            events.append(ClinicalGraphEvent(
                event_type=GraphEventType.CLINICAL_DECISION_CREATED,
                aggregate_type=GraphAggregateType.CLINICAL_DECISION,
                aggregate_id=str(dec.decision_id),
                payload={
                    "decision_id": str(dec.decision_id),
                    "patient_id": str(dec.patient_id) if dec.patient_id else "",
                },
            ))

        # 3. Query tumor board consensuses
        query3 = select(TumorBoardConsensusModel)
        if patient_id:
            query3 = query3.filter(TumorBoardConsensusModel.patient_id == patient_id)
        result3 = await session.execute(query3)
        consensuses = result3.scalars().all()
        for con in consensuses[:100]:
            events.append(ClinicalGraphEvent(
                event_type=GraphEventType.TUMOR_BOARD_CONSENSUS_CREATED,
                aggregate_type=GraphAggregateType.TUMOR_BOARD_CONSENSUS,
                aggregate_id=str(con.consensus_id),
                payload={
                    "consensus_id": str(con.consensus_id),
                    "patient_id": str(con.patient_id) if con.patient_id else "",
                },
            ))

        if dry_run:
            print(f"Dry-run: would process {len(events)} events")
            for evt in events[:5]:
                print(f"  {evt.event_type} {evt.aggregate_id}")
            return

        if not events:
            print("No events to process")
            return

        # 调用 CLI rebuild
        client = ClinicalGraphClient()
        result = await client.apply_events_batch(events)
        if result.get("success"):
            print(f"Rebuild complete: {len(events)} events processed")
        else:
            print(f"Rebuild failed: {result.get('error')}", file=sys.stderr)
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Clinical Graph CLI")
    parser.add_argument("command", choices=["rebuild"], help="Command")
    parser.add_argument("--db-url", required=True, help="Database URL")
    parser.add_argument("--patient-id", help="Filter by patient ID")
    parser.add_argument("--from-date", help="Filter by date (YYYY-MM-DD)")
    parser.add_argument("--dry-run", action="store_true", help="Dry run")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if args.command == "rebuild":
        asyncio.run(rebuild(
            db_url=args.db_url,
            patient_id=args.patient_id,
            from_date=args.from_date,
            dry_run=args.dry_run,
        ))


if __name__ == "__main__":
    main()
