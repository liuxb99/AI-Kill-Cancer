"""
Ensembl VEP adapter — placeholder for Phase 2 integration.

This adapter will submit variants to a local or remote Ensembl VEP instance
for transcript consequence annotation, HGVS notation, and variant classification.

MVP (Phase 1): adapter exists but returns "not_configured" status.
"""

from src.backend.adapters.base import NotConfiguredAdapter

EnsemblVEPAdapter = NotConfiguredAdapter
