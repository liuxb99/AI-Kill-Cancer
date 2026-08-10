"""Public DGIdb adapter entrypoint.

The production implementation lives in :mod:`src.backend.pipeline.dgidb_adapter`.
This module remains as the stable import path used by the adapter registry and
older callers.
"""

from src.backend.pipeline.dgidb_adapter import DGIdbAdapter

__all__ = ["DGIdbAdapter"]
