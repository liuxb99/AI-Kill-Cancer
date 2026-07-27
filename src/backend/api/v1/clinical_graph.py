"""Clinical Graph API — 知识图谱查询与状态管理。"""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.auth import require_auth, require_permission
from src.backend.auth.models import Permission
from src.backend.database.session import get_db
from src.backend.domain.clinical_graph_outbox import ClinicalGraphOutboxModel
from src.backend.repositories.clinical_graph_outbox_repo import ClinicalGraphOutboxRepository

router = APIRouter(prefix="/clinical-graph", tags=["clinical-graph"])


@router.get("/status")
async def get_graph_status(
    db: AsyncSession = Depends(get_db),
    user: Any = Depends(require_auth),
) -> Dict[str, Any]:
    """返回图谱投影状态统计。

    统计 ClinicalGraphOutbox 表中各类状态的事件数量，
    反映知识图谱投影的整体健康度。
    """
    repo = ClinicalGraphOutboxRepository(db)
    # 按 status 字段分组统计
    stmt = (
        select(
            ClinicalGraphOutboxModel.status,
            func.count(ClinicalGraphOutboxModel.id).label("count"),
        )
        .group_by(ClinicalGraphOutboxModel.status)
    )
    result = await db.execute(stmt)
    rows = result.all()

    status_counts: Dict[str, int] = {row.status: row.count for row in rows}
    total = sum(status_counts.values())

    return {
        "status": "operational",
        "total_events": total,
        "status_counts": status_counts,
        "failed": status_counts.get("failed", 0) + status_counts.get("dead_letter", 0),
        "pending": status_counts.get("pending", 0),
        "processing": status_counts.get("processing", 0),
        "completed": status_counts.get("completed", 0),
        "dead_letter": status_counts.get("dead_letter", 0),
    }


@router.get("/failed-events")
async def list_failed_events(
    db: AsyncSession = Depends(get_db),
    user: Any = Depends(require_auth),
) -> List[Dict[str, Any]]:
    """返回失败/死信事件列表。"""
    repo = ClinicalGraphOutboxRepository(db)
    events = await repo.list_failed()
    return [
        {
            "event_id": e.event_id,
            "event_type": e.event_type,
            "aggregate_type": e.aggregate_type,
            "aggregate_id": e.aggregate_id,
            "status": e.status,
            "attempt_count": e.attempt_count,
            "last_error": e.last_error,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in events
    ]


@router.post("/retry/{event_id}")
async def retry_event(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    user: Any = Depends(require_auth),
    _: Any = Depends(require_permission(Permission.MANAGE_SETTINGS)),
) -> Dict[str, Any]:
    """重试指定事件（Admin/Researcher 角色）。

    将事件状态重置为 pending，清除错误信息，以便重试处理器重新消费。
    需要 manage:settings 权限（Admin/Researcher）。
    """
    repo = ClinicalGraphOutboxRepository(db)
    event = await repo.get_by_event_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.status not in ("failed", "dead_letter"):
        raise HTTPException(
            status_code=409,
            detail=f"Event is in status '{event.status}', cannot retry",
        )
    # 重置为 pending
    event.status = "pending"
    event.attempt_count = 0
    event.last_error = None
    await db.commit()
    return {"status": "retrying", "event_id": event_id}


@router.get("/patient/{patient_id}/thread")
async def get_patient_thread(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    user: Any = Depends(require_auth),
) -> Dict[str, Any]:
    """查询患者的 Digital Thread。

    从知识图谱中检索该患者相关的实体与关系路径。
    若 KnowGraphGo CLI 不可用，返回 projection_unavailable。
    """
    try:
        from src.backend.clinical_graph.client import ClinicalGraphClient

        client = ClinicalGraphClient()
        result = await client.query_related(patient_id, depth=3)
        if result.get("success"):
            return {
                "patient_id": patient_id,
                "entities": result.get("entities", []),
                "relations": result.get("relations", []),
                "projection_status": "connected",
            }
        return {
            "patient_id": patient_id,
            "entities": [],
            "relations": [],
            "projection_status": "projection_unavailable",
            "message": result.get("error", "graph query returned no data"),
        }
    except Exception:
        logger = __import__("logging").getLogger(__name__)
        logger.exception("patient_thread query failed for %s", patient_id)
        return {
            "patient_id": patient_id,
            "entities": [],
            "relations": [],
            "projection_status": "projection_unavailable",
            "message": "KnowGraphGo CLI not available or query failed",
        }


@router.get("/recommendation/{recommendation_id}/explain")
async def get_recommendation_explain(
    recommendation_id: str,
    db: AsyncSession = Depends(get_db),
    user: Any = Depends(require_auth),
) -> Dict[str, Any]:
    """查询推荐的 Explain 信息。

    从知识图谱中检索推荐决策的推导路径与证据链。
    若 KnowGraphGo CLI 不可用，返回 projection_pending。
    """
    try:
        from src.backend.clinical_graph.client import ClinicalGraphClient

        client = ClinicalGraphClient()
        related = await client.query_related(recommendation_id, depth=2)
        explain = await client.explain_relation(recommendation_id)
        if related.get("success") or explain.get("success"):
            return {
                "recommendation_id": recommendation_id,
                "entities": related.get("entities", []),
                "relations": related.get("relations", []),
                "provenance": explain.get("provenance", explain.get("evidence", [])),
                "explanation": explain.get("explanation", explain.get("message")),
                "projection_status": "connected",
            }
        return {
            "recommendation_id": recommendation_id,
            "entities": [],
            "relations": [],
            "provenance": [],
            "explanation": None,
            "projection_status": "projection_pending",
            "message": related.get("error") or explain.get("error") or "graph data not yet projected",
        }
    except Exception:
        logger = __import__("logging").getLogger(__name__)
        logger.exception("recommendation_explain query failed for %s", recommendation_id)
        return {
            "recommendation_id": recommendation_id,
            "entities": [],
            "relations": [],
            "provenance": [],
            "explanation": None,
            "projection_status": "projection_pending",
            "message": "KnowGraphGo CLI not available or query failed",
        }


@router.get("/consensus/{consensus_id}/explain")
async def get_consensus_explain(
    consensus_id: str,
    db: AsyncSession = Depends(get_db),
    user: Any = Depends(require_auth),
) -> Dict[str, Any]:
    """查询共识的 Explain 信息。

    从知识图谱中检索肿瘤 board 共识的推导路径与证据链。
    若 KnowGraphGo CLI 不可用，返回 projection_pending。
    """
    try:
        from src.backend.clinical_graph.client import ClinicalGraphClient

        client = ClinicalGraphClient()
        related = await client.query_related(consensus_id, depth=2)
        explain = await client.explain_relation(consensus_id)
        if related.get("success") or explain.get("success"):
            return {
                "consensus_id": consensus_id,
                "entities": related.get("entities", []),
                "relations": related.get("relations", []),
                "provenance": explain.get("provenance", explain.get("evidence", [])),
                "explanation": explain.get("explanation", explain.get("message")),
                "projection_status": "connected",
            }
        return {
            "consensus_id": consensus_id,
            "entities": [],
            "relations": [],
            "provenance": [],
            "explanation": None,
            "projection_status": "projection_pending",
            "message": related.get("error") or explain.get("error") or "graph data not yet projected",
        }
    except Exception:
        logger = __import__("logging").getLogger(__name__)
        logger.exception("consensus_explain query failed for %s", consensus_id)
        return {
            "consensus_id": consensus_id,
            "entities": [],
            "relations": [],
            "provenance": [],
            "explanation": None,
            "projection_status": "projection_pending",
            "message": "KnowGraphGo CLI not available or query failed",
        }
