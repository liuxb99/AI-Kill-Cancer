from pathlib import Path

import pytest
from fastapi import HTTPException

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


@pytest.mark.asyncio
async def test_csv_import_preview_requires_local_persistent_sqlite(monkeypatch):
    monkeypatch.setattr(workspace.settings, 'DB_BACKEND', 'sqlite')
    monkeypatch.setattr(workspace.settings, 'APP_MODE', 'demo')

    with pytest.raises(HTTPException) as exc:
        await workspace.preview_local_csv_import(workspace.LocalCsvImportRequest(source_dir='data/demo'))

    assert exc.value.status_code == 409
    assert exc.value.detail['error'] == 'local_csv_import_not_available'


@pytest.mark.asyncio
async def test_csv_import_preview_validates_without_writing(monkeypatch):
    monkeypatch.setattr(workspace.settings, 'DB_BACKEND', 'sqlite')
    monkeypatch.setattr(workspace.settings, 'APP_MODE', 'local')

    payload = await workspace.preview_local_csv_import(workspace.LocalCsvImportRequest(source_dir='data/demo'))

    assert payload['validation']['ok'] is True
    assert payload['requires_confirmation'] is True
    assert payload['confirmation_token'] == 'IMPORT'
    assert payload['overwrite_existing'] is False
    assert payload['import_scope'] == ['patients', 'cancer_cases', 'specimens', 'sequencing_tests', 'variants']


@pytest.mark.asyncio
async def test_csv_import_commit_requires_explicit_confirmation(monkeypatch):
    monkeypatch.setattr(workspace.settings, 'DB_BACKEND', 'sqlite')
    monkeypatch.setattr(workspace.settings, 'APP_MODE', 'research')

    with pytest.raises(HTTPException) as exc:
        await workspace.commit_local_csv_import(workspace.LocalCsvImportRequest(source_dir='data/demo'))

    assert exc.value.status_code == 409
    assert exc.value.detail['error'] == 'explicit_confirmation_required'


@pytest.mark.asyncio
async def test_csv_import_commit_calls_idempotent_bootstrap(monkeypatch):
    monkeypatch.setattr(workspace.settings, 'DB_BACKEND', 'sqlite')
    monkeypatch.setattr(workspace.settings, 'APP_MODE', 'local')
    fake_factory = object()
    monkeypatch.setattr(workspace.db_session, 'async_session_factory', fake_factory)

    async def fake_ensure():
        return None

    calls = []

    async def fake_bootstrap(factory, path):
        calls.append((factory, Path(path)))
        return {'patients': 3, 'cases': 3, 'specimens': 3, 'sequencing_tests': 3, 'variants': 3}

    monkeypatch.setattr(workspace.db_session, 'ensure_db_initialized', fake_ensure)
    monkeypatch.setattr(workspace, 'bootstrap_demo_dataset', fake_bootstrap)

    payload = await workspace.commit_local_csv_import(
        workspace.LocalCsvImportRequest(source_dir='data/demo', confirm='IMPORT')
    )

    assert payload['ok'] is True
    assert payload['overwrite_existing'] is False
    assert payload['imported']['variants'] == 3
    assert calls and calls[0][0] is fake_factory
