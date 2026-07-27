"""ClinicalGraphClient — Python 侧通过 subprocess 调用 KnowGraphGo CLI。"""

import json
import logging
import subprocess
from typing import Any, Dict, List, Optional

from src.backend.schemas.clinical_graph_event import ClinicalGraphEvent

logger = logging.getLogger(__name__)


class ClinicalGraphClient:
    """KnowGraphGo CLI 适配器客户端。
    
    通过 subprocess 调用 knowgraph CLI，使用 stdin 传递 JSON 事件。
    """

    def __init__(self, cli_path: str = "knowgraph", timeout: int = 30):
        self._cli_path = cli_path
        self._timeout = timeout

    async def apply_event(self, event: ClinicalGraphEvent) -> Dict[str, Any]:
        """应用单个事件到知识图谱。"""
        event_json = event.model_dump_json()
        return await self._run_cli(["clinical", "apply"], input_data=event_json)

    async def apply_events_batch(self, events: List[ClinicalGraphEvent]) -> Dict[str, Any]:
        """批量重建知识图谱。"""
        events_json = json.dumps([json.loads(e.model_dump_json()) for e in events])
        return await self._run_cli(["clinical", "rebuild"], input_data=events_json)

    # ── 查询方法 ──────────────────────────────────────────────

    async def export_graph(self, namespace: str = "clinical") -> Dict[str, Any]:
        """导出知识图谱。"""
        return await self._run_cli(["export", namespace])

    async def query_path(self, from_id: str, to_id: str) -> Dict[str, Any]:
        """查询两个实体之间的路径。"""
        return await self._run_cli(["query", "path", from_id, to_id])

    async def query_related(self, entity_id: str, depth: int = 3) -> Dict[str, Any]:
        """查询相关实体。"""
        return await self._run_cli(["query", "related", entity_id, str(depth)])

    async def explain_relation(self, relation_id: str) -> Dict[str, Any]:
        """查询关系的解释。"""
        return await self._run_cli(["explain", "relation", relation_id])

    # ── CLI 执行 ────────────────────────────────────────────

    async def _run_cli(self, args: List[str], input_data: str = "") -> Dict[str, Any]:
        """运行 CLI 命令。"""
        try:
            result = subprocess.run(
                [self._cli_path] + args,
                input=input_data,
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
            if result.returncode != 0:
                error_msg = result.stderr.strip() or f"CLI exited with code {result.returncode}"
                logger.error("CLI error: %s", error_msg)
                return {"success": False, "error": error_msg}
            if result.stdout.strip():
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    return {"success": True, "message": result.stdout.strip()}
            return {"success": True}
        except subprocess.TimeoutExpired:
            logger.error("CLI timeout after %ds", self._timeout)
            return {"success": False, "error": f"timeout after {self._timeout}s"}
        except FileNotFoundError:
            logger.error("CLI not found: %s", self._cli_path)
            return {"success": False, "error": f"CLI not found: {self._cli_path}"}
        except Exception as e:
            logger.exception("CLI run failed")
            return {"success": False, "error": str(e)}


__all__ = ["ClinicalGraphClient"]
