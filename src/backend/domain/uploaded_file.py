"""
UploadedFile domain model.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import Column, String, DateTime, BigInteger, Enum as SAEnum, ForeignKey
from sqlalchemy.orm import relationship

from src.backend.database.models import CompatUUID, Base as DBBase
from src.backend.domain.enums import FileTypeEnum, UploadStatusEnum, ValidationStatusEnum


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class UploadedFileModel(DBBase):
    __tablename__ = "domain_uploaded_files"

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    sequencing_test_id = Column(CompatUUID, ForeignKey("domain_sequencing_tests.id", ondelete="CASCADE"), nullable=False, index=True)
    original_filename = Column(String(512), nullable=False)
    storage_path = Column(String(1024), nullable=True)
    media_type = Column(String(128), nullable=True)
    file_type = Column(SAEnum(FileTypeEnum), nullable=True)
    size_bytes = Column(BigInteger, nullable=True)
    sha256 = Column(String(64), nullable=True)
    upload_status = Column(SAEnum(UploadStatusEnum), default=UploadStatusEnum.UPLOADING, nullable=False)
    validation_status = Column(SAEnum(ValidationStatusEnum), default=ValidationStatusEnum.PENDING, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    sequencing_test = relationship("SequencingTestModel", back_populates="uploaded_files")

    def __repr__(self):
        return f"<UploadedFileModel(id={self.id}, filename={self.original_filename!r})>"


class UploadedFileCreate(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    sequencing_test_id: str
    original_filename: str = Field(..., max_length=512)
    storage_path: Optional[str] = Field(None, max_length=1024)
    media_type: Optional[str] = Field(None, max_length=128)
    file_type: Optional[FileTypeEnum] = None
    size_bytes: Optional[int] = None
    sha256: Optional[str] = Field(None, max_length=64)


class UploadedFileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: str
    sequencing_test_id: str
    original_filename: str
    storage_path: Optional[str] = None
    media_type: Optional[str] = None
    file_type: Optional[str] = None
    size_bytes: Optional[int] = None
    sha256: Optional[str] = None
    upload_status: str
    validation_status: str
    uploaded_at: datetime
