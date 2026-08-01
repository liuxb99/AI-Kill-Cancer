import { useState, type ReactNode } from 'react'

export type DualMode = 'recent' | 'advanced'

interface Props {
  title: string
  description?: string
  recentContent: ReactNode
  advancedLabel: string
  advancedPlaceholder: string
  advancedValue: string
  onAdvancedValueChange: (value: string) => void
  onAdvancedSubmit: () => void | Promise<void>
  advancedDisabled?: boolean
  advancedLoading?: boolean
  advancedHelp?: string
}

/**
 * Shared interaction contract for all database-backed pages.
 *
 * Default mode lists the latest 100 persisted records. Advanced mode allows
 * an exact identifier or keyword query against the full database. Both modes
 * must feed the same selected/result state in the parent page.
 */
export default function DualModeSelector({
  title,
  description,
  recentContent,
  advancedLabel,
  advancedPlaceholder,
  advancedValue,
  onAdvancedValueChange,
  onAdvancedSubmit,
  advancedDisabled = false,
  advancedLoading = false,
  advancedHelp,
}: Props) {
  const [mode, setMode] = useState<DualMode>('recent')

  return (
    <section className="overflow-hidden rounded-xl border bg-white shadow-sm">
      <div className="border-b bg-slate-50 p-4">
        <h2 className="font-bold text-slate-900">{title}</h2>
        {description && <p className="mt-1 text-sm text-slate-600">{description}</p>}
        <div className="mt-3 inline-flex rounded-lg border bg-white p-1 text-sm">
          <button
            type="button"
            className={`rounded-md px-3 py-1.5 font-semibold ${mode === 'recent' ? 'bg-indigo-600 text-white' : 'text-slate-600'}`}
            onClick={() => setMode('recent')}
          >
            最近 100 筆
          </button>
          <button
            type="button"
            className={`rounded-md px-3 py-1.5 font-semibold ${mode === 'advanced' ? 'bg-indigo-600 text-white' : 'text-slate-600'}`}
            onClick={() => setMode('advanced')}
          >
            進階精準查詢
          </button>
        </div>
      </div>

      {mode === 'recent' ? (
        <div>{recentContent}</div>
      ) : (
        <form
          className="p-4"
          onSubmit={(event) => {
            event.preventDefault()
            void onAdvancedSubmit()
          }}
        >
          <label className="block text-sm font-medium text-slate-700">
            {advancedLabel}
            <div className="mt-2 flex flex-col gap-2 sm:flex-row">
              <input
                className="min-w-0 flex-1 rounded-lg border px-3 py-2"
                value={advancedValue}
                placeholder={advancedPlaceholder}
                onChange={(event) => onAdvancedValueChange(event.target.value)}
              />
              <button
                type="submit"
                className="rounded-lg bg-indigo-600 px-5 py-2 font-semibold text-white disabled:bg-slate-300"
                disabled={advancedDisabled || advancedLoading || !advancedValue.trim()}
              >
                {advancedLoading ? '查詢中…' : '精準查詢'}
              </button>
            </div>
          </label>
          {advancedHelp && <p className="mt-2 text-xs leading-5 text-slate-500">{advancedHelp}</p>}
        </form>
      )}
    </section>
  )
}
