"""
VCF file upload API route.

Handles:
- File upload with SHA256
- Metadata extraction
- VCF format validation
- Genome build detection
- Storage path tracking
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Form

from src.backend.config import settings
from src.backend.vcf.validator import validate_vcf
from src.backend.vcf.parser import parse_vcf
from src.backend.vcf.models import VCFUploadResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vcf", tags=["vcf"])

# Upload directory (configurable, defaults to local)
UPLOAD_DIR = os.getenv("VCF_UPLOAD_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "..", "uploads"))


async def _compute_sha256(content: bytes) -> str:
    """Compute SHA256 hash of file content."""
    return hashlib.sha256(content).hexdigest()


async def _save_upload(file: UploadFile, upload_id: str) -> tuple[str, int]:
    """Save uploaded file to storage and return path and size."""
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # Determine file extension
    ext = ".vcf.gz" if file.filename and file.filename.endswith(".gz") else ".vcf"
    storage_filename = f"{upload_id}{ext}"
    storage_path = os.path.join(UPLOAD_DIR, storage_filename)

    content = await file.read()
    with open(storage_path, "wb") as f:
        f.write(content)

    return storage_path, len(content)


@router.post("/upload", response_model=VCFUploadResponse)
async def upload_vcf(
    file: UploadFile = File(...),
    genome_build: Optional[str] = Form(None),
    sequencing_test_id: Optional[str] = Form(None),
):
    """Upload a VCF file for processing.

    Accepts .vcf and .vcf.gz files. Performs:
    - SHA256 integrity check
    - VCF format validation
    - Genome build detection
    - Record count extraction
    """
    # Validate file extension
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    if not (file.filename.endswith(".vcf") or file.filename.endswith(".vcf.gz")):
        raise HTTPException(status_code=400, detail="File must be .vcf or .vcf.gz")

    upload_id = str(uuid.uuid4())

    # Save file and compute SHA256
    try:
        storage_path, file_size = await _save_upload(file, upload_id)
    except Exception as e:
        logger.exception("Failed to save upload")
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    # Compute SHA256
    try:
        with open(storage_path, "rb") as f:
            content = f.read()
        sha256 = await _compute_sha256(content)
    except Exception as e:
        logger.exception("Failed to compute SHA256")
        sha256 = "error"

    # Validate VCF
    try:
        content_str = content.decode("utf-8", errors="replace")
    except Exception:
        content_str = ""

    if content_str:
        validation = validate_vcf(content_str, expected_build=genome_build)

        # Parse for record count
        parse_result = parse_vcf(content_str) if content_str else None
        record_count = parse_result.record_count if parse_result else 0

        # Determine genome build
        detected_build = validation.genome_build or genome_build
        if not detected_build:
            detected_build = parse_result.header.genome_build if parse_result and parse_result.header else None

        return VCFUploadResponse(
            upload_id=upload_id,
            filename=file.filename,
            size_bytes=file_size,
            sha256=sha256,
            genome_build=detected_build,
            validation_status="valid" if validation.valid else "invalid",
            record_count=record_count,
            warnings=[w.message for w in validation.warnings],
            errors=[e.message for e in validation.errors],
        )

    return VCFUploadResponse(
        upload_id=upload_id,
        filename=file.filename,
        size_bytes=file_size,
        sha256=sha256,
        validation_status="invalid",
        errors=["Could not read file content"],
    )
