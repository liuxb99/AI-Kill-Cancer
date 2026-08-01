import '@testing-library/jest-dom'
import { render, screen } from '@testing-library/react'
import { vi } from 'vitest'

import PTCLiteratureAssetsPanel from '../components/PTCLiteratureAssetsPanel'

vi.mock('../api/ptcLiterature', () => ({
  getPTCPublications: vi.fn().mockResolvedValue({
    count: 1,
    publications: [{
      pmid: '12345678',
      pmcid: 'PMC9999999',
      title: 'BRAF V600E in papillary thyroid carcinoma',
      abstract: 'BRAF activates MAPK signaling.',
      citation: 'PTC Journal 2026',
      source_url: 'https://pubmed.ncbi.nlm.nih.gov/12345678/',
      full_text_available: true,
      full_text_url: 'https://pmc.ncbi.nlm.nih.gov/articles/PMC9999999/',
      authors: ['Ada Lovelace'],
      genes: ['BRAF'],
      figure_count: 1,
      table_count: 1,
      figures: [{
        figure_id: 'F1',
        label: 'Figure 1',
        caption: 'BRAF pathway response.',
        image_url: 'https://pmc.ncbi.nlm.nih.gov/articles/PMC9999999/bin/figure1.jpg',
      }],
      tables: [{
        table_id: 'T1',
        label: 'Table 1',
        caption: 'Observed variants.',
        headers: ['Gene', 'Variant'],
        rows: [['BRAF', 'V600E']],
        row_count: 1,
      }],
    }],
  }),
}))

describe('PTCLiteratureAssetsPanel', () => {
  it('renders PubMed and PMC figures and structured tables', async () => {
    render(<PTCLiteratureAssetsPanel gene="BRAF" />)

    expect(await screen.findByText('BRAF V600E in papillary thyroid carcinoma')).toBeInTheDocument()
    expect(screen.getByText(/Figure 1 · BRAF pathway response/)).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'BRAF pathway response.' })).toHaveAttribute('src', expect.stringContaining('figure1.jpg'))
    expect(screen.getByText(/Table 1 · Observed variants/)).toBeInTheDocument()
    expect(screen.getByText('Gene')).toBeInTheDocument()
    expect(screen.getByText('Variant')).toBeInTheDocument()
    expect(screen.getByText('V600E')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'PMC 全文' })).toHaveAttribute('href', expect.stringContaining('PMC9999999'))
  })
})
