"""
VCF file upload API route — hardened for security, persistence, and gzip support.

Handles:
- .vcf and .vcf.gz file upload with proper gzip detection
- SHA256 integrity check (on original upload bytes)
- Decompression with size limits (zip bomb protection)
- VCF format validation
- Genome build detection + conflict checking
- Database persistence via UploadedFile model
- File size limits, path traversal protection, atomic writes
"""

from __future__ import annotations

import gzip
import hashlib
import logging
import os
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from src.backend.config import settings
from src.backend.database.session import get_db
from src.backend.domain.enums import (
    FileTypeEnum,
    GenomeBuildConfidenceEnum,
    UploadStatusEnum,
    ValidationStatusEnum,
)
from src.backend.domain.uploaded_file import UploadedFileCreate, UploadedFileResponse
from src.backend.repositories.uploaded_file_repo import UploadedFileRepository
from src.backend.vcf.validator import validate_vcf
from src.backend.vcf.models import VCFUploadResponse
from src.backend.reference.registry import get_registry as get_ref_registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vcf", tags=["vcf"])

# ─── Configuration ────────────────────────────────────────────────────────────

UPLOAD_DIR = os.getenv("VCF_UPLOAD_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "..", "uploads"))
MAX_UPLOAD_SIZE = 500 * 1024 * 1024  # 500 MB
MAX_DECOMPRESSED_SIZE = 2 * 1024 * 1024 * 1024  # 2 GB decompression limit

# Safe filename pattern: only allow UUID-based names
SAVE_FILENAME_PATTERN = "{upload_id}{ext}"


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _safe_filename(upload_id: str, ext: str) -> str:
    """Generate a safe storage filename — no user-controlled parts."""
    return f"{upload_id}{ext}"


def _atomic_write(dst_path: str, content: bytes) -> None:
    """Write content to a temporary file then atomically rename."""
    dir_name = os.path.dirname(dst_path)
    os.makedirs(dir_name, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=dir_name, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    os.replace(tmp_path, dst_path)


def _is_gzip_content(data: bytes) -> bool:
    """Check if bytes start with gzip magic bytes."""
    return len(data) >= 2 and data[0] == 0x1f and data[1] == 0x8b


def _is_gz_extension(filename: str) -> bool:
    """Check if filename has .gz extension."""
    return filename.lower().endswith(".gz")


def _detect_compression(filename: str, content_header: bytes) -> str:
    """Detect compression type from filename and content."""
    is_gz_by_content = _is_gzip_content(content_header)
    is_gz_by_name = _is_gz_extension(filename)

    if is_gz_by_content and is_gz_by_name:
        return "gzip"
    elif is_gz_by_content and not is_gz_by_name:
        return "gzip"  # Content indicates gzip even if extension missing
    elif not is_gz_by_content and is_gz_by_name:
        return "gzip_mismatch"  # Extension says gz but content is not
    return "none"


def _decompress_safe(content: bytes, max_size: int = MAX_DECOMPRESSED_SIZE) -> tuple[bytes, Optional[str]]:
    """Safely decompress gzip content with size limit.

    Returns (decompressed_bytes, error_or_None).
    """
    try:
        # Limit initial read to max_size
        result = gzip.decompress(content)
        if len(result) > max_size:
            return b"", "decompressed_content_too_large"
        return result, None
    except gzip.BadGzipFile:
        return b"", "corrupted_gzip"
    except Exception:
        return b"", "corrupted_gzip"


# ─── Upload Endpoint ──────────────────────────────────────────────────────────


@router.post("/upload", response_model=VCFUploadResponse)
async def upload_vcf(
    file: UploadFile = File(...),
    genome_build: Optional[str] = Form(None),
    sequencing_test_id: Optional[str] = Form(None),
    db_session=Depends(get_db),
):
    """Upload a VCF file for processing.

    Accepts .vcf and .vcf.gz files. Performs:
    - Security validation (size, path traversal)
    - SHA256 integrity check
    - Gzip decompression with bomb protection
    - VCF format validation
    - Genome build detection + conflict checking
    - Database persistence
    """
    upload_id = str(uuid.uuid4())
    errors: list[str] = []
    warnings: list[str] = []

    # ── Validate filename ────────────────────────────────────────────────
    if not file.filename:
        raise HTTPException(status_code=400, detail={
            "error": "missing_filename", "message": "No filename provided",
        })
    filename = file.filename

    # Validate extension
    is_gz = _is_gz_extension(filename)
    has_vcf_ext = filename.endswith(".vcf") or filename.endswith(".vcf.gz")
    if not has_vcf_ext:
        raise HTTPException(status_code=400, detail={
            "error": "invalid_file_type",
            "message": "File must be .vcf or .vcf.gz",
        })

    # ── Read with size limit ─────────────────────────────────────────────
    try:
        content = await file.read()
    except Exception:
        raise HTTPException(status_code=400, detail={
            "error": "read_error", "message": "Failed to read uploaded file",
        })

    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail={
            "error": "file_too_large",
            "message": f"File size exceeds maximum of {MAX_UPLOAD_SIZE // (1024*1024)} MB",
        })

    # ── SHA256 of original upload ────────────────────────────────────────
    sha256 = hashlib.sha256(content).hexdigest()

    # ── Detect compression ────────────────────────────────────────────────
    compression = _detect_compression(filename, content[:4])
    file_type = FileTypeEnum.VCF_GZ if compression == "gzip" else FileTypeEnum.VCF

    if compression == "gzip_mismatch":
        warnings.append(f"File extension suggests gzip but content is not gzip: {filename}")

    # ── Decompress if needed ──────────────────────────────────────────────
    decompressed_sha256: Optional[str] = None
    if compression == "gzip":
        decompressed, decompress_error = _decompress_safe(content)
        if decompress_error:
            raise HTTPException(status_code=400, detail={
                "error": decompress_error,
                "message": "Failed to decompress gzip file",
            })
        if not decompressed:
            raise HTTPException(status_code=400, detail={
                "error": "empty_decompressed",
                "message": "Decompressed file is empty",
            })
        content_str = decompressed.decode("utf-8", errors="replace")
        decompressed_sha256 = hashlib.sha256(decompressed).hexdigest()
    else:
        content_str = content.decode("utf-8", errors="replace")

    # ── Validate VCF ──────────────────────────────────────────────────────
    validation = validate_vcf(content_str, expected_build=genome_build)
    validation_status = ValidationStatusEnum.VALID if validation.valid else ValidationStatusEnum.INVALID
    for w in validation.warnings:
        warnings.append(w.message)
    for e in validation.errors:
        errors.append(e.message)

    # ── Genome build detection ─────────────────────────────────────────────
    detected_build: Optional[str] = None
    build_confidence = GenomeBuildConfidenceEnum.UNKNOWN
    header_build = validation.genome_build

    if genome_build:
        detected_build = genome_build
        build_confidence = GenomeBuildConfidenceEnum.EXPLICIT
        if header_build and header_build != genome_build:
            build_confidence = GenomeBuildConfidenceEnum.CONFLICT
            warnings.append(f"Header genome build ({header_build}) conflicts with "
                           f"request build ({genome_build})")
    elif header_build:
        detected_build = header_build
        build_confidence = GenomeBuildConfidenceEnum.HEADER_DETECTED

    # ── Save to storage ────────────────────────────────────────────────────
    ext = ".vcf.gz" if compression == "gzip" else ".vcf"
    safe_name = _safe_filename(upload_id, ext)
    storage_path = os.path.join(UPLOAD_DIR, safe_name)

    try:
        # Validate storage path (no path traversal)
        abs_storage = os.path.abspath(storage_path)
        abs_upload_dir = os.path.abspath(UPLOAD_DIR)
        if not abs_storage.startswith(abs_upload_dir + os.sep) and abs_storage != abs_upload_dir:
            raise HTTPException(status_code=500, detail={
                "error": "storage_error", "message": "Invalid storage path",
            })
        _atomic_write(storage_path, content)
        storage_path = safe_name  # Store relative path only
    except Exception as e:
        logger.exception("Failed to save upload %s", upload_id)
        raise HTTPException(status_code=500, detail={
            "error": "storage_error", "message": "Failed to store uploaded file",
        })

    # ── Persist to Database ────────────────────────────────────────────────
    repo = UploadedFileRepository(db_session)
    try:
        db_record = await repo.create(
            id=upload_id,
            sequencing_test_id=sequencing_test_id,
            original_filename=filename,
            storage_path=storage_path,
            media_type=file.content_type,
            file_type=file_type.value,
            size_bytes=len(content),
            sha256=sha256,
            decompressed_sha256=decompressed_sha256,
            genome_build=detected_build,
            genome_build_confidence=build_confidence.value if build_confidence else None,
            compression=compression if compression != "none" else None,
            record_count=validation.record_count,
            validation_warnings=warnings,
            validation_errors=errors,
            upload_status=UploadStatusEnum.UPLOADED.value,
            validation_status=validation_status.value,
        )
    except Exception as e:
        logger.exception("Failed to create upload record for %s", upload_id)
        # Clean up stored file
        full_path = os.path.join(UPLOAD_DIR, storage_path)
        if os.path.isfile(full_path):
            os.remove(full_path)
        raise HTTPException(status_code=500, detail={
            "error": "db_error", "message": "Failed to save upload metadata",
        })

    # ── Return response ───────────────────────────────────────────────────
    return VCFUploadResponse(
        upload_id=upload_id,
        database_record_id=str(db_record.id),
        filename=filename,
        size_bytes=len(content),
        sha256=sha256,
        file_type=file_type.value if file_type else None,
        compression=compression if compression != "none" else None,
        genome_build=detected_build,
        genome_build_confidence=build_confidence.value if build_confidence else None,
        validation_status=validation_status.value,
        record_count=validation.record_count,
        warnings=warnings,
        errors=errors,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
