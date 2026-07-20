"""
Variant domain model.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import Column, String, Integer, Float, DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import relationship

from src.backend.database.models import CompatUUID, Base as DBBase
from src.backend.domain.enums import (
    DriverStatusEnum,
    NormalizationStatusEnum,
    OncogenicityEnum,
    VariantOriginEnum,
    VariantTypeEnum,
    ZygosityEnum,
)


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class VariantModel(DBBase):
    __tablename__ = "domain_variants"

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    sequencing_test_id = Column(CompatUUID, ForeignKey("domain_sequencing_tests.id", ondelete="CASCADE"), nullable=False, index=True)
    gene_id = Column(CompatUUID, ForeignKey("domain_genes.id", ondelete="SET NULL"), nullable=True, index=True)
    gene_symbol = Column(String(32), nullable=False, index=True)
    chromosome = Column(String(16), nullable=False)
    position = Column(Integer, nullable=False)
    reference = Column(String(256), nullable=False)
    alternate = Column(String(256), nullable=False)
    genome_build = Column(String(32), nullable=False)
    variant_type = Column(SAEnum(VariantTypeEnum), nullable=False)
    transcript = Column(String(64), nullable=True)
    hgvs_g = Column(String(256), nullable=True)
    hgvs_c = Column(String(256), nullable=True)
    hgvs_p = Column(String(256), nullable=True)
    vaf = Column(Float, nullable=True)
    read_depth = Column(Integer, nullable=True)
    origin = Column(SAEnum(VariantOriginEnum), nullable=False)
    clinical_significance = Column(String(128), nullable=True)
    oncogenicity = Column(SAEnum(OncogenicityEnum), default=OncogenicityEnum.NOT_ASSESSED, nullable=False)
    driver_status = Column(SAEnum(DriverStatusEnum), default=DriverStatusEnum.UNKNOWN, nullable=False)
    zygosity = Column(SAEnum(ZygosityEnum), default=ZygosityEnum.UNKNOWN, nullable=False)
    source_record_id = Column(String(256), nullable=True)
    annotation_version = Column(String(64), nullable=True)
    normalization_status = Column(SAEnum(NormalizationStatusEnum), default=NormalizationStatusEnum.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    sequencing_test = relationship("SequencingTestModel", back_populates="variants")
    gene = relationship("GeneModel", back_populates="variants")
    drug_candidates = relationship("DrugCandidateModel", back_populates="variant", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<VariantModel(id={self.id}, gene={self.gene_symbol}, hgvs_p={self.hgvs_p!r})>"


class VariantImport(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    sequencing_test_id: str
    gene_symbol: str = Field(..., max_length=32)
    chromosome: str = Field(..., max_length=16)
    position: int
    reference: str
    alternate: str
    genome_build: str = Field(..., max_length=32)
    variant_type: VariantTypeEnum
    transcript: Optional[str] = Field(None, max_length=64)
    hgvs_g: Optional[str] = Field(None, max_length=256)
    hgvs_c: Optional[str] = Field(None, max_length=256)
    hgvs_p: Optional[str] = Field(None, max_length=256)
    vaf: Optional[float] = None
    read_depth: Optional[int] = None
    origin: VariantOriginEnum = VariantOriginEnum.UNKNOWN
    clinical_significance: Optional[str] = Field(None, max_length=128)
    oncogenicity: OncogenicityEnum = OncogenicityEnum.NOT_ASSESSED
    driver_status: DriverStatusEnum = DriverStatusEnum.UNKNOWN
    zygosity: ZygosityEnum = ZygosityEnum.UNKNOWN
    source_record_id: Optional[str] = Field(None, max_length=256)


class VariantImportBatch(BaseModel):
    items: list[VariantImport]


class VariantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: str
    sequencing_test_id: str
    gene_id: Optional[str] = None
    gene_symbol: str
    chromosome: str
    position: int
    reference: str
    alternate: str
    genome_build: str
    variant_type: str
    transcript: Optional[str] = None
    hgvs_g: Optional[str] = None
    hgvs_c: Optional[str] = None
    hgvs_p: Optional[str] = None
    vaf: Optional[float] = None
    read_depth: Optional[int] = None
    origin: str
    clinical_significance: Optional[str] = None
    oncogenicity: str
    driver_status: str
    zygosity: str
    normalization_status: str
    created_at: datetime
    updated_at: datetime


class VariantListResponse(BaseModel):
    items: list[VariantResponse]
    total: int
    skip: int
    limit: int
