from __future__ import annotations

import sqlite3

import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine

from src.backend.database.session import _schema_upgrade_required
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


def test_schema_upgrade_detection_for_new_table_and_column(tmp_path):
    database = tmp_path / "upgrade.db"
    engine = create_engine(f"sqlite:///{database}")
    existing = MetaData()
    Table("patients", existing, Column("id", Integer, primary_key=True))
    existing.create_all(engine)

    same = MetaData()
    Table("patients", same, Column("id", Integer, primary_key=True))
    with engine.connect() as connection:
        assert _schema_upgrade_required(connection, same) is False

    new_column = MetaData()
    Table(
        "patients",
        new_column,
        Column("id", Integer, primary_key=True),
        Column("display_name", String),
    )
    with engine.connect() as connection:
        assert _schema_upgrade_required(connection, new_column) is True

    new_table = MetaData()
    Table("patients", new_table, Column("id", Integer, primary_key=True))
    Table("variants", new_table, Column("id", Integer, primary_key=True))
    with engine.connect() as connection:
        assert _schema_upgrade_required(connection, new_table) is True

    engine.dispose()


def test_empty_database_does_not_require_preupgrade_backup(tmp_path):
    database = tmp_path / "fresh.db"
    engine = create_engine(f"sqlite:///{database}")
    metadata = MetaData()
    Table("patients", metadata, Column("id", Integer, primary_key=True))
    with engine.connect() as connection:
        assert _schema_upgrade_required(connection, metadata) is False
    engine.dispose()


def test_missing_database_fails_integrity_gate(tmp_path):
    result = check_sqlite_integrity(tmp_path / "missing.db")
    assert result.ok is False
    assert "does not exist" in result.message


def test_restore_rejects_invalid_backup(tmp_path):
    invalid = tmp_path / "broken.db"
    invalid.write_bytes(b"not a sqlite database")
    with pytest.raises((RuntimeError, sqlite3.DatabaseError)):
        restore_sqlite_database(invalid, tmp_path / "workspace.db")
