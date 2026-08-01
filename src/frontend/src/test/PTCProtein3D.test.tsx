import '@testing-library/jest-dom'
import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import PTCProtein3D, { parsePdb } from '../components/PTCProtein3D'

vi.mock('../components/threeRuntime', () => ({
  loadThree: vi.fn(() => new Promise(() => undefined)),
}))

const structure = {
  gene: 'BRAF',
  name: 'B-Raf proto-oncogene kinase',
  uniprot: 'P15056',
  alphafold_entry_id: 'AF-P15056-F1',
  alphafold_entry_url: 'https://alphafold.com/entry/AF-P15056-F1',
  cif_url: 'https://alphafold.ebi.ac.uk/files/AF-P15056-F1-model_v6.cif',
  cif_urls: [
    'https://alphafold.ebi.ac.uk/files/AF-P15056-F1-model_v6.cif',
    'https://alphafold.ebi.ac.uk/files/AF-P15056-F1-model_v4.cif',
  ],
  pdb_url: 'https://alphafold.ebi.ac.uk/files/AF-P15056-F1-model_v6.pdb',
  pdb_urls: [
    'https://alphafold.ebi.ac.uk/files/AF-P15056-F1-model_v6.pdb',
    'https://alphafold.ebi.ac.uk/files/AF-P15056-F1-model_v4.pdb',
  ],
  experimental_structures: [
    {
      pdb_id: '1UWH',
      pdb_url: 'https://files.rcsb.org/download/1UWH.pdb',
      entry_url: 'https://www.ebi.ac.uk/pdbe/entry/pdb/1uwh',
    },
  ],
  experimental_pdb_ids: ['1UWH'],
  default_pdb_id: '1UWH',
  renderer: 'builtin-threejs-pdb' as const,
  uses_alphafold_api: false as const,
  source: 'static files rendered internally',
  disclaimer: 'test',
}

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn(() => new Promise(() => undefined)))
})

describe('PTCProtein3D built-in renderer', () => {
  it('parses PDB atom coordinates with internal code', () => {
    const pdb = [
      'ATOM      1  N   VAL A 600      10.000  11.000  12.000  1.00 95.00           N  ',
      'ATOM      2  CA  VAL A 600      11.000  12.000  13.000  1.00 95.00           C  ',
    ].join('\n')

    const atoms = parsePdb(pdb)
    expect(atoms).toHaveLength(2)
    expect(atoms[1]).toEqual(expect.objectContaining({ atomName: 'CA', residue: 600, element: 'C', confidence: 95 }))
  })

  it('shows the internal renderer and case mutation residue without Molstar', () => {
    render(
      <PTCProtein3D
        structure={structure}
        variants={[{ variant_id: 'braf-v600e', gene: 'BRAF', protein_change: 'p.V600E' }]}
      />,
    )

    expect(screen.getByText(/内建 Three\.js PDB Renderer/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /p\.V600E · residue 600 · 聚焦/ })).toBeDisabled()
    expect(screen.getByText(/不调用 AlphaFold API，不加载 Mol\*/)).toBeInTheDocument()
    expect((window as any).PDBeMolstarPlugin).toBeUndefined()
  })

  it('starts with deterministic AlphaFold v6 and exposes experimental PDB', () => {
    render(<PTCProtein3D structure={structure} variants={[]} />)

    expect(fetch).toHaveBeenCalledWith(
      'https://alphafold.ebi.ac.uk/files/AF-P15056-F1-model_v6.pdb',
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    )

    fireEvent.click(screen.getByRole('button', { name: 'PDB 1UWH' }))
    expect(screen.getByRole('button', { name: 'PDB 1UWH' })).toHaveClass('bg-cyan-400')
  })
})
