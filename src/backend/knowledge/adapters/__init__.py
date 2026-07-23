"""
Knowledge source adapters for public oncology APIs.

Each adapter implements:
- health_check()
- search(query) → list[dict]
- normalize(raw_data) → list[dict]
- supports(query_type) → bool
"""

from src.backend.knowledge.adapters.clinicaltrials import ClinicalTrialsAdapter
from src.backend.knowledge.adapters.clinvar import ClinVarAdapter
from src.backend.knowledge.adapters.pubmed import PubMedAdapter

__all__ = ["ClinVarAdapter", "PubMedAdapter", "ClinicalTrialsAdapter"]
