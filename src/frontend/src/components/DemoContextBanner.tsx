import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

export type DemoCaseContext = {
  case_key: string
  display_name?: string
  cancer_type?: string
  stage?: string
  radioiodine_status?: string
  variant: { gene?: string; hgvs_p?: string; variant_type?: string; driver_status?: string }
  drug: { name?: string; mechanism?: string }
  evidence: { level?: string; direction?: string; summary?: string; synthetic: boolean }
  publication: { title?: string; journal?: string }
  clinical_trial: { id?: string; title?: string; status?: string }
}

export function useDemoContext() {
  const [searchParams] = useSearchParams()
  const caseKey = searchParams.get('demo_case')
  const synthetic = searchParams.get('data_mode') === 'synthetic' || Boolean(caseKey)
  const [context, setContext] = useState<DemoCaseContext | null>(null)
  const [loading, setLoading] = useState(Boolean(caseKey))
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!caseKey) { setContext(null); setLoading(false); setError(null); return }
    setLoading(true)
    fetch('/api/v1/demo/cases')
      .then((response) => response.ok ? response.json() : Promise.reject(new Error('demo API failed')))
      .then((data) => {
        const item = (Array.isArray(data.items) ? data.items : []).find((candidate: DemoCaseContext) => candidate.case_key === caseKey)
        if (!item) throw new Error(`找不到 Demo Case：${caseKey}`)
        setContext(item)
        setError(null)
      })
      .catch((reason) => setError(reason instanceof Error ? reason.message : '無法載入 Demo Context'))
      .finally(() => setLoading(false))
  }, [caseKey])

  return { caseKey, synthetic, context, loading, error }
}

export default function DemoContextBanner({ context, label = 'Synthetic Demo Context' }: { context: DemoCaseContext; label?: string }) {
  return (
    <section className="mb-5 rounded-xl border border-amber-200 bg-amber-50 p-4" data-testid="demo-context-banner">
      <p className="text-xs font-semibold uppercase tracking-wider text-amber-700">{label}</p>
      <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1">
        <strong>{context.case_key}</strong>
        <span>{context.display_name || 'Synthetic patient'}</span>
        <span>{context.variant.gene} {context.variant.hgvs_p}</span>
        <span>{context.drug.name || 'Drug —'}</span>
        <span>Evidence {context.evidence.level || '—'}</span>
      </div>
      <p className="mt-2 text-xs text-amber-800">本區資料由 bundled synthetic CSV 載入，只用於展示軟體流程、資料契約與可追溯性，不構成診斷或治療建議。</p>
    </section>
  )
}
