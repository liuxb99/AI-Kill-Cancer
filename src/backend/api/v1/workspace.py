from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.backend.config import settings
from src.backend.database import session as db_session
from src.backend.database.sqlite_workspace import check_sqlite_integrity
from src.backend.demo import bootstrap_demo_dataset
from src.backend.demo.validator import validate_demo_dataset

router = APIRouter(prefix="/workspace", tags=["workspace"])


class LocalCsvImportRequest(BaseModel):
    source_dir: str
    confirm: str | None = None


def _require_local_sqlite() -> None:
    if settings.DB_BACKEND != "sqlite" or settings.APP_MODE not in {"local", "research"}:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "local_csv_import_not_available",
                "message": "CSV import is only available for persistent local/research SQLite workspaces.",
                "backend": settings.DB_BACKEND,
                "app_mode": settings.APP_MODE,
            },
        )


def _resolve_import_dir(raw: str) -> Path:
    path = Path(raw).expanduser().resolve()
    if not path.is_dir():
        raise HTTPException(status_code=400, detail={"error": "source_dir_not_found", "source_dir": str(path)})
    return path


def _preview_payload(path: Path) -> dict[str, object]:
    validation = validate_demo_dataset(path)
    return {
        "source_dir": str(path),
        "validation": {"ok": validation.ok, "errors": validation.errors},
        "counts": validation.counts,
        "import_scope": ["patients", "cancer_cases", "specimens", "sequencing_tests", "variants"],
        "overwrite_existing": False,
        "requires_confirmation": True,
        "confirmation_token": "IMPORT",
    }


@router.get("/status")
async def workspace_status():
    backend = settings.DB_BACKEND
    payload = {
        "app_mode": settings.APP_MODE,
        "backend": backend,
        "local_first": backend == "sqlite",
        "persistent": backend == "sqlite" and settings.APP_MODE in {"local", "research"},
    }
    if backend != "sqlite":
        return payload | {"database_path": None, "exists": None, "integrity": None}

    path = Path(settings.SQLITE_PATH).expanduser().resolve()
    exists = path.is_file()
    integrity = check_sqlite_integrity(path) if exists else None
    return payload | {
        "database_path": str(path),
        "exists": exists,
        "size_bytes": path.stat().st_size if exists else 0,
        "integrity": None if integrity is None else {"ok": integrity.ok, "message": integrity.message},
        "backup_directory": str((path.parent / "backups").resolve()),
    }


@router.post("/import/csv/preview")
async def preview_local_csv_import(request: LocalCsvImportRequest):
    _require_local_sqlite()
    path = _resolve_import_dir(request.source_dir)
    return _preview_payload(path)


@router.post("/import/csv/commit")
async def commit_local_csv_import(request: LocalCsvImportRequest):
    _require_local_sqlite()
    path = _resolve_import_dir(request.source_dir)
    preview = _preview_payload(path)
    validation = preview["validation"]
    if not isinstance(validation, dict) or not validation.get("ok"):
        raise HTTPException(status_code=422, detail={"error": "dataset_validation_failed", **preview})
    if request.confirm != "IMPORT":
        raise HTTPException(
            status_code=409,
            detail={
                "error": "explicit_confirmation_required",
                "message": "Run preview first, then retry with confirm=IMPORT.",
                **preview,
            },
        )

    await db_session.ensure_db_initialized()
    if db_session.async_session_factory is None:
        raise HTTPException(status_code=503, detail={"error": "database_not_initialized"})

    imported = await bootstrap_demo_dataset(db_session.async_session_factory, path)
    return {
        "ok": True,
        "source_dir": str(path),
        "imported": imported,
        "overwrite_existing": False,
        "message": "Import completed. Existing deterministic records were preserved and not overwritten.",
    }
