"""
VCF-specific Pydantic models.
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class VCFUploadResponse(BaseModel):
    """Response after VCF file upload and initial validation."""
    upload_id: str
    filename: str
    size_bytes: int
    sha256: str
    genome_build: Optional[str] = None
    validation_status: str  # "pending" | "valid" | "invalid"
    record_count: int = 0
    warnings: list[str] = []
    errors: list[str] = []
