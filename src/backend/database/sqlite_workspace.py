from __future__ import annotations

import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class SQLiteIntegrityResult:
    ok: bool
    message: str


def _path(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


def check_sqlite_integrity(database_path: str | Path) -> SQLiteIntegrityResult:
    """Run SQLite's own integrity gate against a persistent local workspace."""
    path = _path(database_path)
    if not path.is_file():
        return SQLiteIntegrityResult(False, f"database does not exist: {path}")
    with sqlite3.connect(path) as connection:
        row = connection.execute("PRAGMA integrity_check").fetchone()
    message = str(row[0]) if row else "no integrity result"
    return SQLiteIntegrityResult(message.lower() == "ok", message)


def backup_sqlite_database(database_path: str | Path, backup_dir: str | Path | None = None) -> Path:
    """Create a timestamped, integrity-checked snapshot before an upgrade/change."""
    source = _path(database_path)
    result = check_sqlite_integrity(source)
    if not result.ok:
        raise RuntimeError(f"Refusing to back up invalid SQLite database: {result.message}")
    target_dir = _path(backup_dir) if backup_dir else source.parent / "backups"
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = target_dir / f"{source.stem}-{stamp}{source.suffix or '.db'}"
    with sqlite3.connect(source) as src, sqlite3.connect(target) as dst:
        src.backup(dst)
    if not check_sqlite_integrity(target).ok:
        target.unlink(missing_ok=True)
        raise RuntimeError("SQLite backup failed integrity verification")
    return target


def restore_sqlite_database(backup_path: str | Path, database_path: str | Path) -> Path:
    """Restore an integrity-checked backup using an atomic replacement file."""
    backup = _path(backup_path)
    target = _path(database_path)
    result = check_sqlite_integrity(backup)
    if not result.ok:
        raise RuntimeError(f"Refusing to restore invalid SQLite backup: {result.message}")
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.with_suffix(f"{target.suffix}.restore")
    shutil.copy2(backup, staging)
    if not check_sqlite_integrity(staging).ok:
        staging.unlink(missing_ok=True)
        raise RuntimeError("Restored SQLite staging file failed integrity verification")
    staging.replace(target)
    return target
