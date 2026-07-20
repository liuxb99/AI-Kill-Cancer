"""
VCF-specific Pydantic models.
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class VCFUploadResponse(BaseModel):
    """Response after VCF file upload and initial validation."""
    upload_id: str
    database_record_id: Optional[str] = None
    filename: str
    size_bytes: int
    sha256: str
    file_type: Optional[str] = None
    compression: Optional[str] = None
    genome_build: Optional[str] = None
    genome_build_confidence: Optional[str] = None
    validation_status: str  # "pending" | "valid" | "invalid"
    analysis_eligible: Optional[str] = None
    record_count: int = 0
    warnings: list[str] = []
    errors: list[str] = []
    created_at: str = ""
