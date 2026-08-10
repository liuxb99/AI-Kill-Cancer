from __future__ import annotations

import sqlite3

import pytest

from src.backend.database.sqlite_workspace import (
    backup_sqlite_database,
    check_sqlite_integrity,
    restore_sqlite_database,
)


def test_integrity_backup_restore_and_restart_persistence(tmp_path):
    database = tmp_path / "workspace.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE research_notes (id INTEGER PRIMARY KEY, note TEXT NOT NULL)")
        connection.execute("INSERT INTO research_notes(note) VALUES (?)", ("persistent-local-research",))
        connection.commit()

    assert check_sqlite_integrity(database).ok is True
    backup = backup_sqlite_database(database)
    assert backup.is_file()
    assert check_sqlite_integrity(backup).ok is True

    # Simulate continued work after the backup, then a process restart.
    with sqlite3.connect(database) as connection:
        connection.execute("INSERT INTO research_notes(note) VALUES (?)", ("post-backup-change",))
        connection.commit()
    with sqlite3.connect(database) as restarted:
        assert restarted.execute("SELECT COUNT(*) FROM research_notes").fetchone()[0] == 2

    restore_sqlite_database(backup, database)
    with sqlite3.connect(database) as restored:
        rows = restored.execute("SELECT note FROM research_notes ORDER BY id").fetchall()
    assert rows == [("persistent-local-research",)]
    assert check_sqlite_integrity(database).ok is True


def test_missing_database_fails_integrity_gate(tmp_path):
    result = check_sqlite_integrity(tmp_path / "missing.db")
    assert result.ok is False
    assert "does not exist" in result.message


def test_restore_rejects_invalid_backup(tmp_path):
    invalid = tmp_path / "broken.db"
    invalid.write_bytes(b"not a sqlite database")
    with pytest.raises((RuntimeError, sqlite3.DatabaseError)):
        restore_sqlite_database(invalid, tmp_path / "workspace.db")
