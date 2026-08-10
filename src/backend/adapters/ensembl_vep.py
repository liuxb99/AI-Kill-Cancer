"""Public Ensembl VEP adapter entrypoint.

The production implementation lives in :mod:`src.backend.pipeline.vep_adapter`.
This compatibility module prevents older imports from silently receiving a
NotConfiguredAdapter after VEP support became real.
"""

from src.backend.pipeline.vep_adapter import VEPAdapter

EnsemblVEPAdapter = VEPAdapter

__all__ = ["EnsemblVEPAdapter", "VEPAdapter"]
