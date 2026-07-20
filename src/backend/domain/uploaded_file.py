"""
UploadedFile domain model.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import Column, String, DateTime, BigInteger, Integer, JSON, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import relationship

from src.backend.database.models import CompatUUID, Base as DBBase
from src.backend.domain.enums import FileTypeEnum, UploadStatusEnum, ValidationStatusEnum, GenomeBuildConfidenceEnum, UploadDuplicateStrategyEnum


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class UploadedFileModel(DBBase):
    __tablename__ = "domain_uploaded_files"

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    sequencing_test_id = Column(CompatUUID, ForeignKey("domain_sequencing_tests.id", ondelete="SET NULL"), nullable=True, index=True)
    original_filename = Column(String(512), nullable=False)
    storage_path = Column(String(1024), nullable=True)
    media_type = Column(String(128), nullable=True)
    file_type = Column(SAEnum(FileTypeEnum), nullable=True)
    size_bytes = Column(BigInteger, nullable=True)
    sha256 = Column(String(64), nullable=True, index=True)
    decompressed_sha256 = Column(String(64), nullable=True, comment="SHA256 of decompressed content (for gzip)")
    genome_build = Column(String(32), nullable=True, comment="Detected or specified genome build")
    genome_build_confidence = Column(SAEnum(GenomeBuildConfidenceEnum), nullable=True, comment="How build was determined")
    compression = Column(String(16), nullable=True, comment="none, gzip")
    record_count = Column(Integer, nullable=True, comment="Number of variant records in file")
    validation_warnings = Column(JSON, default=list)
    validation_errors = Column(JSON, default=list)
    upload_status = Column(SAEnum(UploadStatusEnum), default=UploadStatusEnum.UPLOADING, nullable=False)
    validation_status = Column(SAEnum(ValidationStatusEnum), default=ValidationStatusEnum.PENDING, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    sequencing_test = relationship("SequencingTestModel", back_populates="uploaded_files")

    def __repr__(self):
        return f"<UploadedFileModel(id={self.id}, filename={self.original_filename!r})>"


class UploadedFileCreate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    sequencing_test_id: Optional[str] = None
    original_filename: str = Field(..., max_length=512)
    storage_path: Optional[str] = Field(None, max_length=1024)
    media_type: Optional[str] = Field(None, max_length=128)
    file_type: Optional[FileTypeEnum] = None
    size_bytes: Optional[int] = None
    sha256: Optional[str] = Field(None, max_length=64)
    decompressed_sha256: Optional[str] = Field(None, max_length=64)
    genome_build: Optional[str] = Field(None, max_length=32)
    genome_build_confidence: Optional[GenomeBuildConfidenceEnum] = None
    compression: Optional[str] = Field(None, max_length=16)
    record_count: Optional[int] = None


class UploadedFileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: str
    sequencing_test_id: Optional[str] = None
    original_filename: str
    storage_path: Optional[str] = None
    media_type: Optional[str] = None
    file_type: Optional[str] = None
    size_bytes: Optional[int] = None
    sha256: Optional[str] = None
    decompressed_sha256: Optional[str] = None
    genome_build: Optional[str] = None
    genome_build_confidence: Optional[str] = None
    compression: Optional[str] = None
    record_count: Optional[int] = None
    validation_warnings: list = []
    validation_errors: list = []
    upload_status: str
    validation_status: str
    uploaded_at: datetime
