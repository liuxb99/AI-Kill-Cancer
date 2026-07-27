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
    from src.backend.clinical_graph.client import ClinicalGraphClient

    repo = ClinicalGraphOutboxRepository(db)
    counts = await repo.get_status_counts()
    total = sum(counts.values())

    dead_letter = counts.get("dead_letter", 0)
    failed = counts.get("failed", 0)
    pending = counts.get("pending", 0)
    processing = counts.get("processing", 0)
    completed = counts.get("completed", 0)

    # 检查 CLI 可用性
    cli_available = False
    cli_check_error = None
    verify_result = None
    try:
        client = ClinicalGraphClient()
        result = await client._run_cli(["--help"])
        cli_available = result.get("success", False)
        if cli_available:
            verify = await client._run_cli(["clinical", "verify"])
            verify_result = "pass" if verify.get("success") else "fail"
    except Exception as e:
        cli_check_error = str(e)

    # 查 last completed projection time
    last_completed = None
    try:
        stmt = (
            select(ClinicalGraphOutboxModel.processed_at)
            .where(ClinicalGraphOutboxModel.status == "completed")
            .order_by(ClinicalGraphOutboxModel.processed_at.desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        if row:
            last_completed = row.isoformat() if hasattr(row, 'isoformat') else str(row)
    except Exception:
        pass

    # 查 stale processing count
    stale_count = 0
    try:
        stale_count = await repo.release_stale(timeout_minutes=30)
    except Exception:
        pass

    # 查 oldest pending event age
    oldest_pending_age = None
    try:
        stmt = (
            select(ClinicalGraphOutboxModel.created_at)
            .where(ClinicalGraphOutboxModel.status.in_(["pending", "failed"]))
            .order_by(ClinicalGraphOutboxModel.created_at.asc())
            .limit(1)
        )
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        if row:
            from datetime import datetime
            oldest_pending_age = (datetime.utcnow() - row).total_seconds()
    except Exception:
        pass

    # 决定整体状态
    if not cli_available:
        overall_status = "unavailable"
    elif dead_letter > 0 or stale_count > 0:
        overall_status = "degraded"
    else:
        overall_status = "operational"

    return {
        "status": overall_status,
        "total_events": total,
        "status_counts": counts,
        "failed": failed,
        "pending": pending,
        "processing": processing,
        "completed": completed,
        "dead_letter": dead_letter,
        "cli_available": cli_available,
        "cli_error": cli_check_error,
        "verify_result": verify_result,
        "last_completed_projection_time": last_completed,
        "stale_processing_count": stale_count,
        "oldest_pending_event_age_seconds": oldest_pending_age,
        "degraded_reason": _get_degraded_reason(counts, cli_available, stale_count, dead_letter),
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
        from src.backend.clinical_graph.id_factory import ClinicalGraphIDFactory

        client = ClinicalGraphClient()
        graph_id = ClinicalGraphIDFactory.patient_id(patient_id)
        result = await client.query_related(graph_id, depth=3)
        entities = result.get("entities", [])
        relations = result.get("relations", [])
        if result.get("success") and (entities or relations):
            return {
                "patient_id": patient_id,
                "entities": entities,
                "relations": relations,
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
        from src.backend.clinical_graph.id_factory import ClinicalGraphIDFactory

        client = ClinicalGraphClient()
        graph_id = ClinicalGraphIDFactory.recommendation_id(recommendation_id)
        related = await client.query_related(graph_id, depth=3)

        entities = related.get("entities", [])
        relations = related.get("relations", [])

        if entities:
            return {
                "recommendation_id": recommendation_id,
                "entities": entities,
                "relations": relations,
                "provenance": related.get("provenance", []),
                "explanation": _build_explain_text(entities, relations, "recommendation"),
                "projection_status": "connected",
            }
        return {
            "recommendation_id": recommendation_id,
            "entities": [],
            "relations": [],
            "provenance": [],
            "explanation": None,
            "projection_status": "projection_pending",
            "message": "no graph data found",
        }
    except Exception:
        import logging
        logging.getLogger(__name__).exception("recommendation_explain failed for %s", recommendation_id)
        return {
            "recommendation_id": recommendation_id,
            "entities": [], "relations": [], "provenance": [], "explanation": None,
            "projection_status": "projection_pending",
            "message": "KnowGraphGo CLI not available",
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
        from src.backend.clinical_graph.id_factory import ClinicalGraphIDFactory

        client = ClinicalGraphClient()
        graph_id = ClinicalGraphIDFactory.consensus_id(consensus_id)
        related = await client.query_related(graph_id, depth=3)

        entities = related.get("entities", [])
        relations = related.get("relations", [])

        if entities:
            return {
                "consensus_id": consensus_id,
                "entities": entities,
                "relations": relations,
                "provenance": related.get("provenance", []),
                "explanation": _build_explain_text(entities, relations, "consensus"),
                "projection_status": "connected",
            }
        return {
            "consensus_id": consensus_id,
            "entities": [],
            "relations": [],
            "provenance": [],
            "explanation": None,
            "projection_status": "projection_pending",
            "message": "no graph data found",
        }
    except Exception:
        import logging
        logging.getLogger(__name__).exception("consensus_explain failed for %s", consensus_id)
        return {
            "consensus_id": consensus_id,
            "entities": [], "relations": [], "provenance": [], "explanation": None,
            "projection_status": "projection_pending",
            "message": "KnowGraphGo CLI not available",
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Helper functions
# ═══════════════════════════════════════════════════════════════════════════════


def _get_degraded_reason(counts: dict, cli_available: bool, stale_count: int = 0, dead_letter: int = 0) -> str | None:
    """返回服务降级的原因描述。"""
    if not cli_available:
        return "KnowGraphGo CLI is not available"
    dead_letter = dead_letter or counts.get("dead_letter", 0)
    reasons = []
    if dead_letter > 0:
        reasons.append(f"{dead_letter} dead-letter events")
    if stale_count > 0:
        reasons.append(f"{stale_count} stale processing events recovered")
    if counts.get("failed", 0) > 0:
        reasons.append(f"{counts['failed']} failed events")
    if not reasons:
        return None
    return "; ".join(reasons)


def _build_explain_text(entities: list, relations: list, kind: str) -> str:
    """從 entities/relations 建構可讀的解釋文字。"""
    if kind == "recommendation":
        drugs = [e.get("name", "") for e in entities if e.get("kind") == "drug"]
        evidence_count = sum(1 for e in entities if e.get("kind") == "evidence")
        parts = [f"Found {len(entities)} related entities and {len(relations)} relations."]
        if drugs:
            parts.append(f"Recommended drugs: {', '.join(drugs)}.")
        if evidence_count:
            parts.append(f"Supported by {evidence_count} evidence items.")
        return " ".join(parts)
    elif kind == "consensus":
        opinions = [e.get("name", "") for e in entities if e.get("kind") == "specialist_opinion"]
        specialties = [e.get("name", "") for e in entities if e.get("kind") == "specialty"]
        parts = [f"Found {len(entities)} related entities and {len(relations)} relations."]
        if opinions:
            parts.append(f"Specialist opinions: {len(opinions)}.")
        if specialties:
            parts.append(f"Participating specialties: {', '.join(specialties)}.")
        return " ".join(parts)
    return f"Found {len(entities)} entities and {len(relations)} relations."
