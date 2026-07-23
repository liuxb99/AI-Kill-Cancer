"""
Knowledge domain models for the Extended Knowledge Layer.

Provides unified entity types for genes, variants, diseases, drugs,
publications, trials, guidelines, and regulatory approvals.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class KnowledgeEntity(BaseModel):
    """A knowledge entity (gene, variant, disease, drug, etc.)."""
    model_config = ConfigDict(from_attributes=True)

    id: str = ""
    entity_type: str = ""  # gene, variant, disease, drug, publication, trial, guideline, approval
    source: str = ""  # Which knowledge source
    source_id: str = ""  # Native ID in source
    name: str = ""
    description: str = ""
    aliases: list[str] = []
    identifiers: dict[str, str] = {}  # Cross-reference identifiers
    metadata: dict = {}
    retrieved_at: str = ""


class KnowledgeRelation(BaseModel):
    """A typed relation between two knowledge entities."""
    model_config = ConfigDict(from_attributes=True)

    id: str = ""
    source_entity_id: str = ""
    target_entity_id: str = ""
    relation_type: str = ""  # associated_with, treats, causes, etc.
    evidence: str = ""
    source: str = ""
    confidence: str = ""
    metadata: dict = {}


class Publication(BaseModel):
    """A biomedical publication."""
    model_config = ConfigDict(from_attributes=True)

    pmid: str = ""
    doi: str = ""
    title: str = ""
    authors: list[str] = []
    journal: str = ""
    year: int = 0
    abstract: str = ""
    keywords: list[str] = []
    mesh_terms: list[str] = []
    citation_count: int = 0
    url: str = ""


class ClinicalTrial(BaseModel):
    """A clinical trial."""
    model_config = ConfigDict(from_attributes=True)

    nct_id: str = ""
    title: str = ""
    status: str = ""
    phase: str = ""
    conditions: list[str] = []
    interventions: list[str] = []
    sponsors: list[str] = []
    enrollment: int = 0
    start_date: str = ""
    completion_date: str = ""
    url: str = ""


class GuidelineItem(BaseModel):
    """A clinical guideline recommendation."""
    model_config = ConfigDict(from_attributes=True)

    id: str = ""
    source: str = ""  # NCCN, ASCO, ESMO
    title: str = ""
    disease: str = ""
    recommendation: str = ""
    evidence_level: str = ""
    drug: str = ""
    biomarker: str = ""
    version: str = ""
    url: str = ""


class RegulatoryApproval(BaseModel):
    """A regulatory approval for a drug."""
    model_config = ConfigDict(from_attributes=True)

    id: str = ""
    drug_name: str = ""
    indication: str = ""
    agency: str = ""  # FDA, EMA
    approval_type: str = ""  # full, accelerated, orphan, breakthrough
    approval_date: str = ""
    biomarker: str = ""
    url: str = ""


class VariantDiseaseAssociation(BaseModel):
    """Association between a variant and a disease."""
    variant_id: str = ""
    disease: str = ""
    association_type: str = ""  # oncogenic, benign, risk_factor
    evidence_level: str = ""
    source: str = ""


class DrugDiseaseAssociation(BaseModel):
    """Association between a drug and a disease."""
    drug_name: str = ""
    disease: str = ""
    association_type: str = ""  # approved, trial, preclinical
    evidence_level: str = ""


class GeneDiseaseAssociation(BaseModel):
    """Association between a gene and a disease."""
    gene_symbol: str = ""
    disease: str = ""
    association_type: str = ""  # causal, risk, protective
    source: str = ""


class KnowledgeEntityResponse(BaseModel):
    entity: KnowledgeEntity | None = None
    relations: list[KnowledgeRelation] = []
    publications: list[Publication] = []
    trials: list[ClinicalTrial] = []
    guidelines: list[GuidelineItem] = []
    approvals: list[RegulatoryApproval] = []


class KnowledgeSearchResponse(BaseModel):
    query: str = ""
    results: list[KnowledgeEntity] = []
    total: int = 0
    source: str = ""
