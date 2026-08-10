"""Public CIViC adapter entrypoint.

The production implementation lives in :mod:`src.backend.pipeline.civic_adapter`.
This module remains as the stable import path used by the adapter registry and
older callers.
"""

from src.backend.pipeline.civic_adapter import CIViCAdapter

__all__ = ["CIViCAdapter"]
