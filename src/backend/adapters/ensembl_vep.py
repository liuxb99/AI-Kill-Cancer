"""Public Ensembl VEP adapter entrypoint.

The production implementation lives in :mod:`src.backend.pipeline.vep_adapter`.
This compatibility module keeps older imports wired to the concrete VEP
implementation after REST annotation support became available.
"""

from src.backend.pipeline.vep_adapter import VEPAdapter

EnsemblVEPAdapter = VEPAdapter

__all__ = ["EnsemblVEPAdapter", "VEPAdapter"]
