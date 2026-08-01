import '@testing-library/jest-dom'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import PTCProtein3D from '../components/PTCProtein3D'

const select = vi.fn().mockResolvedValue(undefined)
const highlight = vi.fn().mockResolvedValue(undefined)
const clearHighlight = vi.fn().mockResolvedValue(undefined)
const clearSelection = vi.fn().mockResolvedValue(undefined)
const reset = vi.fn().mockResolvedValue(undefined)
const renderViewer = vi.fn().mockResolvedValue(undefined)
const clear = vi.fn().mockResolvedValue(undefined)

class FakeMolstarPlugin {
  visual = { select, highlight, clearHighlight, clearSelection, reset }
  render = renderViewer
  clear = clear
}

const structure = {
  gene: 'BRAF',
  name: 'B-Raf proto-oncogene kinase',
  uniprot: 'P15056',
  alphafold_entry_id: 'AF-P15056-F1',
  alphafold_entry_url: 'https://alphafold.ebi.ac.uk/entry/P15056',
  cif_url: 'https://alphafold.ebi.ac.uk/files/AF-P15056-F1-model_v4.cif',
  experimental_pdb_ids: ['1UWH'],
  default_pdb_id: '1UWH',
  source: 'test',
  disclaimer: 'test',
}

beforeEach(() => {
  vi.clearAllMocks()
  window.PDBeMolstarPlugin = FakeMolstarPlugin as any
})

describe('PTCProtein3D', () => {
  it('automatically selects and focuses the case mutation residue', async () => {
    render(
      <PTCProtein3D
        structure={structure}
        variants={[{ variant_id: 'braf-v600e', gene: 'BRAF', protein_change: 'p.V600E' }]}
      />,
    )

    await waitFor(() => expect(renderViewer).toHaveBeenCalled())
    await waitFor(() => {
      expect(select).toHaveBeenCalledWith(expect.objectContaining({
        data: expect.arrayContaining([
          expect.objectContaining({ residue_number: 600, focus: true, representation: 'ball-and-stick' }),
        ]),
      }))
    })
    expect(screen.getByRole('button', { name: /p\.V600E · residue 600 · 聚焦/ })).toBeEnabled()
  })

  it('highlights a mutation residue when the user clicks its focus button', async () => {
    render(
      <PTCProtein3D
        structure={structure}
        variants={[{ variant_id: 'braf-v600e', gene: 'BRAF', protein_change: 'p.V600E' }]}
      />,
    )

    const focusButton = await screen.findByRole('button', { name: /p\.V600E · residue 600 · 聚焦/ })
    await waitFor(() => expect(focusButton).toBeEnabled())
    fireEvent.click(focusButton)

    await waitFor(() => {
      expect(highlight).toHaveBeenCalledWith({
        data: [{ residue_number: 600 }],
        color: '#fde047',
        focus: true,
      })
    })
  })
})
