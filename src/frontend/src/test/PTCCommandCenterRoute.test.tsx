import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../pages/PTCCommandCenterPage', () => ({
  default: () => <div data-testid="real-command-center">Real Command Center</div>,
}))

import PTCCommandCenterRoute from '../pages/PTCCommandCenterRoute'

const demoCase = {
  case_key: 'PTC-DEMO-001',
  display_name: 'Synthetic BRAF Case',
  cancer_type: 'Papillary Thyroid Carcinoma',
  stage: 'Stage III',
  radioiodine_status: 'refractory',
  variant: { gene: 'BRAF', hgvs_p: 'p.Val600Glu', variant_type: 'SNV', driver_status: 'driver' },
  drug: { name: 'Demo Drug', mechanism: 'Synthetic MAPK pathway example' },
  evidence: { level: 'A', direction: 'supports', summary: 'Synthetic evidence summary', synthetic: true },
  publication: { title: 'Synthetic PTC Publication', journal: 'Demo Journal' },
  clinical_trial: { id: 'NCT-DEMO-001', title: 'Synthetic Trial', status: 'RECRUITING' },
}

function renderRoute(initialEntry: string) {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes><Route path="/ptc-command-center" element={<PTCCommandCenterRoute />} /></Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.restoreAllMocks()
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ items: [demoCase] }),
  }))
})

describe('PTCCommandCenterRoute', () => {
  it('renders isolated synthetic command center for demo_case deep links', async () => {
    renderRoute('/ptc-command-center?demo_case=PTC-DEMO-001&data_mode=synthetic')

    expect(await screen.findByTestId('demo-context-banner')).toBeInTheDocument()
    expect(screen.getByText('甲狀腺乳突癌 Demo 總控台')).toBeInTheDocument()
    expect(screen.getByText('BRAF p.Val600Glu')).toBeInTheDocument()
    expect(screen.getByText('NCT-DEMO-001')).toBeInTheDocument()
    expect(screen.getByText('外部同步与正式研究数据库操作已停用')).toBeInTheDocument()
    expect(screen.queryByTestId('real-command-center')).not.toBeInTheDocument()
    expect(fetch).toHaveBeenCalledWith('/api/v1/demo/cases')
  })

  it('mounts the existing real command center when demo context is absent', () => {
    renderRoute('/ptc-command-center')

    expect(screen.getByTestId('real-command-center')).toBeInTheDocument()
    expect(screen.queryByText('甲狀腺乳突癌 Demo 總控台')).not.toBeInTheDocument()
    expect(fetch).not.toHaveBeenCalled()
  })
})
