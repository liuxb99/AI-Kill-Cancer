import '@testing-library/jest-dom'
import { fireEvent, render, screen } from '@testing-library/react'
import { vi } from 'vitest'

import DualModeSelector from '../components/DualModeSelector'

describe('DualModeSelector', () => {
  it('defaults to latest 100 records and exposes advanced exact query', () => {
    const submit = vi.fn()
    const change = vi.fn()
    render(
      <DualModeSelector
        title="選擇病例"
        recentContent={<div>TCGA-RECENT-001</div>}
        advancedLabel="完整 Case ID"
        advancedPlaceholder="TCGA-XX-YYYY"
        advancedValue=""
        onAdvancedValueChange={change}
        onAdvancedSubmit={submit}
      />,
    )

    expect(screen.getByText('TCGA-RECENT-001')).toBeInTheDocument()
    expect(screen.queryByPlaceholderText('TCGA-XX-YYYY')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '進階精準查詢' }))
    const input = screen.getByPlaceholderText('TCGA-XX-YYYY')
    fireEvent.change(input, { target: { value: 'TCGA-EXACT-001' } })
    expect(change).toHaveBeenCalledWith('TCGA-EXACT-001')
  })
})
