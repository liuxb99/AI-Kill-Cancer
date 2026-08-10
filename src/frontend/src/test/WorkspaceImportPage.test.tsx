import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  getWorkspaceStatus: vi.fn(),
  previewWorkspaceImport: vi.fn(),
  commitWorkspaceImport: vi.fn(),
  getWorkspaceImportHistory: vi.fn(),
}))

vi.mock('../api/workspace', () => mocks)

import WorkspaceImportPage from '../pages/WorkspaceImportPage'

const localStatus = {
  app_mode: 'local',
  backend: 'sqlite',
  local_first: true,
  persistent: true,
  database_path: 'D:/research/workspace.db',
  exists: true,
}

const preview = {
  source_dir: 'D:/research/ptc-dataset',
  validation: { ok: true, errors: [] },
  counts: { patients: 3, cancer_cases: 3, specimens: 3, sequencing_tests: 3, variants: 3 },
  import_scope: ['patients', 'cancer_cases', 'specimens', 'sequencing_tests', 'variants'],
  duplicates: {
    patients: { total: 3, existing: 1, new: 2, existing_keys: ['PTC-PATIENT-001'], new_keys: ['PTC-PATIENT-002', 'PTC-PATIENT-003'] },
    variants: { total: 3, existing: 0, new: 3, existing_keys: [], new_keys: ['VAR-DEMO-001', 'VAR-DEMO-002', 'VAR-DEMO-003'] },
  },
  overwrite_existing: false,
  requires_confirmation: true,
  confirmation_token: 'IMPORT',
}

beforeEach(() => {
  vi.clearAllMocks()
  mocks.getWorkspaceStatus.mockResolvedValue(localStatus)
  mocks.getWorkspaceImportHistory.mockResolvedValue({ items: [], history_path: 'D:/research/import-history.jsonl' })
  mocks.previewWorkspaceImport.mockResolvedValue(preview)
  mocks.commitWorkspaceImport.mockResolvedValue({
    ok: true,
    source_dir: preview.source_dir,
    imported: { patients: 2, cases: 3, specimens: 3, sequencing_tests: 3, variants: 3 },
    duplicates: preview.duplicates,
    overwrite_existing: false,
    history_path: 'D:/research/import-history.jsonl',
    message: 'Import completed.',
  })
})

describe('WorkspaceImportPage', () => {
  it('blocks writes outside persistent local/research SQLite', async () => {
    mocks.getWorkspaceStatus.mockResolvedValue({ ...localStatus, app_mode: 'demo', persistent: false })
    render(<WorkspaceImportPage />)
    expect(await screen.findByTestId('workspace-import-guard')).toBeInTheDocument()
    expect(screen.queryByText('Validate / Preview')).not.toBeInTheDocument()
    expect(mocks.getWorkspaceImportHistory).not.toHaveBeenCalled()
  })

  it('previews duplicates before explicit import and refreshes history', async () => {
    render(<WorkspaceImportPage />)
    expect(await screen.findByText('Workspace CSV 匯入')).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('CSV Dataset 目錄'), { target: { value: 'D:/research/ptc-dataset' } })
    fireEvent.click(screen.getByText('Validate / Preview'))

    expect(await screen.findByTestId('import-preview')).toBeInTheDocument()
    expect(screen.getByText('Validation PASS')).toBeInTheDocument()
    expect(screen.getByText('Existing / Skip')).toBeInTheDocument()
    expect(screen.getByText('New / Import')).toBeInTheDocument()
    expect(mocks.previewWorkspaceImport).toHaveBeenCalledWith('D:/research/ptc-dataset')

    fireEvent.click(screen.getByTestId('confirm-import'))
    expect(await screen.findByTestId('import-result')).toBeInTheDocument()
    expect(mocks.commitWorkspaceImport).toHaveBeenCalledWith('D:/research/ptc-dataset')
    await waitFor(() => expect(mocks.getWorkspaceImportHistory).toHaveBeenCalledTimes(2))
  })
})
