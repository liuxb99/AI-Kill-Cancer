"""
UploadedFile domain model.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import JSON, BigInteger, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import relationship

from src.backend.database.models import Base as DBBase
from src.backend.database.models import CompatUUID
from src.backend.domain.enums import (
    FileTypeEnum,
    GenomeBuildConfidenceEnum,
    UploadEligibilityEnum,
    UploadStatusEnum,
    ValidationStatusEnum,
)


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
    decompressed_size_bytes = Column(BigInteger, nullable=True, comment="Size after decompression (for gzip)")
    upload_status = Column(SAEnum(UploadStatusEnum), default=UploadStatusEnum.UPLOADING, nullable=False)
    validation_status = Column(SAEnum(ValidationStatusEnum), default=ValidationStatusEnum.PENDING, nullable=False)
    analysis_eligible = Column(SAEnum(UploadEligibilityEnum), default=UploadEligibilityEnum.PENDING_VALIDATION, nullable=False)
    quarantine_reason = Column(String(256), nullable=True, comment="Reason for quarantine/rejection")
    retention_until = Column(DateTime, nullable=True, comment="When this upload record may be cleaned up")
    duplicate_of_upload_id = Column(String(36), nullable=True, comment="Points to original upload if this is a blob duplicate")
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    sequencing_test = relationship("SequencingTestModel", back_populates="uploaded_files")

    def __repr__(self):
        return f"<UploadedFileModel(id={self.id}, filename={self.original_filename!r})>"


class UploadedFileCreate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    sequencing_test_id: str | None = None
    original_filename: str = Field(..., max_length=512)
    storage_path: str | None = Field(None, max_length=1024)
    media_type: str | None = Field(None, max_length=128)
    file_type: FileTypeEnum | None = None
    size_bytes: int | None = None
    decompressed_size_bytes: int | None = None
    sha256: str | None = Field(None, max_length=64)
    decompressed_sha256: str | None = Field(None, max_length=64)
    genome_build: str | None = Field(None, max_length=32)
    genome_build_confidence: GenomeBuildConfidenceEnum | None = None
    compression: str | None = Field(None, max_length=16)
    record_count: int | None = None
    analysis_eligible: UploadEligibilityEnum | None = None
    quarantine_reason: str | None = Field(None, max_length=256)
    retention_until: datetime | None = None
    duplicate_of_upload_id: str | None = Field(None, max_length=36)


class UploadedFileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: str
    sequencing_test_id: str | None = None
    original_filename: str
    file_type: str | None = None
    size_bytes: int | None = None
    decompressed_size_bytes: int | None = None
    sha256: str | None = None
    decompressed_sha256: str | None = None
    genome_build: str | None = None
    genome_build_confidence: str | None = None
    compression: str | None = None
    record_count: int | None = None
    validation_warnings: list = []
    validation_errors: list = []
    upload_status: str
    validation_status: str
    analysis_eligible: str | None = None
    quarantine_reason: str | None = None
    retention_until: datetime | None = None
    duplicate_of_upload_id: str | None = None
    created_at: datetime | None = None
    uploaded_at: datetime
