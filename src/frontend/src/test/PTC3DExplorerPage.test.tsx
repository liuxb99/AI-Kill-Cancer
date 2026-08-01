import '@testing-library/jest-dom'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { vi } from 'vitest'

import PTC3DExplorerPage from '../pages/PTC3DExplorerPage'

vi.mock('../components/PTCCell3D', () => ({
  default: ({ selectedCase, onSelectGene }: any) => (
    <div>
      <span>cell-view:{selectedCase?.case_id || 'none'}</span>
      <button onClick={() => onSelectGene('BRAF')}>cell-braf</button>
    </div>
  ),
}))

vi.mock('../components/PTCProtein3D', () => ({
  default: ({ structure }: any) => <div>protein-view:{structure?.gene || 'none'}</div>,
}))

vi.mock('../api/ptcVisualization', () => ({
  getLatestPTCCases: vi.fn().mockResolvedValue({
    count: 2,
    limit: 100,
    cases: [
      {
        case_id: 'TCGA-NEW-001',
        source_dataset: 'TCGA-THCA',
        source_project: 'TCGA-THCA',
        disease: 'papillary_thyroid_carcinoma',
        updated_at: '2026-08-01T02:00:00',
        pathologic_stage: 'Stage I',
        vital_status: 'Alive',
        variants: [{ variant_id: 'v1', gene: 'BRAF', protein_change: 'p.V600E' }],
        outcomes: [],
      },
      {
        case_id: 'TCGA-OLD-001',
        source_dataset: 'TCGA-THCA',
        source_project: 'TCGA-THCA',
        disease: 'papillary_thyroid_carcinoma',
        updated_at: '2026-07-31T02:00:00',
        pathologic_stage: 'Stage II',
        vital_status: 'Alive',
        variants: [{ variant_id: 'v2', gene: 'RET' }],
        outcomes: [],
      },
    ],
  }),
  getPTCProteinStructure: vi.fn().mockImplementation(async (gene: string) => ({
    gene,
    name: `${gene} protein`,
    uniprot: 'P15056',
    alphafold_entry_id: 'AF-P15056-F1',
    alphafold_entry_url: 'https://alphafold.example/BRAF',
    cif_url: 'https://alphafold.example/BRAF.cif',
    experimental_pdb_ids: ['1UWH'],
    default_pdb_id: '1UWH',
    source: 'test',
    disclaimer: 'test',
  })),
}))

describe('PTC3DExplorerPage', () => {
  it('lists latest cases and switches the selected case', async () => {
    render(<PTC3DExplorerPage />)
    expect(await screen.findByText(/TCGA-NEW-001/)).toBeInTheDocument()
    expect(screen.getByText(/TCGA-OLD-001/)).toBeInTheDocument()
    expect(screen.getByText('cell-view:TCGA-NEW-001')).toBeInTheDocument()

    fireEvent.click(screen.getByText(/TCGA-OLD-001/))
    expect(screen.getByText('cell-view:TCGA-OLD-001')).toBeInTheDocument()
  })

  it('opens protein structure from a case gene', async () => {
    render(<PTC3DExplorerPage />)
    fireEvent.click(await screen.findByRole('button', { name: 'BRAF 结构' }))

    await waitFor(() => {
      expect(screen.getByText('protein-view:BRAF')).toBeInTheDocument()
    })
  })

  it('opens protein structure from a cell mutation beacon', async () => {
    render(<PTC3DExplorerPage />)
    fireEvent.click(await screen.findByText('cell-braf'))

    await waitFor(() => {
      expect(screen.getByText('protein-view:BRAF')).toBeInTheDocument()
    })
  })
})
