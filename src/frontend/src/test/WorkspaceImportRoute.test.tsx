import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

vi.mock('../components/StatusBanner', () => ({ default: () => null }))
vi.mock('../api/workspace', () => ({
  getWorkspaceStatus: vi.fn().mockResolvedValue({
    app_mode: 'local',
    backend: 'sqlite',
    local_first: true,
    persistent: true,
    database_path: '/tmp/workspace.db',
    exists: true,
  }),
  getWorkspaceImportHistory: vi.fn().mockResolvedValue({ items: [], history_path: '/tmp/import-history.jsonl' }),
  previewWorkspaceImport: vi.fn(),
  commitWorkspaceImport: vi.fn(),
}))

import App from '../App'

afterEach(() => cleanup())

describe('Workspace Import route', () => {
  it('renders the local workspace import page through App routing', async () => {
    render(
      <MemoryRouter initialEntries={['/workspace-import']}>
        <App />
      </MemoryRouter>,
    )

    expect(await screen.findByText('Workspace CSV Import')).toBeInTheDocument()
    expect(screen.getByText('Workspace 匯入')).toBeInTheDocument()
  })
})
