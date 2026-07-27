"""Graph Projection 重试策略。"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List


@dataclass
class GraphProjectionRetryPolicy:
    """集中管理重试间隔和最大尝试次数。"""

    # 重试间隔（分钟），按顺序使用
    retry_delays_minutes: List[int] = None

    # 最大死信尝试次数
    max_attempts: int = 5

    def __post_init__(self):
        if self.retry_delays_minutes is None:
            self.retry_delays_minutes = [1, 5, 15, 60, 360]

    @property
    def max_delays(self) -> int:
        return len(self.retry_delays_minutes)

    def next_available_at(self, attempt_count: int) -> datetime:
        """计算下次可用时间。"""
        idx = min(attempt_count, len(self.retry_delays_minutes) - 1)
        return datetime.utcnow() + timedelta(minutes=self.retry_delays_minutes[idx])

    def is_dead_letter(self, attempt_count: int) -> bool:
        """判断是否达到死信阈值。"""
        return attempt_count >= self.max_attempts


# 默认策略
DEFAULT_RETRY_POLICY = GraphProjectionRetryPolicy()


__all__ = ["GraphProjectionRetryPolicy", "DEFAULT_RETRY_POLICY"]
