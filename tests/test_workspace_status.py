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
    assert payload['import_history_path'] == str((tmp_path / 'import-history.jsonl').resolve())


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
async def test_csv_import_preview_validates_and_reports_duplicates(monkeypatch):
    monkeypatch.setattr(workspace.settings, 'DB_BACKEND', 'sqlite')
    monkeypatch.setattr(workspace.settings, 'APP_MODE', 'local')
    fake_factory = object()
    monkeypatch.setattr(workspace.db_session, 'async_session_factory', fake_factory)

    async def fake_ensure():
        return None

    async def fake_duplicates(factory, path):
        assert factory is fake_factory
        assert Path(path).name == 'demo'
        return {
            'patients': {'total': 3, 'existing': 1, 'new': 2, 'existing_keys': ['PTC-PATIENT-001'], 'new_keys': ['PTC-PATIENT-002', 'PTC-PATIENT-003']},
        }

    monkeypatch.setattr(workspace.db_session, 'ensure_db_initialized', fake_ensure)
    monkeypatch.setattr(workspace, 'preview_demo_dataset_duplicates', fake_duplicates)

    payload = await workspace.preview_local_csv_import(workspace.LocalCsvImportRequest(source_dir='data/demo'))

    assert payload['validation']['ok'] is True
    assert payload['requires_confirmation'] is True
    assert payload['confirmation_token'] == 'IMPORT'
    assert payload['overwrite_existing'] is False
    assert payload['import_scope'] == ['patients', 'cancer_cases', 'specimens', 'sequencing_tests', 'variants']
    assert payload['duplicates']['patients']['existing'] == 1
    assert payload['duplicates']['patients']['new'] == 2


@pytest.mark.asyncio
async def test_csv_import_commit_requires_explicit_confirmation(monkeypatch):
    monkeypatch.setattr(workspace.settings, 'DB_BACKEND', 'sqlite')
    monkeypatch.setattr(workspace.settings, 'APP_MODE', 'research')
    fake_factory = object()
    monkeypatch.setattr(workspace.db_session, 'async_session_factory', fake_factory)

    async def fake_ensure():
        return None

    async def fake_duplicates(factory, path):
        return {}

    monkeypatch.setattr(workspace.db_session, 'ensure_db_initialized', fake_ensure)
    monkeypatch.setattr(workspace, 'preview_demo_dataset_duplicates', fake_duplicates)

    with pytest.raises(HTTPException) as exc:
        await workspace.commit_local_csv_import(workspace.LocalCsvImportRequest(source_dir='data/demo'))

    assert exc.value.status_code == 409
    assert exc.value.detail['error'] == 'explicit_confirmation_required'


@pytest.mark.asyncio
async def test_csv_import_commit_calls_idempotent_bootstrap_and_records_history(tmp_path, monkeypatch):
    db_path = tmp_path / 'workspace.db'
    monkeypatch.setattr(workspace.settings, 'DB_BACKEND', 'sqlite')
    monkeypatch.setattr(workspace.settings, 'APP_MODE', 'local')
    monkeypatch.setattr(workspace.settings, 'SQLITE_PATH', str(db_path))
    fake_factory = object()
    monkeypatch.setattr(workspace.db_session, 'async_session_factory', fake_factory)

    async def fake_ensure():
        return None

    async def fake_duplicates(factory, path):
        return {'variants': {'total': 3, 'existing': 2, 'new': 1, 'existing_keys': ['A', 'B'], 'new_keys': ['C']}}

    calls = []

    async def fake_bootstrap(factory, path):
        calls.append((factory, Path(path)))
        return {'patients': 0, 'cases': 0, 'specimens': 0, 'sequencing_tests': 0, 'variants': 1}

    monkeypatch.setattr(workspace.db_session, 'ensure_db_initialized', fake_ensure)
    monkeypatch.setattr(workspace, 'preview_demo_dataset_duplicates', fake_duplicates)
    monkeypatch.setattr(workspace, 'bootstrap_demo_dataset', fake_bootstrap)

    payload = await workspace.commit_local_csv_import(
        workspace.LocalCsvImportRequest(source_dir='data/demo', confirm='IMPORT')
    )

    assert payload['ok'] is True
    assert payload['overwrite_existing'] is False
    assert payload['imported']['variants'] == 1
    assert payload['duplicates']['variants']['existing'] == 2
    assert calls and calls[0][0] is fake_factory
    assert Path(payload['history_path']).is_file()

    history = await workspace.local_csv_import_history()
    assert len(history['items']) == 1
    assert history['items'][0]['imported']['variants'] == 1
    assert history['items'][0]['duplicates']['variants']['new'] == 1
    assert history['items'][0]['overwrite_existing'] is False


def test_import_history_reader_skips_malformed_lines_and_limits(tmp_path, monkeypatch):
    db_path = tmp_path / 'workspace.db'
    monkeypatch.setattr(workspace.settings, 'SQLITE_PATH', str(db_path))
    history_path = tmp_path / 'import-history.jsonl'
    history_path.write_text(
        '{"timestamp":"1","imported":{"variants":1}}\nnot-json\n{"timestamp":"2","imported":{"variants":2}}\n',
        encoding='utf-8',
    )

    rows = workspace._read_import_history(limit=1)
    assert len(rows) == 1
    assert rows[0]['timestamp'] == '2'
