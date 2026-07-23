"""Evidence package — clinical evidence integration from CIViC, DGIdb."""
from src.backend.evidence.cache import TTLCache, gene_cache, variant_cache
from src.backend.evidence.merger import EvidenceMerger

__all__ = [
    "EvidenceMerger",
    "TTLCache",
    "gene_cache",
    "variant_cache",
]
