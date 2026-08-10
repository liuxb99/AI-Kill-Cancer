from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

from src.backend.config import settings
from src.backend.database.sqlite_workspace import check_sqlite_integrity

router = APIRouter(prefix="/workspace", tags=["workspace"])


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
