"""Public OpenCRAVAT adapter entrypoint.

The runtime implementation lives in :mod:`src.backend.pipeline.opencravat_adapter`.
The adapter reports unavailable when the local OpenCRAVAT executable is absent
instead of masquerading as a generic placeholder.
"""

from src.backend.pipeline.opencravat_adapter import OpenCRAVATAdapter

__all__ = ["OpenCRAVATAdapter"]
