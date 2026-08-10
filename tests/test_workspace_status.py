from pathlib import Path

import pytest

from src.backend.api.v1 import workspace


@pytest.mark.asyncio
async def test_workspace_status_reports_persistent_local_sqlite(tmp_path, monkeypatch):
    db_path = tmp_path / 'workspace.db'
    db_path.write_bytes(b'sqlite-fixture')

    monkeypatch.setattr(workspace.settings, 'DB_BACKEND', 'sqlite')
    monkeypatch.setattr(workspace.settings, 'APP_MODE', 'local')
    monkeypatch.setattr(workspace.settings, 'SQLITE_PATH', str(db_path))
    monkeypatch.setattr(
        workspace,
        'check_sqlite_integrity',
        lambda path: type('Integrity', (), {'ok': True, 'message': 'ok'})(),
    )

    payload = await workspace.workspace_status()

    assert payload['backend'] == 'sqlite'
    assert payload['local_first'] is True
    assert payload['persistent'] is True
    assert payload['database_path'] == str(db_path.resolve())
    assert payload['exists'] is True
    assert payload['size_bytes'] == len(b'sqlite-fixture')
    assert payload['integrity'] == {'ok': True, 'message': 'ok'}
    assert payload['backup_directory'] == str((tmp_path / 'backups').resolve())


@pytest.mark.asyncio
async def test_workspace_status_marks_demo_sqlite_ephemeral(tmp_path, monkeypatch):
    db_path = tmp_path / 'demo.db'

    monkeypatch.setattr(workspace.settings, 'DB_BACKEND', 'sqlite')
    monkeypatch.setattr(workspace.settings, 'APP_MODE', 'demo')
    monkeypatch.setattr(workspace.settings, 'SQLITE_PATH', str(db_path))

    payload = await workspace.workspace_status()

    assert payload['local_first'] is True
    assert payload['persistent'] is False
    assert payload['exists'] is False
    assert payload['size_bytes'] == 0
    assert payload['integrity'] is None


@pytest.mark.asyncio
async def test_workspace_status_handles_non_sqlite_backend(monkeypatch):
    monkeypatch.setattr(workspace.settings, 'DB_BACKEND', 'postgresql')
    monkeypatch.setattr(workspace.settings, 'APP_MODE', 'research')

    payload = await workspace.workspace_status()

    assert payload == {
        'app_mode': 'research',
        'backend': 'postgresql',
        'local_first': False,
        'persistent': False,
        'database_path': None,
        'exists': None,
        'integrity': None,
    }
