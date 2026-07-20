"""
Extended Knowledge Layer — unified oncology knowledge integration.

Provides adapter architecture for multiple knowledge sources,
cross-source identifier mapping, and persistent knowledge graphs.
"""

from src.backend.knowledge.models import (
    KnowledgeEntity, KnowledgeRelation,
    Publication, ClinicalTrial, GuidelineItem, RegulatoryApproval,
    VariantDiseaseAssociation, DrugDiseaseAssociation, GeneDiseaseAssociation,
    KnowledgeEntityResponse, KnowledgeSearchResponse,
)
from src.backend.knowledge.identifiers import (
    IdentifierMapper, IdentifierMapping,
    normalize_hgvs, normalize_gene_symbol,
)
from src.backend.knowledge.repository import (
    KnowledgeEntityModel, KnowledgeRelationModel,
    KnowledgeRepository,
)
from src.backend.knowledge.service import KnowledgeService

__all__ = [
    "KnowledgeEntity", "KnowledgeRelation",
    "Publication", "ClinicalTrial", "GuidelineItem", "RegulatoryApproval",
    "VariantDiseaseAssociation", "DrugDiseaseAssociation", "GeneDiseaseAssociation",
    "KnowledgeEntityResponse", "KnowledgeSearchResponse",
    "IdentifierMapper", "IdentifierMapping",
    "normalize_hgvs", "normalize_gene_symbol",
    "KnowledgeEntityModel", "KnowledgeRelationModel",
    "KnowledgeRepository",
    "KnowledgeService",
]
